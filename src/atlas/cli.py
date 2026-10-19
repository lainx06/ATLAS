"""Command line: `python -m atlas.cli audit <project> --mode audit|agent [--runs-dir runs]`.

`--mode audit` is the deterministic audit (trusted fixtures). `--mode agent` (T-06) is the
bounded agent run: the original and every candidate run in the isolated Docker runner, each only
after the person at the terminal types the first 12 characters of its hash.

- **Fixture (non-live):** `--mode agent --fixture-script FILE` with `ATLAS_MODEL_MODE=fixture`
  (the default). Model replies come from the script, labelled non-live.
- **Live (T-06 slice 4):** `--mode agent --live --authorize-spend-usd AMOUNT`, for the one live
  run the lead decided (DECISIONS.md "T-06 slice 4 live-run decisions (lead)"). Running it needs
  the lead's Gate 3 go-ahead. Refusals, each exiting 2 before any run directory, Docker call,
  key read, client construction or network access, in this order:
  1. `--live` without `--mode agent`, or together with `--fixture-script`;
  2. `ATLAS_MODEL_MODE` is not `live`;
  3. `--authorize-spend-usd` missing, not a finite decimal, or not equal to the decided
     authorization;
  4. the decided spending limits do not cover the provider-enforced worst case.

  Then the key is read from `.env` (`load_api_key`, never printed), the pre-run model check runs
  (`agent.preflight`). If it aborts or raises (recorded as `preflight_error: <type name>`, never
  the message), the CLI exits `PREFLIGHT_ABORT_EXIT` (6) with no completion
  sent and the sanitized evidence in `<runs-dir>/preflight-<UTC time>.json`. Only after it
  passes is the production client built and the run started with the decided limits; the
  evidence goes into the run's report and `preflight.json`.

**Comparison (T-11):** `evaluate --suite comparison` runs the predeclared three-way comparison
(`atlas.evaluation`, `docs/EVALUATION.md`). It refuses unless one of these is given (nothing
run): `--fixture-script FILE` (non-live, `ATLAS_MODEL_MODE=fixture`, the default) or `--live
--authorize-spend-usd AMOUNT`, which has the same refusals, in the same order and with the same
exit codes, as the agent live path above (the worst case is checked per case run of at most
three requests), then the same key read and pre-run check. `--seed N` fixes the case order
(otherwise a seed is drawn and recorded). Exit 0 when every case's ATLAS result was obtained,
1 when one was unavailable (the records say why).

With `ATLAS_HOSTED=1` every mode is refused first (exit 2, a fixed message, nothing run and no
run directory): the hosted environment executes nothing (T-12 fix pass 1).

Exit codes: 0 REPORT, 1 ERROR, 3 NEEDS_INPUT, 4 BUDGET_EXHAUSTED, 5 NOT_SUPPORTED, 2 refused
before running, 6 pre-run check aborted.
"""

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from atlas.audit import audit
from atlas.hosted import enabled as hosted_enabled

