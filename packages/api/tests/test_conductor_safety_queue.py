from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

import services.safety_queue as safety_queue
from services.conductor import (
    _deliver_prepared_deliveries,
    get_node_scale,
    list_deliveries,
    prepare_major_inquiry_hook_deliveries,
    validate_webhook_url,
)
from services.safety_queue import enqueue_safety_review, list_safety_review_queue


def test_get_node_scale_defaults_to_minor_and_accepts_major():
    assert get_node_scale({}) == "minor"
    assert get_node_scale({"metadata": {"scale": "major"}}) == "major"
    assert get_node_scale({"metadata": {"scale": "unexpected"}}) == "minor"
    assert get_node_scale({"metadata": '{"scale": "major"}'}) == "major"


def test_prepare_major_inquiry_hook_deliveries_filters_and_inserts_pending():
    cur = MagicMock()
    cur.fetchone.side_effect = [
        {
            "id": "mem_1",
            "workspace_id": "ws_1",
            "title": "Need design",
            "body": "please investigate",
            "tags": ["agent-loop"],
            "content_type": "inquiry",
            "status": "active",
            "updated_at": "2026-06-16T00:00:00Z",
            "metadata": {"scale": "major"},
        },
        None,
        {"id": "hookd_1"},
    ]
    cur.fetchall.return_value = [
        {
            "id": "hook_1",
            "url": "https://example.test/a",
            "secret": "secret",
            "event_filter": {"scale": "major", "tags": ["agent-loop"]},
        },
        {
            "id": "hook_2",
            "url": "https://example.test/b",
            "secret": None,
            "event_filter": {"tags": ["other"]},
        },
    ]

    result = prepare_major_inquiry_hook_deliveries(cur, "ws_1", "mem_1", "node_event:created")

    assert result["status"] == "processed"
    assert result["pending"] == 1
    assert result["skipped"] == 1
    assert result["_deliveries"][0]["id"].startswith("hookd_")
    assert result["_deliveries"][0]["payload"]["event"] == "major_inquiry"


def test_prepare_major_inquiry_hook_deliveries_skips_minor_or_non_inquiry():
    cur = MagicMock()
    cur.fetchone.return_value = {
        "id": "mem_1",
        "workspace_id": "ws_1",
        "title": "Small note",
        "body": "body",
        "tags": [],
        "content_type": "factual",
        "status": "active",
        "updated_at": "2026-06-16T00:00:00Z",
        "metadata": {"scale": "major"},
    }

    result = prepare_major_inquiry_hook_deliveries(cur, "ws_1", "mem_1", "node_event:updated")

    assert result == {"status": "skipped", "reason": "not_major_inquiry", "scale": "major"}
    cur.fetchall.assert_not_called()


def test_list_deliveries_filters_workspace_and_status():
    cur = MagicMock()
    cur.fetchall.return_value = [{"id": "hookd_1", "status": "delivered"}]

    rows = list_deliveries(cur, workspace_id="ws_1", status="delivered", limit=10, offset=5)

    assert rows == [{"id": "hookd_1", "status": "delivered"}]
    sql, params = cur.execute.call_args.args
    assert "d.workspace_id = %s" in sql
    assert "d.status = %s" in sql
    assert params == ["ws_1", "delivered", 10, 5]


def test_enqueue_safety_review_returns_inserted_row_or_none():
    cur = MagicMock()
    cur.fetchone.return_value = {"id": "safeq_1", "event_id": "evt_1"}

    row = enqueue_safety_review(
        cur,
        workspace_id="ws_1",
        node_id="mem_1",
        event_type="updated",
        event_id="evt_1",
    )

    assert row == {"id": "safeq_1", "event_id": "evt_1"}
    assert "ON CONFLICT (event_id) DO NOTHING" in cur.execute.call_args.args[0]


def test_list_safety_review_queue_filters_workspace_and_status():
    cur = MagicMock()
    cur.fetchall.return_value = [{"id": "safeq_1", "status": "queued"}]

    rows = list_safety_review_queue(cur, workspace_id="ws_1", status="queued", limit=20, offset=0)

    assert rows == [{"id": "safeq_1", "status": "queued"}]
    sql, params = cur.execute.call_args.args
    assert "workspace_id = %s" in sql
    assert "status = %s" in sql
    assert params == ["ws_1", "queued", 20, 0]


def test_validate_webhook_url_allows_localhost_http_but_rejects_remote_http_and_private_ip():
    assert validate_webhook_url("http://localhost:8787/hook") == "http://localhost:8787/hook"
    assert validate_webhook_url("http://127.0.0.1:8787/hook") == "http://127.0.0.1:8787/hook"
    assert validate_webhook_url("https://hooks.example.com/memtrace") == "https://hooks.example.com/memtrace"

    with pytest.raises(HTTPException):
        validate_webhook_url("http://hooks.example.com/memtrace")
    with pytest.raises(HTTPException):
        validate_webhook_url("https://192.168.1.10/hook")


@pytest.mark.asyncio
async def test_deliver_prepared_deliveries_marks_false_delivery_failed():
    cur = MagicMock()

    @contextmanager
    def fake_db_cursor(*args, **kwargs):
        yield cur

    result = {
        "_deliveries": [
            {
                "id": "hookd_1",
                "hook_id": "hook_1",
                "url": "https://hooks.example.com/memtrace",
                "secret": None,
                "payload": {"event": "major_inquiry"},
            }
        ],
        "pending": 1,
    }

    with patch("services.conductor.deliver_webhook", new=AsyncMock(return_value=False)), \
         patch("services.conductor.db_cursor", new=fake_db_cursor):
        updated = await _deliver_prepared_deliveries(result)

    assert updated["delivered"] == 0
    assert updated["failed"] == 1
    sql, params = cur.execute.call_args.args
    assert "SET status = 'failed'" in sql
    assert params[1] == "hookd_1"


@pytest.mark.asyncio
async def test_safety_queue_claim_uses_skip_locked_and_recovers_expired_leases():
    cur = MagicMock()
    cur.fetchall.return_value = []

    @contextmanager
    def fake_db_cursor(*args, **kwargs):
        yield cur

    with patch("services.safety_queue.db_cursor", new=fake_db_cursor), \
         patch("services.safety_queue.start_job_run", return_value="jobrun_1"), \
         patch("services.safety_queue.finish_job_run"):
        await safety_queue.process_safety_review_queue_job(limit=7)

    claim_sql, params = cur.execute.call_args.args
    assert "FOR UPDATE SKIP LOCKED" in claim_sql
    assert "status = 'processing'" in claim_sql
    assert "lease_until < now()" in claim_sql
    assert params == (7,)
