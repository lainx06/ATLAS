"""Independent metrics: definitions, completeness, tolerance and baselines (SPEC §8, policy-v1.3)."""

import math
from fractions import Fraction

import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.metrics import balanced_accuracy_score, f1_score

from atlas.checks.independent_metrics import (
    BASELINES,
    CLASS_SUPPORT,
    RECOMPUTED,
    REPORTED,
    metric_assertions,
)
from atlas.contracts import EvidenceRef, Manifest, Reason, Status
from atlas.evaluator import (
    balanced_accuracy,
    canonical_label,
    macro_f1,
    most_frequent,
    within_tolerance,
)

EVIDENCE = [EvidenceRef(artifact="splits.json", sha256="x")]
CLASSES = {"0": "a", "1": "b", "2": "c"}
ORDER = list(CLASSES)
P, F, N, E = Status.PASS, Status.FAIL, Status.NOT_ASSESSED, Status.ERROR

# Worked examples E1 and E2 (docs/specs/t02-contract.md §8)
E1 = ([0, 0, 0, 1, 1, 2], [0, 0, 1, 1, 1, 0])
E2 = ([0, 0, 1, 1], [0, 2, 1, 1])
E1_TRAIN = [0, 0, 1, 1, 1, 2]


def _keys(values):
    return [str(v) for v in values]


# --- definitions --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("example", "ba", "f1"),
    [(E1, Fraction(5, 9), Fraction(22, 45)), (E2, Fraction(3, 4), Fraction(5, 9))],
    ids=["E1", "E2_absent_class"],
)
def test_hand_computed_metrics(example, ba, f1):
    y_true, y_pred = map(_keys, example)

    assert balanced_accuracy(y_true, y_pred, ORDER) == pytest.approx(
        float(ba), abs=1e-15
    )
    assert macro_f1(y_true, y_pred, ORDER) == pytest.approx(float(f1), abs=1e-15)


@pytest.mark.filterwarnings("ignore:y_pred contains classes not in y_true")
@pytest.mark.parametrize("example", [E1, E2], ids=["E1", "E2"])
def test_definitions_agree_with_scikit_learn_defaults(example):
    y_true, y_pred = example

    assert balanced_accuracy(_keys(y_true), _keys(y_pred), ORDER) == pytest.approx(
        balanced_accuracy_score(y_true, y_pred), abs=1e-15
    )
    assert macro_f1(_keys(y_true), _keys(y_pred), ORDER) == pytest.approx(
        f1_score(y_true, y_pred, average="macro", zero_division=0), abs=1e-15
    )


@pytest.mark.parametrize(
    ("value", "key"),
    [
        ("1", "1"),
        (1, "1"),
        (1.0, "1"),  # an integer column with nulls is read as float
        (True, None),
        (1.5, None),
        (math.nan, None),
        (None, None),
        ("b", None),  # a class name, not a key
        (3, None),  # outside the universe
    ],
)
def test_canonical_labels(value, key):
    assert canonical_label(value, CLASSES) == key


# --- tolerance: the literal float64 rule ----------------------------------------------------------


def test_tolerance_boundary_and_adjacent_representable_values():
    boundary = 1e-6

    assert within_tolerance(boundary, 0.0)  # equality passes
    assert within_tolerance(math.nextafter(boundary, 0.0), 0.0)
    assert not within_tolerance(math.nextafter(boundary, 1.0), 0.0)
    assert within_tolerance(0.0, boundary)  # symmetric


def test_decimal_intended_equality_can_fall_outside_after_representation():
    recomputed = 5 / 9
    reported = 5 / 9 + 1e-6

    assert abs(reported - recomputed) == 1.0000000000287557e-06
    assert not within_tolerance(reported, recomputed)


@pytest.mark.parametrize(
    ("offset", "passes"), [(2e-6, False), (5e-7, True)], ids=["2e-6", "5e-7"]
)
def test_task_acceptance_offsets(offset, passes):
    assert within_tolerance(5 / 9 + offset, 5 / 9) is passes


# --- reported_matches_recomputed through the assertion ---------------------------------------------


def _manifest(reported, class_map=None):
    return Manifest.model_validate(
        {
            "schema_version": "0.3",
            "table": {"path": "t.csv", "format": "csv"},
            "columns": {
                "row_id": "row_id",
                "target": "y",
                "class_map": class_map or CLASSES,
                "features": ["f0"],
            },
            "claim": {
                "type": "same_population",
                "statement": "s",
                "sampling_unit": "row",
                "dependence": [],
            },
            "primary_metric": "balanced_accuracy",
            "development_seeds": [0],
            "entry_point": "evaluate.py",
            "reported_metrics": reported,
        }
    )


def _entry(
    value,
    fold="all",
    aggregation="mean_over_folds",
    name="balanced_accuracy",
    partition="development_eval",
):
    return {
        "metric_definition": name,
        "partition": partition,
        "fold": fold,
        "aggregation": aggregation,
        "value": value,
    }


