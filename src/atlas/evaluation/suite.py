"""The T-11 comparison suite: legs (a) and (c), the run, and its records
(docs/EVALUATION.md; `atlas.cli evaluate --suite comparison`).

**Leg (a), ATLAS deterministic audit, through existing code only.**

- `s01_faulty`, `har_flawed`, `har_clean`: the hash-verified recorded runs in `demo/recorded/`
  (`RECORDED`). Each is used only if the recorded-run viewer's verification
  (`ui.recorded.verify`) finds every recorded hash and outcome intact, and the recorded original
  evaluated this project's current entry point (same bytes) and manifest (same content).
  Nothing is executed.
- `s02_clean` has no recorded run, so it is run exactly as T-09 ran its audits
  (`benchmarks/real_sensor/run_audit.py`): the agent loop with one fixture reply `finish`
  (NON-LIVE, no model) and T-09's `OriginalOnly` approver, so the unmodified original runs in
  the isolated Docker runner (`--network none`, non-root, read-only rootfs; no host fallback)
  and the trusted evaluator judges it. No new execution path.

A case whose ATLAS result cannot be obtained is reported unavailable, with its reason.

**Leg (c), metrics (descriptive only, never part of an outcome).** From the leg (a) run records:
the project's reported metric (if its manifest declares one), ATLAS's independently recomputed
primary metric, and for a flawed case its clean control's recomputed metric.

**Records** go to `<runs-dir>/<UTC time>/` (git-ignored `runs/t11/` by default): `suite.json`,
`atlas/<case>.json`, `baseline/<case>.json`, `replies/<case>/t<N>.txt` (untrusted),
`scores.json` and `results.md` (the development-case caveat first). Every scheduled trial is in
them. Cost totals are estimates at listed prices, not billing.
"""

import hashlib
import importlib.util
import json
import random
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from atlas.agent import money
from atlas.agent.client import FixtureClient
from atlas.contracts import Manifest
from atlas.evaluation import (
    CAVEAT,
    DEFINITIONS_PATH,
    EXPECTED_PATH,
    ROOT,
    Case,
    load_cases,
    load_definitions,
)
from atlas.evaluation import baseline as B
from atlas.evaluation.score import UNDEFINED, score_suite
from atlas.hosted import refuse_if_hosted
from atlas.policy import POLICY_VERSION
from atlas.ui import artifacts as A
from atlas.ui import recorded as RR

RECORDED_ROOT = ROOT / "demo" / "recorded"
RECORDED = {
    "s01_faulty": "live6/agent-s01_faulty-877f8245a8a2",
    "har_flawed": "t09/agent-har_flawed-1e2267f662c0",
    "har_clean": "t09/agent-har_clean-ac63eaecd7a8",
}
T09_AUDIT = ROOT / "benchmarks" / "real_sensor" / "run_audit.py"
SUITE = "comparison"


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _rows(outcome: dict) -> list[dict]:
    return [
        {
            "assertion_id": a.get("assertion_id"),
            "status": a.get("status"),
            "reason": a.get("reason"),
            "evidence_valid": a.get("evidence_valid", True),
        }
        for a in outcome.get("assertions") or []
    ]


def _unavailable(case: Case, source: str, reason: str) -> dict:
    return {"case_id": case.case_id, "leg": "a_atlas", "available": False,
            "source": source, "reason": reason}  # fmt: skip


def _result(case: Case, source: str, outcome: dict, evidence: dict) -> dict:
    return {
        "case_id": case.case_id,
        "leg": "a_atlas",
        "available": True,
        "source": source,
        "outcome": outcome.get("outcome"),
        "policy_version": outcome.get("policy_version"),
        "assertions": _rows(outcome),
        "incomplete_coverage": outcome.get("incomplete_coverage"),
        "evidence": evidence,
        "metrics": _metrics(outcome),
    }


