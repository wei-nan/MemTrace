"""
AI router - user-facing endpoints for:
  - Managing personal API keys (CRUD)
  - Querying free-tier credit usage
  - Invoking AI features (extraction, embedding, restructure)
"""

from __future__ import annotations

from datetime import datetime
import json
import logging
from typing import Literal, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from core.ai import (
    AIProviderError,
    AIProviderUnavailable,
    PROVIDER_REGISTRY,
    Feature,
    chat_completion,
    embed,
    encrypt_api_key,
    record_usage,
    resolve_provider,
    RESTRUCTURE_SYSTEM,
    strip_fences,
)
from core.config import settings
from core.database import db_cursor
from core.deps import get_current_user
from core.security import generate_id
from core.constants import FAQ_CACHE_HIT, CONTRADICTION_CHECK

from services.search import extract_search_terms, hybrid_retrieval_for_chat
from services.review import parse_ai_proposals, apply_ai_proposals_to_db
from services.ai_config import list_user_ai_keys, upsert_user_ai_key, delete_user_ai_key

import re as _re

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

# -- Pydantic models ------------------------------------------------------------

class AIKeyCreate(BaseModel):
    provider: str = Field(description="Provider identifier, must exist in PROVIDER_REGISTRY")
    api_key:  Optional[str] = Field(None, max_length=200)
    base_url: Optional[str] = None
    auth_mode: Optional[str] = "none"
    auth_token: Optional[str] = None
    default_chat_model: Optional[str] = None
    default_embedding_model: Optional[str] = None

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
    has_own_key:    dict[str, bool]   # {"openai": True, "anthropic": False, "gemini": False, "ollama": True}


class ExtractionRequest(BaseModel):
    segment:       str = Field(min_length=10, max_length=8000)
    workspace_id:  str
    kb_type:       Literal["evergreen", "ephemeral"] = "evergreen"
    existing_titles: list[str] = Field(default_factory=list, max_length=100)
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    doc_type: Optional[str] = "generic"


class ExtractedNode(BaseModel):
    title:           str
    content_type:    str
    body:            str
    tags:            list[str]
    suggested_edges: list[dict]   # [{to_index: int, relation: str}]


class ExtractionResponse(BaseModel):
    nodes:       list[ExtractedNode]
    tokens_used: int
    source:      str   # "workspace_key" | "account_key"


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
    history: Optional[list[dict]] = None  # deprecated: use session_id instead
    allow_edits: bool = False
    cross_kb_ids: Optional[list[str]] = None
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    force_auto_active: bool = False
    session_id: Optional[str] = None  # Phase 6: server-side session
    want_spoken_summary: bool = False  # voice mode: emit a leading spoken summary (D7 / mem_77b74b8a)

class ChatResponse(BaseModel):
    answer: str
    proposals: list[dict] = []  # Contains review_queue_id if allow_edits=True
    source_nodes: list[dict]
    tokens_used: int
    source: str

class ChatFeedback(BaseModel):
    workspace_id: str
    question_node_id: str
    answer_node_id: str
    is_helpful: bool
    comment: Optional[str] = None


class TestConnectionRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    auth_mode: Optional[str] = "none"
    auth_token: Optional[str] = None
    model: Optional[str] = None  # override default_chat_model for Ollama test


# -- API Key management ---------------------------------------------------------

