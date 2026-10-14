# ATLAS status

WRITER: Claude Code
MODEL: Opus 5.5 (`claude-opus-5-5`), effort high
CURRENT STEP: Start Here Step 9: Codex review 1 of T-01 found 7 issues; repair pass 1 is complete and self-tested. **Awaiting verification by the same Codex session**; T-01 is not accepted. T-02 not started.
CHECKPOINT: repair base `216f3ff` (T-01 implementation); head = local commit "Repair T-01 after Codex review" (parent `216f3ff`). Not pushed; no remote configured.
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

- **T-01 after repair pass 1 (self-tested; awaiting Codex verification):** deterministic audit of trusted synthetic fixtures (`benchmarks/t01/`).
  - `uv run --locked pytest tests/unit tests/integration -q` → 103 passed (exit 0): 83 previous plus 20 regression tests from Codex review 1.
  - `uv run --locked python scripts/mutation_check.py` → 3/3 mutations caught (exit 0). The log is in `runs/mutation_check.log` (git-ignored).
  - CLI evidence (git-ignored `runs/`): `uv run --locked python -m atlas.cli audit benchmarks/t01/<s> --mode audit --runs-dir runs` →
    - s01 `VIOLATION_FOUND` (outcome.json sha256 `42d1aed735c896c9…`, provenance `1db556338dca2e13…`; one origin, the global `SelectKBest` fit);
    - s02 `NO_VIOLATION_FOUND` (`c7b8f40acc9ab0a2…`, `ad32a07fc4f5180c…`);
    - s07 `INCONCLUSIVE` (`5b68a70e113d28be…`, `ad32a07fc4f5180c…`).
  - The runner capability is `trusted_pipeline_only`: inventory-allowlisted fixtures run in an isolated-mode host subprocess (import-controlled, **not a sandbox**). `runtime.json` shows `isolated=1`, `safe_path=true`, and that neither the fixture directory nor the cwd is on `sys.path`.
  - Codex review 1: findings, dispositions and tests are recorded once in TASKS.md (T-01 "REVIEW 1"). The reproductions are preserved at `runs/review-t01/`.

## What does not exist yet
- Not implemented: T-02 assertions (windows, temporal separation, `future_time`, reported-metric comparison, metric recomputation and baselines); `load_holdout_features()`; isolated runner (Docker); model calls and the agent loop; procedures; UI; hosting; real-data and held-out evaluation. These are materialized as NOT_ASSESSED `unimplemented_assertion` where policy requires them.
- No `atlas` console-script entry point (`python -m atlas.cli` only). No static analyzer for unadapted code.
- Planned paths not created yet, by design: `docs/specs/`. (`handoffs/` holds only the Step 8 packet.)
- No `.env` created and no API key requested or read.
- No completed independent verification of the T-01 repairs yet. T-01 is not accepted.
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
- Codex skill discovery: the `code-review-and-quality` skill was discovered through Codex's normal skill catalog during review 1 (reported by the user).
- Docker/isolation: not installed. Not needed until Step 10; blocks candidate-code execution.

## Next task
1. **The same local Codex session verifies repair pass 1:** the delta `216f3ff..` (the repair commit), the regression tests and the reproductions.
2. If verified, the lead records T-01 acceptance. Otherwise Claude repairs the confirmed findings; the same issue failing twice stops for diagnosis. Do not start T-02 before acceptance.

## Unresolved questions
- Remaining gated questions, each with an owner and gate: docs/SPEC.md §14. These are the repeated-measures rule (before T-02 acceptance), the T-02 assertions, synthetic generator settings (before any benchmark measurement), UCI HAR containment evidence (T-09), scoring answer keys (before T-10/T-11 measurement), the frozen procedure-store hash (T-11), and hosting checks (T-03).
- Hosting/access checks before choosing a host or enabling paid usage: DECISIONS.md "Open hosting and access checks".
