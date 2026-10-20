"""The hosted page (T-12; SPEC §13 limited hosted). Shown only when ATLAS_HOSTED=1.

Two views:

- **Recorded runs** (the default): the bundled runs in the hash-verifying viewer, disclosed
  as recordings. Nothing executes and no approval is asked. Always available.
- **Live session**: one live Nemotron session per visitor session. The model inspects and
  proposes; every proposal passes `validate_diff` and is "not executed here". The original's
  findings are those of the recorded, hash-verified trusted evaluation. The session runs in
  a background thread of this server process (`session.run_live_session`); the page follows
  its log.

Secrets are read on the server (`secrets.read`) and are never rendered: the page shows only
fixed messages and codes. The typed judge access code lives in a form that clears on submit.
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

from atlas.agent.controller import NOT_EXECUTED_HERE, recorded_label
from atlas.hosted import bundle, secrets
from atlas.hosted import session as hs
from atlas.ui import artifacts as A
from atlas.ui import recorded as RR
from atlas.ui import results as R
from atlas.ui import views as V
from atlas.ui.catalogue import BY_NAME, read_claim

RECORDED_VIEW, LIVE_VIEW = "recorded", "live"
HAR_CITATION = (
    "UCI HAR: Reyes-Ortiz, J., Anguita, D., Ghio, A., Oneto, L., & Parra, X. (2013). Human "
    "Activity Recognition Using Smartphones [Dataset]. UCI Machine Learning Repository. "
    "https://doi.org/10.24432/C54S4K. The dataset page grants CC BY 4.0; the archive's 2012 "
    'README.txt adds "Any commercial use is prohibited." This demo shows precomputed results '
    "only and does not distribute the data (benchmarks/real_sensor/ATTRIBUTION.md)."
)
REPLAY_DISCLOSURE = (
    "Replay: these are recorded runs. Every recorded hash is recomputed from the bundled "
    "files before anything is shown; nothing is re-executed here and no model is called."
)
LIVE_INTRO = (
    "One live session per visitor session, with the decided limits (at most 6 model "
    "requests, an estimate cap of $0.0648). The model inspects the project and may propose "
    f"revisions; each proposal is checked by ATLAS validation and is {NOT_EXECUTED_HERE}: "
    "the hosted demo runs no candidate code, so nothing here validates a diff beyond that."
)


@dataclass
class LiveHandle:
    """One live session started from this visitor session (its thread and its result)."""

    runs_dir: Path
    started_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    thread: threading.Thread | None = None
    outcome: hs.Outcome | None = None
    crash: str | None = None
    route: str | None = None

    @property
    def active(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self, secret, typed: str | None) -> None:
        def work():
            try:
                self.outcome = hs.run_live_session(
                    secret, typed, runs_dir=self.runs_dir, on_route=self._route
                )
            except Exception as exc:  # noqa: BLE001 - shown by type only, never as a result
                self.crash = type(exc).__name__

        self.thread = threading.Thread(
            target=work, name="atlas-hosted-live", daemon=True
        )
        self.thread.start()

    def _route(self, route: str) -> None:
        self.route = route

    def run_dir(self) -> Path | None:
        if self.outcome is not None and self.outcome.run_dir is not None:
            return self.outcome.run_dir
        found = sorted(self.runs_dir.glob("agent-*")) if self.runs_dir.is_dir() else []
        return found[-1] if found else None


def main() -> None:
    secret = secrets.read
    if "hosted_view" not in st.session_state:
        st.session_state.hosted_view = RECORDED_VIEW
    reason = hs.availability(secret)
    handle: LiveHandle | None = st.session_state.get("hosted_live")
    running = handle is not None and handle.active
    runs = {r.label: r for r in bundle.list_bundle()}
    run = None
    with st.sidebar:
        st.markdown("## ATLAS")
        st.caption("Checks whether an evaluation supports its deployment claim.")
        st.radio(
            "View",
            [RECORDED_VIEW, LIVE_VIEW],
            key="hosted_view",
            format_func=lambda v: (
                "Recorded runs" if v == RECORDED_VIEW else "Live session"
            ),
            disabled=running,
        )
        # The run picker sits here so the recorded run's hero fits the first viewport.
        if st.session_state.hosted_view == RECORDED_VIEW and runs:
            run = runs[
                st.selectbox("Recorded run", list(runs), key="hosted_recorded_run")
            ]
        st.markdown("**Capability**")
        st.markdown(":blue-badge[Hosted demo: limited]")
        st.caption(
            f"Candidate code is {NOT_EXECUTED_HERE}; the full workflow runs locally."
        )
        if reason is None:
            st.markdown(":blue-badge[Live: available]")
        else:
            st.markdown(":gray-badge[Live: unavailable]")
            st.caption(hs.UNAVAILABLE_MESSAGE)
    if st.session_state.hosted_view == RECORDED_VIEW:
        recorded_view(run)
    else:
        live_view(secret, reason, handle)


def recorded_view(run: RR.RecordedRun | None) -> None:
    """The replay disclosure (and the HAR citation for HAR runs) sits in the run's banner, so
    the hero fits the first viewport."""
    if run is None:
        with st.container(key="hosted-replay"):
            st.markdown(":blue-badge[Recorded runs] " + REPLAY_DISCLOSURE)
            st.markdown("No recorded runs are bundled.")
        return
    har = (HAR_CITATION,) if run.project.startswith("har_") else ()
    R.recorded_page(run, bundled=True, notes=(REPLAY_DISCLOSURE, *har))


def _label() -> str:
    path = bundle.BUNDLE_ROOT / bundle.LIVE_ORIGINAL_RUN
    report = A.read_json(path / "agent_report.json")
    return recorded_label(bundle.recorded_date(report) or "date unknown")


def _original_card():
    """The recorded original's findings, verified first. Returns (intact, label)."""
    path = bundle.BUNDLE_ROOT / bundle.LIVE_ORIGINAL_RUN
    report = A.read_json(path / "agent_report.json")
    checks = RR.verify(path, report) if report is not None else []
    ok = bool(checks) and RR.intact(checks)
    label = recorded_label(bundle.recorded_date(report) or "date unknown")
    with st.container(key="card-hosted-original", border=True):
        st.subheader("The original's findings (recorded)")
        if not ok:
            V.integrity(checks, ok)
            return False, label
        outcome = A.read_json(path / "original" / "outcome.json") or {}
        V.outcome_headline(
            outcome.get("outcome"), "hosted-original", f"Original: {label}"
        )
        st.caption(
            f"From the recorded run `{bundle.LIVE_ORIGINAL_RUN}`, re-verified now "
            f"({len(checks)} items). The original is not executed here."
        )
        rows = (((report or {}).get("comparison") or {}).get("original") or {}).get(
            "required_set"
        ) or []
        if rows:
            V.required_table(rows, "hosted-original-checks")
    return True, label