AGENT_EXIT = {
    "REPORT": 0,
    "ERROR": 1,
    "NEEDS_INPUT": 3,
    "BUDGET_EXHAUSTED": 4,
    "NOT_SUPPORTED": 5,
}
REFUSED_EXIT = 2
HOSTED_REFUSAL = (
    "The hosted environment (ATLAS_HOSTED=1) executes nothing: audit and agent runs are "
    "refused."
)
PREFLIGHT_ABORT_EXIT = 6  # equals agent.preflight.PREFLIGHT_ABORT_EXIT
LIVE_ENV_FILE = (
    Path(__file__).resolve().parents[2] / ".env"
)  # read only on the live path
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atlas")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("audit", help="audit a supported project")
    p.add_argument("project", type=Path)
    p.add_argument(
        "--mode", default="audit", choices=["audit", "agent", "agent+memory"]
    )
    p.add_argument("--runs-dir", type=Path, default=Path("runs"))
    p.add_argument(
        "--fixture-script",
        type=Path,
        help="agent mode: the fixture model replies (JSON: name, replies); non-live",
    )
    p.add_argument(
        "--live",
        action="store_true",
        help="agent mode: the one authorized live run (needs ATLAS_MODEL_MODE=live and "
        "--authorize-spend-usd)",
    )
    p.add_argument(
        "--authorize-spend-usd",
        dest="authorize_spend_usd",
        help="with --live: the maximum authorized expenditure, which must equal the decided "
        "amount",
    )
    e = sub.add_parser("evaluate", help="run a predeclared evaluation suite (T-11)")
    e.add_argument("--suite", required=True, choices=["comparison"])
    e.add_argument("--runs-dir", type=Path, default=Path("runs") / "t11")
    e.add_argument(
        "--fixture-script",
        type=Path,
        help="non-live leg (b) replies (JSON: name, cases: {case: [replies]})",
    )
    e.add_argument(
        "--live",
        action="store_true",
        help="leg (b) against the model (needs ATLAS_MODEL_MODE=live and "
        "--authorize-spend-usd)",
    )
    e.add_argument("--authorize-spend-usd", dest="authorize_spend_usd")
    e.add_argument("--seed", type=int, help="case-order seed (recorded)")
    args = parser.parse_args(argv)

    if hosted_enabled():
        return _refuse(HOSTED_REFUSAL)
    if args.command == "evaluate":
        return _evaluate(args)
    if (args.live or args.authorize_spend_usd is not None) and args.mode != "agent":
        return _refuse("--live and --authorize-spend-usd require --mode agent.")
    if args.mode == "agent":
        return _agent(args)
    if args.mode != "audit":
        print(
            f"mode {args.mode!r} is not implemented (planned for T-08)",
            file=sys.stderr,
        )
        return 2
    result = audit(args.project, args.runs_dir)
    out = result.outcome
    print(f"outcome: {out.outcome}  ({out.policy_version})")
    if out.reason:
        print(f"reason: {out.reason}")
    for a in out.assertions:
        reason = f" ({a.reason})" if a.reason else ""
        print(f"  {a.status:<13} {a.assertion_id}{reason}")
    if out.incomplete_coverage:
        print("incomplete coverage: " + ", ".join(out.incomplete_coverage))
    print(f"evidence: {result.run_dir}")
    return 0


def _refuse(message: str) -> int:
    print(f"{message} Nothing was run.", file=sys.stderr)
    return REFUSED_EXIT


def _agent(args) -> int:
    if args.live:
        return _live(args)
    if args.authorize_spend_usd is not None:
        return _refuse("--authorize-spend-usd applies only with --live.")

    from atlas.agent.approval import TerminalApprover
    from atlas.agent.client import MODE_ENV, FixtureClient
    from atlas.agent.controller import run_agent

    mode = os.environ.get(MODE_ENV, "fixture")
    if mode != "fixture":
        print(
            f"{MODE_ENV}={mode!r} without --live: live inference is not authorized this way "
            "(a live run needs --live and --authorize-spend-usd). Nothing was run.",
            file=sys.stderr,
        )
        return 2
    if args.fixture_script is None:
        print(
            "agent mode needs --fixture-script FILE (non-live replies) or --live. "
            "Nothing was run.",
            file=sys.stderr,
        )
        return 2
    try:
        client = FixtureClient.from_file(args.fixture_script)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(
            f"fixture script unusable ({type(exc).__name__}). Nothing was run.",
            file=sys.stderr,
        )
        return 2
    print(
        f"NON-LIVE agent run: model replies come from fixture script {client.model_id!r}."
    )
    result = run_agent(args.project, args.runs_dir, client, TerminalApprover())
    return _finish(result)


def _finish(result) -> int:
    print()
    print(f"terminal state: {result.terminal_state}")
    if result.reason:
        print(f"reason: {result.reason}")
    if result.original is not None:
        where = result.original.runner if result.original.executed else "not executed"
        print(f"original: {result.original.outcome.outcome} ({where})")
    for c in result.candidates:
        print(
            f"candidate {c.candidate_hash[:12]}: execution {c.execution.get('status')}, "
            f"outcome {c.outcome.outcome}"
        )
    print(f"report: {result.run_dir / 'agent_report.json'}")
    return AGENT_EXIT.get(result.terminal_state, 1)


