"""Candidate-side adapter (SPEC §4.1). Imported by a project's evaluate.py.

The adapter loads data as tracked objects, provides supported row selection (`take`), records
declared splits and writes predictions. Scoring happens later in the trusted evaluator.
"""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

from atlas.recorder import Recorder

ADAPTER_VERSION = "0.1"
_SESSION: "Session | None" = None


class Session:
    def __init__(self, manifest: dict, table: pd.DataFrame, out_dir: Path):
        self.manifest = manifest
        self.table = table
        self.out_dir = Path(out_dir)
        self.recorder = Recorder(table.index)
        self.events = self.recorder.events
        self.splits: list[dict] = []

    def write_evidence(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        with open(
            self.out_dir / "provenance.jsonl", "w", encoding="utf-8", newline="\n"
        ) as f:
            f.writelines(
                json.dumps(event, sort_keys=True) + "\n" for event in self.events
            )
        (self.out_dir / "splits.json").write_text(
            json.dumps(self.splits, indent=1), encoding="utf-8", newline="\n"
        )


@contextmanager
def session(manifest: dict, table: pd.DataFrame, out_dir) -> Iterator[Session]:
    """Install the recorder for one evaluation; always uninstall and write evidence."""
    global _SESSION
    if _SESSION is not None:
        raise RuntimeError("an adapter session is already active")
    s = Session(manifest, table, Path(out_dir))
    _SESSION = s
    s.recorder.install()
    try:
        with sklearn.config_context(transform_output="pandas"):
            yield s
    finally:
        s.recorder.uninstall()
        _SESSION = None
        s.write_evidence()


def _require() -> Session:
    if _SESSION is None:
        raise RuntimeError("no ATLAS adapter session is active")
    return _SESSION


def load_table() -> tuple[pd.DataFrame, pd.Series]:
    """Development rows as tracked (X, y), indexed by row_id."""
    s = _require()
    cols = s.manifest["columns"]
    X = s.table[cols["features"]].copy()
    y = s.table[cols["target"]].copy()
    rows = tuple(map(str, s.table.index))
    for obj, kind in ((X, "features"), (y, "labels")):
        token = s.recorder.register(obj, rows, frozenset(), True)
        s.events.append(
            {"type": "load", "token": token, "object": kind, "n_rows": len(rows)}
        )
    return X, y


def load_metadata() -> pd.DataFrame:
    """Non-feature, non-target columns (e.g. group IDs) for building splits. Untracked: not for fitting."""
    s = _require()
    cols = s.manifest["columns"]
    keep = [
        c for c in s.table.columns if c not in set(cols["features"]) | {cols["target"]}
    ]
    return s.table[keep].copy()


def take(obj, row_ids) -> pd.DataFrame | pd.Series:
    """Supported row selection: a subset that keeps its connection to the source rows."""
    s = _require()
    if not isinstance(obj, (pd.DataFrame, pd.Series)):
        raise TypeError("take() supports pandas DataFrame or Series only")
    ids = [str(r) for r in row_ids]
    if len(set(ids)) != len(ids):
        raise ValueError("take(): duplicate row IDs")
    missing = set(ids) - set(map(str, obj.index))
    if missing:
        raise ValueError(f"take(): {len(missing)} row IDs not present in the input")
    info = s.recorder.resolve(obj)
    out = obj.loc[ids]
    token = s.recorder.register(
        out, tuple(ids), info.deps if info.known else None, info.known
    )
    s.events.append(
        {
            "type": "take",
            "token": token,
            "input_token": info.token,
            "input_status": info.status,
            "n_rows": len(ids),
        }
    )
    return out


def declare_split(
    fold: str, train_ids, eval_ids, kind: str = "development_eval", training_cutoff=None
) -> None:
    """Open fold context `fold` and record its partitions."""
    s = _require()
    train = [str(r) for r in train_ids]
    evaluate = [str(r) for r in eval_ids]
    for name, ids in (("train_ids", train), ("eval_ids", evaluate)):
        if len(set(ids)) != len(ids):
            raise ValueError(f"declare_split(): duplicate {name}")
        unknown = set(ids) - s.recorder.row_ids
        if unknown:
            raise ValueError(f"declare_split(): {len(unknown)} unknown {name}")
    s.splits.append(
        {
            "fold": fold,
            "kind": kind,
            "train_ids": train,
            "eval_ids": evaluate,
            "training_cutoff": training_cutoff,
        }
    )
    s.recorder.fold = fold


def write_predictions(fold: str, row_ids, y_pred, y_score=None) -> None:
    """Write predictions keyed by row ID and record whether they trace to a recorded prediction."""
    s = _require()
    ids = [str(r) for r in row_ids]
    if len(ids) != len(y_pred):
        raise ValueError("write_predictions(): row_ids and y_pred lengths differ")
    info = s.recorder.resolve(y_pred)
    s.events.append(
        {
            "type": "predictions",
            "fold": fold,
            "pred_token": info.token,
            "pred_status": info.status,
            "rows_match": info.rows == tuple(ids),
            "n_rows": len(ids),
        }
    )
    pred_dir = s.out_dir / "predictions"
    pred_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame({"row_id": ids, "y_pred": np.asarray(y_pred)})
    if y_score is not None:
        frame["y_score"] = np.asarray(y_score).tolist()
    frame.to_parquet(pred_dir / f"{fold}.parquet", index=False)
