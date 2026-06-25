import os
import sys
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.edges import list_edges_in_db


def test_list_edges_defaults_to_active_edges():
    cur = MagicMock()

    with patch("services.workspaces.require_ws_access"):
        list_edges_in_db(cur, "ws_1", None, {"sub": "usr_1"})

    sql = cur.execute.call_args.args[0]
    assert "status = 'active'" in sql
    assert "faded" not in sql


def test_list_edges_can_include_faded_edges():
    cur = MagicMock()

    with patch("services.workspaces.require_ws_access"):
        list_edges_in_db(cur, "ws_1", "mem_1", {"sub": "usr_1"}, include_faded=True)

    sql = cur.execute.call_args.args[0]
    assert "status IN ('active', 'faded')" in sql