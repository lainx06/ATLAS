"""Compaction handoff for Claude Code hooks (`.claude/settings.json`).

Default (the PreCompact hook): write a short snapshot of the working state to
`runs/handoff/<UTC timestamp>.md` and overwrite `runs/handoff/latest.md` (`runs/` is
git-ignored). It holds the branch, HEAD, `git status --porcelain`, the last 5 commits,
STATUS.md's CURRENT STEP section and the tails of the 5 most recently modified `*.log`
files under `runs/`, at most 8 KB in all.

`--context` (the SessionStart hook, matcher `compact`): print the ATLAS invariants and
where to resume, at most 25 lines; Claude Code adds this stdout to the model's context.

Standard library only. It reads only git output, STATUS.md and `*.log` files under
`runs/`; it never opens `.env` or `.env.*`. It never fails a hook: every error is caught
and the exit status is always 0.
"""

import contextlib
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
OUT = RUNS / "handoff"
MAX_BYTES = 8 * 1024
STATUS_LINES = 60
PORCELAIN_LINES = 40
LOGS = 5
LOG_TAIL = 3
LINE_CHARS = 400

CONTEXT = """\
ATLAS post-compaction context (SessionStart hook, scripts/handoff_snapshot.py --context).
Invariants:
- Candidate code executes only in Docker: --network none, non-root, read-only rootfs.
- Model replies are validated exactly against the schema; nothing is repaired or guessed.
- At most 6 requests per run, each reserved in the budget before dispatch.
- Never read .env or .env.* (no key inspection, no printing secrets).
- No live run (Nebius request) without the user's explicit go-ahead for that run.
- Outcomes come only from the trusted evaluator and are reported as measured
  (VIOLATION_FOUND, NO_VIOLATION_FOUND, INCONCLUSIVE, NOT_SUPPORTED); never "VALID".
Checkout:
- Main checkout: C:/Users/Lain/source/atlas. Work there unless the brief names a worktree.
- Kept worktrees (atlas-s4c, atlas-t07b, atlas-t09) hold evidence in their git-ignored
  runs/; do not remove or edit them. Do not merge or push unless asked.
Before continuing: read runs/handoff/latest.md and STATUS.md CURRENT STEP; if a test run was in progress, rerun it rather than assume it finished.
"""


def git(*args: str) -> str:
    try:
        done = subprocess.run(
            ["git", *args],
            check=False,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            stdin=subprocess.DEVNULL,
        )
        return (done.stdout or done.stderr).rstrip()
    except Exception as exc:  # noqa: BLE001 - recorded, never raised
        return f"(git {' '.join(args)} failed: {type(exc).__name__})"


def clip(line: str) -> str:
    return line if len(line) <= LINE_CHARS else line[: LINE_CHARS - 1] + "…"


def current_step() -> list[str]:
    """STATUS.md from the CURRENT STEP line to the next heading, at most 60 lines."""
    try:
        lines = (ROOT / "STATUS.md").read_text(encoding="utf-8").splitlines()
    except Exception as exc:  # noqa: BLE001
        return [f"(STATUS.md unreadable: {type(exc).__name__})"]
    start = next((i for i, x in enumerate(lines) if x.startswith("CURRENT STEP")), None)
    if start is None:
        return ["(no CURRENT STEP line in STATUS.md)"]
    section = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("#") or len(section) >= STATUS_LINES:
            break
        section.append(line)
    return [clip(x) for x in section]


def is_env(path: Path) -> bool:
    return any(p == ".env" or p.startswith(".env.") for p in path.parts)


def tail(path: Path, n: int) -> list[str]:
    with path.open("rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - 8192))
        data = f.read()
    lines = [
        x for x in data.decode("utf-8", errors="replace").splitlines() if x.strip()
    ]
    return [clip(x) for x in lines[-n:]]


def recent_logs() -> list[str]:
    found = []
    try:
        for path in RUNS.rglob("*.log"):
            try:
                if path.is_file() and not is_env(path.relative_to(RUNS)):
                    found.append((path.stat().st_mtime, path))
            except OSError:
                continue
    except Exception as exc:  # noqa: BLE001
        return [f"(runs/ not scanned: {type(exc).__name__})"]
    out = []
    for mtime, path in sorted(found, reverse=True)[:LOGS]:
        when = datetime.fromtimestamp(mtime, UTC).strftime("%Y-%m-%d %H:%M:%SZ")
        out.append(f"- `{path.relative_to(ROOT).as_posix()}` (modified {when})")
        try:
            out += [f"    {x}" for x in tail(path, LOG_TAIL)] or ["    (empty)"]
        except Exception as exc:  # noqa: BLE001
            out.append(f"    (unreadable: {type(exc).__name__})")
    return out or ["(no *.log files under runs/)"]


def facts() -> dict:
    porcelain = git("status", "--porcelain").splitlines()
    if len(porcelain) > PORCELAIN_LINES:
        more = len(porcelain) - PORCELAIN_LINES
        porcelain = porcelain[:PORCELAIN_LINES] + [f"... {more} more lines"]
    return {
        "branch": git("branch", "--show-current") or "(detached)",
        "head": git("log", "-1", "--format=%H %s"),
        "porcelain": porcelain or ["(clean)"],
        "commits": git("log", "-5", "--format=%h %ad %s", "--date=short"),
        "logs": recent_logs(),
    }


def render(now: datetime, f: dict, step: list[str]) -> str:
    parts = [
        f"# Handoff snapshot {now.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "Written by scripts/handoff_snapshot.py (PreCompact hook). Facts only; verify before acting.",
        "",
        f"Branch: `{f['branch']}`",
        f"HEAD: `{f['head']}`",
        "",
        "## git status --porcelain",
        "```",
        *f["porcelain"],
        "```",
        "",
        "## Last 5 commits",
        "```",
        f["commits"],
        "```",
        "",
        "## Recent logs under runs/ (last 3 lines each)",
        *f["logs"],
        "",
        f"## STATUS.md CURRENT STEP ({len(step)} lines)",
        *step,
        "",
    ]
    return "\n".join(parts)


def snapshot() -> None:
    now = datetime.now(UTC)
    found, step = facts(), current_step()
    text = render(now, found, step)
    # Over 8 KB: drop CURRENT STEP lines from the end (it is last), then cut hard.
    while len(text.encode("utf-8")) > MAX_BYTES and len(step) > 1:
        step = step[:-1]
        text = render(now, found, step + ["... (cut to fit 8 KB)"])
    data = text.encode("utf-8")[:MAX_BYTES].decode("utf-8", errors="ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    stamped = OUT / f"{now.strftime('%Y%m%dT%H%M%SZ')}.md"
    for path in (stamped, OUT / "latest.md"):
        path.write_text(data, encoding="utf-8", newline="\n")
    print(f"handoff snapshot: {stamped.relative_to(ROOT).as_posix()} and latest.md")


def main() -> None:
    try:
        if "--context" in sys.argv[1:]:
            sys.stdout.write(CONTEXT)
        else:
            snapshot()
    except BaseException as exc:  # noqa: BLE001 - a hook must never fail
        with contextlib.suppress(Exception):
            print(f"handoff snapshot skipped: {type(exc).__name__}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
