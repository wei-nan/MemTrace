"""
Voice router — user-facing endpoints for:
  - Managing personal voice (STT/TTS) credentials (CRUD)
  - Proxying speech-to-text and text-to-speech calls

See spec mem_bede56ef: voice is a personal, opt-in modality wrapper around the
existing /ai/chat-stream path. The backend always proxies the call — the
frontend never holds or calls third-party voice credentials directly.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core.ai import AIProviderError, AIProviderUnavailable, chat_completion, resolve_provider
from core.database import db_cursor
from core.deps import get_current_user
from core.security import decode_token
from core.voice import VOICE_PROVIDER_REGISTRY, resolve_voice_provider

logger = logging.getLogger(__name__)

from services.voice_config import (
    list_user_voice_keys,
    upsert_user_voice_key,
    delete_user_voice_key,
)

router = APIRouter(prefix="/api/v1/ai", tags=["voice"])

# -- Pydantic models ------------------------------------------------------------

class VoiceKeyCreate(BaseModel):
    purpose: str = Field(description="'stt' or 'tts'")
    provider: str = Field(description="Provider identifier, must exist in VOICE_PROVIDER_REGISTRY")
    credential: str = Field(description="API key string, or raw Service Account JSON for GCP")
    credential_type: str = "api_key"

    def validate_fields(self) -> None:
        if self.purpose not in ("stt", "tts"):
            raise ValueError("purpose must be 'stt' or 'tts'")
        if self.provider not in VOICE_PROVIDER_REGISTRY:
            known = ", ".join(VOICE_PROVIDER_REGISTRY.keys())
            raise ValueError(f"Unknown voice provider '{self.provider}'. Known: {known}")
        if self.credential_type not in ("api_key", "service_account_json"):
            raise ValueError("credential_type must be 'api_key' or 'service_account_json'")


class VoiceKeyResponse(BaseModel):
    id: str
    purpose: str
    provider: str
    credential_type: str
    key_hint: str
    created_at: datetime
    last_used_at: Optional[datetime]


class TextToSpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: str = "en-US"
    voice: Optional[str] = None


class SpeechSummaryRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    language: str = "en-US"
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None


# Spec mem_bede56ef / mem_77b74b8a (D7): the assistant's on-screen reply may
# contain code and markdown. Reading it verbatim through TTS is jarring, so
# before synthesizing speech we condense it into a spoken-friendly summary.
_SPOKEN_SUMMARY_SYSTEM = """\
You rewrite an assistant's chat reply into a short summary meant to be READ ALOUD by a text-to-speech engine.

Rules:
- Write in the language identified by the BCP-47 tag given in the user message (e.g. zh-TW → Traditional Chinese, en-US → English).
- Keep it concise: at most 2-3 sentences capturing the main point or conclusion.
- Do NOT include code, commands, file paths, URLs, markdown symbols, tables, or bullet lists — none of these read well aloud.
- If the reply contains code or a code-heavy answer, don't read it; instead say something like the code is shown on screen.
- Sound natural and conversational, as if spoken. Output only the spoken text, nothing else."""


# -- Voice key management ---------------------------------------------------------

@router.get("/voice-keys", response_model=list[VoiceKeyResponse])
def list_voice_keys(user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        return list_user_voice_keys(cur, user["sub"])


@router.post("/voice-keys", response_model=VoiceKeyResponse, status_code=201)
def create_voice_key(body: VoiceKeyCreate, user: dict = Depends(get_current_user)):
    try:
        body.validate_fields()
        with db_cursor(commit=True) as cur:
            return upsert_user_voice_key(
                cur,
                user["sub"],
                body.purpose,
                body.provider,
                body.credential,
                body.credential_type,
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/voice-keys/{purpose}", status_code=204)
def delete_voice_key(purpose: str, user: dict = Depends(get_current_user)):
    with db_cursor(commit=True) as cur:
        if not delete_user_voice_key(cur, user["sub"], purpose):
            raise HTTPException(status_code=404, detail="No voice key found for this purpose")


# -- Speech proxy endpoints ---------------------------------------------------------

@router.post("/speech/stt")
async def speech_to_text(
    file: UploadFile = File(...),
    language: str = "en-US",
    user: dict = Depends(get_current_user),
):
    try:
        resolved = resolve_voice_provider(user["sub"], "stt")
    except AIProviderUnavailable as e:
        raise HTTPException(status_code=400, detail=str(e))

    audio_bytes = await file.read()
    try:
        transcript = await resolved.provider.speech_to_text(
            resolved, audio_bytes, file.content_type or "audio/webm", language,
        )
    except AIProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE user_voice_keys SET last_used_at = now() WHERE user_id = %s AND purpose = 'stt'",
            (user["sub"],),
        )
    return {"transcript": transcript}


@router.post("/speech/tts")
async def text_to_speech(body: TextToSpeechRequest, user: dict = Depends(get_current_user)):
    try:
        resolved = resolve_voice_provider(user["sub"], "tts")
    except AIProviderUnavailable as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        audio_bytes, mime_type = await resolved.provider.text_to_speech(
            resolved, body.text, body.language, body.voice,
        )
    except AIProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE user_voice_keys SET last_used_at = now() WHERE user_id = %s AND purpose = 'tts'",
            (user["sub"],),
        )
    return Response(content=audio_bytes, media_type=mime_type)


@router.get("/speech/voices")
async def list_tts_voices(language: str = "en-US", user: dict = Depends(get_current_user)):
    """List selectable TTS voices for the user's provider (empty if unsupported)."""
    try:
        resolved = resolve_voice_provider(user["sub"], "tts")
    except AIProviderUnavailable as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not getattr(resolved.provider, "supports_voice_listing", False):
        return {"provider": resolved.provider.name, "voices": []}

    try:
        voices = await resolved.provider.list_voices(resolved, language)
    except AIProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"provider": resolved.provider.name, "voices": voices}


