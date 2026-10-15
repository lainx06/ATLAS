"""Independent metrics (SPEC §5, §8; policy-v1.3). Trusted side.

`metric.reported_matches_recomputed` is required when the manifest declares reported metrics.
`metric.recomputed_primary`, `metric.baselines` and `split.class_support` are descriptive: they
are reported and never enter outcome derivation.

True labels come from the evaluator's own table copy; predictions from the verified
`predictions/<fold>.parquet` artifacts, matched by row ID. An empty, invalid or missing required
fold is never silently left out of an aggregate: an incomplete aggregate cannot support PASS.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from atlas.contracts import (
    AssertionResult,
    DescriptiveResult,
    EvidenceRef,
    Manifest,
    Reason,
    ReportedMetric,
    Status,
)
from atlas.evaluator import (
    METRICS,
    TOLERANCE,
    canonical_label,
    metric,
    most_frequent,
    within_tolerance,
)

REPORTED = "metric.reported_matches_recomputed"
RECOMPUTED = "metric.recomputed_primary"
BASELINES = "metric.baselines"
CLASS_SUPPORT = "split.class_support"
RULE = (
    "abs(reported - recomputed) <= 1e-6 in float64; no relative tolerance, rounding or "
    "extra epsilon"
)
_SEVERITY = {Status.FAIL: 3, Status.ERROR: 2, Status.NOT_ASSESSED: 1, Status.PASS: 0}


@dataclass
class FoldScore:
    """One fold's labels and metric values, or why they are unavailable."""

    fold: str
    kind: str
    status: Status | None = None  # None: usable; otherwise ERROR or NOT_ASSESSED
    reason: Reason | None = None
    detail: str | None = None
    y_true: list[str] = field(default_factory=list)
    y_pred: list[str] = field(default_factory=list)
    rows: list[str] = field(default_factory=list)  # evaluated row IDs, in y_true order
    values: dict[str, float] = field(default_factory=dict)

    def summary(self) -> dict:
        return {
            "fold": self.fold,
            "kind": self.kind,
            "usable": self.status is None,
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            **{m: self.values.get(m) for m in METRICS},
        }


def _kind(split: dict) -> str:
    return split.get("kind", "development_eval")


def _problem(score: FoldScore, status: Status, reason: Reason, detail: str):
    score.status, score.reason, score.detail = status, reason, detail
    return score


def _labels(table, manifest, ids) -> list[str | None]:
    class_map = manifest.columns.class_map
    return [
        canonical_label(v, class_map) for v in table.loc[ids, manifest.columns.target]
    ]


def score_fold(manifest: Manifest, table, split: dict, frame) -> FoldScore:
    """Recompute one fold from the evaluator's labels and the fold's prediction artifact.

    `frame` is the verified artifact, or None when it is missing or failed verification.
    """
    score = FoldScore(fold=split["fold"], kind=_kind(split))
    evaluated = split["eval_ids"]
    invalid = (Status.ERROR, Reason.EVIDENCE_INVALID)
    if not evaluated:
        return _problem(
            score,
            Status.NOT_ASSESSED,
            Reason.EMPTY_EVALUATION,
            "evaluation partition is empty",
        )
    if frame is None:
        return _problem(score, *invalid, "prediction artifact missing or invalid")
    if not {"row_id", "y_pred"} <= set(frame.columns):
        return _problem(score, *invalid, "prediction artifact lacks row_id/y_pred")
    rows = [str(r) for r in frame["row_id"]]
    if len(rows) != len(set(rows)) or set(rows) != set(evaluated):
        return _problem(
            score, *invalid, "prediction rows differ from the declared evaluation rows"
        )
    if any(r not in table.index for r in evaluated):
        return _problem(score, *invalid, "evaluation rows absent from the label copy")
    y_true = _labels(table, manifest, evaluated)
    if None in y_true:
        return _problem(score, *invalid, "true label outside the class_map keys")
    predicted = dict(zip(rows, frame["y_pred"], strict=True))
    class_map = manifest.columns.class_map
    y_pred = [canonical_label(predicted[r], class_map) for r in evaluated]
    if None in y_pred:
        return _problem(score, *invalid, "prediction outside the class_map keys")
    order = list(class_map)
    score.y_true, score.y_pred, score.rows = y_true, y_pred, list(evaluated)
    score.values = {m: metric(m, y_true, y_pred, order) for m in METRICS}
    return score


