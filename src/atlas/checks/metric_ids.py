"""Independent metric check, identifier assertion only (SPEC §5). Trusted side.

Metric recomputation, baselines and reported-metric comparison are T-02.
"""

from atlas.contracts import AssertionResult, EvidenceRef, Reason, Status

AID = "metric.prediction_ids_match_eval_ids"


def prediction_id_assertions(
    splits: list[dict],
    predictions: dict[str, list[str]],
    evidence: list[EvidenceRef],
    evidence_valid: bool = True,
) -> dict[str, AssertionResult]:
    if not evidence_valid:
        return {
            AID: AssertionResult(
                assertion_id=AID,
                status=Status.ERROR,
                reason=Reason.EVIDENCE_INVALID,
                evidence=evidence,
                evidence_valid=False,
            )
        }
    if not splits:
        return {
            AID: AssertionResult(
                assertion_id=AID,
                status=Status.NOT_ASSESSED,
                reason=Reason.NOT_EXECUTED,
                evidence=evidence,
            )
        }

    missing_folds, mismatches = [], {}
    for s in splits:
        rows = predictions.get(s["fold"])
        if rows is None:
            missing_folds.append(s["fold"])
            continue
        expected = set(s["eval_ids"])
        problems = {}
        if len(rows) != len(set(rows)):
            problems["duplicate_prediction_rows"] = len(rows) - len(set(rows))
        if expected - set(rows):
            problems["missing_eval_rows"] = sorted(expected - set(rows))[:10]
        if set(rows) - expected:
            problems["unexpected_rows"] = sorted(set(rows) - expected)[:10]
        if problems:
            mismatches[s["fold"]] = problems
    failed = bool(missing_folds or mismatches)
    return {
        AID: AssertionResult(
            assertion_id=AID,
            status=Status.FAIL if failed else Status.PASS,
            observed={
                "folds_without_predictions": missing_folds,
                "mismatches": mismatches,
                "folds": len(splits),
            },
            evidence=evidence,
        )
    }
