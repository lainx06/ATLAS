"""T-06 slice 2 integration: a fixture-driven agent run through the real slice 1 executor.

    ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_agent_fixture_docker.py

Fixture model replies (no model, no network) -> audit of s01_faulty (trusted host-fixture
runner) -> the fold-local patch -> an explicit test approver bound to the exact candidate ->
the isolated Docker runner -> trusted re-evaluation -> a report labelled non-live.
"""

import difflib
import json
import os
from pathlib import Path

import pytest

from atlas.agent import controller as ctl
from atlas.agent.client import FixtureClient
from atlas.candidates import Approval
from atlas.contracts import Outcome
from atlas.runner import docker as dr

ROOT = Path(__file__).resolve().parents[2]
S01 = ROOT / "benchmarks" / "t01" / "s01_faulty"
S02 = ROOT / "benchmarks" / "t01" / "s02_clean"
REQUIRE_DOCKER = os.environ.get("ATLAS_REQUIRE_DOCKER") == "1"


@pytest.fixture(scope="module")
def isolation():
    cap = dr.probe()
    if cap.state != dr.CAPABILITY_AVAILABLE:
        message = f"isolated runner unavailable: {cap.reason}"
        if REQUIRE_DOCKER:
            pytest.fail(message)
        pytest.skip(message)
    return cap


class ApproveExactly:
    def __init__(self):
        self.requests = []

    def decide(self, request):
        self.requests.append(request)
        return Approval(
            request.candidate_hash,
            request.base_snapshot_hash,
            "2026-10-15T00:00:00+00:00",
        )


def test_fixture_agent_run_through_the_isolated_executor(isolation, tmp_path):
    original = (S01 / "evaluate.py").read_text(encoding="utf-8")
    fix = (S02 / "evaluate.py").read_text(encoding="utf-8")
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(True),
            fix.splitlines(True),
            "a/evaluate.py",
            "b/evaluate.py",
        )
    )
    script = [
        {"content": json.dumps({"action": {"tool": "inspect_evidence", "check": "split_integrity"}})},
        {"content": json.dumps({"action": {"tool": "propose_patch", "diff": diff, "rationale": "fold-local selection, grouped folds"}})},
        {"content": json.dumps({"action": {"tool": "finish", "summary": "done"}})},
    ]  # fmt: skip
    approver = ApproveExactly()
    result = ctl.run_agent(
        S01, tmp_path / "runs", FixtureClient("s01-docker", script), approver, env={}
    )

    assert result.terminal_state == ctl.REPORT, result.reason
    assert result.original.outcome.outcome is Outcome.VIOLATION_FOUND
    (candidate,) = result.candidates
    assert candidate.candidate_hash == approver.requests[0].candidate_hash
    assert candidate.execution["status"] == "completed"
    assert candidate.execution["container_removed"] is True
    assert candidate.outcome.outcome is Outcome.NO_VIOLATION_FOUND
    report = result.report
    assert (report["live"], report["model_id"]) == (False, "fixture:s01-docker")
    assert report["scientific_outcomes"]["candidates"] == [Outcome.NO_VIOLATION_FOUND]
    assert report["budget"]["used"]["attempts"] == 3
