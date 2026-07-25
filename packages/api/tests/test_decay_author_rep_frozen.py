"""Guards the 2026-07-25 containment: decay_job() must not call
recalculate_author_rep(). See ws_spec_plan/mem_82155065.

recalculate_author_rep() writes dim_author_rep = AVG(trust_score) per author,
and dim_author_rep feeds every trust_score formula in the codebase. An
unauthorized backfill wrote trust_score with a formula found nowhere else in
the codebase across ~1300 nodes in 56+ workspaces. Leaving the scheduled call
live would launder that value into dim_author_rep on every 24h decay run.

This test does not assert what the *right* fix is — only that the call stays
frozen until a human resolves the incident. Delete this test only as part of
that resolution, not to make an unrelated change pass.
"""
from unittest.mock import MagicMock, patch

import pytest

from jobs import decay as decay_module


@pytest.mark.asyncio
async def test_decay_job_does_not_call_recalculate_author_rep():
    fake_cur = MagicMock()
    fake_cur.fetchall.return_value = []

    fake_ctx = MagicMock()
    fake_ctx.__enter__.return_value = fake_cur
    fake_ctx.__exit__.return_value = False

    with patch.object(decay_module, "db_cursor", return_value=fake_ctx), \
         patch.object(decay_module, "recalculate_freshness") as mock_freshness, \
         patch.object(decay_module, "recalculate_author_rep") as mock_author_rep, \
         patch.object(decay_module, "snapshot_kb_health"):
        await decay_module.decay_job()

    mock_freshness.assert_called_once()
    mock_author_rep.assert_not_called()
