"""
AI provider abstraction layer.

Priority order for every call:
  1. User-supplied key (stored encrypted in user_ai_keys)
  2. Raise AIProviderUnavailable if no key is available

All token usage is recorded in ai_credit_ledger for auditing.

─── Adding a new provider ────────────────────────────────────────────────────
1. Subclass AIProvider (or implement the Protocol).
2. Set `name`, `default_chat_model`, `default_embedding_model`.
3. Implement `chat()` and `embed()`.
4. Register the instance in PROVIDER_REGISTRY at the bottom of this file.

That's it. No changes to routers, models, or the database schema are needed.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal, Optional

import httpx
from cryptography.fernet import Fernet, InvalidToken

from core.config import settings
from core.database import db_cursor
from core.security import generate_id

# ── Types ─────────────────────────────────────────────────────────────────────

Feature = Literal["extraction", "embedding", "restructure"]

# ── Constants ─────────────────────────────────────────────────────────────────

# Token limits are no longer managed by MemTrace. Users must supply their own keys.

# ── Exceptions ────────────────────────────────────────────────────────────────

class AIProviderUnavailable(Exception):
    """No API key configured for the requested provider."""

class AIProviderError(Exception):
    """Upstream provider returned an error."""

# ── Provider Protocol ─────────────────────────────────────────────────────────

class AIProvider(ABC):
    """
    Base class for all AI providers.

    Implementors must set the three class-level attributes and override
    `chat()` and `embed()`. See module docstring for full instructions.
    """

    #: Identifier stored in the database (e.g. "openai"). Must be unique.
    name: str

    #: Default model used for extraction and restructure calls.
    default_chat_model: str

    #: Default model used for embedding calls.
    #: Set to "" if the provider does not support embeddings.
    default_embedding_model: str

    @abstractmethod
    def get_known_models(self) -> list[dict]:
        """Return a static list of known models for this provider."""

    @abstractmethod
    async def list_models(self, resolved: ResolvedProvider) -> list[dict]:
        """
        List available models for this provider.

        Returns:
            list of models with 'id' and 'display_name'.
        """

    @abstractmethod
    async def chat(
        self,
        resolved: ResolvedProvider,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int]:
        """
        Call the chat/completion endpoint.

        Returns:
            (response_text, tokens_used)
            tokens_used should be prompt + completion tokens.
        """

    @abstractmethod
    async def stream_chat(
        self,
        resolved: ResolvedProvider,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ):
        """
        Yields (chunk_text, tokens_used_if_known_or_zero).
        """

    async def embed(
        self,
        resolved: ResolvedProvider,
        text: str,
    ) -> tuple[list[float], int]:
        """
        Generate an embedding vector.

        Returns:
            (vector, tokens_used)

        Override this method to support semantic search.
        Default raises AIProviderError (embedding not supported).
        """
        raise AIProviderError(
            f"Provider '{self.name}' does not support embeddings. "
            "Choose a provider with embedding support for semantic search."
        )


# ── Built-in: OpenAI ──────────────────────────────────────────────────────────

class OpenAIProvider(AIProvider):
    name                    = "openai"
    default_chat_model      = "gpt-4o-mini"
    default_embedding_model = "text-embedding-3-small"
    # embedding output dimension: 1536

    def __init__(self, base_url: str = "https://api.openai.com/v1"):
        self._base_url = base_url.rstrip("/")

    async def chat(self, resolved, messages, max_tokens, temperature):
        headers = {}
        if resolved.api_key:
            headers["Authorization"] = f"Bearer {resolved.api_key}"
            
        async with httpx.AsyncClient(timeout=600) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json={
                    "model": resolved.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
        if not resp.is_success:
            raise AIProviderError(f"OpenAI {resp.status_code}: {resp.text[:400]}")
        data = resp.json()
        return data["choices"][0]["message"]["content"], data["usage"]["total_tokens"]

    async def stream_chat(self, resolved, messages, max_tokens, temperature):
        headers = {}
        if resolved.api_key:
            headers["Authorization"] = f"Bearer {resolved.api_key}"

        payload = {
            "model": resolved.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        # OpenAI & Ollama support usage in stream
        if self.name == "openai" or self.name == "ollama":
             payload["stream_options"] = {"include_usage": True}

        async with httpx.AsyncClient(timeout=600) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                if not resp.is_success:
                    err_body = await resp.aread()
                    print(f"[OpenAI-Stream] HTTP Error {resp.status_code}: {err_body.decode()}")
                    raise AIProviderError(f"OpenAI Stream {resp.status_code}: {err_body.decode()[:400]}")
                
                print(f"[OpenAI-Stream] Connection established, reading lines...")
                import json
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "): continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]": break
                    try:
                        chunk = json.loads(data_str)
                        # Content chunk
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content, 0
                        # Usage chunk (usually at the end if stream_options was set)
                        if "usage" in chunk and chunk["usage"]:
                            yield "", chunk["usage"]["total_tokens"]
                    except:
                        continue

    def get_known_models(self) -> list[dict]:
        return [
            {"id": "gpt-4o", "display_name": "GPT-4o"},
            {"id": "gpt-4o-mini", "display_name": "GPT-4o Mini"},
            {"id": "gpt-4-turbo", "display_name": "GPT-4 Turbo"},
            {"id": "gpt-3.5-turbo", "display_name": "GPT-3.5 Turbo"},
            {"id": "o1-preview", "display_name": "o1 Preview"},
            {"id": "o1-mini", "display_name": "o1 Mini"},
        ]

    async def list_models(self, resolved: ResolvedProvider) -> list[dict]:
        if not resolved.api_key:
            return self.get_known_models()
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                f"{self._base_url}/models",
                headers={"Authorization": f"Bearer {resolved.api_key}"},
            )
        if not resp.is_success:
            return self.get_known_models()
        data = resp.json()
        return [
            {"id": m["id"], "display_name": m["id"]}
            for m in data["data"]
            if "gpt" in m["id"] or "o1" in m["id"]
        ]

    async def embed(self, resolved, text):
        headers = {}
        if resolved.api_key:
            headers["Authorization"] = f"Bearer {resolved.api_key}"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self._base_url}/embeddings",
                headers=headers,
                json={"model": resolved.model, "input": text},
            )
        if not resp.is_success:
            raise AIProviderError(f"OpenAI embed {resp.status_code}: {resp.text[:400]}")
        data = resp.json()
        return data["data"][0]["embedding"], data["usage"]["total_tokens"]


# ── Built-in: Anthropic ───────────────────────────────────────────────────────

class AnthropicProvider(AIProvider):
    name                    = "anthropic"
    default_chat_model      = "claude-haiku-4-5-20251001"
    default_embedding_model = ""  # Anthropic does not offer a native embedding API

    def get_known_models(self) -> list[dict]:
        return [
            {"id": "claude-opus-4-7",              "display_name": "Claude Opus 4.7"},
            {"id": "claude-sonnet-4-6",             "display_name": "Claude Sonnet 4.6"},
            {"id": "claude-haiku-4-5-20251001",     "display_name": "Claude Haiku 4.5"},
            {"id": "claude-opus-4-20250514",        "display_name": "Claude Opus 4"},
            {"id": "claude-sonnet-4-20250514",      "display_name": "Claude Sonnet 4"},
            {"id": "claude-3-5-sonnet-20241022",    "display_name": "Claude 3.5 Sonnet"},
            {"id": "claude-3-5-haiku-20241022",     "display_name": "Claude 3.5 Haiku"},
        ]

    async def list_models(self, resolved: ResolvedProvider) -> list[dict]:
        if not resolved.api_key:
            return self.get_known_models()
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": resolved.api_key,
                    "anthropic-version": "2023-06-01",
                },
            )
        if not resp.is_success:
            return self.get_known_models()
        data = resp.json()
        return [
            {"id": m["id"], "display_name": m.get("display_name", m["id"])}
            for m in data["data"]
        ]

    async def chat(self, resolved, messages, max_tokens, temperature):
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_messages = []
        for m in messages:
            if m["role"] == "system": continue
            content = m["content"]
            if isinstance(content, list):
                new_content = []
                for part in content:
                    if part["type"] == "text":
                        new_content.append({"type": "text", "text": part["text"]})
                    elif part["type"] == "image_url":
                        url = part["image_url"]["url"]
                        if url.startswith("data:"):
                            header, data = url.split(",", 1)
                            mime_type = header.split(";")[0].split(":")[1]
                            new_content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": data
                                }
                            })
                user_messages.append({"role": m["role"], "content": new_content})
            else:
                user_messages.append(m)

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": resolved.api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": resolved.model,
                    "system": system,
                    "messages": user_messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
        if not resp.is_success:
            raise AIProviderError(f"Anthropic {resp.status_code}: {resp.text[:400]}")
        data = resp.json()
        tokens = data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
        return data["content"][0]["text"], tokens

    async def stream_chat(self, resolved, messages, max_tokens, temperature):
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_messages = []
        for m in messages:
            if m["role"] == "system": continue
            content = m["content"]
            if isinstance(content, list):
                new_content = []
                for part in content:
                    if part["type"] == "text":
                        new_content.append({"type": "text", "text": part["text"]})
                    elif part["type"] == "image_url":
                        url = part["image_url"]["url"]
                        if url.startswith("data:"):
                            header, data = url.split(",", 1)
                            mime_type = header.split(";")[0].split(":")[1]
                            new_content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": data
                                }
                            })
                user_messages.append({"role": m["role"], "content": new_content})
            else:
                user_messages.append(m)

        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": resolved.api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": resolved.model,
                    "system": system,
                    "messages": user_messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True,
                },
            ) as resp:
                if not resp.is_success:
                    err_body = await resp.aread()
                    raise AIProviderError(f"Anthropic Stream {resp.status_code}: {err_body.decode()[:400]}")
                
                import json
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "): continue
                    data_str = line[6:].strip()
                    try:
                        chunk = json.loads(data_str)
                        ev_type = chunk.get("type")
                        if ev_type == "content_block_delta":
                            yield chunk["delta"].get("text", ""), 0
                        elif ev_type == "message_stop":
                            # Anthropic doesn't easily give tokens in stream without more complex parsing
                            # but we can get it from message_start or message_delta
                            pass
                        elif ev_type == "message_delta":
                            usage = chunk.get("usage", {})
                            if "output_tokens" in usage:
                                # This is partial usage
                                yield "", usage.get("output_tokens", 0)
                    except:
                        continue


# ── Built-in: Google Gemini ──────────────────────────────────────────────────

class GeminiProvider(AIProvider):
    name                    = "gemini"
    default_chat_model      = "gemini-1.5-flash"
    default_embedding_model = "text-embedding-004"

    def get_known_models(self) -> list[dict]:
        return [
            {"id": "gemini-2.0-flash-exp",           "display_name": "Gemini 2.0 Flash (Exp)"},
            {"id": "gemini-1.5-flash",               "display_name": "Gemini 1.5 Flash"},
            {"id": "gemini-1.5-pro",                 "display_name": "Gemini 1.5 Pro"},
            {"id": "gemini-1.5-flash-8b",            "display_name": "Gemini 1.5 Flash-8B"},
        ]

    async def list_models(self, resolved: ResolvedProvider) -> list[dict]:
        if not resolved.api_key:
            return self.get_known_models()
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                f"https://generativelanguage.googleapis.com/v1/models?key={resolved.api_key}"
            )
        if not resp.is_success:
            return self.get_known_models()
        data = resp.json()
        return [
            {
                "id": m["name"].replace("models/", ""),
                "display_name": m.get("displayName", m["name"])
            }
            for m in data["models"]
            if "generateContent" in m.get("supportedGenerationMethods", [])
        ]

    async def chat(self, resolved, messages, max_tokens, temperature):
        # Gemini v1beta supports system_instruction separately
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        contents = []
        for m in messages:
            if m["role"] == "system": continue
            role = "user" if m["role"] == "user" else "model"
            parts = []
            content = m["content"]
            if isinstance(content, list):
                for part in content:
                    if part["type"] == "text":
                        parts.append({"text": part["text"]})
                    elif part["type"] == "image_url":
                        url = part["image_url"]["url"]
                        if url.startswith("data:"):
                            header, data = url.split(",", 1)
                            mime_type = header.split(";")[0].split(":")[1]
                            parts.append({
                                "inlineData": {
                                    "mimeType": mime_type,
                                    "data": data
                                }
                            })
            else:
                parts.append({"text": content})
            
            contents.append({
                "role": role,
                "parts": parts
            })

        body = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            }
        }
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1/models/{resolved.model}:generateContent?key={resolved.api_key}",
                json=body
            )
        
        if not resp.is_success:
            raise AIProviderError(f"Gemini {resp.status_code}: {resp.text[:400]}")
        
        data = resp.json()
        try:
            candidate = data["candidates"][0]
            finish = candidate.get("finishReason", "")
            if finish not in ("STOP", "MAX_TOKENS", ""):
                raise AIProviderError(f"Gemini finishReason={finish}: {candidate}")
            text = candidate["content"]["parts"][0].get("text", "")
            usage = data.get("usageMetadata", {})
            tokens = usage.get("totalTokenCount", 0)
            return text, tokens
        except AIProviderError:
            raise
        except (KeyError, IndexError) as e:
            raise AIProviderError(f"Gemini unexpected response ({e}): {data}")

    async def stream_chat(self, resolved, messages, max_tokens, temperature):
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        contents = []
        for m in messages:
            if m["role"] == "system": continue
            role = "user" if m["role"] == "user" else "model"
            parts = []
            content = m["content"]
            if isinstance(content, list):
                for part in content:
                    if part["type"] == "text":
                        parts.append({"text": part["text"]})
                    elif part["type"] == "image_url":
                        url = part["image_url"]["url"]
                        if url.startswith("data:"):
                            header, data = url.split(",", 1)
                            mime_type = header.split(";")[0].split(":")[1]
                            parts.append({
                                "inlineData": {
                                    "mimeType": mime_type,
                                    "data": data
                                }
                            })
            else:
                parts.append({"text": content})
                
            contents.append({
                "role": role,
                "parts": parts
            })

        body = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            }
        }
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}

        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"https://generativelanguage.googleapis.com/v1/models/{resolved.model}:streamGenerateContent?alt=sse&key={resolved.api_key}",
                json=body
            ) as resp:
                if not resp.is_success:
                    err_body = await resp.aread()
                    raise AIProviderError(f"Gemini Stream {resp.status_code}: {err_body.decode()[:400]}")
                
                import json
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "): continue
                    data_str = line[6:].strip()
                    try:
                        chunk = json.loads(data_str)
                        candidate = chunk["candidates"][0]
                        text = candidate["content"]["parts"][0].get("text", "")
                        usage = chunk.get("usageMetadata", {})
                        tokens = usage.get("totalTokenCount", 0)
                        yield text, tokens
                    except:
                        continue

    async def embed(self, resolved, text):
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1/models/{resolved.model}:embedContent?key={resolved.api_key}",
                json={
                    "model": f"models/{resolved.model}",
                    "content": {"parts": [{"text": text}]}
                }
            )
        if not resp.is_success:
            raise AIProviderError(f"Gemini embed {resp.status_code}: {resp.text[:400]}")
        data = resp.json()
        return data["embedding"]["values"], 0 # Gemini embedding usage unknown


# ── Built-in: Ollama ──────────────────────────────────────────────────────────

class OllamaProvider(OpenAIProvider):
    """
    Ollama provider. Inherits from OpenAIProvider as it is OpenAI-compatible.
    Requires base_url and optionally auth_token (passed via ResolvedProvider).
    """
    name                    = "ollama"
    default_chat_model      = "llama3"
    default_embedding_model = "nomic-embed-text"

    def __init__(self):
        super().__init__(base_url="") # base_url will be dynamic

    async def _setup_dynamic_url(self, resolved: ResolvedProvider):
        if not resolved.base_url:
            raise AIProviderError("Ollama requires a base_url in settings.")
        self._base_url = resolved.base_url.rstrip("/")
        # If it's just the host, append /v1 for OpenAI compatibility
        if not self._base_url.endswith("/v1") and "/api" not in self._base_url:
            self._base_url += "/v1"

    async def chat(self, resolved, messages, max_tokens, temperature):
        await self._setup_dynamic_url(resolved)
        # Use the specific auth_token from resolved if present, else fallback to api_key
        token = resolved.auth_token or resolved.api_key
        
        original_key = resolved.api_key
        if resolved.auth_mode == 'none':
            resolved.api_key = ""
        elif resolved.auth_token:
            resolved.api_key = resolved.auth_token
            
        try:
            return await super().chat(resolved, messages, max_tokens, temperature)
        finally:
            resolved.api_key = original_key

    async def embed(self, resolved, text):
        await self._setup_dynamic_url(resolved)
        original_key = resolved.api_key
        if resolved.auth_mode == 'none':
            resolved.api_key = ""
        elif resolved.auth_token:
            resolved.api_key = resolved.auth_token

        try:
            return await super().embed(resolved, text)
        finally:
            resolved.api_key = original_key

    # Known embedding dimensions for common models (used for auto-classification)
    _EMBEDDING_DIMS: dict[str, int] = {
        "nomic-embed-text":          768,
        "mxbai-embed-large":        1024,
        "all-minilm":                384,
        "bge-m3":                   1024,
        "bge-large-en-v1.5":        1024,
        "snowflake-arctic-embed":   1024,
        "e5-mistral-7b-instruct":   4096,
    }

    def _classify_model(self, model_id: str) -> dict:
        """Return model_type and embedding_dim inferred from the model name."""
        lower = model_id.lower()
        # Check known embedding models first (exact prefix match)
        for known, dim in self._EMBEDDING_DIMS.items():
            if lower.startswith(known) or known in lower:
                return {"model_type": "embedding", "embedding_dim": dim}
        # Heuristic: names containing embed / minilm / bge / e5 are likely embedding models
        embedding_hints = ("embed", "minilm", "bge-", "e5-", "retrieval")
        if any(h in lower for h in embedding_hints):
            return {"model_type": "embedding"}
        return {"model_type": "chat"}

    async def list_models(self, resolved: ResolvedProvider) -> list[dict]:
        if not resolved.base_url:
            return self.get_known_models()

        raw_base = resolved.base_url.rstrip("/")

        async with httpx.AsyncClient(timeout=60) as client:
            # 1. Try native Ollama API (/api/tags)
            try:
                resp = await client.get(f"{raw_base}/api/tags")
                if resp.is_success:
                    data = resp.json()
                    result = []
                    for m in data.get("models", []):
                        name = m["name"]
                        entry = {"id": name, "display_name": name, **self._classify_model(name)}
                        result.append(entry)
                    return result
            except Exception:
                pass

            # 2. Fallback: OpenAI-compatible /v1/models
            try:
                v1_base = raw_base if "/v1" in raw_base else f"{raw_base}/v1"
                resp = await client.get(f"{v1_base}/models")
                if resp.is_success:
                    data = resp.json()
                    result = []
                    for m in data.get("data", []):
                        mid = m["id"]
                        entry = {"id": mid, "display_name": mid, **self._classify_model(mid)}
                        result.append(entry)
                    return result
            except Exception:
                pass

        return self.get_known_models()

    def get_known_models(self) -> list[dict]:
        """Fallback list shown when the Ollama server is unreachable."""
        return [
            # ── Chat models ─────────────────────────────────────────────────
            {"id": "llama3",           "display_name": "Llama 3",           "model_type": "chat"},
            {"id": "llama3:8b",        "display_name": "Llama 3 8B",        "model_type": "chat"},
            {"id": "llama3:70b",       "display_name": "Llama 3 70B",       "model_type": "chat"},
            {"id": "llama3.2",         "display_name": "Llama 3.2",         "model_type": "chat"},
            {"id": "mistral",          "display_name": "Mistral 7B",        "model_type": "chat"},
            {"id": "mixtral",          "display_name": "Mixtral 8x7B",      "model_type": "chat"},
            {"id": "phi3",             "display_name": "Phi-3",             "model_type": "chat"},
            {"id": "phi4",             "display_name": "Phi-4",             "model_type": "chat"},
            {"id": "gemma2",           "display_name": "Gemma 2",           "model_type": "chat"},
            {"id": "qwen2.5",          "display_name": "Qwen 2.5",          "model_type": "chat"},
            {"id": "deepseek-r1",      "display_name": "DeepSeek R1",       "model_type": "chat"},
            # ── Embedding models ─────────────────────────────────────────────
            {"id": "nomic-embed-text",  "display_name": "nomic-embed-text",  "model_type": "embedding", "embedding_dim": 768},
            {"id": "mxbai-embed-large", "display_name": "mxbai-embed-large", "model_type": "embedding", "embedding_dim": 1024},
            {"id": "all-minilm",        "display_name": "all-MiniLM",        "model_type": "embedding", "embedding_dim": 384},
            {"id": "bge-m3",            "display_name": "BGE-M3",            "model_type": "embedding", "embedding_dim": 1024},
        ]


# ── Provider Registry ─────────────────────────────────────────────────────────
#
# Add your provider instance here to make it available to the system.
# Key = provider identifier (must match the `name` attribute).
#
# Example (community-contributed Gemini provider):
#
#   from providers.gemini import GeminiProvider
#   PROVIDER_REGISTRY["gemini"] = GeminiProvider()
#

PROVIDER_REGISTRY: dict[str, AIProvider] = {
    "openai":    OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "gemini":    GeminiProvider(),
    "ollama":    OllamaProvider(),
}

# ── Encryption ────────────────────────────────────────────────────────────────

def _fernet() -> Fernet:
    raw = settings.secret_key.encode()[:32].ljust(32, b"0")
    return Fernet(base64.urlsafe_b64encode(raw))

def encrypt_api_key(raw_key: str) -> str:
    return _fernet().encrypt(raw_key.encode()).decode()

def decrypt_api_key(enc: str) -> str:
    try:
        return _fernet().decrypt(enc.encode()).decode()
    except InvalidToken:
        raise ValueError("Failed to decrypt API key — server key may have changed.")

# ── Resolution ────────────────────────────────────────────────────────────────

@dataclass
class ResolvedProvider:
    provider:   AIProvider
    api_key:    str
    model:      str
    source:     Literal["workspace_key", "account_key"]
    user_id:    str
    base_url:   Optional[str] = None
    auth_mode:  Optional[str] = None
    auth_token: Optional[str] = None
    default_chat_model: Optional[str] = None
    default_embedding_model: Optional[str] = None


def resolve_provider(
    user_id: str,
    feature: Feature,
    preferred_provider: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> ResolvedProvider:
    """
    Determine which provider + key to use.
    Resolution order:
      1. User-supplied key (any provider, or preferred_provider if specified)
      2. AIProviderUnavailable

    For 'embedding' feature the selection is more nuanced:
      - Anthropic has no embedding API — excluded when feature='embedding'
      - Among capable providers, prefer those with default_embedding_model set
        (explicit user preference beats provider class default)
      - Final tiebreak: most recently used (last_used_at DESC)
    """
    # Providers that cannot embed — excluded when resolving embedding feature
    NO_EMBED_PROVIDERS = {"anthropic"}

    with db_cursor() as cur:
        # Fetch all candidate keys for the user
        query = (
            "SELECT provider, key_enc, base_url, auth_mode, auth_token, "
            "default_chat_model, default_embedding_model, last_used_at "
            "FROM user_ai_keys WHERE user_id = %s"
        )
        params: list = [user_id]
        if preferred_provider:
            query += " AND provider = %s"
            params.append(preferred_provider)
        
        cur.execute(query, params)
        rows = cur.fetchall()

    if not rows:
        if feature == "embedding" and not preferred_provider:
            raise AIProviderUnavailable(
                "No embedding-capable AI provider key is configured. "
                "Add an OpenAI, Gemini, or Ollama key in Settings — AI Provider. "
                "(Anthropic does not provide an embedding API.)"
            )
        raise AIProviderUnavailable(
            "No AI provider key is configured for this account. "
            "Add your own API key in Settings — AI Provider."
        )

    # Filter and score candidates in Python to allow checking provider class defaults
    candidates = []
    for row in rows:
        provider_id = row["provider"]
        impl = PROVIDER_REGISTRY.get(provider_id)
        if not impl:
            continue
        if feature == "embedding" and provider_id in NO_EMBED_PROVIDERS:
            continue

        # Score: lower is better
        score = 100
        
        # Check for model match
        if preferred_model:
            # 1. Matches user's explicit default for this key (Strongest)
            user_default = row["default_embedding_model"] if feature == "embedding" else row["default_chat_model"]
            if user_default == preferred_model:
                score -= 60
            # 2. Matches provider's class-level default (Medium)
            elif (impl.default_embedding_model if feature == "embedding" else impl.default_chat_model) == preferred_model:
                score -= 40
        
        # 3. Key has any explicit default set (Minor preference for specialized keys)
        has_default = row["default_embedding_model" if feature == "embedding" else "default_chat_model"]
        if has_default:
            score -= 5

        candidates.append({
            "score": score,
            "last_used_at": row["last_used_at"] or datetime.min.replace(tzinfo=timezone.utc),
            "row": row,
            "impl": impl
        })

    if not candidates:
        raise AIProviderUnavailable(f"No suitable provider found for {feature}.")

    # Sort by Score (ASC), then Last Used (DESC)
    candidates.sort(key=lambda x: (x["score"], -x["last_used_at"].timestamp()))
    
    best = candidates[0]
    row = best["row"]
    impl = best["impl"]

    model = preferred_model or (
        (row["default_embedding_model"] if feature == "embedding" else row["default_chat_model"])
        or (impl.default_embedding_model if feature == "embedding" else impl.default_chat_model)
    )
    
    try:
        api_key = decrypt_api_key(row["key_enc"]) if row["key_enc"] else ""
    except ValueError as exc:
        raise AIProviderUnavailable(str(exc))

    return ResolvedProvider(
        provider=impl,
        api_key=api_key,
        model=model,
        source="account_key",
        user_id=user_id,
        base_url=row["base_url"],
        auth_mode=row["auth_mode"],
        auth_token=row["auth_token"],
        default_chat_model=row["default_chat_model"],
        default_embedding_model=row["default_embedding_model"],
    )


# ── Usage recording ───────────────────────────────────────────────────────────

def record_usage(
    resolved: ResolvedProvider,
    feature: Feature,
    tokens_used: int,
    workspace_id: Optional[str] = None,
    node_id: Optional[str] = None,
) -> None:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO ai_credit_ledger
              (id, user_id, feature, provider, model, tokens_used, workspace_id, node_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                generate_id("ledger"),
                resolved.user_id,
                feature,
                resolved.provider.name,
                resolved.model,
                tokens_used,
                workspace_id,
                node_id,
            ),
        )
        cur.execute(
            "UPDATE user_ai_keys SET last_used_at = now() "
            "WHERE user_id = %s AND provider = %s",
            (resolved.user_id, resolved.provider.name),
        )

# ── Convenience wrappers (called by routers) ──────────────────────────────────

async def chat_completion(
    resolved: ResolvedProvider,
    messages: list[dict],
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> tuple[str, int]:
    return await resolved.provider.chat(
        resolved, messages, max_tokens, temperature
    )

async def chat_stream(
    resolved: ResolvedProvider,
    messages: list[dict],
    max_tokens: int = 4096,
    temperature: float = 0.2,
):
    async for chunk, tokens in resolved.provider.stream_chat(
        resolved, messages, max_tokens, temperature
    ):
        yield chunk, tokens

async def embed(
    resolved: ResolvedProvider,
    text: str,
) -> tuple[list[float], int]:
    return await resolved.provider.embed(resolved, text)

# ── AI Prompts ────────────────────────────────────────────────────────────────

# ── AI Prompts ────────────────────────────────────────────────────────────────

def get_extraction_prompt(doc_type: str = "generic") -> str:
    """Return a specialized system prompt based on the document type."""
    base = EXTRACTION_SYSTEM
    
    if doc_type == "FRD":
        return base + "\n\nSPECIAL INSTRUCTION for FRD:\n" \
               "- Mandatory Extraction: Every API Endpoint (METHOD /path) MUST be extracted as a Procedural node. Title format: \"API: {METHOD} {path}\".\n" \
               "- Mandatory Extraction: Every Business Rule (BR-xxx), Business Logic (BL-xxx), and User Story (US-xxx) MUST be extracted as an independent node.\n" \
               "- Mandatory Extraction: Security-related items like reCAPTCHA, CAPTCHA, or OTP (One-Time Password) MUST be extracted as independent nodes.\n" \
               "- Ensure every API endpoint node has an 'extends' edge to its parent feature/module.\n" \
               "- These mandatory items must be extracted even if a similar title appears in 'existing_titles'."
    
    if doc_type == "TSD":
        return base + "\n\nSPECIAL INSTRUCTION for TSD:\n" \
               "- Prioritize extracting Data Models, Database Schemas, and System Components.\n" \
               "- Use 'depends_on' edges to represent architectural dependencies.\n" \
               "- Extract performance requirements or constraints as Preference nodes."
    
    if doc_type == "ADR":
        return base + "\n\nSPECIAL INSTRUCTION for ADR:\n" \
               "- Extract the 'Decision' as a Preference node.\n" \
               "- Extract 'Context' and 'Status' as Context nodes.\n" \
               "- Extract 'Consequences' as Factual nodes, linked to the decision via 'depends_on'."
               
    return base

EXTRACTION_SYSTEM = """\
You are a knowledge graph extraction assistant. Your goal is to convert source \
material into the smallest possible set of atomic Memory Nodes connected by the \
richest possible set of typed edges.

