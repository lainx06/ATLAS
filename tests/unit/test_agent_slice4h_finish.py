"""T-06 slice 4h, offline: finish-after-success guidance.

Live run 6 (`runs/live6/agent-s01_faulty-877f8245a8a2/`) was the first complete live loop:
revision 1 was approved, executed in Docker and judged NO_VIOLATION_FOUND, but the model then
proposed a second revision (rejected by `validate_diff`, `syntax_error`) and the run ended
BUDGET_EXHAUSTED on the 2-revision limit instead of finishing.

Here a candidate the trusted evaluator judged NO_VIOLATION_FOUND gets one fixed line in its
evaluate_candidate result, and the system prompt says to finish after such a candidate. It is
guidance only: no other result carries it, and the model still chooses the next action.

Fixture replies; scripted executors stand in for the runner (the Docker replay is in
tests/integration/test_agent_fixture_docker.py).
"""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from atlas.agent import controller as ctl
from atlas.agent.client import FixtureClient
from atlas.contracts import Outcome, RunOutcome


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name.removesuffix(".py"), Path(__file__).with_name(name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _load("test_agent_slice3.py")
S01 = S.S01
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
FINISH = S.FINISH
LINE = (
    "The trusted evaluator found no violation for this candidate. Call finish with a "
    "summary unless a further revision is needed."
)
SENTENCE = "After a candidate is judged NO_VIOLATION_FOUND, finish."
# Live run 6's first three replies, byte for byte (list, read, the new_source revision that
# the trusted evaluator judged NO_VIOLATION_FOUND in Docker).
LIVE6 = {
    n: (FIXTURES / f"live6_a{n}.txt").read_bytes().decode("utf-8") for n in (1, 2, 3)
}
LIVE6_SHA256 = {
    1: "deb06356e1e2f7ca70f41bd99c7c370cb0553cb739eee8de694712a79ac98485",
    2: "07bf7b2fd0cc5da673bd44aceb4d0eac046369c8ce45361231b6d626af8b9d97",
    3: "b518f4d8592cddd7a74e251f29124793e26f227f78c982ab61049f076ac50246",
}
FIX = (S01.parent / "s02_clean" / "evaluate.py").read_text(encoding="utf-8")
P1 = S.act("propose_patch", new_source=FIX, rationale="grouped folds")
P2 = S.act("propose_patch", diff=S.DIFF, rationale="another revision")


class OutcomeExecutor:
    """A candidate that ran with the given execution status and trusted outcome."""

    def __init__(self, outcome, status="completed"):
        self.outcome, self.status, self.calls = outcome, status, []

    def __call__(
        self, snapshot, candidate, approval, candidate_dir, *, proposed_at=None
    ):
        from atlas.agent.execute import CandidateResult

        self.calls.append(Path(candidate_dir))
        Path(candidate_dir).mkdir(parents=True)
        return CandidateResult(
            candidate_dir=Path(candidate_dir),
            candidate_hash=approval.candidate_hash,
            approval=approval.to_dict(),
            diff_sha256=candidate.diff_sha256,
            execution={"status": self.status},
            evaluated=True,
            outcome=RunOutcome(outcome=self.outcome, policy_version="policy-v1.3"),
            timing={},
            candidate_output="" if self.status != "completed" else None,
        )


@pytest.fixture
def host_baseline(monkeypatch):
    monkeypatch.setattr(ctl, "docker_original", S.host_fixture_original)


def fixture_run(tmp_path, replies, executor):
    client = FixtureClient("s4h", [{"content": r} for r in replies])
    result = ctl.run_agent(
        S01, tmp_path / "runs", client, S.ApproveExactly(), executor=executor, env={}
    )
    return result, client


def history(request) -> list[dict]:
    (user,) = [m for m in request.messages if m["role"] == "user"]
    return json.loads(user["content"])["history"]


def evaluations(request) -> list[dict]:
    return [h["result"] for h in history(request) if h["tool"] == "evaluate_candidate"]


# =============================================================================================
# 1. The prompt
# =============================================================================================


def test_the_fixed_line_is_the_decided_text():
    assert ctl.FINISH_AFTER_SUCCESS == LINE


def test_the_system_prompt_says_to_finish_after_success():
    assert SENTENCE in ctl.SYSTEM_INSTRUCTIONS
    assert ctl.SYSTEM_PROMPT.startswith(ctl.SYSTEM_INSTRUCTIONS)
    # Generic: no project, file or check names.
    for word in ("s01", "evaluate.py", "subject", "split.", "fit."):
        assert word not in SENTENCE


def test_the_prompt_budget_figures_are_rederived(tmp_path):
    """At the decided 12,000-token input estimate (the production client over a mock)."""
    system = len(ctl.SYSTEM_PROMPT.encode("utf-8"))
    assert len(ctl.SYSTEM_INSTRUCTIONS.encode("utf-8")) == 1225
    assert system == 2309
    result, _ = S.live_run(
        tmp_path, [(200, S.ok_body(FINISH, S.USAGE))], max_input_tokens=12_000
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    assert result.report["prompt_budget"] == {
        "user_message_bytes": 12_000 - system - 2 * 16,
        "tool_result_chars": (12_000 - system - 2 * 16) // 2,
    }
    assert result.report["prompt_budget"] == {
        "user_message_bytes": 9659,
        "tool_result_chars": 4829,
    }


# =============================================================================================
# 2. The fixed line, only for NO_VIOLATION_FOUND candidates
# =============================================================================================


def test_a_no_violation_candidate_gets_the_fixed_line(tmp_path, host_baseline):
    result, client = fixture_run(
        tmp_path, [P1, FINISH], OutcomeExecutor(Outcome.NO_VIOLATION_FOUND)
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    (seen,) = evaluations(client.requests[1])
    assert seen["scientific_outcome"] == "NO_VIOLATION_FOUND"
    assert seen["next_step"] == LINE
    # Exactly once in what the model is sent, and only in that result.
    sent = json.dumps(client.requests[1].messages)
    assert sent.count(json.dumps(LINE)[1:-1]) == 1
    others = [
        h for h in history(client.requests[1]) if h["tool"] != "evaluate_candidate"
    ]
    assert all("next_step" not in json.dumps(h) for h in others)


@pytest.mark.parametrize(
    ("outcome", "status"),
    [
        (Outcome.VIOLATION_FOUND, "completed"),
        (Outcome.INCONCLUSIVE, "completed"),
        (Outcome.INCONCLUSIVE, "failed"),
        (Outcome.NOT_SUPPORTED, "completed"),
    ],
    ids=["violation", "inconclusive", "failed", "not-supported"],
)
def test_other_outcomes_get_no_line(tmp_path, host_baseline, outcome, status):
    result, client = fixture_run(
        tmp_path, [P1, FINISH], OutcomeExecutor(outcome, status)
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    (seen,) = evaluations(client.requests[1])
    assert seen["scientific_outcome"] == outcome.value
    assert "next_step" not in seen
    assert json.dumps(LINE)[1:-1] not in json.dumps(client.requests[1].messages)


def test_the_line_is_not_in_the_report_or_the_log(tmp_path, host_baseline):
    result, _ = fixture_run(
        tmp_path, [P1, FINISH], OutcomeExecutor(Outcome.NO_VIOLATION_FOUND)
    )
    assert LINE not in json.dumps(result.report)
    assert "next_step" not in json.dumps(result.report)
    assert result.report["scientific_outcomes"]["candidates"] == ["NO_VIOLATION_FOUND"]
    assert result.report["scientific_outcomes"]["source"] == "trusted evaluator only"


def test_the_line_is_guidance_and_the_model_still_decides(tmp_path, host_baseline):
    """A further revision after the line is handled exactly as before."""
    executor = OutcomeExecutor(Outcome.NO_VIOLATION_FOUND)
    result, client = fixture_run(tmp_path, [P1, P2, FINISH], executor)
    assert result.terminal_state == ctl.REPORT, result.reason
    assert len(executor.calls) == 2
    assert [p["outcome"] for p in result.report["proposals"]] == [
        "executed",
        "executed",
    ]
    assert [e.get("next_step") for e in evaluations(client.requests[2])] == [LINE, LINE]


# =============================================================================================
# 3. Fixture replay: success -> finish -> REPORT
# =============================================================================================


def test_the_fixtures_are_live_run_6s_bytes():
    for n, text in LIVE6.items():
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert digest == LIVE6_SHA256[n], n


def test_the_live_run_6_replay_finishes_after_success(tmp_path, host_baseline):
    """Live run 6's replies 1 to 3 byte for byte; the candidate is judged NO_VIOLATION_FOUND,
    the next request carries the line, and a finish ends the run REPORT within budget."""
    finish = S.act("finish", summary="the revision removed the violations")
    executor = OutcomeExecutor(Outcome.NO_VIOLATION_FOUND)
    result, client = fixture_run(
        tmp_path, [LIVE6[1], LIVE6[2], LIVE6[3], finish], executor
    )
    assert result.terminal_state == ctl.REPORT, result.reason
    assert result.report["schema_failures"] == []
    assert len(client.requests) == 4 and len(executor.calls) == 1
    assert [e["next_step"] for e in evaluations(client.requests[3])] == [LINE]
    (record,) = result.report["proposals"]
    assert (record["source_kind"], record["outcome"]) == ("new_source", "executed")
    assert result.report["budget"]["used"]["revisions"] == 1
    assert result.report["scientific_outcomes"]["candidates"] == ["NO_VIOLATION_FOUND"]
    summaries = [
        t for t in result.report["model_text"] if t["kind"] == "finish_summary"
    ]
    assert [t["text"] for t in summaries] == ["the revision removed the violations"]
