"""Window, separation and time-availability assertions (SPEC §5, policy-v1.3). Trusted side.

Runs in the trusted evaluator on the evaluator's own table copy and the declared splits. Times are
finite numbers in the one declared unit (SPEC §3). A null, non-numeric, boolean or nonfinite time
makes its row unknown. Known values decide first: a witness among known rows is a FAIL with the
unknown counts disclosed; otherwise unknown rows give NOT_ASSESSED(missing_metadata), and PASS
needs every participating row known.

None of these checks is proof of statistical independence (SPEC §15).
"""

import math
import numbers

import numpy as np
import pandas as pd

from atlas.contracts import AssertionResult, EvidenceRef, Manifest, Reason, Status

WINDOW = "split.no_window_overlap"
SEPARATION = "split.temporal_separation"
LABELS = "temporal.training_labels_available_by_cutoff"
PRECEDES = "temporal.cutoff_precedes_evaluation"
FEATURES = "temporal.features_available_when_used"
ASSERTIONS = (WINDOW, SEPARATION, LABELS, PRECEDES, FEATURES)

WINDOW_LIMITATION = (
    "Verifies declared stream identity and window intervals; not proof of statistical "
    "independence."
)
SEPARATION_LIMITATION = (
    "Verifies the declared separation rule; not proof of statistical independence."
)
DECLARED_BY_CODE = (
    "Training cutoffs and fold membership are declared by the evaluated code; the data are "
    "checked against those declarations, which are not verified independently."
)
MAX_WITNESSES = 20
_PAIR_BUDGET = 1_000_000  # pairs compared per chunk, to bound memory


def temporal_assertions(
    manifest: Manifest,
    table: pd.DataFrame,
    splits: list[dict],
    evidence: list[EvidenceRef],
    evidence_valid: bool = True,
    group_result: AssertionResult | None = None,
) -> dict[str, AssertionResult]:
    """Compute every window/separation/temporal assertion; the policy decides which are required.

    `group_result` is the computed `split.no_group_overlap`; route C of the window check depends
    on it being a valid PASS.
    """
    if not evidence_valid:
        return {
            aid: AssertionResult(
                assertion_id=aid,
                status=Status.ERROR,
                reason=Reason.EVIDENCE_INVALID,
                evidence=evidence,
                evidence_valid=False,
            )
            for aid in ASSERTIONS
        }
    if not _participating(splits):
        return {
            aid: AssertionResult(
                assertion_id=aid,
                status=Status.NOT_ASSESSED,
                reason=Reason.NOT_EXECUTED,
                observed={"declared_folds": len(splits), "participating_rows": 0},
                evidence=evidence,
            )
            for aid in ASSERTIONS
        }
    return {
        WINDOW: _window_overlap(manifest, table, splits, evidence, group_result),
        SEPARATION: _separation(manifest, table, splits, evidence),
        LABELS: _labels_by_cutoff(manifest, table, splits, evidence),
        PRECEDES: _cutoff_precedes(manifest, table, splits, evidence),
        FEATURES: _features_available(manifest, table, splits, evidence),
    }


# --- values -----------------------------------------------------------------------------------


