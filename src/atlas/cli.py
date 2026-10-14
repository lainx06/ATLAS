"""Command line: `python -m atlas.cli audit <project> --mode audit [--runs-dir runs]`."""

import argparse
import sys
from pathlib import Path

from atlas.audit import audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atlas")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("audit", help="audit a supported project")
    p.add_argument("project", type=Path)
    p.add_argument(
        "--mode", default="audit", choices=["audit", "agent", "agent+memory"]
    )
    p.add_argument("--runs-dir", type=Path, default=Path("runs"))
    args = parser.parse_args(argv)

    if args.mode != "audit":
        print(
            f"mode {args.mode!r} is not implemented (planned for T-06/T-08)",
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


if __name__ == "__main__":
    sys.exit(main())
