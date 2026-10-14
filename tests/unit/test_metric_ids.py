"""metric.prediction_ids_match_eval_ids (SPEC §5)."""

from atlas.checks.metric_ids import prediction_id_assertions
from atlas.contracts import EvidenceRef, Reason, Status

EVIDENCE = [
    EvidenceRef(artifact="splits.json", sha256="x"),
    EvidenceRef(artifact="predictions/f0.parquet", sha256="y"),
]
SPLITS = [
    {
        "fold": "f0",
        "kind": "development_eval",
        "train_ids": ["r0", "r1"],
        "eval_ids": ["r2", "r3"],
    }
]
AID = "metric.prediction_ids_match_eval_ids"


def test_predictions_covering_exactly_the_eval_rows_pass():
    result = prediction_id_assertions(SPLITS, {"f0": ["r3", "r2"]}, EVIDENCE)[AID]

    assert result.status is Status.PASS


def test_missing_extra_or_duplicate_prediction_rows_fail():
    for preds in (["r2"], ["r2", "r3", "r1"], ["r2", "r2", "r3"]):
        result = prediction_id_assertions(SPLITS, {"f0": preds}, EVIDENCE)[AID]
        assert result.status is Status.FAIL, preds


def test_declared_fold_without_predictions_fails():
    result = prediction_id_assertions(SPLITS, {}, EVIDENCE)[AID]

    assert result.status is Status.FAIL
    assert result.observed["folds_without_predictions"] == ["f0"]


def test_invalid_evidence_is_error():
    result = prediction_id_assertions(
        SPLITS, {"f0": ["r2", "r3"]}, EVIDENCE, evidence_valid=False
    )[AID]

    assert result.status is Status.ERROR
    assert result.evidence_valid is False


def test_no_declared_folds_is_not_executed():
    result = prediction_id_assertions([], {}, EVIDENCE)[AID]

    assert result.status is Status.NOT_ASSESSED
    assert result.reason is Reason.NOT_EXECUTED
