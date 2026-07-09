"""
p0b_dedup_symmetric_edges.py — one-off cleanup for P0b.

Symmetric relations (related_to / similar_to) carry no direction, but were
historically stored in both directions (a->b and b->a). P0 stops new reverse
duplicates at write time (services/edges.py); this script collapses the
existing ones.

For each bidirectional pair {x, y} (x < y) of a symmetric relation it keeps the
canonical edge (from_id < to_id) and deletes the reverse edge (from_id > to_id),
first merging the reverse edge's accumulated signal into the survivor:
  weight          -> max(survivor, reverse)
  traversal_count -> sum
  co_access_count -> sum
  rating_sum/count-> sum
  pinned          -> OR

Deletions are tombstoned (services.tombstones.record_edge_tombstone), matching
delete_edge_in_db's audit convention. Reverse rows are backed up to
_p0b_backup_reverse_dup_edges before deletion.

Usage (inside an image that has the app on PYTHONPATH, DATABASE_URL set):
    python scripts/p0b_dedup_symmetric_edges.py            # dry-run
    python scripts/p0b_dedup_symmetric_edges.py --execute  # apply
"""
from __future__ import annotations

import argparse

from core.constants import SYMMETRIC_RELATIONS
from core.database import db_cursor
from services.tombstones import record_edge_tombstone

# Reverse (to-be-deleted) edges: a symmetric-relation edge stored non-canonically
# (from_id > to_id) whose canonical mirror is also present and active.
REVERSE_DUP_SQL = """
SELECT r.*
FROM edges r
WHERE r.relation::text = ANY(%(rels)s)
  AND r.status = 'active'
  AND r.from_id > r.to_id
  AND EXISTS (
    SELECT 1 FROM edges s
    WHERE s.workspace_id = r.workspace_id
      AND s.from_id = r.to_id
      AND s.to_id = r.from_id
      AND s.relation = r.relation
      AND s.status = 'active'
  )
ORDER BY r.workspace_id, r.relation
"""

MERGE_SURVIVOR_SQL = """
UPDATE edges s SET
    weight          = GREATEST(s.weight, %(w)s),
    traversal_count = s.traversal_count + %(tc)s,
    co_access_count = s.co_access_count + %(cc)s,
    rating_sum      = s.rating_sum + %(rs)s,
    rating_count    = s.rating_count + %(rc)s,
    pinned          = s.pinned OR %(pin)s
WHERE s.workspace_id = %(ws)s
  AND s.from_id = %(sfrom)s
  AND s.to_id = %(sto)s
  AND s.relation = %(rel)s
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="apply changes (default: dry-run)")
    args = ap.parse_args()

    rels = sorted(SYMMETRIC_RELATIONS)

    with db_cursor(commit=args.execute) as cur:
        cur.execute(REVERSE_DUP_SQL, {"rels": rels})
        reverse_edges = [dict(r) for r in cur.fetchall()]

        by_key: dict[tuple[str, str], int] = {}
        for r in reverse_edges:
            k = (r["workspace_id"], r["relation"])
            by_key[k] = by_key.get(k, 0) + 1

        print(f"[{'EXECUTE' if args.execute else 'DRY-RUN'}] reverse-duplicate edges to remove: {len(reverse_edges)}")
        for (ws, rel), n in sorted(by_key.items()):
            print(f"  {ws:14s} {rel:12s} {n}")

        if not reverse_edges:
            print("nothing to do.")
            return

        if not args.execute:
            print("\nsample (first 5):")
            for r in reverse_edges[:5]:
                print(f"  {r['id']} {r['from_id']} -> {r['to_id']} [{r['relation']}] w={r['weight']}")
            print("\nre-run with --execute to apply.")
            return

        # Back up the rows we are about to delete (idempotent create).
        cur.execute(
            "CREATE TABLE IF NOT EXISTS _p0b_backup_reverse_dup_edges "
            "(LIKE edges INCLUDING DEFAULTS)"
        )
        removed = 0
        for r in reverse_edges:
            cur.execute(
                "INSERT INTO _p0b_backup_reverse_dup_edges SELECT * FROM edges WHERE id = %s",
                (r["id"],),
            )
            # Merge signal into the canonical survivor (from_id/to_id swapped).
            cur.execute(MERGE_SURVIVOR_SQL, {
                "w": r["weight"], "tc": r["traversal_count"], "cc": r["co_access_count"],
                "rs": r["rating_sum"], "rc": r["rating_count"], "pin": r["pinned"],
                "ws": r["workspace_id"], "sfrom": r["to_id"], "sto": r["from_id"], "rel": r["relation"],
            })
            record_edge_tombstone(
                cur, r["workspace_id"], r,
                deleted_by="system", reason_category="duplicate",
                reason_note="P0b: symmetric reverse-duplicate collapsed into canonical edge",
            )
            cur.execute(
                "DELETE FROM edges WHERE id = %s AND workspace_id = %s",
                (r["id"], r["workspace_id"]),
            )
            removed += 1

        # Verify no bidirectional pairs remain.
        cur.execute(
            "SELECT count(*) AS n FROM edges r WHERE r.relation::text = ANY(%(rels)s) AND r.status='active' "
            "AND EXISTS (SELECT 1 FROM edges s WHERE s.workspace_id=r.workspace_id "
            "AND s.from_id=r.to_id AND s.to_id=r.from_id AND s.relation=r.relation AND s.status='active')",
            {"rels": rels},
        )
        remaining = cur.fetchone()["n"]
        print(f"\nremoved {removed} reverse edges; remaining bidirectional edges: {remaining}")
        if remaining != 0:
            raise SystemExit(f"expected 0 remaining, got {remaining} — rolled back")


if __name__ == "__main__":
    main()
