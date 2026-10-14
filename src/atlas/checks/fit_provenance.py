"""Fit provenance on the bounded supported path (SPEC §4.3, §5, F1). Trusted side.

Judges recorder events: fitted-state dependencies are checked against the training partition of
the fold where the state is used, and coverage requires an observed supported classifier fit and
a traceable prediction path for every evaluated fold. Unknown ancestry is NOT_ASSESSED, never an
invented FAIL.
"""

from atlas.contracts import AssertionResult, EvidenceRef, Reason, Status

SD = "fit.state_dependencies_within_fold_train"
CC = "fit.coverage_complete"


def fit_assertions(
    events: list[dict],
    splits: list[dict],
    evidence: list[EvidenceRef],
    evidence_valid: bool = True,
) -> dict[str, AssertionResult]:
    if not evidence_valid:
        return {
            aid: AssertionResult(
                assertion_id=aid,
                status=Status.ERROR,
                reason=Reason.EVIDENCE_INVALID,
                evidence=evidence,
                evidence_valid=False,
            )
            for aid in (SD, CC)
        }
    if not splits:
        return {
            aid: AssertionResult(
                assertion_id=aid,
                status=Status.NOT_ASSESSED,
                reason=Reason.NOT_EXECUTED,
                evidence=evidence,
            )
            for aid in (SD, CC)
        }
    classifier_fits = [
        e for e in events if e["type"] == "fit" and e["classifier"] and e["supported"]
    ]
    return {
        SD: _state_dependencies(events, splits, classifier_fits, evidence),
        CC: _coverage(events, splits, classifier_fits, evidence),
    }


def _state_dependencies(events, splits, classifier_fits, evidence) -> AssertionResult:
    train_of = {s["fold"]: set(s["train_ids"]) for s in splits}
    violations: dict[str, list] = {}
    unknown = []
    judged = 0
    for use in (e for e in events if e["type"] == "use"):
        if use["fold"] not in train_of:
            continue  # global-context uses are judged through the dependencies they propagate
        check_fold = use["fold"]  # the fold where the state is USED (F1)
        train = train_of.get(check_fold)
        if train is None:
            continue
        if use["effective_deps"] is None:
            unknown.append(
                {"fold": use["fold"], "class": use["class"], "method": use["method"]}
            )
            continue
        judged += 1
        outside = set(use["effective_deps"]) - train
        if outside:
            violations.setdefault(use["fold"], []).append(
                {
                    "instance": use["instance"],
                    "class": use["class"],
                    "method": use["method"],
                    "state_fit_fold": use["state_fit_fold"],
                    "rows_outside_train": len(outside),
                    "sample": sorted(outside)[:5],
                }
            )
    observed = {
        "judged_uses": judged,
        "unknown_uses": unknown,
        "violations": violations,
    }
    if violations:
        observed["violating_folds"] = sorted(violations)
        return AssertionResult(
            assertion_id=SD, status=Status.FAIL, observed=observed, evidence=evidence
        )
    if not classifier_fits:
        return AssertionResult(
            assertion_id=SD,
            status=Status.NOT_ASSESSED,
            reason=Reason.ZERO_FIT,
            observed=observed,
            evidence=evidence,
        )
    if unknown:
        return AssertionResult(
            assertion_id=SD,
            status=Status.NOT_ASSESSED,
            reason=Reason.UNKNOWN_ANCESTRY,
            observed=observed,
            evidence=evidence,
        )
    predicted_folds = {
        e["fold"] for e in events if e["type"] == "use" and e["method"] == "predict"
    }
    missing = sorted(set(train_of) - predicted_folds)
    if missing:
        observed["folds_without_observed_prediction"] = missing
        return AssertionResult(
            assertion_id=SD,
            status=Status.NOT_ASSESSED,
            reason=Reason.COVERAGE_GAP,
            observed=observed,
            evidence=evidence,
        )
    return AssertionResult(
        assertion_id=SD, status=Status.PASS, observed=observed, evidence=evidence
    )


