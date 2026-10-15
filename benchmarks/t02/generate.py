"""Generate the T-02 synthetic fixture tables and manifests (trusted, repo-authored).

Run: uv run --locked python benchmarks/t02/generate.py

Settings are fixed here and recorded in README.md. These are test fixtures for T-02, not a
benchmark measurement. The data is synthetic.

The reported metrics in s11b/s11c are computed here with scikit-learn on a plain replication of
the fixture's protocol, read back from the written CSV. That is an independent cross-check of the
evaluator's own metric code, not a copy of it.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
SEED = 20261015
FEATURES = ["f0", "f1", "f2"]
SIGNAL = np.array([1.0, 0.7, 0.4])

# future_time (s11): one row per day
N_DAYS = 120
# A row's label is known 7 days after its prediction day.
HORIZON, REPORTING_DELAY = 5, 2
FIRST_CUTOFF, BLOCK, N_FOLDS = 60, 15, 4  # fold k evaluates days [60 + 15k, 75 + 15k)

# same_population windows (s12): 6 streams x 24 windows of length 10, step 5
STREAMS = ["A", "B", "C", "D", "E", "F"]
WINDOWS_PER_STREAM = 24
STEP, LENGTH = 5, 10
MIN_GAP = 5
EVAL_BLOCK = 6  # fold k evaluates windows [6k, 6k + 6) of every stream


def future_table() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    latent = rng.normal(size=N_DAYS)
    label = (latent > 0).astype(int)
    x = label[:, None] * SIGNAL + rng.normal(size=(N_DAYS, len(FEATURES)))
    t = pd.DataFrame({f: np.round(x[:, i], 6) for i, f in enumerate(FEATURES)})
    t.insert(0, "row_id", [f"r{i:04d}" for i in range(N_DAYS)])
    t.insert(1, "observation_id", [f"o{i:04d}" for i in range(N_DAYS)])
    t.insert(2, "pred_day", np.arange(N_DAYS))
    # f2 becomes known exactly at prediction time (the equality boundary).
    t.insert(3, "f2_known", np.arange(N_DAYS))
    t["outcome"] = label
    return t


def future_folds(day: pd.Series, clean: bool):
    """(cutoff, train mask, eval mask) per fold. Clean: a training row's label is known by the cutoff."""
    delay = HORIZON + REPORTING_DELAY
    for k in range(N_FOLDS):
        cutoff = FIRST_CUTOFF + BLOCK * k
        train = (day + delay <= cutoff) if clean else (day < cutoff)
        yield cutoff, train, (day >= cutoff) & (day < cutoff + BLOCK)


def future_reference(table_csv: Path) -> dict:
    """scikit-learn's own metrics for the clean protocol, on the table as written."""
    t = pd.read_csv(table_csv, dtype={"row_id": str})
    trues, preds, per_fold = [], [], []
    for _, train, ev in future_folds(t["pred_day"], clean=True):
        model = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression())])
        model.fit(t.loc[train, FEATURES], t.loc[train, "outcome"])
        p = model.predict(t.loc[ev, FEATURES])
        per_fold.append(balanced_accuracy_score(t.loc[ev, "outcome"], p))
        trues += list(t.loc[ev, "outcome"])
        preds += list(p)
    return {
        "balanced_accuracy_mean_over_folds": float(np.mean(per_fold)),
        "macro_f1_pooled": float(
            f1_score(trues, preds, average="macro", zero_division=0)
        ),
    }


def future_manifest(reported=None) -> dict:
    return {
        "schema_version": "0.3",
        "table": {"path": "table.csv", "format": "csv"},
        "columns": {
            "row_id": "row_id",
            "target": "outcome",
            "class_map": {"0": "no", "1": "yes"},
            "features": FEATURES,
            "observation_id": "observation_id",
            "prediction_time": "pred_day",
        },
        "claim": {
            "type": "future_time",
            "statement": "The classifier predicts each day's outcome for later days.",
            "sampling_unit": "row",
            "dependence": [{"kind": "temporal_order"}],
        },
        "time_basis": {
            "unit": "day",
            "reference_time": "day 0 = the first prediction day (synthetic)",
            "scope": "global",
        },
        "feature_availability": {
            "f0": {"offset": 0},
            "f1": {"offset": -1},
            "f2": {"column": "f2_known"},
        },
        "label_availability": {"horizon": HORIZON, "reporting_delay": REPORTING_DELAY},
        "temporal_gap": 0,
        "primary_metric": "balanced_accuracy",
        "development_seeds": [0],
        "entry_point": "evaluate.py",
        "reported_metrics": reported or [],
    }


