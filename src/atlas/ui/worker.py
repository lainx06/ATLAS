"""Background runs (GAP-11) and the one-run-at-a-time policy (GAP-12).

`run_agent` and `audit` are synchronous, so each run happens in a worker process
(`atlas.ui.runproc`) while the page follows `<run>/agent_log.jsonl`. A process, not a thread:
the engine's fixture network guard is process-wide (its banner says so) and would block the
Streamlit server's own sockets. The registry lives in the server process, not in a browser
session: a refresh opens a new session that reattaches to the active run or shows the last
finished one, and a second start, from a double-click or another tab, is refused while a run
is active.
"""

import os
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from atlas.ui import approver as channel_io
from atlas.ui.catalogue import BY_NAME, ROOT
from atlas.ui.scripts import BY_KEY

AUDIT = "audit"
AGENT = "agent"
RUNS_ENV = "ATLAS_UI_RUNS_DIR"
CHANNELS = ".ui-channels"  # under the runs root; not a run directory


def runs_root() -> Path:
    return Path(os.environ.get(RUNS_ENV) or ROOT / "runs" / "ui").resolve()


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class RunHandle:
    id: str
    project: str
    mode: str  # AUDIT or AGENT
    script: str | None
    runs_root: Path
    channel: Path
    started_utc: str
    before: frozenset[str]
    proc: subprocess.Popen | None = None
    finished_utc: str | None = None
    run_dir: Path | None = None
    crash: str | None = None
    crash_detail: str | None = None

    @property
    def active(self) -> bool:
        if self.finished_utc is not None:
            return False
        exited = self.proc is not None and self.proc.poll() is not None
        if not exited and not (self.channel / "result.json").exists():
            return True
        if self.proc is not None and not exited:
            try:
                self.proc.wait(timeout=10)  # result.json is its last act
            except subprocess.TimeoutExpired:
                pass
        self._finish()
        return False

    def _finish(self) -> None:
        result = channel_io._read(self.channel / "result.json") or {}
        if result.get("run_dir"):
            self.run_dir = Path(result["run_dir"])
        self.crash = result.get("crash")
        self.crash_detail = result.get("crash_detail")
        if not result:
            code = self.proc.returncode if self.proc is not None else None
            self.crash = "WorkerExited"
            self.crash_detail = (
                f"the run's worker process ended (exit code {code}) without a result"
            )
        self.find_run_dir()
        self.finished_utc = _now()

    def touch(self) -> None:
        channel_io.touch(self.channel)

    def pending(self) -> dict | None:
        return channel_io.read_pending(self.channel) if self.mode == AGENT else None

    def decisions(self) -> list[dict]:
        return channel_io.read_decisions(self.channel)

    def find_run_dir(self) -> Path | None:
        """The run directory this run created: new since the start, named for the project."""
        if self.run_dir is not None:
            return self.run_dir
        prefix = f"agent-{self.project}-" if self.mode == AGENT else f"{self.project}-"
        if not self.runs_root.is_dir():
            return None
        new = [
            p
            for p in self.runs_root.iterdir()
            if p.is_dir() and p.name.startswith(prefix) and p.name not in self.before
        ]
        if len(new) == 1:
            self.run_dir = new[0]
        return self.run_dir


class Registry:
    def __init__(self):
        self._lock = threading.Lock()
        self._handle: RunHandle | None = None
        self.started = 0  # runs started by this server process

    def current(self) -> RunHandle | None:
        with self._lock:
            return self._handle

    def start(self, project: str, mode: str, script: str | None) -> RunHandle | None:
        """Start a run, or return None if one is already active (nothing is started)."""
        if project not in BY_NAME:
            raise ValueError(f"unknown project {project!r}")
        if mode == AGENT and script not in BY_KEY:
            raise ValueError(f"unknown fixture script {script!r}")
        with self._lock:
            if self._handle is not None and self._handle.active:
                return None
            root = runs_root()
            root.mkdir(parents=True, exist_ok=True)
            run_id = uuid.uuid4().hex[:12]
            channel = root / CHANNELS / run_id
            channel.mkdir(parents=True)
            handle = RunHandle(
                id=run_id,
                project=project,
                mode=mode,
                script=script if mode == AGENT else None,
                runs_root=root,
                channel=channel,
                started_utc=_now(),
                before=frozenset(p.name for p in root.iterdir()),
            )
            handle.touch()  # the starting page is there to be asked
            args = [sys.executable, "-m", "atlas.ui.runproc", "--channel", str(channel),
                    "--project", project, "--mode", mode, "--runs-root", str(root)]  # fmt: skip
            if mode == AGENT:
                args += ["--script", script]
            log = open(channel / "worker.log", "wb")  # noqa: SIM115 - owned by the child
            handle.proc = subprocess.Popen(
                args, stdout=log, stderr=subprocess.STDOUT, cwd=str(ROOT)
            )
            log.close()
            self._handle = handle
            self.started += 1
            return handle


_REGISTRY = Registry()


def registry() -> Registry:
    return _REGISTRY