@router.get("/keys", response_model=list[AIKeyResponse])
def list_ai_keys(user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        return list_user_ai_keys(cur, user["sub"])


@router.post("/keys", response_model=AIKeyResponse, status_code=201)
def create_ai_key(body: AIKeyCreate, user: dict = Depends(get_current_user)):
    try:
        body.validate_provider()
        with db_cursor(commit=True) as cur:
            return upsert_user_ai_key(
                cur, 
                user["sub"], 
                body.provider, 
                body.api_key,
                body.base_url,
                body.auth_mode or "none",
                body.auth_token,
                body.default_chat_model,
                body.default_embedding_model
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/keys/{provider}", status_code=204)
def delete_ai_key(
    provider: str,
    user: dict = Depends(get_current_user),
):
    from services.review_policy import revoke_user_model_bindings
    with db_cursor(commit=True) as cur:
        if not delete_user_ai_key(cur, user["sub"], provider):
            raise HTTPException(status_code=404, detail="No key found for this provider")
        revoke_user_model_bindings(cur, user["sub"], provider)

@router.get("/models/{provider}")
async def list_models(
    provider: str,
    user: dict = Depends(get_current_user),
):
    impl = PROVIDER_REGISTRY.get(provider)
    if not impl:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    try:
        resolved = resolve_provider(user["sub"], "extraction", provider)
    except Exception:
        # No key configured — return known models
        return impl.get_known_models()
    try:
        return await resolved.provider.list_models(resolved)
    except AIProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/providers/{provider}/test-connection")
async def test_provider_connection(
    provider: str,
    body: TestConnectionRequest,
    user: dict = Depends(get_current_user),
):
    from core.ai import ResolvedProvider
    impl = PROVIDER_REGISTRY.get(provider)
    if not impl:
        raise HTTPException(status_code=400, detail=f"Unknown provider {provider}")
    
    # Create a dummy ResolvedProvider for the call
    # Use caller-supplied model if given (important for Ollama where the installed
    # model may differ from the hardcoded default "llama3")
    resolved = ResolvedProvider(
        provider=impl,
        api_key=body.api_key or "",
        model=body.model or impl.default_chat_model,
        source="account_key",
        user_id=user["sub"],
        base_url=body.base_url,
        auth_mode=body.auth_mode,
        auth_token=body.auth_token,
    )
    
    try:
        # Simple chat call to test
        messages = [{"role": "user", "content": "hi"}]
        await impl.chat(resolved, messages, max_tokens=5, temperature=0.0)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/providers/{provider}/models")
async def proxy_list_models(
    provider: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    auth_mode: Optional[str] = "none",
    auth_token: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    from core.ai import ResolvedProvider
    impl = PROVIDER_REGISTRY.get(provider)
    if not impl:
        raise HTTPException(status_code=400, detail=f"Unknown provider {provider}")

    resolved = ResolvedProvider(
        provider=impl,
        api_key=api_key or "",
        model=impl.default_chat_model,
        source="account_key",
        user_id=user["sub"],
        base_url=base_url,
        auth_mode=auth_mode,
        auth_token=auth_token,
    )
    
    try:
        models = await impl.list_models(resolved)
    except AIProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # For Ollama: if the live server returned no embedding models, append the
    # fallback embedding list so users can still pick one (they just need to pull it).
    if provider == "ollama":
        has_embed = any(m.get("model_type") == "embedding" for m in models)
        if not has_embed:
            fallback_embeds = [
                m for m in impl.get_known_models()
                if m.get("model_type") == "embedding"
            ]
            # Tag them so the UI can show "(需安裝)" hint
            for m in fallback_embeds:
                m["needs_install"] = True
                m["display_name"] = m["display_name"] + "（需安裝）"
            models = models + fallback_embeds

    return models


# -- Resolved model preview (for CreateWorkspaceModal) -------------------------

@router.get("/resolved-models")
def get_resolved_model(
    type: str = "embedding",
    user: dict = Depends(get_current_user),
):
    """
    Preview which provider + model will be selected for the given feature.
    Used by the UI to show 'embedding model to be locked' before workspace creation.
    type: 'embedding' | 'chat' | 'extraction'
    """
    from core.ai import resolve_provider, AIProviderUnavailable
    feature_map = {"embedding": "embedding", "chat": "chat", "extraction": "extraction"}
    feature = feature_map.get(type, "embedding")
    try:
        resolved = resolve_provider(user["sub"], feature)
        return {"provider": resolved.provider.name, "model": resolved.model}
    except AIProviderUnavailable:
        return {"provider": None, "model": None}


# -- Credit status --------------------------------------------------------------

@router.get("/credits", response_model=CreditStatusResponse)
def get_credit_status(user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            "SELECT provider FROM user_ai_keys WHERE user_id = %s",
            (user["sub"],),
        )
        own_keys = {row["provider"] for row in cur.fetchall()}

    return CreditStatusResponse(
        has_own_key={
            "openai":    "openai"    in own_keys,
            "anthropic": "anthropic" in own_keys,
            "gemini":    "gemini"    in own_keys,
            "ollama":    "ollama"    in own_keys,
        },
    )


# -- AI Feature: Extraction -----------------------------------------------------

@router.post("/extract", response_model=ExtractionResponse)
async def extract_nodes(
    body: ExtractionRequest,
    user: dict = Depends(get_current_user),
):
    try:
        resolved = resolve_provider(user["sub"], "extraction", body.preferred_provider, body.preferred_model)
    except AIProviderUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))

    # ISS-C-2: If FRD and segment looks like it contains mandatory items, suppress existing_titles hint
    use_existing_hint = True
    if body.doc_type == "FRD":
        import re
        mandatory_patterns = [
            r'(GET|POST|PUT|DELETE|PATCH)\s+/',
            r'BR-\d+', r'BL-\d+', r'US-\d+',
            r'reCAPTCHA', r'OTP', r'One-Time Password', r'CAPTCHA'
        ]
        if any(re.search(p, body.segment, re.IGNORECASE) for p in mandatory_patterns):
            use_existing_hint = False

    existing_hint = ""
    if use_existing_hint and body.existing_titles:
        existing_hint = (
            f"\nExisting node titles in this workspace (avoid duplication):\n"
            + "\n".join(f"- {t}" for t in body.existing_titles[:50])
        )

    from core.ai import get_extraction_prompt
    messages = [
        {"role": "system", "content": get_extraction_prompt(body.doc_type)},
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


# -- AI Feature: Embedding ------------------------------------------------------

@router.post("/embed", response_model=EmbedResponse)
async def embed_text(
    body: EmbedRequest,
    user: dict = Depends(get_current_user),
):
    try:
        resolved = resolve_provider(user["sub"], "embedding", body.preferred_provider, body.preferred_model)
    except AIProviderUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))

    try:
        vector, tokens = await embed(resolved, body.text)
    except AIProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

    record_usage(resolved, "embedding", tokens, body.workspace_id, body.node_id)

    return EmbedResponse(vector=vector, tokens_used=tokens, source=resolved.source)


