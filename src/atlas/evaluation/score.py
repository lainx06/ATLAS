"""Finding-level scoring for the T-11 comparison (SPEC §17 "Finding-level scoring";
docs/EVALUATION.md "Scoring").

Per case and leg, against the case's expected violated assertion IDs (`evaluation/expected.json`),
counted per canonical assertion ID:

- **Leg (a) ATLAS:** an ID is detected when its status is FAIL on valid evidence. An expected ID
  that ATLAS left NOT_ASSESSED is a **coverage gap**, not a miss; one with status ERROR (or a FAIL
  or PASS on invalid evidence) is an **error**, not a miss. Neither counts as FN.
- **Leg (b) Nemotron alone:** each VALID trial is scored on its `violated` list. INVALID_REPLY,
  NOT_SENT and MODEL_ERROR trials have no valid answer: they are counted separately and never
  scored as a detection or a miss.

Precision is TP / (TP + FP) and recall TP / (TP + FN); either is the string "undefined" when its
denominator is zero, never a manufactured number. Clean controls also report false positives and
the false-violation rate (SPEC §17). Every scheduled trial is reported. All of it is descriptive.
"""

from fractions import Fraction

from atlas.evaluation.baseline import INVALID_REPLY, MODEL_ERROR, NOT_SENT, VALID

UNDEFINED = "undefined"


def ratio(numerator: int, denominator: int):
    """A float in [0, 1], or UNDEFINED when the denominator is zero."""
    if denominator == 0:
        return UNDEFINED
    return float(Fraction(numerator, denominator))


def counts(predicted, expected, *, gaps=(), errors=()) -> dict:
    """TP/FP/FN as ID lists. Expected IDs in `gaps` or `errors` are excluded from FN."""
    predicted, expected = set(predicted), set(expected)
    excused = (set(gaps) | set(errors)) - predicted
    return {
        "tp": sorted(predicted & expected),
        "fp": sorted(predicted - expected),
        "fn": sorted(expected - predicted - excused),
    }


def _totals(rows: list[dict]) -> dict:
    tp = sum(len(r["tp"]) for r in rows)
    fp = sum(len(r["fp"]) for r in rows)
    fn = sum(len(r["fn"]) for r in rows)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
    }


def score_atlas(case_id: str, expected, atlas: dict) -> dict:
    """One case's leg (a) result: `atlas` holds `outcome` and `assertions` (id/status/
    evidence_valid), or `available: False` when no ATLAS result could be obtained."""
    if not atlas.get("available"):
        return {"case_id": case_id, "available": False, "outcome": None,
                "reason": atlas.get("reason"), "tp": [], "fp": [], "fn": [],
                "coverage_gaps": [], "errors": [], "expected_gaps": [],
                "expected_errors": []}  # fmt: skip
    rows = atlas["assertions"]
    detected = [
        r["assertion_id"]
        for r in rows
        if r["status"] == "FAIL" and r.get("evidence_valid", True)
    ]
    gaps = [r["assertion_id"] for r in rows if r["status"] == "NOT_ASSESSED"]
    errors = [
        r["assertion_id"]
        for r in rows
        if r["status"] == "ERROR"
        or (r["status"] in ("FAIL", "PASS") and not r.get("evidence_valid", True))
    ]
    c = counts(detected, expected, gaps=gaps, errors=errors)
    return {
        "case_id": case_id,
        "available": True,
        "outcome": atlas["outcome"],
        **c,
        "coverage_gaps": sorted(gaps),
        "errors": sorted(errors),
        "expected_gaps": sorted(set(gaps) & set(expected)),
        "expected_errors": sorted(set(errors) & set(expected)),
    }


def score_baseline(case_id: str, expected, trials: list[dict]) -> dict:
    """One case's leg (b) result: every scheduled trial, scored or counted separately."""
    scored = []
    for t in trials:
        row = {
            "repetition": t["repetition"],
            "status": t["status"],
            "code": t.get("code"),
        }
        if t["status"] == VALID:
            row.update(counts(t["violated"], expected), violated=sorted(t["violated"]))
        scored.append(row)
    valid = [r for r in scored if r["status"] == VALID]
    return {
        "case_id": case_id,
        "trials_scheduled": len(trials),
        "valid": len(valid),
        "invalid_reply": sum(r["status"] == INVALID_REPLY for r in scored),
        "not_sent": sum(r["status"] == NOT_SENT for r in scored),
        "model_error": sum(r["status"] == MODEL_ERROR for r in scored),
        "tp": sum(len(r["tp"]) for r in valid),
        "fp": sum(len(r["fp"]) for r in valid),
        "fn": sum(len(r["fn"]) for r in valid),
        "trials": scored,
    }


def score_suite(expected: dict[str, frozenset], atlas: dict, baseline: dict) -> dict:
    """`expected`, `atlas` and `baseline` are keyed by case ID (the cases in predeclared order).
    `clean` names the clean-control cases (empty expected set)."""
    a_rows = [score_atlas(cid, expected[cid], atlas[cid]) for cid in expected]
    b_rows = [score_baseline(cid, expected[cid], baseline[cid]) for cid in expected]
    clean = [cid for cid, ids in expected.items() if not ids]

    a_clean = [r for r in a_rows if r["case_id"] in clean and r["available"]]
    b_valid_clean = [
        t
        for r in b_rows
        if r["case_id"] in clean
        for t in r["trials"]
        if t["status"] == VALID
    ]
    b_trials = [t for r in b_rows for t in r["trials"]]
    b_valid = [t for t in b_trials if t["status"] == VALID]
    return {
        "atlas": {
            "cases": a_rows,
            "totals": {
                **_totals([r for r in a_rows if r["available"]]),
                "cases_available": sum(r["available"] for r in a_rows),
                "coverage_gaps_on_expected": sum(
                    len(r["expected_gaps"]) for r in a_rows
                ),
                "errors_on_expected": sum(len(r["expected_errors"]) for r in a_rows),
                "clean_false_positives": sum(len(r["fp"]) for r in a_clean),
                "clean_false_violation_rate": ratio(
                    sum(r["outcome"] == "VIOLATION_FOUND" for r in a_clean),
                    len(a_clean),
                ),
            },
        },
        "baseline": {
            "cases": b_rows,
            "totals": {
                **_totals(b_valid),
                "trials_scheduled": len(b_trials),
                "valid": len(b_valid),
                "invalid_reply": sum(t["status"] == INVALID_REPLY for t in b_trials),
                "not_sent": sum(t["status"] == NOT_SENT for t in b_trials),
                "model_error": sum(t["status"] == MODEL_ERROR for t in b_trials),
                "clean_false_positives": sum(len(t["fp"]) for t in b_valid_clean),
                "clean_false_violation_rate": ratio(
                    sum(bool(t["violated"]) for t in b_valid_clean), len(b_valid_clean)
                ),
            },
        },
    }