def aggregate(scores: list[FoldScore], how: str, name: str, order: list[str]) -> dict:
    """A single-fold, mean-over-folds or pooled value, or why it is incomplete.

    Every listed fold is required: none is silently dropped. Pooled observations are the
    concatenated (fold, row) pairs, so a row evaluated in several folds counts once per occurrence.
    """
    if not scores:
        return {
            "complete": False,
            "status": Status.NOT_ASSESSED,
            "reason": Reason.NOT_EXECUTED,
            "detail": "no declared fold of this partition",
        }
    problems = [s for s in scores if s.status is not None]
    if problems:
        error = any(s.status is Status.ERROR for s in problems)
        return {
            "complete": False,
            "status": Status.ERROR if error else Status.NOT_ASSESSED,
            "reason": Reason.EVIDENCE_INVALID if error else problems[0].reason,
            "detail": "incomplete aggregate: a required fold is unusable",
            "unusable_folds": [
                {
                    "fold": s.fold,
                    "status": s.status,
                    "reason": s.reason,
                    "detail": s.detail,
                }
                for s in problems
            ],
        }
    if how == "single_fold":
        return {"complete": True, "value": scores[0].values[name]}
    if how == "mean_over_folds":
        return {
            "complete": True,
            "value": float(np.mean([s.values[name] for s in scores])),
            "folds": len(scores),
        }
    y_true = [t for s in scores for t in s.y_true]
    y_pred = [p for s in scores for p in s.y_pred]
    counts = pd.Series([r for s in scores for r in s.rows]).value_counts()
    return {
        "complete": True,
        "value": metric(name, y_true, y_pred, order),
        "observations": len(y_true),
        "rows_counted_more_than_once": int((counts > 1).sum()),
    }


def metric_assertions(
    manifest: Manifest,
    table,
    splits: list[dict],
    predictions: dict,
    evidence: list[EvidenceRef],
    evidence_valid: bool = True,
) -> tuple[dict[str, AssertionResult], list[DescriptiveResult]]:
    """`predictions`: declared fold -> verified prediction frame, or None (missing or invalid)."""
    if not evidence_valid or not splits:
        why = (
            "split or table evidence invalid"
            if not evidence_valid
            else "no declared folds"
        )
        computed = {}
        if manifest.reported_metrics:
            computed[REPORTED] = AssertionResult(
                assertion_id=REPORTED,
                status=Status.ERROR if not evidence_valid else Status.NOT_ASSESSED,
                reason=Reason.EVIDENCE_INVALID
                if not evidence_valid
                else Reason.NOT_EXECUTED,
                evidence=evidence,
                evidence_valid=evidence_valid,
            )
        return computed, [
            DescriptiveResult(
                result_id=rid, available=False, reason=why, evidence=evidence
            )
            for rid in (RECOMPUTED, BASELINES, CLASS_SUPPORT)
        ]

    scores = {
        s["fold"]: score_fold(manifest, table, s, predictions.get(s["fold"]))
        for s in splits
    }
    computed = {}
    if manifest.reported_metrics:
        computed[REPORTED] = _reported(manifest, splits, scores, evidence)
    descriptive = [
        _recomputed(manifest, splits, scores, evidence),
        _baselines(manifest, table, splits, evidence),
        _class_support(manifest, table, splits, evidence),
    ]
    return computed, descriptive


# --- metric.reported_matches_recomputed -------------------------------------------------------


def _entry(entry: ReportedMetric, splits, scores, order) -> dict:
    out: dict = {"entry": entry.model_dump()}
    if entry.partition == "final_holdout":
        return out | {
            "status": Status.NOT_ASSESSED,
            "reason": Reason.NOT_EXECUTED,
            "detail": "no evaluator-only holdout label store exists yet",
        }
    declared = {s["fold"]: s for s in splits}
    if entry.fold == "all":
        if "all" in declared:
            return out | {
                "status": Status.ERROR,
                "reason": Reason.EVIDENCE_INVALID,
                "detail": "a declared fold is named 'all', so fold 'all' is ambiguous",
            }
        folds = [s for s in splits if _kind(s) == entry.partition]
    else:
        split = declared.get(entry.fold)
        if split is None or _kind(split) != entry.partition:
            return out | {
                "status": Status.ERROR,
                "reason": Reason.EVIDENCE_INVALID,
                "detail": f"no declared {entry.partition} fold named {entry.fold!r}",
            }
        folds = [split]
    agg = aggregate(
        [scores[s["fold"]] for s in folds],
        entry.aggregation,
        entry.metric_definition,
        order,
    )
    out["recomputed"] = agg
    if not agg["complete"]:
        return out | {k: agg[k] for k in ("status", "reason", "detail")}
    difference = abs(entry.value - agg["value"])
    passed = within_tolerance(entry.value, agg["value"])
    return out | {
        "status": Status.PASS if passed else Status.FAIL,
        "reason": None,
        "abs_difference": difference,
    }