def _decimal(text) -> Decimal | None:
    """A finite Decimal from the command line, else None."""
    if not isinstance(text, str) or len(text) > 40:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def _live(args) -> int:
    # 1. Flag combination (no run directory, Docker call, key read, client or network yet).
    if args.fixture_script is not None:
        return _refuse("--live cannot be combined with --fixture-script.")

    from atlas.agent.client import MODE_ENV

    # 2. The mode.
    mode = os.environ.get(MODE_ENV, "fixture")
    if mode != "live":
        return _refuse(f"--live needs {MODE_ENV}=live (it is {mode!r}).")

    from atlas.agent.budget import DECIDED_SLICE4, Budget, SpendLimits, SpendRefused

    # 3. The authorized amount must equal the decided one (Decimal comparison).
    decided = DECIDED_SLICE4["authorized_usd"]
    given = args.authorize_spend_usd
    amount = _decimal(given)
    if amount is None or amount != decided:
        shown = "missing" if given is None else repr(given[:40])
        return _refuse(
            f"--authorize-spend-usd must equal the decided authorization {decided} USD "
            f"(given: {shown})."
        )

    # 4. The decided limits must cover the provider-enforced worst case.
    from atlas.agent.nebius import NebiusConfig

    try:
        config = NebiusConfig(**{k: DECIDED_SLICE4[k] for k in CONFIG_KEYS})
        limits = SpendLimits(
            authorized_usd=amount, estimate_cap_usd=DECIDED_SLICE4["estimate_cap_usd"]
        )
        figures = limits.check(config, DECIDED_SLICE4["max_attempts"])
    except (SpendRefused, ValueError, TypeError) as exc:
        return _refuse(f"spending limits refused: {exc}")

    # 5. The key, the pre-run check, and only then the client and the run.
    from atlas.agent import nebius
    from atlas.agent import preflight as pf
    from atlas.agent.approval import TerminalApprover
    from atlas.agent.controller import run_agent

    try:
        key = nebius.load_api_key(LIVE_ENV_FILE)
    except (OSError, ValueError) as exc:
        return _refuse(f"the API key is not available ({type(exc).__name__}).")
    try:
        evidence = pf.run_preflight(config, key)
    except Exception as exc:  # noqa: BLE001 - any failure of the check is an abort, never a pass
        # Only the type name is kept (never the message); no key-dependent step follows.
        evidence = pf.error_evidence(config, type(exc))
    for line in pf.summary_lines(evidence):
        print(line)
    if evidence["result"] != pf.PASS:
        path = _save_preflight(Path(args.runs_dir), evidence)
        print(
            f"Pre-run check aborted: no completion was sent. Evidence: {path}",
            file=sys.stderr,
        )
        return PREFLIGHT_ABORT_EXIT
    client = nebius.NebiusClient(config, key)
    del key
    print(
        f"LIVE agent run: model {config.model_id!r}; authorized up to "
        f"{figures['authorized_usd']} USD, estimate cap {figures['estimate_cap_usd']} USD, "
        f"at most {figures['max_attempts']} requests."
    )
    result = run_agent(
        args.project,
        args.runs_dir,
        client,
        TerminalApprover(),
        budget=Budget(max_attempts=DECIDED_SLICE4["max_attempts"]),
        live_authorized=True,
        spend=limits,
        preflight=evidence,
    )
    _write_json(result.run_dir / "preflight.json", evidence)
    return _finish(result)


def _decided_config():
    from atlas.agent.budget import DECIDED_SLICE4
    from atlas.agent.nebius import NebiusConfig

    return NebiusConfig(**{k: DECIDED_SLICE4[k] for k in CONFIG_KEYS})


def _seed(args) -> int | None:
    """The given seed if in range, a new recorded one if none was given, else None."""
    from atlas.evaluation.suite import new_seed

    if args.seed is None:
        return new_seed()
    return args.seed if 0 <= args.seed < 2**32 else None


def _evaluate(args) -> int:
    if args.live:
        return _evaluate_live(args)
    if args.authorize_spend_usd is not None:
        return _refuse("--authorize-spend-usd applies only with --live.")
    if args.fixture_script is None:
        return _refuse(
            "evaluate needs --fixture-script FILE (non-live replies) or --live "
            "--authorize-spend-usd AMOUNT."
        )

    from atlas.agent.client import MODE_ENV
    from atlas.evaluation import baseline as B
    from atlas.evaluation import suite

    mode = os.environ.get(MODE_ENV, "fixture")
    if mode != "fixture":
        return _refuse(
            f"{MODE_ENV}={mode!r} without --live: live inference is not authorized this "
            "way (a live run needs --live and --authorize-spend-usd)."
        )
    seed = _seed(args)
    if seed is None:
        return _refuse("--seed must be from 0 to 2**32 - 1.")
    try:
        name, cases = suite.load_fixture_script(args.fixture_script)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return _refuse(f"fixture script unusable ({type(exc).__name__}).")
    print(f"NON-LIVE comparison: leg (b) replies come from fixture script {name!r}.")
    record = suite.run_suite(
        args.runs_dir,
        suite.fixture_clients(name, cases),
        config=B.leg_b_config(_decided_config()),
        seed=seed,
        live=False,
    )
    return _evaluate_finish(record)


