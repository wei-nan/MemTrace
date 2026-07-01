"""
Voice router — user-facing endpoints for:
  - Managing personal voice (STT/TTS) credentials (CRUD)
  - Proxying speech-to-text and text-to-speech calls

See spec mem_bede56ef: voice is a personal, opt-in modality wrapper around the
existing /ai/chat-stream path. The backend always proxies the call — the
frontend never holds or calls third-party voice credentials directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core.ai import AIProviderError, AIProviderUnavailable
from core.database import db_cursor
from core.deps import get_current_user
from core.voice import VOICE_PROVIDER_REGISTRY, resolve_voice_provider

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
            resolved, body.text, body.language,
        )
    except AIProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE user_voice_keys SET last_used_at = now() WHERE user_id = %s AND purpose = 'tts'",
            (user["sub"],),
        )
    return Response(content=audio_bytes, media_type=mime_type)