def time_value(value) -> float:
    """A usable time as a float, or NaN (null, non-numeric, boolean or nonfinite)."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real):
        return math.nan
    number = float(value)
    return number if math.isfinite(number) else math.nan


def _times(table: pd.DataFrame, column: str) -> pd.Series:
    return table[column].map(time_value).astype(float)


def _column(table: pd.DataFrame, name: str | None) -> str | None:
    return name if name is not None and name in table.columns else None


def _participating(splits: list[dict]) -> list[str]:
    return list(
        dict.fromkeys(r for s in splits for r in [*s["train_ids"], *s["eval_ids"]])
    )


def _result(aid, status, evidence, observed, reason=None, **extra) -> AssertionResult:
    return AssertionResult(
        assertion_id=aid,
        status=status,
        reason=reason,
        observed=observed,
        evidence=evidence,
        **extra,
    )


def _status(
    witnesses: int, invalid: bool, unknown: bool
) -> tuple[Status, Reason | None]:
    """Known values first: a valid FAIL stands; then invalid evidence; then missing values."""
    if witnesses:
        return Status.FAIL, None
    if invalid:
        return Status.ERROR, Reason.EVIDENCE_INVALID
    if unknown:
        return Status.NOT_ASSESSED, Reason.MISSING_METADATA
    return Status.PASS, None


def _pairs(tr_lo, tr_hi, ev_lo, ev_hi):
    """Yield (train index, eval index, signed gap) blocks over all train x eval pairs.

    For intervals [lo, hi) the signed gap is max(ev_lo - tr_hi, tr_lo - ev_hi): negative when they
    overlap, 0 when adjacent. A point is the interval [t, t], so its gap is abs(t_eval - t_train).
    """
    if not len(tr_lo) or not len(ev_lo):
        return
    step = max(1, _PAIR_BUDGET // len(tr_lo))
    for start in range(0, len(ev_lo), step):
        lo, hi = ev_lo[start : start + step], ev_hi[start : start + step]
        gap = np.maximum(lo[None, :] - tr_hi[:, None], tr_lo[:, None] - hi[None, :])
        yield start, gap


# --- split.no_window_overlap ------------------------------------------------------------------


def _bounds_problem(manifest: Manifest, table: pd.DataFrame) -> str | None:
    cols = manifest.columns
    if (
        _column(table, cols.window_start) is None
        or _column(table, cols.window_end) is None
    ):
        return "window_start/window_end columns not declared or absent"
    if manifest.time_basis is None:
        return "time_basis not declared"
    return None


def _by_stream(ids: list[str], stream: pd.Series) -> dict:
    found: dict = {}
    for r in ids:
        if not pd.isna(stream[r]):
            found.setdefault(stream[r], []).append(r)
    return found


def _usable_windows(ids, starts, ends) -> tuple[list[str], np.ndarray, np.ndarray, int]:
    """Windows with known bounds and start < end (lead policy, v1.3); the rest are unusable."""
    # The comparison is False for NaN bounds, start == end and start > end.
    keep = [r for r in ids if starts[r] < ends[r]]
    return (
        keep,
        np.array([starts[r] for r in keep], dtype=float),
        np.array([ends[r] for r in keep], dtype=float),
        len(ids) - len(keep),
    )


def _stream_group_contradictions(
    table: pd.DataFrame, stream_col, group_col, splits
) -> list[dict]:
    if stream_col is None or group_col is None:
        return []
    rows = table.loc[_participating(splits), [stream_col, group_col]].dropna()
    groups = rows.groupby(stream_col)[group_col].unique()
    return [
        {"stream_id": str(k), "group_ids": sorted(map(str, g))}
        for k, g in groups.items()
        if len(g) > 1
    ]


def _window_overlap(manifest, table, splits, evidence, group_result) -> AssertionResult:
    cols = manifest.columns
    stream_col = _column(table, cols.stream_id)
    bounds_problem = _bounds_problem(manifest, table)
    starts = ends = None
    if bounds_problem is None:
        starts = _times(table, cols.window_start)
        ends = _times(table, cols.window_end)

    folds, witnesses, n_witnesses = [], [], 0
    for s in splits:
        fold = {"fold": s["fold"]}
        folds.append(fold)
        if stream_col is None:
            fold.update(
                direct="incomplete", why="stream_id column not declared or absent"
            )
            continue
        stream = table[stream_col]
        rows = [*s["train_ids"], *s["eval_ids"]]
        unknown_stream = sum(bool(pd.isna(stream[r])) for r in rows)
        train_by, eval_by = (
            _by_stream(s["train_ids"], stream),
            _by_stream(s["eval_ids"], stream),
        )
        crossing = sorted(set(train_by) & set(eval_by), key=str)
        unusable = 0
        for key in crossing:
            if bounds_problem is not None:
                unusable += len(train_by[key]) + len(eval_by[key])
                continue
            tr_ids, tr_lo, tr_hi, bad_tr = _usable_windows(train_by[key], starts, ends)
            ev_ids, ev_lo, ev_hi, bad_ev = _usable_windows(eval_by[key], starts, ends)
            unusable += bad_tr + bad_ev
            for offset, gap in _pairs(tr_lo, tr_hi, ev_lo, ev_hi):
                for i, j in zip(*np.nonzero(gap < 0), strict=True):
                    n_witnesses += 1
                    if len(witnesses) < MAX_WITNESSES:
                        e = offset + j
                        witnesses.append(
                            {
                                "fold": s["fold"],
                                "stream_id": str(key),
                                "train_row_id": tr_ids[i],
                                "train_window": [tr_lo[i], tr_hi[i]],
                                "eval_row_id": ev_ids[e],
                                "eval_window": [ev_lo[e], ev_hi[e]],
                            }
                        )
        fold.update(
            streams_in_both_partitions=[str(k) for k in crossing],
            rows_with_unknown_stream=unknown_stream,
            rows_with_unusable_bounds=unusable,
        )
        if unknown_stream or unusable:
            fold["direct"] = "incomplete"
            fold["why"] = (
                "rows with unknown stream identity"
                if unknown_stream
                else f"unusable bounds in a stream in both partitions ({bounds_problem or 'bounds missing, or start >= end'})"
            )
        else:
            fold["direct"] = "complete"
            fold["basis"] = (
                "interval_comparison" if crossing else "stream_membership_disjoint"
            )

    observed: dict = {
        "folds": folds,
        "witnesses": witnesses,
        "witness_count": n_witnesses,
    }
    limits = [WINDOW_LIMITATION]
    if n_witnesses:  # a valid direct-route finding is never suppressed
        observed["established_by"] = "route D: overlapping windows in the same stream"
        return _result(WINDOW, Status.FAIL, evidence, observed, limitations=limits)
    incomplete = [f["fold"] for f in folds if f["direct"] == "incomplete"]
    if not incomplete:
        observed["established_by"] = {f["fold"]: f["basis"] for f in folds}
        return _result(WINDOW, Status.PASS, evidence, observed, limitations=limits)

    # Route C, only for the folds the direct route could not complete.
    containment = manifest.window_containment
    group_col = _column(table, cols.group_id)
    contradictions = _stream_group_contradictions(table, stream_col, group_col, splits)
    observed["route_c"] = {
        "needed_for_folds": incomplete,
        "declaration": containment.model_dump() if containment else None,
        "stream_group_contradictions": contradictions,
        "group_check": None
        if group_result is None
        else {
            "assertion_id": group_result.assertion_id,
            "status": group_result.status,
            "evidence_valid": group_result.evidence_valid,
        },
    }
    if containment is None or group_col is None:
        observed["route_c"]["why"] = (
            "no window_containment declaration"
            if containment is None
            else "group_id column not declared or absent"
        )
        return _result(
            WINDOW,
            Status.NOT_ASSESSED,
            evidence,
            observed,
            Reason.MISSING_METADATA,
            limitations=limits,
        )
    if contradictions:
        observed["route_c"]["why"] = (
            "a stream is observed in several groups: documented containment is contradicted"
        )
        return _result(
            WINDOW,
            Status.NOT_ASSESSED,
            evidence,
            observed,
            Reason.NO_SUPPORTED_RULE,
            limitations=limits,
        )
    if (
        group_result is None
        or group_result.status is not Status.PASS
        or not group_result.evidence_valid
    ):
        observed["route_c"]["why"] = (
            "route C needs a valid split.no_group_overlap PASS, which is absent"
        )
        return _result(
            WINDOW,
            Status.NOT_ASSESSED,
            evidence,
            observed,
            Reason.MISSING_METADATA,
            limitations=limits,
            depends_on=["split.no_group_overlap"],
        )
    observed["established_by"] = {
        f["fold"]: f.get("basis", "documented_containment") for f in folds
    }
    return _result(
        WINDOW,
        Status.PASS,
        evidence,
        observed,
        depends_on=["split.no_group_overlap"],
        limitations=[
            "PASS for folds "
            + ", ".join(incomplete)
            + " is conditional on documented containment, not independently verified: "
            f"source {containment.source!r}; statement {containment.statement!r}. "
            "The source was not fetched; a non-empty declaration does not show that it proves "
            "the claim. It also depends on the valid split.no_group_overlap PASS.",
            *limits,
        ],
    )


# --- split.temporal_separation ----------------------------------------------------------------


def _separation_problem(manifest: Manifest, table: pd.DataFrame) -> str | None:
    rule, basis, cols = manifest.separation_rule, manifest.time_basis, manifest.columns
    if rule.times is None:
        return "separation_rule.times not declared (legacy 0.2 rule); the basis is never guessed"
    if basis is None:
        return "time_basis not declared"
    if rule.scope == "global" and basis.scope != "global":
        return (
            "a global separation rule needs time_basis.scope 'global' "
            f"(declared: {basis.scope or 'unspecified'})"
        )
    if rule.scope == "per_stream" and _column(table, cols.stream_id) is None:
        return "stream_id column not declared or absent"
    if rule.times == "prediction_time" and _column(table, cols.prediction_time) is None:
        return "prediction_time column not declared or absent"
    if rule.times == "window" and (
        _column(table, cols.window_start) is None
        or _column(table, cols.window_end) is None
    ):
        return "window_start/window_end columns not declared or absent"
    return None


def _separation(manifest, table, splits, evidence) -> AssertionResult:
    rule, cols = manifest.separation_rule, manifest.columns
    limits = [SEPARATION_LIMITATION]
    if rule is None:
        return _result(
            SEPARATION,
            Status.NOT_ASSESSED,
            evidence,
            {},
            Reason.NO_DECLARED_RULE,
            limitations=limits,
        )
    observed: dict = {"rule": rule.model_dump()}
    problem = _separation_problem(manifest, table)
    if problem is not None:
        observed["problem"] = problem
        return _result(
            SEPARATION,
            Status.NOT_ASSESSED,
            evidence,
            observed,
            Reason.MISSING_METADATA,
            limitations=limits,
        )
    if rule.times == "prediction_time":
        lo = hi = _times(table, cols.prediction_time)
        usable = lo.notna()
    else:
        lo, hi = _times(table, cols.window_start), _times(table, cols.window_end)
        usable = lo < hi  # lead policy (v1.3): start < end
    stream = table[cols.stream_id] if rule.scope == "per_stream" else None

    folds, witnesses, n_witnesses, unknown_total = [], [], 0, 0
    for s in splits:
        rows = [*s["train_ids"], *s["eval_ids"]]
        known = [
            r for r in rows if usable[r] and (stream is None or not pd.isna(stream[r]))
        ]
        unknown = len(rows) - len(known)
        unknown_total += unknown
        key_of = (lambda r: None) if stream is None else (lambda r: stream[r])
        known_set = set(known)
        train = [r for r in s["train_ids"] if r in known_set]
        ev = [r for r in s["eval_ids"] if r in known_set]
        min_gap_seen = None
        for key in {key_of(r) for r in train} & {key_of(r) for r in ev}:
            tr = [r for r in train if key_of(r) == key]
            ee = [r for r in ev if key_of(r) == key]
            tr_lo, tr_hi = lo[tr].to_numpy(), hi[tr].to_numpy()
            ev_lo, ev_hi = lo[ee].to_numpy(), hi[ee].to_numpy()
            for offset, gap in _pairs(tr_lo, tr_hi, ev_lo, ev_hi):
                smallest = float(gap.min())
                min_gap_seen = (
                    smallest if min_gap_seen is None else min(min_gap_seen, smallest)
                )
                for i, j in zip(*np.nonzero(gap < rule.min_gap), strict=True):
                    n_witnesses += 1
                    if len(witnesses) < MAX_WITNESSES:
                        witnesses.append(
                            {
                                "fold": s["fold"],
                                "stream_id": None if key is None else str(key),
                                "train_row_id": tr[i],
                                "eval_row_id": ee[offset + j],
                                "gap": float(gap[i, j]),
                            }
                        )
        folds.append(
            {
                "fold": s["fold"],
                "smallest_gap": min_gap_seen,
                "rows_with_unknown_time": unknown,
            }
        )
    observed.update(
        folds=folds,
        witnesses=witnesses,
        witness_count=n_witnesses,
        direction="two-sided, within each fold",
    )
    status, reason = _status(n_witnesses, False, unknown_total > 0)
    return _result(SEPARATION, status, evidence, observed, reason, limitations=limits)


# --- future_time: temporal.* ------------------------------------------------------------------


def _clock_problem(manifest: Manifest, table: pd.DataFrame, need_global: bool):
    basis = manifest.time_basis
    if basis is None:
        return "time_basis not declared"
    if _column(table, manifest.columns.prediction_time) is None:
        return "prediction_time column not declared or absent"
    if need_global and basis.scope != "global":
        return (
            "a single training cutoff per fold needs a global clock "
            f"(time_basis.scope: {basis.scope or 'unspecified'})"
        )
    return None


def _cutoff(split: dict) -> tuple[str, float | None]:
    """('ok', value), ('missing', None) or ('invalid', None) for a fold's declared cutoff."""
    raw = split.get("training_cutoff")
    if raw is None:
        return "missing", None
    value = time_value(raw)
    return ("invalid", None) if math.isnan(value) else ("ok", value)


