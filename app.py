"""ATLAS browser UI (T-07). Run: uv run --locked streamlit run app.py

One screen, top to bottom: the claim, the analysis, what ATLAS found, what the revision changed,
and how far to trust it (docs/UI_SPEC.md §2). Every result shown is read from the run's files.
"""

from datetime import datetime

import streamlit as st

from atlas.ui import artifacts as A
from atlas.ui import views as V
from atlas.ui.catalogue import BY_NAME, CATALOGUE_LABEL, FIXTURES, read_claim
from atlas.ui.scripts import BY_KEY, default_script, scripts_for
from atlas.ui.worker import AGENT, AUDIT, registry

st.set_page_config(page_title="ATLAS", page_icon=":material/fact_check:", layout="wide")
V.inject_css()

REG = registry()
handle = REG.current()
if handle is not None:
    handle.touch()

# -- session defaults: a refresh reattaches to the active or last run -----------------------
if "project" not in st.session_state:
    st.session_state.project = handle.project if handle else FIXTURES[0].name
if "mode" not in st.session_state:
    st.session_state.mode = (handle.mode if handle else AGENT) or AGENT


@st.cache_data(ttl=30, show_spinner=False)
def docker_capability() -> tuple[str, str | None]:
    from atlas.runner import docker as dr

    cap = dr.probe()
    return cap.state, cap.reason


def short_time(iso: str | None) -> str:
    if not iso:
        return "unknown time"
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M:%S UTC")
    except ValueError:
        return iso


def last_run_for(project: str) -> str:
    from atlas.ui.worker import runs_root

    root = runs_root()
    if not root.is_dir():
        return "No runs yet."
    dirs = sorted(
        (
            p
            for p in root.iterdir()
            if p.is_dir() and p.name.startswith(f"agent-{project}-")
        ),
        key=lambda p: p.stat().st_mtime,
    )
    if not dirs:
        return "No agent runs yet."
    report = A.read_json(dirs[-1] / "agent_report.json") or {}
    return f"Last agent run `{dirs[-1].name}`: {report.get('terminal_state', 'in progress')}"


# -- left rail ---------------------------------------------------------------------------------
running = handle is not None and handle.active
with st.sidebar:
    st.markdown("## ATLAS")
    st.caption("Checks whether an evaluation supports its deployment claim.")
    st.radio(
        "Project",
        [f.name for f in FIXTURES],
        key="project",
        captions=[f.purpose for f in FIXTURES],
        disabled=running,
    )
    st.caption(CATALOGUE_LABEL)
    st.markdown("**Runs**")
    if handle is None:
        st.caption("No run in this session yet.")
    else:
        st.caption(
            f"{'Running' if handle.active else 'Finished'}: `{handle.run_dir.name if handle.run_dir else handle.project}`"
        )
    st.markdown("**Capability**")
    state, reason = docker_capability()
    if state == "isolated_available":
        st.markdown(":green-badge[Docker: isolated_available]")
    else:
        st.markdown(f":orange-badge[Docker: {state}]")
        st.caption(reason or "")
    st.markdown(":gray-badge[Live: needs go-ahead]")
    st.caption("Live runs need the lead's explicit go-ahead.")

project = st.session_state.project
fixture = BY_NAME[project]

# -- banner --------------------------------------------------------------------------------------
report = None
run_dir = None
if handle is not None and not handle.active:
    run_dir = handle.run_dir or handle.find_run_dir()
    if run_dir is not None and handle.mode == AGENT:
        report = A.read_json(run_dir / "agent_report.json")
elif handle is not None:
    run_dir = handle.find_run_dir()
V.banner(
    report,
    run_dir.name if run_dir else None,
    handle.mode if handle else st.session_state.mode,
)

st.title("Does the evaluation support the claim?")

pending = handle.pending() if (handle and handle.active) else None


def start_run() -> None:
    mode = st.session_state.mode
    script = st.session_state.get(f"script-{project}") if mode == AGENT else None
    REG.start(project, mode, script)


# -- approval: a blocking panel, shown before anything else ---------------------------------------
if pending is not None:
    V.approval_panel(handle.channel, pending)

    @st.fragment(run_every=3.0)
    def keep_alive(handle_id: str, seq: int) -> None:
        """The session heartbeat while the panel waits; reruns the page once it is answered."""
        h = REG.current()
        if h is not None:
            h.touch()
        now = (
            h.pending() if (h is not None and h.id == handle_id and h.active) else None
        )
        if now is None or now.get("seq") != seq:
            st.rerun()
        st.caption(
            f"Waiting for your decision (asked {short_time(now.get('asked_utc'))}). "
            "Nothing runs until you submit."
        )

    keep_alive(handle.id, pending.get("seq"))
    st.stop()

