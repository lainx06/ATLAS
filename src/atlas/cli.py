"""Command line: `python -m atlas.cli audit <project> --mode audit|agent [--runs-dir runs]`.

`--mode audit` is the deterministic audit (trusted fixtures). `--mode agent` (T-06 slice 3) is
the bounded agent run: the original and every candidate run in the isolated Docker runner, each
only after the person at the terminal types the first 12 characters of its hash. In this build
the model replies come from a fixture script (`--fixture-script`), labelled non-live; live
inference is refused (T-06 slice 4 needs explicit authorization).
"""

import argparse
import os
import sys
from pathlib import Path

from atlas.audit import audit

AGENT_EXIT = {
    "REPORT": 0,
    "ERROR": 1,
    "NEEDS_INPUT": 3,
    "BUDGET_EXHAUSTED": 4,
    "NOT_SUPPORTED": 5,
}


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
    args = parser.parse_args(argv)

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


def _agent(args) -> int:
    from atlas.agent.approval import TerminalApprover
    from atlas.agent.client import MODE_ENV, FixtureClient
    from atlas.agent.controller import run_agent

    mode = os.environ.get(MODE_ENV, "fixture")
    if mode != "fixture":
        print(
            f"{MODE_ENV}={mode!r}: live inference is not authorized in this build "
            "(T-06 slice 4 needs explicit authorization). Nothing was run.",
            file=sys.stderr,
        )
        return 2
    if args.fixture_script is None:
        print(
            "agent mode in this build needs --fixture-script FILE (non-live replies). "
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
    print()
    print(f"terminal state: {result.terminal_state}")
    if result.reason:
        print(f"reason: {result.reason}")
    if result.original is not None:
        print(f"original: {result.original.outcome.outcome} ({result.original.runner})")
    for c in result.candidates:
        print(
            f"candidate {c.candidate_hash[:12]}: execution {c.execution.get('status')}, "
            f"outcome {c.outcome.outcome}"
        )
    print(f"report: {result.run_dir / 'agent_report.json'}")
    return AGENT_EXIT.get(result.terminal_state, 1)


if __name__ == "__main__":
    sys.exit(main())
