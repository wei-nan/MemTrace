"""
scripts/phase6/__main__.py — Phase 6 migration CLI entry point.

Usage:
    python -m scripts.phase6 <command> [options]

Commands:
    classify-bilingual   Analyse every workspace and classify as zh/en/bilingual/mixed.
    split-bilingual      Execute the bilingual workspace split (requires classify first).
    consolidate-fields   Merge title_zh/title_en → title and workspaces.name_zh/en → name.
    migrate-source-docs  Move source_document nodes into the documents table.
    audit                Run the full Stage-2 integrity audit.

Options (all commands):
    --dry-run            Print plan without writing any data.
    --ws-id <id>         Restrict operation to a single workspace.
    --verbose            Print every row being processed.
"""
import argparse
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("phase6")


def main():
    parser = argparse.ArgumentParser(
        prog="python -m scripts.phase6",
        description="Phase 6 migration toolkit",
    )
    parser.add_argument("--version", action="version", version="phase6-migration 1.0.0")
    
    sub = parser.add_subparsers(dest="command", required=True)

    # ── Shared options factory ──────────────────────────────────────────────
    def add_common_args(p: argparse.ArgumentParser):
        p.add_argument("--dry-run",  action="store_true", help="Print plan; do not write data")
        p.add_argument("--ws-id",    metavar="ID",        help="Restrict to a single workspace")
        p.add_argument("--verbose",  action="store_true", help="Print every row being processed")
        return p

    # ── classify-bilingual ──────────────────────────────────────────────────
    p_cls = sub.add_parser(
        "classify-bilingual",
        help="Classify workspaces as zh / en / bilingual / mixed",
    )
    add_common_args(p_cls)

    # ── split-bilingual ──────────────────────────────────────────────────────
    p_spl = sub.add_parser(
        "split-bilingual",
        help="Split bilingual/mixed workspaces into two mono-language workspaces",
    )
    add_common_args(p_spl)

    # ── consolidate-fields ───────────────────────────────────────────────────
    p_con = sub.add_parser(
        "consolidate-fields",
        help="Merge title_zh/title_en → title, name_zh/name_en → name",
    )
    add_common_args(p_con)

    # ── migrate-source-docs ──────────────────────────────────────────────────
    p_msd = sub.add_parser(
        "migrate-source-docs",
        help="Move source_document nodes into the documents table",
    )
    add_common_args(p_msd)

    # ── audit ────────────────────────────────────────────────────────────────
    p_aud = sub.add_parser(
        "audit",
        help="Run the Stage-2 integrity audit (M5 + M7 checks)",
    )
    add_common_args(p_aud)
    p_aud.add_argument(
        "--output", metavar="PATH",
        help="Write audit report JSON to this path (default: stdout)",
    )

    args = parser.parse_args()

    # ── Dispatch ─────────────────────────────────────────────────────────────
    if args.command == "classify-bilingual":
        from scripts.phase6.classify_bilingual import run
        run(dry_run=args.dry_run, ws_id=args.ws_id, verbose=args.verbose)

    elif args.command == "split-bilingual":
        from scripts.phase6.split_bilingual import run
        run(dry_run=args.dry_run, ws_id=args.ws_id, verbose=args.verbose)

    elif args.command == "consolidate-fields":
        from scripts.phase6.consolidate_fields import run
        run(dry_run=args.dry_run, ws_id=args.ws_id, verbose=args.verbose)

    elif args.command == "migrate-source-docs":
        from scripts.phase6.migrate_source_docs import run
        run(dry_run=args.dry_run, ws_id=args.ws_id, verbose=args.verbose)

    elif args.command == "audit":
        from scripts.phase6.audit import run
        output_path = getattr(args, "output", None)
        passed = run(
            dry_run=args.dry_run,
            ws_id=args.ws_id,
            verbose=args.verbose,
            output_path=output_path,
        )
        sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
