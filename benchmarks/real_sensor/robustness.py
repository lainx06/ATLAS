"""Robustness of repeated T-09 audits: are outcomes, statuses and evidence hashes stable?

    uv run --locked python benchmarks/real_sensor/robustness.py runs/t09/audit/t09_audit_<stamp>.json

Reads a `run_audit.py --repeat N` summary and, per project, compares across repeats:
the outcome and every assertion's status and reason; the SHA-256 of each evidence file the
evaluated original wrote (outcome, splits, predictions, provenance, ...); and the independent
primary metric (pooled and mean over folds, plus the per-fold values) and the reported-metric
comparison. Descriptive only (SPEC §17): three repeats show stability or its absence, nothing
more.
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Files that record when or how long, so they differ between repeats by design.
TIMED = {
    "approval.json",  # approved_at
    "candidate.json",  # the approval record it embeds (approved_at)
    "execution.json",
    "runtime.json",
    "index.json",
    "report.json",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence(original: Path) -> dict[str, str]:
    return {
        p.relative_to(original).as_posix(): sha(p)
        for p in sorted(original.rglob("*"))
        if p.is_file() and "exec/stage" not in p.as_posix()
    }


def metric(outcome: dict) -> dict:
    d = next(
        x
        for x in outcome["descriptive"]
        if x["result_id"] == "metric.recomputed_primary"
    )
    obs = d["observed"]
    agg = obs["aggregates"]["development_eval"][obs["primary_metric"]]
    return {
        "pooled": agg["pooled"]["value"],
        "mean_over_folds": agg["mean_over_folds"]["value"],
        "per_fold": [f[obs["primary_metric"]] for f in obs["per_fold"]],
    }


def main(summary: Path) -> int:
    runs = json.loads(summary.read_text(encoding="utf-8"))
    report = {}
    for project in sorted({r["project"] for r in runs}):
        reps = [r for r in runs if r["project"] == project]
        originals = [ROOT / r["run_dir"] / "original" for r in reps]
        outcomes = [
            json.loads((o / "outcome.json").read_text(encoding="utf-8"))
            for o in originals
        ]
        statuses = [
            [(a["assertion_id"], a["status"], a["reason"]) for a in o["assertions"]]
            for o in outcomes
        ]
        hashes = [evidence(o) for o in originals]
        files = sorted(set().union(*hashes))
        differing = [f for f in files if len({h.get(f) for h in hashes}) > 1]
        metrics = [metric(o) for o in outcomes]
        reported = [
            next(
                (a["status"], a["observed"])
                for a in o["assertions"]
                if a["assertion_id"] == "metric.reported_matches_recomputed"
            )
            if any(
                a["assertion_id"] == "metric.reported_matches_recomputed"
                for a in o["assertions"]
            )
            else None
            for o in outcomes
        ]
        spread = {
            k: max(m[k] for m in metrics) - min(m[k] for m in metrics)
            for k in ("pooled", "mean_over_folds")
        }
        report[project] = {
            "repeats": len(reps),
            "outcomes": sorted({o["outcome"] for o in outcomes}),
            "statuses_identical": all(s == statuses[0] for s in statuses),
            "evidence_files": len(files),
            "differing_files": differing,
            "differing_untimed_files": [
                f for f in differing if Path(f).name not in TIMED
            ],
            "metric_first_repeat": metrics[0],
            "metric_spread": spread,
            "per_fold_identical": all(
                m["per_fold"] == metrics[0]["per_fold"] for m in metrics
            ),
            "reported_metric_status": [r[0] if r else None for r in reported],
        }
    print(json.dumps(report, indent=2))
    out = summary.with_name(summary.stem + "_robustness.json")
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve()))