def live_view(secret, reason: str | None, handle: LiveHandle | None) -> None:
    with st.container(key="banner", border=True):
        st.markdown(":blue-badge[HOSTED LIVE SESSION] Limited hosted mode")
        st.caption(LIVE_INTRO)
    st.title("Does the evaluation support the claim?")
    fixture = BY_NAME[bundle.LIVE_PROJECT]
    with st.container(key="card-claim", border=True):
        st.subheader("1. Claim")
        claim = read_claim(fixture.path)
        if claim.statement:
            st.markdown(f"#### {claim.statement}")
        st.caption(f"Read-only, from `{fixture.name}/atlas_manifest.json:claim`.")
    if (
        handle is not None
        and not handle.active
        and handle.outcome is not None
        and handle.outcome.status == "ran"
    ):
        # The finished run's own Finding card shows the original, with the same label.
        _finished(handle, _label())
        return
    intact, label = _original_card()
    if handle is None:
        _start_form(secret, reason, intact)
        return
    if handle.active:
        _follow(handle)
        return
    _finished(handle, label)


def _start_form(secret, reason: str | None, intact: bool) -> None:
    with st.container(key="card-live-start", border=True):
        st.subheader("Live session")
        if reason is not None or not intact:
            with st.container(key="live-unavailable"):
                st.info(hs.UNAVAILABLE_MESSAGE, icon=":material/cloud_off:")
            return
        with st.form("live-start", clear_on_submit=True, border=False):
            typed = st.text_input(
                "Judge access code (optional)",
                type="password",
                help="Judges use their private code; leave it empty for the public demo.",
            )
            with st.container(key="primary-start-live"):
                submitted = st.form_submit_button(
                    "Start the live session", type="primary"
                )
        if submitted:
            handle = LiveHandle(hs.runs_root() / uuid.uuid4().hex[:12])
            st.session_state.hosted_live = handle
            handle.start(secret, typed or None)
            del typed
            st.rerun()


def _follow(handle: LiveHandle) -> None:
    with st.container(key="card-analysis", border=True):
        st.subheader("Live session")
        st.markdown(
            f"Live session in progress (started {A.short_time(handle.started_utc)})."
        )

        @st.fragment(run_every=1.0)
        def trace() -> None:
            if not handle.active:
                st.rerun()
            d = handle.run_dir()
            V.trace(A.read_log(d) if d else [], None, [])

        trace()


def _finished(handle: LiveHandle, label: str) -> None:
    outcome = handle.outcome
    if handle.crash is not None or outcome is None:
        with st.container(key="live-crash", border=True):
            st.error(
                f"The live session stopped with an internal error ({handle.crash}). "
                "Recorded runs remain available.",
                icon=":material/error:",
            )
        return
    if outcome.status == "exhausted" or outcome.code == "exhausted":
        with st.container(key="live-exhausted"):
            st.warning(hs.EXHAUSTED_MESSAGE, icon=":material/savings:")
    if outcome.status == "unavailable":
        with st.container(key="live-unavailable"):
            st.info(
                f"{hs.UNAVAILABLE_MESSAGE} ({hs.REASONS.get(outcome.code, 'unavailable')})",
                icon=":material/cloud_off:",
            )
        return
    if outcome.status != "ran" or outcome.run_dir is None:
        return
    st.caption(
        "Route: judge pool (access code accepted)."
        if outcome.route == "judge"
        else "Route: public demo budget."
    )
    report = A.read_json(outcome.run_dir / "agent_report.json")
    st.caption(
        f"Proposals marked '{NOT_EXECUTED_HERE}' pass ATLAS validation; nothing here "
        "validates them beyond that."
    )
    R.finished_run(
        outcome.run_dir,
        report,
        R.AGENT,
        decisions=[],
        notes=(),
        original_title=f"Original: {label}",
    )