def window_table() -> pd.DataFrame:
    rng = np.random.default_rng(SEED + 1)
    rows = []
    for stream in STREAMS:
        offset = rng.normal(0, 0.3, size=len(FEATURES))
        for j in range(WINDOWS_PER_STREAM):
            label = (j // 3) % 2
            x = label * SIGNAL + offset + rng.normal(size=len(FEATURES))
            rows.append(
                {
                    "stream_id": stream,
                    "window_index": j,
                    "window_start": STEP * j,
                    "window_end": STEP * j + LENGTH,
                    **{f: round(float(v), 6) for f, v in zip(FEATURES, x, strict=True)},
                    "state": label,
                }
            )
    t = pd.DataFrame(rows)
    t.insert(0, "row_id", [f"w{i:04d}" for i in range(len(t))])
    t.insert(1, "observation_id", [f"o{i:04d}" for i in range(len(t))])
    return t


def window_manifest() -> dict:
    return {
        "schema_version": "0.3",
        "table": {"path": "table.csv", "format": "csv"},
        "columns": {
            "row_id": "row_id",
            "target": "state",
            "class_map": {"0": "idle", "1": "active"},
            "features": FEATURES,
            "observation_id": "observation_id",
            "stream_id": "stream_id",
            "window_start": "window_start",
            "window_end": "window_end",
        },
        "claim": {
            "type": "same_population",
            "statement": "The classifier works on new windows from these same sensors.",
            "sampling_unit": "row",
            "dependence": [{"kind": "overlapping_windows"}, {"kind": "temporal_order"}],
        },
        "time_basis": {
            "unit": "sample",
            "reference_time": "start of each sensor stream (synthetic)",
            "scope": "per_stream",
        },
        "separation_rule": {
            "scope": "per_stream",
            "min_gap": MIN_GAP,
            "times": "window",
        },
        "primary_metric": "balanced_accuracy",
        "development_seeds": [0],
        "entry_point": "evaluate.py",
    }


def write(name: str, table: pd.DataFrame, man: dict | None = None) -> Path:
    d = HERE / name
    d.mkdir(exist_ok=True)
    table.to_csv(d / "table.csv", index=False, lineterminator="\n", float_format="%.6f")
    if man is not None:
        write_manifest(name, man)
    return d / "table.csv"


def write_manifest(name: str, man: dict) -> None:
    (HERE / name / "atlas_manifest.json").write_text(
        json.dumps(man, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def reported(ref: dict, shift: float = 0.0) -> list[dict]:
    return [
        {
            "metric_definition": "balanced_accuracy",
            "partition": "development_eval",
            "fold": "all",
            "aggregation": "mean_over_folds",
            "value": ref["balanced_accuracy_mean_over_folds"] + shift,
        },
        {
            "metric_definition": "macro_f1",
            "partition": "development_eval",
            "fold": "all",
            "aggregation": "pooled",
            "value": ref["macro_f1_pooled"],
        },
    ]


def main() -> None:
    future = future_table()
    write("s11a_future_time_label_leak", future, future_manifest())
    ref = future_reference(write("s11b_future_time_clean", future))
    write_manifest("s11b_future_time_clean", future_manifest(reported(ref)))
    # Misreported by 0.01 (far outside the 1e-6 tolerance); everything else as in s11b.
    shift = -0.01 if ref["balanced_accuracy_mean_over_folds"] > 0.5 else 0.01
    write(
        "s11c_reported_metric_mismatch", future, future_manifest(reported(ref, shift))
    )
    windows = window_table()
    write("s12a_same_population_random_windows", windows, window_manifest())
    write("s12b_same_population_blocked_windows", windows, window_manifest())
    print(json.dumps(ref, indent=2))


if __name__ == "__main__":
    main()
