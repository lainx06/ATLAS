"""Full-source proposals and proposal records (T-06 slice 4c).

A `propose_patch` reply carries either a unified `diff` or `new_source`, the complete revised
entry point. For `new_source`, ATLAS builds the unified diff itself, deterministically
(`difflib.unified_diff` against the snapshot's entry point, headers `--- a/<entry>` and
`+++ b/<entry>`). **`candidates.validate_diff` is then the only gate, unchanged**, exactly as for
a supplied diff. The validated candidate's entry bytes must equal `new_source`'s UTF-8 bytes,
otherwise the proposal is rejected (`diff_mismatch`). Model text is never altered.

**Newline rule (documented choice).** `new_source` must end with a newline. Without one it is
rejected as `malformed_source`, never silently completed. When the text has no line break but
two or more literal backslash-n sequences (a double-escaped JSON string), the rejection carries a
detail saying so; the source is still rejected, never decoded again. It must also contain no carriage
return or NUL (`malformed_source`), which `validate_diff` refuses in any diff. If the snapshot's
own entry point lacks a final newline, the generated diff carries the standard
`\\ No newline at end of file` marker for that old line, which `validate_diff` already parses.

An unchanged `new_source` is rejected as `no_change`, the same code `validate_diff` uses, because
an empty diff would otherwise be reported as a missing file header.
"""

import difflib

from atlas.candidates import CandidateRejected

NO_NEWLINE = "\\ No newline at end of file\n"
DETAIL_CHARS = 200
DETAIL_LABEL = "validator message; may quote model text"
FILE_LABEL = "model-written (untrusted)"
LITERAL_BACKSLASH_N = "\\n"  # the two characters backslash and n
DOUBLE_ESCAPED_DETAIL = (
    "new_source contains literal backslash-n sequences and no line breaks; "
    "it appears double-escaped. In the JSON reply, escape each newline once, as \\n."
)


def source_diff(original: str, new_source: str, entry_point: str) -> str:
    """The unified diff from `original` to `new_source`, in the form `validate_diff` accepts."""
    if "\r" in new_source or "\x00" in new_source:
        raise CandidateRejected(
            "malformed_source", "carriage return or NUL in new_source"
        )
    if not new_source.endswith("\n"):
        if "\n" not in new_source and new_source.count(LITERAL_BACKSLASH_N) >= 2:
            raise CandidateRejected("malformed_source", DOUBLE_ESCAPED_DETAIL)
        raise CandidateRejected(
            "malformed_source", "new_source must end with a newline (it is not altered)"
        )
    if new_source == original:
        raise CandidateRejected("no_change")
    lines = []
    for line in difflib.unified_diff(
        original.splitlines(keepends=True),
        new_source.splitlines(keepends=True),
        f"a/{entry_point}",
        f"b/{entry_point}",
    ):
        if line.endswith("\n"):
            lines.append(line)
        else:  # only the original's last line can lack a newline (new_source ends with one)
            lines.append(line + "\n")
            lines.append(NO_NEWLINE)
    return "".join(lines)


def bounded_detail(exc: Exception) -> str | None:
    """The validator's message without its code prefix, cut to DETAIL_CHARS characters."""
    code = getattr(exc, "code", None)
    text = str(exc)
    if code and text.startswith(f"{code}: "):
        text = text[len(code) + 2 :]
    elif code and text == code:
        return None
    return text[:DETAIL_CHARS]


def summary_line(records: list[dict]) -> str:
    """The run-level limitation line, e.g. "2 proposals: 2 rejected by validation, 0
    declined, 0 executed"."""
    count = {k: sum(1 for r in records if r["outcome"] == k) for k in OUTCOMES}
    line = (
        f"{len(records)} proposal{'s' if len(records) != 1 else ''}: "
        f"{count['rejected']} rejected by validation, {count['declined']} declined, "
        f"{count['executed']} executed"
    )
    if count["unavailable"]:
        line += f", {count['unavailable']} unavailable (no approval possible)"
    if count[NOT_EXECUTED_HERE]:  # hosted mode only (T-12)
        line += f", {count[NOT_EXECUTED_HERE]} passed ATLAS validation and not executed here"
    return line


# Hosted mode (T-12, SPEC §13): a validated proposal is recorded, never approved or executed.
NOT_EXECUTED_HERE = "not_executed_here"
OUTCOMES = ("rejected", "declined", "unavailable", "executed", NOT_EXECUTED_HERE)
