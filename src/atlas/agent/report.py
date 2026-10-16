"""Original-versus-candidate report (SPEC §6, §9.6; T-06 slice 1).

Execution status (did the candidate run, in isolation?) and scientific outcome (what the
trusted evaluator found for the full required set) are reported separately. Neither says that
the deployment claim is true, and no candidate is called "fixed" or "improved": the report
lists every required assertion's status before and after, with the evidence files' hashes.

The report only reads the original run; it never changes it.
"""

import json
from pathlib import Path

from atlas.agent.execute import CandidateResult
from atlas.contracts import RunOutcome
from atlas.policy import POLICY_VERSION
from atlas.reports import sha256_file
from atlas.runner import docker as dr

MIXED_BASIS = (
    "Host trusted-fixture baseline (trusted_pipeline_only) versus Docker candidates "
    "(isolated_available): the two runs used different runners. This T-06 slice 1 comparison "
    "is labelled as such; final agent acceptance requires Docker for both the original and "
    "the candidates."
)
DOCKER_BASIS = "Original and candidates all executed in the isolated Docker runner."
READING_GUIDE = [
    "Execution status says whether the candidate ran, and how it ended, in the isolated runner.",
    (
        "Scientific outcome is the trusted evaluator's result for the full required assertion set "
        f"under {POLICY_VERSION}; it is derived only from evidence, never from the execution status."
    ),
    (
        "A completed candidate whose outcome is VIOLATION_FOUND is a normal result, and a lower "
        "score can be the honest one."
    ),
    (
        "No outcome says that the deployment claim is true; NO_VIOLATION_FOUND means only that no "
        "required check found a violation, with the limitations listed."
    ),
]
EVIDENCE_FILES = (
    "outcome.json",
    "report.json",
    "execution.json",
    "approval.json",
    "candidate.json",
    "index.json",
)


def _assertions(outcome: RunOutcome) -> list[dict]:
    return [
        {
            "assertion_id": a.assertion_id,
            "status": a.status,
            "reason": a.reason,
            "evidence_valid": a.evidence_valid,
        }
        for a in outcome.assertions
    ]


def _evidence(run_dir: Path) -> dict[str, str]:
    return {
        name: sha256_file(run_dir / name)
        for name in EVIDENCE_FILES
        if (run_dir / name).is_file()
    }


def _execution(run_dir: Path) -> dict:
    try:
        record = json.loads((run_dir / "execution.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return record if isinstance(record, dict) else {}


def _limitations(run_dir: Path) -> list:
    try:
        report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["report.json unavailable"]
    return report.get("limitations", []) if isinstance(report, dict) else []


def comparison_report(
    original_run_dir: Path, original: RunOutcome, candidates: list[CandidateResult]
) -> dict:
    original_run_dir = Path(original_run_dir)
    original_execution = _execution(original_run_dir)
    original_runner = original_execution.get("runner")
    basis = DOCKER_BASIS if original_runner == dr.RUNNER_NAME else MIXED_BASIS
    original_status = {a.assertion_id: a.status for a in original.assertions}
    entries = []
    for c in candidates:
        candidate_status = {a.assertion_id: a.status for a in c.outcome.assertions}
        ids = list(original_status) + [
            i for i in candidate_status if i not in original_status
        ]
        entries.append(
            {
                "candidate_hash": c.candidate_hash,
                "diff_sha256": c.diff_sha256,
                "approval": c.approval,
                "execution": {"runner": dr.RUNNER_NAME, **c.execution},
                "evaluated": c.evaluated,
                "scientific_outcome": c.outcome.outcome,
                "outcome_reason": c.outcome.reason,
                "required_set": _assertions(c.outcome),
                "incomplete_coverage": c.outcome.incomplete_coverage,
                "status_by_assertion": [
                    {
                        "assertion_id": i,
                        "original": original_status.get(i),
                        "candidate": candidate_status.get(i),
                    }
                    for i in ids
                ],
                "limitations": _limitations(c.candidate_dir),
                "timing": c.timing,
                "run_dir": str(c.candidate_dir),
                "evidence_sha256": _evidence(c.candidate_dir),
            }
        )
    return {
        "report": "t06-slice1-candidate-reevaluation",
        "policy_version": POLICY_VERSION,
        "model": "none (T-06 slice 1 has no model client; candidate diffs are supplied inputs)",
        "comparison_basis": basis,
        "reading_guide": READING_GUIDE,
        "original": {
            "runner": original_runner,
            "capability": original_execution.get("capability"),
            "scientific_outcome": original.outcome,
            "outcome_reason": original.reason,
            "required_set": _assertions(original),
            "incomplete_coverage": original.incomplete_coverage,
            "limitations": _limitations(original_run_dir),
            "run_dir": str(original_run_dir),
            "evidence_sha256": _evidence(original_run_dir),
        },
        "candidates": entries,
    }
