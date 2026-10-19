"""T-11 comparison (re-scoped): predeclared inputs, leg (a) from recorded runs, the CLI's
refusals, the live path over mocks, and a full fixture run with s02_clean in Docker.

    $env:ATLAS_MODEL_MODE='fixture'; $env:ATLAS_REQUIRE_DOCKER='1'
    uv run --locked pytest tests/integration/test_t11_comparison.py -q -p no:cacheprovider

No request leaves the process and the repository `.env` is never read: the live path runs
against `httpx2.MockTransport` with a synthetic key file. With ATLAS_REQUIRE_DOCKER=1 an
unavailable runner fails the Docker test instead of skipping it.
"""

import functools
import importlib.util
import json
import os
import re
import shutil
from pathlib import Path

import httpx2
import pytest

from atlas import cli
from atlas.agent import nebius, preflight
from atlas.agent.network import deny_network
from atlas.contracts import Status
from atlas.evaluation import (
    CASE_IDS,
    CAVEAT,
    DEFINITIONS_PATH,
    ROOT,
    load_cases,
    load_definitions,
    load_expected,
    suite,
)
from atlas.evaluation import baseline as B
from atlas.policy import IMPLEMENTED
from atlas.runner import docker as dr

SCRIPT = ROOT / "tests" / "fixtures" / "t11_comparison_script.json"
REQUIRE_DOCKER = os.environ.get("ATLAS_REQUIRE_DOCKER") == "1"
CASES = {c.case_id: c for c in load_cases()}
KEY = "sk-test-SECRET-t11-cli-0123456789"
LISTING = json.loads(
    (ROOT / "tests" / "fixtures" / "nebius_models_verbose.json").read_text(
        encoding="utf-8"
    )
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# =============================================================================================
# The predeclared inputs
# =============================================================================================


def _spec_definitions() -> dict[str, str]:
    text = (ROOT / "docs" / "SPEC.md").read_text(encoding="utf-8")
    section = text.split("## 5 Checks and the evaluation policy", 1)[1].split(
        "\n## 6 "
    )[0]
    rows = {}
    for line in section.splitlines():
        m = re.match(r"^\| `([a-z_.]+)` \|(.*)\|\s*$", line)
        if m:
            rows[m.group(1)] = [c.strip() for c in m.group(2).split(" | ")][-1]
    return rows


def test_the_definitions_are_the_policy_table_verbatim():
    definitions = load_definitions(DEFINITIONS_PATH)
    assert set(definitions) == set(IMPLEMENTED)
    spec = _spec_definitions()
    for aid, text in definitions.items():
        assert text == spec[aid], aid


def test_expected_sets_are_sourced_canonical_and_fixed():
    data = load_expected()
    assert tuple(data["cases"]) == CASE_IDS
    for cid, entry in data["cases"].items():
        case = CASES[cid]
        assert (ROOT / entry["path"]).is_dir()
        ids = [e["assertion_id"] for e in entry["expected_violated"]]
        assert set(ids) <= set(case.canonical) and len(ids) == len(set(ids))
        sources = [s for e in entry["expected_violated"] for s in e["sources"]]
        sources += entry["empty_set_sources"]
        assert sources, cid
        for source in sources:
            assert (ROOT / source.split(",")[0]).is_file(), source
    assert {c: sorted(CASES[c].expected) for c in CASE_IDS} == {
        "s01_faulty": [
            "fit.state_dependencies_within_fold_train",
            "split.no_group_overlap",
            "split.repeated_measures_rule",
            "split.sampling_unit_disjoint",
        ],
        "s02_clean": [],
        "har_flawed": [
            "fit.state_dependencies_within_fold_train",
            "split.no_group_overlap",
            "split.no_window_overlap",
            "split.repeated_measures_rule",
            "split.sampling_unit_disjoint",
        ],
        "har_clean": [],
    }


def test_the_synthetic_expected_sets_equal_the_t01_scenario_table():
    t01 = _load(ROOT / "tests" / "integration" / "test_t01_scenarios.py", "t01_table")
    for cid in ("s01_faulty", "s02_clean"):
        row, others, _ = t01.EXPECTED[cid]
        fails = {a for a, s in zip(t01.COLUMNS, row, strict=True) if s is Status.FAIL}
        fails |= {a for a, s in others.items() if s is Status.FAIL}
        assert fails == CASES[cid].expected, cid


def test_the_har_expected_sets_contain_the_t09_fail_list():
    text = (ROOT / "docs" / "T09_CONTAINMENT.md").read_text(encoding="utf-8")
    flawed = text.split("### `har_flawed`", 1)[1].split("- **NOT_ASSESSED:**")[0]
    fails = set(re.findall(r"`((?:split|fit|metric)\.[a-z_]+)`", flawed))
    assert fails and fails <= CASES["har_flawed"].expected
    # the one addition is violated by design and recorded NOT_ASSESSED by ATLAS
    assert CASES["har_flawed"].expected - fails == {"split.no_window_overlap"}


def test_the_system_prompt_is_the_predeclared_one():
    text = (ROOT / "docs" / "EVALUATION.md").read_text(encoding="utf-8")
    block = text.split("### System prompt (verbatim)", 1)[1].split("```text\n", 1)[1]
    assert block.split("\n```", 1)[0] == B.SYSTEM_PROMPT


# =============================================================================================
# Leg (a) from the recorded runs (nothing executes)
# =============================================================================================


@pytest.mark.parametrize("cid", sorted(suite.RECORDED))
def test_recorded_runs_are_verified_and_used(cid):
    result = suite.recorded_atlas(CASES[cid], suite.RECORDED[cid])
    assert result["available"] is True and result["evidence"]["intact"] is True
    ids = [a["assertion_id"] for a in result["assertions"]]
    assert ids == list(CASES[cid].canonical)
    fails = {a["assertion_id"] for a in result["assertions"] if a["status"] == "FAIL"}
    gaps = {
        a["assertion_id"] for a in result["assertions"] if a["status"] == "NOT_ASSESSED"
    }
    assert fails | gaps == CASES[cid].expected


def test_a_tampered_recorded_run_is_not_used(tmp_path):
    rel = suite.RECORDED["har_clean"]
    shutil.copytree(suite.RECORDED_ROOT / rel, tmp_path / rel)
    outcome = tmp_path / rel / "original" / "outcome.json"
    outcome.write_bytes(
        outcome.read_bytes().replace(b"NO_VIOLATION_FOUND", b"VIOLATION_FOUND")
    )
    result = suite.recorded_atlas(CASES["har_clean"], rel, root=tmp_path)
    assert result["available"] is False
    assert result["reason"].startswith("recorded_changed")


def test_a_recorded_run_of_other_code_is_not_used():
    result = suite.recorded_atlas(CASES["s02_clean"], suite.RECORDED["s01_faulty"])
    assert result["available"] is False and result["reason"].startswith(
        "recorded_mismatch"
    )


# =============================================================================================
# CLI refusals: exit 2, nothing run, no run directory
# =============================================================================================


class Tripwire(Exception):
    pass


def tripwire(name):
    def trip(*args, **kwargs):
        raise Tripwire(f"{name} was reached")

    return trip


@pytest.fixture
def no_side_effects(monkeypatch):
    monkeypatch.setattr(suite, "run_suite", tripwire("run_suite"))
    monkeypatch.setattr(nebius, "load_api_key", tripwire("key read"))
    monkeypatch.setattr(nebius, "NebiusClient", tripwire("client built"))
    monkeypatch.setattr(preflight, "run_preflight", tripwire("pre-run check"))
    monkeypatch.setattr(dr, "probe", tripwire("Docker probe"))
    monkeypatch.setattr(dr, "_docker", tripwire("Docker CLI"))


def evaluate(tmp_path, *argv):
    with deny_network():
        return cli.main(
            ["evaluate", "--suite", "comparison", "--runs-dir", str(tmp_path / "runs"),
             *argv]
        )  # fmt: skip


LIVE = ["--live", "--authorize-spend-usd", "0.51"]


@pytest.mark.parametrize(
    ("argv", "mode", "message"),
    [
        ([], "fixture", "needs --fixture-script"),
        ([], "live", "needs --fixture-script"),
        (["--live"], "live", "must equal the decided authorization"),
        (["--live", "--authorize-spend-usd", "0.50"], "live", "given: '0.50'"),
        (["--live", "--authorize-spend-usd", "NaN"], "live", "decided authorization"),
        (LIVE, "fixture", "--live needs ATLAS_MODEL_MODE=live"),
        ([*LIVE, "--fixture-script", str(SCRIPT)], "live", "cannot be combined"),
        (["--authorize-spend-usd", "0.51", "--fixture-script", str(SCRIPT)], "fixture",
         "applies only with --live"),
        (["--fixture-script", str(SCRIPT)], "live", "without --live"),
        (["--fixture-script", str(SCRIPT), "--seed", "-1"], "fixture", "--seed"),
    ],
)  # fmt: skip
def test_refusals_run_nothing(tmp_path, monkeypatch, capsys, no_side_effects, argv,
                              mode, message):  # fmt: skip
    monkeypatch.setenv("ATLAS_MODEL_MODE", mode)
    assert evaluate(tmp_path, *argv) == cli.REFUSED_EXIT
    err = capsys.readouterr().err
    assert message in err and "Nothing was run." in err
    assert not (tmp_path / "runs").exists()


def test_the_live_refusal_order_matches_the_agent_path(tmp_path, monkeypatch, capsys,
                                                       no_side_effects):  # fmt: skip
    # mode before amount, as in `audit --mode agent --live`
    monkeypatch.setenv("ATLAS_MODEL_MODE", "fixture")
    assert evaluate(tmp_path, "--live") == cli.REFUSED_EXIT
    assert "--live needs ATLAS_MODEL_MODE=live" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [["--fixture-script", str(SCRIPT)], LIVE, []])
