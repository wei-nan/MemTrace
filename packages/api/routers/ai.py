"""
AI router — user-facing endpoints for:
  - Managing personal API keys (CRUD)
  - Querying free-tier credit usage
  - Invoking AI features (extraction, embedding, restructure)
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.ai import (
    AIProviderError,
    AIProviderUnavailable,
    AIQuotaExceeded,
    PROVIDER_REGISTRY,
    Feature,
    chat_completion,
    embed,
    encrypt_api_key,
    record_usage,
    resolve_provider,
    FREE_TOKEN_LIMIT,
    EXTRACTION_SYSTEM,
    RESTRUCTURE_SYSTEM,
    strip_fences,
)
from core.database import db_cursor
from core.deps import get_current_user
from core.security import generate_id

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

# ── Pydantic models ────────────────────────────────────────────────────────────

class AIKeyCreate(BaseModel):
    provider: str = Field(description="Provider identifier, must exist in PROVIDER_REGISTRY")
    api_key:  str = Field(min_length=10, max_length=200)

    def validate_provider(self) -> None:
        if self.provider not in PROVIDER_REGISTRY:
            known = ", ".join(PROVIDER_REGISTRY.keys())
            raise ValueError(f"Unknown provider '{self.provider}'. Known: {known}")


class AIKeyResponse(BaseModel):
    id:           str
    provider:     str
    key_hint:     str
    created_at:   datetime
    last_used_at: Optional[datetime]


class CreditStatusResponse(BaseModel):
    free_limit:     int
    free_used:      int
    free_remaining: int
    has_own_key:    dict[str, bool]   # {"openai": True, "anthropic": False, "gemini": False}


class ExtractionRequest(BaseModel):
    segment:       str = Field(min_length=10, max_length=8000)
    workspace_id:  str
    kb_type:       Literal["evergreen", "ephemeral"] = "evergreen"
    existing_titles: list[str] = Field(default_factory=list, max_length=100)
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None


class ExtractedNode(BaseModel):
    title_zh:        str
    title_en:        str
    content_type:    str
    body_zh:         str
    body_en:         str
    tags:            list[str]
    suggested_edges: list[dict]   # [{to_index: int, relation: str}]


class ExtractionResponse(BaseModel):
    nodes:       list[ExtractedNode]
    tokens_used: int
    source:      str   # "user_key" | "managed"


class EmbedRequest(BaseModel):
    text:        str = Field(min_length=1, max_length=4000)
    workspace_id: str
    node_id:     Optional[str] = None
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None


class EmbedResponse(BaseModel):
    vector:      list[float]
    tokens_used: int
    source:      str


class RestructureRequest(BaseModel):
    node_ids:    list[str] = Field(min_length=1, max_length=20)
    workspace_id: str
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None


class ProposedChange(BaseModel):
    operation:       str
    target_node_ids: list[str]
    reason:          str
    proposed:        dict


class RestructureResponse(BaseModel):
    changes:     list[ProposedChange]
    tokens_used: int
    source:      str

class ChatRequest(BaseModel):
    workspace_id: str
    message: str
    history: Optional[list[dict]] = None
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    proposals: list[ProposedChange]
    source_nodes: list[dict]
    tokens_used: int
    source: str


# ── API Key management ─────────────────────────────────────────────────────────

@router.get("/keys", response_model=list[AIKeyResponse])
def list_ai_keys(user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, provider, key_hint, created_at, last_used_at "
            "FROM user_ai_keys WHERE user_id = %s ORDER BY created_at DESC",
            (user["sub"],),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]


@router.post("/keys", response_model=AIKeyResponse, status_code=201)
def create_ai_key(body: AIKeyCreate, user: dict = Depends(get_current_user)):
    try:
        body.validate_provider()
        key_hint = body.api_key[-4:]
        key_enc  = encrypt_api_key(body.api_key)
        key_id   = generate_id("uak")

        with db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO user_ai_keys (id, user_id, provider, key_enc, key_hint)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, provider) DO UPDATE
                  SET key_enc = EXCLUDED.key_enc,
                      key_hint = EXCLUDED.key_hint,
                      last_used_at = NULL
                RETURNING id, provider, key_hint, created_at, last_used_at
                """,
                (key_id, user["sub"], body.provider, key_enc, key_hint),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=500, detail="Failed to save key")
            return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/keys/{provider}", status_code=204)
