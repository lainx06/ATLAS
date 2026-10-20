"""The local "Try It Live" page (T-07; navigation since UI restructure slice 1): run a
project, or open a recorded run read-only. Moved unchanged from app.py's local mode; the
only change is that no local filesystem path is shown (the recorded-runs folder is named,
not printed). Every result shown is read from the run's files (docs/UI_SPEC.md §2)."""

import streamlit as st

from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import hud as H
from atlas.ui import recorded as RR
from atlas.ui import results as R
from atlas.ui import views as V
from atlas.ui.catalogue import (
    BY_NAME,
    CATALOGUE_LABEL,
    FIXTURES,
    REAL_SENSOR,
    ROOT,
    read_claim,
)
from atlas.ui.scripts import BY_KEY, default_script, scripts_for
from atlas.ui.worker import AGENT, AUDIT, registry

RUN_VIEW = "run"
RECORDED_VIEW = "recorded"


def recorded_root_label() -> str:
    """The recorded-runs folder, named without a local filesystem path."""
    root = RR.recorded_root()
    try:
        return C.RECORDED_ROOT_REPO.format(path=root.relative_to(ROOT).as_posix())
    except ValueError:
        return C.RECORDED_ROOT_ENV


@st.cache_data(ttl=30, show_spinner=False)
def docker_capability() -> tuple[str, str | None]:
    from atlas.runner import docker as dr

    cap = dr.probe()
    return cap.state, cap.reason


short_time = A.short_time


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


