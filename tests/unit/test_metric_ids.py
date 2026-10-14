"""metric.prediction_ids_match_eval_ids (SPEC §5; Codex review finding 6)."""

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
    },
    {
        "fold": "f1",
        "kind": "development_eval",
        "train_ids": ["r2", "r3"],
        "eval_ids": ["r0", "r1"],
    },
]
AID = "metric.prediction_ids_match_eval_ids"


def _check(artifacts, **kwargs):
    return prediction_id_assertions(SPLITS, artifacts, EVIDENCE, **kwargs)[AID]


def test_valid_artifacts_covering_exactly_the_eval_rows_pass():
    result = _check({"f0": ["r3", "r2"], "f1": ["r0", "r1"]})

    assert result.status is Status.PASS


def test_valid_artifact_with_missing_extra_or_duplicate_rows_fails():
    for preds in (["r2"], ["r2", "r3", "r1"], ["r2", "r2", "r3"]):
        result = _check({"f0": preds, "f1": ["r0", "r1"]})
        assert result.status is Status.FAIL, preds


def test_missing_prediction_artifact_for_a_declared_fold_is_error_not_fail():
    result = _check({"f0": ["r2", "r3"]})

    assert result.status is Status.ERROR
    assert result.evidence_valid is False
    assert result.observed["missing_or_invalid_artifacts"] == ["f1"]


def test_invalid_prediction_artifact_is_error():
    result = _check({"f0": ["r2", "r3"], "f1": None})

    assert result.status is Status.ERROR


def test_valid_wrong_ids_fail_survives_a_missing_artifact_elsewhere():
    result = _check({"f0": ["r2"]})

    assert result.status is Status.FAIL
    assert result.observed["missing_or_invalid_artifacts"] == ["f1"]


def test_artifact_for_an_undeclared_fold_is_error():
    result = _check({"f0": ["r2", "r3"], "f1": ["r0", "r1"], "f9": ["r0"]})

    assert result.status is Status.ERROR
    assert result.observed["artifacts_for_undeclared_folds"] == ["f9"]


def test_invalid_split_evidence_is_error():
    result = _check({"f0": ["r2", "r3"], "f1": ["r0", "r1"]}, evidence_valid=False)

    assert result.status is Status.ERROR
    assert result.evidence_valid is False


def test_no_declared_folds_is_not_executed():
    result = prediction_id_assertions([], {}, EVIDENCE)[AID]

    assert result.status is Status.NOT_ASSESSED
    assert result.reason is Reason.NOT_EXECUTED
