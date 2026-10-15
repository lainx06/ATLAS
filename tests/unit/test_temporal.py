"""Window, separation and time-availability assertions (SPEC §5, policy-v1.3; T-02 contract)."""

import math

import pandas as pd
import pytest

from atlas.checks.temporal import (
    FEATURES,
    LABELS,
    PRECEDES,
    SEPARATION,
    WINDOW,
    temporal_assertions,
)
from atlas.contracts import AssertionResult, EvidenceRef, Manifest, Reason, Status
from atlas.policy import derive_outcome

EVIDENCE = [EvidenceRef(artifact="splits.json", sha256="x")]
P, F, N, E = Status.PASS, Status.FAIL, Status.NOT_ASSESSED, Status.ERROR


def _manifest(version="0.3", columns=None, **fields):
    cols = {
        "row_id": "row_id",
        "target": "y",
        "class_map": {"0": "a", "1": "b"},
        "features": ["f0", "f1"],
        "group_id": "subject",
        "stream_id": "stream",
        "window_start": "ws",
        "window_end": "we",
        "prediction_time": "pt",
    }
    cols.update(columns or {})
    cols = {k: v for k, v in cols.items() if v is not None}
    claim = fields.pop(
        "claim",
        {
            "type": "same_population",
            "statement": "s",
            "sampling_unit": "row",
            "dependence": [{"kind": "overlapping_windows"}, {"kind": "temporal_order"}],
        },
    )
    if "time_basis" not in fields:
        fields["time_basis"] = {"unit": "s", "reference_time": "t0", "scope": "global"}
    fields = {k: v for k, v in fields.items() if v is not None}
    return Manifest.model_validate(
        {
            "schema_version": version,
            "table": {"path": "t.csv", "format": "csv"},
            "columns": cols,
            "claim": claim,
            "primary_metric": "balanced_accuracy",
            "development_seeds": [0],
            "entry_point": "evaluate.py",
            **fields,
        }
    )


def _table(rows):
    """rows: row_id -> dict of column values."""
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("row_id")


def _split(train, ev, fold="f0", cutoff=None):
    return {
        "fold": fold,
        "kind": "development_eval",
        "train_ids": list(train),
        "eval_ids": list(ev),
        "training_cutoff": cutoff,
    }


def _run(manifest, table, splits, group=None, valid=True):
    return temporal_assertions(
        manifest, table, splits, EVIDENCE, evidence_valid=valid, group_result=group
    )


def _group(status=P, valid=True):
    return AssertionResult(
        assertion_id="split.no_group_overlap", status=status, evidence_valid=valid
    )


def _w(stream, start, end, subject="A"):
    return {"stream": stream, "ws": start, "we": end, "subject": subject, "pt": 0}


# --- split.no_window_overlap: route D ---------------------------------------------------------


@pytest.mark.parametrize(
    ("train", "ev", "status", "basis"),
    [
        (
            _w("A", 0, 10),
            _w("A", 10, 20),
            P,
            "interval_comparison",
        ),  # half-open: touch only
        (_w("A", 0, 10), _w("A", 5, 15), F, None),  # shared span [5, 10)
        (_w("A", 0, 10), _w("B", 5, 15), P, "stream_membership_disjoint"),
    ],
)
def test_window_overlap_direct_route(train, ev, status, basis):
    result = _run(_manifest(), _table({"t": train, "e": ev}), [_split(["t"], ["e"])])[
        WINDOW
    ]

    assert result.status is status
    if basis:
        assert result.observed["established_by"] == {"f0": basis}
    else:
        assert result.observed["witnesses"][0]["eval_window"] == [5.0, 15.0]
    assert any("not proof of statistical independence" in x for x in result.limitations)


@pytest.mark.parametrize("bounds", [(5, 5), (6, 5)], ids=["zero_length", "reversed"])
def test_unusable_window_bounds_in_a_crossing_stream_are_not_assessed(bounds):
    """Lead policy (v1.3): needed bounds must satisfy start < end."""
    table = _table({"t": _w("A", 20, 30), "e": _w("A", *bounds)})

    result = _run(_manifest(), table, [_split(["t"], ["e"])])[WINDOW]

    assert (result.status, result.reason) == (N, Reason.MISSING_METADATA)
    assert result.observed["folds"][0]["rows_with_unusable_bounds"] == 1


