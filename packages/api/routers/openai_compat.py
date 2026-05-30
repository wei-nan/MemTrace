"""
openai_compat.py — OpenAI-compatible endpoints for MemTrace.
"""
import time
import json
import re
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from core.deps import get_current_user
from core.database import db_cursor
from services.workspaces import list_workspaces_in_db
from services.search import hybrid_retrieval_for_chat
from core.ai import (
    CHAT_SYSTEM,
    chat_completion,
    chat_stream,
    resolve_provider,
    record_usage,
    estimate_tokens,
    AIProviderError
)

router = APIRouter(prefix="/v1", tags=["openai_compat"])

# -- Pydantic models for request ----------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 4096

    model_config = {
        "extra": "ignore"
    }

# -- Helper to map Workspace to OpenAI Model representation --------------------

def workspace_to_openai_model(ws: dict) -> dict:
    # Created time as timestamp; fall back to current time if missing
    created_ts = int(ws["created_at"].timestamp()) if ws.get("created_at") else int(time.time())
    return {
        "id": f"memtrace-{ws['id']}",
        "object": "model",
        "created": created_ts,
        "owned_by": "memtrace",
        "display_name": ws.get("name", "")
    }

# -- Endpoints -----------------------------------------------------------------

@router.get("/models")
def list_models(user: dict = Depends(get_current_user)):
    """
    List all workspaces accessible by the authenticated user and map them as memtrace-{workspace_id} models.
    """
    with db_cursor() as cur:
        # Use existing list_workspaces_in_db to get workspaces matching user's permissions
        workspaces = list_workspaces_in_db(cur, search=None, user=user)
        
    openai_models = [workspace_to_openai_model(ws) for ws in workspaces]
    return {
        "object": "list",
        "data": openai_models
    }

@router.get("/models/{model_id}")
def get_model(model_id: str, user: dict = Depends(get_current_user)):
    """
    Get metadata for a specific workspace mapped model.
    """
    workspace_id = model_id
    if workspace_id.startswith("memtrace-"):
        workspace_id = workspace_id[len("memtrace-"):]
    else:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "message": f"Model '{model_id}' not found. Must start with 'memtrace-' prefix.",
                    "type": "invalid_request_error",
                    "param": "model",
                    "code": "model_not_found"
                }
            }
        )

    with db_cursor() as cur:
        # Check permission to access this workspace
        cur.execute(
            """SELECT w.* FROM workspaces w
               LEFT JOIN workspace_members wm ON wm.workspace_id = w.id AND wm.user_id = %s
               WHERE w.id = %s AND (w.owner_id = %s OR wm.user_id IS NOT NULL OR w.visibility = 'public')""",
            (user["sub"], workspace_id, user["sub"])
        )
        ws_row = cur.fetchone()
        
    if not ws_row:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "message": f"Model '{model_id}' not found or access denied.",
                    "type": "invalid_request_error",
                    "param": "model",
                    "code": "model_not_found"
                }
            }
        )

    return workspace_to_openai_model(ws_row)

