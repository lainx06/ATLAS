"""Versioned evaluation policy: required assertions, materialization, outcome (SPEC §5, §6)."""

from typing import Any

from atlas.contracts import AssertionResult, Manifest, Outcome, Reason, Status

# v1.1 (2026-10-14): split.repeated_measures_rule clarified (explicit routes, same-fold
# witnesses, no inherited aggregate statuses). Assertion IDs unchanged.
POLICY_VERSION = "policy-v1.1"
SUPPORTED_CLAIM_TYPES = ("same_population", "unseen_group", "future_time")

# Assertions that this build computes. Every other required assertion is materialized as
# NOT_ASSESSED(unimplemented_assertion); none is dropped (F1, T-01).
IMPLEMENTED = frozenset(
    {
        "split.no_row_overlap",
        "split.no_shared_source_observation",
        "split.no_group_overlap",
        "split.sampling_unit_disjoint",
        "split.repeated_measures_rule",
        "fit.state_dependencies_within_fold_train",
        "fit.coverage_complete",
        "metric.prediction_ids_match_eval_ids",
    }
)


def supported_claim(claim_type: Any) -> bool:
    return isinstance(claim_type, str) and claim_type in SUPPORTED_CLAIM_TYPES


def required_assertions(manifest: Manifest) -> list[str]:
    """The full required set for the confirmed claim, from the policy-v1 table in SPEC §5.

    Applicability depends on the claim and its declared dependence, never on which
    metadata columns happen to be present.
    """
    claim_type = manifest.claim.type
    kinds = manifest.dependence_kinds()
    required = [
        "split.no_row_overlap",
        "split.no_shared_source_observation",
    ]
    if claim_type == "unseen_group":
        required.append("split.no_group_overlap")
    if manifest.claim.sampling_unit != "row":
        required.append("split.sampling_unit_disjoint")
    if "repeated_measures" in kinds:
        required.append("split.repeated_measures_rule")
    if "overlapping_windows" in kinds:
        required.append("split.no_window_overlap")
    if "temporal_order" in kinds and claim_type in ("same_population", "unseen_group"):
        required.append("split.temporal_separation")
    required += [
        "fit.state_dependencies_within_fold_train",
        "fit.coverage_complete",
        "metric.prediction_ids_match_eval_ids",
    ]
    if manifest.reported_metrics:
        required.append("metric.reported_matches_recomputed")
    if claim_type == "future_time":
        required += [
            "temporal.training_labels_available_by_cutoff",
            "temporal.cutoff_precedes_evaluation",
            "temporal.features_available_when_used",
        ]
    return required


def materialize(
    required: list[str], computed: dict[str, AssertionResult]
) -> list[AssertionResult]:
    """One result per required assertion, in policy order; missing ones become NOT_ASSESSED."""
    results = []
    for aid in required:
        if aid in computed:
            results.append(computed[aid])
        elif aid in IMPLEMENTED:
            # Implemented but no result was produced: the evaluation never ran far enough.
            results.append(
                AssertionResult(
                    assertion_id=aid,
                    status=Status.NOT_ASSESSED,
                    reason=Reason.NOT_EXECUTED,
                )
            )
        else:
            results.append(
                AssertionResult(
                    assertion_id=aid,
                    status=Status.NOT_ASSESSED,
                    reason=Reason.UNIMPLEMENTED_ASSERTION,
                )
            )
    return results


def derive_outcome(results: list[AssertionResult]) -> Outcome:
    """SPEC §6 for a supported claim. A FAIL or PASS on invalid evidence counts as ERROR."""
    if any(r.status is Status.FAIL and r.evidence_valid for r in results):
        return Outcome.VIOLATION_FOUND
    if not results:
        return Outcome.INCONCLUSIVE
    if all(r.status is Status.PASS and r.evidence_valid for r in results):
        return Outcome.NO_VIOLATION_FOUND
    return Outcome.INCONCLUSIVE


def incomplete_coverage(results: list[AssertionResult]) -> list[str]:
    """Required assertions to display prominently as incomplete coverage."""
    return [
        r.assertion_id
        for r in results
        if r.status in (Status.NOT_ASSESSED, Status.ERROR) or not r.evidence_valid
    ]