def _evaluate_finish(record: dict) -> int:
    print(
        f"seed {record['seed']}; leg (b) case order {', '.join(record['case_order'])}"
    )
    for cid, estimate in record["input_estimates"].items():
        print(
            f"  {cid}: input estimate {estimate} (ceiling {record['max_input_tokens']})"
        )
    print(f"results: {Path(record['run_dir']) / 'results.md'}")
    if record["atlas_unavailable"]:
        print(
            "ATLAS result unavailable: " + ", ".join(record["atlas_unavailable"]),
            file=sys.stderr,
        )
        return 1
    return 0


def _evaluate_live(args) -> int:
    # 1. Flag combination (no run directory, Docker call, key read, client or network yet).
    if args.fixture_script is not None:
        return _refuse("--live cannot be combined with --fixture-script.")

    from atlas.agent.client import MODE_ENV

    # 2. The mode.
    mode = os.environ.get(MODE_ENV, "fixture")
    if mode != "live":
        return _refuse(f"--live needs {MODE_ENV}=live (it is {mode!r}).")

    from atlas.agent.budget import DECIDED_SLICE4, SpendLimits, SpendRefused

    # 3. The authorized amount must equal the decided one (Decimal comparison).
    decided = DECIDED_SLICE4["authorized_usd"]
    given = args.authorize_spend_usd
    amount = _decimal(given)
    if amount is None or amount != decided:
        shown = "missing" if given is None else repr(given[:40])
        return _refuse(
            f"--authorize-spend-usd must equal the decided authorization {decided} USD "
            f"(given: {shown})."
        )

    # 4. The decided limits must cover the provider-enforced worst case of one case run, and
    #    three leg (b) reservations (at its own 40,000 input ceiling) the estimate cap.
    from atlas.agent import money
    from atlas.evaluation import baseline as B
    from atlas.evaluation import suite

    try:
        config = B.leg_b_config(_decided_config())
        limits = SpendLimits(
            authorized_usd=amount, estimate_cap_usd=DECIDED_SLICE4["estimate_cap_usd"]
        )
        figures = limits.check(config, B.REQUESTS_PER_CASE)
        reserved = money.times(B.REQUESTS_PER_CASE, config.ceiling_cost())
        if money.exceeds(reserved, limits.estimate_cap_usd):
            raise SpendRefused("three leg (b) reservations exceed the estimate cap")
    except (SpendRefused, ValueError, TypeError) as exc:
        return _refuse(f"spending limits refused: {exc}")
    seed = _seed(args)
    if seed is None:
        return _refuse("--seed must be from 0 to 2**32 - 1.")

    # 5. The key, the pre-run check, and only then the client and the run.
    from atlas.agent import nebius
    from atlas.agent import preflight as pf

    try:
        key = nebius.load_api_key(LIVE_ENV_FILE)
    except (OSError, ValueError) as exc:
        return _refuse(f"the API key is not available ({type(exc).__name__}).")
    try:
        evidence = pf.run_preflight(config, key)
    except Exception as exc:  # noqa: BLE001 - any failure of the check is an abort, never a pass
        evidence = pf.error_evidence(config, type(exc))
    for line in pf.summary_lines(evidence):
        print(line)
    if evidence["result"] != pf.PASS:
        path = _save_preflight(Path(args.runs_dir), evidence)
        print(
            f"Pre-run check aborted: no completion was sent. Evidence: {path}",
            file=sys.stderr,
        )
        return PREFLIGHT_ABORT_EXIT
    client = nebius.NebiusClient(config, key)
    del key
    print(
        f"LIVE comparison: model {config.model_id!r}; per case run authorized up to "
        f"{figures['authorized_usd']} USD, estimate cap {figures['estimate_cap_usd']} USD, "
        f"at most {figures['max_attempts']} requests."
    )
    record = suite.run_suite(
        args.runs_dir,
        lambda case_id: client,
        config=config,
        seed=seed,
        live=True,
        spend=limits,
        preflight=evidence,
    )
    return _evaluate_finish(record)


def _save_preflight(runs_dir: Path, evidence: dict) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    path = runs_dir / f"preflight-{stamp}.json"
    _write_json(path, evidence)
    return path


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
