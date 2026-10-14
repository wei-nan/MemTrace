"""
TokenEstimator: Unified 3-level Token Measurement Module for MemTrace.

Level 1 (Lexical): CJK and Unicode-aware character & word heuristic estimation (zero dependencies).
Level 2 (Vendor Calibration): Vendor-specific tokenizers (tiktoken for OpenAI, fallback to Lexical).
Level 3 (Analytics): Standardized token usage calculations for analytics reports.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FutureTimeoutError
from typing import Optional, List

logger = logging.getLogger(__name__)

# tiktoken.get_encoding() downloads the BPE file over the network on first use
# and has no built-in timeout, so a slow/unreachable host can block the caller
# indefinitely. Load it in a worker thread with a hard timeout so a stalled
# download degrades to the lexical fallback instead of hanging the process
# (this previously stalled the asyncio event loop during app startup when the
# decay job ran before the encoding was cached).
_TIKTOKEN_ENCODER = None
try:
    import tiktoken
    _pool = ThreadPoolExecutor(max_workers=1)
    try:
        _TIKTOKEN_ENCODER = _pool.submit(tiktoken.get_encoding, "cl100k_base").result(timeout=5)
    finally:
        # wait=False: a stalled download's thread is abandoned rather than
        # blocked on, since ThreadPoolExecutor has no way to cancel it.
        _pool.shutdown(wait=False)
except _FutureTimeoutError:
    _TIKTOKEN_ENCODER = None
    logger.warning(
        "tiktoken encoding download timed out; TokenEstimator will fall back "
        "to the lexical heuristic for vendor-mode estimates."
    )
except Exception as e:
    _TIKTOKEN_ENCODER = None
    logger.warning(
        f"tiktoken unavailable ({e}); TokenEstimator will fall back to the "
        "lexical heuristic for vendor-mode estimates."
    )


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
                    logger.warning(
                        f"tiktoken encoding failed ({e}); falling back to lexical estimate."
                    )

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
