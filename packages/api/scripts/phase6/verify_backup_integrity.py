"""
scripts/phase6/verify_backup_integrity.py — Phase 6 backup verification tool.

Verifies that the three backup tables (_migration_backup_*_v6) were created
correctly and contain data consistent with the live tables.

Usage:
    python -m scripts.phase6.verify_backup_integrity
"""
import logging
import hashlib
import json
import sys

logger = logging.getLogger(__name__)


def _hash_row(row: dict, keys: list) -> str:
    """Deterministic hash of selected columns from a row."""
    payload = {k: str(row.get(k, "")) for k in sorted(keys)}
    return hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def verify_backup_integrity(sample_size: int = 100) -> bool:
    """
    Returns True if all checks pass, False otherwise.

    Checks:
    1. All three backup tables exist.
    2. Row counts match between backup and live tables.
    3. A sample of `sample_size` rows have identical content in key columns.
    """
    from core.database import db_cursor

    all_ok = True

    tables = [
        ("_migration_backup_workspaces_v6", "workspaces",   ["id", "name_zh", "name_en"]),
        ("_migration_backup_nodes_v6",      "memory_nodes", ["id", "workspace_id", "title_zh", "title_en", "body_zh", "body_en"]),
        ("_migration_backup_edges_v6",      "edges",         ["id", "workspace_id", "from_id", "to_id"]),
    ]

    with db_cursor() as cur:
        for backup_tbl, live_tbl, check_cols in tables:
            # 1. Existence check
            cur.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                (backup_tbl,),
            )
            if not cur.fetchone():
                logger.error("❌ Backup table %s does not exist", backup_tbl)
                all_ok = False
                continue

            # 2. Row count check
            cur.execute(f"SELECT count(*) AS cnt FROM {backup_tbl}")
            bk_cnt = cur.fetchone()["cnt"]
            cur.execute(f"SELECT count(*) AS cnt FROM {live_tbl}")
            live_cnt = cur.fetchone()["cnt"]

            if bk_cnt != live_cnt:
                logger.error(
                    "❌ Row count mismatch for %s: backup=%d live=%d",
                    backup_tbl, bk_cnt, live_cnt,
                )
                all_ok = False
            else:
                logger.info("✅ %s row count matches: %d rows", backup_tbl, bk_cnt)

            # 3. Sample content check
            cur.execute(
                f"SELECT * FROM {live_tbl} ORDER BY id LIMIT %s",
                (sample_size,),
            )
            live_rows = {r["id"]: dict(r) for r in cur.fetchall()}

            cur.execute(
                f"SELECT * FROM {backup_tbl} WHERE id = ANY(%s)",
                (list(live_rows.keys()),),
            )
            bk_rows = {r["id"]: dict(r) for r in cur.fetchall()}

            mismatches = 0
            for rid, live_row in live_rows.items():
                if rid not in bk_rows:
                    logger.warning("⚠️  Row %s missing from %s", rid, backup_tbl)
                    mismatches += 1
                    continue
                live_hash = _hash_row(live_row, [c for c in check_cols if c in live_row])
                bk_hash   = _hash_row(bk_rows[rid], [c for c in check_cols if c in bk_rows[rid]])
                if live_hash != bk_hash:
                    logger.warning(
                        "⚠️  Content mismatch for row %s in %s", rid, backup_tbl
                    )
                    mismatches += 1

            if mismatches == 0:
                logger.info(
                    "✅ %s sample check passed (%d rows matched)", backup_tbl, len(live_rows)
                )
            else:
                logger.error(
                    "❌ %s sample check: %d/%d rows mismatched",
                    backup_tbl, mismatches, len(live_rows),
                )
                all_ok = False

    return all_ok


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ok = verify_backup_integrity()
    print("\n✅ All backup integrity checks passed." if ok else "\n❌ Some checks failed — see above.")
    sys.exit(0 if ok else 1)
