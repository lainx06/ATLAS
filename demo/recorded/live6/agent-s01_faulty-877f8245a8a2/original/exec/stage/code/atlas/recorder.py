"""Candidate-side provenance recorder for the bounded supported path (SPEC §4.3, F1).

It wraps an enumerated set of scikit-learn classes and records, for each fit, a fitted-state
version with the training rows it depends on, and for each use (transform/predict), the state
version used, the fold context, and the input/output ancestry.

Limits (stated, not hidden): it runs inside the candidate's Python process, so it is not a
tamper-proof boundary. Fingerprints detect unexpected changes to tracked objects; they do not
prove that arbitrary Python preprocessing was observed. Missing traces never prove absence.
"""

import functools
import hashlib
import itertools
from dataclasses import dataclass

import numpy as np
import pandas as pd

FIT_METHODS = ("fit", "partial_fit", "fit_transform")
USE_METHODS = ("transform", "predict", "predict_proba", "decision_function")
SUPERVISED_ROLES = frozenset({"supervised_transformer", "classifier"})
_MISSING = object()


def supported_classes() -> dict[type, str]:
    """The enumerated supported operations (SPEC §4.2) and their roles."""
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_selection import SelectKBest
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    return {
        StandardScaler: "transformer",
        SimpleImputer: "transformer",
        SelectKBest: "supervised_transformer",
        LogisticRegression: "classifier",
        RandomForestClassifier: "classifier",
        DummyClassifier: "classifier",
    }


def _supported_configuration(est) -> bool:
    from sklearn.feature_selection import SelectKBest, f_classif

    if isinstance(est, SelectKBest):
        return est.score_func is f_classif
    return True


def fingerprint(obj) -> str | None:
    """Content hash of a frame, series or array; None for anything else."""
    h = hashlib.sha256()
    if isinstance(obj, pd.DataFrame):
        h.update(pd.util.hash_pandas_object(obj, index=True).to_numpy().tobytes())
        h.update(repr([str(c) for c in obj.columns]).encode())
    elif isinstance(obj, pd.Series):
        h.update(pd.util.hash_pandas_object(obj, index=True).to_numpy().tobytes())
        h.update(repr(str(obj.name)).encode())
    elif isinstance(obj, np.ndarray):
        h.update(np.ascontiguousarray(obj).tobytes())
        h.update(repr((obj.shape, obj.dtype.str)).encode())
    else:
        return None
    return h.hexdigest()


@dataclass
class _Tracked:
    obj: object
    token: str
    rows: tuple[str, ...] | None
    deps: frozenset | None
    known: bool
    fp: str


@dataclass
class Info:
    """What the recorder knows about one input object at the moment it is used."""

    status: str  # tracked | untracked | mutated | none
    token: str | None
    rows: tuple[str, ...] | None
    deps: frozenset | None
    known: bool