def test_unusable_bounds_that_are_not_needed_do_not_block_pass():
    """No stream is in both partitions, so bounds are unused (route D, membership only)."""
    table = _table({"t": _w("A", 6, 5), "e": _w("B", 5, 5)})

    result = _run(_manifest(), table, [_split(["t"], ["e"])])[WINDOW]

    assert result.status is P
    assert result.observed["established_by"] == {"f0": "stream_membership_disjoint"}


def test_unknown_stream_without_witness_is_missing_metadata():
    table = _table({"t": _w("A", 0, 10), "e": _w(None, 50, 60)})

    result = _run(_manifest(), table, [_split(["t"], ["e"])])[WINDOW]

    assert (result.status, result.reason) == (N, Reason.MISSING_METADATA)


def test_valid_window_fail_survives_unknown_rows():
    table = _table({"t": _w("A", 0, 10), "e": _w("A", 5, 15), "u": _w(None, 50, 60)})

    result = _run(_manifest(), table, [_split(["t"], ["e", "u"])])[WINDOW]

    assert result.status is F
    assert result.observed["folds"][0]["rows_with_unknown_stream"] == 1


def test_bounds_are_compared_within_a_stream_even_with_an_unspecified_clock():
    """Legacy 0.2 without scope: within-stream comparisons stay assessable."""
    m = _manifest("0.2", time_basis={"unit": "s", "reference_time": "per stream"})
    assert m.time_basis.scope is None
    overlap = _table({"t": _w("A", 0, 10), "e": _w("A", 5, 15)})
    apart = _table({"t": _w("A", 0, 10), "e": _w("A", 10, 20)})

    assert _run(m, overlap, [_split(["t"], ["e"])])[WINDOW].status is F
    assert _run(m, apart, [_split(["t"], ["e"])])[WINDOW].status is P


def test_crossing_stream_without_time_basis_is_missing_metadata():
    m = _manifest(time_basis=None)
    table = _table({"t": _w("A", 0, 10), "e": _w("A", 10, 20)})

    result = _run(m, table, [_split(["t"], ["e"])])[WINDOW]

    assert (result.status, result.reason) == (N, Reason.MISSING_METADATA)


# --- split.no_window_overlap: route C and contradictions ----------------------------------------

CONTAINMENT = {
    "within": "group_id",
    "source": "https://example.org/dataset-description",
    "statement": "Each recording session belongs to exactly one subject.",
}


def _no_stream_table():
    return _table(
        {
            "t": {"subject": "A", "ws": 0, "we": 10, "pt": 0},
            "e": {"subject": "B", "ws": 0, "we": 10, "pt": 0},
        }
    )


def test_route_c_passes_only_with_declaration_and_valid_group_pass():
    m = _manifest(columns={"stream_id": None}, window_containment=CONTAINMENT)

    result = _run(m, _no_stream_table(), [_split(["t"], ["e"])], group=_group())[WINDOW]

    assert result.status is P
    assert result.depends_on == ["split.no_group_overlap"]
    assert result.observed["established_by"] == {"f0": "documented_containment"}
    note = result.limitations[0]
    assert CONTAINMENT["source"] in note and CONTAINMENT["statement"] in note
    assert "not independently verified" in note and "not fetched" in note


@pytest.mark.parametrize(
    ("group", "containment"),
    [
        (_group(P), None),  # no declaration
        (_group(F), CONTAINMENT),  # groups cross partitions
        (_group(P, valid=False), CONTAINMENT),  # PASS on invalid evidence
        (None, CONTAINMENT),  # no group result
    ],
    ids=["no_declaration", "group_fail", "group_pass_invalid", "no_group_result"],
)
def test_route_c_without_its_conditions_is_missing_metadata(group, containment):
    m = _manifest(columns={"stream_id": None}, window_containment=containment)

    result = _run(m, _no_stream_table(), [_split(["t"], ["e"])], group=group)[WINDOW]

    assert (result.status, result.reason) == (N, Reason.MISSING_METADATA)


def _contradicted(extra_eval):
    """Stream S is observed in subjects A and B; row 'n' has an unknown stream."""
    rows = {
        "t": _w("S", 0, 10, "A"),
        "t2": _w("S", 100, 110, "B"),
        "n": _w(None, 300, 310, "C"),
        **extra_eval,
    }
    return _table(rows)