# -- AI Feature: Restructure ----------------------------------------------------

@router.post("/restructure", response_model=RestructureResponse)
async def restructure_nodes(
    body: RestructureRequest,
    user: dict = Depends(get_current_user),
):
    if len(body.node_ids) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 nodes per restructure request")

    try:
        resolved = resolve_provider(user["sub"], "restructure", body.preferred_provider, body.preferred_model)
    except AIProviderUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Fetch node data
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, title, content_type, body, tags
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


# Note: _archive_qa_to_kb and _increment_ask_count moved to services.nodes


def _persist_chat_turn(
    session_id: str,
    question: str,
    answer: str,
    source_node_ids: list[str],
    tokens: int,
) -> None:
    """Persist a user+assistant message pair and update session metadata."""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO chat_messages (session_id, role, content, source_node_ids, tokens_used)
            VALUES (%s, 'user', %s, '{}', 0),
                   (%s, 'assistant', %s, %s, %s)
        """, (session_id, question, session_id, answer, source_node_ids, tokens))
        cur.execute("""
            UPDATE chat_sessions SET
                anchored_node_ids = (
                    SELECT COALESCE(array_agg(DISTINCT x), '{}')
                    FROM unnest(anchored_node_ids || %s::text[]) x
                ),
                message_count  = message_count + 2,
                tokens_total   = tokens_total + %s,
                last_active_at = now(),
                title = CASE WHEN title = '' THEN LEFT(%s, 60) ELSE title END
            WHERE id = %s
        """, (source_node_ids, tokens, question, session_id))


# Voice mode (D7 / mem_77b74b8a): the model leads its reply with a spoken
# summary wrapped in these markers, so it can be shown/spoken before the full
# answer finishes streaming. The markers are stripped from the visible answer.
_SPOKEN_START = "<<<SPOKEN>>>"
_SPOKEN_END = "<<<END_SPOKEN>>>"

_SPOKEN_SUMMARY_INSTRUCTION = (
    "\n\nVOICE MODE — begin your reply with a summary meant to be read aloud, "
    f"wrapped EXACTLY like this:\n{_SPOKEN_START}\n"
    "a natural, spoken version of the answer in the user's language that walks through "
    "ALL of its main points — touch on each key idea or section the answer covers (a "
    "thought or two each) so the listener gets the real substance, not a one-line gist. "
    "Scale with the answer: brief for a short reply, a fuller multi-point rundown for a "
    "long or structured one. Stay conversational; skip code, exact syntax, markdown, "
    "URLs, and lists — describe them in words instead of reading them out.\n"
    f"{_SPOKEN_END}\n"
    "Then write your full detailed answer as normal after the closing marker."
)


async def _stream_with_spoken_summary(stream, want: bool):
    """Wrap chat_stream, splitting a leading <<<SPOKEN>>>...<<<END_SPOKEN>>> block.

    Yields (kind, text, tokens) where kind is 'summary', 'summary_done', or
    'content'. If the markers never appear (model ignored the instruction) or
    want is False, everything is emitted as 'content'.
    """
    mode = "seek" if want else "content"
    buf = ""
    emitted = 0
    async for chunk, tokens in stream:
        if mode == "content":
            yield ("content", chunk or "", tokens)
            continue
        if not chunk:
            yield ("content", "", tokens)  # carry token count; empty text is ignored downstream
            continue
        buf += chunk
        if mode == "seek":
            i = buf.find(_SPOKEN_START)
            if i != -1:
                buf = buf[i + len(_SPOKEN_START):]
                mode = "summary"
            elif len(buf) > 2000:
                # Model isn't going to emit the marker — treat as plain content.
                yield ("content", buf, tokens)
                buf = ""
                mode = "content"
                continue
            else:
                yield ("content", "", tokens)
                continue
        if mode == "summary":
            e = buf.find(_SPOKEN_END)
            if e != -1:
                seg = buf[emitted:e]
                if seg:
                    yield ("summary", seg, 0)
                yield ("summary_done", "", 0)
                remainder = buf[e + len(_SPOKEN_END):].lstrip("\n")
                buf = ""
                emitted = 0
                mode = "content"
                yield ("content", remainder, tokens)
            else:
                # Emit summary text but hold back a tail that could be a partial end marker.
                safe = len(buf) - len(_SPOKEN_END)
                if safe > emitted:
                    yield ("summary", buf[emitted:safe], 0)
                    emitted = safe
                yield ("content", "", tokens)
    # Flush anything left if the stream ended before markers closed.
    if mode != "content" and buf:
        yield ("content", buf[emitted:] if mode == "summary" else buf, 0)


@router.post("/chat-stream")
async def chat_with_kb_stream(
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    from core.ai import CHAT_SYSTEM, chat_stream, embed
    from services.nodes import propose_change as _propose_change
    from fastapi.responses import StreamingResponse

    headers: dict[str, str] = {}
    if body.history:
        headers["Deprecation"] = "true"
        headers["Link"] = '</api/v1/ai/sessions>; rel="successor-version"'

    async def event_generator():
        from datetime import timezone
        try:
            # --- Phase 6: Session handling ---
            session_id = body.session_id
            anchored_node_ids: list[str] = []
            history: list[dict] = body.history or []

            if session_id:
                with db_cursor() as cur:
                    cur.execute(
                        "SELECT last_active_at, anchored_node_ids FROM chat_sessions WHERE id = %s AND user_id = %s",
                        (session_id, user["sub"])
                    )
                    session_row = cur.fetchone()
                if not session_row:
                    yield json.dumps({"type": "error", "detail": "session_not_found"}) + "\n"
                    return
                # Cold session guard (>= 7 days since last activity)
                age_days = (datetime.now(timezone.utc) - session_row["last_active_at"]).days
                if age_days >= 7:
                    yield json.dumps({"type": "error", "detail": "session_frozen"}) + "\n"
                    return
                anchored_node_ids = session_row["anchored_node_ids"] or []
                # Load last 20 messages from DB (overrides body.history)
                with db_cursor() as cur:
                    cur.execute("""
                        SELECT role, content FROM chat_messages
                        WHERE session_id = %s ORDER BY created_at DESC, id DESC LIMIT 20
                    """, (session_id,))
                    rows = cur.fetchall()
                history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
            else:
                # Create new session
                session_id = generate_id("chs")
                title = body.message[:60]
                with db_cursor(commit=True) as cur:
                    cur.execute(
                        "INSERT INTO chat_sessions (id, workspace_id, user_id, title) VALUES (%s, %s, %s, %s)",
                        (session_id, body.workspace_id, user["sub"], title)
                    )

            yield json.dumps({"type": "session", "session_id": session_id}) + "\n"

            # --- Workspace config ---
            with db_cursor() as cur:
                cur.execute("SELECT embedding_model, embedding_provider FROM workspaces WHERE id = %s", (body.workspace_id,))
                ws_row = cur.fetchone()
                ws_embed_model = ws_row["embedding_model"] if ws_row else None
                ws_embed_prov = ws_row["embedding_provider"] if ws_row else None

                cur.execute("SELECT target_ws_id FROM workspace_associations WHERE source_ws_id = %s", (body.workspace_id,))
                target_ids = {body.workspace_id} | {r["target_ws_id"] for r in cur.fetchall()}
                if body.cross_kb_ids:
                    target_ids |= set(body.cross_kb_ids)

            resolved = resolve_provider(user["sub"], "extraction", body.preferred_provider, body.preferred_model)

            # --- Hybrid node retrieval (Route C: pass anchored_node_ids) ---
            from services.nodes import increment_ask_count
            with db_cursor() as cur:
                source_nodes = await hybrid_retrieval_for_chat(
                    cur, list(target_ids), body.message, user["sub"],
                    ws_embed_prov=ws_embed_prov, ws_embed_model=ws_embed_model,
                    anchor_node_ids=anchored_node_ids,
                )
                faq_hit_id = next((n["_faq_hit_id"] for n in source_nodes if "_faq_hit_id" in n), None)
                if faq_hit_id:
                    background_tasks.add_task(increment_ask_count, faq_hit_id)

            yield json.dumps({"type": "source_nodes", "nodes": [dict(n) for n in source_nodes]}) + "\n"

            context_str = json.dumps([dict(n) for n in source_nodes], ensure_ascii=False, indent=2)
            messages = [{"role": "system", "content": CHAT_SYSTEM}]
            if history:
                messages.extend(history)

            edit_prompt = "\nYou ARE allowed to propose edits/additions. Format them as a JSON block at the end of your response." if body.allow_edits else ""
            summary_prompt = _SPOKEN_SUMMARY_INSTRUCTION if body.want_spoken_summary else ""
            messages.append({"role": "user", "content": f"CONTEXT NODES:\n{context_str}\n\nUSER MESSAGE: {body.message}{edit_prompt}{summary_prompt}"})

            full_answer = ""
            total_tokens = 0
            print(f"[chat-stream] Starting AI stream with provider {resolved.provider.name}...")

            async for kind, text, tokens in _stream_with_spoken_summary(
                chat_stream(resolved, messages), body.want_spoken_summary
            ):
                if kind == "summary":
                    yield json.dumps({"type": "spoken_summary", "delta": text}) + "\n"
                elif kind == "summary_done":
                    yield json.dumps({"type": "spoken_summary_done"}) + "\n"
                elif kind == "content" and text:
                    full_answer += text
                    yield json.dumps({"type": "content", "delta": text}) + "\n"
                if tokens > 0:
                    total_tokens = tokens
            print(f"[chat-stream] AI stream finished. Total tokens: {total_tokens}")

            proposals = []
            final_answer, raw_proposals = parse_ai_proposals(full_answer)

            if raw_proposals and body.allow_edits:
                with db_cursor(commit=True) as cur:
                    proposals = apply_ai_proposals_to_db(cur, body.workspace_id, raw_proposals, body.message)

            if proposals:
                yield json.dumps({"type": "proposals", "proposals": proposals}) + "\n"

            if len(body.message) > 10:
                from services.nodes import archive_qa_to_kb
                background_tasks.add_task(
                    archive_qa_to_kb,
                    body.workspace_id, user["sub"], body.message,
                    final_answer, [n["id"] for n in source_nodes], body.force_auto_active
                )

            # Persist session messages synchronously before yielding done so that
            # getSessionMessages called immediately after receives the full turn.
            try:
                import asyncio as _asyncio
                await _asyncio.to_thread(
                    _persist_chat_turn,
                    session_id, body.message, final_answer,
                    [n["id"] for n in source_nodes], total_tokens,
                )
            except Exception as _persist_err:
                logger.error("Failed to persist chat turn: %s", _persist_err)

            record_usage(resolved, "extraction", total_tokens, body.workspace_id)
            yield json.dumps({"type": "done", "tokens_used": total_tokens, "source": resolved.source}) + "\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield json.dumps({"type": "error", "detail": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson", headers=headers)


@router.post("/chat", response_model=ChatResponse)
async def chat_with_kb(
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    try:
        from core.ai import CHAT_SYSTEM, chat_completion, embed
        from services.nodes import propose_change as _propose_change

        with db_cursor() as cur:
            cur.execute("SELECT embedding_model, embedding_provider FROM workspaces WHERE id = %s", (body.workspace_id,))
            ws_row = cur.fetchone()
            ws_embed_model = ws_row["embedding_model"] if ws_row else None
            ws_embed_prov = ws_row["embedding_provider"] if ws_row else None

            cur.execute("SELECT target_ws_id FROM workspace_associations WHERE source_ws_id = %s", (body.workspace_id,))
            target_ids = {body.workspace_id} | {r["target_ws_id"] for r in cur.fetchall()}
            if body.cross_kb_ids:
                target_ids |= set(body.cross_kb_ids)
        
        resolved = resolve_provider(user["sub"], "extraction", body.preferred_provider, body.preferred_model)

        # --- Hybrid node retrieval ---
        from services.nodes import increment_ask_count
        with db_cursor() as cur:
            source_nodes = await hybrid_retrieval_for_chat(
                cur, list(target_ids), body.message, user["sub"],
                ws_embed_prov=ws_embed_prov, ws_embed_model=ws_embed_model
            )
            
            # If FAQ hit, increment ask count
            faq_hit_id = next((n["_faq_hit_id"] for n in source_nodes if "_faq_hit_id" in n), None)
            if faq_hit_id:
                background_tasks.add_task(increment_ask_count, faq_hit_id)

        context_str = json.dumps([dict(n) for n in source_nodes], ensure_ascii=False, indent=2)
        messages = [{"role": "system", "content": CHAT_SYSTEM}]
        if body.history: messages.extend(body.history)
        
        edit_prompt = "\nYou ARE allowed to propose edits/additions. Format them as a JSON block at the end of your response." if body.allow_edits else ""
        messages.append({"role": "user", "content": f"CONTEXT NODES:\n{context_str}\n\nUSER MESSAGE: {body.message}{edit_prompt}"})

        raw, tokens = await chat_completion(resolved, messages)
        
        answer, raw_proposals = parse_ai_proposals(raw)
        proposals = []
        
        if raw_proposals:
            if body.allow_edits:
                with db_cursor(commit=True) as cur:
                    proposals = apply_ai_proposals_to_db(cur, body.workspace_id, raw_proposals, body.message)
            else:
                proposals = raw_proposals
        
        if len(body.message) > 10:
            background_tasks.add_task(
                _archive_qa_to_kb,
                body.workspace_id,
                user["sub"],
                body.message,
                answer,
                [n["id"] for n in source_nodes],
                body.force_auto_active
            )

        record_usage(resolved, "extraction", tokens, body.workspace_id)
        return ChatResponse(
            answer=answer, 
            proposals=proposals,
            source_nodes=[dict(n) for n in source_nodes],
            tokens_used=tokens, 
            source=resolved.source
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/me")
def get_my_usage(user: dict = Depends(get_current_user)):
    """Return the current user's AI token usage: monthly totals and per-feature breakdown."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                TO_CHAR(created_at, 'YYYY-MM') AS year_month,
                feature,
                provider,
                SUM(tokens_used) AS token_count
            FROM ai_credit_ledger
            WHERE user_id = %s
            GROUP BY year_month, feature, provider
            ORDER BY year_month DESC, token_count DESC
        """, (user["sub"],))
        ledger_rows = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT id, title, tokens_total, message_count, created_at, last_active_at
            FROM chat_sessions
            WHERE user_id = %s
            ORDER BY last_active_at DESC
            LIMIT 20
        """, (user["sub"],))
        sessions = [dict(r) for r in cur.fetchall()]

    return {"ledger": ledger_rows, "sessions": sessions}


