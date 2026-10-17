"""BrowserApprover: the controller's unchanged `Approver.decide` contract, answered in a browser.

The engine runs in its own worker process (`atlas.ui.runproc`), because `run_agent`'s fixture
network guard is process-wide and would otherwise block the Streamlit server's sockets. The
approver lives in that process and talks to the page through files in the run's channel
directory: `pending.json` (the request exactly as the engine passed it), `answer-<n>.json`
(the page's single submission) and `heartbeat` (touched while a page shows the run).

The rule is the CLI's (`atlas.agent.approval.TerminalApprover`) and is applied here, inside
`decide`: the typed text, stripped and lowercased, must equal the first CONFIRM_CHARS
characters of the code hash. One attempt per request; a mismatch declines; an approval
carries the full hash. Nobody to ask (no page heartbeat), a closed panel, a page left without
a decision or the wait timing out raise `ApprovalUnavailable`, which the engine turns into
NEEDS_INPUT with nothing executed. `last_reason` uses the CLI's values: confirmed,
confirmation_mismatch, input_closed, no_terminal.
"""

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from atlas.agent.approval import CONFIRM_CHARS, ApprovalUnavailable
from atlas.candidates import Approval

NO_SESSION_S = 30.0  # no page heartbeat for this long: nobody is there to ask
LEFT_PAGE_S = 120.0  # a pending panel unseen for this long: the page was left
WAIT_LIMIT_S = 900.0  # an absolute bound on one approval wait
POLL_S = 0.25

PENDING = "pending.json"
HEARTBEAT = "heartbeat"
DECISIONS = "decisions.jsonl"


def _write_atomic(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# -- page side ---------------------------------------------------------------------------------
def touch(channel: Path) -> None:
    """A page is showing this run (the approver's session heartbeat): the file's mtime, which
    is updated atomically, so the worker never reads a half-written value."""
    (Path(channel) / HEARTBEAT).touch()
    os.utime(Path(channel) / HEARTBEAT)


def read_pending(channel: Path) -> dict | None:
    return _read(Path(channel) / PENDING)


def answer(channel: Path, seq: int, typed: str | None) -> bool:
    """The panel's single submission (None: closed without deciding). Exclusive create, so a
    second submission for the same request is refused (False)."""
    path = Path(channel) / f"answer-{seq}.json"
    try:
        with open(path, "x", encoding="utf-8") as f:
            json.dump({"typed": typed}, f)
    except FileExistsError:
        return False
    return True


def read_decisions(channel: Path) -> list[dict]:
    try:
        lines = (Path(channel) / DECISIONS).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [json.loads(x) for x in lines if x.strip()]


# -- engine side (the worker process) --------------------------------------------------------
class BrowserApprover:
    def __init__(
        self,
        channel: Path,
        *,
        now=None,
        clock=time.time,
        no_session_s: float = NO_SESSION_S,
        left_page_s: float = LEFT_PAGE_S,
        wait_limit_s: float = WAIT_LIMIT_S,
    ):
        self.channel = Path(channel)
        self._now = now or (lambda: datetime.now(UTC).isoformat())
        self._clock = clock
        self._no_session_s = no_session_s
        self._left_page_s = left_page_s
        self._wait_limit_s = wait_limit_s
        self._seq = 0
        self.last_reason: str | None = None

    def _heartbeat_age(self) -> float:
        try:
            seen = (self.channel / HEARTBEAT).stat().st_mtime
        except OSError:
            return float("inf")
        return self._clock() - seen

    def _record(self, kind: str, decision: str) -> None:
        with open(self.channel / DECISIONS, "a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": kind, "decision": decision}) + "\n")

    def decide(self, request):
        self.last_reason = None
        if self._heartbeat_age() > self._no_session_s:
            self.last_reason = "no_terminal"
            raise ApprovalUnavailable("no browser session to approve in")
        self._seq += 1
        seq = self._seq
        _write_atomic(
            self.channel / PENDING,
            {
                "seq": seq,
                "asked_utc": self._now(),
                "kind": getattr(request, "kind", "candidate"),
                "entry_point": request.entry_point,
                "diff": request.diff,
                "candidate_hash": request.candidate_hash,
                "base_snapshot_hash": request.base_snapshot_hash,
                "model_rationale": request.model_rationale,
            },
        )
        started = self._clock()
        reply = self.channel / f"answer-{seq}.json"
        try:
            while True:
                if reply.exists():
                    data = _read(reply)
                    if data is not None:
                        typed = data.get("typed")
                        break
                if self._heartbeat_age() > self._left_page_s:
                    self.last_reason = "input_closed"
                    raise ApprovalUnavailable("the page was left without a decision")
                if self._clock() - started > self._wait_limit_s:
                    self.last_reason = "input_closed"
                    raise ApprovalUnavailable("the approval wait timed out")
                time.sleep(POLL_S)
        finally:
            (self.channel / PENDING).unlink(missing_ok=True)
        if typed is None:
            self.last_reason = "input_closed"
            self._record(request.kind, "closed")
            raise ApprovalUnavailable(
                "the approval panel was closed without a decision"
            )
        if str(typed).strip().lower() != request.candidate_hash[:CONFIRM_CHARS]:
            self.last_reason = "confirmation_mismatch"
            self._record(request.kind, "declined")
            return None
        self.last_reason = "confirmed"
        self._record(request.kind, "approved")
        return Approval(request.candidate_hash, request.base_snapshot_hash, self._now())
