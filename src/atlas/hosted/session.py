"""One hosted live session (T-12): checks in order, then `run_agent` in hosted mode.

Nothing is sent unless every check passes, in this order (each refusal is reported with a
fixed code and the page says live calls are unavailable; recorded runs still work):

1. the kill switch: HOSTED_LIVE_ENABLED must be exactly "true" (absent means false);
2. DATABASE_URL and NEBIUS_API_KEY must be set;
3. the budget store must answer (`setup`);
4. the route: the judge pool only for the correct access code (`access.select_route`);
5. the session must fit its caps (`open_session`); exhaustion is reported as "Live demo
   budget reached for today; recorded runs remain available" and nothing else is tried;
6. the pre-run model check (one free GET /models, `agent.preflight`) must pass.

Then the production client runs the unchanged agent loop with the decided values
(`budget.DECIDED_SLICE4`: model, ceilings, timeout, base URL, 6 attempts, estimate cap
$0.0648) in hosted mode: the original from the bundled recorded run, `NotExecutedHere`, no
approver, and every request reserved in the store first. The kill switch is read again
before each request.

Secrets are passed in by the page (read on the server from st.secrets or the environment)
and are never written to a log, report or event. The key goes only to the client.
"""

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from atlas.agent import nebius
from atlas.agent import preflight as pf
from atlas.agent.budget import DECIDED_SLICE4, Budget, ReservationRefused, SpendLimits
from atlas.hosted import access, bundle
from atlas.hosted.budget_store import BudgetStore, connector
from atlas.ui.catalogue import BY_NAME

KILL_SWITCH = "HOSTED_LIVE_ENABLED"
SECRET_NAMES = ("NEBIUS_API_KEY", "DATABASE_URL", "JUDGE_ACCESS_CODE", KILL_SWITCH)
RUNS_ENV = "ATLAS_HOSTED_RUNS_DIR"
CONFIG_KEYS = (
    "base_url",
    "model_id",
    "max_input_tokens",
    "max_completion_tokens",
    "template_overhead_tokens",
    "timeout_s",
    "price_input_per_token",
    "price_output_per_token",
    "context_length_tokens",
)
EXHAUSTED_MESSAGE = (
    "Live demo budget reached for today; recorded runs remain available."
)
UNAVAILABLE_MESSAGE = "Live calls are unavailable; recorded runs remain available."
# Fixed, display-safe reasons (never secret values or exception messages).
REASONS = {
    "live_disabled": "the live demo is switched off",
    "no_database": "the budget store is not configured",
    "no_key": "the model key is not configured",
    "store_unavailable": "the budget store is unavailable",
    "preflight_abort": "the pre-run model check did not pass",
    "client_unavailable": "the model client could not be set up",
}


def live_enabled(raw) -> bool:
    """The kill switch: only the exact string "true" enables live calls."""
    return raw == "true"


@dataclass
class Outcome:
    """What the page shows for one attempt to run a live session."""

    status: str  # "ran", "exhausted" or "unavailable"
    code: str | None = None  # a fixed code (REASONS, or the store's refusal code)
    route: str | None = None
    run_dir: Path | None = None
    terminal_state: str | None = None
    preflight: dict = field(default_factory=dict)

    @property
    def message(self) -> str:
        if self.status == "exhausted":
            return EXHAUSTED_MESSAGE
        if self.status == "unavailable":
            return UNAVAILABLE_MESSAGE
        return ""


def runs_root() -> Path:
    import os

    root = os.environ.get(RUNS_ENV)
    return Path(root) if root else Path(tempfile.gettempdir()) / "atlas-hosted-runs"


def decided_config() -> nebius.NebiusConfig:
    return nebius.NebiusConfig(**{k: DECIDED_SLICE4[k] for k in CONFIG_KEYS})


def decided_limits() -> SpendLimits:
    return SpendLimits(
        authorized_usd=DECIDED_SLICE4["authorized_usd"],
        estimate_cap_usd=DECIDED_SLICE4["estimate_cap_usd"],
    )


def availability(secret) -> str | None:
    """None if a live session may be attempted, else a REASONS code. Contacts nothing."""
    if not live_enabled(secret(KILL_SWITCH)):
        return "live_disabled"
    if not secret("DATABASE_URL"):
        return "no_database"
    if not secret("NEBIUS_API_KEY"):
        return "no_key"
    return None


def run_live_session(
    secret,
    typed_code: str | None,
    *,
    runs_dir: Path | None = None,
    store_factory=None,
    on_route=None,
) -> Outcome:
    """Run one hosted live session. `secret(name)` returns a secret's value or None; it is
    read again for the kill switch before each request. Never raises for a refusal."""
    reason = availability(secret)
    if reason is not None:
        return Outcome("unavailable", reason)
    store = (store_factory or (lambda url: BudgetStore(connector(url))))(
        secret("DATABASE_URL")
    )
    try:
        try:
            store.setup()
        except Exception:  # noqa: BLE001 - fails closed; the type is not shown either
            return Outcome("unavailable", "store_unavailable")
        route = access.select_route(
            typed_code, secret("JUDGE_ACCESS_CODE"), store.log_event
        )
        if on_route is not None:
            on_route(route)
        config = decided_config()
        try:
            session = store.open_session(route, config.ceiling_cost())
        except ReservationRefused as exc:
            return Outcome("exhausted", exc.code, route)
        except Exception:  # noqa: BLE001
            return Outcome("unavailable", "store_unavailable", route)
        session.enabled = lambda: live_enabled(secret(KILL_SWITCH))
        key = secret("NEBIUS_API_KEY")
        try:
            evidence = pf.run_preflight(config, key)
        except Exception as exc:  # noqa: BLE001 - an abort, never a pass
            evidence = pf.error_evidence(config, type(exc))
        if evidence.get("result") != pf.PASS:
            store.log_quietly(route, "preflight_abort")
            return Outcome("unavailable", "preflight_abort", route, preflight=evidence)
        try:
            client = nebius.NebiusClient(config, key)
        except Exception:  # noqa: BLE001
            return Outcome("unavailable", "client_unavailable", route)
        del key
        from atlas.agent.controller import NoApprover, run_agent

        result = run_agent(
            BY_NAME[bundle.LIVE_PROJECT].path,
            runs_dir or runs_root(),
            client,
            NoApprover(),
            budget=Budget(max_attempts=DECIDED_SLICE4["max_attempts"]),
            original=bundle.live_original(),
            live_authorized=True,
            spend=decided_limits(),
            preflight=evidence,
            hosted=True,
            reservations=session,
        )
        state = result.terminal_state
        exhausted = (result.reason or "").startswith("hosted_budget:")
        return Outcome(
            "ran",
            "exhausted" if exhausted else None,
            route,
            result.run_dir,
            state,
            evidence,
        )
    finally:
        store.close()
