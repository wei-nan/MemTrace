from __future__ import annotations

import os
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "test-secret-for-job-observability-tests-0001")

from services.job_observability import _duration_ms, list_job_runs, list_scheduler_heartbeats


def test_duration_ms_never_negative():
    assert _duration_ms(10.0, 10.25) == 250
    assert _duration_ms(10.25, 10.0) == 0
    assert _duration_ms(None, 10.0) is None


def test_list_job_runs_filters_workspace_and_returns_rows():
    cur = MagicMock()
    cur.fetchall.return_value = [
        {"id": "jobrun_1", "job_name": "audit_reviewers", "workspace_id": "ws_1"}
    ]

    rows = list_job_runs(
        cur,
        workspace_id="ws_1",
        job_name="audit_reviewers",
        status="success",
        limit=25,
        offset=5,
    )

    assert rows[0]["id"] == "jobrun_1"
    sql, params = cur.execute.call_args.args
    assert "workspace_id = %s" in sql
    assert "job_name = %s" in sql
    assert "status = %s" in sql
    assert params == ["ws_1", "audit_reviewers", "success", 25, 5]


def test_list_scheduler_heartbeats_returns_rows():
    cur = MagicMock()
    cur.fetchall.return_value = [{"job_name": "process_node_events", "status": "success"}]

    rows = list_scheduler_heartbeats(cur)

    assert rows == [{"job_name": "process_node_events", "status": "success"}]
    assert "scheduler_heartbeats" in cur.execute.call_args.args[0]


def test_system_monitor_job_runs_reviewer_filter_matches_job_name_and_summary(monkeypatch):
    from routers import admin

    cur = MagicMock()
    cur.fetchall.return_value = [
        {"id": "jobrun_1", "job_name": "audit_reviewers", "status": "success"}
    ]
    cur.fetchone.return_value = {"cnt": 1}
    monkeypatch.setattr(admin, "db_cursor", lambda: MagicMock(
        __enter__=lambda _: cur,
        __exit__=lambda *_: None,
    ))

    res = admin.get_monitor_job_runs(
        status=None,
        reviewer="safety_review",
        limit=25,
        offset=5,
        user={"sub": "admin"},
    )

    assert res["total"] == 1
    first_sql, first_params = cur.execute.call_args_list[0].args
    assert "jr.job_name = %s" in first_sql
    assert "audit_reviewers:%s" not in first_sql
    assert "jr.summary->'reviewers'" in first_sql
    assert "jr.summary->>'reviewer_id'" in first_sql
    assert first_params == [
        "safety_review",
        "audit_reviewers:safety_review",
        "safety_review",
        "safety_review",
        "safety_review",
        25,
        5,
    ]


def test_cleanup_job_purges_job_runs_by_configured_retention(monkeypatch):
    import pytest
    from jobs import cleanup

    cur = MagicMock()
    cur.fetchall.return_value = []
    monkeypatch.setattr(cleanup.settings, "job_runs_retention_days", 42)
    monkeypatch.setattr(cleanup.settings, "ai_usage_retention_months", 6)
    monkeypatch.setattr(cleanup, "db_cursor", lambda commit=False: MagicMock(
        __enter__=lambda _: cur,
        __exit__=lambda *_: None,
    ))

    pytest.importorskip("pytest_asyncio")

    import asyncio
    asyncio.run(cleanup.cleanup_job())

    calls = [call.args for call in cur.execute.call_args_list]
    assert any(
        len(args) == 2
        and args[0] == "DELETE FROM job_runs WHERE started_at < NOW() - (%s * INTERVAL '1 day')"
        and args[1] == (42,)
        for args in calls
    )
