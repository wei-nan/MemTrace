"""services/clusters.py — Dynamic node cluster CRUD."""
from __future__ import annotations
from typing import Optional
from core.database import db_cursor
from core.security import generate_id


def list_clusters(ws_id: str) -> list[dict]:
    with db_cursor() as cur:
        cur.execute(
            """SELECT c.id, c.workspace_id, c.name, c.color,
                      c.created_at, c.updated_at,
                      COUNT(n.id) FILTER (WHERE n.status = 'active') AS node_count
               FROM node_clusters c
               LEFT JOIN memory_nodes n ON n.cluster_id = c.id
               WHERE c.workspace_id = %s
               GROUP BY c.id
               ORDER BY c.name""",
            (ws_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_or_create_cluster(cur, ws_id: str, name: str, color: str = "blue") -> str:
    """Find an existing cluster by name (case-insensitive) or create a new one. Returns cluster id."""
    cur.execute(
        """SELECT id FROM node_clusters
           WHERE workspace_id = %s AND lower(name) = lower(%s)
           LIMIT 1""",
        (ws_id, name),
    )
    row = cur.fetchone()
    if row:
        return row["id"]
    cluster_id = generate_id("cl")
    cur.execute(
        """INSERT INTO node_clusters (id, workspace_id, name, color)
           VALUES (%s, %s, %s, %s)""",
        (cluster_id, ws_id, name, color),
    )
    return cluster_id


def update_cluster(ws_id: str, cluster_id: str, data: dict) -> dict:
    allowed = {"name", "color"}
    fields = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        raise ValueError("No valid fields to update")
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [ws_id, cluster_id]
    with db_cursor(commit=True) as cur:
        cur.execute(
            f"UPDATE node_clusters SET {set_clause}, updated_at = now() "
            f"WHERE workspace_id = %s AND id = %s RETURNING *",
            values,
        )
        row = cur.fetchone()
        if not row:
            raise ValueError("Cluster not found")
        return dict(row)


def delete_cluster(ws_id: str, cluster_id: str) -> None:
    """Delete cluster; nodes with this cluster_id become unassigned (FK ON DELETE SET NULL)."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM node_clusters WHERE workspace_id = %s AND id = %s",
            (ws_id, cluster_id),
        )


def fetch_clusters_for_prompt(ws_id: str) -> list[dict]:
    """Return minimal cluster list for injection into the AI extraction prompt."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, name FROM node_clusters WHERE workspace_id = %s ORDER BY name",
            (ws_id,),
        )
        return [dict(r) for r in cur.fetchall()]
