"""Split integrity: row, source-observation, group, sampling-unit and repeated-measures rules.

Runs in the trusted evaluator on the evaluator's own table copy and the declared splits.
"""

from collections.abc import Iterable

import pandas as pd

from atlas.contracts import AssertionResult, EvidenceRef, Manifest, Reason, Status

ASSERTIONS = (
    "split.no_row_overlap",
    "split.no_shared_source_observation",
    "split.no_group_overlap",
    "split.sampling_unit_disjoint",
    "split.repeated_measures_rule",
)
_SEVERITY = {Status.FAIL: 3, Status.ERROR: 2, Status.NOT_ASSESSED: 1, Status.PASS: 0}


def split_assertions(
    manifest: Manifest,
    table: pd.DataFrame,
    splits: list[dict],
    evidence: list[EvidenceRef],
    evidence_valid: bool = True,
) -> dict[str, AssertionResult]:
    """Compute every split assertion; the policy decides which are required."""
    if not evidence_valid:
        return {
            aid: AssertionResult(
                assertion_id=aid,
                status=Status.ERROR,
                reason=Reason.EVIDENCE_INVALID,
                evidence=evidence,
                evidence_valid=False,
            )
            for aid in ASSERTIONS
        }
    if not splits:
        return {
            aid: AssertionResult(
                assertion_id=aid,
                status=Status.NOT_ASSESSED,
                reason=Reason.NOT_EXECUTED,
                observed={"declared_folds": 0},
                evidence=evidence,
            )
            for aid in ASSERTIONS
        }

    results = {
        "split.no_row_overlap": _row_overlap(splits, evidence),
        "split.no_shared_source_observation": _shared_observation(
            manifest, table, splits, evidence
        ),
    }
    group_col = manifest.columns.group_id
    results["split.no_group_overlap"] = _unit_overlap(
        "split.no_group_overlap",
        "overlapping_groups",
        group_col,
        table,
        splits,
        evidence,
    )
    results["split.sampling_unit_disjoint"] = _unit_overlap(
        "split.sampling_unit_disjoint",
        "overlapping_units",
        manifest.columns.unit_id,
        table,
        splits,
        evidence,
    )
    results["split.repeated_measures_rule"] = _repeated_measures(
        manifest, table, splits, results, evidence
    )
    return results


def _units(ids: Iterable[str], unit_of: pd.Series) -> set:
    """Known identity values only; missing (null) values are excluded and counted separately."""
    return {unit_of[r] for r in ids if not pd.isna(unit_of[r])}


def _overlap_by(
    column: str, table: pd.DataFrame, splits: list[dict]
) -> dict[str, list]:
    unit_of = table[column]
    found = {}
    for s in splits:
        shared = _units(s["train_ids"], unit_of) & _units(s["eval_ids"], unit_of)
        if shared:
            found[s["fold"]] = sorted(map(str, shared))
    return found


def _unknown_identity(
    column: str, table: pd.DataFrame, splits: list[dict]
) -> dict[str, int]:
    """Participating rows whose identity value is missing, per fold."""
    missing = table[column].isna()
    found = {}
    for s in splits:
        n = int(sum(bool(missing[r]) for r in [*s["train_ids"], *s["eval_ids"]]))
        if n:
            found[s["fold"]] = n
    return found


def _row_overlap_by_fold(splits: list[dict]) -> dict[str, list]:
    found = {}
    for s in splits:
        shared = set(s["train_ids"]) & set(s["eval_ids"])
        if shared:
            found[s["fold"]] = sorted(shared)
    return found


def _row_overlap(splits: list[dict], evidence: list[EvidenceRef]) -> AssertionResult:
    found = _row_overlap_by_fold(splits)
    return AssertionResult(
        assertion_id="split.no_row_overlap",
        status=Status.FAIL if found else Status.PASS,
        observed={"overlapping_rows": found, "folds": len(splits)},
        evidence=evidence,
    )


def _unit_overlap(
    aid: str,
    key: str,
    column: str | None,
    table: pd.DataFrame,
    splits: list[dict],
    evidence: list[EvidenceRef],
) -> AssertionResult:
    if column is None or column not in table.columns:
        return AssertionResult(
            assertion_id=aid,
            status=Status.NOT_ASSESSED,
            reason=Reason.MISSING_METADATA,
            observed={"column": column},
            evidence=evidence,
        )
    overlap = _overlap_by(column, table, splits)  # compares unit values, never row IDs
    unknown = _unknown_identity(column, table, splits)
    observed = {
        key: overlap,
        "column": column,
        "folds": len(splits),
        "rows_with_unknown_identity": unknown,
    }
    if overlap:  # a violation among known identities stands
        return AssertionResult(
            assertion_id=aid, status=Status.FAIL, observed=observed, evidence=evidence
        )
    if unknown:
        return AssertionResult(
            assertion_id=aid,
            status=Status.NOT_ASSESSED,
            reason=Reason.MISSING_METADATA,
            observed=observed,
            evidence=evidence,
        )
    return AssertionResult(
        assertion_id=aid, status=Status.PASS, observed=observed, evidence=evidence
    )


