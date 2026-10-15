"""Manifest schema 0.3 and legacy 0.2 validation, and intake's NOT_SUPPORTED explanation (SPEC §3)."""

import copy
import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from atlas.contracts import Manifest
from atlas.intake import load_project

T01 = Path(__file__).resolve().parents[2] / "benchmarks" / "t01"
T02 = Path(__file__).resolve().parents[2] / "benchmarks" / "t02"

BASE = {
    "schema_version": "0.3",
    "table": {"path": "table.csv", "format": "csv"},
    "columns": {
        "row_id": "row_id",
        "target": "y",
        "class_map": {"0": "a", "1": "b"},
        "features": ["f0", "f1"],
        "prediction_time": "pt",
    },
    "claim": {
        "type": "future_time",
        "statement": "s",
        "sampling_unit": "row",
        "dependence": [],
    },
    "primary_metric": "balanced_accuracy",
    "development_seeds": [0],
    "entry_point": "evaluate.py",
    "time_basis": {"unit": "day", "reference_time": "day 0", "scope": "global"},
    "feature_availability": {"f0": {"offset": 0}, "f1": {"column": "f1_known"}},
    "label_availability": {"horizon": 5, "reporting_delay": 2},
    "temporal_gap": 0,
    "separation_rule": {"scope": "global", "min_gap": 1, "times": "prediction_time"},
    "window_containment": {"within": "group_id", "source": "doc", "statement": "x"},
    "reported_metrics": [
        {
            "metric_definition": "balanced_accuracy",
            "partition": "development_eval",
            "fold": "all",
            "aggregation": "mean_over_folds",
            "value": 0.7,
        }
    ],
}


def _with(path: str, value):
    """BASE with the dotted `path` set to `value` (or removed for the sentinel `...`)."""
    data = copy.deepcopy(BASE)
    *parents, last = path.split(".")
    node = data
    for key in parents:
        node = node[int(key)] if key.isdigit() else node[key]
    if value is ...:
        del node[last]
    elif last.isdigit():
        node[int(last)] = value
    else:
        node[last] = value
    return data


def test_complete_schema_0_3_manifest_validates():
    m = Manifest.model_validate(BASE)

    assert m.time_basis.scope == "global"
    assert m.reported_metrics[0].value == 0.7


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("schema_version", "0.4"),
        ("schema_version", "1"),
        ("primary_metric", "accuracy"),
        ("time_basis.scope", ...),  # required in 0.3
        ("time_basis.scope", "local"),
        ("time_basis.unit", " "),
        ("separation_rule.times", ...),  # required in 0.3
        ("separation_rule.times", "auto"),
        ("separation_rule.min_gap", -1),
        ("feature_availability.f0", {"offset": 0, "column": "c"}),
        ("feature_availability.f0", {}),
        ("feature_availability.f9", {"offset": 0}),  # undeclared feature
        ("label_availability", {"horizon": 5}),
        ("label_availability", {"column": "c", "horizon": 1, "reporting_delay": 1}),
        ("label_availability.horizon", -1),
        ("window_containment.within", "unit_id"),
        ("window_containment.source", ""),
        ("window_containment.statement", "   "),
        ("reported_metrics.0.fold", "fold0"),  # named fold with mean_over_folds
        ("reported_metrics.0.aggregation", "single_fold"),  # 'all' with single_fold
        ("reported_metrics.0.metric_definition", "accuracy"),
    ],
)
def test_malformed_fields_are_rejected(path, value):
    with pytest.raises(ValidationError):
        Manifest.model_validate(_with(path, value))


@pytest.mark.parametrize(
    "path",
    [
        "reported_metrics.0.value",
        "temporal_gap",
        "separation_rule.min_gap",
        "label_availability.horizon",
        "feature_availability.f0.offset",
    ],
)
@pytest.mark.parametrize(
    "value",
    [True, False, math.nan, math.inf, -math.inf, "0.5"],
    ids=["true", "false", "nan", "inf", "-inf", "string"],
)
def test_booleans_nonfinite_and_strings_are_rejected(path, value):
    with pytest.raises(ValidationError):
        Manifest.model_validate(_with(path, value))


