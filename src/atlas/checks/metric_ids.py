"""Independent metric check, identifier assertion only (SPEC §5). Trusted side.

The expected prediction inventory is the set of declared folds, never the files that happen to
exist. A missing or invalid artifact for a declared fold, or an artifact for an undeclared fold, is
ERROR; a valid artifact whose row IDs are wrong is FAIL, and such a FAIL survives ERRORs elsewhere.
Metric recomputation, baselines and reported-metric comparison are T-02.
"""

from atlas.contracts import AssertionResult, EvidenceRef, Reason, Status

AID = "metric.prediction_ids_match_eval_ids"


def prediction_id_assertions(
    splits: list[dict],
    artifacts: dict[str, list[str] | None],
    evidence: list[EvidenceRef],
    evidence_valid: bool = True,
    *,
    unexpected_artifacts: list[str] = (),
    inventory_issues: list[str] = (),
) -> dict[str, AssertionResult]:
    """`artifacts`: declared fold -> row IDs from a verified artifact, or None if present but
    invalid. `unexpected_artifacts`: prediction paths outside the expected inventory; they are
    evidence errors and are never treated as fold data."""
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

    declared = [s["fold"] for s in splits]
    missing_or_invalid, mismatches = [], {}
    for s in splits:
        rows = artifacts.get(s["fold"])
        if rows is None:
            missing_or_invalid.append(s["fold"])
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
    not_declared = sorted(set(artifacts) - set(declared))
    observed = {
        "missing_or_invalid_artifacts": missing_or_invalid,
        "unexpected_artifacts": sorted(unexpected_artifacts),
        "inventory_issues": list(inventory_issues),
        "mismatches": mismatches,
        "folds": len(splits),
    }
    if not_declared:
        observed["artifacts_keyed_to_undeclared_folds"] = not_declared
    # Evidence-backed by valid artifacts; survives missing artifacts elsewhere.
    if mismatches:
        return {
            AID: AssertionResult(
                assertion_id=AID,
                status=Status.FAIL,
                observed=observed,
                evidence=evidence,
            )
        }
    if missing_or_invalid or unexpected_artifacts or inventory_issues or not_declared:
        return {
            AID: AssertionResult(
                assertion_id=AID,
                status=Status.ERROR,
                reason=Reason.EVIDENCE_INVALID,
                observed=observed,
                evidence=evidence,
                evidence_valid=False,
            )
        }
    return {
        AID: AssertionResult(
            assertion_id=AID, status=Status.PASS, observed=observed, evidence=evidence
        )
    }