@router.post("/chat/completions")
async def chat_completions(
    request_body: ChatCompletionRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """
    OpenAI-compatible chat completion utilizing MemTrace hybrid RAG search.
    """
    # 1. Resolve workspace_id from model name
    workspace_id = None
    if request_body.model.startswith("memtrace-"):
        workspace_id = request_body.model[len("memtrace-"):]

    # 2. Check system message override
    system_override_id = None
    for msg in request_body.messages:
        if msg.role == "system":
            match = re.search(r"workspace_id:\s*(ws_[a-zA-Z0-9_\-]+)", msg.content)
            if match:
                system_override_id = match.group(1)
                break

    if system_override_id:
        workspace_id = system_override_id

    if not workspace_id:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": "Invalid model parameter or missing workspace ID. Model must start with 'memtrace-' or a system message override must specify 'workspace_id: ws_xxx'",
                    "type": "invalid_request_error",
                    "param": "model",
                    "code": "model_invalid"
                }
            }
        )

    # 3. Retrieve workspace and verify access
    with db_cursor() as cur:
        cur.execute(
            """SELECT w.id, w.embedding_model, w.embedding_provider
               FROM workspaces w
               LEFT JOIN workspace_members wm ON wm.workspace_id = w.id AND wm.user_id = %s
               WHERE w.id = %s AND (w.owner_id = %s OR wm.user_id IS NOT NULL OR w.visibility = 'public')""",
            (user["sub"], workspace_id, user["sub"])
        )
        ws_row = cur.fetchone()

    if not ws_row:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "message": f"Workspace '{workspace_id}' not found or access denied.",
                    "type": "invalid_request_error",
                    "param": "model",
                    "code": "model_not_found"
                }
            }
        )

    ws_embed_model = ws_row["embedding_model"]
    ws_embed_prov = ws_row["embedding_provider"]

    # 4. Fetch target_ids based on associations
    with db_cursor() as cur:
        cur.execute("SELECT target_ws_id FROM workspace_associations WHERE source_ws_id = %s", (workspace_id,))
        target_ids = {workspace_id} | {r["target_ws_id"] for r in cur.fetchall()}

    # 5. Extract user query (last message) and messages list
    if not request_body.messages:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": "At least one message is required.",
                    "type": "invalid_request_error",
                    "param": "messages",
                    "code": "messages_empty"
                }
            }
        )

    user_query = request_body.messages[-1].content

    # 6. Resolve provider configuration
    try:
        resolved = resolve_provider(user["sub"], "extraction")
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": f"AI provider error: {str(e)}",
                    "type": "invalid_request_error",
                    "param": "model",
                    "code": "provider_unavailable"
                }
            }
        )

    # 7. Run Hybrid RAG Retrieval
    with db_cursor() as cur:
        source_nodes = await hybrid_retrieval_for_chat(
            cur, list(target_ids), user_query, user["sub"],
            ws_embed_prov=ws_embed_prov, ws_embed_model=ws_embed_model
        )

    # 8. Reconstruct LLM message list
    llm_messages = []
    client_system_content = ""
    history_start = 0
    if request_body.messages[0].role == "system":
        client_system_content = request_body.messages[0].content
        history_start = 1

    # Merge CHAT_SYSTEM with client system message if custom instructions exist
    system_content = CHAT_SYSTEM
    if client_system_content:
        # Strip workspace override header to avoid confusing LLM
        cleaned_client_system = re.sub(r"workspace_id:\s*ws_\w+", "", client_system_content).strip()
        if cleaned_client_system:
            system_content += f"\n\nAdditional Instructions:\n{cleaned_client_system}"

    llm_messages.append({"role": "system", "content": system_content})

    # Include intermediate history messages
    for msg in request_body.messages[history_start:-1]:
        llm_messages.append({"role": msg.role, "content": msg.content})

    # User message contains RAG context
    context_str = json.dumps([dict(n) for n in source_nodes], ensure_ascii=False, indent=2)
    llm_messages.append({
        "role": "user",
        "content": f"CONTEXT NODES:\n{context_str}\n\nUSER MESSAGE: {user_query}"
    })

    headers = {
        "x-ratelimit-remaining-requests": "999",
        "x-ratelimit-remaining-tokens": "99999",
    }

    # 9. Handle Non-streaming
    if not request_body.stream:
        try:
            raw, tokens = await chat_completion(
                resolved,
                llm_messages,
                max_tokens=request_body.max_tokens or 4096,
                temperature=request_body.temperature or 0.2
            )
        except AIProviderError as e:
            return JSONResponse(
                status_code=502,
                content={
                    "error": {
                        "message": f"AI Completion failed: {str(e)}",
                        "type": "api_error",
                        "code": "provider_error"
                    }
                }
            )

        content = raw
        if source_nodes:
            sources_text = "\n\n**Sources:**\n" + "\n".join(f"[{i+1}] {node['title']}" for i, node in enumerate(source_nodes))
            content += sources_text

        # Estimate prompt/completion tokens
        prompt_content = json.dumps(llm_messages)
        prompt_tokens = estimate_tokens(prompt_content, resolved.model)
        completion_tokens = max(0, tokens - prompt_tokens)

        # Record usage
        background_tasks.add_task(record_usage, resolved, "extraction", tokens, workspace_id)

        completion_id = f"chatcmpl-{int(time.time() * 1000)}"
        response_data = {
            "id": completion_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request_body.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": tokens
            },
            "x_source_nodes": jsonable_encoder([dict(n) for n in source_nodes])
        }
        return JSONResponse(content=response_data, headers=headers)

    # 10. Handle Streaming response
    async def stream_generator():
        completion_id = f"chatcmpl-{int(time.time() * 1000)}"
        created_time = int(time.time())
        total_tokens = 0
        try:
            async for chunk, tokens in chat_stream(
                resolved,
                llm_messages,
                max_tokens=request_body.max_tokens or 4096,
                temperature=request_body.temperature or 0.2
            ):
                if tokens > 0:
                    total_tokens = tokens
                if chunk:
                    chunk_payload = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created_time,
                        "model": request_body.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {
                                    "content": chunk
                                },
                                "finish_reason": None
                            }
                        ]
                    }
                    yield f"data: {json.dumps(chunk_payload, ensure_ascii=False)}\n\n"

            # Stream finished. Now stream inline source citations if they exist
            if source_nodes:
                sources_text = "\n\n**Sources:**\n" + "\n".join(f"[{i+1}] {node['title']}" for i, node in enumerate(source_nodes))
                sources_payload = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": request_body.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": sources_text
                            },
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(sources_payload, ensure_ascii=False)}\n\n"

            # Yield top-level metadata and finish_reason in final chunk
            final_payload = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": request_body.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ],
                "x_source_nodes": jsonable_encoder([dict(n) for n in source_nodes])
            }
            yield f"data: {json.dumps(final_payload, ensure_ascii=False)}\n\n"

            # Record usage in background
            record_usage(resolved, "extraction", total_tokens or 100, workspace_id)

        except Exception as e:
            error_payload = {
                "error": {
                    "message": f"Stream error: {str(e)}",
                    "type": "api_error"
                }
            }
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            **headers
        }
    )
