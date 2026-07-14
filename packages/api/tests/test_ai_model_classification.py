"""Task A (ws_spec_plan/mem_a1a93bfd): AI model-list classification correctness.

Non-text generative models (image / TTS / video) must be excluded from the
language-model (chat) picker even when a provider exposes them via the same call
surface as chat models (e.g. Gemini's gemini-2.5-flash-image "Nano Banana").
"""
import sys
import os
import types

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ai import is_non_text_model, OllamaProvider, GeminiProvider


def test_is_non_text_model_flags_image_tts_video():
    assert is_non_text_model("gemini-2.5-flash-image", "Nano Banana") is True
    assert is_non_text_model("imagen-3.0-generate-002") is True
    assert is_non_text_model("gemini-2.5-flash-preview-tts") is True
    assert is_non_text_model("veo-2.0-generate-001") is True


def test_is_non_text_model_keeps_language_models():
    assert is_non_text_model("gemini-2.5-flash") is False
    assert is_non_text_model("gpt-4.1") is False
    assert is_non_text_model("claude-opus-4-8") is False
    assert is_non_text_model("qwen2.5-coder:7b") is False
    # vision-INPUT multimodal still outputs text → remains a language model
    assert is_non_text_model("llava:13b") is False


def test_ollama_classify_excludes_non_text_from_chat():
    p = OllamaProvider()
    assert p._classify_model("gemma4:latest")["model_type"] == "chat"
    assert p._classify_model("qwen2.5-coder:7b")["model_type"] == "chat"
    assert p._classify_model("bge-m3:latest")["model_type"] == "embedding"
    assert p._classify_model("nomic-embed-text:latest")["model_type"] == "embedding"
    # image / tts pulled into ollama must not be offered as chat
    assert p._classify_model("sdxl-image")["model_type"] != "chat"
    assert p._classify_model("xtts-v2")["model_type"] != "chat"


class _FakeResp:
    is_success = True

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, **kwargs):
        return _FakeResp(self._payload)


@pytest.mark.asyncio
async def test_gemini_list_models_excludes_image_and_tts(monkeypatch):
    payload = {
        "models": [
            {"name": "models/gemini-2.5-flash", "displayName": "Gemini 2.5 Flash",
             "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-2.5-flash-image", "displayName": "Nano Banana",
             "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-2.5-flash-preview-tts", "displayName": "Flash TTS",
             "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/text-embedding-004", "displayName": "text-embedding-004",
             "supportedGenerationMethods": ["embedContent"]},
        ]
    }
    monkeypatch.setattr("core.ai.httpx.AsyncClient", lambda *a, **k: _FakeClient(payload))

    resolved = types.SimpleNamespace(api_key="test-key")
    models = await GeminiProvider().list_models(resolved)

    ids = {m["id"] for m in models}
    assert "gemini-2.5-flash" in ids                       # language model kept
    assert "gemini-2.5-flash-image" not in ids             # Nano Banana excluded
    assert "gemini-2.5-flash-preview-tts" not in ids       # TTS excluded
    # embedding still classified as embedding (not chat)
    embed = [m for m in models if m["id"] == "text-embedding-004"]
    assert embed and embed[0]["model_type"] == "embedding"
    # every chat entry is genuinely a language model
    assert all(m["model_type"] == "chat" for m in models if m["id"] != "text-embedding-004")