def test_the_hosted_refusal_covers_evaluate(tmp_path, monkeypatch, capsys,
                                            no_side_effects, argv):  # fmt: skip
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    monkeypatch.setenv("ATLAS_MODEL_MODE", "live" if argv == LIVE else "fixture")
    assert evaluate(tmp_path, *argv) == cli.REFUSED_EXIT
    assert cli.HOSTED_REFUSAL in capsys.readouterr().err
    assert not (tmp_path / "runs").exists()


def test_the_harness_itself_refuses_when_hosted(tmp_path, monkeypatch):
    """Not only the CLI: the suite and a case run refuse before anything is read or run."""
    from atlas.agent.client import FixtureClient
    from atlas.hosted import HostedExecutionRefused

    client = FixtureClient("t", [])
    monkeypatch.setattr(dr, "_docker", tripwire("Docker CLI"))
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    with pytest.raises(HostedExecutionRefused):
        suite.run_suite(tmp_path / "runs", lambda cid: client,
                        config=cli._decided_config(), seed=1, live=False)  # fmt: skip
    with pytest.raises(HostedExecutionRefused):
        B.run_case(CASES["s01_faulty"], client, tmp_path / "case",
                   config=cli._decided_config(), definitions=load_definitions())  # fmt: skip
    assert client.requests == []
    assert not (tmp_path / "runs").exists() and not (tmp_path / "case").exists()


