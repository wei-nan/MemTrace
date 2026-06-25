"""
services/node_projection.py — Detail level projection and top edges calculation.
"""
from __future__ import annotations

import datetime
from typing import Literal, Optional, List, Dict, Any


def calculate_top_edges(edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate top edges for a node based on the sorting weight:
    (weight * 2) + (traversal_count * 0.1) + recency_factor.

    Each direction (in / out) gets 1.5 edges (up to 3 total).
    Returns a list of dicts: { relation, target_id, target_title, weight }.
    """
    if not edges:
        return []

    now = datetime.datetime.now(datetime.timezone.utc)
    scored_edges = []

    for e in edges:
        last_accessed = e.get("last_co_accessed")
        if last_accessed is None:
            # Fallback if somehow None
            last_accessed = now
        elif isinstance(last_accessed, str):
            # Parse if string
            try:
                # Handle potential ISO format with 'Z' or offset
                if last_accessed.endswith("Z"):
                    last_accessed = last_accessed[:-1] + "+00:00"
                last_accessed = datetime.datetime.fromisoformat(last_accessed)
            except Exception:
                last_accessed = now
        elif not isinstance(last_accessed, datetime.datetime):
            last_accessed = now
        
        # Ensure last_accessed has timezone info
        if last_accessed.tzinfo is None:
            last_accessed = last_accessed.replace(tzinfo=datetime.timezone.utc)
        
        diff_days = (now - last_accessed).total_seconds() / 86400.0
        recency_factor = 1.0 / (1.0 + max(0.0, diff_days))

        weight = float(e.get("weight", 1.0))
        traversal_count = int(e.get("traversal_count") or 0)
        score = (weight * 2.0) + (traversal_count * 0.1) + recency_factor

        scored_edges.append({
            "relation": e.get("relation"),
            "target_id": e.get("target_id"),
            "target_title": e.get("target_title") or "",
            "weight": weight,
            "direction": e.get("direction", "out"),
            "score": score
        })

    # Separate by direction
    in_edges = [se for se in scored_edges if se["direction"] == "in"]
    out_edges = [se for se in scored_edges if se["direction"] == "out"]

    in_edges.sort(key=lambda x: x["score"], reverse=True)
    out_edges.sort(key=lambda x: x["score"], reverse=True)

    result = []
    in_idx = 0
    out_idx = 0

    # Round 1: Take 1 from each if possible
    if in_idx < len(in_edges):
        result.append(in_edges[in_idx])
        in_idx += 1
    if out_idx < len(out_edges):
        result.append(out_edges[out_idx])
        out_idx += 1

    # Round 2: Take remaining from sorted union of both directions to make it up to 3
    remaining = []
    if in_idx < len(in_edges):
        remaining.extend(in_edges[in_idx:])
    if out_idx < len(out_edges):
        remaining.extend(out_edges[out_idx:])

    remaining.sort(key=lambda x: x["score"], reverse=True)

    while len(result) < 3 and remaining:
        result.append(remaining.pop(0))

    # Format return list
    return [
        {
            "relation": r["relation"],
            "target_id": r["target_id"],
            "target_title": r["target_title"],
            "weight": r["weight"]
        }
        for r in result
    ]


def get_node_top_edges(cur, ws_id: str, node_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all active edges connected to a node, calculate, and return the top 3 edges.
    """
    cur.execute(
        """
        SELECT 
            e.id, e.relation, e.weight, e.traversal_count, e.last_co_accessed,
            e.from_id, e.to_id,
            CASE WHEN e.from_id = %s THEN 'out' ELSE 'in' END AS direction,
            CASE WHEN e.from_id = %s THEN e.to_id ELSE e.from_id END AS target_id,
            n.title AS target_title
        FROM edges e
        JOIN memory_nodes n ON n.id = CASE WHEN e.from_id = %s THEN e.to_id ELSE e.from_id END
        WHERE e.workspace_id = %s AND e.status = 'active'
          AND e.edge_class <> 'telemetry'
          AND (e.from_id = %s OR e.to_id = %s)
        """,
        (node_id, node_id, node_id, ws_id, node_id, node_id)
    )
    rows = cur.fetchall()
    return calculate_top_edges(rows)


def project_node(
    node: Dict[str, Any], 
    level: Literal['probe', 'brief', 'full'], 
    top_edges: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Project a node to the desired detail level.
    """
    body = node.get("body") or ""
    summary_1line = node.get("summary_1line") or (body[:80] if body else "")
    
    if level == 'probe':
        return {
            "id": node.get("id"),
            "title": node.get("title"),
            "content_type": node.get("content_type"),
            "tags": node.get("tags") or [],
            "trust_score": float(node["trust_score"]) if node.get("trust_score") is not None else None,
            "summary_1line": summary_1line,
            "top_edges": top_edges or []
        }
    elif level == 'brief':
        probe = project_node(node, 'probe', top_edges)
        probe.update({
            "body_excerpt_200": body[:200] if body else "",
            "why_matched": node.get("why_matched") or ""
        })
        return probe
    else:
        # full
        full_node = dict(node)
        if top_edges is not None:
            full_node["top_edges"] = top_edges
        if "summary_1line" not in full_node:
            full_node["summary_1line"] = summary_1line
        return full_node
