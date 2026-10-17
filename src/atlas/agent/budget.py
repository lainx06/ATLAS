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
from decimal import Decimal

from atlas.agent import money

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


UNRESOLVED_NOTE = (
    "Unresolved amounts are estimates from the configured ceilings, not a guaranteed maximum "
    "charge: the input ceiling is enforced before sending only by an unverified token "
    "estimate, so a provider could report more."
)
UNREPRESENTABLE = "unrepresentable"


class CostLedger:
    """Per-run cost accounting at listed prices (DECISIONS.md 2026-10-15).

    Before a request is dispatched, its ceiling cost (both token ceilings at listed prices) is
    reserved. After it, each **validated known** usage count is charged at its listed price,
    even above its ceiling (known actual usage is never capped at an estimate). Each unknown
    count (timeout, connection failure, missing or invalid usage) is held at its component
    ceiling, and while any count is unknown the entry never drops below the original
    reservation. Only a request refused before sending is released. Fixture clients have no
    provider cost.

    All arithmetic is exact and independent of the caller's `decimal` context (`agent/money.py`).
    The unknown components' hold is computed directly, never recovered by subtracting two
    large totals. If an amount cannot be represented exactly, the entry is marked
    `unrepresentable` (no figure is invented, and nothing is reported as settled) and the
    summary's totals are withheld; the controller then ends the run (`cost_unrepresentable`).

    `known_usd` is reported usage at listed prices. `unresolved_usd` is the estimate held for
    unknown counts; it is not a guaranteed maximum (UNRESOLVED_NOTE). This is accounting, not
    spending authorization: the $0.051 planning estimate authorizes nothing.
    """

    def __init__(self, client):
        ceiling = getattr(client, "ceiling_cost", None)
        self.applicable = callable(ceiling)
        if self.applicable and not all(
            callable(getattr(client, name, None))
            for name in ("component_costs", "component_ceilings")
        ):
            raise TypeError("a priced client must provide component costs and ceilings")
        self.ceiling = None
        if self.applicable:
            # Checked before any request: an unsupported configuration never reaches dispatch.
            self.ceiling = money.total([ceiling()])
            components = client.component_ceilings()
            if money.total(components) != self.ceiling:
                raise money.MoneyError("ceiling components do not add up")
        self._client = client
        self.entries: list[dict] = []

    def reserve(self, attempt: int) -> None:
        if self.applicable:
            self.entries.append(
                {
                    "attempt": attempt,
                    "status": "reserved",
                    "known_usd": Decimal(0),
                    "unresolved_usd": self.ceiling,
                }
            )

    def settle(self, attempt: int, usage, dispatched: bool) -> str | None:
        """Settle one attempt; returns its new status (None for a fixture client)."""
        if not self.applicable:
            return None
        entry = next(e for e in self.entries if e["attempt"] == attempt)
        if dispatched is False:  # only an explicit "never sent" releases a reservation
            entry.update(
                status="released", known_usd=Decimal(0), unresolved_usd=Decimal(0)
            )
            return entry["status"]
        try:
            status, known, unresolved = self._settlement(usage)
        except money.MoneyError:
            entry.update(status=UNREPRESENTABLE, known_usd=None, unresolved_usd=None)
            return entry["status"]
        entry.update(status=status, known_usd=known, unresolved_usd=unresolved)
        return status

    def _settlement(self, usage) -> tuple[str, Decimal, Decimal]:
        # component_costs validates the counts itself: invalid ones count as unknown.
        costs = tuple(self._client.component_costs(usage))
        ceilings = tuple(self._client.component_ceilings())
        if len(costs) != 2 or len(ceilings) != 2:
            raise money.MoneyError("expected input and output components")
        known = money.total(c for c in costs if c is not None)
        if None not in costs:
            return "settled", known, Decimal(0)
        held = money.total(m for c, m in zip(costs, ceilings) if c is None)
        # Never below the original reservation while a count is unknown: if the known part
        # plus the held part is smaller, the shortfall is held as well.
        floor_gap = money.difference(self.ceiling, money.total((known, held)))
        unresolved = money.total((held, floor_gap)) if floor_gap > 0 else held
        status = (
            "partial_usage" if any(c is not None for c in costs) else "unknown_usage"
        )
        return status, known, unresolved

    @property
    def unrepresentable(self) -> bool:
        return any(e["status"] == UNREPRESENTABLE for e in self.entries)

    def summary(self) -> dict:
        if not self.applicable:
            return {
                "applicable": False,
                "reason": "fixture replies: no provider request",
            }
        figures = {}
        if not self.unrepresentable:
            known = money.total(e["known_usd"] for e in self.entries)
            unresolved = money.total(e["unresolved_usd"] for e in self.entries)
            figures = {
                "known_usd": money.text(known),
                "unresolved_usd": money.text(unresolved),
                "estimated_total_usd": money.text(money.total((known, unresolved))),
            }
        else:
            figures = {
                "known_usd": None,
                "unresolved_usd": None,
                "estimated_total_usd": None,
                "unrepresentable_note": (
                    "an amount could not be represented exactly; totals are withheld "
                    "rather than rounded or shown as infinite"
                ),
            }
        return {
            "applicable": True,
            "basis": (
                "validated reported usage at listed prices, computed exactly; each unknown "
                "count held at its configured ceiling, never below the request's original "
                "reservation"
            ),
            "ceiling_per_request_usd": money.text(self.ceiling),
            **figures,
            "unknown_usage_attempts": sum(
                e["status"] in ("unknown_usage", "partial_usage") for e in self.entries
            ),
            "unrepresentable_attempts": sum(
                e["status"] == UNREPRESENTABLE for e in self.entries
            ),
            "entries": [
                {
                    **e,
                    "known_usd": None
                    if e["known_usd"] is None
                    else money.text(e["known_usd"]),
                    "unresolved_usd": None
                    if e["unresolved_usd"] is None
                    else money.text(e["unresolved_usd"]),
                }
                for e in self.entries
            ],
            "unresolved_note": UNRESOLVED_NOTE,
            "note": "accounting only; not a spending authorization",
        }
