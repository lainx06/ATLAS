"""Fixture model replies for the UI's NON-LIVE agent mode (no model is called).

`revision` is the script the Docker integration test drives
(`tests/integration/test_agent_fixture_docker.py:SCRIPT`), built the same way: the s01->s02
unified diff of the entry point. `tests/unit/test_ui_scripts.py` checks they stay identical.
The others are curated for the UI's failure and honest-empty states. A fixture run is never
live proof, and the report's banner says so.
"""

import difflib
import json
from dataclasses import dataclass

from atlas.ui.catalogue import BENCHMARKS


def _act(tool: str, **fields) -> dict:
    return {"content": json.dumps({"action": {"tool": tool, **fields}})}


def s01_to_s02_diff() -> str:
    return "".join(
        difflib.unified_diff(
            (BENCHMARKS / "s01_faulty" / "evaluate.py")
            .read_text(encoding="utf-8")
            .splitlines(True),
            (BENCHMARKS / "s02_clean" / "evaluate.py")
            .read_text(encoding="utf-8")
            .splitlines(True),
            "a/evaluate.py",
            "b/evaluate.py",
        )
    )


def _miscounted(diff: str) -> str:
    """The same diff with its first hunk's new-side count raised by one (malformed_diff)."""
    lines = diff.splitlines(True)
    i = next(n for n, line in enumerate(lines) if line.startswith("@@"))
    head, rest = lines[i].split(" @@", 1)
    old, new = head[3:].split(" ")
    start, count = new.split(",")
    lines[i] = f"@@ {old} {start},{int(count) + 1} @@{rest}"
    return "".join(lines)


@dataclass(frozen=True)
class Script:
    key: str
    title: str
    description: str
    projects: tuple[str, ...] | None  # None: offered for every project

    def replies(self) -> list[dict]:
        return _REPLIES[self.key]()


def _revision() -> list[dict]:
    return [
        _act("inspect_evidence", check="split_integrity"),
        _act(
            "propose_patch",
            diff=s01_to_s02_diff(),
            rationale="fold-local selection, grouped folds",
        ),
        _act("finish", summary="done"),
    ]


def _inspect_only() -> list[dict]:
    return [
        _act("inspect_evidence", check="split_integrity"),
        _act("finish", summary="Inspected the split evidence; no revision proposed."),
    ]


def _rejected() -> list[dict]:
    return [
        _act(
            "propose_patch",
            diff=_miscounted(s01_to_s02_diff()),
            rationale="fold-local selection, grouped folds",
        ),
        _act("finish", summary="The revision was not accepted."),
    ]


def _timeout() -> list[dict]:
    # Two timeouts end the run after its one retry; the third reply is never read.
    return [{"error": "timeout"}, {"error": "timeout"}, {"content": "not json"}]


def _invalid() -> list[dict]:
    return [
        {"content": "This reply is prose, not the JSON action the schema requires."}
    ]


_REPLIES = {
    "revision": _revision,
    "inspect_only": _inspect_only,
    "rejected": _rejected,
    "timeout": _timeout,
    "invalid": _invalid,
}

SCRIPTS = (
    Script(
        "revision",
        "Propose a grouped, fold-local revision",
        "Inspects the split evidence, proposes one revision of the entry point, then "
        "finishes (the Docker integration test's script).",
        ("s01_faulty",),
    ),
    Script(
        "inspect_only",
        "Inspect only, no revision",
        "Inspects the split evidence and finishes without proposing a revision.",
        None,
    ),
    Script(
        "rejected",
        "Propose a malformed revision",
        "Proposes a diff whose hunk counts are wrong; validation rejects it, so nothing "
        "executes.",
        ("s01_faulty",),
    ),
    Script(
        "timeout",
        "Provider timeout",
        "Two timeouts in a row: the run ends after its single recorded retry.",
        None,
    ),
    Script(
        "invalid",
        "Invalid reply",
        "A reply that is not JSON: a schema failure, with no repair retry.",
        None,
    ),
)
BY_KEY = {s.key: s for s in SCRIPTS}


def scripts_for(project: str) -> list[Script]:
    return [s for s in SCRIPTS if s.projects is None or project in s.projects]


def default_script(project: str) -> str:
    return "revision" if project == "s01_faulty" else "inspect_only"
