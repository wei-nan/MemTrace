"""The connection pool must not hand out connections that died while idle (a Postgres restart)."""
from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

from core import database


class _FakeConn:
    """Just enough of a psycopg2 connection for select(): a fileno() and a closed flag."""

    def __init__(self, sock: socket.socket, closed: int = 0) -> None:
        self._sock = sock
        self.closed = closed

    def fileno(self) -> int:
        return self._sock.fileno()


def test_idle_connection_with_nothing_to_read_is_usable():
    ours, theirs = socket.socketpair()
    try:
        assert database._connection_usable(_FakeConn(ours)) is True
    finally:
        ours.close()
        theirs.close()


def test_connection_the_server_closed_is_not_usable():
    ours, theirs = socket.socketpair()
    try:
        theirs.close()  # what a restarting server does to every idle client
        assert database._connection_usable(_FakeConn(ours)) is False
    finally:
        ours.close()


def test_connection_already_marked_closed_is_not_usable():
    ours, theirs = socket.socketpair()
    try:
        assert database._connection_usable(_FakeConn(ours, closed=2)) is False
    finally:
        ours.close()
        theirs.close()


def test_get_conn_replaces_dead_pooled_connections_before_handing_one_out():
    dead_one, dead_two, live = MagicMock(name="dead_one"), MagicMock(name="dead_two"), MagicMock(name="live")
    pool = MagicMock()
    pool.getconn.side_effect = [dead_one, dead_two, live]
    usable = {id(dead_one): False, id(dead_two): False, id(live): True}

    with (
        patch("core.database._pool", pool),
        patch("core.database.settings.database_url", "postgresql://test"),
        patch("core.database._connection_usable", side_effect=lambda conn: usable[id(conn)]),
    ):
        conn = database.get_conn()

    assert conn is live
    assert [call.args[0] for call in pool.putconn.call_args_list] == [dead_one, dead_two]
    assert all(call.kwargs == {"close": True} for call in pool.putconn.call_args_list)
    live.set_client_encoding.assert_called_once_with("UTF8")


def test_get_conn_keeps_a_healthy_connection_without_touching_the_pool_again():
    live = MagicMock()
    pool = MagicMock()
    pool.getconn.return_value = live

    with (
        patch("core.database._pool", pool),
        patch("core.database.settings.database_url", "postgresql://test"),
        patch("core.database._connection_usable", return_value=True),
    ):
        assert database.get_conn() is live

    pool.putconn.assert_not_called()
    assert pool.getconn.call_count == 1
