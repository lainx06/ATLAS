"""Run ceilings (SPEC §11; DECISIONS.md 2026-10-15).

- **Model attempts:** 6 per run, counting every attempted request, retries included. An attempt
  is reserved before the request is sent and counts even if it fails or returns no usage.
- **Retries:** at most 1 per transient call, and only while an attempt remains.
- **Tool operations:** 12 per run; reserved before the operation runs.
- **Candidate revisions:** 2 per run.
- **Active time:** 5 minutes per run. Waiting for a human approval is excluded (the clock is
  paused around it); total elapsed time is recorded separately.

Per-stage token ceilings (`docs/HOSTING_PROBE.md`) remain proposed; the request parameter below
is recorded with every attempt and is not a reviewed or enforced spending ceiling.
"""

import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass

MAX_ATTEMPTS = 6
MAX_RETRIES_PER_CALL = 1
MAX_TOOL_OPERATIONS = 12
MAX_REVISIONS = 2
MAX_ACTIVE_S = 300.0
PROPOSED_MAX_COMPLETION_TOKENS = 8000  # proposed; reviewed before any live execution


class BudgetExhausted(Exception):
    def __init__(self, ceiling: str, detail: str):
        super().__init__(f"{ceiling}: {detail}")
        self.ceiling = ceiling


@dataclass
class Usage:
    attempts: int = 0
    retries: int = 0
    tool_operations: int = 0
    revisions: int = 0


class Budget:
    def __init__(
        self,
        max_attempts: int = MAX_ATTEMPTS,
        max_tool_operations: int = MAX_TOOL_OPERATIONS,
        max_revisions: int = MAX_REVISIONS,
        max_active_s: float = MAX_ACTIVE_S,
        clock=time.monotonic,
    ):
        self.max_attempts = max_attempts
        self.max_tool_operations = max_tool_operations
        self.max_revisions = max_revisions
        self.max_active_s = max_active_s
        self.used = Usage()
        self._clock = clock
        self._started = clock()
        self._paused_s = 0.0

    # -- time -----------------------------------------------------------------------------
    def active_s(self) -> float:
        return self._clock() - self._started - self._paused_s

    def total_s(self) -> float:
        return self._clock() - self._started

    @contextmanager
    def paused(self):
        """Exclude the enclosed wait (a human approval) from active time."""
        start = self._clock()
        try:
            yield
        finally:
            self._paused_s += self._clock() - start

    def check_time(self) -> None:
        if self.active_s() > self.max_active_s:
            raise BudgetExhausted(
                "active_time", f"{self.active_s():.1f} s > {self.max_active_s:.0f} s"
            )

    # -- counted resources ----------------------------------------------------------------
    def can_attempt(self) -> bool:
        return self.used.attempts < self.max_attempts

    def reserve_attempt(self, retry: bool) -> int:
        """Count an attempt before it is sent; returns its 1-based number."""
        self.check_time()
        if not self.can_attempt():
            raise BudgetExhausted(
                "model_attempts",
                f"{self.max_attempts} attempts used (retries included)",
            )
        self.used.attempts += 1
        if retry:
            self.used.retries += 1
        return self.used.attempts

    def reserve_tool_operation(self, tool: str) -> int:
        self.check_time()
        if self.used.tool_operations >= self.max_tool_operations:
            raise BudgetExhausted(
                "tool_operations",
                f"{self.max_tool_operations} operations used; {tool} not run",
            )
        self.used.tool_operations += 1
        return self.used.tool_operations

    def reserve_revision(self) -> int:
        if self.used.revisions >= self.max_revisions:
            raise BudgetExhausted(
                "candidate_revisions",
                f"{self.max_revisions} revisions already proposed",
            )
        self.used.revisions += 1
        return self.used.revisions

    def summary(self) -> dict:
        return {
            "used": asdict(self.used),
            "limits": {
                "model_attempts": self.max_attempts,
                "retries_per_call": MAX_RETRIES_PER_CALL,
                "tool_operations": self.max_tool_operations,
                "candidate_revisions": self.max_revisions,
                "active_s": self.max_active_s,
            },
            "active_s": round(self.active_s(), 3),
            "total_elapsed_s": round(self.total_s(), 3),
            "approval_wait_s": round(self._paused_s, 3),
        }


class CostLedger:
    """Conservative per-run cost accounting at listed prices (DECISIONS.md 2026-10-15).

    Before a request is dispatched, its ceiling cost (both token ceilings at listed prices) is
    reserved. A reply with complete usage settles it at the usage cost. A dispatched request whose
    usage is unknown (timeout, connection failure, missing usage) keeps the full ceiling
    reserved; only a request refused before sending is released. Fixture clients have no provider
    cost. This is accounting, not spending authorization: the $0.051 planning estimate authorizes
    nothing.
    """

    def __init__(self, client):
        ceiling = getattr(client, "ceiling_cost", None)
        self.applicable = callable(ceiling)
        self.ceiling = ceiling() if self.applicable else None
        self._usage_cost = getattr(client, "usage_cost", None)
        self.entries: list[dict] = []

    def reserve(self, attempt: int) -> None:
        if self.applicable:
            self.entries.append(
                {"attempt": attempt, "status": "reserved", "usd": self.ceiling}
            )

    def settle(self, attempt: int, usage, dispatched: bool) -> None:
        if not self.applicable:
            return
        entry = next(e for e in self.entries if e["attempt"] == attempt)
        if not dispatched:
            entry.update(status="released", usd=0)
            return
        cost = self._usage_cost(usage) if isinstance(usage, dict) and usage else None
        if cost is None:
            entry.update(status="unknown_usage")  # the ceiling stays reserved
        else:
            entry.update(status="settled", usd=cost)

    def summary(self) -> dict:
        if not self.applicable:
            return {
                "applicable": False,
                "reason": "fixture replies: no provider request",
            }
        return {
            "applicable": True,
            "basis": "listed prices from configuration; ceiling cost kept when usage is unknown",
            "ceiling_per_request_usd": str(self.ceiling),
            "conservative_total_usd": str(sum(e["usd"] for e in self.entries)),
            "unknown_usage_attempts": sum(
                e["status"] == "unknown_usage" for e in self.entries
            ),
            "entries": [{**e, "usd": str(e["usd"])} for e in self.entries],
            "note": "accounting only; not a spending authorization",
        }
