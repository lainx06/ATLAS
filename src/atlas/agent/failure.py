"""A failing candidate's bounded, sanitized error summary for the model (T-06 slice 4f).

The in-container supervisor merges the candidate child's stderr into its stdout and keeps the
last 16 KiB as `candidate_output_tail` in its frame header (`runner/container_entry.py`,
`supervise`). The execution record's `stderr_tail` is the docker CLI's own stderr, not the
candidate's, so it is empty when only the candidate failed. This module summarizes the captured
output only; nothing in the runner changes.

The summary is the exception line of the last traceback (its type and message) plus at most
the last MAX_LINES lines of that traceback, or of the output when there is no traceback. Both
together are at most MAX_CHARS characters, keeping the end. Before bounding, host paths (the
given host strings, then, on any line where a Windows drive or UNC path starts in any slash
style, quoted or not, everything from that start to the end of the line; a traceback frame
line, File "<anything>", line <digits>[, in <name>], becomes File "<host-path>" with its tail
kept as written), host environment values and the given secrets are redacted; then every
control or format character except the line separator is escaped. It is candidate-written
text, labelled untrusted: never evidence and never an outcome.

Redaction is best-effort for host paths and known values, not a guarantee. The candidate runs
in a container whose only mounts are under /work, so a host path reaches its output only
through text the candidate itself constructs. Path text deliberately split or encoded across
lines (or otherwise transformed) is not guaranteed to be redacted; only exact known values are
replaced, not fragments of them.
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
# The start of a Windows drive path (C:\, C:/, repr-doubled C:\\) or a UNC path in any slash
# style (\\host, //host/, \\host/, /\host\, repr-doubled \\\\host). A forward-slash UNC path
# needs its share separator, and none may follow a word character, ":" or a slash, so URLs
# (https://...), floor division (x//2) and container paths (/work, /opt, /usr) are kept.
_DRIVE = r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]"
_HOST = r"[A-Za-z0-9._$-]+"
_UNC = rf"(?<![\w:/\\])(?:\\{{2,}}{_HOST}|[\\/]{{2,}}{_HOST}[\\/])"
_PATH_START = re.compile(rf"{_DRIVE}|{_UNC}")
# A Python traceback frame line, File "<anything>", line <digits>[, in <name>]. Its tail is
# kept as written; the name is an identifier, a dotted qualified name or <module>-style, so
# the kept tail can hold no path.
_FRAME = re.compile(
    r'(\s*File )".*"(, line \d+(?:, in (?:<[A-Za-z_]\w*>|[A-Za-z_][\w.]*))?\r?)'
)


def _redact_paths(line: str) -> str:
    """Everything from the line's first host-path start to its end becomes HOST_PATH (quotes,
    spaces and commas included); a traceback frame line keeps its quotes and its tail."""
    start = _PATH_START.search(line)
    if start is None:
        return line
    frame = _FRAME.fullmatch(line)
    if frame is not None:
        return f'{frame[1]}"{HOST_PATH}"{frame[2]}'
    return line[: start.start()] + HOST_PATH


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
    return "\n".join(_redact_paths(line) for line in text.split("\n"))


def _escape(line: str) -> str:
    return "".join(
        ch if not unicodedata.category(ch).startswith("C") else _code(ch) for ch in line
    )


def _code(ch: str) -> str:
    n = ord(ch)
    return (
        f"\\x{n:02x}" if n < 0x100 else f"\\u{n:04x}" if n < 0x10000 else f"\\U{n:08x}"
    )