@pytest.mark.parametrize("value", [-0.01, 1.2])
def test_out_of_range_reported_values_are_rejected(value):
    with pytest.raises(ValidationError):
        Manifest.model_validate(_with("reported_metrics.0.value", value))


@pytest.mark.parametrize("value", [0, 1, 0.0, 1.0])
def test_reported_value_bounds_are_inclusive(value):
    assert Manifest.model_validate(_with("reported_metrics.0.value", value))


def test_legacy_0_2_scope_is_unspecified_not_per_stream():
    data = _with("schema_version", "0.2")
    del data["time_basis"]["scope"]
    del data["separation_rule"]["times"]

    m = Manifest.model_validate(data)

    assert m.time_basis.scope is None  # unspecified
    assert m.separation_rule.times is None  # not assessable later; never guessed


def test_every_committed_fixture_manifest_still_validates():
    names = sorted(p.parent.name for p in T01.glob("*/atlas_manifest.json"))
    names += sorted(p.parent.name for p in T02.glob("*/atlas_manifest.json"))
    for root in (T01, T02):
        for path in root.glob("*/atlas_manifest.json"):
            Manifest.model_validate_json(path.read_text(encoding="utf-8"))
    assert len(names) == 19
    s07 = Manifest.model_validate_json(
        (T01 / "s07_unimplemented_window" / "atlas_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert s07.schema_version == "0.2" and s07.time_basis.scope is None


@pytest.mark.parametrize(
    ("raw_value", "field"),
    [
        ("NaN", "reported_metrics.0.value"),
        ("true", "reported_metrics.0.value"),
        ("1.5", "reported_metrics.0.value"),
    ],
)
def test_intake_rejects_invalid_values_as_not_supported_with_a_specific_reason(
    tmp_path, raw_value, field
):
    text = json.dumps(BASE).replace('"value": 0.7', f'"value": {raw_value}')
    (tmp_path / "atlas_manifest.json").write_text(text, encoding="utf-8")

    intake = load_project(tmp_path)

    assert not intake.supported
    assert intake.reason.startswith("manifest unparseable: 1 validation error(s): ")
    assert field in intake.reason


def test_intake_names_an_unsupported_schema_version(tmp_path):
    (tmp_path / "atlas_manifest.json").write_text(
        json.dumps(_with("schema_version", "9.9")), encoding="utf-8"
    )

    intake = load_project(tmp_path)

    assert not intake.supported and "schema_version" in intake.reason


# --- Codex review of 487664e: an integer beyond the float64 range is a validation error ---


@pytest.mark.parametrize(
    "path",
    [
        "reported_metrics.0.value",
        "temporal_gap",
        "separation_rule.min_gap",
        "label_availability.horizon",
        "feature_availability.f0.offset",
    ],
)
def test_integer_beyond_float64_is_rejected(path):
    with pytest.raises(ValidationError, match="float64"):
        Manifest.model_validate(_with(path, 10**400))


def test_large_but_finite_values_stay_valid():
    m = Manifest.model_validate(_with("temporal_gap", 10**300))

    assert m.temporal_gap == 1e300


@pytest.mark.parametrize("digits", [401, 5000])
def test_intake_names_an_oversized_reported_value(tmp_path, digits):
    big = str(10 ** (digits - 1)) if digits < 4000 else "1" + "0" * (digits - 1)
    text = json.dumps(BASE).replace('"value": 0.7', f'"value": {big}')
    (tmp_path / "atlas_manifest.json").write_text(text, encoding="utf-8")

    intake = load_project(tmp_path)

    assert not intake.supported
    if digits == 401:  # parsed as an integer, then refused by field validation
        assert "reported_metrics.0.value" in intake.reason
    else:  # refused earlier by the JSON parser, which reports a position, not a field
        assert "number out of range" in intake.reason
