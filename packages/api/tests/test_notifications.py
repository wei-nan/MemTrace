"""
tests/test_notifications.py
Phase 6.4 Track D — 通知投遞層單元測試（mock httpx + DB，不碰真實資料庫）。

驗證對應計畫:
  V6 / M6 通知投遞（webhook 簽章、重試）
  D1 解耦原則：投遞失敗不影響事件落地（不拋例外）
"""
from __future__ import annotations

import hmac
import hashlib
import json
from contextlib import contextmanager
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from services.notifications import deliver_webhook, send_consult_notification


# ─── deliver_webhook ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_signs_payload_with_hmac():
    """有 secret 時，payload 以 HMAC-SHA256 簽章放在 X-MemTrace-Signature header。"""
    captured = {}

    class FakeResp:
        status_code = 200

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, content=None, headers=None, timeout=None):
            captured["headers"] = headers
            captured["content"] = content
            return FakeResp()

    payload = {"event": "consultation", "session_id": "con_1"}
    with patch("services.notifications.httpx.AsyncClient", new=lambda *a, **k: FakeClient()):
        ok = await deliver_webhook("https://hook.example/x", "s3cr3t", payload)

    assert ok is True
    expected = hmac.new(b"s3cr3t", captured["content"].encode(), hashlib.sha256).hexdigest()
    assert captured["headers"]["X-MemTrace-Signature"] == expected


@pytest.mark.asyncio
async def test_webhook_retries_on_failure_then_gives_up():
    """投遞持續失敗應重試 3 次後放棄，且不向外拋例外。"""
    calls = {"n": 0}

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k):
            calls["n"] += 1
            raise ConnectionError("boom")

    with patch("services.notifications.httpx.AsyncClient", new=lambda *a, **k: FakeClient()), \
         patch("services.notifications.asyncio.sleep", new=AsyncMock()):
        ok = await deliver_webhook("https://hook.example/x", None, {"a": 1})  # no exception raised

    assert ok is False
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_webhook_no_secret_omits_signature():
    captured = {}

    class FakeResp:
        status_code = 200

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, content=None, headers=None, timeout=None):
            captured["headers"] = headers
            return FakeResp()

    with patch("services.notifications.httpx.AsyncClient", new=lambda *a, **k: FakeClient()):
        ok = await deliver_webhook("https://hook.example/x", None, {"a": 1})
    assert ok is True
    assert "X-MemTrace-Signature" not in captured["headers"]


# ─── send_consult_notification (decoupling + dispatch) ────────────────────────

def _patch_ws_lookup(settings=None):
    """Patch db_cursor so the workspace lookup returns name + settings."""
    cur = MagicMock()
    cur.fetchone.return_value = {"name": "故障排除", "settings": settings or {}}

    @contextmanager
    def fake_db_cursor(*a, **k):
        yield cur

    return patch("services.notifications.db_cursor", new=fake_db_cursor)


def test_escalated_notification_dispatches_email():
    with _patch_ws_lookup(), \
         patch("services.notifications.get_workspace_admins", return_value=["owner@example.com"]), \
         patch("services.notifications._dispatch") as dispatch:
        send_consult_notification(
            ws_id="ws_1", session_id="con_1", classification="safe",
            action_taken="escalated", proposal={"new_node": {"title": "Check logs"}},
            proposal_id="prop_1",
        )
    dispatch.assert_called_once()
    to_email, subject, _html, _text = dispatch.call_args.args
    assert to_email == "owner@example.com"
    assert "待核准" in subject


def test_notification_failure_is_decoupled():
    """投遞層丟例外時，send_consult_notification 必須吞掉、不影響呼叫端交易。"""
    with _patch_ws_lookup(), \
         patch("services.notifications.get_workspace_admins", side_effect=RuntimeError("db down")):
        # Must NOT raise
        send_consult_notification(
            ws_id="ws_1", session_id="con_1", classification="safe",
            action_taken="escalated", proposal={}, proposal_id="p",
        )


def test_webhook_dispatched_when_configured():
    """workspace settings 設了 webhook_url 時，會排程 webhook 投遞。"""
    with _patch_ws_lookup(settings={"webhook_url": "https://hook.example/x"}), \
         patch("services.notifications.get_workspace_admins", return_value=[]), \
         patch("services.notifications.asyncio.create_task",
               side_effect=lambda coro: coro.close()) as create_task:
        send_consult_notification(
            ws_id="ws_1", session_id="con_1", classification="dangerous",
            action_taken="blocked", proposal={"new_node": {"title": "x"}},
        )
    create_task.assert_called_once()