def test_contradiction_disables_route_c():
    m = _manifest(window_containment=CONTAINMENT)
    table = _contradicted({"e": _w("T", 0, 10, "D")})

    result = _run(m, table, [_split(["t", "t2"], ["e", "n"])], group=_group())[WINDOW]

    assert (result.status, result.reason) == (N, Reason.NO_SUPPORTED_RULE)
    assert result.observed["route_c"]["stream_group_contradictions"] == [
        {"stream_id": "S", "group_ids": ["A", "B"]}
    ]


def test_contradiction_never_suppresses_a_direct_fail():
    m = _manifest(window_containment=CONTAINMENT)
    table = _contradicted({"e": _w("S", 5, 15, "A")})

    result = _run(m, table, [_split(["t", "t2"], ["e", "n"])], group=_group())[WINDOW]

    assert result.status is F


def test_contradiction_never_suppresses_a_complete_direct_assessment():
    m = _manifest(window_containment=CONTAINMENT)
    table = _table(
        {
            "t": _w("S", 0, 10, "A"),
            "t2": _w("S", 100, 110, "B"),
            "e": _w("S", 20, 30, "A"),
        }
    )

    result = _run(m, table, [_split(["t", "t2"], ["e"])], group=_group(F))[WINDOW]

    assert result.status is P
    assert result.observed["established_by"] == {"f0": "interval_comparison"}


# --- split.temporal_separation -----------------------------------------------------------------


def _points(train, ev):
    rows = {f"t{i}": {"pt": t, "stream": "A"} for i, t in enumerate(train)}
    rows |= {f"e{i}": {"pt": t, "stream": "A"} for i, t in enumerate(ev)}
    return _table(rows), [
        _split([r for r in rows if r[0] == "t"], [r for r in rows if r[0] == "e"])
    ]


def _rule(min_gap, times="prediction_time", scope="global"):
    return {"scope": scope, "min_gap": min_gap, "times": times}


@pytest.mark.parametrize(
    ("ev", "min_gap", "status"),
    [([35, 45], 15, P), ([35, 45], 16, F), ([-10], 15, F)],
    ids=["equality_passes", "one_short", "two_sided"],
)
def test_point_separation_is_two_sided_with_equality_passing(ev, min_gap, status):
    table, splits = _points([0, 10, 20], ev)

    result = _run(_manifest(separation_rule=_rule(min_gap)), table, splits)[SEPARATION]

    assert result.status is status
    assert any("not proof of statistical independence" in x for x in result.limitations)


@pytest.mark.parametrize(
    ("ev", "min_gap", "status"),
    [((10, 20), 0, P), ((5, 15), 0, F), ((10, 20), 1, F)],
    ids=["adjacent_gap_0", "overlap_negative_gap", "adjacent_needs_1"],
)
def test_window_separation_uses_the_signed_interval_gap(ev, min_gap, status):
    table = _table({"t": _w("A", 0, 10), "e": _w("A", *ev)})
    m = _manifest(separation_rule=_rule(min_gap, "window"))

    result = _run(m, table, [_split(["t"], ["e"])])[SEPARATION]

    assert result.status is status
    assert result.observed["folds"][0]["smallest_gap"] == ev[0] - 10


def test_no_separation_rule_is_no_declared_rule():
    table, splits = _points([0], [10])

    result = _run(_manifest(), table, splits)[SEPARATION]

    assert (result.status, result.reason) == (N, Reason.NO_DECLARED_RULE)


def test_separation_basis_is_never_guessed():
    """A legacy 0.2 rule without `times` is not assessable."""
    m = _manifest("0.2", separation_rule={"scope": "global", "min_gap": 1})
    table, splits = _points([0], [10])

    result = _run(m, table, splits)[SEPARATION]

    assert (result.status, result.reason) == (N, Reason.MISSING_METADATA)
    assert "never guessed" in result.observed["problem"]