@router.post("/speech/tts-summary")
async def tts_summary(body: SpeechSummaryRequest, user: dict = Depends(get_current_user)):
    """Condense an assistant reply into a spoken-friendly summary for TTS (D7).

    Falls back to the original text on any provider error so voice mode never
    breaks just because summarization was unavailable.
    """
    try:
        resolved = resolve_provider(
            user["sub"], "extraction", body.preferred_provider, body.preferred_model
        )
    except AIProviderUnavailable:
        return {"summary": body.text, "summarized": False}

    messages = [
        {"role": "system", "content": _SPOKEN_SUMMARY_SYSTEM},
        {"role": "user", "content": f"Target language: {body.language}\n\nAssistant reply:\n{body.text}"},
    ]
    try:
        # Generous cap: "thinking" models (e.g. Gemini 2.5) spend output budget on
        # reasoning, so a tight limit truncates the actual summary mid-sentence.
        summary, _ = await chat_completion(resolved, messages, max_tokens=2048, temperature=0.3)
    except AIProviderError:
        return {"summary": body.text, "summarized": False}

    summary = summary.strip()
    if not summary:
        return {"summary": body.text, "summarized": False}
    return {"summary": summary, "summarized": True}


# -- Streaming STT (WebSocket) ---------------------------------------------------
#
# Spec mem_77b74b8a (D6): live, interim-result transcription. The browser can't
# set an Authorization header on a WS handshake, so the JWT is passed as a query
# param. We authenticate, resolve the user's STT provider, and — if it supports
# streaming (currently Deepgram) — relay raw PCM16 frames up to the provider and
# interim/final transcripts back down. Batch STT (/speech/stt) is untouched.

async def _authenticate_ws(token: str) -> Optional[str]:
    """Resolve a user id from a query-param JWT, or None if invalid."""
    if not token:
        return None
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        return None
    jti = payload.get("jti")
    if jti:
        with db_cursor() as cur:
            cur.execute("SELECT 1 FROM session_blocklist WHERE jti = %s", (jti,))
            if cur.fetchone():
                return None
    return payload["sub"]


@router.websocket("/speech/stt-stream")
async def speech_to_text_stream(
    ws: WebSocket,
    token: str = "",
    language: str = "en-US",
    sample_rate: int = 16000,
):
    import websockets

    user_id = await _authenticate_ws(token)
    if not user_id:
        await ws.close(code=4401)  # unauthorized
        return

    try:
        resolved = resolve_voice_provider(user_id, "stt")
    except AIProviderUnavailable as e:
        await ws.accept()
        await ws.send_json({"type": "error", "detail": str(e)})
        await ws.close(code=4400)
        return

    if not getattr(resolved.provider, "supports_stt_streaming", False):
        await ws.accept()
        await ws.send_json({
            "type": "error",
            "detail": f"Provider '{resolved.provider.name}' does not support streaming. "
                      "Switch STT to Deepgram, or use the standard mic.",
        })
        await ws.close(code=4400)
        return

    # Clamp to a sane audio sample-rate range before trusting the client value.
    sample_rate = sample_rate if 8000 <= sample_rate <= 48000 else 16000
    dg_url, dg_headers = resolved.provider.stream_stt_endpoint(resolved, language, sample_rate)

    await ws.accept()
    try:
        async with websockets.connect(dg_url, additional_headers=dg_headers, max_size=None) as upstream:

            async def pump_client_to_upstream():
                while True:
                    msg = await ws.receive()
                    if msg["type"] == "websocket.disconnect":
                        break
                    data = msg.get("bytes")
                    if data is not None:
                        await upstream.send(data)
                        continue
                    text = msg.get("text")
                    if text and "stop" in text:
                        # Flush: tell Deepgram to finalize and drain remaining audio.
                        await upstream.send(json.dumps({"type": "CloseStream"}))

            async def pump_upstream_to_client():
                async for raw in upstream:
                    try:
                        payload = json.loads(raw)
                    except (ValueError, TypeError):
                        continue
                    if payload.get("type") != "Results":
                        continue
                    alt = (payload.get("channel", {}).get("alternatives") or [{}])[0]
                    transcript = alt.get("transcript", "")
                    if transcript:
                        await ws.send_json({
                            "type": "transcript",
                            "transcript": transcript,
                            "is_final": bool(payload.get("is_final")),
                        })

            up = asyncio.create_task(pump_client_to_upstream())
            down = asyncio.create_task(pump_upstream_to_client())
            done, pending = await asyncio.wait({up, down}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            # Surface any exception from the finished task(s).
            for task in done:
                exc = task.exception()
                if exc:
                    raise exc
    except WebSocketDisconnect:
        pass
    except Exception as e:  # upstream/auth/transport failure — report once, then close
        logger.warning("STT stream error for user %s: %s", user_id, e)
        try:
            await ws.send_json({"type": "error", "detail": f"STT stream error: {e}"})
        except Exception:
            pass
    finally:
        try:
            with db_cursor(commit=True) as cur:
                cur.execute(
                    "UPDATE user_voice_keys SET last_used_at = now() WHERE user_id = %s AND purpose = 'stt'",
                    (user_id,),
                )
        except Exception:
            pass
        try:
            await ws.close()
        except Exception:
            pass