def _unknown(reason: str, aid: str, evidence, observed=None) -> AssertionResult:
    return _result(
        aid,
        Status.NOT_ASSESSED,
        evidence,
        {"problem": reason, **(observed or {})},
        Reason.MISSING_METADATA,
        limitations=[DECLARED_BY_CODE],
    )


def _label_times(manifest, table, pt: pd.Series) -> pd.Series | None:
    la = manifest.label_availability
    if la.column is not None:
        col = _column(table, la.column)
        return None if col is None else _times(table, col)
    return pt + la.horizon + la.reporting_delay


def _labels_by_cutoff(manifest, table, splits, evidence) -> AssertionResult:
    problem = _clock_problem(manifest, table, need_global=True)
    if problem is None and manifest.label_availability is None:
        problem = "label_availability not declared"
    if problem is not None:
        return _unknown(problem, LABELS, evidence)
    pt = _times(table, manifest.columns.prediction_time)
    la = _label_times(manifest, table, pt)
    if la is None:
        return _unknown("label availability column absent", LABELS, evidence)

    folds, witnesses, n_witnesses, invalid, unknown = [], [], 0, [], 0
    for s in splits:
        state, cutoff = _cutoff(s)
        fold = {"fold": s["fold"], "cutoff": cutoff, "cutoff_state": state}
        folds.append(fold)
        if state != "ok":
            if state == "invalid":
                invalid.append(s["fold"])
            unknown += state == "missing"
            continue
        n_unknown = 0
        for r in s["train_ids"]:
            p, a = pt[r], la[r]
            if math.isnan(p) or math.isnan(a):
                n_unknown += 1
            elif p > cutoff or a > cutoff:
                n_witnesses += 1
                if len(witnesses) < MAX_WITNESSES:
                    witnesses.append(
                        {
                            "fold": s["fold"],
                            "row_id": r,
                            "prediction_time": p,
                            "label_available": a,
                            "cutoff": cutoff,
                        }
                    )
        fold["training_rows_with_unknown_time"] = n_unknown
        unknown += n_unknown
    observed = {
        "folds": folds,
        "witnesses": witnesses,
        "witness_count": n_witnesses,
        "invalid_cutoff_folds": invalid,
    }
    status, reason = _status(n_witnesses, bool(invalid), unknown > 0)
    return _result(
        LABELS,
        status,
        evidence,
        observed,
        reason,
        evidence_valid=status is not Status.ERROR,
        limitations=[DECLARED_BY_CODE],
    )


