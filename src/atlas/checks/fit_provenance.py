"""Fit provenance on the bounded supported path (SPEC §4.3, §5, F1). Trusted side.

Judges recorder events: fitted-state dependencies are checked against the training partition of
the fold where the state is used, and coverage requires, for every declared fold, a written
prediction bound to its actual recorded producer (same fold, same rows, supported classifier
state, matching artifact hash) with a fully traced ancestry. Unknown ancestry is NOT_ASSESSED,
never an invented FAIL.

Fold inventories in splits.json, provenance split events, prediction events and use events must
agree. Limit: consistency cannot prove the existence of a fold erased from every source; that
needs an independent expected-fold contract (not part of T-01).
"""

from atlas.contracts import AssertionResult, EvidenceRef, Reason, Status
from atlas.reports import ids_sha256

SD = "fit.state_dependencies_within_fold_train"
CC = "fit.coverage_complete"


def fit_assertions(
    events: list[dict],
    splits: list[dict],
    evidence: list[EvidenceRef],
    evidence_valid: bool = True,
    *,
    artifacts: dict[str, str],
) -> dict[str, AssertionResult]:
    """`artifacts`: verified evidence files (name -> sha256) from the run index."""
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
    graph = _Graph(events)
    inventory = _fold_inventory(events, splits)
    return {
        SD: _state_dependencies(
            events, splits, classifier_fits, graph, inventory, evidence
        ),
        CC: _coverage(
            events, splits, classifier_fits, graph, inventory, artifacts, evidence
        ),
    }


class _Graph:
    """Recorded lineage: data token -> producing event; (instance, version) -> fit event."""

    def __init__(self, events: list[dict]):
        self.producer = {}
        for e in events:
            if e["type"] in ("load", "take") and e.get("token"):
                self.producer[e["token"]] = e
            elif e["type"] == "use" and e.get("output_token"):
                self.producer[e["output_token"]] = e
        self.fit_of_state = {
            (e["instance"], e["version"]): e for e in events if e["type"] == "fit"
        }

    def upstream_fits(self, use: dict) -> list[dict]:
        """Fit events on the recorded ancestry of a use: its own state and all upstream states."""
        found, seen, stack = {}, set(), [use]
        while stack:
            event = stack.pop()
            if id(event) in seen:
                continue
            seen.add(id(event))
            if event["type"] == "use":
                fit = self.fit_of_state.get((event["instance"], event["version"]))
                if fit is not None:
                    found[(fit["instance"], fit["version"])] = fit
                    stack.append(fit)
            token = event.get("input_token")
            if token and token in self.producer:
                stack.append(self.producer[token])
        return list(found.values())


def _fold_inventory(events: list[dict], splits: list[dict]) -> dict:
    """Reconcile declared folds across splits.json and provenance; report every inconsistency."""
    declared = [s["fold"] for s in splits]
    declared_set = set(declared)
    split_events = {e["fold"]: e for e in events if e["type"] == "split"}
    issues: list[str] = []
    if len(declared) != len(declared_set):
        issues.append("splits.json declares a fold more than once")
    for fold in sorted(declared_set - set(split_events)):
        issues.append(
            f"fold {fold} is in splits.json but has no provenance split event"
        )
    for fold in sorted(set(split_events) - declared_set):
        issues.append(
            f"fold {fold} has a provenance split event but is missing from splits.json"
        )
    for s in splits:
        e = split_events.get(s["fold"])
        if e is not None and (
            e["train_sha256"] != ids_sha256(s["train_ids"])
            or e["eval_sha256"] != ids_sha256(s["eval_ids"])
        ):
            issues.append(
                f"fold {s['fold']} partitions differ between splits.json and provenance"
            )
    pred_folds = [e["fold"] for e in events if e["type"] == "predictions"]
    for fold in sorted(set(pred_folds) - declared_set):
        issues.append(f"predictions were written for undeclared fold {fold}")
    for fold in sorted({f for f in pred_folds if pred_folds.count(f) > 1}):
        issues.append(f"predictions were written more than once for fold {fold}")
    orphan_uses = sorted(
        {e["fold"] for e in events if e["type"] == "use"} - declared_set - {"global"}
    )
    for fold in orphan_uses:
        issues.append(f"fitted states were used in undeclared fold {fold}")
    return {"issues": issues, "orphan_use_folds": orphan_uses}


def _state_dependencies(
    events, splits, classifier_fits, graph: _Graph, inventory: dict, evidence
) -> AssertionResult:
    train_of = {s["fold"]: set(s["train_ids"]) for s in splits}
    violations: dict[str, list] = {}
    origins: dict[tuple, dict] = {}
    unknown = []
    judged = 0
    for use in (e for e in events if e["type"] == "use"):
        if use["fold"] not in train_of:
            continue  # global uses are judged through what they propagate; orphans are gaps
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
        if not outside:
            continue
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
        _record_origins(origins, graph.upstream_fits(use), use, train)
    observed = {
        "judged_uses": judged,
        "unknown_uses": unknown,
        "violations": violations,
        "fold_inventory_issues": inventory["issues"],
    }
    if violations:
        observed["violating_folds"] = sorted(violations)
        observed["origins"] = sorted(
            origins.values(), key=lambda o: (o["fit_scope"], o["instance"])
        )
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
    if missing or inventory["orphan_use_folds"]:
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


