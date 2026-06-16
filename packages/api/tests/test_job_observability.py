from __future__ import annotations

from unittest.mock import MagicMock

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
