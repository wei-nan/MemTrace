from __future__ import annotations

import sys
import types
import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "test-secret-for-safety-sweep-tests-0001")

from core.scheduler import Scheduler
from jobs.safety_sweep import _get_safety_sweep_interval_seconds, _sweep_workspace


def test_safety_sweep_interval_supports_hours_alias(monkeypatch):
    monkeypatch.delenv("SAFETY_SWEEP_INTERVAL_SECONDS", raising=False)
    monkeypatch.setenv("SAFETY_SWEEP_INTERVAL_HOURS", "6")

    assert _get_safety_sweep_interval_seconds() == 21600


def test_safety_sweep_interval_seconds_takes_precedence(monkeypatch):
    monkeypatch.setenv("SAFETY_SWEEP_INTERVAL_SECONDS", "900")
    monkeypatch.setenv("SAFETY_SWEEP_INTERVAL_HOURS", "6")

    assert _get_safety_sweep_interval_seconds() == 900


def test_sweep_workspace_flags_risky_nodes_and_advances_offset():
    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"value": "0"},
        None,
    ]
    cur.fetchall.return_value = [
        {
            "id": "mem_danger",
            "title": "Dangerous maintenance",
            "body": "Run rm -rf /tmp/cache",
            "author": "user_1",
        },
        {
            "id": "mem_safe",
            "title": "Safe maintenance",
            "body": "Read the logs before changing configuration.",
            "author": "user_1",
        },
    ]

    with patch("services.audit_proposals.create_proposal") as create_proposal:
        result = _sweep_workspace(cur, "ws_1", batch_size=2)

    assert result == {"scanned": 2, "flagged": 1}
    create_proposal.assert_called_once()
    proposal_kwargs = create_proposal.call_args.kwargs
    assert proposal_kwargs["workspace_id"] == "ws_1"
    assert proposal_kwargs["reviewer"] == "safety_sweep"
    assert proposal_kwargs["target_ids"] == ["mem_danger"]
    assert proposal_kwargs["severity"] == "high"

    _, offset_params = cur.execute.call_args.args
    assert offset_params == ("safety_sweep_offset:ws_1", "2")


def test_scheduler_registers_safety_sweep_as_observable_job(monkeypatch):
    def noop():
        return None

    fake_modules = {
        "jobs.decay": {
            "decay_job": noop,
            "DECAY_INTERVAL_SECONDS": 1,
            "ephemeral_decay_job": noop,
            "EPHEMERAL_DECAY_INTERVAL_SECONDS": 1,
        },
        "jobs.cleanup": {
            "cleanup_job": noop,
            "CLEANUP_INTERVAL_SECONDS": 1,
            "deletion_notification_job": noop,
        },
        "jobs.ingest": {
            "stale_ingest_job": noop,
            "STALE_INGEST_CHECK_INTERVAL_SECONDS": 1,
        },
        "jobs.backup": {
            "backup_job": noop,
            "BACKUP_CHECK_INTERVAL_SECONDS": 1,
        },
        "jobs.path_reinforcement": {
            "path_reinforcement_job": noop,
            "PATH_REINFORCEMENT_INTERVAL_SECONDS": 1,
        },
        "jobs.audit_reviewers": {
            "audit_reviewers_job": noop,
        },
        "core.audit": {
            "audit_writer_loop": noop,
        },
        "jobs.safety_sweep": {
            "safety_sweep_job": noop,
            "SAFETY_SWEEP_INTERVAL_SECONDS": 86400,
        },
        "services.bg_jobs": {
            "retry_failed_embeddings_job": noop,
            "process_node_events_job": noop,
        },
        "services.safety_queue": {
            "process_safety_review_queue_job": noop,
        },
    }
    for name, attrs in fake_modules.items():
        module = types.ModuleType(name)
        for attr, value in attrs.items():
            setattr(module, attr, value)
        monkeypatch.setitem(sys.modules, name, module)

    scheduler = Scheduler()
    registered = []

    def record_loop(name, coro_func, interval_seconds, *, observable=True):
        registered.append(
            {
                "name": name,
                "interval_seconds": interval_seconds,
                "observable": observable,
            }
        )

    monkeypatch.setattr(scheduler, "register_loop", record_loop)

    scheduler.register_system_jobs()

    assert {
        "name": "safety_sweep",
        "interval_seconds": 86400,
        "observable": False,
    } in registered
