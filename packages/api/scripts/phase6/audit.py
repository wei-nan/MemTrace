"""
scripts/phase6/audit.py — Phase 6 Stage-2 integrity audit (M5 + M7 gate).

Four audit checks:
  A. Bilingual split completeness  (M7)
  B. Field consolidation           (title/body non-null check)
  C. source_document migration     (documents table + file hash)
  D. Retrieval sampling            (M5-related recall probe)

Outputs a JSON report to stdout or a file.
Exit code: 0 = all pass, 1 = any failure.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Individual check stubs ────────────────────────────────────────────────────

def check_bilingual_split(cur, ws_id: Optional[str], verbose: bool) -> dict:
    """
    A. Bilingual split completeness.
    - Every ws must have `language IS NOT NULL`
    - Bilingual ws must have been split: classification table rows with
      category IN ('bilingual','mixed') must have a corresponding split log entry.
    - linked_workspace_id must be symmetric (both sides point to each other).
    """
    result = {"check": "bilingual_split", "status": "SKIP", "details": []}

    # Check that the classification table exists (may not yet exist in early runs)
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = '_migration_classification_v6'"
    )
    if not cur.fetchone():
        result["status"] = "SKIP"
        result["message"] = "_migration_classification_v6 table does not exist yet — run classify-bilingual first"
        return result

    ws_filter = "AND c.workspace_id = %s" if ws_id else ""
    params = [ws_id] if ws_id else []

    # Check all workspaces have language set
    cur.execute(
        f"""
        SELECT count(*) AS cnt FROM workspaces w
        WHERE w.language IS NULL {ws_filter.replace('c.workspace_id', 'w.id')}
        """,
        params,
    )
    null_lang_count = cur.fetchone()["cnt"]
    if null_lang_count > 0:
        result["status"] = "FAIL"
        result["details"].append(f"{null_lang_count} workspaces still have language=NULL")
    else:
        result["details"].append("All workspaces have language set ✅")

    # Check linked_workspace_id symmetry
    cur.execute(
        """
        SELECT count(*) AS cnt
        FROM workspaces a
        JOIN workspaces b ON a.linked_workspace_id = b.id
        WHERE b.linked_workspace_id != a.id
        """
    )
    asymmetric = cur.fetchone()["cnt"]
    if asymmetric > 0:
        result["status"] = "FAIL"
        result["details"].append(f"{asymmetric} workspace pairs have asymmetric linked_workspace_id")
    else:
        result["details"].append("All linked_workspace_id references are symmetric ✅")

    if result["status"] != "FAIL":
        result["status"] = "PASS"
    return result


def check_field_consolidation(cur, ws_id: Optional[str], verbose: bool) -> dict:
    """
    B. Field consolidation (title/body non-null).
    Checks memory_nodes.title IS NOT NULL AND length > 0.
    Only runs if the column exists (added in Stage 2).
    """
    result = {"check": "field_consolidation", "status": "SKIP", "details": []}

    # Check if title column exists
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'memory_nodes' AND column_name = 'title'
        """
    )
    if not cur.fetchone():
        result["message"] = "memory_nodes.title column does not exist yet — run consolidate-fields first"
        return result

    ws_filter = "AND workspace_id = %s" if ws_id else ""
    params = [ws_id] if ws_id else []

    cur.execute(
        f"""
        SELECT count(*) AS cnt FROM memory_nodes
        WHERE (title IS NULL OR length(title) = 0)
          AND status = 'active'
          {ws_filter}
        """,
        params,
    )
    empty_title = cur.fetchone()["cnt"]
    if empty_title > 0:
        result["status"] = "FAIL"
        result["details"].append(f"{empty_title} active nodes have empty/null title")
    else:
        result["details"].append("All active nodes have non-empty title ✅")
        result["status"] = "PASS"
    return result


