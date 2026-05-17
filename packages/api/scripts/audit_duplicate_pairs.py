"""
scripts/audit_duplicate_pairs.py ? M4 ????????

?????
  snapshot_kb_health() ???? cosine pairwise SQL??????????
  ???????????????????????
    1. ???? cosine >= 0.80 ?????????/????
    2. ? cosine >= 0.85 ???????
    3. --fix ??????? similar_to edge
    4. ???? kb_health_daily.duplicate_pairs_unlinked

???
  python packages/api/scripts/audit_duplicate_pairs.py
  python packages/api/scripts/audit_duplicate_pairs.py --fix
  python packages/api/scripts/audit_duplicate_pairs.py --threshold 0.82 --workspace ws_spec0001
"""
from __future__ import annotations

import sys
import os
import json
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from dotenv import load_dotenv
load_dotenv(".env")

from core.database import db_cursor
from core.security import generate_id

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("audit_pairs")

REPORTS_DIR = Path("reports")


def run_audit(workspace_id: str, threshold: float, fix: bool, verbose: bool):
    REPORTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    print(f"\n=== Duplicate Pair Audit ===")
    print(f"Workspace : {workspace_id}")
    print(f"Threshold : cosine >= {threshold}")
    print(f"Fix mode  : {'YES -- will create missing similar_to edges' if fix else 'NO (dry-run)'}")

    with db_cursor(commit=fix) as cur:
        # -- Step 1: count embeddings -----------------------------------------
        cur.execute("""
            SELECT COUNT(*) as total,
                   COUNT(embedding) as with_embed
            FROM memory_nodes
            WHERE workspace_id = %s AND status = 'active'
        """, (workspace_id,))
        r = cur.fetchone()
        total_nodes = r["total"]
        nodes_with_embed = r["with_embed"]
        print(f"\nActive nodes  : {total_nodes}")
        print(f"With embedding: {nodes_with_embed}")
        if nodes_with_embed < 2:
            print("Not enough nodes with embeddings to compare.")
            return

        # -- Step 2: find all pairs above lower threshold (0.80) -------------
        # Using pgvector <=> operator (cosine distance = 1 - cosine_similarity)
        print(f"\nRunning pairwise cosine scan (this may take a moment)...")
        cur.execute("""
            SELECT
                a.id          AS id_a,
                b.id          AS id_b,
                a.title_en    AS title_a,
                b.title_en    AS title_b,
                ROUND(CAST(1 - (a.embedding <=> b.embedding) AS numeric), 4) AS cosine,
                EXISTS (
                    SELECT 1 FROM edges e
                    WHERE e.relation = 'similar_to'
                      AND e.status   = 'active'
                      AND (
                          (e.from_id = a.id AND e.to_id = b.id)
                       OR (e.from_id = b.id AND e.to_id = a.id)
                      )
                ) AS has_edge
            FROM memory_nodes a
            JOIN memory_nodes b
              ON a.workspace_id = b.workspace_id
             AND a.id < b.id
             AND a.status = 'active'
             AND b.status = 'active'
             AND a.embedding IS NOT NULL
             AND b.embedding IS NOT NULL
             AND 1 - (a.embedding <=> b.embedding) >= %s
            WHERE a.workspace_id = %s
            ORDER BY cosine DESC
        """, (threshold, workspace_id))
        pairs = cur.fetchall()

        all_pairs       = [dict(p) for p in pairs]
        linked_pairs    = [p for p in all_pairs if p["has_edge"]]
        unlinked_high   = [p for p in all_pairs if not p["has_edge"] and float(p["cosine"]) >= 0.85]
        unlinked_low    = [p for p in all_pairs if not p["has_edge"] and float(p["cosine"]) < 0.85]

        # -- Step 3: print results --------------------------------------------
        print(f"\n{'-'*60}")
        print(f"Pairs >= {threshold:.2f}  : {len(all_pairs):>4}")
        print(f"  Already linked  : {len(linked_pairs):>4}  (similar_to edge exists)")
        print(f"  Unlinked >= 0.85 : {len(unlinked_high):>4}  <- M4 target (should be 0)")
        print(f"  Unlinked < 0.85 : {len(unlinked_low):>4}  (informational)")
        print(f"{'-'*60}")

        if verbose or unlinked_high:
            print(f"\n{'COSINE':>7}  {'EDGE?':>5}  PAIR")
            print("-" * 60)
            for p in all_pairs:
                linked_str = "Y" if p["has_edge"] else ("! MISSING" if float(p["cosine"]) >= 0.85 else ".")
                ta = (p["title_a"] or p["id_a"])[:30]
                tb = (p["title_b"] or p["id_b"])[:30]
                print(f"  {p['cosine']:>5}  {linked_str:<9}  {ta} <-> {tb}")

        # -- Step 4: fix if requested -----------------------------------------
        edges_created = 0
        if fix and unlinked_high:
            print(f"\n[FIX] Creating {len(unlinked_high)} missing similar_to edges...")
            for p in unlinked_high:
                edge_id = generate_id("edge")
                cur.execute("""
                    INSERT INTO edges
                        (id, workspace_id, from_id, to_id, relation, weight,
                         half_life_days, min_weight, status, pinned, source_type)
                    VALUES
                        (%s, %s, %s, %s, 'similar_to', 0.85,
                         90, 0.1, 'active', false, 'system')
                    ON CONFLICT DO NOTHING
                """, (edge_id, workspace_id, p["id_a"], p["id_b"]))
                if cur.rowcount:
                    edges_created += 1
                    print(f"  Created {edge_id}: {p['id_a'][:12]} <-> {p['id_b'][:12]}  (cosine={p['cosine']})")
            print(f"  Done. {edges_created} edge(s) created.")

        # -- Step 5: update kb_health_daily ----------------------------------
        unlinked_count = len(unlinked_high) - edges_created  # after fix
        cur.execute("""
            UPDATE kb_health_daily
            SET duplicate_pairs_unlinked = %s
            WHERE workspace_id = %s
              AND date = (
                  SELECT MAX(date) FROM kb_health_daily WHERE workspace_id = %s
              )
        """, (unlinked_count, workspace_id, workspace_id))
        if cur.rowcount:
            print(f"\n[DB] Updated kb_health_daily.duplicate_pairs_unlinked = {unlinked_count}")

        # -- Step 6: write report ---------------------------------------------
        report = {
            "timestamp": ts,
            "workspace_id": workspace_id,
            "threshold": threshold,
            "total_active_nodes": total_nodes,
            "nodes_with_embedding": nodes_with_embed,
            "total_pairs_scanned": len(all_pairs),
            "linked_pairs": len(linked_pairs),
            "unlinked_high_cosine": len(unlinked_high),
            "unlinked_low_cosine": len(unlinked_low),
            "edges_created_by_fix": edges_created,
            "m4_status": "PASS" if (len(unlinked_high) - edges_created) == 0 else "FAIL",
            "pairs": all_pairs,
        }
        report_path = REPORTS_DIR / f"audit_pairs_{ts}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        # -- Final verdict ----------------------------------------------------
        print(f"\n{'='*55}")
        print(f"M4 VERDICT: {'[PASS] no unlinked high-cosine pairs' if unlinked_count == 0 else f'[FAIL] {unlinked_count} pair(s) unlinked (run with --fix to repair)'}")
        print(f"Report: {report_path}")
        print(f"{'='*55}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit near-duplicate node pairs in a MemTrace workspace")
    parser.add_argument("--workspace",  default="ws_spec0001", help="Workspace ID")
    parser.add_argument("--threshold",  type=float, default=0.80,
                        help="Lower cosine bound for scan (default: 0.80). Alert threshold is always 0.85.")
    parser.add_argument("--fix",        action="store_true",
                        help="Create missing similar_to edges for pairs with cosine >= 0.85")
    parser.add_argument("--verbose",    action="store_true",
                        help="Show all pairs, not just unlinked ones")
    args = parser.parse_args()

    run_audit(
        workspace_id=args.workspace,
        threshold=args.threshold,
        fix=args.fix,
        verbose=args.verbose,
    )