def _metrics(outcome: dict) -> dict:
    primary = A.primary_metric(outcome)
    reported = A.reported_metric(outcome)
    return {
        "metric": primary.name if primary else None,
        "recomputed_mean_over_folds": primary.mean_over_folds if primary else None,
        "recomputed_pooled": primary.pooled if primary else None,
        "reported": [r["reported"] for r in reported] if reported else [],
    }


# -- leg (a) -------------------------------------------------------------------------------------
def recorded_atlas(case: Case, rel: str, root: Path = RECORDED_ROOT) -> dict:
    """A recorded run's original outcome, only after the viewer's verification passes and the
    recorded code and manifest equal the case's current ones. Nothing is executed."""
    source = f"recorded: demo/recorded/{rel}"
    run = Path(root) / rel
    report = A.read_json(run / "agent_report.json")
    if report is None:
        return _unavailable(case, source, "recorded_unavailable: no agent_report.json")
    checks = RR.verify(run, report)
    changed = [c.item for c in checks if not c.ok]
    if not checks or changed:
        return _unavailable(case, source, f"recorded_changed: {RR.CHANGED} "
                            f"({len(changed)} of {len(checks)} items)")  # fmt: skip
    stage = run / "original" / "exec" / "stage" / "project"
    try:
        entry = (stage / case.entry_point).read_bytes().replace(b"\r\n", b"\n")
        manifest = Manifest.model_validate_json(
            (stage / "atlas_manifest.json").read_bytes()
        )
    except (OSError, ValueError):
        return _unavailable(
            case, source, "recorded_unavailable: no recorded project files"
        )
    if entry != case.entry_text.encode("utf-8") or manifest.model_dump(
        mode="json"
    ) != case.manifest.model_dump(mode="json"):
        return _unavailable(case, source, "recorded_mismatch: the recorded run evaluated "
                            "other code or another manifest")  # fmt: skip
    outcome_path = run / "original" / "outcome.json"
    outcome = A.read_json(outcome_path) or {}
    evidence = {
        "run": f"demo/recorded/{rel}",
        "verified_items": len(checks),
        "intact": True,
        "outcome_sha256": _sha256(outcome_path),
        "recorded_finished_utc": A.run_finished_utc(report),
        "executed": "in the recorded run (Docker); not re-executed here",
    }
    return _result(case, source, outcome, evidence)


