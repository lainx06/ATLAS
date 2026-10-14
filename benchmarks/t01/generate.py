"""Generate the T-01 synthetic fixture tables and manifests (trusted, repo-authored).

Run: uv run --locked python benchmarks/t01/generate.py

Settings are fixed here and recorded in README.md. These are test fixtures for T-01, not a
benchmark measurement. The data is synthetic and does not represent any real person.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

HERE = Path(__file__).resolve().parent
SEED = 20261014
N_SUBJECTS = 8
SESSIONS_PER_SUBJECT = 2
WINDOWS_PER_SESSION = 10
FEATURES = [f"f{i}" for i in range(6)]
SIGNAL = np.array([0.8, 0.6, 0.4, 0.0, 0.0, 0.0])  # modest class signal on f0-f2
SUBJECT_SD = 1.0  # subject-specific offsets (confounding by subject)
SESSION_SD = 0.3
N_FOLDS = 4  # GroupKFold used by the grouped fixture scripts
N_PLANTED_PAIRS = 3

BASE_COLUMNS = {
    "row_id": "row_id",
    "target": "activity",
    "class_map": {"0": "rest", "1": "move"},
    "features": FEATURES,
    "group_id": "subject_id",
    "unit_id": "subject_id",
    "observation_id": "observation_id",
}
BASE_CLAIM = {
    "type": "unseen_group",
    "statement": "The activity classifier works on people absent from training.",
    "sampling_unit": "subject",
    "dependence": [
        {"kind": "repeated_measures", "column": "subject_id"},
        {"kind": "repeated_measures", "column": "session_id"},
    ],
}


def base_table() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    for s in range(N_SUBJECTS):
        subject_offset = rng.normal(0, SUBJECT_SD, size=len(FEATURES))
        for sess in range(SESSIONS_PER_SUBJECT):
            session_offset = rng.normal(0, SESSION_SD, size=len(FEATURES))
            for w in range(WINDOWS_PER_SESSION):
                label = w % 2
                x = (
                    label * SIGNAL
                    + subject_offset
                    + session_offset
                    + rng.normal(0, 1, size=len(FEATURES))
                )
                rows.append(
                    {
                        "subject_id": f"S{s + 1:02d}",
                        "session_id": f"S{s + 1:02d}-{sess + 1}",
                        "window_index": w,
                        **{
                            f: round(float(v), 6)
                            for f, v in zip(FEATURES, x, strict=True)
                        },
                        "activity": label,
                    }
                )
    t = pd.DataFrame(rows)
    t.insert(0, "row_id", [f"r{i:04d}" for i in range(len(t))])
    t.insert(3, "observation_id", [f"o{i:04d}" for i in range(len(t))])
    return t


def overlapping_window_table() -> pd.DataFrame:
    """Windows of length 10 with step 5 within each session stream: truthfully overlapping."""
    t = base_table()
    t["stream_id"] = t["session_id"]
    t["window_start"] = t["window_index"] * 5
    t["window_end"] = t["window_start"] + 10
    return t


def planted_pairs(t: pd.DataFrame) -> list[tuple[str, str]]:
    """Row pairs (src, dst) whose subjects fall in different GroupKFold folds of the fixture scripts."""
    fold_of = {}
    splitter = GroupKFold(n_splits=N_FOLDS)
    for k, (_, ev) in enumerate(
        splitter.split(t[FEATURES], t["activity"], t["subject_id"])
    ):
        for subject in t.iloc[ev]["subject_id"].unique():
            fold_of[subject] = k
    subjects = sorted(fold_of)
    pairs = []
    for src_subject in subjects:
        dst_subject = next(
            s
            for s in subjects
            if fold_of[s] != fold_of[src_subject] and s > src_subject
        )
        src = t[(t["subject_id"] == src_subject) & (t["window_index"] == 0)][
            "row_id"
        ].iloc[0]
        dst = t[(t["subject_id"] == dst_subject) & (t["window_index"] == 2)][
            "row_id"
        ].iloc[0]
        pairs.append((src, dst))
        if len(pairs) == N_PLANTED_PAIRS:
            return pairs
    raise RuntimeError("could not plant cross-fold pairs")


def identical_value_table() -> tuple[pd.DataFrame, list[tuple[str, str]]]:
    """Independently observed rows that happen to share feature and target values."""
    t = base_table()
    pairs = planted_pairs(t)
    idx = t.set_index("row_id")
    for src, dst in pairs:
        idx.loc[dst, [*FEATURES, "activity"]] = idx.loc[
            src, [*FEATURES, "activity"]
        ].to_numpy()
    out = idx.reset_index()
    out["activity"] = out["activity"].astype(int)
    return out, pairs


def manifest(columns=None, claim=None, **extra) -> dict:
    cols = {**BASE_COLUMNS, **(columns or {})}
    cols = {k: v for k, v in cols.items() if v is not None}
    return {
        "schema_version": "0.2",
        "table": {"path": "table.csv", "format": "csv"},
        "columns": cols,
        "claim": {**BASE_CLAIM, **(claim or {})},
        "primary_metric": "balanced_accuracy",
        "development_seeds": [0],
        "entry_point": "evaluate.py",
        **extra,
    }


def write(name: str, table: pd.DataFrame, man: dict) -> None:
    d = HERE / name
    d.mkdir(exist_ok=True)
    table.to_csv(d / "table.csv", index=False, lineterminator="\n", float_format="%.6f")
    (d / "atlas_manifest.json").write_text(
        json.dumps(man, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> None:
    base = base_table()
    for name in (
        "s01_faulty",
        "s02_clean",
        "s03a_rebuilt_frame",
        "s03b_inplace_mutation",
        "s04_zero_fit",
        "s05a_contaminated_reuse",
        "s05b_benign_reuse",
        "s08b_no_adapter",
    ):
        write(name, base, manifest())
    write(
        "s06_missing_metadata",
        base,
        manifest(columns={"group_id": None, "unit_id": None}),
    )
    write(
        "s07_unimplemented_window",
        overlapping_window_table(),
        manifest(
            columns={
                "stream_id": "stream_id",
                "window_start": "window_start",
                "window_end": "window_end",
            },
            claim={
                "dependence": [
                    *BASE_CLAIM["dependence"],
                    {"kind": "overlapping_windows"},
                ]
            },
            time_basis={
                "unit": "sample",
                "reference_time": "start of each session stream",
            },
        ),
    )
    write(
        "s08a_combined_claim",
        base,
        manifest(claim={"type": "unseen_group+future_time"}),
    )
    identical, pairs = identical_value_table()
    write("s10a_identical_values_with_ids", identical, manifest())
    no_ids = identical.drop(columns=["observation_id"])
    write(
        "s10b_identical_values_no_ids",
        no_ids,
        manifest(columns={"observation_id": None}),
    )
    write(
        "s10c_known_duplicate",
        no_ids,
        manifest(columns={"observation_id": None}, known_duplicates=[list(pairs[0])]),
    )
    print("planted identical-value pairs (src, dst):", pairs)


if __name__ == "__main__":
    main()