@router.post("/chat/feedback", status_code=204)

@router.post("/chat/feedback", status_code=204)
async def submit_chat_feedback(
    body: ChatFeedback,
    user: dict = Depends(get_current_user),
):
    """
    Apply reinforcement or decay based on user feedback.
    """
    from core.database import db_cursor
    
    with db_cursor(commit=True) as cur:
        # 1. Update edge weight
        boost = 0.2 if body.is_helpful else -0.3
        cur.execute("""
            UPDATE edges 
            SET weight = LEAST(1.0, GREATEST(0.0, weight + %s)),
                last_co_accessed = now(),
                co_access_count = co_access_count + 1
            WHERE from_id = %s AND to_id = %s AND workspace_id = %s
            RETURNING weight
        """, (boost, body.question_node_id, body.answer_node_id, body.workspace_id))
        
        res = cur.fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="Edge not found")
        
        new_weight = float(res["weight"])
        
        # 2. Auto-promotion logic
        if body.is_helpful and new_weight > 0.7:
            cur.execute("""
                UPDATE memory_nodes SET status = 'active' 
                WHERE id IN (%s, %s) AND status = 'archived'
            """, (body.question_node_id, body.answer_node_id))

        # 3. Handle fading
        if new_weight < 0.1:
            cur.execute("""
                UPDATE edges SET status = 'faded'
                WHERE from_id = %s AND to_id = %s
            """, (body.question_node_id, body.answer_node_id))

    return


