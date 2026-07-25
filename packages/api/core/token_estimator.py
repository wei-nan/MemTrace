"""
TokenEstimator: Unified 3-level Token Measurement Module for MemTrace.

Level 1 (Lexical): CJK and Unicode-aware character & word heuristic estimation (zero dependencies).
Level 2 (Vendor Calibration): Vendor-specific tokenizers (tiktoken for OpenAI, fallback to Lexical).
Level 3 (Analytics): Standardized token usage calculations for analytics reports.
"""

import logging
import re
from typing import Optional, List

logger = logging.getLogger(__name__)

# Try loading optional vendor tokenizers
_TIKTOKEN_ENCODER = None
try:
    import tiktoken
    _TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _TIKTOKEN_ENCODER = None


class TokenEstimator:
    """Unified Token Estimator for MemTrace."""

    @staticmethod
    def estimate_lexical(text: str) -> int:
        """
        Level 1 (Lexical): Heuristic token estimation.
        - Non-CJK (EN/Latin): ~4 characters per token (or ~1.3 tokens per word).
        - CJK (Chinese, Japanese, Korean): ~1.5 to 2 tokens per character.
        """
        if not text:
            return 0

        # Count CJK characters
        cjk_chars = len(re.findall(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', text))
        non_cjk_chars = len(text) - cjk_chars

        # Heuristic ratio: ~1.5 tokens per CJK char, ~0.25 tokens per Non-CJK char
        estimated = int(cjk_chars * 1.5 + non_cjk_chars * 0.25)
        return max(1, estimated)

    @staticmethod
    def estimate_vendor(text: str, provider: str = "openai", model_name: Optional[str] = None) -> int:
        """
        Level 2 (Vendor Calibration): Uses vendor tokenizers when available, falling back to Lexical.
        """
        if not text:
            return 0

        provider_clean = (provider or "generic").lower()

        if provider_clean == "openai" or model_name and "gpt" in model_name.lower():
            if _TIKTOKEN_ENCODER is not None:
                try:
                    return len(_TIKTOKEN_ENCODER.encode(text))
                except Exception as e:
                    logger.debug(f"tiktoken encoding failed: {e}")

        # Fallback for Anthropic / Gemini / Cursor / Ollama or when tiktoken is unavailable
        return TokenEstimator.estimate_lexical(text)

    @classmethod
    def estimate(cls, text: str, provider: str = "generic", mode: str = "lexical", model_name: Optional[str] = None) -> int:
        """
        Unified estimation entry point.
        :param text: Content string to measure
        :param provider: Model vendor ('generic', 'openai', 'anthropic', 'gemini', 'cursor', 'ollama')
        :param mode: 'lexical' (Level 1) or 'vendor' (Level 2)
        :param model_name: Optional model name string
        """
        if not text:
            return 0

        if mode == "vendor" or provider.lower() in ("openai", "gpt-4", "gpt-3.5"):
            return cls.estimate_vendor(text, provider=provider, model_name=model_name)

        return cls.estimate_lexical(text)

    @classmethod
    def estimate_full_doc(cls, bodies: List[str], provider: str = "generic") -> int:
        """
        Level 3 (Analytics): Measure concatenated active node bodies.
        """
        if not bodies:
            return 0
        concatenated = "\n\n".join(b for b in bodies if b)
        return cls.estimate(concatenated, provider=provider, mode="lexical")