def _fixture(fold_examples, train_labels=None):
    """Folds from (y_true, y_pred) examples; training rows are separate rows."""
    rows, splits, predictions = {}, [], {}
    for k, (y_true, y_pred) in enumerate(fold_examples):
        eval_ids = [f"e{k}_{i}" for i in range(len(y_true))]
        train = train_labels or [0, 1]
        train_ids = [f"t{k}_{i}" for i in range(len(train))]
        rows |= {r: {"y": y, "f0": 0.0} for r, y in zip(eval_ids, y_true, strict=True)}
        rows |= {r: {"y": y, "f0": 0.0} for r, y in zip(train_ids, train, strict=True)}
        splits.append(
            {
                "fold": f"fold{k}",
                "kind": "development_eval",
                "train_ids": train_ids,
                "eval_ids": eval_ids,
            }
        )
        predictions[f"fold{k}"] = pd.DataFrame({"row_id": eval_ids, "y_pred": y_pred})
    table = pd.DataFrame.from_dict(rows, orient="index").rename_axis("row_id")
    return table, splits, predictions


def _reported(entries, table, splits, predictions):
    computed, descriptive = metric_assertions(
        _manifest(entries), table, splits, predictions, EVIDENCE
    )
    return computed[REPORTED], {d.result_id: d for d in descriptive}


def test_aggregates_match_the_hand_computed_e3_values():
    table, splits, preds = _fixture([E1, E2])
    entries = [
        _entry(float(Fraction(47, 72))),
        _entry(float(Fraction(47, 90)), name="macro_f1"),
        _entry(float(Fraction(8, 15)), aggregation="pooled"),
        _entry(float(Fraction(14, 27)), name="macro_f1", aggregation="pooled"),
        _entry(float(Fraction(5, 9)), fold="fold0", aggregation="single_fold"),
    ]

    result, _ = _reported(entries, table, splits, preds)

    assert result.status is P, result.observed["entries"]
    assert result.depends_on == ["metric.prediction_ids_match_eval_ids"]


def test_pooled_counts_a_repeated_row_once_per_evaluation_occurrence():
    table, splits, preds = _fixture([E1, E1])
    splits[1]["eval_ids"] = splits[0][
        "eval_ids"
    ]  # the same rows evaluated in both folds
    preds["fold1"] = preds["fold0"].copy()

    result, _ = _reported([_entry(5 / 9, aggregation="pooled")], table, splits, preds)

    recomputed = result.observed["entries"][0]["recomputed"]
    assert recomputed["observations"] == 12
    assert recomputed["rows_counted_more_than_once"] == 6


def test_missing_fold_is_never_dropped_from_an_aggregate():
    table, splits, preds = _fixture([E1, E2])
    del preds["fold1"]  # missing or invalid artifact
    fold0_only = balanced_accuracy(*map(_keys, E1), ORDER)

    result, descriptive = _reported([_entry(fold0_only)], table, splits, preds)

    assert (result.status, result.reason) == (E, Reason.EVIDENCE_INVALID)
    entry = result.observed["entries"][0]
    assert entry["recomputed"]["complete"] is False
    assert entry["recomputed"]["unusable_folds"][0]["fold"] == "fold1"
    per_fold = descriptive[RECOMPUTED].observed["per_fold"]
    assert per_fold[0]["usable"] and per_fold[0]["balanced_accuracy"] == fold0_only


def test_empty_fold_makes_an_aggregate_not_assessed():
    table, splits, preds = _fixture([E1, E2])
    splits[1]["eval_ids"] = []
    preds["fold1"] = pd.DataFrame({"row_id": [], "y_pred": []})

    result, _ = _reported([_entry(0.5)], table, splits, preds)

    assert (result.status, result.reason) == (N, Reason.EMPTY_EVALUATION)


@pytest.mark.parametrize(
    "bad_prediction",
    [3, "b", None, True],
    ids=["outside", "class_name", "null", "boolean"],
)
def test_invalid_prediction_is_an_evidence_error(bad_prediction):
    table, splits, preds = _fixture([E1])
    preds["fold0"]["y_pred"] = preds["fold0"]["y_pred"].astype(object)
    preds["fold0"].loc[0, "y_pred"] = bad_prediction

    result, _ = _reported(
        [_entry(0.5, fold="fold0", aggregation="single_fold")], table, splits, preds
    )

    assert (result.status, result.reason) == (E, Reason.EVIDENCE_INVALID)
    unusable = result.observed["entries"][0]["recomputed"]["unusable_folds"]
    assert "prediction outside the class_map keys" in unusable[0]["detail"]


def test_prediction_rows_must_equal_the_declared_evaluation_rows():
    table, splits, preds = _fixture([E1])
    preds["fold0"] = preds["fold0"].iloc[1:]

    result, _ = _reported(
        [_entry(0.5, fold="fold0", aggregation="single_fold")], table, splits, preds
    )

    assert (result.status, result.reason) == (E, Reason.EVIDENCE_INVALID)