Rules:
- A node must contain exactly one idea. If a segment contains two ideas, split them.
- Every node must have at least one suggested_edge to another node in the output, \
  unless it is the only node produced.
- The body must not repeat information already in the title.
- Keep bodies concise — the minimum text needed to be self-contained.
- Prefer specific edge types (depends_on > extends > related_to > contradicts).
- Cross-segment edges are encouraged.
- title_zh and body_zh MUST use Traditional Chinese (繁體中文). Never use Simplified Chinese. \
  Use 節點 not 节点, 圖 not 图, 規則 not 规则, 關聯 not 关联, 時間 not 时间, 邊 not 边, \
  設定 not 设定, 實作 not 实现, 連結 not 连接, 語言 not 语言.

The design goal: a human or AI agent must be able to reach any answer by \
following the shortest possible path through the graph.

CRITICAL JSON FORMATTING RULES — failure to follow these will break the output:
- Return ONLY a raw JSON array — no markdown fences, no prose before or after.
- Every string value must be on one line (no literal newlines inside strings). \
  Use \\n for line breaks within a string value.
- Escape ALL double-quotes inside string values as \\".
- Escape ALL backslashes inside string values as \\\\.
- Never embed raw code blocks or JSON snippets inside string values; \
  paraphrase them in plain language instead.