def _cutoff_precedes(manifest, table, splits, evidence) -> AssertionResult:
    gap = manifest.temporal_gap
    if (
        gap is not None and gap < 0
    ):  # decided by the declaration alone (SPEC: temporal_gap >= 0)
        return _result(
            PRECEDES,
            Status.FAIL,
            evidence,
            {"temporal_gap": gap, "rule": "temporal_gap must be >= 0"},
            limitations=[DECLARED_BY_CODE],
        )
    problem = _clock_problem(manifest, table, need_global=True)
    if problem is None and gap is None:
        problem = "temporal_gap not declared"
    if problem is not None:
        return _unknown(problem, PRECEDES, evidence)
    pt = _times(table, manifest.columns.prediction_time)

    folds, witnesses, n_witnesses, invalid, unknown = [], [], 0, [], 0
    for s in splits:
        state, cutoff = _cutoff(s)
        fold = {"fold": s["fold"], "cutoff": cutoff, "cutoff_state": state}
        folds.append(fold)
        if state != "ok":
            if state == "invalid":
                invalid.append(s["fold"])
            unknown += state == "missing"
            continue
        times = pt[s["eval_ids"]]
        fold["eval_rows_with_unknown_time"] = int(times.isna().sum())
        unknown += fold["eval_rows_with_unknown_time"]
        known = times.dropna()
        fold["earliest_known_eval_time"] = float(known.min()) if len(known) else None
        early = known[known < cutoff + gap]
        n_witnesses += len(early)
        for r, p in early.items():
            if len(witnesses) < MAX_WITNESSES:
                witnesses.append(
                    {
                        "fold": s["fold"],
                        "row_id": r,
                        "prediction_time": float(p),
                        "cutoff_plus_gap": cutoff + gap,
                    }
                )
    observed = {
        "temporal_gap": gap,
        "folds": folds,
        "witnesses": witnesses,
        "witness_count": n_witnesses,
        "invalid_cutoff_folds": invalid,
    }
    status, reason = _status(n_witnesses, bool(invalid), unknown > 0)
    return _result(
        PRECEDES,
        status,
        evidence,
        observed,
        reason,
        evidence_valid=status is not Status.ERROR,
        limitations=[DECLARED_BY_CODE],
    )


