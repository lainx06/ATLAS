"""Trusted evaluator primitives (SPEC §8): class labels and metric formulas.

These run in the trusted evaluator, after the candidate process has exited, on the evaluator's
own copy of the table. Labels are the `class_map` keys; candidate predictions are matched to them
by value, never trusted as given.
"""

import math
import numbers

import numpy as np

METRICS = ("balanced_accuracy", "macro_f1")
TOLERANCE = 1e-6  # fixed absolute tolerance, compared in float64 (SPEC §8)


def canonical_label(value, class_map: dict[str, str]) -> str | None:
    """The `class_map` key that `value` denotes, or None if it denotes none.

    Accepted: a string equal to a key, an integer whose decimal form equals a key, or an integral
    finite float (pandas reads an integer column holding nulls as float). Booleans, other floats,
    nulls and class *names* are not labels.
    """
    if isinstance(value, (bool, np.bool_)):
        return None
    if isinstance(value, str):
        key = value
    elif isinstance(value, numbers.Integral):
        try:
            key = str(int(value))
        except ValueError:  # beyond Python's integer-to-string digit limit: not a key
            return None
    elif isinstance(value, numbers.Real):
        try:
            number = float(value)
        except OverflowError:  # e.g. a Fraction outside the float64 range
            return None
        if not math.isfinite(number) or not number.is_integer():
            return None
        key = str(int(number))
    else:
        return None
    return key if key in class_map else None


def balanced_accuracy(y_true: list[str], y_pred: list[str], order: list[str]) -> float:
    """Mean recall over the classes present in `y_true` (in `order`, the class_map order)."""
    present = set(y_true)
    recalls = []
    for c in order:
        if c not in present:
            continue
        rows = [p for t, p in zip(y_true, y_pred, strict=True) if t == c]
        recalls.append(sum(p == c for p in rows) / len(rows))
    return float(np.mean(recalls))


def macro_f1(y_true: list[str], y_pred: list[str], order: list[str]) -> float:
    """Mean of 2·TP/(2·TP+FP+FN) over the classes present in `y_true` or `y_pred`."""
    present = set(y_true) | set(y_pred)
    pairs = list(zip(y_true, y_pred, strict=True))
    scores = []
    for c in order:
        if c not in present:
            continue
        tp = sum(t == c and p == c for t, p in pairs)
        fp = sum(t != c and p == c for t, p in pairs)
        fn = sum(t == c and p != c for t, p in pairs)
        scores.append(2 * tp / (2 * tp + fp + fn))
    return float(np.mean(scores))


def metric(name: str, y_true: list[str], y_pred: list[str], order: list[str]) -> float:
    return {"balanced_accuracy": balanced_accuracy, "macro_f1": macro_f1}[name](
        y_true, y_pred, order
    )


def within_tolerance(reported: float, recomputed: float) -> bool:
    """The literal SPEC §8 rule: abs(reported - recomputed) <= 1e-6 in float64.

    No relative tolerance, rounding or extra epsilon. A decimal-intended equality can fall on
    either side after binary representation.
    """
    return abs(float(reported) - float(recomputed)) <= TOLERANCE


def most_frequent(labels: list[str], order: list[str]) -> str:
    """The most frequent label; ties go to the earliest class in the declared `class_map` order."""
    counts = {c: labels.count(c) for c in order}
    best = max(counts.values())
    return next(c for c in order if counts[c] == best)
