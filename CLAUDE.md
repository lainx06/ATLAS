# CLAUDE.md

Shared rules live in @AGENTS.md. Do not duplicate them here.

Before working, read `STATUS.md` (current writer, checkpoint, blockers, next task) and the current entry in `TASKS.md`.

Claude Code specifics:
- Shell is native Windows (PowerShell 5.1 primary; Git Bash available). Run Python via `uv run`, not a manually activated venv.
- PowerShell 5.1 mangles quotes in `python -c "..."`; put multi-line Python in a file instead.
- Project-local skills (once installed in Step 6) live in `.claude/skills/`; see `docs/TOOLING.md`.
- Update `STATUS.md` at every task boundary or handoff.