def _record_origins(origins: dict, fits: list[dict], use: dict, train: set) -> None:
    """Fitted states on the use's recorded ancestry whose own fit rows fall outside the fold's train."""
    for fit in fits:
        if fit["rows"] is None:
            continue
        outside = set(fit["rows"]) - train
        if not outside:
            continue
        key = (fit["instance"], fit["version"])
        origin = origins.setdefault(
            key,
            {
                "instance": fit["instance"],
                "version": fit["version"],
                "class": fit["class"],
                "fit_scope": fit["fold"],
                "contributing_rows": len(fit["rows"]),
                "labels_supplied": fit["labels_supplied"],
                "labels_used": fit["labels_used"],
                "affected_folds": [],
                "rows_outside_train_by_fold": {},
                "affected_uses": [],
            },
        )
        if use["fold"] not in origin["affected_folds"]:
            origin["affected_folds"].append(use["fold"])
        origin["rows_outside_train_by_fold"][use["fold"]] = len(outside)
        mention = f"{use['fold']}:{use['class']}.{use['method']}"
        if mention not in origin["affected_uses"]:
            origin["affected_uses"].append(mention)


def _coverage(
    events, splits, classifier_fits, graph: _Graph, inventory: dict, artifacts, evidence
) -> AssertionResult:
    limitations = [
        "Coverage is limited to the bounded supported path; the in-process recorder is not tamper-proof.",
        "Provenance begins at the supplied feature table.",
        "Fold consistency cannot prove the existence of a fold erased from every source.",
    ]
    if not classifier_fits:
        return AssertionResult(
            assertion_id=CC,
            status=Status.NOT_ASSESSED,
            reason=Reason.ZERO_FIT,
            observed={"supported_classifier_fits": 0},
            evidence=evidence,
            limitations=["A fit count alone never establishes coverage.", *limitations],
        )
    predictions: dict[str, list[dict]] = {}
    for e in events:
        if e["type"] == "predictions":
            predictions.setdefault(e["fold"], []).append(e)

    gaps: dict[str, list[str]] = {}
    for s in splits:
        found = _fold_gaps(s, predictions.get(s["fold"], []), graph, artifacts)
        if found:
            gaps[s["fold"]] = found
    if inventory["issues"]:
        gaps["fold_inventory"] = inventory["issues"]
    observed = {
        "supported_classifier_fits": len(classifier_fits),
        "gaps": gaps,
        "folds": len(splits),
    }
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


def _fold_gaps(
    split: dict, preds: list[dict], graph: _Graph, artifacts: dict
) -> list[str]:
    """Bind the fold's written predictions to their actual producer, state, rows and artifact."""
    fold = split["fold"]
    if not preds:
        return ["no predictions written"]
    if len(preds) > 1:
        return ["more than one prediction event for this fold"]
    pred = preds[0]
    if pred.get("artifact") != f"predictions/{fold}.parquet":
        return ["prediction event names an artifact other than this fold's own"]
    if pred["pred_status"] != "tracked":
        return [f"missing prediction ancestry ({pred['pred_status']})"]
    if pred.get("artifact") not in artifacts or artifacts[pred["artifact"]] != pred.get(
        "artifact_sha256"
    ):
        return ["prediction event does not match a verified prediction artifact"]
    use = graph.producer.get(pred["pred_token"])
    if use is None or use["type"] != "use" or use["method"] != "predict":
        return ["predictions do not come from a recorded predict"]
    if use["fold"] != fold:
        return [f"predictions were produced in fold {use['fold']}, not {fold}"]
    if use["rows"] != pred["rows"]:
        return ["written row IDs differ from the rows the producer predicted"]
    fit = graph.fit_of_state.get((use["instance"], use["version"]))
    if fit is None or not fit["classifier"] or not fit["supported"]:
        return ["predictions do not come from an observed supported classifier fit"]
    gaps: list[str] = []
    _walk(use, graph, gaps, set())
    return gaps


def _walk(event, graph: _Graph, gaps, seen) -> None:
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
    upstream = graph.producer.get(event["input_token"])
    if upstream is None:
        gaps.append(f"{kind} input has no recorded producer")
    else:
        _walk(upstream, graph, gaps, seen)
    if kind == "use":
        if not event["input_known"]:
            gaps.append(
                f"use {event['class']}.{event['method']} input ancestry unknown"
            )
        fit = graph.fit_of_state.get((event["instance"], event["version"]))
        if fit is None:
            gaps.append(f"use {event['class']}.{event['method']} has no recorded fit")
            return
        if fit["deps"] is None:
            gaps.append(
                f"fit {fit['class']} dependencies unknown ({fit['input_status']})"
            )
        _walk(fit, graph, gaps, seen)
    elif kind == "fit" and event.get("labels_token"):
        labels = graph.producer.get(event["labels_token"])
        if labels is None:
            gaps.append(f"fit {event['class']} labels have no recorded producer")
        else:
            _walk(labels, graph, gaps, seen)