def test_an_unusable_fixture_script_is_refused(tmp_path, monkeypatch, no_side_effects):
    bad = tmp_path / "bad.json"
    bad.write_text('{"name": "x", "cases": []}', encoding="utf-8")
    monkeypatch.setenv("ATLAS_MODEL_MODE", "fixture")
    assert evaluate(tmp_path, "--fixture-script", str(bad)) == cli.REFUSED_EXIT


# =============================================================================================
# The live path over a mocked provider (synthetic key file; no network)
# =============================================================================================


def completion(content):
    return {
        "id": "cmpl-1", "object": "chat.completion", "created": 0,
        "model": "nvidia/nemotron-3-super-120b-a12b",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 3000, "completion_tokens": 300, "total_tokens": 3300},
    }  # fmt: skip


class Provider:
    def __init__(self, completions):
        self.completions, self.requests = list(completions), []

    def __call__(self, request):
        self.requests.append(request)
        if request.method == "GET":
            return httpx2.Response(200, json=LISTING, headers={"x-request-id": "pf-1"})
        return httpx2.Response(200, json=self.completions.pop(0),
                               headers={"x-request-id": f"req-{len(self.requests)}"})  # fmt: skip


def stub_atlas(case, runs_dir):
    """Leg (a) without Docker: recorded runs, and s02_clean reported unavailable."""
    if case.case_id in suite.RECORDED:
        return suite.recorded_atlas(case, suite.RECORDED[case.case_id])
    return suite._unavailable(case, "stub", "not run in this test")