@pytest.mark.parametrize(
    "time_basis",
    [
        {"unit": "s", "reference_time": "t0", "scope": "per_stream"},
        {
            "unit": "s",
            "reference_time": "t0 (global, says the prose)",
        },  # 0.2: unspecified
    ],
    ids=["per_stream_clock", "unspecified_clock"],
)
def test_global_separation_needs_a_declared_global_clock(time_basis):
    version = "0.3" if "scope" in time_basis else "0.2"
    m = _manifest(version, time_basis=time_basis, separation_rule=_rule(1))
    table, splits = _points([0], [10])

    result = _run(m, table, splits)[SEPARATION]

    assert (result.status, result.reason) == (N, Reason.MISSING_METADATA)


def test_per_stream_separation_is_assessable_without_a_global_clock():
    m = _manifest(
        "0.2",
        time_basis={"unit": "s", "reference_time": "per stream"},
        separation_rule=_rule(5, scope="per_stream"),
    )
    table, splits = _points([0], [10])

    assert _run(m, table, splits)[SEPARATION].status is P


def test_separation_fail_survives_unknown_times():
    table, splits = _points([0, None], [3])

    result = _run(_manifest(separation_rule=_rule(5)), table, splits)[SEPARATION]

    assert result.status is F
    assert result.observed["folds"][0]["rows_with_unknown_time"] == 1


def test_separation_unknown_time_without_witness_is_missing_metadata():
    table, splits = _points([0, None], [30])

    result = _run(_manifest(separation_rule=_rule(5)), table, splits)[SEPARATION]

    assert (result.status, result.reason) == (N, Reason.MISSING_METADATA)


# --- future_time: the 100/150/120 counterexample and its corrections ----------------------------

FUTURE_CLAIM = {
    "type": "future_time",
    "statement": "s",
    "sampling_unit": "row",
    "dependence": [],
}
OFFSETS = {"f0": {"offset": 0}, "f1": {"offset": 0}}


def _future(scope="global", label=None, gap=0, version="0.3", **extra):
    basis = {"unit": "day", "reference_time": "day 0"}
    if scope is not None:
        basis["scope"] = scope
    return _manifest(
        version,
        claim=FUTURE_CLAIM,
        time_basis=basis,
        label_availability=label or {"horizon": 30, "reporting_delay": 20},
        temporal_gap=gap,
        feature_availability=extra.pop("features", OFFSETS),
        **extra,
    )


def _counterexample(cutoff):
    table = _table(
        {"r1": {"pt": 100, "label_day": 150}, "r2": {"pt": 120, "label_day": None}}
    )
    return table, [_split(["r1"], ["r2"], cutoff=cutoff)]


@pytest.mark.parametrize(
    ("cutoff", "labels", "precedes"),
    [
        (120, F, P),
        (150, P, F),
        (130, F, F),
        (None, (N, Reason.MISSING_METADATA), (N, Reason.MISSING_METADATA)),
    ],
)
def test_future_time_counterexample_never_passes(cutoff, labels, precedes):
    table, splits = _counterexample(cutoff)

    results = _run(_future(), table, splits)

    for aid, expected in ((LABELS, labels), (PRECEDES, precedes)):
        status, reason = expected if isinstance(expected, tuple) else (expected, None)
        assert (results[aid].status, results[aid].reason) == (status, reason), aid
    outcome = derive_outcome([results[LABELS], results[PRECEDES], results[FEATURES]])
    assert outcome.value != "NO_VIOLATION_FOUND"


def test_label_availability_column_gives_the_same_counterexample():
    table, splits = _counterexample(120)

    results = _run(_future(label={"column": "label_day"}), table, splits)

    assert results[LABELS].status is F


def test_gap_moves_the_precedence_boundary():
    table, splits = _counterexample(110)

    results = _run(_future(gap=10), table, splits)

    assert results[PRECEDES].status is P  # 110 + 10 <= 120 (equality)
    assert results[LABELS].status is F  # label at 150 > 110


def test_negative_declared_gap_fails():
    table, splits = _counterexample(100)

    assert _run(_future(gap=-1), table, splits)[PRECEDES].status is F


@pytest.mark.parametrize(
    ("scope", "version"),
    [("per_stream", "0.3"), (None, "0.2")],
    ids=["per_stream", "unspecified"],
)
def test_single_cutoff_checks_need_a_global_clock_but_features_do_not(scope, version):
    table, splits = _counterexample(150)

    results = _run(_future(scope=scope, version=version), table, splits)

    assert (results[LABELS].status, results[LABELS].reason) == (
        N,
        Reason.MISSING_METADATA,
    )
    assert (results[PRECEDES].status, results[PRECEDES].reason) == (
        N,
        Reason.MISSING_METADATA,
    )
    assert results[FEATURES].status is P  # same-row comparison on the row's local clock
    assert results[FEATURES].observed["clock_scope"] == (scope or "unspecified")


