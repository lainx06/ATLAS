# ATLAS status

WRITER: Claude Code
MODEL: Opus 5.5 (`claude-opus-5-5`), effort high
CURRENT STEP: Start Here Step 9: T-01 implemented and self-tested; **awaiting local Codex review** (not independently reviewed). T-02 not started.
CHECKPOINT: base `35016bb`; head = local commit "Implement T-01 deterministic audit slice" (parent `35016bb`). Not pushed; no remote configured.
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
- Step 8: Gemini reviewed `handoffs/science-01.md` (preserved unchanged as the reviewed snapshot). The lead's dispositions are applied. Documentation and reference checks only; no tests exist.

- **T-01 (self-tested, not independently reviewed):** deterministic audit of trusted synthetic fixtures (`benchmarks/t01/`).
  - `uv run --locked pytest tests/unit tests/integration -q` → 83 passed (exit 0).
  - `uv run --locked python scripts/mutation_check.py` → 3/3 mutations caught (exit 0). The log is in `runs/mutation_check.log` (git-ignored).
  - CLI evidence (git-ignored `runs/`): `uv run --locked python -m atlas.cli audit benchmarks/t01/<s> --mode audit --runs-dir runs` →
    - s01 `VIOLATION_FOUND` (outcome.json sha256 `4fdc133f2ee69aff…`, provenance `479882ced75da766…`);
    - s02 `NO_VIOLATION_FOUND` (`983182ab388e4266…`, `a09d8c656dfe5dd3…`);
    - s07 `INCONCLUSIVE` (`86253ae739ae4423…`, `a09d8c656dfe5dd3…`).
  - The runner capability is `trusted_pipeline_only`: allowlisted fixtures in a host subprocess, with no isolation.

## What does not exist yet
- Not implemented: T-02 assertions (windows, temporal separation, `future_time`, reported-metric comparison, metric recomputation and baselines); `load_holdout_features()`; isolated runner (Docker); model calls and the agent loop; procedures; UI; hosting; real-data and held-out evaluation. These are materialized as NOT_ASSESSED `unimplemented_assertion` where policy requires them.
- No `atlas` console-script entry point (`python -m atlas.cli` only). No static analyzer for unadapted code.
- Planned paths not created yet, by design: `docs/specs/`. (`handoffs/` holds only the Step 8 packet.)
- No `.env` created and no API key requested or read.
- No independent review of T-01 yet.
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

9. T-01: TDD cycles with `uv run --locked pytest tests/unit/<file> -q` (RED then GREEN per module); `uv run --locked python benchmarks/t01/generate.py`; `uv run --locked python -m atlas.runner.trusted allowlist benchmarks/t01`; full suite; `scripts/mutation_check.py`; CLI audits of s01/s02/s07; ruff check/format; `sync_skills.py --check`.

## Blockers
- `/grill-with-docs` slash discovery/invocation: **unverified** (Step 7 followed the wrapper manually). `/to-spec`: **unverified** (not used; PRD/SPEC were synthesized directly, which Start Here Step 7 permits).
- Codex discovery of `.agents/skills`: **unverified**, pending the Codex setup step.
- Docker/isolation: not installed. Not needed until Step 10; blocks candidate-code execution.

## Next task
1. **Local Codex review of T-01** (Start Here Step 9): install/sign in to the Codex extension, then use the review prompt in the T-01 handoff. Record whether `.agents/skills` loaded and which review skill was used.
2. Claude repairs confirmed findings and reruns the affected checks. Do not start T-02 before the review disposition.

## Unresolved questions
- Remaining gated questions, each with an owner and gate: docs/SPEC.md §14. These are the repeated-measures rule (before T-02 acceptance), the T-02 assertions, synthetic generator settings (before any benchmark measurement), UCI HAR containment evidence (T-09), scoring answer keys (before T-10/T-11 measurement), the frozen procedure-store hash (T-11), and hosting checks (T-03).
- Hosting/access checks before choosing a host or enabling paid usage: DECISIONS.md "Open hosting and access checks".