# ---------------------------------------------------------------------------
# Phase 6 — Chat Session CRUD
# ---------------------------------------------------------------------------

class SessionRenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)


@router.get("/sessions")
async def list_chat_sessions(
    workspace_id: str,
    limit: int = 20,
    user: dict = Depends(get_current_user),
):
    """List recent chat sessions for a workspace, split into hot (<=7d) and cold (>7d)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, title, message_count, tokens_total, created_at, last_active_at,
                   (now() - last_active_at) > INTERVAL '7 days' AS is_cold
            FROM chat_sessions
            WHERE workspace_id = %s AND user_id = %s
            ORDER BY last_active_at DESC
            LIMIT %s
        """, (workspace_id, user["sub"], limit))
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = 20,
    before_id: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    """Return messages for a session with cursor-based pagination (before_id to page back)."""
    with db_cursor() as cur:
        # Verify ownership
        cur.execute("SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s", (session_id, user["sub"]))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Session not found")

        if before_id:
            cur.execute("""
                SELECT id, role, content, source_node_ids, tokens_used, created_at
                FROM chat_messages
                WHERE session_id = %s AND id < %s
                ORDER BY created_at DESC, id DESC LIMIT %s
            """, (session_id, before_id, limit))
        else:
            cur.execute("""
                SELECT id, role, content, source_node_ids, tokens_used, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at DESC, id DESC LIMIT %s
            """, (session_id, limit))
        rows = cur.fetchall()
    return list(reversed([dict(r) for r in rows]))


@router.patch("/sessions/{session_id}", status_code=204)
async def rename_chat_session(
    session_id: str,
    body: SessionRenameRequest,
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE chat_sessions SET title = %s WHERE id = %s AND user_id = %s",
            (body.title, session_id, user["sub"])
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_chat_session(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM chat_sessions WHERE id = %s AND user_id = %s",
            (session_id, user["sub"])
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")