def delete_ai_key(
    provider: str,
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM user_ai_keys WHERE user_id = %s AND provider = %s",
            (user["sub"], provider),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="No key found for this provider")

@router.get("/models/{provider}")
async def list_models(
    provider: str,
    user: dict = Depends(get_current_user),
):
    try:
        resolved = resolve_provider(user["sub"], "extraction", provider)
        return await resolved.provider.list_models(resolved.api_key)
    except Exception as e:
        # Fallback to static list if resolve fails (e.g. no key configured)
        impl = PROVIDER_REGISTRY.get(provider)
        if impl:
            return impl.get_known_models()
        raise HTTPException(status_code=400, detail=str(e))


# ── Credit status ──────────────────────────────────────────────────────────────

@router.get("/credits", response_model=CreditStatusResponse)
def get_credit_status(user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            "SELECT ai_free_tokens_remaining(%s, %s) AS remaining",
            (user["sub"], FREE_TOKEN_LIMIT),
        )
        remaining = cur.fetchone()["remaining"]

        cur.execute(
            "SELECT provider FROM user_ai_keys WHERE user_id = %s",
            (user["sub"],),
        )
        own_keys = {row["provider"] for row in cur.fetchall()}

    return CreditStatusResponse(
        free_limit=FREE_TOKEN_LIMIT,
        free_used=FREE_TOKEN_LIMIT - remaining,
        free_remaining=remaining,
        has_own_key={
            "openai":    "openai"    in own_keys,
            "anthropic": "anthropic" in own_keys,
            "gemini":    "gemini"    in own_keys,
        },
    )


# ── AI Feature: Extraction ─────────────────────────────────────────────────────

@router.post("/extract", response_model=ExtractionResponse)
async def extract_nodes(
    body: ExtractionRequest,
    user: dict = Depends(get_current_user),
):
    try:
        resolved = resolve_provider(user["sub"], "extraction", body.preferred_provider, body.preferred_model)
    except AIQuotaExceeded as e:
        raise HTTPException(status_code=402, detail=str(e))
    except AIProviderUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))

    existing_hint = (
        f"\nExisting node titles in this workspace (avoid duplication):\n"
        + "\n".join(f"- {t}" for t in body.existing_titles[:50])
        if body.existing_titles else ""
    )

    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Workspace type: {body.kb_type}{existing_hint}\n\n"
                f"---\n{body.segment}\n---\n\n"
                "Extract Memory Nodes from the segment above."
            ),
        },
    ]

    try:
        raw, tokens = await chat_completion(resolved, messages, max_tokens=4096)
    except AIProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

    try:
        nodes_data = json.loads(strip_fences(raw))
        if not isinstance(nodes_data, list):
            raise ValueError("Expected JSON array")
        nodes = [ExtractedNode(**n) for n in nodes_data]
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="AI returned malformed JSON. Please retry or adjust the segment.",
        )

    record_usage(resolved, "extraction", tokens, body.workspace_id)

    return ExtractionResponse(nodes=nodes, tokens_used=tokens, source=resolved.source)


# ── AI Feature: Embedding ──────────────────────────────────────────────────────

@router.post("/embed", response_model=EmbedResponse)
async def embed_text(
    body: EmbedRequest,
    user: dict = Depends(get_current_user),
):
    try:
        resolved = resolve_provider(user["sub"], "embedding", body.preferred_provider, body.preferred_model)
    except AIQuotaExceeded as e:
        raise HTTPException(status_code=402, detail=str(e))
    except AIProviderUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))

    try:
        vector, tokens = await embed(resolved, body.text)
    except AIProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

    record_usage(resolved, "embedding", tokens, body.workspace_id, body.node_id)

    return EmbedResponse(vector=vector, tokens_used=tokens, source=resolved.source)