def _duplicate_candidates(
    manifest: Manifest, table: pd.DataFrame, splits: list[dict]
) -> dict[str, list]:
    """Train/eval row pairs with identical feature and target values (candidates only, L2)."""
    value_cols = [*manifest.columns.features, manifest.columns.target]
    keys = table[value_cols].apply(lambda row: tuple(row.tolist()), axis=1)
    found = {}
    for s in splits:
        by_key: dict[tuple, list[str]] = {}
        for r in s["train_ids"]:
            by_key.setdefault(keys[r], []).append(r)
        pairs = [[t, e] for e in s["eval_ids"] for t in by_key.get(keys[e], [])]
        if pairs:
            found[s["fold"]] = sorted(pairs)
    return found


def _shared_observation(
    manifest: Manifest,
    table: pd.DataFrame,
    splits: list[dict],
    evidence: list[EvidenceRef],
) -> AssertionResult:
    aid = "split.no_shared_source_observation"
    candidates = _duplicate_candidates(manifest, table, splits)
    observed: dict = {"duplicate_candidates": candidates}

    shared: dict[str, list] = {}
    obs_col = manifest.columns.observation_id
    if obs_col is not None:
        if obs_col not in table.columns:
            return AssertionResult(
                assertion_id=aid,
                status=Status.NOT_ASSESSED,
                reason=Reason.MISSING_METADATA,
                observed={**observed, "column": obs_col},
                evidence=evidence,
            )
        shared.update(_overlap_by(obs_col, table, splits))
        observed["rows_with_unknown_identity"] = _unknown_identity(
            obs_col, table, splits
        )
    documented = []
    for group in manifest.known_duplicates:
        members = set(group)
        for s in splits:
            if members & set(s["train_ids"]) and members & set(s["eval_ids"]):
                documented.append({"fold": s["fold"], "rows": sorted(members)})
    observed.update(
        {
            "shared_observation_ids": shared,
            "documented_duplicates_across_partitions": documented,
        }
    )

    if shared or documented:
        return AssertionResult(
            assertion_id=aid, status=Status.FAIL, observed=observed, evidence=evidence
        )
    if obs_col is not None and observed["rows_with_unknown_identity"]:
        return AssertionResult(
            assertion_id=aid,
            status=Status.NOT_ASSESSED,
            reason=Reason.MISSING_METADATA,
            observed=observed,
            evidence=evidence,
        )
    if obs_col is not None:
        return AssertionResult(
            assertion_id=aid, status=Status.PASS, observed=observed, evidence=evidence
        )
    if candidates:
        return AssertionResult(
            assertion_id=aid,
            status=Status.NOT_ASSESSED,
            reason=Reason.UNRESOLVED_DUPLICATE_CANDIDATES,
            observed=observed,
            evidence=evidence,
            limitations=[
                "Equal feature/target values do not establish a shared source observation."
            ],
        )
    return AssertionResult(
        assertion_id=aid,
        status=Status.PASS,
        observed=observed,
        evidence=evidence,
        limitations=[
            "exact-value screen only: no source-observation identity declared; near-duplicates not assessed"
        ],
    )


def _repeated_measures(
    manifest: Manifest,
    table: pd.DataFrame,
    splits: list[dict],
    results: dict[str, AssertionResult],
    evidence: list[EvidenceRef],
) -> AssertionResult:
    """Assess each declared repeated-measures unit only through a supported rule (F3)."""
    aid = "split.repeated_measures_rule"
    cols = manifest.columns
    per_unit = []
    for dep in manifest.claim.dependence:
        if dep.kind != "repeated_measures":
            continue
        col = dep.column
        if (
            col is None
            or col not in table.columns
            or _unknown_identity(col, table, splits)
        ):
            per_unit.append((col, Status.NOT_ASSESSED, Reason.MISSING_METADATA, None))
        elif cols.unit_id is not None and col == cols.unit_id:
            follow = results["split.sampling_unit_disjoint"]
            per_unit.append(
                (col, follow.status, follow.reason, "split.sampling_unit_disjoint")
            )
        elif manifest.claim.type == "unseen_group":
            group = cols.group_id
            if group is None or group not in table.columns:
                per_unit.append(
                    (col, Status.NOT_ASSESSED, Reason.MISSING_METADATA, None)
                )
            elif (
                table.groupby(col)[group].nunique().max() == 1
            ):  # containment shown from the table
                follow = results["split.no_group_overlap"]
                per_unit.append(
                    (col, follow.status, follow.reason, "split.no_group_overlap")
                )
            else:
                per_unit.append(
                    (col, Status.NOT_ASSESSED, Reason.NO_SUPPORTED_RULE, None)
                )
        else:
            per_unit.append((col, Status.NOT_ASSESSED, Reason.NO_SUPPORTED_RULE, None))

    if not per_unit:
        return AssertionResult(
            assertion_id=aid,
            status=Status.NOT_ASSESSED,
            reason=Reason.MISSING_METADATA,
            evidence=evidence,
        )
    worst = max(per_unit, key=lambda u: _SEVERITY[u[1]])
    return AssertionResult(
        assertion_id=aid,
        status=worst[1],
        reason=worst[2] if worst[1] is Status.NOT_ASSESSED else None,
        observed={
            "units": [{"column": c, "status": s, "rule": d} for c, s, _, d in per_unit]
        },
        evidence=evidence,
        depends_on=sorted({d for *_, d in per_unit if d}),
    )
