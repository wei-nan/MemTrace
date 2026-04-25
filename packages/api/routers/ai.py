"""
AI router - user-facing endpoints for:
  - Managing personal API keys (CRUD)
  - Querying free-tier credit usage
  - Invoking AI features (extraction, embedding, restructure)
"""

from __future__ import annotations

from datetime import datetime
import json
from typing import Literal, Optional

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
    EXTRACTION_SYSTEM,
    RESTRUCTURE_SYSTEM,
    strip_fences,
)
from core.database import db_cursor
from core.deps import get_current_user
from core.security import generate_id

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

# -- Pydantic models ------------------------------------------------------------

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
    history: Optional[list[dict]] = None
    allow_edits: bool = False
    cross_kb_ids: Optional[list[str]] = None
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None

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


# -- API Key management ---------------------------------------------------------

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


async def _archive_qa_to_kb(ws_id: str, user_id: str, question: str, answer: str, source_node_ids: list[str]):
    """
    Background task to distill a Q&A interaction into structured Memory Nodes.
    """
    try:
        from core.ai import chat_completion, resolve_provider, strip_fences
        from core.database import db_cursor
        from core.security import generate_id
        from routers.kb import _propose_change

        # 1. Resolve AI provider for distillation
        resolved = resolve_provider(user_id, "extraction")
        
        system_prompt = (
            "You are a Knowledge Archiver. Distill the following Q&A into a set of MemTrace nodes.\n"
            "RULE 1: The Question MUST be a 'context' node.\n"
            "RULE 2: The Answer should be 'factual', 'procedural', or 'preference'.\n"
            "RULE 3: Return a JSON array of nodes with 'title_zh', 'title_en', 'content_type', 'body_zh', 'body_en', 'tags'.\n"
            "Output EXACTLY one Q node and one A node."
        )
        user_prompt = f"QUESTION: {question}\n\nANSWER: {answer}"
        
        raw, _ = await chat_completion(resolved, [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}])
        nodes_data = json.loads(strip_fences(raw))
        
        if not isinstance(nodes_data, list) or len(nodes_data) < 2:
            return

        with db_cursor(commit=True) as cur:
            # Create the nodes
            q_node = nodes_data[0]
            a_node = nodes_data[1]
            q_node["content_type"] = "context"
            
            # Initial status is 'archived' (Review Queue)
            q_id = _propose_change(cur, ws_id, "create", None, q_node, "ai", "qa_archiver")
            a_id = _propose_change(cur, ws_id, "create", None, a_node, "ai", "qa_archiver")
            
            # Create the initial Edge between Q and A
            edge_id = generate_id("edge")
            cur.execute("""
                INSERT INTO edges (id, workspace_id, from_id, to_id, relation, weight, status)
                VALUES (%s, %s, %s, %s, 'related_to', 0.5, 'active')
            """, (edge_id, ws_id, q_id, a_id))
            
            print(f"[qa-archiver] Created Q-A pair: {q_id} -> {a_id}")

    except Exception as e:
        print(f"[qa-archiver] Failed to archive Q&A: {e}")


@router.post("/chat", response_model=ChatResponse)
async def chat_with_kb(
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    try:
        from core.ai import CHAT_SYSTEM
        from routers.kb import _propose_change

        resolved = resolve_provider(user["sub"], "extraction", body.preferred_provider, body.preferred_model)
        embed_prov = resolve_provider(user["sub"], "embedding", body.preferred_provider, body.preferred_model)
        vector, _ = await embed(embed_prov, body.message)
        
        with db_cursor() as cur:
            # D5: Association-aware search + cross_kb_ids
            cur.execute("SELECT target_ws_id FROM workspace_associations WHERE source_ws_id = %s", (body.workspace_id,))
            target_ids = {body.workspace_id} | {r["target_ws_id"] for r in cur.fetchall()}
            if body.cross_kb_ids:
                target_ids |= set(body.cross_kb_ids)
            
            cur.execute("""
                SELECT id, title_zh, title_en, body_zh, body_en, workspace_id,
                       (1 - (embedding <=> %s::vector)) AS similarity
                FROM memory_nodes
                WHERE workspace_id = ANY(%s) AND embedding IS NOT NULL AND status = 'active'
                ORDER BY similarity DESC LIMIT 10
            """, (vector, list(target_ids)))
            source_nodes = cur.fetchall()

        context_str = json.dumps([dict(n) for n in source_nodes], ensure_ascii=False, indent=2)
        messages = [{"role": "system", "content": CHAT_SYSTEM}]
        if body.history: messages.extend(body.history)
        
        edit_prompt = "\nYou ARE allowed to propose edits/additions. Format them as a JSON block at the end of your response." if body.allow_edits else ""
        messages.append({"role": "user", "content": f"CONTEXT NODES:\n{context_str}\n\nUSER MESSAGE: {body.message}{edit_prompt}"})

        raw, tokens = await chat_completion(resolved, messages)
        
        answer = raw
        proposals = []
        
        if "```json" in raw:
            parts = raw.split("```json")
            answer = parts[0].strip()
            json_part = parts[1].split("```")[0].strip()
            try:
                raw_proposals = json.loads(json_part)
                if body.allow_edits:
                    with db_cursor(commit=True) as cur:
                        for p in raw_proposals:
                            op = p.get("operation", "update")
                            if op not in ("create", "update", "delete"):
                                op = "update"
                                
                            rid = _propose_change(
                                cur,
                                body.workspace_id,
                                op,
                                p.get("target_node_ids", [None])[0],
                                p.get("proposed"),
                                "ai",
                                "chat_assistant",
                                proposer_meta={"source": "chat", "original_query": body.message},
                                source_info=f"AI Chat Proposal: {p.get('reason', 'No reason provided')}"
                            )
                            proposals.append({"review_queue_id": rid, "operation": op, "reason": p.get("reason")})
                else:
                    proposals = raw_proposals
            except Exception as e:
                print(f"Failed to parse or save chat proposals: {e}")
        
        # ACTIVE ARCHIVING: Archive this Q&A in the background
        if len(body.message) > 10:
            background_tasks.add_task(
                _archive_qa_to_kb,
                body.workspace_id,
                user["sub"],
                body.message,
                answer,
                [n["id"] for n in source_nodes]
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