def test_valid_fail_survives_an_error_in_another_entry():
    table, splits, preds = _fixture([E1, E2])
    del preds["fold1"]
    entries = [
        _entry(0.9, fold="fold0", aggregation="single_fold"),  # recomputed 5/9: FAIL
        _entry(0.5),  # needs fold1: ERROR
    ]

    result, _ = _reported(entries, table, splits, preds)

    assert result.status is F and result.evidence_valid
    assert [e["status"] for e in result.observed["entries"]] == [F, E]


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        (_entry(0.5, partition="final_holdout"), (N, Reason.NOT_EXECUTED)),
        (
            _entry(0.5, fold="fold9", aggregation="single_fold"),
            (E, Reason.EVIDENCE_INVALID),
        ),
    ],
    ids=["final_holdout", "undeclared_fold"],
)
def test_unrecomputable_entries(entry, expected):
    table, splits, preds = _fixture([E1])

    result, _ = _reported([entry], table, splits, preds)

    assert (result.status, result.reason) == expected


def test_fold_named_all_makes_fold_all_ambiguous():
    table, splits, preds = _fixture([E1])
    splits[0]["fold"] = "all"
    preds = {"all": preds["fold0"]}

    result, _ = _reported([_entry(0.5)], table, splits, preds)

    assert (result.status, result.reason) == (E, Reason.EVIDENCE_INVALID)


def test_reported_value_is_compared_through_the_literal_rule():
    # All four predictions wrong: recomputed balanced accuracy is exactly 0.
    table, splits, preds = _fixture([([0, 0, 1, 1], [1, 1, 0, 0])])
    single = {"fold": "fold0", "aggregation": "single_fold"}

    at_boundary, _ = _reported([_entry(1e-6, **single)], table, splits, preds)
    beyond, _ = _reported(
        [_entry(math.nextafter(1e-6, 1.0), **single)], table, splits, preds
    )

    assert at_boundary.status is P
    assert beyond.status is F


# --- baselines and class support ------------------------------------------------------------


def test_dummy_baseline_matches_the_worked_example():
    table, splits, preds = _fixture([E1], train_labels=E1_TRAIN)

    _, descriptive = _reported([_entry(0.5)], table, splits, preds)

    dummy = descriptive[BASELINES].observed["dummy"]
    fold = dummy["per_fold"][0]
    assert fold["detail"] == "predicts '1'"
    assert fold["balanced_accuracy"] == pytest.approx(1 / 3, abs=1e-15)
    assert fold["macro_f1"] == pytest.approx(1 / 6, abs=1e-15)
    sk = DummyClassifier(strategy="most_frequent").fit([[0]] * 6, E1_TRAIN)
    assert str(sk.predict([[0]])[0]) == "1"  # no tie here, so the rules agree
    assert descriptive[BASELINES].observed["linear"]["computed"] is False


def test_baseline_ties_follow_the_declared_class_map_order():
    assert most_frequent(["0", "1", "1", "0"], ["1", "0"]) == "1"
    assert most_frequent(["0", "1", "1", "0"], ["0", "1"]) == "0"


@pytest.mark.parametrize(
    ("train", "why"),
    [([], "empty training partition"), (["x", 0], "invalid training labels")],
    ids=["empty", "invalid"],
)
def test_baseline_is_unavailable_rather_than_invented(train, why):
    table, splits, preds = _fixture([E1])
    for r in splits[0]["train_ids"]:
        table = table.drop(index=r)
    train_ids = [f"tt{i}" for i in range(len(train))]
    extra = pd.DataFrame({"y": train, "f0": [0.0] * len(train)}, index=train_ids)
    table = pd.concat([table.astype(object), extra.astype(object)]).rename_axis(
        "row_id"
    )
    splits[0]["train_ids"] = train_ids

    _, descriptive = _reported([_entry(0.5)], table, splits, preds)

    fold = descriptive[BASELINES].observed["dummy"]["per_fold"][0]
    assert fold["usable"] is False and why in fold["detail"]
    assert fold["balanced_accuracy"] is None
    mean = descriptive[BASELINES].observed["dummy"]["aggregates"]["development_eval"]
    assert mean["balanced_accuracy"]["mean_over_folds"]["complete"] is False


def test_class_support_reports_absent_classes_and_unavailable_splitter_requirements():
    table, splits, preds = _fixture([E2])

    _, descriptive = _reported([_entry(0.5)], table, splits, preds)

    support = descriptive[CLASS_SUPPORT].observed
    assert support["folds"][0]["absent_in_eval"] == ["2"]
    assert support["splitter_minimum_requirements"].startswith("unavailable")


def test_no_reported_metrics_means_no_reported_assertion():
    table, splits, preds = _fixture([E1])

    computed, descriptive = metric_assertions(
        _manifest([]), table, splits, preds, EVIDENCE
    )

    assert REPORTED not in computed
    assert {d.result_id for d in descriptive} == {RECOMPUTED, BASELINES, CLASS_SUPPORT}


def test_invalid_evidence_gives_error_and_unavailable_descriptive_results():
    table, splits, preds = _fixture([E1])

    computed, descriptive = metric_assertions(
        _manifest([_entry(0.5)]), table, splits, preds, EVIDENCE, evidence_valid=False
    )

    assert computed[REPORTED].status is E
    assert not any(d.available for d in descriptive)