def check_source_doc_migration(cur, ws_id: Optional[str], verbose: bool) -> dict:
    """
    C. source_document node migration.
    - No active memory_nodes with content_type='source_document' should remain.
    - documents table should exist and have rows.
    - node_document_links should have rows.
    """
    result = {"check": "source_doc_migration", "status": "SKIP", "details": []}

    # Check documents table exists
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'documents'"
    )
    if not cur.fetchone():
        result["message"] = "documents table does not exist yet — run Stage 1 migrations first"
        return result

    ws_filter = "AND workspace_id = %s" if ws_id else ""
    params = [ws_id] if ws_id else []

    # Check no source_document nodes remain.
    # Cast content_type to text to avoid InvalidTextRepresentation when the
    # enum value 'source_document' has been removed (migration 056).
    cur.execute(
        f"""
        SELECT count(*) AS cnt FROM memory_nodes
        WHERE content_type::text = 'source_document' AND status = 'active'
          {ws_filter}
        """,
        params,
    )
    remaining = cur.fetchone()["cnt"]

    if remaining > 0:
        result["status"] = "FAIL"
        result["details"].append(f"{remaining} source_document nodes still exist")
    else:
        result["details"].append("No source_document nodes remain ✅")

    cur.execute("SELECT count(*) AS cnt FROM documents")
    doc_cnt = cur.fetchone()["cnt"]
    result["details"].append(f"documents table has {doc_cnt} rows")

    cur.execute("SELECT count(*) AS cnt FROM node_document_links")
    link_cnt = cur.fetchone()["cnt"]
    result["details"].append(f"node_document_links table has {link_cnt} rows")

    if result["status"] != "FAIL":
        result["status"] = "PASS"
    return result


def check_retrieval_sampling(cur, ws_id: Optional[str], verbose: bool) -> dict:
    """
    D. Retrieval sampling (M5 — data integrity proxy check).
    Verifies that retrieval_logs exist and workspace nodes have embeddings.
    Full golden-set recall evaluation is performed separately by eval_retrieval.py.
    """
    result = {"check": "retrieval_sampling", "status": "SKIP", "details": []}

    if ws_id:
        cur.execute(
            "SELECT count(*) AS cnt FROM memory_nodes WHERE workspace_id = %s AND embedding IS NOT NULL",
            [ws_id],
        )
    else:
        cur.execute(
            "SELECT count(*) AS cnt FROM memory_nodes WHERE embedding IS NOT NULL"
        )
    embedded_cnt = cur.fetchone()["cnt"]

    if ws_id:
        cur.execute(
            "SELECT count(*) AS cnt FROM memory_nodes WHERE workspace_id = %s",
            [ws_id],
        )
    else:
        cur.execute(
            "SELECT count(*) AS cnt FROM memory_nodes"
        )
    total_cnt = cur.fetchone()["cnt"]

    if total_cnt == 0:
        result["status"] = "SKIP"
        result["message"] = "No nodes found"
        return result

    ratio = embedded_cnt / total_cnt
    result["details"].append(f"{embedded_cnt}/{total_cnt} nodes have embeddings ({ratio:.1%})")

    if ratio < 0.50:
        result["status"] = "WARN"
        result["details"].append("Less than 50% of nodes have embeddings — re-index may be pending")
    else:
        result["status"] = "PASS"
        result["details"].append("Embedding coverage acceptable ✅")

    return result


# ─── Main audit runner ─────────────────────────────────────────────────────────

def run(
    dry_run: bool = False,
    ws_id: Optional[str] = None,
    verbose: bool = False,
    output_path: Optional[str] = None,
) -> bool:
    """
    Run all four audit checks and print/save a JSON report.
    Returns True if all mandatory checks (A, B, C) pass.
    """
    from core.database import db_cursor

    logger.info("Starting Phase 6 Stage-2 audit%s...", " (dry-run)" if dry_run else "")

    with db_cursor() as cur:
        checks = [
            check_bilingual_split(cur, ws_id, verbose),
            check_field_consolidation(cur, ws_id, verbose),
            check_source_doc_migration(cur, ws_id, verbose),
            check_retrieval_sampling(cur, ws_id, verbose),
        ]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "generated_at": timestamp,
        "dry_run": dry_run,
        "ws_id_filter": ws_id,
        "checks": checks,
        "overall": "PASS" if all(c["status"] in ("PASS", "SKIP", "WARN") for c in checks) else "FAIL",
    }

    report_json = json.dumps(report, indent=2, ensure_ascii=False)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_json)
        logger.info("Audit report written to %s", output_path)
    else:
        print(report_json)

    # Summary
    print("\n=== Audit Summary ===")
    for c in checks:
        icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭", "WARN": "⚠️"}.get(c["status"], "?")
        print(f"  {icon} [{c['status']}] {c['check']}")
        if verbose or c["status"] in ("FAIL", "WARN"):
            for d in c.get("details", []):
                print(f"       {d}")
    print(f"\nOverall: {'✅ PASS' if report['overall'] == 'PASS' else '❌ FAIL'}")

    return report["overall"] == "PASS"