# ── AI Feature: Restructure ────────────────────────────────────────────────────

@router.post("/restructure", response_model=RestructureResponse)
async def restructure_nodes(
    body: RestructureRequest,
    user: dict = Depends(get_current_user),
):
    if len(body.node_ids) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 nodes per restructure request")

    try:
        resolved = resolve_provider(user["sub"], "restructure", body.preferred_provider, body.preferred_model)
    except AIQuotaExceeded as e:
        raise HTTPException(status_code=402, detail=str(e))
    except AIProviderUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Fetch node data
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, title_zh, title_en, content_type, body_zh, body_en, tags
            FROM memory_nodes
            WHERE id = ANY(%s) AND workspace_id = %s
            """,
            (body.node_ids, body.workspace_id),
        )
        nodes = cur.fetchall()

    if not nodes:
        raise HTTPException(status_code=404, detail="No nodes found in this workspace")

    node_payload = json.dumps([dict(n) for n in nodes], ensure_ascii=False, indent=2)

    messages = [
        {"role": "system", "content": RESTRUCTURE_SYSTEM},
        {
            "role": "user",
            "content": f"Analyse these Memory Nodes and propose improvements:\n\n{node_payload}",
        },
    ]

    try:
        raw, tokens = await chat_completion(resolved, messages, max_tokens=4096)
    except AIProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

    try:
        changes_data = json.loads(strip_fences(raw))
        changes = [ProposedChange(**c) for c in changes_data]
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="AI returned malformed JSON. Please retry.",
        )

    record_usage(resolved, "restructure", tokens, body.workspace_id)

    return RestructureResponse(changes=changes, tokens_used=tokens, source=resolved.source)


@router.post("/chat", response_model=ChatResponse)
async def chat_with_kb(
    body: ChatRequest,
    user: dict = Depends(get_current_user),
):
    try:
        from core.ai import CHAT_SYSTEM
        resolved = resolve_provider(user["sub"], "extraction", body.preferred_provider, body.preferred_model)
        embed_prov = resolve_provider(user["sub"], "embedding", body.preferred_provider, body.preferred_model)
        vector, _ = await embed(embed_prov, body.message)
        
        with db_cursor() as cur:
            cur.execute("SELECT target_ws_id FROM workspace_associations WHERE source_ws_id = %s", (body.workspace_id,))
            target_ids = [body.workspace_id] + [r["target_ws_id"] for r in cur.fetchall()]
            
            cur.execute("""
                SELECT id, title_zh, title_en, body_zh, body_en, workspace_id,
                       (1 - (embedding <=> %s::vector)) AS similarity
                FROM memory_nodes
                WHERE workspace_id = ANY(%s) AND embedding IS NOT NULL AND status = 'active'
                ORDER BY similarity DESC LIMIT 10
            """, (vector, target_ids))
            source_nodes = cur.fetchall()

        context_str = json.dumps([dict(n) for n in source_nodes], ensure_ascii=False, indent=2)
        messages = [{"role": "system", "content": CHAT_SYSTEM}]
        if body.history: messages.extend(body.history)
        messages.append({"role": "user", "content": f"CONTEXT NODES:\n{context_str}\n\nUSER MESSAGE: {body.message}"})

        raw, tokens = await chat_completion(resolved, messages)
        proposals = []
        answer = raw
        if "```json" in raw:
            parts = raw.split("```json")
            answer = parts[0].strip()
            json_part = parts[1].split("```")[0].strip()
            try:
                proposals = [ProposedChange(**p) for p in json.loads(json_part)]
            except: pass
        
        record_usage(resolved, "extraction", tokens, body.workspace_id)
        return ChatResponse(
            answer=answer, proposals=proposals,
            source_nodes=[dict(n) for n in source_nodes],
            tokens_used=tokens, source=resolved.source
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