def _t09_audit_module():
    spec = importlib.util.spec_from_file_location("t09_run_audit", T09_AUDIT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def docker_atlas(case: Case, runs_dir: Path) -> dict:
    """The T-09 audit path, unchanged: one fixture `finish`, T-09's OriginalOnly approver, the
    original in Docker, the trusted evaluator's verdict on it."""
    from atlas.agent.controller import run_agent

    source = "re-run: the T-09 Docker audit path (benchmarks/real_sensor/run_audit.py)"
    t09 = _t09_audit_module()
    try:
        result = run_agent(
            case.path,
            runs_dir,
            FixtureClient("t11-atlas-finish", t09.FINISH),
            t09.OriginalOnly(),
            env={},
        )
    except Exception as exc:  # noqa: BLE001 - recorded as unavailable, never a result
        return _unavailable(case, source, f"run_failed: {type(exc).__name__}")
    original = result.original
    if original is None or not original.executed:
        return _unavailable(case, source, f"original_not_executed: {result.reason}")
    outcome_path = original.run_dir / "outcome.json"
    outcome = A.read_json(outcome_path) or {}
    evidence = {
        "run": str(result.run_dir),
        "runner": original.runner,
        "terminal_state": result.terminal_state,
        "outcome_sha256": _sha256(outcome_path),
        "executed": "here, in the isolated Docker runner",
    }
    return _result(case, source, outcome, evidence)


def atlas_leg(case: Case, runs_dir: Path) -> dict:
    rel = RECORDED.get(case.case_id)
    if rel is not None:
        return recorded_atlas(case, rel)
    return docker_atlas(case, runs_dir)


# -- leg (c) -------------------------------------------------------------------------------------
def metrics_leg(cases: list[Case], atlas: dict) -> list[dict]:
    rows = []
    for case in cases:
        own = (
            (atlas[case.case_id].get("metrics") or {})
            if atlas[case.case_id].get("available")
            else {}
        )
        control = {}
        if case.clean_control:
            other = atlas.get(case.clean_control) or {}
            control = (other.get("metrics") or {}) if other.get("available") else {}
        rows.append(
            {
                "case_id": case.case_id,
                "metric": own.get("metric"),
                "reported": own.get("reported", []),
                "recomputed_mean_over_folds": own.get("recomputed_mean_over_folds"),
                "recomputed_pooled": own.get("recomputed_pooled"),
                "clean_control": case.clean_control,
                "clean_control_recomputed_mean_over_folds": control.get(
                    "recomputed_mean_over_folds"
                ),
            }
        )
    return rows


# -- the run -------------------------------------------------------------------------------------
def load_fixture_script(path: Path) -> tuple[str, dict[str, list]]:
    """{"name": str, "cases": {case_id: [FixtureClient entries]}}; raises on any other shape."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    name, cases = data["name"], data["cases"]
    if not isinstance(name, str) or not isinstance(cases, dict):
        raise TypeError("fixture script must hold a name and cases")
    for cid, entries in cases.items():
        if not isinstance(entries, list):
            raise TypeError(f"fixture script entries for {cid} must be a list")
    return name, cases


def fixture_clients(name: str, cases: dict[str, list]):
    """A fresh FixtureClient per case run (the script for a case not listed is empty)."""
    return lambda case_id: FixtureClient(f"{name}-{case_id}", cases.get(case_id, []))


def case_order(case_ids, seed: int) -> list[str]:
    order = list(case_ids)
    random.Random(seed).shuffle(order)
    return order


def new_seed() -> int:
    return secrets.randbelow(2**32)


def run_suite(
    runs_root: Path,
    client_for,
    *,
    config,
    seed: int,
    live: bool,
    spend=None,
    preflight: dict | None = None,
    atlas_for=None,
    env=None,
) -> dict:
    """The whole suite: leg (a) for every case, then leg (b) case runs in seeded random order,
    then leg (c) and the scores. Returns the suite record; everything is written to disk.
    `atlas_for(case, runs_dir)` defaults to `atlas_leg`. Refused with ATLAS_HOSTED=1 before
    anything is read, written or run."""
    refuse_if_hosted("the T-11 comparison")
    if env is not None:
        refuse_if_hosted("the T-11 comparison", env)
    atlas_for = atlas_for or atlas_leg
    cases = load_cases()
    definitions = load_definitions()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = Path(runs_root) / stamp
    run_dir.mkdir(parents=True, exist_ok=False)
    by_id = {c.case_id: c for c in cases}
    order = case_order(by_id, seed)

    atlas = {}
    for case in cases:
        atlas[case.case_id] = atlas_for(case, run_dir / "atlas_runs")
        _write(run_dir / "atlas" / f"{case.case_id}.json", atlas[case.case_id])

    baseline = {}
    for case_id in order:
        record = B.run_case(
            by_id[case_id],
            client_for(case_id),
            run_dir,
            config=config,
            definitions=definitions,
            spend=spend,
            env=env,
        )
        baseline[case_id] = record.to_dict()
        _write(run_dir / "baseline" / f"{case_id}.json", baseline[case_id])

    expected = {c.case_id: c.expected for c in cases}
    scores = score_suite(
        expected, atlas, {cid: baseline[cid]["trials"] for cid in expected}
    )
    metrics = metrics_leg(cases, atlas)
    suite = {
        "suite": SUITE,
        "task": 'T-11 (re-scoped), DECISIONS.md "T-11 re-scope and T-10 (lead, 2026-10-19)"',
        "caveat": CAVEAT,
        "live": live,
        "model_id": config.model_id
        if live
        else "fixture (scripted replies; not model output)",
        "request_body": "model, messages, max_completion_tokens, n=1 (provider default sampling)",
        "max_completion_tokens": config.max_completion_tokens,
        "max_input_tokens": config.max_input_tokens,
        "seed": seed,
        "case_order": order,
        "repetitions": B.REPETITIONS,
        "max_requests_per_case": B.REQUESTS_PER_CASE,
        "policy_version": POLICY_VERSION,
        "system_prompt_sha256": hashlib.sha256(
            B.SYSTEM_PROMPT.encode("utf-8")
        ).hexdigest(),
        "inputs": {
            "expected.json": _sha256(EXPECTED_PATH),
            "assertion_definitions.json": _sha256(DEFINITIONS_PATH),
        },
        "expected": {cid: sorted(ids) for cid, ids in expected.items()},
        "input_estimates": {cid: baseline[cid]["input_estimate"] for cid in expected},
        "preflight": preflight,
        "spend": _spend_view(spend, baseline),
        "atlas_sources": {cid: atlas[cid]["source"] for cid in expected},
        "atlas_unavailable": [cid for cid in expected if not atlas[cid]["available"]],
        "metrics": metrics,
        "run_dir": str(run_dir),
    }
    _write(run_dir / "scores.json", scores)
    _write(run_dir / "suite.json", suite)
    (run_dir / "results.md").write_text(
        results_markdown(suite, scores, atlas, baseline), encoding="utf-8"
    )
    return suite


def _spend_view(spend, baseline: dict) -> dict:
    """Per case run figures from each ledger; totals are estimates, not billing."""
    per_case = {cid: (r.get("cost") or {}) for cid, r in baseline.items()}
    view = {
        "label": "estimates at listed prices from provider-reported usage; not billing",
        "per_case": {
            cid: c.get("estimated_total_usd", "not applicable (fixture)")
            for cid, c in per_case.items()
        },
    }
    if spend is not None:
        view["per_case_run_limits"] = {
            "authorized_usd": str(spend.authorized_usd),
            "estimate_cap_usd": str(spend.estimate_cap_usd),
        }
        totals = [c.get("estimated_total_usd") for c in per_case.values()]
        if all(isinstance(t, str) for t in totals):
            view["estimated_total_usd"] = money.text(
                money.total(Decimal(t) for t in totals)
            )
        else:
            view["estimated_total_usd"] = None
    return view


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n",
                    encoding="utf-8")  # fmt: skip


# -- the results table ---------------------------------------------------------------------------
def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if value == UNDEFINED:
        return UNDEFINED
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _ids(ids) -> str:
    return ", ".join(f"`{i}`" for i in ids) if ids else "none"


def results_markdown(suite: dict, scores: dict, atlas: dict, baseline: dict) -> str:
    mode = (
        f"LIVE, model `{suite['model_id']}`"
        if suite["live"]
        else "NON-LIVE fixture run: leg (b) replies are scripted, not model output"
    )
    lines = [
        "# T-11 three-way comparison (descriptive)",
        "",
        f"> **{CAVEAT}**",
        "",
        f"- Mode: {mode}.",
        f"- Seed {suite['seed']}; leg (b) case order: {', '.join(suite['case_order'])}.",
        (
            f"- Policy {suite['policy_version']}; {suite['repetitions']} repetitions per case, "
            f"at most {suite['max_requests_per_case']} requests per case run, no retries."
        ),
        "",
        "## Expected violated assertion IDs (predeclared, `evaluation/expected.json`)",
        "",
        "| Case | Expected |",
        "| --- | --- |",
    ]
    lines += [f"| {cid} | {_ids(ids)} |" for cid, ids in suite["expected"].items()]
    lines += [
        "",
        "## Leg (a): ATLAS deterministic audit",
        "",
        "| Case | Source | Outcome | TP | FP | FN | Coverage gaps (expected) | Errors |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in scores["atlas"]["cases"]:
        source = atlas[r["case_id"]]["source"]
        if not r["available"]:
            lines.append(f"| {r['case_id']} | {source} | unavailable: {r['reason']} "
                         "| | | | | |")  # fmt: skip
            continue
        lines.append(
            f"| {r['case_id']} | {source} | {r['outcome']} | {_ids(r['tp'])} | "
            f"{_ids(r['fp'])} | {_ids(r['fn'])} | {_ids(r['coverage_gaps'])} "
            f"({_ids(r['expected_gaps'])}) | {_ids(r['errors'])} |"
        )
    lines += [
        "",
        "## Leg (b): Nemotron alone (no executable checks)",
        "",
        "| Case | Input estimate | Trial | Status | Code | Violated | TP | FP | FN |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in scores["baseline"]["cases"]:
        estimate = baseline[r["case_id"]]["input_estimate"]
        for t in r["trials"]:
            scored = t["status"] == "VALID"
            lines.append(
                f"| {r['case_id']} | {estimate} | {t['repetition']} | {t['status']} | "
                f"{t['code'] or ''} | {_ids(t.get('violated')) if scored else ''} | "
                f"{len(t['tp']) if scored else ''} | {len(t['fp']) if scored else ''} | "
                f"{len(t['fn']) if scored else ''} |"
            )
    a, b = scores["atlas"]["totals"], scores["baseline"]["totals"]
    lines += [
        "",
        "## Totals",
        "",
        "| Leg | TP | FP | FN | Precision | Recall | Clean FP | Clean false-violation rate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| (a) ATLAS | {a['tp']} | {a['fp']} | {a['fn']} | {_fmt(a['precision'])} | "
            f"{_fmt(a['recall'])} | {a['clean_false_positives']} | "
            f"{_fmt(a['clean_false_violation_rate'])} |"
        ),
        (
            f"| (b) Nemotron alone, valid trials | {b['tp']} | {b['fp']} | {b['fn']} | "
            f"{_fmt(b['precision'])} | {_fmt(b['recall'])} | {b['clean_false_positives']} | "
            f"{_fmt(b['clean_false_violation_rate'])} |"
        ),
        "",
        (
            f"- Leg (a): {a['cases_available']} of {len(scores['atlas']['cases'])} cases "
            f"available; expected IDs left NOT_ASSESSED (coverage gaps, not misses): "
            f"{a['coverage_gaps_on_expected']}; on ERROR: {a['errors_on_expected']}."
        ),
        (
            f"- Leg (b): {b['trials_scheduled']} trials scheduled; {b['valid']} valid, "
            f"{b['invalid_reply']} INVALID_REPLY, {b['not_sent']} not sent, "
            f"{b['model_error']} model errors (none of these is scored)."
        ),
        "",
        "## Leg (c): reported against recomputed metric (descriptive, never an outcome)",
        "",
        (
            "| Case | Metric | Reported | Recomputed (mean over folds) | Recomputed (pooled) "
            "| Clean control | Clean control recomputed (mean over folds) |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for m in suite["metrics"]:
        reported = ", ".join(_fmt(v) for v in m["reported"]) or "none declared"
        lines.append(
            f"| {m['case_id']} | {m['metric'] or 'n/a'} | {reported} | "
            f"{_fmt(m['recomputed_mean_over_folds'])} | {_fmt(m['recomputed_pooled'])} | "
            f"{m['clean_control'] or ''} | "
            f"{_fmt(m['clean_control_recomputed_mean_over_folds']) if m['clean_control'] else ''} |"
        )
    spend = suite["spend"]
    lines += [
        "",
        "## Cost (estimates, not billing)",
        "",
        f"- {spend['label']}.",
        f"- Per case run: {json.dumps(spend['per_case'], sort_keys=True)}.",
    ]
    if "estimated_total_usd" in spend:
        lines.append(
            f"- Estimated total: {spend['estimated_total_usd']} USD (not billing)."
        )
    lines.append("")
    return "\n".join(lines)
