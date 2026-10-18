"""A failing candidate's bounded, sanitized error summary for the model (T-06 slice 4f).

The in-container supervisor merges the candidate child's stderr into its stdout and keeps the
last 16 KiB as `candidate_output_tail` in its frame header (`runner/container_entry.py`,
`supervise`). The execution record's `stderr_tail` is the docker CLI's own stderr, not the
candidate's, so it is empty when only the candidate failed. This module summarizes the captured
output only; nothing in the runner changes.

The summary is the exception line of the last traceback (its type and message) plus at most
the last MAX_LINES lines of that traceback, or of the output when there is no traceback. Both
together are at most MAX_CHARS characters, keeping the end. Before bounding, host paths (the
given host strings and any Windows drive or UNC path), host environment values and the given
secrets are redacted; then every control or format character except the line separator is
escaped. It is candidate-written text, labelled untrusted: never evidence and never an outcome.
"""

import os
import re
import unicodedata
from collections.abc import Iterable, Mapping

LABEL = "candidate output (untrusted)"
MAX_CHARS = 2000
MAX_LINES = 20
MAX_EXCEPTION_CHARS = 500
MIN_ENV_VALUE_CHARS = 8  # shorter values are too common to redact meaningfully
HOST_PATH = "<host-path>"
ENV_VALUE = "<env-redacted>"
SECRET = "<redacted>"
TRACEBACK_HEADER = "Traceback (most recent call last):"
# A Windows drive path (C:\..., C:/..., or repr-doubled C:\\...) or a UNC path (\\host\...),
# up to the next whitespace, quote or bracket. Container paths (/work, /opt, /usr) are kept.
_WINDOWS_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s'\"<>|()\[\]{},;]*")
_UNC_PATH = re.compile(r"\\{2,}[A-Za-z0-9._$-]+(?:\\+[^\s'\"<>|()\[\]{},;]*)?")


def summarize(
    output: str | None,
    *,
    host_strings: Iterable[str] = (),
    env: Mapping[str, str] | None = None,
    secrets: Iterable[str] = (),
) -> dict:
    """The summary of a failing candidate's captured output (None or "" gives an empty one).
    `env` defaults to this process's environment."""
    text = _redact(
        output or "", host_strings, os.environ if env is None else env, secrets
    )
    lines = text.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    starts = [i for i, line in enumerate(lines) if line.rstrip() == TRACEBACK_HEADER]
    block = lines[starts[-1] :] if starts else lines
    exception = None
    if starts:
        tail = [line for line in block[1:] if line.strip() and not line[0].isspace()]
        exception = tail[-1] if tail else None
    kept = [_escape(line) for line in block[-MAX_LINES:]]
    truncated = len(block) > MAX_LINES
    if exception is not None:
        exception = _escape(exception)
        if len(exception) > MAX_EXCEPTION_CHARS:
            exception, truncated = exception[:MAX_EXCEPTION_CHARS], True
    traceback = "\n".join(kept)
    room = MAX_CHARS - len(exception or "")
    if len(traceback) > room:
        traceback, truncated = traceback[len(traceback) - room :], True
    return {
        "label": LABEL,
        "exception": exception,
        "traceback": traceback,
        "truncated": truncated,
    }


def _redact(text: str, host_strings, env, secrets) -> str:
    for secret in sorted({s for s in secrets if s}, key=len, reverse=True):
        text = text.replace(secret, SECRET)
    values = {
        v for v in env.values() if isinstance(v, str) and len(v) >= MIN_ENV_VALUE_CHARS
    }
    hosts = set()
    for host in host_strings:
        bare = (host or "").rstrip("\\/")
        if not bare or re.fullmatch(r"[A-Za-z]:", bare):
            continue  # a filesystem root would redact every separator
        hosts |= {bare, bare.replace("\\", "/"), bare.replace("\\", "\\\\")}
    # Longest first, so a path is replaced whole before any value inside it.
    for value in sorted(hosts | values, key=len, reverse=True):
        marker = HOST_PATH if value in hosts else ENV_VALUE
        text = re.sub(re.escape(value), marker, text, flags=re.IGNORECASE)
    text = _UNC_PATH.sub(HOST_PATH, text)
    return _WINDOWS_PATH.sub(HOST_PATH, text)


def _escape(line: str) -> str:
    return "".join(
        ch if not unicodedata.category(ch).startswith("C") else _code(ch) for ch in line
    )


def _code(ch: str) -> str:
    n = ord(ch)
    return (
        f"\\x{n:02x}" if n < 0x100 else f"\\u{n:04x}" if n < 0x10000 else f"\\U{n:08x}"
    )
