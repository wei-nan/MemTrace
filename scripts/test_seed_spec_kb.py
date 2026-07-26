"""Tests for the seed_spec_kb comparison logic.

Runs on the host, not in the API container — the repo-root scripts/ directory is
outside the container's build context (which is packages/api).

    python3 -m pytest scripts/test_seed_spec_kb.py -q

Only the pure comparison helpers are covered. They decide whether --check-live
reports a clean result, so a wrong classification here would produce a false
"OK" — worse than having no drift detector at all.
"""

import inspect
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from seed_spec_kb import _field_mismatches, _preview, _seed_declared, _live_declared, _node_sql, upsert_nodes


def test_node_sql_never_writes_computed_fields_on_conflict():
    """Regression guard: _node_sql() generates the committed migration SQL
    (packages/api/migrations/003_seed_spec_kb.sql), applied manually per
    docs/DEPLOYMENT.md — it is not in MANIFEST.txt and run_migrations() does
    not execute it. This is a separate code path from upsert_nodes().
    trust_score/dim_* are computed live; a seed upsert must never overwrite
    them on conflict. See ws_spec_plan/mem_82155065, mem_be783548, mem_cbac2be0."""
    node = {
        "id": "mem_x", "title": "T",
        "content": {"type": "factual", "format": "markdown", "body": "B"},
        "tags": [], "visibility": "public",
        "provenance": {"author": "system", "source_type": "human"},
    }
    sql = "\n".join(_node_sql(node, "ws_spec0001"))
    set_clause = sql.split("DO UPDATE SET")[1]
    for forbidden in ("trust_score", "dim_accuracy", "dim_freshness", "dim_utility", "dim_author_rep", "status"):
        assert forbidden not in set_clause, f"_node_sql() DO UPDATE SET must not touch {forbidden}"


def test_upsert_nodes_never_writes_computed_fields_on_conflict():
    """Same guard for upsert_nodes(), the live-DB-write path used by main().

    status is a second, subtler regression: `status = EXCLUDED.status` looks
    like an ordinary upsert pattern but resolves to the column's DEFAULT
    ('active') because status is never in the INSERT's column list — silently
    re-activating archived nodes on every seed run, identical in effect to
    the literal `status = 'active'` this project already removed once."""
    sql = inspect.getsource(upsert_nodes)
    set_clause = sql.split("DO UPDATE SET")[1].split('"""')[0]
    for forbidden in ("trust_score", "dim_accuracy", "dim_freshness", "dim_utility", "dim_author_rep", "status"):
        assert forbidden not in set_clause, f"upsert_nodes() DO UPDATE SET must not touch {forbidden}"


def seed_node(**over):
    n = {
        "id": "mem_x",
        "title": "T",
        "content": {"type": "factual", "format": "markdown", "body": "B"},
        "tags": ["a", "b"],
        "visibility": "public",
    }
    n.update(over)
    return n


def live_row(**over):
    r = {
        "id": "mem_x",
        "title": "T",
        "content_type": "factual",
        "content_format": "markdown",
        "body": "B",
        "tags": ["a", "b"],
        "visibility": "public",
        "status": "active",
    }
    r.update(over)
    return r


def test_identical_nodes_report_nothing():
    assert _field_mismatches({"mem_x": seed_node()}, {"mem_x": live_row()}) == []


def test_tag_order_is_not_drift():
    """Tag order carries no meaning; reporting it would be noise."""
    assert _field_mismatches(
        {"mem_x": seed_node(tags=["b", "a"])}, {"mem_x": live_row(tags=["a", "b"])}
    ) == []


def test_trailing_newline_is_warn_not_drift():
    """The write path trims trailing whitespace, so this is a seed-file artifact."""
    out = _field_mismatches(
        {"mem_x": seed_node(content={"type": "factual", "format": "markdown", "body": "B\n"})},
        {"mem_x": live_row(body="B")},
    )
    assert out == [("mem_x", "body", "WARN")]


def test_real_body_change_is_drift():
    out = _field_mismatches(
        {"mem_x": seed_node(content={"type": "factual", "format": "markdown", "body": "B"})},
        {"mem_x": live_row(body="something else")},
    )
    assert out == [("mem_x", "body", "DRIFT")]


def test_每個_declared_欄位都被比對():
    """A field silently dropped from the comparison is the dangerous failure."""
    cases = {
        "title": (seed_node(title="A"), live_row(title="Z")),
        "visibility": (seed_node(visibility="public"), live_row(visibility="private")),
        "content_type": (
            seed_node(content={"type": "factual", "format": "markdown", "body": "B"}),
            live_row(content_type="procedural"),
        ),
        "content_format": (
            seed_node(content={"type": "factual", "format": "markdown", "body": "B"}),
            live_row(content_format="plain"),
        ),
        "tags": (seed_node(tags=["a"]), live_row(tags=["z"])),
    }
    for field, (s, l) in cases.items():
        out = _field_mismatches({"mem_x": s}, {"mem_x": l})
        assert out == [("mem_x", field, "DRIFT")], f"{field} was not compared"


def test_computed_fields_are_never_compared():
    """trust_score and friends are computed live; diffing them is permanent noise."""
    s, l = _seed_declared(seed_node()), _live_declared(live_row())
    for f in ("trust_score", "dim_accuracy", "dim_freshness", "version", "updated_at"):
        assert f not in s
        assert f not in l


def test_preview_truncates_and_counts():
    assert _preview(["a", "b"], n=8) == "a, b"
    assert _preview([str(i) for i in range(10)], n=8).endswith("…(+2)")
