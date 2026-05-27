"""
services/inquiry_paths.py — Inquiry paths recording, similarity search, and reinforcement.
"""
from __future__ import annotations

import json
import logging
import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from core.database import db_cursor
from core.ai import embed, resolve_provider, record_usage
from core.security import generate_id

logger = logging.getLogger(__name__)


@dataclass
class InquiryPath:
    id: str
    workspace_id: str
    agent_id: str
    query_text: str
    node_sequence: List[str]
    outcome: Literal['success', 'partial', 'failed', 'gap']
    started_at: datetime.datetime
    ended_at: datetime.datetime
    query_emb: Optional[List[float]] = None
    token_used: Optional[int] = None
    rating: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "agent_id": self.agent_id,
            "query_text": self.query_text,
            "node_sequence": self.node_sequence,
            "outcome": self.outcome,
            "started_at": self.started_at.isoformat() if isinstance(self.started_at, datetime.datetime) else str(self.started_at),
            "ended_at": self.ended_at.isoformat() if isinstance(self.ended_at, datetime.datetime) else str(self.ended_at),
            "token_used": self.token_used,
            "rating": self.rating,
            "metadata": self.metadata
        }


async def record_path_in_db(
    cur,
    ws_id: str,
    user_id: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Record an agent's exploration path (B1-T08).
    Automatically embeds query_text and persists the path to the DB.
    """
    query_text = payload["query_text"]
    node_sequence = payload.get("node_sequence") or []
    outcome = payload["outcome"]
    started_at_val = payload["started_at"]
    token_used = payload.get("token_used")
    rating = payload.get("rating")
    metadata = payload.get("metadata") or {}

    # Support parsing string datetimes
    if isinstance(started_at_val, str):
        try:
            if started_at_val.endswith("Z"):
                started_at_val = started_at_val[:-1] + "+00:00"
            started_at = datetime.datetime.fromisoformat(started_at_val)
        except Exception:
            started_at = datetime.datetime.now(datetime.timezone.utc)
    else:
        started_at = started_at_val

    ended_at = datetime.datetime.now(datetime.timezone.utc)

    # 1. Fetch workspace embedding config to generate embedding
    cur.execute("SELECT embedding_model, embedding_provider FROM workspaces WHERE id = %s", (ws_id,))
    ws_row = cur.fetchone()
    ws_model = ws_row["embedding_model"] if ws_row else None
    ws_prov = ws_row["embedding_provider"] if ws_row else None

    query_emb = None
    if ws_model:
        try:
            resolved = resolve_provider(user_id, "embedding", preferred_provider=ws_prov, preferred_model=ws_model)
            vector, tokens = await embed(resolved, query_text)
            record_usage(resolved, "record_path", tokens, ws_id)
            query_emb = vector
        except Exception as exc:
            logger.error(f"Failed to generate embedding for record_path: {exc}")

    # Generate path ID
    path_id = generate_id("path")

    # 2. Insert into DB
    cur.execute(
        """
        INSERT INTO inquiry_paths (
            id, workspace_id, agent_id, query_text, query_emb, node_sequence,
            outcome, started_at, ended_at, token_used, rating, metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            path_id, ws_id, user_id, query_text, query_emb, node_sequence,
            outcome, started_at, ended_at, token_used, rating, json.dumps(metadata)
        )
    )
    row = cur.fetchone()
    
    # Cast row to dict safely (handling psycopg2 RealDictRow)
    result = dict(row) if row else {}
    if "query_emb" in result:
        result.pop("query_emb")  # Remove massive vector from normal response
    return result


async def search_with_history_in_db(
    cur,
    ws_id: str,
    query_text: str,
    similarity_threshold: float,
    limit: int,
    user_id: str
) -> List[Dict[str, Any]]:
    """
    Search historical inquiry paths using vector similarity on query_emb (B1-T09).
    Filters on outcome in ('success', 'partial') and rating >= 0 (or NULL).
    """
    cur.execute("SELECT embedding_model, embedding_provider FROM workspaces WHERE id = %s", (ws_id,))
    ws_row = cur.fetchone()
    if not ws_row:
        return []
    ws_model = ws_row["embedding_model"]
    ws_prov = ws_row["embedding_provider"]

    # 1. Embed query_text
    try:
        resolved = resolve_provider(user_id, "embedding", preferred_provider=ws_prov, preferred_model=ws_model)
        vector, tokens = await embed(resolved, query_text)
        record_usage(resolved, "search_with_history", tokens, ws_id)
    except Exception as exc:
        logger.error(f"Embedding failed in search_with_history: {exc}")
        return []

    # 2. Vector search on inquiry_paths
    # Note: query_emb <=> %s::vector is the cosine distance, so 1 - distance is similarity
    cur.execute(
        """
        SELECT id, query_text, node_sequence, outcome, rating,
               (1 - (query_emb <=> %s::vector)) AS similarity
        FROM inquiry_paths
        WHERE workspace_id = %s 
          AND query_emb IS NOT NULL
          AND outcome IN ('success', 'partial')
          AND (rating IS NULL OR rating >= 0)
          AND archived_at IS NULL
          AND (1 - (query_emb <=> %s::vector)) >= %s
        ORDER BY similarity DESC
        LIMIT %s
        """,
        (vector, ws_id, vector, similarity_threshold, limit)
    )
    rows = cur.fetchall()
    
    results = []
    for r in rows:
        results.append({
            "path_id": r["id"],
            "query_text": r["query_text"],
            "node_sequence": r["node_sequence"] or [],
            "outcome": r["outcome"],
            "similarity": float(r["similarity"]) if r["similarity"] is not None else 0.0,
            "rating": r["rating"]
        })
    return results