def _reported(manifest, splits, scores, evidence) -> AssertionResult:
    order = list(manifest.columns.class_map)
    entries = [_entry(e, splits, scores, order) for e in manifest.reported_metrics]
    worst = max(entries, key=lambda e: _SEVERITY[e["status"]])
    status = worst["status"]
    return AssertionResult(
        assertion_id=REPORTED,
        status=status,
        reason=worst["reason"]
        if status in (Status.NOT_ASSESSED, Status.ERROR)
        else None,
        observed={"tolerance": TOLERANCE, "rule": RULE, "entries": entries},
        evidence=evidence,
        depends_on=["metric.prediction_ids_match_eval_ids"],
        evidence_valid=status is not Status.ERROR,
        limitations=[
            (
                "Reported values are compared at full precision; a value rounded for display "
                "(e.g. to 4 decimals) generally differs by more than 1e-6."
            )
        ],
    )


# --- descriptive -------------------------------------------------------------------------------


def _kinds(splits) -> list[str]:
    return list(dict.fromkeys(_kind(s) for s in splits))


def _aggregates(scores_by_kind: dict, order) -> dict:
    return {
        kind: {
            name: {
                how: aggregate(scores, how, name, order)
                for how in ("mean_over_folds", "pooled")
            }
            for name in METRICS
        }
        for kind, scores in scores_by_kind.items()
    }


def _recomputed(manifest, splits, scores, evidence) -> DescriptiveResult:
    order = list(manifest.columns.class_map)
    by_kind = {
        k: [scores[s["fold"]] for s in splits if _kind(s) == k] for k in _kinds(splits)
    }
    return DescriptiveResult(
        result_id=RECOMPUTED,
        available=True,
        observed={
            "primary_metric": manifest.primary_metric,
            "per_fold": [scores[s["fold"]].summary() for s in splits],
            "aggregates": _aggregates(by_kind, order),
        },
        evidence=evidence,
        limitations=["Descriptive only; never part of the outcome."],
    )


def _baselines(manifest, table, splits, evidence) -> DescriptiveResult:
    """Most frequent training class per fold; ties by declared class_map order (SPEC §8)."""
    order = list(manifest.columns.class_map)
    per_fold, by_kind = [], {}
    for s in splits:
        score = FoldScore(fold=s["fold"], kind=_kind(s))
        train = _labels(table, manifest, s["train_ids"])
        evaluated = _labels(table, manifest, s["eval_ids"])
        unavailable = (Status.NOT_ASSESSED, Reason.NOT_EXECUTED)
        if not train:
            _problem(
                score, *unavailable, "baseline unavailable: empty training partition"
            )
        elif None in train:
            _problem(
                score, *unavailable, "baseline unavailable: invalid training labels"
            )
        elif not evaluated:
            _problem(
                score, Status.NOT_ASSESSED, Reason.EMPTY_EVALUATION, "empty evaluation"
            )
        elif None in evaluated:
            _problem(
                score, *unavailable, "baseline unavailable: invalid evaluation labels"
            )
        else:
            predicted = most_frequent(train, order)
            score.y_true, score.y_pred = evaluated, [predicted] * len(evaluated)
            score.rows = list(s["eval_ids"])
            score.values = {
                m: metric(m, score.y_true, score.y_pred, order) for m in METRICS
            }
            score.detail = f"predicts {predicted!r}"
        per_fold.append(score.summary())
        by_kind.setdefault(score.kind, []).append(score)
    return DescriptiveResult(
        result_id=BASELINES,
        available=True,
        observed={
            "dummy": {
                "strategy": (
                    "most frequent training class per fold; ties broken by the declared "
                    "class_map order (not claimed to match scikit-learn's tie rule)"
                ),
                "per_fold": per_fold,
                "aggregates": _aggregates(by_kind, order),
            },
            "linear": {
                "computed": False,
                "reason": "deferred (DECISIONS.md, 'T-02 contract dispositions', item 7)",
            },
        },
        evidence=evidence,
        limitations=[
            (
                "Descriptive only. Beating a baseline is not evidence of usefulness; falling "
                "below one is not evidence of leakage."
            )
        ],
    )


def _class_support(manifest, table, splits, evidence) -> DescriptiveResult:
    order = list(manifest.columns.class_map)
    folds = []
    for s in splits:
        row = {"fold": s["fold"], "kind": _kind(s)}
        for part in ("train", "eval"):
            labels = _labels(table, manifest, s[f"{part}_ids"])
            row[f"{part}_counts"] = {c: labels.count(c) for c in order}
            row[f"{part}_invalid_labels"] = labels.count(None)
            row[f"absent_in_{part}"] = [c for c in order if c not in labels]
        folds.append(row)
    return DescriptiveResult(
        result_id=CLASS_SUPPORT,
        available=True,
        observed={
            "folds": folds,
            "splitter_minimum_requirements": (
                "unavailable: not recorded by the recorder (SPEC §4.2)"
            ),
        },
        evidence=evidence,
        limitations=["Descriptive: missing class support is never a split violation."],
    )
