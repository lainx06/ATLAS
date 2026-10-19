"""T-12 step 4: hosted configuration (offline).

- requirements.txt is exactly `uv export` of uv.lock (the full locked runtime set) for
  Streamlit Community Cloud; the host build itself is the deferred T-03 stage C check.
- Hosted mode is selected only by ATLAS_HOSTED=1.
- Secrets come only from st.secrets or the process environment, never from `.env`.
"""

import subprocess

import hosted_helpers as H
import pytest

from atlas import hosted
from atlas.hosted import secrets


def test_requirements_txt_is_the_locked_set():
    exported = subprocess.run(
        ["uv", "export", "--frozen", "--no-dev", "--no-hashes", "--format",
         "requirements.txt", "-o", "-"],
        cwd=H.ROOT, capture_output=True, text=True, check=True, timeout=120,
    ).stdout  # fmt: skip
    committed = (H.ROOT / "requirements.txt").read_text(encoding="utf-8")
    strip = lambda text: [
        line for line in text.splitlines() if line and not line.startswith("#")
    ]
    assert strip(committed) == strip(exported)
    assert (
        "-e ." in committed and "psycopg==" in committed and "streamlit==" in committed
    )
    assert not any(dev in committed for dev in ("pytest==", "ruff==", "playwright=="))


@pytest.mark.parametrize(
    ("value", "expected"), [("1", True), (None, False), ("0", False), ("true", False),
                            ("yes", False), (" 1", False)],
)  # fmt: skip
def test_hosted_mode_needs_exactly_one(value, expected):
    env = {} if value is None else {"ATLAS_HOSTED": value}
    assert hosted.enabled(env) is expected


def test_secrets_come_from_the_environment_never_from_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(f"NEBIUS_API_KEY={H.KEY}\n", encoding="utf-8")
    for name in secrets.NAMES:
        monkeypatch.delenv(name, raising=False)
        assert secrets.read(name) is None  # a .env file is never read
    monkeypatch.setenv("JUDGE_ACCESS_CODE", H.JUDGE_CODE)
    monkeypatch.setenv("HOSTED_LIVE_ENABLED", "")
    assert secrets.read("JUDGE_ACCESS_CODE") == H.JUDGE_CODE
    assert secrets.read("HOSTED_LIVE_ENABLED") is None  # empty counts as absent
    with pytest.raises(KeyError):
        secrets.read("PATH")  # only the four hosted secrets


def test_the_kill_switch_reads_exactly_true():
    from atlas.hosted.session import live_enabled

    assert live_enabled("true") is True
    for value in (None, "", "True", "TRUE", "1", "yes", "true ", " true"):
        assert live_enabled(value) is False