# ─── In-app notification center (trigger fan-out + read state) ────────────────

from services.audit_proposals import create_proposal
from services.notifications import (
    list_notifications,
    unread_count,
    mark_notification_read,
    mark_all_read,
    dismiss_notification,
    dismiss_notifications,
)


@pytest.mark.integration
class TestNotificationCenter:
    """Every audit proposal must fan out to workspace owner/admins as in-app notifications."""

    def test_audit_proposal_fans_out_to_owner(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"   # owner = usr_seed (seeded)
        recipient = "usr_seed"
        with conn.cursor() as cur:
            before = unread_count(cur, recipient, ws_id)
            prop = create_proposal(
                cur, ws_id, "integrity_auditor", "null_updated_at",
                ["seed_n1"], "test notify", severity="high",
            )
            assert prop is not None
            assert unread_count(cur, recipient, ws_id) == before + 1

            items = list_notifications(cur, recipient, workspace_id=ws_id, unread_only=True)
            mine = [n for n in items if n["source_id"] == prop["id"]]
            assert len(mine) == 1
            assert mine[0]["source_type"] == "audit_proposal"
            assert mine[0]["severity"] == "high"
            assert mine[0]["target_node_id"] == "seed_n1"  # first target_ids element

    def test_mark_read_is_owner_scoped_and_idempotent(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        recipient = "usr_seed"
        with conn.cursor() as cur:
            prop = create_proposal(
                cur, ws_id, "secret_scanner", "leaked_secret",
                ["seed_n1"], "secret found", severity="high",
            )
            items = list_notifications(cur, recipient, workspace_id=ws_id, unread_only=True)
            nid = next(n["id"] for n in items if n["source_id"] == prop["id"])

            # cross-user cannot read someone else's notification
            assert mark_notification_read(cur, nid, "someone_else") is False
            # owner reads it once
            assert mark_notification_read(cur, nid, recipient) is True
            # second read is a no-op (already read)
            assert mark_notification_read(cur, nid, recipient) is False

    def test_severity_filter_and_dismiss(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        recipient = "usr_seed"
        with conn.cursor() as cur:
            high = create_proposal(cur, ws_id, "secret_scanner", "leaked_secret", ["seed_n1"], "x", severity="high")
            low = create_proposal(cur, ws_id, "tag_normalizer", "tag_orphan", ["seed_n1"], "y", severity="low")

            # severity filter only returns matching rows
            highs = list_notifications(cur, recipient, workspace_id=ws_id, severity="high")
            assert highs and all(n["severity"] == "high" for n in highs)
            assert any(n["source_id"] == high["id"] for n in highs)
            assert all(n["source_id"] != low["id"] for n in highs)

            # dismiss one (owner-scoped, idempotent)
            hid = next(n["id"] for n in list_notifications(cur, recipient, workspace_id=ws_id)
                       if n["source_id"] == high["id"])
            assert dismiss_notification(cur, hid, "someone_else") is False
            assert dismiss_notification(cur, hid, recipient) is True
            assert dismiss_notification(cur, hid, recipient) is False

            # bulk clear read
            lid = next(n["id"] for n in list_notifications(cur, recipient, workspace_id=ws_id)
                       if n["source_id"] == low["id"])
            mark_notification_read(cur, lid, recipient)
            assert dismiss_notifications(cur, recipient, workspace_id=ws_id, read_only=True) >= 1

    def test_mark_all_read_clears_unread(self, db_transaction):
        conn = db_transaction
        ws_id = "ws_spec0001"
        recipient = "usr_seed"
        with conn.cursor() as cur:
            create_proposal(cur, ws_id, "deduper", "duplicate", ["seed_n1", "seed_n2"], "dup", severity="low")
            create_proposal(cur, ws_id, "tag_normalizer", "tag_orphan", ["seed_n1"], "orphan", severity="low")
            assert unread_count(cur, recipient, ws_id) >= 2
            updated = mark_all_read(cur, recipient, ws_id)
            assert updated >= 2
            assert unread_count(cur, recipient, ws_id) == 0
