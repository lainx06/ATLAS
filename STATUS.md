# ATLAS status

WRITER: Claude Code
MODEL: Opus 5.5 (`claude-opus-5-5`), effort high
CURRENT STEP: Start Here Step 8 prepared, not started. The review packet `handoffs/science-01.md` is ready for Gemini. docs/PRD.md and docs/SPEC.md are **pending scientific review**; the design is **not accepted**. No implementation.
CHECKPOINT: "Draft requirements and prepare scientific review" committed locally on `main` (parent `6c06d5e`). Not pushed; no remote configured.
LAST UPDATED: 2026-10-14

## What works (verified by running)
- Python 3.11 environment: uv-managed CPython 3.11.17 in `.venv/`, pinned by `.python-version`.
- Dependencies resolved and locked: `uv.lock` (61 packages). `uv lock --check` exit 0.
- Import check: `uv run --locked python scripts/check_imports.py` exit 0; numpy, pandas, sklearn, pydantic, streamlit, openai, dotenv, pytest, and atlas all import.
- Lint: `uv run --locked ruff check .` → "All checks passed!" (exit 0); `uv run --locked ruff format --check .` exit 0 (vendored skill trees excluded from ruff; see docs/TOOLING.md).
- `.gitignore` exclusions verified with `git check-ignore -v --no-index` for .env, .env.*, *.pem, secrets.toml, .venv/, __pycache__/, .pytest_cache/, .ruff_cache/, artifacts/, runs/, *.log, data/raw/, .dev/ (vendor clones), dist/, test-results/. Tracked files (.env.example, pyproject.toml, uv.lock, sources, docs) are not ignored.
- Skills (Step 6): 8 skills + 3 Addy shared references copied from pinned commits (matt `49dd158d`, addy `aeac41d4`) into `.claude/` and `.agents/`. `uv run --locked python scripts/sync_skills.py --check` → "32 files x 2 destinations; problems: 0", exit 0. Copies identical across roots and to upstream; relative reference paths resolve. Details and statuses: docs/TOOLING.md.
- Claude Code native discovery of the 5 model-invocable skills, and native loading of `code-review-and-quality` with its `../../references/security-checklist.md`: verified (the first attempt said `Unknown skill`; discovery caught up later in the same session, and one retry succeeded). No restart needed.
- `/setup-matt-pocock-skills`: invoked successfully by the user from the `/` menu (discovery + invocation verified). Configuration written and verified: `docs/agents/issue-tracker.md` (local files: specs in `docs/`; index and Section 24 task entries in `TASKS.md`; `handoffs/` only for Section 19 transfers), `docs/agents/domain.md` (single-context; ADR policy), `## Agent skills` block appended to AGENTS.md. Upstream skill files unchanged (`sync_skills.py --check` problems 0); ruff exit 0. Details: docs/TOOLING.md "Matt skill configuration".
- Step 7 interview: the `grill-with-docs` wrapper was followed manually (it arrived as pasted text, not a slash invocation); its companions `grilling` and `domain-modeling` loaded natively. Decisions Q1–Q6 are in DECISIONS.md. Documents are drafts, verified only for formatting (`ruff format --check .` exit 0) and internal references; nothing in them is implemented.

## What does not exist yet
- **No tests.** `uv run --locked pytest -q` → "no tests ran", exit 5. Nothing has been tested.
- No application code. `src/atlas/` holds only a package docstring. No `atlas` CLI entry point.
- Everything in docs/PRD.md and docs/SPEC.md is **planned, not implemented**: checks, adapter/recorder, policy, evaluator, runner, agent, procedures, UI, benchmarks, hosting.
- Planned paths not created yet, by design: `docs/specs/`. (`handoffs/` now exists, holding only the Step 8 packet.)
- No `.env` created and no API key requested or read.
- No Nebius call made. Docker is not on PATH (isolation not available; trusted fixtures only).

## Commands executed in setup
1. `git init -b main`
2. `uv python install 3.11` → installed cpython-3.11.17
3. `uv init --lib --name atlas --python 3.11 --vcs none --no-readme --managed-python`
4. `uv add numpy pandas scikit-learn pydantic streamlit openai python-dotenv`
5. `uv add --dev pytest ruff`
6. `uv lock --check`, `uv sync --locked`, import check, ruff check/format, pytest (results above)
7. `git check-ignore -v --no-index ...`, `git status --porcelain --untracked-files=all`
8. Step 6: `/setup-matt-pocock-skills` (user-invoked) → wrote docs/agents/*, AGENTS.md block; verified with `sync_skills.py --check`, path checks, ruff. Earlier: `git clone` both skill repos into `.dev/skill-sources/{matt,addy}`, `git rev-parse HEAD`; `uv run --locked python scripts/sync_skills.py` (install) and `--check`; `diff`/`sha256sum` comparisons; ruff check/format.

## Blockers
- `/grill-with-docs` slash discovery/invocation: **unverified** (Step 7 followed the wrapper manually). `/to-spec`: **unverified** (not used; PRD/SPEC were synthesized directly, which Start Here Step 7 permits).
- Codex discovery of `.agents/skills`: **unverified**, pending the Codex setup step.
- Docker/isolation: not installed. Not needed until Step 10; blocks candidate-code execution.

## Next task
1. User: open Gemini (Argon High), attach `handoffs/science-01.md`, `docs/SPEC.md` and `GLOSSARY.md`, and paste the Start Here Step 8 prompt. Return Gemini's exact findings to the lead.
2. The lead records an accepted/rejected/deferred disposition for each finding in DECISIONS.md. Claude then updates SPEC/PRD/TASKS (including T-01's scoped-versus-INCONCLUSIVE clean outcome) and clears the "pending scientific review" status only after that.
3. Then T-01 (first deterministic slice), blocked on S-08.

## Unresolved questions
- Scientific questions for Step 8: the five in `handoffs/science-01.md` (mirroring docs/SPEC.md §14, including the T-01 outcome-policy question). SPEC §6 does not yet define handling of required-but-unimplemented assertions.
- Hosting/access checks before choosing a host or enabling paid usage: DECISIONS.md "Open hosting and access checks".
