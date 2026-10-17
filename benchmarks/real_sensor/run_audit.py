"""The T-09 deterministic audit of the HAR projects, in the isolated Docker runner.

    uv run --locked python benchmarks/real_sensor/run_audit.py [--repeat N] [--runs-dir DIR]

Why not `python -m atlas.cli audit <project> --mode audit`: audit mode executes only
allowlisted, repository-authored trusted fixtures, on the host (`trusted_pipeline_only`). It
refuses these projects before executing anything, and admitting them would need a runner
allowlist change and host execution of project code, both out of bounds for T-09.

The existing engine path that runs a project's original code in Docker and judges it with the
trusted evaluator is the agent loop. Here it runs with **one fixture reply, `finish`**
(NON-LIVE: no model is called, and no candidate is proposed), so the result is the trusted
evaluator's verdict on the original alone. Execution of the original still needs an approval
bound to its code and snapshot hashes: `OriginalOnly` grants exactly that request (kind
`original`, empty diff) and refuses anything else. The authority for that approval is the T-09
task instruction to run these two ATLAS-authored projects in Docker.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from atlas.agent.client import FixtureClient
from atlas.agent.controller import run_agent
from atlas.candidates import Approval

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROJECTS = ("har_flawed", "har_clean")
FINISH = [
    {
        "content": json.dumps(
            {"action": {"tool": "finish", "summary": "T-09 audit: no revision."}}
        )
    }
]


class OriginalOnly:
    """Approves the unmodified original of this run, bound to its hashes; declines the rest."""

    def __init__(self):
        self.last_reason = None
        self.granted = []

    def decide(self, request):
        if getattr(request, "kind", None) != "original" or request.diff != "":
            self.last_reason = "t09_refused_non_original"
            return None
        self.last_reason = "t09_task_authorized_original"
        self.granted.append(request.candidate_hash)
        return Approval(
            request.candidate_hash,
            request.base_snapshot_hash,
            datetime.now(UTC).isoformat(),
        )


def audit_once(project: str, runs: Path) -> dict:
    result = run_agent(
        HERE / project,
        runs,
        FixtureClient("t09-audit-finish", FINISH),
        OriginalOnly(),
        env={},
    )
    report = result.report
    original = result.original
    outcome = None
    if original is not None:
        outcome = json.loads(
            (original.run_dir / "outcome.json").read_text(encoding="utf-8")
        )
    return {
        "project": project,
        "run_dir": str(result.run_dir.relative_to(ROOT)),
        "terminal_state": result.terminal_state,
        "terminal_reason": result.reason,
        "outcome": report.get("scientific_outcomes", {}).get("original"),
        "runner": original.runner if original else None,
        "executed": original.executed if original else None,
        "assertions": [
            {
                "assertion_id": a["assertion_id"],
                "status": a["status"],
                "reason": a["reason"],
            }
            for a in (outcome or {}).get("assertions", [])
        ],
        "evidence_sha256": (report.get("comparison") or {})
        .get("original", {})
        .get("evidence_sha256"),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--runs-dir", type=Path, default=ROOT / "runs" / "t09")
    p.add_argument("--project", choices=PROJECTS, action="append")
    args = p.parse_args(argv)
    args.runs_dir = args.runs_dir.resolve()
    results = []
    for project in args.project or PROJECTS:
        for i in range(args.repeat):
            r = audit_once(project, args.runs_dir)
            r["repeat"] = i + 1
            results.append(r)
            failed = [
                a["assertion_id"] for a in r["assertions"] if a["status"] == "FAIL"
            ]
            print(
                f"{project} #{i + 1}: {r['terminal_state']} {r['outcome']} "
                f"({r['runner']}) FAIL={failed} -> {r['run_dir']}"
            )
    out = args.runs_dir / f"t09_audit_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"summary: {out.relative_to(ROOT)}")
    return 0 if all(r["terminal_state"] == "REPORT" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
