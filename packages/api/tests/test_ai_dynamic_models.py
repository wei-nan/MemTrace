"""Task B (ws_spec_plan/mem_6ee3ee82): dynamic-only provider model lists.

Model lists must come live from the provider when the key is valid; there is no
hardcoded fallback, so an unconfigured / invalid key yields no usable models.
"""
import sys
import os
import types

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ai import OpenAIProvider, AnthropicProvider, GeminiProvider

_KEY_PROVIDERS = (OpenAIProvider, AnthropicProvider, GeminiProvider)


@pytest.mark.asyncio
async def test_no_key_yields_empty_model_list():
    resolved = types.SimpleNamespace(api_key="")
    for provider_cls in _KEY_PROVIDERS:
        models = await provider_cls().list_models(resolved)
        assert models == [], f"{provider_cls.__name__} should return [] without a key"


def test_get_known_models_has_no_hardcoded_fallback():
    for provider_cls in _KEY_PROVIDERS:
        assert provider_cls().get_known_models() == [], (
            f"{provider_cls.__name__} must not present a hardcoded model list"
        )
