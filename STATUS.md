# ATLAS status

WRITER: Claude Code
MODEL: Opus 5.5 (`claude-opus-5-5`), effort high
CURRENT STEP: Start Here Step 6 complete: 8 skills installed. Claude native loading verified for the model-invocable skills only. User-invoked Matt skill discovery unverified (awaiting slash-menu check). Codex unverified (pending Codex setup).
CHECKPOINT: Step 6 committed locally on `main` ("Install selected development skills"; parent `7a0f155`). Not pushed; no remote configured.
LAST UPDATED: 2026-10-14

## What works (verified by running)
- Python 3.11 environment: uv-managed CPython 3.11.17 in `.venv/`, pinned by `.python-version`.
- Dependencies resolved and locked: `uv.lock` (61 packages). `uv lock --check` exit 0.
- Import check: `uv run --locked python scripts/check_imports.py` exit 0; numpy, pandas, sklearn, pydantic, streamlit, openai, dotenv, pytest, and atlas all import.
- Lint: `uv run --locked ruff check .` → "All checks passed!" (exit 0); `uv run --locked ruff format --check .` exit 0 (vendored skill trees excluded from ruff; see docs/TOOLING.md).
- `.gitignore` exclusions verified with `git check-ignore -v --no-index` for .env, .env.*, *.pem, secrets.toml, .venv/, __pycache__/, .pytest_cache/, .ruff_cache/, artifacts/, runs/, *.log, data/raw/, .dev/ (vendor clones), dist/, test-results/. Tracked files (.env.example, pyproject.toml, uv.lock, sources, docs) are not ignored.
- Skills (Step 6): 8 skills + 3 Addy shared references copied from pinned commits (matt `49dd158d`, addy `aeac41d4`) into `.claude/` and `.agents/`. `uv run --locked python scripts/sync_skills.py --check` → "32 files x 2 destinations; problems: 0", exit 0. Copies identical across roots and to upstream; relative reference paths resolve. Details and statuses: docs/TOOLING.md.
- Claude Code native discovery of the 5 model-invocable skills, and native loading of `code-review-and-quality` with its `../../references/security-checklist.md`: verified (the first attempt said `Unknown skill`; discovery caught up later in the same session, and one retry succeeded). No restart needed.

## What does not exist yet
- **No tests.** `uv run --locked pytest -q` → "no tests ran", exit 5. Nothing has been tested.
- No application code. `src/atlas/` holds only a package docstring. No `atlas` CLI entry point.
- `docs/PRD.md`, `docs/SPEC.md`, and implementation task cards are **pending Step 7**.
- `/setup-matt-pocock-skills` has not been run (no `docs/agents/`, no `## Agent skills` block). No `.env` created and no API key requested or read.
- No Nebius call made. Docker is not on PATH (isolation not available; trusted fixtures only).

## Commands executed in setup
1. `git init -b main`
2. `uv python install 3.11` → installed cpython-3.11.17
3. `uv init --lib --name atlas --python 3.11 --vcs none --no-readme --managed-python`
4. `uv add numpy pandas scikit-learn pydantic streamlit openai python-dotenv`
5. `uv add --dev pytest ruff`
6. `uv lock --check`, `uv sync --locked`, import check, ruff check/format, pytest (results above)
7. `git check-ignore -v --no-index ...`, `git status --porcelain --untracked-files=all`
8. Step 6: `git clone` both skill repos into `.dev/skill-sources/{matt,addy}`, `git rev-parse HEAD`; `uv run --locked python scripts/sync_skills.py` (install) and `--check`; `diff`/`sha256sum` comparisons; ruff check/format.

## Blockers
- `/setup-matt-pocock-skills`, `/grill-with-docs`, `/to-spec` discovery: **unverified** until the user checks the Claude Code `/` menu.
- Codex discovery of `.agents/skills`: **unverified**, pending the Codex setup step.
- Docker/isolation: not installed. Not needed until Step 10; blocks candidate-code execution.

## Next task
1. User: confirm `/setup-matt-pocock-skills`, `/grill-with-docs`, `/to-spec` appear in the Claude Code `/` menu (user-invoked only; the model cannot see them), then record the result in docs/TOOLING.md.
2. Start Here Step 7 (not started): `/setup-matt-pocock-skills` with local files (specs in `docs/`, index in `TASKS.md`; shared instructions in AGENTS.md), then `/grill-with-docs` and `/to-spec`. See DECISIONS.md 2026-10-14.

## Unresolved questions
- None. (Spec location and instruction placement were decided 2026-10-14; see DECISIONS.md.)
