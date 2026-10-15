"""Local tests of the stage A publication set. No network, no deployment.

Run: uv run --locked python -m pytest hosting_probe/test_stage_a.py -q
"""

import hashlib
import socket
from pathlib import Path

from streamlit.testing.v1 import AppTest

from hosting_probe import check_publication

APP = str(Path(__file__).with_name("stage_a") / "app.py")


LOCAL = {None, "", "localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _is_local(address) -> bool:
    host = address[0] if isinstance(address, tuple) else address
    return not isinstance(host, str) or host in LOCAL or host.startswith("127.")


def _guard(monkeypatch):
    """Refuse any non-loopback name lookup or connection (loopback is the test harness itself)."""
    real_connect, real_lookup = socket.socket.connect, socket.getaddrinfo

    def connect(self, address):
        if not _is_local(address):
            raise AssertionError(
                f"stage A must make no outbound connection: {address!r}"
            )
        return real_connect(self, address)

    def lookup(host, *args, **kwargs):
        if not _is_local((host,)):
            raise AssertionError(f"stage A must make no outbound lookup: {host!r}")
        return real_lookup(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "getaddrinfo", lookup)


def _run(monkeypatch, secrets=None):
    _guard(monkeypatch)
    at = AppTest.from_file(APP, default_timeout=30)
    for k, v in (secrets or {}).items():
        at.secrets[k] = v
    return at.run()


def _shown(at):
    return str([e.value for e in at.json] + [e.value for e in at.markdown])


def test_publication_set_is_exactly_two_clean_files():
    assert check_publication.problems("stage_a") == []


def test_renders_with_no_network_and_no_secret(monkeypatch):
    at = _run(monkeypatch)
    assert not at.exception
    assert '"present": false' in _shown(at)


def test_canary_shows_presence_and_hash_prefix_only(monkeypatch):
    at = _run(monkeypatch, {"CANARY": "harmless-canary-12345"})
    shown = _shown(at)
    assert not at.exception
    assert "harmless-canary-12345" not in shown
    assert hashlib.sha256(b"harmless-canary-12345").hexdigest()[:8] in shown


def test_other_secrets_are_never_read_or_shown(monkeypatch):
    at = _run(monkeypatch, {"CANARY": "c", "NEBIUS_API_KEY": "must-not-appear"})
    assert "must-not-appear" not in _shown(at)


def test_the_network_guard_itself_refuses_outbound_lookups(monkeypatch):
    """Self-check, so a passing app test means something: no packet is sent."""
    import pytest

    _guard(monkeypatch)
    with pytest.raises(AssertionError, match="outbound lookup"):
        socket.getaddrinfo("example.com", 443)
    with pytest.raises(AssertionError, match="outbound connection"):
        socket.socket().connect(("203.0.113.1", 443))
