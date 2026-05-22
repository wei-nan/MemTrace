"""
scripts/phase6/classify_bilingual.py — S2-T05: Workspace bilingual classification.

Analyses every workspace to determine its language composition:
  - zh   : ≥95% of nodes have substantive zh content, <5% en
  - en   : <5% zh, ≥95% en
  - bilingual : ≥50% zh AND ≥50% en
  - mixed     : anything else

Results are stored in _migration_classification_v6 table.

Usage (via CLI):
    python -m scripts.phase6 classify-bilingual [--dry-run] [--ws-id <id>]
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Constants ─────────────────────────────────────────────────────────────────

ZH_RANGES = [(ord("一"), ord("鿿")), (ord("㐀"), ord("㿿")), (ord("丽"), ord("𯨟"))]


def _contains_cjk(text: str) -> bool:
    """Return True if text contains at least one CJK character."""
    return any(
        lo <= ord(c) <= hi
        for c in text
        for lo, hi in ZH_RANGES
    )


def is_substantive(title: str, body: str, other_title: str = "") -> bool:
    """
    A field is 'substantive' if:
    - It has at least 3 non-whitespace characters
    - It is NOT a simple copy of the other language's title (fallback detection)
    """
    text = (title or "").strip()
    if len(text) < 3:
        return False
    # Fallback detection: if title equals the other language's title, treat as non-substantive
    if other_title and text.lower() == (other_title or "").strip().lower():
        return False
    return True


def classify_workspace(cur, ws_id: str) -> dict:
    """
    Classify a single workspace and return a classification dict.
    """
    cur.execute(
        "SELECT count(*) AS cnt FROM memory_nodes WHERE workspace_id = %s AND status = 'active'",
        (ws_id,),
    )
    total = cur.fetchone()["cnt"]
    if total == 0:
        return {
            "workspace_id": ws_id,
            "category": "zh",  # empty workspace — default to zh until owner decides
            "zh_ratio": 0.0,
            "en_ratio": 0.0,
            "node_count": 0,
            "mixed_node_ids": [],
        }

    cur.execute(
        """
        SELECT id, title_zh, title_en, body_zh, body_en
        FROM memory_nodes
        WHERE workspace_id = %s AND status = 'active'
        """,
        (ws_id,),
    )
    rows = cur.fetchall()

    zh_substantive = 0
    en_substantive = 0
    mixed_node_ids = []

    for row in rows:
        zh_ok = is_substantive(row["title_zh"], row["body_zh"], row["title_en"])
        en_ok = is_substantive(row["title_en"], row["body_en"], row["title_zh"])

        if zh_ok:
            zh_substantive += 1
        if en_ok:
            en_substantive += 1
        if zh_ok and en_ok:
            mixed_node_ids.append(row["id"])

    zh_ratio = zh_substantive / total
    en_ratio  = en_substantive / total

    if zh_ratio >= 0.95 and en_ratio < 0.05:
        category = "zh"
    elif en_ratio >= 0.95 and zh_ratio < 0.05:
        category = "en"
    elif zh_ratio >= 0.5 and en_ratio >= 0.5:
        category = "bilingual"
    else:
        category = "mixed"

    return {
        "workspace_id": ws_id,
        "category": category,
        "zh_ratio": round(zh_ratio, 4),
        "en_ratio": round(en_ratio, 4),
        "node_count": total,
        "mixed_node_ids": mixed_node_ids[:100],  # cap at 100 for storage
    }


def _ensure_classification_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS _migration_classification_v6 (
            workspace_id   TEXT PRIMARY KEY,
            category       TEXT NOT NULL,    -- 'zh' | 'en' | 'bilingual' | 'mixed'
            zh_ratio       FLOAT,
            en_ratio       FLOAT,
            node_count     INT,
            mixed_node_ids TEXT[],
            classified_at  TIMESTAMPTZ DEFAULT now()
        )
    """)


def run(
    dry_run: bool = False,
    ws_id: Optional[str] = None,
    verbose: bool = False,
):
    """Main entry point for classify-bilingual command."""
    from core.database import db_cursor
    import json

    with db_cursor(commit=not dry_run) as cur:
        _ensure_classification_table(cur)

        # Fetch workspaces to classify
        if ws_id:
            cur.execute("SELECT id FROM workspaces WHERE id = %s", (ws_id,))
        else:
            cur.execute("SELECT id FROM workspaces ORDER BY created_at")
        ws_rows = cur.fetchall()

        logger.info("Classifying %d workspace(s)%s...", len(ws_rows), " (dry-run)" if dry_run else "")

        counts = {"zh": 0, "en": 0, "bilingual": 0, "mixed": 0}
        for ws_row in ws_rows:
            wid = ws_row["id"]
            result = classify_workspace(cur, wid)
            counts[result["category"]] += 1

            if verbose:
                logger.info(
                    "  ws=%s  category=%-10s  zh=%.1f%%  en=%.1f%%  nodes=%d",
                    wid, result["category"],
                    result["zh_ratio"] * 100, result["en_ratio"] * 100,
                    result["node_count"],
                )

            if not dry_run:
                cur.execute(
                    """
                    INSERT INTO _migration_classification_v6
                        (workspace_id, category, zh_ratio, en_ratio, node_count, mixed_node_ids)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (workspace_id) DO UPDATE SET
                        category       = EXCLUDED.category,
                        zh_ratio       = EXCLUDED.zh_ratio,
                        en_ratio       = EXCLUDED.en_ratio,
                        node_count     = EXCLUDED.node_count,
                        mixed_node_ids = EXCLUDED.mixed_node_ids,
                        classified_at  = now()
                    """,
                    (
                        result["workspace_id"],
                        result["category"],
                        result["zh_ratio"],
                        result["en_ratio"],
                        result["node_count"],
                        result["mixed_node_ids"],
                    ),
                )

    logger.info(
        "Classification complete: zh=%d  en=%d  bilingual=%d  mixed=%d",
        counts["zh"], counts["en"], counts["bilingual"], counts["mixed"],
    )
    if dry_run:
        logger.info("[DRY-RUN] No data written.")
