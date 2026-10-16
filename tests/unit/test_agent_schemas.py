"""T-06 slice 2: strict, bounded, single-action replies, validated whole (SPEC §11)."""

import json

import pytest

from atlas.agent import schemas
from atlas.agent.schemas import ReplyRejected, parse_reply


def reply(action: dict) -> str:
    return json.dumps({"action": action})


VALID = {
    "list": {"tool": "list_project_files"},
    "read": {"tool": "read_project_file", "path": "evaluate.py"},
    "inspect": {"tool": "inspect_evidence", "check": "split_integrity"},
    "patch": {"tool": "propose_patch", "diff": "--- a/x\n+++ b/x\n", "rationale": "r"},
    "finish": {"tool": "finish", "summary": "done"},
}


@pytest.mark.parametrize("name", list(VALID))
def test_each_action_is_accepted_exactly(name):
    action = parse_reply(reply(VALID[name])).action
    assert action.model_dump() == VALID[name]


def test_only_surrounding_whitespace_is_removed():
    assert parse_reply("\n\n  " + reply(VALID["finish"]) + "\n").action.tool == "finish"


DEEP = '{"action": ' + "[" * 100_000 + "]" * 100_000 + "}"
INVALID = {
    "prose_before": ("Here is my answer: " + reply(VALID["finish"]), "not_json"),
    "markdown_fence": ("```json\n" + reply(VALID["finish"]) + "\n```", "not_json"),
    "two_actions_in_a_list": (
        json.dumps({"action": [VALID["list"], VALID["finish"]]}),
        "schema",
    ),
    "two_concatenated_replies": (
        reply(VALID["list"]) + reply(VALID["finish"]),
        "not_json",
    ),
    "bare_action": (json.dumps(VALID["finish"]), "schema"),
    "top_level_array": (json.dumps([{"action": VALID["finish"]}]), "not_an_object"),
    "extra_top_level_approval": (
        json.dumps(
            {"action": VALID["finish"], "approval": {"candidate_hash": "a" * 64}}
        ),
        "schema",
    ),
    "extra_action_field_approved": (
        reply({**VALID["patch"], "approved": True}),
        "schema",
    ),
    "assertions_field": (reply({**VALID["finish"], "assertions": []}), "schema"),
    "outcome_field": (
        reply({**VALID["finish"], "outcome": "NO_VIOLATION_FOUND"}),
        "schema",
    ),
    "unknown_tool": (reply({"tool": "run_shell", "command": "ls"}), "schema"),
    "evaluate_candidate_is_not_a_model_action": (
        reply({"tool": "evaluate_candidate", "candidate_hash": "a" * 64}),
        "schema",
    ),
    "wrong_type_coerced_nowhere": (
        reply({"tool": "inspect_evidence", "check": 1}),
        "schema",
    ),
    "unknown_check": (
        reply({"tool": "inspect_evidence", "check": "everything"}),
        "schema",
    ),
    "missing_field": (reply({"tool": "read_project_file"}), "schema"),
    "duplicate_tool_key": (
        '{"action": {"tool": "finish", "tool": "propose_patch", "summary": "x"}}',
        "duplicate_key",
    ),
    "duplicate_action_key": (
        '{"action": {"tool": "finish", "summary": "a"}, "action": {"tool": "list_project_files"}}',
        "duplicate_key",
    ),
    "path_too_long": (
        reply({"tool": "read_project_file", "path": "a" * 201}),
        "schema",
    ),
    "summary_too_long": (reply({"tool": "finish", "summary": "s" * 4001}), "schema"),
    "diff_too_long": (
        reply({**VALID["patch"], "diff": "d" * (schemas.MAX_DIFF_BYTES + 1)}),
        "schema",
    ),
    "reply_too_large": (" " * (schemas.MAX_REPLY_BYTES + 1), "too_large"),
    "empty": ("", "empty"),
    "whitespace_only": ("  \n ", "empty"),
    "deeply_nested": (DEEP, "too_large"),
    "truncated": (reply(VALID["finish"])[:-5], "not_json"),
    "null_content": (None, "missing_content"),
    "non_string_content": ({"action": VALID["finish"]}, "missing_content"),
}


@pytest.mark.parametrize("case", list(INVALID))
def test_invalid_replies_authorize_nothing(case):
    content, code = INVALID[case]
    with pytest.raises(ReplyRejected) as raised:
        parse_reply(content)
    assert raised.value.code == code


def test_deep_nesting_within_the_size_cap_is_rejected_not_crashed():
    nested = '{"action": ' + "[" * 20_000 + "]" * 20_000 + "}"
    assert len(nested) < schemas.MAX_REPLY_BYTES
    with pytest.raises(ReplyRejected) as raised:
        parse_reply(nested)
    assert raised.value.code in ("not_json", "schema")


# --- repair pass 1 (Codex review of 4232cc5): the diff limit is in UTF-8 bytes ----------------


def patch_reply(diff: str) -> str:
    action = {"tool": "propose_patch", "diff": diff, "rationale": ""}
    return json.dumps({"action": action}, ensure_ascii=False)


HALF = schemas.MAX_DIFF_BYTES // 2  # "é" is two UTF-8 bytes


@pytest.mark.parametrize(
    "diff",
    ["é" * HALF, "a" * schemas.MAX_DIFF_BYTES, "é" * (HALF - 1) + "ab"],
    ids=["multibyte_at_limit", "ascii_at_limit", "mixed_at_limit"],
)
def test_a_diff_of_exactly_the_byte_limit_is_accepted(diff):
    assert len(diff.encode("utf-8")) == schemas.MAX_DIFF_BYTES
    assert parse_reply(patch_reply(diff)).action.diff == diff


@pytest.mark.parametrize(
    "diff",
    ["é" * HALF + "x", "é" * 40_000, "a" * schemas.MAX_DIFF_BYTES + "é"],
    ids=[
        "multibyte_one_byte_over",
        "multibyte_80000_bytes",
        "ascii_then_multibyte_over",
    ],
)
def test_a_diff_over_the_byte_limit_is_a_schema_failure(diff):
    assert len(diff.encode("utf-8")) > schemas.MAX_DIFF_BYTES
    with pytest.raises(ReplyRejected) as raised:
        parse_reply(patch_reply(diff))
    assert raised.value.code == "schema"


def test_a_lone_surrogate_in_a_diff_is_a_schema_failure():
    with pytest.raises(ReplyRejected):
        parse_reply(
            '{"action": {"tool": "propose_patch", "diff": "\ud800", "rationale": ""}}'
        )