class Recorder:
    def __init__(self, table_row_ids):
        self.row_ids = frozenset(map(str, table_row_ids))
        self.events: list[dict] = []
        self.fold = "global"
        self._tracked: dict[int, _Tracked] = {}
        self._instances: dict[int, tuple[object, str]] = {}
        self._states: dict[str, dict] = {}
        self._ids = itertools.count()
        self._depth = 0
        self._patched: list[tuple[type, str, object]] = []

    # --- identity, registration, resolution -------------------------------------------------

    def identity(self, obj) -> tuple[str, ...] | None:
        """Row identity from a unique index of known row IDs. Identity is not ancestry."""
        if isinstance(obj, (pd.DataFrame, pd.Series)):
            rows = tuple(map(str, obj.index))
            if obj.index.is_unique and set(rows) <= self.row_ids:
                return rows
        return None

    def register(self, obj, rows, deps, known) -> str | None:
        fp = fingerprint(obj)
        if fp is None:
            return None
        token = f"d{next(self._ids)}"
        self._tracked[id(obj)] = _Tracked(
            obj, token, tuple(rows) if rows is not None else None, deps, known, fp
        )
        return token

    def resolve(self, obj) -> Info:
        if obj is None:
            return Info("none", None, None, None, False)
        rec = self._tracked.get(id(obj))
        if rec is not None and rec.obj is obj:
            if fingerprint(obj) != rec.fp:
                self.gap("unexplained_mutation", token=rec.token)
                return Info("mutated", rec.token, self.identity(obj), None, False)
            return Info("tracked", rec.token, rec.rows, rec.deps, rec.known)
        rows = self.identity(obj)
        known = False  # untracked: a valid index is identity, not ancestry
        return Info("untracked", None, rows, frozenset() if known else None, known)

    def gap(self, reason: str, **detail) -> None:
        self.events.append(
            {"type": "gap", "reason": reason, "fold": self.fold, **detail}
        )

    # --- patching -------------------------------------------------------------------------------

    def install(self) -> None:
        for cls, role in supported_classes().items():
            for name in FIT_METHODS + USE_METHODS:
                if not hasattr(cls, name):
                    continue
                self._patched.append((cls, name, cls.__dict__.get(name, _MISSING)))
                setattr(cls, name, self._wrap(cls, role, name, getattr(cls, name)))

    def uninstall(self) -> None:
        for cls, name, previous in reversed(self._patched):
            if previous is _MISSING:
                delattr(cls, name)
            else:
                setattr(cls, name, previous)
        self._patched.clear()

    def _wrap(self, cls, role, name, original):
        recorder = self

        @functools.wraps(original)
        def wrapper(est, *args, **kwargs):
            if (
                recorder._depth > 0
            ):  # internal calls (fit_transform -> fit, predict -> decision_function)
                return original(est, *args, **kwargs)
            X = args[0] if args else kwargs.get("X")
            y = args[1] if len(args) > 1 else kwargs.get("y")
            x_info = recorder.resolve(X)
            y_info = (
                recorder.resolve(y) if name in FIT_METHODS and y is not None else None
            )
            recorder._depth += 1
            try:
                result = original(est, *args, **kwargs)
            finally:
                recorder._depth -= 1
            if name in FIT_METHODS:
                recorder._record_fit(
                    est, cls, role, x_info, y_info, partial=name == "partial_fit"
                )
            if name == "fit_transform" or name in USE_METHODS:
                recorder._record_use(
                    est,
                    cls,
                    "transform" if name == "fit_transform" else name,
                    x_info,
                    result,
                )
            return result

        return wrapper

    # --- events ---------------------------------------------------------------------------------

    def _instance_id(self, est) -> str:
        entry = self._instances.get(id(est))
        if entry is None or entry[0] is not est:
            entry = (est, f"i{next(self._ids)}")
            self._instances[id(est)] = entry
        return entry[1]

    def _record_fit(
        self, est, cls, role, x_info: Info, y_info: Info | None, partial: bool
    ) -> None:
        inst = self._instance_id(est)
        previous = self._states.get(inst)
        supported = _supported_configuration(est)
        labels_supplied = y_info is not None
        labels_traced = (not labels_supplied) or (
            y_info.known and y_info.rows == x_info.rows
        )
        known = supported and x_info.known and x_info.rows is not None and labels_traced
        deps = frozenset(x_info.rows) | x_info.deps if known else None
        if partial and previous is not None and deps is not None:
            deps = None if previous["deps"] is None else deps | previous["deps"]
        if not supported:
            self.gap("unsupported_configuration", instance=inst, cls=cls.__name__)
        if x_info.status == "untracked":
            self.gap("untracked_input", instance=inst, cls=cls.__name__, method="fit")
        if labels_supplied and not labels_traced:
            self.gap("untraced_labels", instance=inst, cls=cls.__name__)
        version = previous["version"] + 1 if previous else 1
        self._states[inst] = {"version": version, "deps": deps, "fit_fold": self.fold}
        self.events.append(
            {
                "type": "fit",
                "instance": inst,
                "version": version,
                "class": cls.__name__,
                "role": role,
                "classifier": role == "classifier",
                "supported": supported,
                "fold": self.fold,
                "input_token": x_info.token,
                "input_status": x_info.status,
                "labels_token": y_info.token if y_info else None,
                "labels_supplied": labels_supplied,
                "labels_used": labels_supplied and role in SUPERVISED_ROLES,
                "rows": list(x_info.rows) if x_info.rows is not None else None,
                "deps": sorted(deps) if deps is not None else None,
            }
        )

    def _record_use(self, est, cls, method, x_info: Info, result) -> None:
        inst = self._instance_id(est)
        state = self._states.get(inst)
        state_deps = state["deps"] if state else None
        effective = (
            state_deps | x_info.deps
            if state_deps is not None and x_info.known
            else None
        )
        rows = x_info.rows
        if isinstance(result, (pd.DataFrame, pd.Series)):
            lineage_ok = rows is not None and tuple(map(str, result.index)) == rows
        else:
            lineage_ok = rows is not None and len(result) == len(rows)
        if not lineage_ok:
            self.gap("lineage_break", instance=inst, cls=cls.__name__, method=method)
        if x_info.status == "untracked":
            self.gap("untracked_input", instance=inst, cls=cls.__name__, method=method)
        known = effective is not None and lineage_ok
        out_token = self.register(
            result, rows if lineage_ok else None, effective if known else None, known
        )
        self.events.append(
            {
                "type": "use",
                "instance": inst,
                "version": state["version"] if state else None,
                "state_fit_fold": state["fit_fold"] if state else None,
                "class": cls.__name__,
                "method": method,
                "fold": self.fold,
                "input_token": x_info.token,
                "input_status": x_info.status,
                "input_known": x_info.known,
                "output_token": out_token,
                "rows": list(rows) if rows is not None else None,
                "state_deps": sorted(state_deps) if state_deps is not None else None,
                "effective_deps": sorted(effective) if effective is not None else None,
            }
        )