def _coverage(events, splits, classifier_fits, evidence) -> AssertionResult:
    if not classifier_fits:
        return AssertionResult(
            assertion_id=CC,
            status=Status.NOT_ASSESSED,
            reason=Reason.ZERO_FIT,
            observed={"supported_classifier_fits": 0},
            evidence=evidence,
            limitations=["A fit count alone never establishes coverage."],
        )
    producer = {}
    for e in events:
        if e["type"] in ("load", "take") and e.get("token"):
            producer[e["token"]] = e
        elif e["type"] == "use" and e.get("output_token"):
            producer[e["output_token"]] = e
    fit_of_state = {
        (e["instance"], e["version"]): e for e in events if e["type"] == "fit"
    }
    predictions = {e["fold"]: e for e in events if e["type"] == "predictions"}

    gaps: dict[str, list[str]] = {}
    for s in splits:
        fold = s["fold"]
        found = _fold_gaps(predictions.get(fold), producer, fit_of_state)
        if found:
            gaps[fold] = found
    observed = {
        "supported_classifier_fits": len(classifier_fits),
        "gaps": gaps,
        "folds": len(splits),
    }
    limitations = [
        "Coverage is limited to the bounded supported path; the in-process recorder is not tamper-proof.",
        "Provenance begins at the supplied feature table.",
    ]
    if gaps:
        return AssertionResult(
            assertion_id=CC,
            status=Status.NOT_ASSESSED,
            reason=Reason.COVERAGE_GAP,
            observed=observed,
            evidence=evidence,
            limitations=limitations,
        )
    return AssertionResult(
        assertion_id=CC,
        status=Status.PASS,
        observed=observed,
        evidence=evidence,
        limitations=limitations,
    )


def _fold_gaps(pred, producer, fit_of_state) -> list[str]:
    if pred is None:
        return ["no predictions written"]
    if pred["pred_status"] != "tracked" or not pred["rows_match"]:
        return [f"missing prediction ancestry ({pred['pred_status']})"]
    use = producer.get(pred["pred_token"])
    if use is None or use["type"] != "use" or use["method"] != "predict":
        return ["predictions do not come from a recorded predict"]
    fit = fit_of_state.get((use["instance"], use["version"]))
    if fit is None or not fit["classifier"] or not fit["supported"]:
        return ["predictions do not come from an observed supported classifier fit"]
    gaps: list[str] = []
    _walk(use, producer, fit_of_state, gaps, set())
    return gaps


def _walk(event, producer, fit_of_state, gaps, seen) -> None:
    """Follow the ancestry of data and fitted states back to the adapter load; collect gaps."""
    key = id(event)
    if key in seen:
        return
    seen.add(key)
    kind = event["type"]
    if kind == "load":
        return
    if event.get("input_status") != "tracked":
        gaps.append(
            f"{kind} {event.get('class', '')} {event.get('method', '')} input {event.get('input_status')}".strip()
        )
        return
    upstream = producer.get(event["input_token"])
    if upstream is None:
        gaps.append(f"{kind} input has no recorded producer")
    else:
        _walk(upstream, producer, fit_of_state, gaps, seen)
    if kind == "use":
        if not event["input_known"]:
            gaps.append(
                f"use {event['class']}.{event['method']} input ancestry unknown"
            )
        fit = fit_of_state.get((event["instance"], event["version"]))
        if fit is None:
            gaps.append(f"use {event['class']}.{event['method']} has no recorded fit")
            return
        if fit["deps"] is None:
            gaps.append(
                f"fit {fit['class']} dependencies unknown ({fit['input_status']})"
            )
        _walk(fit, producer, fit_of_state, gaps, seen)
    elif kind == "fit" and event.get("labels_token"):
        labels = producer.get(event["labels_token"])
        if labels is None:
            gaps.append(f"fit {event['class']} labels have no recorded producer")
        else:
            _walk(labels, producer, fit_of_state, gaps, seen)