# -- 1. Claim --------------------------------------------------------------------------------------
with st.container(key="card-claim", border=True):
    st.subheader("1. Claim")
    try:
        claim = read_claim(fixture.path)
    except Exception as exc:  # noqa: BLE001 - an unreadable project is shown, not run
        claim = None
        st.error(
            f"Project unreadable: {type(exc).__name__}: {exc}", icon=":material/error:"
        )
    if claim is not None and claim.statement is None:
        st.error(f"Project unreadable: {claim.reason}", icon=":material/error:")
        claim = None
    if claim is not None:
        left, right = st.columns([5, 4], gap="large")
        with left:
            with st.container(key="claim-statement"):
                st.markdown(f"#### {claim.statement}")
            st.caption(
                f"Read-only, from `{project}/atlas_manifest.json:claim`. The engine reads only "
                "the manifest's claim, so it is shown for confirmation and cannot be edited "
                "here."
            )
            if not claim.supported:
                st.warning(f"Intake reports this project unsupported: {claim.reason}")
            st.segmented_control(
                "Mode",
                [AGENT, AUDIT],
                format_func=lambda m: (
                    "Agent, fixture replies (NON-LIVE)"
                    if m == AGENT
                    else "Deterministic audit: no model"
                ),
                key="mode",
                required=True,
                disabled=running,
            )
            if st.session_state.mode == AGENT:
                options = [s.key for s in scripts_for(project)]
                key = f"script-{project}"
                if st.session_state.get(key) not in options:
                    st.session_state[key] = default_script(project)
                st.selectbox(
                    "Fixture replies",
                    options,
                    format_func=lambda k: BY_KEY[k].title,
                    key=key,
                    disabled=running,
                )
                st.caption(BY_KEY[st.session_state[key]].description)
            with st.container(horizontal=True, vertical_alignment="center"):
                st.button(
                    "Confirm & run",
                    type="primary",
                    disabled=running,
                    on_click=start_run,
                    key="confirm-run",
                )
                st.button(
                    "Agent, live",
                    disabled=True,
                    help="Live runs need the lead's explicit go-ahead.",
                    key="live-disabled",
                )
            st.caption(
                "Live runs need the lead's explicit go-ahead. " + last_run_for(project)
            )
            if running:
                st.caption(
                    f"Run in progress (started {short_time(handle.started_utc)})."
                )
        with right:
            V.claim_fields(claim)

if handle is None:
    with st.container(key="card-empty", border=True):
        st.subheader("2. Analysis")
        st.markdown("Not run yet. Confirm the claim and run to see the analysis.")
    st.stop()

stale = handle.project != project
if stale:
    st.info(
        f"Results below are from a different project ({handle.project}). Run this project "
        "to replace them.",
        icon=":material/history:",
    )

# -- 2. Analysis (live trace) -------------------------------------------------------------------
if handle.active:
    with st.container(key="card-analysis", border=True):
        st.subheader("2. Analysis")
        st.markdown(f"Run in progress (started {short_time(handle.started_utc)}).")

        @st.fragment(run_every=1.0)
        def live_trace(handle_id: str) -> None:
            h = REG.current()
            if h is not None:
                h.touch()
            if h is None or h.id != handle_id or not h.active:
                st.rerun()
            if h.pending() is not None:
                st.rerun()
            d = h.find_run_dir()
            events = A.read_log(d) if d else []
            t = A.trace(events)
            if t.current_state == "CHECK":
                st.markdown("Original under evaluation.")
            elif t.current_state == "EXECUTE":
                st.markdown("Executing in Docker.")
            if h.mode == AUDIT:
                st.markdown("Deterministic audit running (no model, no live trace).")
            else:
                V.trace(events, None, h.decisions())

        live_trace(handle.id)
    st.stop()


# -- finished run ---------------------------------------------------------------------------------
finished = A.run_finished_utc(report) if report else handle.finished_utc
with st.container(key="results-label"):
    st.caption(
        f"Results from run `{run_dir.name if run_dir else 'unknown'}`, finished "
        f"{short_time(finished)}"
        + (f" (from a different project: {handle.project})" if stale else "")
    )

if handle.crash:
    with st.container(key="card-crash", border=True):
        st.subheader("2. Analysis")
        st.error(
            f"The run raised {handle.crash} before writing a report. Nothing below is a "
            f"result.\n\n`{handle.crash_detail}`",
            icon=":material/error:",
        )
        st.button("Start a new run", on_click=start_run, key="restart-crash")
    st.stop()

terminal = report.get("terminal_state") if report else None
terminal_reason = report.get("terminal_reason") if report else None
comp = (report or {}).get("comparison") or {}