@pytest.mark.parametrize(
    "cutoff", ["120", True, math.inf], ids=["string", "boolean", "infinite"]
)
def test_invalid_cutoff_is_an_evidence_error(cutoff):
    table, splits = _counterexample(cutoff)

    result = _run(_future(), table, splits)[LABELS]

    assert (result.status, result.reason) == (E, Reason.EVIDENCE_INVALID)
    assert result.evidence_valid is False


def test_valid_fail_in_one_fold_survives_an_invalid_cutoff_in_another():
    table = _table(
        {"r1": {"pt": 100}, "r2": {"pt": 120}, "r3": {"pt": 200}, "r4": {"pt": 260}}
    )
    splits = [
        _split(["r1"], ["r2"], fold="a", cutoff=120),  # label at 150 > 120
        _split(["r3"], ["r4"], fold="b", cutoff="bad"),
    ]

    result = _run(_future(), table, splits)[LABELS]

    assert result.status is F and result.evidence_valid
    assert result.observed["invalid_cutoff_folds"] == ["b"]


# --- temporal.features_available_when_used ------------------------------------------------------


@pytest.mark.parametrize(
    ("known", "status"), [(121, F), (120, P)], ids=["late", "equality"]
)
def test_feature_availability_column(known, status):
    table = _table(
        {"r1": {"pt": 100, "f1_known": 90}, "r2": {"pt": 120, "f1_known": known}}
    )
    m = _future(features={"f0": {"offset": 0}, "f1": {"column": "f1_known"}})

    result = _run(m, table, [_split(["r1"], ["r2"], cutoff=150)])[FEATURES]

    assert result.status is status


def test_positive_offset_fails_every_row():
    table, splits = _counterexample(150)
    m = _future(features={"f0": {"offset": 1}, "f1": {"offset": 0}})

    result = _run(m, table, splits)[FEATURES]

    assert result.status is F
    assert result.observed["features"]["f0"]["late_rows"] == 2


def test_feature_without_availability_is_missing_unless_another_fails():
    table, splits = _counterexample(150)
    missing = _future(features={"f0": {"offset": 0}})
    failing = _future(features={"f0": {"offset": 1}})

    assert _run(missing, table, splits)[FEATURES].reason is Reason.MISSING_METADATA
    assert _run(failing, table, splits)[FEATURES].status is F


def test_boolean_or_null_times_make_rows_unknown():
    table = _table({"r1": {"pt": True}, "r2": {"pt": 120}})

    results = _run(_future(), table, [_split(["r1"], ["r2"], cutoff=150)])

    assert (results[FEATURES].status, results[FEATURES].reason) == (
        N,
        Reason.MISSING_METADATA,
    )
    assert results[LABELS].reason is Reason.MISSING_METADATA


# --- evidence ---------------------------------------------------------------------------------


def test_invalid_split_or_table_evidence_is_an_error_for_every_assertion():
    table, splits = _counterexample(150)

    results = _run(_future(), table, splits, valid=False)

    assert {r.status for r in results.values()} == {E}


def test_no_participating_rows_is_not_executed():
    results = _run(_future(), _table({"r1": {"pt": 1}}), [_split([], [])])

    assert {(r.status, r.reason) for r in results.values()} == {
        (N, Reason.NOT_EXECUTED)
    }


# --- Codex review of 487664e: regressions ------------------------------------------------------
# Finding 1: a missing value must not suppress a violation shown by the row's other known value.


def _partial(pt, label, label_source="label_day"):
    table = _table(
        {"r1": {"pt": pt, "label_day": label}, "r2": {"pt": 150, "label_day": 150}}
    )
    m = _future(label={"column": label_source})
    return _run(m, table, [_split(["r1"], ["r2"], cutoff=120)])[LABELS]


