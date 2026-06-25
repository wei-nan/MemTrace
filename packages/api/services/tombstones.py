"""services/tombstones.py — record hard-deletes as auditable tombstones.

Decay (mem_3bbdf4dc) governs knowledge that was once true: it fades, it is not
deleted. Genuinely mis-created data (hallucination, wrong-direction edge,
duplicate, orphaned reference, PII) is never-true noise and may be hard-deleted —
but per mem_347895c4 the *fact* of removal must remain auditable. The content can
disappear; the record that something was removed must not. 帳本不說謊，連對刪除也不說謊。
"""
from __future__ import annotations

import json
from typing import Optional

from core.security import generate_id

VALID_REASON_CATEGORIES = frozenset(
    {"hallucination", "wrong_direction", "duplicate", "pii", "orphaned", "other"}
)


def record_node_tombstone(
    cur,
    ws_id: str,
    node_row: dict,
    deleted_by: str = "system",
    reason_category: str = "other",
    reason_note: str = "",
    source_context: Optional[dict] = None,
) -> None:
    _insert(
        cur, ws_id, "node", (node_row or {}).get("id"),
        deleted_by, reason_category, reason_note, source_context,
        title=(node_row or {}).get("title"),
    )


def record_edge_tombstone(
    cur,
    ws_id: str,
    edge_row: dict,
    deleted_by: str = "system",
    reason_category: str = "other",
    reason_note: str = "",
    source_context: Optional[dict] = None,
) -> None:
    edge_row = edge_row or {}
    _insert(
        cur, ws_id, "edge", edge_row.get("id"),
        deleted_by, reason_category, reason_note, source_context,
        relation=edge_row.get("relation"),
        from_id=edge_row.get("from_id"),
        to_id=edge_row.get("to_id"),
    )


def _insert(
    cur,
    ws_id: str,
    object_type: str,
    object_id: Optional[str],
    deleted_by: str,
    reason_category: str,
    reason_note: str,
    source_context: Optional[dict],
    *,
    relation: Optional[str] = None,
    from_id: Optional[str] = None,
    to_id: Optional[str] = None,
    title: Optional[str] = None,
) -> None:
    if reason_category not in VALID_REASON_CATEGORIES:
        reason_category = "other"
    cur.execute(
        """
        INSERT INTO tombstones
            (id, workspace_id, object_type, object_id, relation, from_id, to_id, title,
             deleted_by, reason_category, reason_note, source_context)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            generate_id("tomb"), ws_id, object_type, object_id, relation, from_id, to_id, title,
            deleted_by, reason_category, reason_note,
            json.dumps(source_context) if source_context else None,
        ),
    )
