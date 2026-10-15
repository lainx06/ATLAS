"""Local tests of the stub with streamlit's AppTest. No network, no deployment.

Run: uv run --locked python -m pytest hosting_probe/test_stub.py -q
"""

import hashlib
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).with_name("app.py"))


def _run(secrets=None):
    at = AppTest.from_file(APP, default_timeout=30)
    for k, v in (secrets or {}).items():
        at.secrets[k] = v
    return at.run()


def _text(at):
    return str([e.value for e in at.json] + [e.value for e in at.markdown])


def test_renders_without_secrets():
    at = _run()
    assert not at.exception
    assert any("skipped" in m.value for m in at.markdown)


def test_canary_shows_presence_and_hash_prefix_only():
    at = _run({"CANARY": "atlas-canary-12345"})
    shown = _text(at)
    assert "atlas-canary-12345" not in shown
    assert hashlib.sha256(b"atlas-canary-12345").hexdigest()[:8] in shown


def test_nebius_check_is_off_until_a_button_press_and_never_shows_the_key(monkeypatch):
    calls = []
    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: calls.append(a))
    at = _run({"NEBIUS_API_KEY": "not-a-real-key"})
    assert calls == []  # no network on render
    assert "not-a-real-key" not in _text(at)


def test_button_press_reports_status_and_count_with_a_mocked_response(monkeypatch):
    """The only network call is mocked: nothing leaves this machine."""
    import io
    import json
    import urllib.request

    class Fake(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    seen = {}

    def fake(request, timeout):
        seen["auth"] = request.get_header("Authorization")
        return Fake(json.dumps({"data": [{}, {}, {}]}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    at = _run({"NEBIUS_API_KEY": "not-a-real-key"})
    at.button[0].click().run()

    shown = _text(at)
    assert '"models": 3' in shown and "not-a-real-key" not in shown
    assert seen["auth"] == "Bearer not-a-real-key"  # sent to the (mocked) server only
