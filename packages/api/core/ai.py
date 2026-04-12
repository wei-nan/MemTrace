"""
AI provider abstraction layer.

Priority order for every call:
  1. User-supplied key (stored encrypted in user_ai_keys)
  2. Managed free-tier credits (up to FREE_TOKEN_LIMIT per month)
  3. Raise AIProviderUnavailable if neither is available

All token usage is recorded in ai_credit_ledger regardless of source.

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

FREE_TOKEN_LIMIT: int = getattr(settings, "ai_free_token_limit", 50_000)

# ── Exceptions ────────────────────────────────────────────────────────────────

class AIProviderUnavailable(Exception):
    """No API key and no free quota available."""

class AIQuotaExceeded(Exception):
    """User has exhausted their free monthly quota."""

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
    async def chat(
        self,
        api_key: str,
        model: str,
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

    async def embed(
        self,
        api_key: str,
        model: str,
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

    async def chat(self, api_key, model, messages, max_tokens, temperature):
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
        if not resp.is_success:
            raise AIProviderError(f"OpenAI {resp.status_code}: {resp.text[:400]}")
        data = resp.json()
        return data["choices"][0]["message"]["content"], data["usage"]["total_tokens"]

    async def embed(self, api_key, model, text):
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._base_url}/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "input": text},
            )
        if not resp.is_success:
            raise AIProviderError(f"OpenAI embed {resp.status_code}: {resp.text[:400]}")
        data = resp.json()
        return data["data"][0]["embedding"], data["usage"]["total_tokens"]


# ── Built-in: Anthropic ───────────────────────────────────────────────────────

class AnthropicProvider(AIProvider):
    name                    = "anthropic"
    default_chat_model      = "claude-3-haiku-20240307"
    default_embedding_model = ""  # Anthropic does not offer a native embedding API

    async def chat(self, api_key, model, messages, max_tokens, temperature):
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_messages = [m for m in messages if m["role"] != "system"]

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": model,
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
    source:     Literal["user_key", "managed"]
    user_id:    str


def resolve_provider(
    user_id: str,
    feature: Feature,
    preferred_provider: Optional[str] = None,
) -> ResolvedProvider:
    """
    Determine which provider + key to use.

    Resolution order:
      1. User-supplied key (any provider, or preferred_provider if specified)
      2. Managed free-tier credits via server key
      3. AIQuotaExceeded / AIProviderUnavailable
    """
    with db_cursor() as cur:
        # ── 1. User-supplied key ───────────────────────────────────────────
        query = "SELECT provider, key_enc FROM user_ai_keys WHERE user_id = %s"
        params: list = [user_id]
        if preferred_provider:
            query += " AND provider = %s"
            params.append(preferred_provider)
        query += " ORDER BY last_used_at DESC NULLS LAST LIMIT 1"
        cur.execute(query, params)
        row = cur.fetchone()

        if row:
            provider_id: str = row["provider"]
            impl = PROVIDER_REGISTRY.get(provider_id)
            if not impl:
                raise AIProviderUnavailable(
                    f"Provider '{provider_id}' is not installed on this server."
                )
            model = (
                impl.default_embedding_model
                if feature == "embedding"
                else impl.default_chat_model
            )
            return ResolvedProvider(
                provider=impl,
                api_key=decrypt_api_key(row["key_enc"]),
                model=model,
                source="user_key",
                user_id=user_id,
            )

        # ── 2. Managed free credits ────────────────────────────────────────
        cur.execute(
            "SELECT ai_free_tokens_remaining(%s, %s) AS remaining",
            (user_id, FREE_TOKEN_LIMIT),
        )
        remaining = cur.fetchone()["remaining"]

        if remaining <= 0:
            raise AIQuotaExceeded(
                f"Free tier limit of {FREE_TOKEN_LIMIT:,} tokens/month reached. "
                "Add your own API key in Settings → AI Provider to continue."
            )

        managed_id: str = preferred_provider or "openai"
        managed_key = getattr(settings, f"{managed_id}_api_key", "")
        impl = PROVIDER_REGISTRY.get(managed_id)

        if not impl or not managed_key:
            raise AIProviderUnavailable(
                "No AI provider is configured on this server. "
                "Add your own API key in Settings → AI Provider."
            )

        model = (
            impl.default_embedding_model
            if feature == "embedding"
            else impl.default_chat_model
        )
        return ResolvedProvider(
            provider=impl,
            api_key=managed_key,
            model=model,
            source="managed",
            user_id=user_id,
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
        if resolved.source == "managed":
            cur.execute(
                "SELECT ai_deduct_free_tokens(%s, %s)",
                (resolved.user_id, tokens_used),
            )
        if resolved.source == "user_key":
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
        resolved.api_key, resolved.model, messages, max_tokens, temperature
    )

async def embed(
    resolved: ResolvedProvider,
    text: str,
) -> tuple[list[float], int]:
    return await resolved.provider.embed(resolved.api_key, resolved.model, text)

# ── AI Prompts ────────────────────────────────────────────────────────────────

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

The design goal: a human or AI agent must be able to reach any answer by \
following the shortest possible path through the graph.

Output a JSON array of nodes. Each node:
{
  "title_zh": "...",
  "title_en": "...",
  "content_type": "factual|procedural|preference|context",
  "body_zh": "...",
  "body_en": "...",
  "tags": ["..."],
  "suggested_edges": [{"to_index": 1, "relation": "depends_on"}]
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

# ── Utility ────────────────────────────────────────────────────────────────────

def strip_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped its JSON output."""
    import re
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()