@pytest.fixture
def mocked_live(tmp_path, monkeypatch):
    env = tmp_path / "synthetic.env"
    env.write_text(f"NEBIUS_API_KEY={KEY}\n", encoding="utf-8")
    monkeypatch.setattr(cli, "LIVE_ENV_FILE", env)
    monkeypatch.setattr(suite, "atlas_leg", stub_atlas)
    monkeypatch.setenv("ATLAS_MODEL_MODE", "live")
    good = json.dumps({"violated": ["split.no_group_overlap"], "rationale": "r"})
    provider = Provider([completion(good)] * 6)
    http = httpx2.Client(transport=httpx2.MockTransport(provider))
    real_preflight, real_client = preflight.run_preflight, nebius.NebiusClient
    monkeypatch.setattr(
        preflight, "run_preflight", functools.partial(real_preflight, http_client=http)
    )
    monkeypatch.setattr(
        nebius,
        "NebiusClient",
        lambda config, key: real_client(config, key, http_client=http),
    )
    return provider


def test_the_live_path_end_to_end_over_mocks(tmp_path, mocked_live, capsys):
    code = evaluate(tmp_path, *LIVE, "--seed", "3")
    assert code == 1  # s02_clean's ATLAS result is stubbed unavailable here
    gets = [r for r in mocked_live.requests if r.method == "GET"]
    posts = [r for r in mocked_live.requests if r.method == "POST"]
    assert len(gets) == 1 and len(posts) == 6  # two HAR cases refused before sending
    for request in posts:
        body = json.loads(request.content)
        assert set(body) == {"model", "messages", "max_completion_tokens", "n"}
        assert (body["max_completion_tokens"], body["n"]) == (8000, 1)
    (run_dir,) = (tmp_path / "runs").iterdir()
    record = json.loads((run_dir / "suite.json").read_text(encoding="utf-8"))
    assert record["live"] is True and record["seed"] == 3
    assert record["preflight"]["result"] == "pass"
    assert set(record["spend"]["per_case"]) == set(CASE_IDS)
    for cid in ("har_flawed", "har_clean"):
        trials = json.loads((run_dir / "baseline" / f"{cid}.json").read_text())[
            "trials"
        ]
        assert {t["code"] for t in trials} == {"input_over_ceiling"}
    for path in run_dir.rglob("*"):
        if path.is_file():
            assert KEY.encode() not in path.read_bytes(), path


def test_a_failed_preflight_sends_no_completion(tmp_path, monkeypatch, mocked_live):
    listing = json.loads(json.dumps(LISTING))
    listing["data"] = [m for m in listing["data"] if "nemotron-3-super" not in m["id"]]
    monkeypatch.setattr(mocked_live, "completions", [])
    monkeypatch.setitem(globals(), "LISTING", listing)
    assert evaluate(tmp_path, *LIVE) == cli.PREFLIGHT_ABORT_EXIT
    assert [r.method for r in mocked_live.requests] == ["GET"]
    assert list((tmp_path / "runs").glob("preflight-*.json"))