@pytest.mark.parametrize(
    ("pt", "label", "late"),
    [(130, None, ["prediction_time"]), (None, 130, ["label_available"])],
    ids=["known_prediction_late_label_missing", "known_label_late_prediction_missing"],
)
def test_known_late_value_fails_despite_the_other_value_missing(pt, label, late):
    result = _partial(pt, label)

    assert result.status is F and result.evidence_valid
    witness = result.observed["witnesses"][0]
    assert witness["after_cutoff"] == late
    fold = result.observed["folds"][0]
    assert fold["training_rows_missing_prediction_time"] == (pt is None)
    assert fold["training_rows_missing_label_availability"] == (label is None)


def test_absent_label_source_still_preserves_a_late_prediction():
    result = _partial(130, 100, label_source="not_a_column")

    assert result.status is F
    assert "label_availability" in result.observed["absent_sources"]


@pytest.mark.parametrize(("pt", "label"), [(100, None), (None, 100)])
def test_missing_value_without_a_known_late_value_is_missing_metadata(pt, label):
    result = _partial(pt, label)

    assert (result.status, result.reason) == (N, Reason.MISSING_METADATA)
    assert result.observed["folds"][0]["training_rows_undecided"] == 1


# Finding 2: stream_id and group_id may name the same physical column.


def _aliased(rows, containment=None):
    extra = {"window_containment": containment} if containment else {}
    return _manifest(columns={"group_id": "stream"}, **extra), _table(rows)


def test_shared_stream_group_column_complete_direct_routes():
    disjoint = {"t": _w("A", 0, 10), "e": _w("B", 5, 15)}
    crossing = {"t": _w("A", 0, 10), "e": _w("A", 5, 15)}

    m, table = _aliased(disjoint)
    assert _run(m, table, [_split(["t"], ["e"])])[WINDOW].status is P
    m, table = _aliased(crossing)
    assert _run(m, table, [_split(["t"], ["e"])])[WINDOW].status is F


@pytest.mark.parametrize(
    "containment", [None, CONTAINMENT], ids=["undeclared", "declared"]
)
def test_shared_stream_group_column_incomplete_direct_route_does_not_raise(
    containment,
):
    """Unknown bounds in a crossing stream: route D is incomplete; route C is considered."""
    from atlas.checks.split_integrity import split_assertions

    values = {
        "f0": 0.0,
        "f1": 0.0,
        "y": 0,
    }  # split_assertions reads features and target
    rows = {"t": _w("S", None, 10) | values, "e": _w("S", 5, 15) | values}
    m, table = _aliased(rows, containment)
    splits = [_split(["t"], ["e"])]
    group = split_assertions(m, table, splits, EVIDENCE)["split.no_group_overlap"]

    result = _run(m, table, splits, group=group)[WINDOW]

    assert (result.status, result.reason) == (N, Reason.MISSING_METADATA)
    assert result.observed["route_c"]["stream_group_contradictions"] == []


def test_shared_stream_group_column_with_unknown_stream_does_not_raise():
    m, table = _aliased({"t": _w("A", 0, 10), "e": _w(None, 5, 15)}, CONTAINMENT)

    result = _run(m, table, [_split(["t"], ["e"])], group=_group(N))[WINDOW]

    assert (result.status, result.reason) == (N, Reason.MISSING_METADATA)


# Finding 3: an integer beyond the float64 range is unusable, not an exception.


def test_integer_beyond_float64_is_not_a_time():
    from atlas.checks.temporal import time_value

    assert math.isnan(time_value(10**400))
    assert time_value(10**300) == 1e300  # large but finite: still a valid time


def test_oversized_cutoff_is_an_evidence_error():
    table, splits = _counterexample(10**400)

    results = _run(_future(), table, splits)

    for aid in (LABELS, PRECEDES):
        assert (results[aid].status, results[aid].reason) == (
            E,
            Reason.EVIDENCE_INVALID,
        )


def test_oversized_cutoff_does_not_hide_a_fail_in_another_fold():
    table = _table(
        {"r1": {"pt": 100}, "r2": {"pt": 120}, "r3": {"pt": 200}, "r4": {"pt": 260}}
    )
    splits = [
        _split(["r1"], ["r2"], fold="a", cutoff=120),  # label at 150 > 120
        _split(["r3"], ["r4"], fold="b", cutoff=10**400),
    ]

    result = _run(_future(), table, splits)[LABELS]

    assert result.status is F
    assert result.observed["invalid_cutoff_folds"] == ["b"]
