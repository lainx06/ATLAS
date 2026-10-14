"""Bounded fit provenance: recorder events (candidate side) judged by trusted checks (SPEC §4.3, §5, F1)."""

import numpy as np
import pandas as pd
import pytest
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from atlas import adapter
from atlas.checks.fit_provenance import fit_assertions
from atlas.contracts import EvidenceRef, Reason, Status

EVIDENCE = [EvidenceRef(artifact="provenance.jsonl", sha256="x")]
FEATURES = ["f0", "f1", "f2", "f3"]


def _table():
    rng = np.random.default_rng(7)
    n = 24
    subjects = [f"S{i // 6}" for i in range(n)]  # 4 subjects x 6 rows
    y = np.array([0, 1] * (n // 2))
    X = rng.normal(size=(n, 4)) + y[:, None] * 0.8
    t = pd.DataFrame(X, columns=FEATURES)
    t["subject_id"] = subjects
    t["label"] = y
    t.index = pd.Index([f"r{i:02d}" for i in range(n)], name="row_id")
    return t


MANIFEST = {"columns": {"features": FEATURES, "target": "label"}}


def _folds(table):
    """Two grouped folds: eval subjects S0,S1 then S2,S3."""
    folds = []
    for k, ev_subjects in enumerate([("S0", "S1"), ("S2", "S3")]):
        ev = list(table.index[table["subject_id"].isin(ev_subjects)])
        tr = [r for r in table.index if r not in ev]
        folds.append((f"fold{k}", tr, ev))
    return folds


def _judge(session):
    results = fit_assertions(session.events, session.splits, EVIDENCE)
    return results["fit.state_dependencies_within_fold_train"], results[
        "fit.coverage_complete"
    ]


def _pipeline():
    return Pipeline(
        [
            ("scale", StandardScaler()),
            ("select", SelectKBest(f_classif, k=2)),
            ("clf", LogisticRegression()),
        ]
    )


def test_fold_local_pipeline_passes_dependencies_and_coverage(tmp_path):
    table = _table()
    with adapter.session(MANIFEST, table, tmp_path) as s:
        X, y = adapter.load_table()
        for fold, tr, ev in _folds(table):
            adapter.declare_split(fold, tr, ev)
            model = _pipeline().fit(adapter.take(X, tr), adapter.take(y, tr))
            adapter.write_predictions(fold, ev, model.predict(adapter.take(X, ev)))

    sd, cc = _judge(s)

    assert sd.status is Status.PASS
    assert cc.status is Status.PASS


def test_global_supervised_selection_fails_where_its_state_is_used(tmp_path):
    table = _table()
    with adapter.session(MANIFEST, table, tmp_path) as s:
        X, y = adapter.load_table()
        Xs = SelectKBest(f_classif, k=2).fit_transform(
            X, y
        )  # fit on every row, labels used
        for fold, tr, ev in _folds(table):
            adapter.declare_split(fold, tr, ev)
            clf = LogisticRegression().fit(adapter.take(Xs, tr), adapter.take(y, tr))
            adapter.write_predictions(fold, ev, clf.predict(adapter.take(Xs, ev)))

    sd, cc = _judge(s)

    assert sd.status is Status.FAIL
    assert set(sd.observed["violating_folds"]) == {"fold0", "fold1"}
    fits = [e for e in s.events if e["type"] == "fit" and e["class"] == "SelectKBest"]
    assert fits[0]["labels_used"] is True
    assert cc.status is Status.PASS


def test_rebuilt_frame_with_valid_index_is_not_ancestry(tmp_path):
    table = _table()
    with adapter.session(MANIFEST, table, tmp_path) as s:
        X, y = adapter.load_table()
        for fold, tr, ev in _folds(table):
            adapter.declare_split(fold, tr, ev)
            Xtr = adapter.take(X, tr)
            rebuilt = pd.DataFrame(Xtr.to_numpy(), index=Xtr.index, columns=Xtr.columns)
            model = _pipeline().fit(rebuilt, adapter.take(y, tr))
            adapter.write_predictions(fold, ev, model.predict(adapter.take(X, ev)))

    sd, cc = _judge(s)

    assert sd.status is Status.NOT_ASSESSED
    assert sd.reason is Reason.UNKNOWN_ANCESTRY
    assert cc.status is Status.NOT_ASSESSED
    assert cc.reason is Reason.COVERAGE_GAP


def test_in_place_mutation_is_an_unexplained_change(tmp_path):
    table = _table()
    with adapter.session(MANIFEST, table, tmp_path) as s:
        X, y = adapter.load_table()
        for fold, tr, ev in _folds(table):
            adapter.declare_split(fold, tr, ev)
            Xtr = adapter.take(X, tr)
            Xtr.iloc[:, 0] = Xtr.iloc[:, 0] * 1.5
            model = _pipeline().fit(Xtr, adapter.take(y, tr))
            adapter.write_predictions(fold, ev, model.predict(adapter.take(X, ev)))

    sd, cc = _judge(s)

    assert any(
        e["type"] == "gap" and e["reason"] == "unexplained_mutation" for e in s.events
    )
    assert sd.status is Status.NOT_ASSESSED
    assert sd.reason is Reason.UNKNOWN_ANCESTRY
    assert cc.reason is Reason.COVERAGE_GAP


def test_predictions_without_any_classifier_fit_are_zero_fit(tmp_path):
    table = _table()
    with adapter.session(MANIFEST, table, tmp_path) as s:
        _, y = adapter.load_table()
        for fold, tr, ev in _folds(table):
            adapter.declare_split(fold, tr, ev)
            majority = adapter.take(y, tr).mode().iloc[0]
            adapter.write_predictions(fold, ev, np.full(len(ev), majority))

    sd, cc = _judge(s)

    assert sd.status is Status.NOT_ASSESSED and sd.reason is Reason.ZERO_FIT
    assert cc.status is Status.NOT_ASSESSED and cc.reason is Reason.ZERO_FIT


def test_classifier_fit_with_untraced_predictions_is_a_coverage_gap_not_zero_fit(
    tmp_path,
):
    table = _table()
    with adapter.session(MANIFEST, table, tmp_path) as s:
        X, y = adapter.load_table()
        for fold, tr, ev in _folds(table):
            adapter.declare_split(fold, tr, ev)
            model = _pipeline().fit(adapter.take(X, tr), adapter.take(y, tr))
            preds = model.predict(adapter.take(X, ev)).copy()  # a new, untracked array
            adapter.write_predictions(fold, ev, preds)

    _, cc = _judge(s)

    assert cc.status is Status.NOT_ASSESSED
    assert cc.reason is Reason.COVERAGE_GAP


def test_reusing_state_learned_from_another_folds_eval_rows_fails(tmp_path):
    table = _table()
    with adapter.session(MANIFEST, table, tmp_path) as s:
        X, y = adapter.load_table()
        selector = None
        for fold, tr, ev in _folds(table):
            adapter.declare_split(fold, tr, ev)
            Xtr, ytr, Xev = (
                adapter.take(X, tr),
                adapter.take(y, tr),
                adapter.take(X, ev),
            )
            if selector is None:
                selector = SelectKBest(f_classif, k=2).fit(
                    Xtr, ytr
                )  # learned from fold0 training rows
            clf = LogisticRegression().fit(selector.transform(Xtr), ytr)
            adapter.write_predictions(fold, ev, clf.predict(selector.transform(Xev)))

    sd, _ = _judge(s)

    assert sd.status is Status.FAIL
    assert sd.observed["violating_folds"] == ["fold1"]


def test_whole_model_fitted_in_one_fold_and_reused_to_predict_another_fails(tmp_path):
    """Only the use-fold rule catches this: no state is refit in the fold where it is used."""
    table = _table()
    with adapter.session(MANIFEST, table, tmp_path) as s:
        X, y = adapter.load_table()
        model = None
        for fold, tr, ev in _folds(table):
            adapter.declare_split(fold, tr, ev)
            if model is None:
                model = _pipeline().fit(
                    adapter.take(X, tr), adapter.take(y, tr)
                )  # fit once, in fold0
            adapter.write_predictions(fold, ev, model.predict(adapter.take(X, ev)))

    sd, cc = _judge(s)

    assert sd.status is Status.FAIL
    assert sd.observed["violating_folds"] == ["fold1"]
    assert cc.status is Status.PASS


def test_reusing_state_learned_only_from_always_training_rows_passes(tmp_path):
    table = _table()
    always_train = list(table.index[table["subject_id"] == "S3"])
    with adapter.session(MANIFEST, table, tmp_path) as s:
        X, y = adapter.load_table()
        selector = SelectKBest(f_classif, k=2).fit(
            adapter.take(X, always_train), adapter.take(y, always_train)
        )
        for k, ev_subject in enumerate(["S0", "S1", "S2"]):
            ev = list(table.index[table["subject_id"] == ev_subject])
            tr = [r for r in table.index if r not in ev]
            adapter.declare_split(f"fold{k}", tr, ev)
            Xtr, ytr = adapter.take(X, tr), adapter.take(y, tr)
            clf = LogisticRegression().fit(selector.transform(Xtr), ytr)
            adapter.write_predictions(
                f"fold{k}", ev, clf.predict(selector.transform(adapter.take(X, ev)))
            )

    sd, cc = _judge(s)

    assert sd.status is Status.PASS
    assert cc.status is Status.PASS


def test_labels_supplied_to_an_unsupervised_scaler_are_not_labels_used(tmp_path):
    table = _table()
    with adapter.session(MANIFEST, table, tmp_path) as s:
        X, y = adapter.load_table()
        StandardScaler().fit(X, y)

    fit = next(
        e for e in s.events if e["type"] == "fit" and e["class"] == "StandardScaler"
    )
    assert fit["labels_supplied"] is True
    assert fit["labels_used"] is False


def test_session_exit_restores_scikit_learn_methods(tmp_path):
    original = StandardScaler.fit
    with adapter.session(MANIFEST, _table(), tmp_path):
        assert StandardScaler.fit is not original

    assert StandardScaler.fit is original


def test_invalid_provenance_evidence_is_error():
    results = fit_assertions(
        [],
        [{"fold": "f", "kind": "development_eval", "train_ids": [], "eval_ids": []}],
        EVIDENCE,
        evidence_valid=False,
    )

    for result in results.values():
        assert result.status is Status.ERROR
        assert result.evidence_valid is False


@pytest.mark.parametrize("bad_ids", [["r00", "r00"], ["missing"]])
def test_take_rejects_duplicate_or_unknown_rows(tmp_path, bad_ids):
    with adapter.session(MANIFEST, _table(), tmp_path):
        X, _ = adapter.load_table()
        with pytest.raises(ValueError):
            adapter.take(X, bad_ids)
