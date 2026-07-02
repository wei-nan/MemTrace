"""
Voice (STT/TTS) provider abstraction layer.

Mirrors core/ai.py's provider pattern, but STT and TTS are resolved and
selected independently per spec mem_bede56ef (V6): a user has at most one
active STT key and one active TTS key (user_voice_keys, UNIQUE(user_id, purpose)),
and the two need not be the same provider.

─── Adding a new provider ────────────────────────────────────────────────────
1. Subclass VoiceProvider.
2. Implement speech_to_text() and/or text_to_speech() (raise
   AIProviderError NotImplemented for the unsupported side).
3. Register the instance in VOICE_PROVIDER_REGISTRY at the bottom of this file.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional

import httpx
from jose import jwt as jose_jwt

from core.ai import AIProviderError, AIProviderUnavailable
from core.credentials import decrypt_secret, encrypt_secret
from core.database import db_cursor, is_postgres

Purpose = Literal["stt", "tts"]

# ── Provider Protocol ─────────────────────────────────────────────────────────

class VoiceProvider(ABC):
    """Base class for all voice (STT/TTS) providers."""

    #: Identifier stored in the database (e.g. "gcp"). Must be unique.
    name: str

    async def speech_to_text(
        self,
        resolved: "ResolvedVoiceProvider",
        audio_bytes: bytes,
        mime_type: str,
        language: str,
    ) -> str:
        """Transcribe audio to text. Returns the transcript."""
        raise AIProviderError(f"Provider '{self.name}' does not support speech-to-text.")

    async def text_to_speech(
        self,
        resolved: "ResolvedVoiceProvider",
        text: str,
        language: str,
    ) -> tuple[bytes, str]:
        """Synthesize speech from text. Returns (audio_bytes, mime_type)."""
        raise AIProviderError(f"Provider '{self.name}' does not support text-to-speech.")


# ── Built-in: OpenAI (STT: whisper-1, TTS: tts-1) ─────────────────────────────

class OpenAIVoiceProvider(VoiceProvider):
    name = "openai"

    async def speech_to_text(self, resolved, audio_bytes, mime_type, language):
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {resolved.credential}"},
                data={"model": "whisper-1", "language": language.split("-")[0]},
                files={"file": ("audio", audio_bytes, mime_type)},
            )
        if not resp.is_success:
            raise AIProviderError(f"OpenAI STT {resp.status_code}: {resp.text[:400]}")
        return resp.json()["text"]

    async def text_to_speech(self, resolved, text, language):
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {resolved.credential}"},
                json={"model": "tts-1", "voice": "alloy", "input": text},
            )
        if not resp.is_success:
            raise AIProviderError(f"OpenAI TTS {resp.status_code}: {resp.text[:400]}")
        return resp.content, "audio/mpeg"


# ── Built-in: GCP (STT: Cloud Speech-to-Text, TTS: Cloud Text-to-Speech) ──────

# In-memory cache of short-lived Bearer tokens exchanged from Service Account
# JSON. Token caching strategy proper (invalidation, per-worker sharing) is
# deferred — see spec mem_bede56ef V7. This is just enough to avoid a token
# exchange on literally every request within the same process.
_gcp_token_cache: dict[str, tuple[str, float]] = {}


async def _gcp_bearer_token(credential: str, credential_type: str, scope: str) -> str:
    if credential_type == "api_key":
        return credential  # used as a query param, not a header — handled by caller

    cache_key = f"{scope}:{credential[:64]}"
    cached = _gcp_token_cache.get(cache_key)
    if cached and cached[1] > time.time() + 30:
        return cached[0]

    account = json.loads(credential)
    now = int(time.time())
    claims = {
        "iss": account["client_email"],
        "scope": scope,
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }
    assertion = jose_jwt.encode(claims, account["private_key"], algorithm="RS256")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
        )
    if not resp.is_success:
        raise AIProviderError(f"GCP token exchange {resp.status_code}: {resp.text[:400]}")
    data = resp.json()
    token = data["access_token"]
    _gcp_token_cache[cache_key] = (token, time.time() + data.get("expires_in", 3600))
    return token


def _raise_gcp_error(label: str, resp: httpx.Response) -> None:
    try:
        reason = resp.json().get("error", {}).get("details", [{}])[0].get("reason", "")
    except Exception:
        reason = ""
    if reason == "API_KEY_HTTP_REFERRER_BLOCKED":
        raise AIProviderError(
            "Google API 金鑰設定了「HTTP 來源限制」，但 MemTrace 是從伺服器呼叫，"
            "沒有瀏覽器來源，因此被 Google 封鎖。\n"
            "請至 GCP Console → API 和服務 → 憑證，找到此金鑰，"
            "將「應用程式限制」改為「無」或改用「IP 位址」限制後儲存。"
        )
    raise AIProviderError(f"GCP {label} {resp.status_code}: {resp.text[:400]}")


class GCPVoiceProvider(VoiceProvider):
    name = "gcp"

    async def speech_to_text(self, resolved, audio_bytes, mime_type, language):
        import base64

        body = {
            "config": {
                "languageCode": language,
                "enableAutomaticPunctuation": True,
            },
            "audio": {"content": base64.b64encode(audio_bytes).decode()},
        }
        url = "https://speech.googleapis.com/v1/speech:recognize"
        headers = {}
        if resolved.credential_type == "service_account_json":
            token = await _gcp_bearer_token(
                resolved.credential, resolved.credential_type,
                "https://www.googleapis.com/auth/cloud-platform",
            )
            headers["Authorization"] = f"Bearer {token}"
        else:
            url += f"?key={resolved.credential}"

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=body)
        if not resp.is_success:
            _raise_gcp_error("STT", resp)
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return ""
        return " ".join(r["alternatives"][0]["transcript"] for r in results)

    async def text_to_speech(self, resolved, text, language):
        body = {
            "input": {"text": text},
            "voice": {"languageCode": language},
            "audioConfig": {"audioEncoding": "MP3"},
        }
        url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        headers = {}
        if resolved.credential_type == "service_account_json":
            token = await _gcp_bearer_token(
                resolved.credential, resolved.credential_type,
                "https://www.googleapis.com/auth/cloud-platform",
            )
            headers["Authorization"] = f"Bearer {token}"
        else:
            url += f"?key={resolved.credential}"

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=body)
        if not resp.is_success:
            _raise_gcp_error("TTS", resp)
        import base64
        audio_content = resp.json()["audioContent"]
        return base64.b64decode(audio_content), "audio/mpeg"


# ── Built-in: Azure AI Speech ──────────────────────────────────────────────────

class AzureVoiceProvider(VoiceProvider):
    name = "azure"

    # Azure Speech is region-scoped; the subscription key encodes region as
    # "<region>:<key>" since user_voice_keys has no separate region column.
    def _split(self, credential: str) -> tuple[str, str]:
        region, _, key = credential.partition(":")
        if not key:
            raise AIProviderError("Azure voice key must be formatted as '<region>:<subscription_key>'.")
        return region, key

    async def speech_to_text(self, resolved, audio_bytes, mime_type, language):
        region, key = self._split(resolved.credential)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"
                f"?language={language}",
                headers={
                    "Ocp-Apim-Subscription-Key": key,
                    "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
                },
                content=audio_bytes,
            )
        if not resp.is_success:
            raise AIProviderError(f"Azure STT {resp.status_code}: {resp.text[:400]}")
        return resp.json().get("DisplayText", "")

    async def text_to_speech(self, resolved, text, language):
        region, key = self._split(resolved.credential)
        ssml = (
            f"<speak version='1.0' xml:lang='{language}'>"
            f"<voice xml:lang='{language}'>{text}</voice></speak>"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
                headers={
                    "Ocp-Apim-Subscription-Key": key,
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
                },
                content=ssml.encode(),
            )
        if not resp.is_success:
            raise AIProviderError(f"Azure TTS {resp.status_code}: {resp.text[:400]}")
        return resp.content, "audio/mpeg"


# ── Built-in: Deepgram (STT only) ─────────────────────────────────────────────

class DeepgramVoiceProvider(VoiceProvider):
    name = "deepgram"

    async def speech_to_text(self, resolved, audio_bytes, mime_type, language):
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"https://api.deepgram.com/v1/listen?language={language}",
                headers={
                    "Authorization": f"Token {resolved.credential}",
                    "Content-Type": mime_type,
                },
                content=audio_bytes,
            )
        if not resp.is_success:
            raise AIProviderError(f"Deepgram STT {resp.status_code}: {resp.text[:400]}")
        data = resp.json()
        return data["results"]["channels"][0]["alternatives"][0]["transcript"]


# ── Built-in: ElevenLabs (TTS only) ───────────────────────────────────────────

class ElevenLabsVoiceProvider(VoiceProvider):
    name = "elevenlabs"

    _DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # "Rachel", public default voice

    async def text_to_speech(self, resolved, text, language):
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{self._DEFAULT_VOICE_ID}",
                headers={"xi-api-key": resolved.credential},
                json={"text": text, "model_id": "eleven_multilingual_v2"},
            )
        if not resp.is_success:
            raise AIProviderError(f"ElevenLabs TTS {resp.status_code}: {resp.text[:400]}")
        return resp.content, "audio/mpeg"


# ── Provider Registry ─────────────────────────────────────────────────────────

VOICE_PROVIDER_REGISTRY: dict[str, VoiceProvider] = {
    "openai":     OpenAIVoiceProvider(),
    "gcp":        GCPVoiceProvider(),
    "azure":      AzureVoiceProvider(),
    "deepgram":   DeepgramVoiceProvider(),
    "elevenlabs": ElevenLabsVoiceProvider(),
}

# ── Encryption ────────────────────────────────────────────────────────────────

def encrypt_voice_credential(raw: str) -> str:
    return encrypt_secret(raw)

def decrypt_voice_credential(enc: str) -> str:
    return decrypt_secret(enc)

# ── Resolution ────────────────────────────────────────────────────────────────

@dataclass
class ResolvedVoiceProvider:
    provider:        VoiceProvider
    credential:      str
    credential_type: Literal["api_key", "service_account_json"]
    user_id:         str


def resolve_voice_provider(user_id: str, purpose: Purpose) -> ResolvedVoiceProvider:
    """Look up the user's single active key for this purpose (stt or tts)."""
    with db_cursor() as cur:
        placeholder = "%s" if is_postgres() else "?"
        cur.execute(
            f"SELECT provider, credential_type, key_enc FROM user_voice_keys "
            f"WHERE user_id = {placeholder} AND purpose = {placeholder}",
            (user_id, purpose),
        )
        row = cur.fetchone()

    if not row:
        raise AIProviderUnavailable(
            f"No {purpose.upper()} voice provider is configured for this account. "
            "Add a voice key in Settings — Voice."
        )

    impl = VOICE_PROVIDER_REGISTRY.get(row["provider"])
    if not impl:
        raise AIProviderUnavailable(f"Unknown voice provider '{row['provider']}'.")

    try:
        credential = decrypt_voice_credential(row["key_enc"])
    except ValueError as exc:
        raise AIProviderUnavailable(str(exc))

    return ResolvedVoiceProvider(
        provider=impl,
        credential=credential,
        credential_type=row["credential_type"],
        user_id=user_id,
    )
