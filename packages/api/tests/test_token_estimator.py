"""Unit tests for TokenEstimator."""
import pytest
from core.token_estimator import TokenEstimator

def test_token_estimator_lexical():
    # Empty string
    assert TokenEstimator.estimate("") == 0
    assert TokenEstimator.estimate(None) == 0

    # English text
    en_text = "Hello world, this is a test for token estimation."
    en_tokens = TokenEstimator.estimate(en_text, mode="lexical")
    assert en_tokens > 0

    # CJK text
    zh_text = "MemTrace 知識庫與 Token 估算器單元測試"
    zh_tokens = TokenEstimator.estimate(zh_text, mode="lexical")
    assert zh_tokens > 0

def test_token_estimator_vendor():
    text = "Testing OpenAI vendor token estimation."
    vendor_tokens = TokenEstimator.estimate(text, provider="openai", mode="vendor")
    assert vendor_tokens > 0

def test_token_estimator_full_doc():
    bodies = [
        "First node content in Chinese 知識庫",
        "Second node content describing architecture."
    ]
    total_tokens = TokenEstimator.estimate_full_doc(bodies)
    assert total_tokens > 0