if handle.mode == AGENT:
    with st.container(key="card-analysis", border=True):
        st.subheader("2. Analysis")
        with st.container(key="terminal"):
            st.markdown(f"Terminal state {V.state_badge(terminal)}")
            if terminal_reason:
                st.markdown(f"Reason: `{terminal_reason}`")
        if report is None:
            st.error(
                "No agent_report.json was written for this run.",
                icon=":material/error:",
            )
        elif report.get("finalization_failures"):
            st.warning(
                "Partial report: the full report could not be built "
                f"({report['finalization_failures']}). It is shown as written.",
            )
        if terminal in A.FAILED_STATES or terminal is None:
            st.button("Start a new run", on_click=start_run, key="restart")
        V.trace(A.read_log(run_dir) if run_dir else [], report, handle.decisions())

# -- 3. Finding -------------------------------------------------------------------------------------
with st.container(key="card-finding", border=True):
    st.subheader("3. Finding")
    if handle.mode == AUDIT:
        outcome = A.read_json(run_dir / "outcome.json") if run_dir else None
        audit_report = A.read_json(run_dir / "report.json") if run_dir else None
        code = (outcome or {}).get("outcome")
        if code == "NOT_SUPPORTED":
            V.not_supported((outcome or {}).get("reason"))
        else:
            V.outcome_headline(code, "headline-original", "Deterministic audit outcome")
        rows = [
            {
                k: a.get(k)
                for k in ("assertion_id", "status", "reason", "evidence_valid")
            }
            for a in (outcome or {}).get("assertions", [])
        ]
        coverage = (outcome or {}).get("incomplete_coverage") or []
        limitations = (audit_report or {}).get("limitations")
    elif terminal == "NOT_SUPPORTED":
        V.not_supported(terminal_reason)
        outcome, rows, coverage, limitations = None, [], [], None
    else:
        original = comp.get("original") or {}
        outcome = (
            A.read_json(run_dir / "original" / "outcome.json") if run_dir else None
        )
        code = ((report or {}).get("scientific_outcomes") or {}).get("original")
        if not original and code is None:
            st.markdown("No findings yet: the original was not evaluated in this run.")
        else:
            V.outcome_headline(code, "headline-original", "Original, trusted evaluator")
            if original and not original.get("executed"):
                st.warning(
                    f"The original was not executed. {comp.get('comparison_basis', '')}",
                    icon=":material/block:",
                )
        rows = original.get("required_set") or []
        coverage = original.get("incomplete_coverage") or []
        limitations = original.get("limitations")
    if rows:
        with st.container(key="finding-counts"):
            st.markdown(V.counts_line(rows))
        V.required_table(rows, "finding-checks")
        if coverage:
            st.warning(
                "Incomplete coverage: " + ", ".join(coverage), icon=":material/warning:"
            )
        with st.expander("Check details: observed values, limitations, evidence"):
            V.assertion_details(outcome, rows)
        V.metric_block(outcome, "finding-metric")
        V.baselines(outcome)
        V.reported_metric(outcome)
    if limitations:
        with st.expander("Limitations of this evaluation"):
            V.bullet_list(limitations, "finding-limitations")

# -- 4. Revision and 5. Comparison (agent runs) -------------------------------------------------------
if handle.mode == AGENT and report is not None:
    views = A.proposals(run_dir, report)
    rationale = [
        t for t in report.get("model_text") or [] if t.get("kind") == "patch_rationale"
    ]
    with st.container(key="card-revision", border=True):
        st.subheader("4. Revision")
        line = next(
            (
                x
                for x in report.get("limitations") or []
                if " proposal" in x and "rejected by validation" in x
            ),
            None,
        )
        if line:
            with st.container(key="proposal-summary"):
                st.markdown(line)
        if not views:
            st.markdown("No candidate proposed: the model finished without a revision.")
        for i, v in enumerate(views, start=1):
            V.proposal(v, i)
            if i <= len(rationale):
                V.model_text(
                    rationale[i - 1]["text"],
                    rationale[i - 1]["label"],
                    f"model-rationale-{i}",
                )
        for i, c in enumerate(comp.get("candidates") or [], start=1):
            V.candidate_detail(c, i)
    if comp.get("candidates"):
        with st.container(key="card-comparison", border=True):
            st.subheader("5. Comparison")
            V.comparison(report, run_dir)

# -- 6. Trust and export -------------------------------------------------------------------------
with st.container(key="card-trust", border=True):
    st.subheader("6. Trust and export")
    if report is not None:
        for i, t in enumerate(report.get("model_text") or []):
            if t.get("kind") != "patch_rationale":
                V.model_text(t["text"], t["label"], f"model-text-{i}")
        V.cost(report)
        with st.container(key="run-limitations"):
            st.markdown("**Limitations**")
            V.bullet_list(report.get("limitations"))
    if run_dir is not None:
        V.export(run_dir, report)
    else:
        st.caption("Export is available once a report exists.")