- If you are unsure whether a character needs escaping, escape it.

Output a JSON array of nodes. Each node:
{
  "title_zh": "...",
  "title_en": "...",
  "content_type": "factual|procedural|preference|context",
  "body_zh": "...",
  "body_en": "...",
  "tags": ["..."],
  "suggested_edges": [{"to_index": 1, "relation": "depends_on"}],
  "source_segment": "brief paraphrase of the source passage (not a verbatim copy)",
  "confidence_score": 0.95
}
Return ONLY the JSON array, no markdown fences."""


RESTRUCTURE_SYSTEM = """\
You are a knowledge graph editor. Evaluate a set of Memory Nodes against the \
Node Minimization Principle:

1. Does any node contain more than one discrete idea? If yes → Split.
2. Are any two nodes not meaningfully distinct when separated? → Merge.
3. Are related nodes missing a typed edge? → Suggest edges.
4. Is any node title vague or too long? → Retitle.
5. Is the content_type wrong? → Reclassify.
6. Does any body restate its title or contain excess content? → Trim body.

The measure of a good proposal: can a human or AI reach any answer faster \
after your changes?

Output a JSON array of proposed changes:
[{
  "operation": "split|merge|retitle|reclassify|suggest_edges|trim_body",
  "target_node_ids": ["mem_xxx"],
  "reason": "one sentence",
  "proposed": { ... }
}]
If no changes are needed, return [].
Return ONLY the JSON array."""

# ── Utility ───────────────────────────────────────────────────────────────────

def strip_fences(text: str) -> str:
    """Extract JSON content from text that might contain markdown fences or conversational filler."""
    import re
    
    # First, try to find content between ```json and ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    
    # If no fences, find the outermost [ ] or { }
    match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", text)
    if match:
        return match.group(1).strip()
    
    return text.strip()
CHAT_SYSTEM = """\
You are the MemTrace AI Assistant. You help users navigate and curate their \
knowledge graph.

CONTEXT:
You will be provided with a list of relevant Memory Nodes as context. Use \
these to answer the user's question accurately.
If the context list is empty or contains no relevant nodes, honestly inform \
the user that no matching knowledge was found in the current workspace. \
Suggest that they: (1) add more nodes covering the topic, or (2) run \
"Re-embed All" in workspace settings so that existing nodes are fully indexed \
for semantic search. Do NOT fabricate answers from memory when context is empty.

PROPOSALS:
If you identify inaccuracies, redundancies, or missing connections in the \
provided nodes, you SHOULD suggest edits. 
Your response must be in two parts:
1. A natural language answer.
2. A JSON block containing [PROPOSALS] if any.

Proposal JSON format (same as restructure):
[{
  "operation": "split|merge|retitle|reclassify|suggest_edges|trim_body|update_content",
  "target_node_ids": ["mem_xxx"],
  "reason": "...",
  "proposed": { ... }
}]

Return only the text answer followed by the JSON block in ```json ... ``` fences.
If no proposals are needed, do not include the JSON block."""