# =============================================================================================
# A full fixture run, s02_clean audited in Docker (the T-09 path)
# =============================================================================================


@pytest.fixture(scope="module")
def isolation():
    cap = dr.probe()
    if cap.state != dr.CAPABILITY_AVAILABLE:
        message = f"isolated runner unavailable: {cap.reason}"
        if REQUIRE_DOCKER:
            pytest.fail(message)
        pytest.skip(message)
    return cap


def test_the_full_fixture_run_end_to_end(tmp_path, monkeypatch, capsys, isolation):
    monkeypatch.setenv("ATLAS_MODEL_MODE", "fixture")
    assert evaluate(tmp_path, "--fixture-script", str(SCRIPT), "--seed", "7") == 0
    (run_dir,) = (tmp_path / "runs").iterdir()
    record = json.loads((run_dir / "suite.json").read_text(encoding="utf-8"))
    scores = json.loads((run_dir / "scores.json").read_text(encoding="utf-8"))
    results = (run_dir / "results.md").read_text(encoding="utf-8")

    assert results.splitlines()[2] == f"> **{CAVEAT}**"
    assert "NON-LIVE fixture run" in results
    assert record["case_order"] == suite.case_order(CASE_IDS, 7)
    assert record["atlas_unavailable"] == []

    # leg (a): three recorded runs, s02_clean executed here in Docker
    s02 = json.loads((run_dir / "atlas" / "s02_clean.json").read_text(encoding="utf-8"))
    assert (
        s02["source"].startswith("re-run")
        and s02["evidence"]["runner"] == "docker_isolated"
    )
    assert s02["outcome"] == "NO_VIOLATION_FOUND"
    a = scores["atlas"]["totals"]
    assert (a["tp"], a["fp"], a["fn"]) == (8, 0, 0)
    assert a["coverage_gaps_on_expected"] == 1  # har_flawed's window assertion
    assert (a["precision"], a["recall"], a["clean_false_violation_rate"]) == (
        1.0,
        1.0,
        0.0,
    )

    # leg (b): every scheduled trial is reported, the HAR cases refused before sending
    b = scores["baseline"]["totals"]
    assert (b["trials_scheduled"], b["valid"], b["invalid_reply"], b["not_sent"]) == (
        12, 4, 2, 6)  # fmt: skip
    assert (b["tp"], b["fp"], b["fn"]) == (5, 2, 3)
    assert b["clean_false_violation_rate"] == 0.5
    codes = {(r["case_id"], t["repetition"]): t["code"]
             for r in scores["baseline"]["cases"] for t in r["trials"]}  # fmt: skip
    assert codes[("s01_faulty", 3)] == "not_json"
    assert codes[("s02_clean", 3)] == "duplicate_key"
    assert {codes[(c, r)] for c in ("har_flawed", "har_clean") for r in (1, 2, 3)} == {
        "input_over_ceiling"
    }
    assert (run_dir / "replies" / "s01_faulty" / "t3.txt").read_text().startswith("```")

    # leg (c): descriptive metrics from the run records
    metrics = {m["case_id"]: m for m in record["metrics"]}
    assert metrics["har_flawed"]["reported"] == [0.906396437268804]
    assert metrics["har_flawed"]["recomputed_mean_over_folds"] == pytest.approx(
        0.906396437268804
    )
    assert metrics["har_flawed"][
        "clean_control_recomputed_mean_over_folds"
    ] == pytest.approx(0.875188, abs=1e-6)
    assert metrics["s01_faulty"]["reported"] == []
    assert metrics["s01_faulty"]["clean_control_recomputed_mean_over_folds"] is not None