def main() -> None:
    REG = registry()
    handle = REG.current()
    if handle is not None:
        handle.touch()

    # -- session defaults: a refresh reattaches to the active or last run -----------------------
    if "project" not in st.session_state:
        st.session_state.project = handle.project if handle else FIXTURES[0].name
    # The user's choices live in plain keys, not widget keys: Streamlit drops a widget's state on
    # any rerun that does not render it (the approval panel stops the page early), so widgets are
    # seeded from these keys and write back to them (UI_SPEC §12).
    if "sel_mode" not in st.session_state:
        st.session_state.sel_mode = (handle.mode if handle else AGENT) or AGENT
    if "sel_scripts" not in st.session_state:
        st.session_state.sel_scripts = {}
    if "view" not in st.session_state:
        st.session_state.view = RUN_VIEW
    # The recorded view hides the project list; keep its choice (a widget key) for the way back.
    if "project" in st.session_state:
        st.session_state.project = st.session_state.project

    # -- left rail ---------------------------------------------------------------------------------
    running = handle is not None and handle.active
    recorded_run = None
    with st.sidebar:
        st.markdown("## ATLAS")
        st.caption("Checks whether an evaluation supports its deployment claim.")
        st.radio(
            "View",
            [RUN_VIEW, RECORDED_VIEW],
            key="view",
            format_func=lambda v: (
                "Run a project" if v == RUN_VIEW else "Open a recorded run"
            ),
            disabled=running,
            help="Finish the active run first." if running else None,
        )
        if st.session_state.view == RECORDED_VIEW:
            root = RR.recorded_root()
            recorded = {r.label: r for r in RR.list_runs(root)}
            if recorded:
                choice = st.selectbox(
                    "Recorded run",
                    list(recorded),
                    format_func=lambda k: f"{k} ({recorded[k].kind})",
                    key="recorded_run",
                )
                recorded_run = recorded[choice]
            st.caption(
                f"Finished runs under {recorded_root_label()} (`live*/agent-*` and `ui/*`), "
                "read-only: nothing executes and no approval is asked."
            )
        else:
            st.radio(
                "Project",
                [f.name for f in FIXTURES],
                key="project",
                format_func=lambda n: BY_NAME[n].label,
                captions=[
                    f.purpose
                    + (" Unavailable: data not retrieved." if f.unavailable() else "")
                    for f in FIXTURES
                ],
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
    pending = handle.pending() if (handle and handle.active) else None

    # -- a recorded run, read-only (a pending approval still comes first) ----------------------------
    if st.session_state.view == RECORDED_VIEW and pending is None:
        if recorded_run is None:
            with st.container(key="hud-page"):
                V.banner(None, None, None)
                st.title("Does the evaluation support the claim?")
                V.state_panel(
                    "no-runs",
                    "stone",
                    "NO RECORDED RUNS",
                    f"No finished runs under {recorded_root_label()}.",
                    "finish a run under Run a project (with the default folders it "
                    "appears here under `ui/`), or set ATLAS_UI_RECORDED_DIR to a folder of "
                    "recorded runs.",
                )
        else:
            R.recorded_page(recorded_run)
        st.stop()

    # The run view sits on the HUD page container (the engineering grid, the HUD spacing).
    with st.container(key="hud-page"):
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
            handle.mode if handle else st.session_state.sel_mode,
        )

        st.title("Does the evaluation support the claim?")

        def start_run() -> None:
            """Confirm & run: the selected project with the selected mode and fixture replies."""
            mode = AGENT if agent_only(project) else st.session_state.sel_mode
            script = chosen_script(project) if mode == AGENT else None
            REG.start(project, mode, script)

        def agent_only(name: str) -> bool:
            """Real-data projects are not allowlisted trusted fixtures: the deterministic audit
            refuses them, so they run in Docker through the agent path (typed approval)."""
            return BY_NAME[name].root == REAL_SENSOR

        def restart_run() -> None:
            """Start a new run with the finished run's own project, mode and fixture replies."""
            REG.start(handle.project, handle.mode, handle.script)

        def chosen_script(name: str) -> str:
            options = [s.key for s in scripts_for(name)]
            choice = st.session_state.sel_scripts.get(name)
            return choice if choice in options else default_script(name)

        def remember_mode() -> None:
            st.session_state.sel_mode = st.session_state.mode_widget

        def remember_script(name: str) -> None:
            st.session_state.sel_scripts[name] = st.session_state[
                f"script_widget-{name}"
            ]

        # -- approval: a blocking panel, shown before anything else ---------------------------------------
        if pending is not None:
            V.approval_panel(handle.channel, pending)

            @st.fragment(run_every=1.0)
            def keep_alive(handle_id: str, seq: int) -> None:
                """The session heartbeat while the panel waits; reruns the page once it is answered."""
                h = REG.current()
                if h is not None:
                    h.touch()
                now = (
                    h.pending()
                    if (h is not None and h.id == handle_id and h.active)
                    else None
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
            unavailable = fixture.unavailable()
            if unavailable is not None:
                with st.container(key="project-unavailable"):
                    st.warning(unavailable, icon=":material/download:")
            try:
                claim = read_claim(fixture.path)
            except Exception as exc:  # noqa: BLE001 - an unreadable project is shown, not run
                claim = None
                st.error(
                    f"Project unreadable: {type(exc).__name__}: {exc}",
                    icon=":material/error:",
                )
            if claim is not None and claim.statement is None:
                st.error(f"Project unreadable: {claim.reason}", icon=":material/error:")
                claim = None
            if claim is not None:
                # Once this project has results, the claim fields fold away so the analysis and the
                # finding sit near the top (the 30-second read, UI_SPEC §2).
                compact = handle is not None and handle.project == project
                left, right = (
                    st.columns([5, 4], gap="large")
                    if not compact
                    else (st.container(), None)
                )
                with left:
                    with st.container(key="claim-statement"):
                        st.markdown(f"#### {claim.statement}")
                    st.caption(
                        f"Read-only, from `{project}/atlas_manifest.json:claim`. The engine reads only "
                        "the manifest's claim, so it is shown for confirmation and cannot be edited "
                        "here."
                    )
                    if not claim.supported:
                        st.warning(
                            f"Intake reports this project unsupported: {claim.reason}"
                        )
                    st.segmented_control(
                        "Mode",
                        [AGENT] if agent_only(project) else [AGENT, AUDIT],
                        format_func=lambda m: (
                            "Agent, fixture replies (NON-LIVE)"
                            if m == AGENT
                            else "Deterministic audit: no model"
                        ),
                        default=AGENT
                        if agent_only(project)
                        else st.session_state.sel_mode,
                        key="mode_widget",
                        on_change=remember_mode,
                        required=True,
                        disabled=running,
                        wrap=True,
                    )
                    if agent_only(project):
                        st.caption(
                            "Real data runs in the isolated Docker runner through the agent path; the "
                            "deterministic audit runs only the allowlisted synthetic fixtures."
                        )
                    docker_state, docker_reason = docker_capability()
                    if docker_state != "isolated_available" and (
                        agent_only(project) or st.session_state.sel_mode == AGENT
                    ):
                        V.state_panel(
                            "docker",
                            "amber",
                            f"Docker: {docker_state}",
                            (f"`{docker_reason}`. " if docker_reason else "")
                            + "Agent runs execute project code only in the isolated Docker runner; "
                            "ATLAS never falls back to running it on this machine, so the original "
                            "cannot be executed until the runner is available.",
                            "start Docker, then reload this page.",
                        )
                    if agent_only(project) or st.session_state.sel_mode == AGENT:
                        options = [s.key for s in scripts_for(project)]
                        chosen = chosen_script(project)
                        st.selectbox(
                            "Fixture replies",
                            options,
                            index=options.index(chosen),
                            format_func=lambda k: BY_KEY[k].title,
                            key=f"script_widget-{project}",
                            on_change=remember_script,
                            args=(project,),
                            disabled=running,
                        )
                        st.caption(BY_KEY[chosen].description)
                    with st.container(horizontal=True, vertical_alignment="center"):
                        st.button(
                            "Confirm & run",
                            type="primary",
                            disabled=running or unavailable is not None,
                            on_click=start_run,
                            key="primary-confirm-run",
                        )
                        st.button(
                            "Agent, live",
                            disabled=True,
                            help="Live runs need the lead's explicit go-ahead.",
                            key="live-disabled",
                        )
                    st.caption(
                        "Live runs need the lead's explicit go-ahead. "
                        + last_run_for(project)
                    )
                    if running:
                        st.caption(
                            f"Run in progress (started {short_time(handle.started_utc)})."
                        )
                if right is not None:
                    with right:
                        V.claim_fields(claim)
                else:
                    with st.expander(
                        "Claim fields (read-only, from atlas_manifest.json)"
                    ):
                        V.claim_fields(claim)

        if handle is None:
            with st.container(key="card-empty", border=True):
                st.subheader("2. Analysis")
                st.markdown(
                    "Not run yet. Confirm the claim and run to see the analysis."
                )
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
                st.markdown(
                    f"Run in progress (started {short_time(handle.started_utc)})."
                )

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
                        st.markdown(
                            "Deterministic audit running (no model, no live trace)."
                        )
                    else:
                        # Each stage the log records lights once, when it first appears here.
                        lit = st.session_state.setdefault("track_lit", {})
                        with st.container(key="hud-track"):
                            st.markdown(
                                H.track_live(
                                    events,
                                    H.Ids(H.run_hash(handle_id)),
                                    lit_from=lit.get(handle_id, 0),
                                ),
                                unsafe_allow_html=True,
                            )
                        lit[handle_id] = len(H.log_progress(events)[0])
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
                V.state_panel(
                    "crash",
                    "violet",
                    "ERROR",
                    f"The run raised `{handle.crash}` before writing a report. Nothing below is a "
                    f"result.\n\n`{handle.crash_detail}`",
                    "start a new run; if it happens again, the detail above names the exception.",
                )
                st.button("Start a new run", on_click=restart_run, key="restart-crash")
            st.stop()

        R.finished_verified(
            run_dir,
            report,
            handle.mode,
            run_id=run_dir.name if run_dir else handle.id,
            decisions=handle.decisions(),
            notes=fixture.notes,
            compare=(fixture, BY_NAME[fixture.compare_with])
            if fixture.compare_with
            else None,
            on_restart=restart_run,
        )