def _features_available(manifest, table, splits, evidence) -> AssertionResult:
    """Same-row comparison on the row's declared clock: assessable under any scope (v1.3)."""
    problem = _clock_problem(manifest, table, need_global=False)
    if problem is not None:
        return _unknown(problem, FEATURES, evidence)
    rows = _participating(splits)
    pt = _times(table, manifest.columns.prediction_time)[rows]
    declared = manifest.feature_availability or {}
    per_feature, witnesses, n_witnesses, unknown = {}, [], 0, False
    for feature in manifest.columns.features:
        source = declared.get(feature)
        if source is None:
            per_feature[feature] = {"status": "no availability declared"}
            unknown = True
            continue
        if source.column is not None:
            col = _column(table, source.column)
            if col is None:
                per_feature[feature] = {"status": f"column {source.column!r} absent"}
                unknown = True
                continue
            available = _times(table, col)[rows]
        else:
            available = pt + source.offset
        missing = available.isna() | pt.isna()
        late = available[~missing] > pt[~missing]
        late_rows = list(late[late].index)
        per_feature[feature] = {
            "rows_with_unknown_time": int(missing.sum()),
            "late_rows": len(late_rows),
        }
        unknown = unknown or bool(missing.any())
        n_witnesses += len(late_rows)
        for r in late_rows:
            if len(witnesses) < MAX_WITNESSES:
                witnesses.append(
                    {
                        "feature": feature,
                        "row_id": r,
                        "available": float(available[r]),
                        "prediction_time": float(pt[r]),
                    }
                )
    observed = {
        "features": per_feature,
        "witnesses": witnesses,
        "witness_count": n_witnesses,
        "clock_scope": manifest.time_basis.scope or "unspecified",
    }
    status, reason = _status(n_witnesses, False, unknown)
    return _result(FEATURES, status, evidence, observed, reason)
