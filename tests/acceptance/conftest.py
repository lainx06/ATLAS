"""Acceptance tests: Playwright Python against the running Streamlit app (UI_SPEC §9).

    $env:ATLAS_REQUIRE_DOCKER='1'; uv run --locked pytest tests/acceptance -q -p no:cacheprovider

Each test module starts its own app server (`streamlit run app.py`, bound to localhost, on a
free port) with a fresh runs directory under the test's basetemp, so engine artifacts can be
compared with what the page shows. Model replies are fixture scripts (NON-LIVE); no model or
provider is called. Agent runs execute the original and candidates in the real Docker runner:
with ATLAS_REQUIRE_DOCKER=1 an unavailable runner fails the test instead of skipping it.
"""

import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REQUIRE_DOCKER = os.environ.get("ATLAS_REQUIRE_DOCKER") == "1"
HASH = re.compile(r"[0-9a-f]{64}")


@pytest.fixture(scope="session")
def docker():
    from atlas.runner import docker as dr

    cap = dr.probe()
    if cap.state != dr.CAPABILITY_AVAILABLE:
        message = f"isolated runner unavailable: {cap.reason}"
        if REQUIRE_DOCKER:
            pytest.fail(message)
        pytest.skip(message)
    return cap


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class App:
    def __init__(self, url: str, runs: Path, proc: subprocess.Popen, log: Path):
        self.url, self.runs, self.proc, self.log = url, runs, proc, log

    def agent_runs(self, project: str) -> list[Path]:
        if not self.runs.is_dir():
            return []
        return sorted(
            (p for p in self.runs.iterdir() if p.name.startswith(f"agent-{project}-")),
            key=lambda p: p.stat().st_mtime,
        )

    def audit_runs(self, project: str) -> list[Path]:
        if not self.runs.is_dir():
            return []
        return sorted(
            (p for p in self.runs.iterdir() if p.name.startswith(f"{project}-")),
            key=lambda p: p.stat().st_mtime,
        )


@pytest.fixture(scope="module")
def app(request, tmp_path_factory):
    """The app server for one test module. A module may define `app_env(base)`, returning
    extra environment for its server (e.g. the recorded-run root under `base`)."""
    base = tmp_path_factory.mktemp("app")
    runs = base / "runs"
    log = base / "server.log"
    port = _free_port()
    env = {**os.environ, "ATLAS_UI_RUNS_DIR": str(runs), "ATLAS_MODEL_MODE": "fixture"}
    extra = getattr(request.module, "app_env", None)
    if extra is not None:
        env.update(extra(base))
    with open(log, "wb") as out:
        proc = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py",
             "--server.port", str(port), "--server.headless", "true"],
            cwd=ROOT, env=env, stdout=out, stderr=subprocess.STDOUT,
        )  # fmt: skip
    url = f"http://localhost:{port}"
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/_stcore/health", timeout=2) as r:
                if r.status == 200:
                    break
        except OSError:
            time.sleep(0.5)
    else:
        proc.kill()
        pytest.fail(f"app did not start; see {log}")
    yield App(url, runs, proc, log)
    _kill_tree(proc)


def _kill_tree(proc: subprocess.Popen) -> None:
    """Stop the server and any run worker it started (a worker would otherwise wait out its
    approval timeout)."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        proc.kill()
    proc.wait(timeout=10)


@pytest.fixture
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 1440, "height": 900}}
