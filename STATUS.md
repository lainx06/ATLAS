# ATLAS status

WRITER: Claude Code
MODEL: Opus 5.5 (`claude-opus-5-5`), effort high
CURRENT STEP: Start Here Step 10 (T-04), **configuration preparation only**. The placeholder `.env` exists and is git-ignored; **waiting for the user to enter the Nebius Token Factory API key locally.** No API call made. T-01 accepted at `f5aa4dc`. GitHub setup complete (private `lainx06/atlas`). T-02 not started.
CHECKPOINT: `origin` = `https://github.com/lainx06/atlas.git` (**private**, published by the user via VS Code). `main` tracks `origin/main` at `35dbb63` (verified: `git ls-remote origin refs/heads/main` equals local HEAD; remote refs are only `HEAD` and `refs/heads/main`). This STATUS update is a local commit on top of `35dbb63` and is not pushed.
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

- **T-01 after repair pass 2 (self-tested; awaiting Codex verification):** deterministic audit of trusted synthetic fixtures (`benchmarks/t01/`).
  - `uv run --locked pytest tests/unit tests/integration -q` → 165 passed (exit 0) under policy-v1.2 (135 under v1.1; 115 at repair pass 2).
  - policy-v1.2 adds the required prerequisite `split.evaluation_folds_nonempty`; route B handles a shared unit/group column. Mutation check re-run (required set changed): baseline ALL PASS; m1/m2/m3 caught cleanly.
  - Repeated-measures repair (policy-v1.1): explicit sampling-unit and contained-group routes, same-fold witnesses, no inherited statuses. Mutation check re-run: baseline ALL PASS; m1/m2/m3 caught cleanly.
  - All-null repeated-measures fix: containment now requires positive evidence from known participating units. The mutation check was not re-run for this fix (no mutation target or script changed); its last run (repair pass 2) was clean.
  - `uv run --locked python scripts/mutation_check.py` → an unmutated temporary copy passes the full suite; m1/m2/m3 each caught with no unrelated runtime-origin failures (exit 0). The log is in `runs/mutation_check.log` (git-ignored). Repair pass 1's "3/3" had hidden an unrelated runtime-origin failure in every mutation run; that is now fixed and guarded.
  - Output integrity (every indexed output exists with a current hash; none unindexed): consistent for the s01/s02/s07 runs and two recovery paths (snapshot missing with hash-matching fallback → `INCONCLUSIVE`; unrecoverable manifest → `INCONCLUSIVE`).
  - CLI evidence (git-ignored `runs/`): `uv run --locked python -m atlas.cli audit benchmarks/t01/<s> --mode audit --runs-dir runs` →
    - s01 `VIOLATION_FOUND` (outcome.json sha256 `19a2e0c00f89bc9f…`, provenance `1db556338dca2e13…`; one origin, the global `SelectKBest` fit);
    - s02 `NO_VIOLATION_FOUND` (`b6f2ad49b5b4fe74…`, `ad32a07fc4f5180c…`);
    - s07 `INCONCLUSIVE` (`b0860af1b788ce61…`, `ad32a07fc4f5180c…`).
  - The runner capability is `trusted_pipeline_only`: inventory-allowlisted fixtures run in an isolated-mode host subprocess (import-controlled, **not a sandbox**). `runtime.json` shows `isolated=1`, `safe_path=true`, and that neither the fixture directory nor the cwd is on `sys.path`.
  - Codex review 1 and its verification: findings, traced causes, dispositions and tests are recorded once in TASKS.md (T-01 "REVIEW 1" and "CODEX VERIFICATION OF REPAIR PASS 1"). The reproductions are preserved unchanged at `runs/review-t01/` and `runs/review-t01-repair/`.

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
- **Nebius key (user action):** T-04 waits for the user to enter `NEBIUS_API_KEY` in the local `.env`.
- None for T-01 (accepted). The T-01 limitations are recorded in TASKS.md (T-01 "ACCEPTANCE").
- `/grill-with-docs` slash discovery/invocation: **unverified** (Step 7 followed the wrapper manually). `/to-spec`: **unverified** (not used; PRD/SPEC were synthesized directly, which Start Here Step 7 permits).
- Codex skill discovery: the `code-review-and-quality` skill was discovered through Codex's normal skill catalog during review 1 (reported by the user).
- Docker/isolation: not installed. Not needed until Step 10; blocks candidate-code execution.

## Nebius configuration (Step 10 preparation, 2026-10-14)
- **Contract:** `.env.example` and SPEC §11. The key goes in variable `NEBIUS_API_KEY`, in the git-ignored file `.env` at the repository root (loaded with `python-dotenv`). Base URL `NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/`. `ATLAS_MODEL_PRIMARY` stays a placeholder until an authenticated `GET /models` verifies an NVIDIA model ID. `ATLAS_MODEL_MODE=fixture` until live access is verified.
- **`.env`:** created from `.env.example` (byte-identical: placeholders only). `git check-ignore -v .env` → `.gitignore:2:.env`; it is not tracked and does not appear in `git status`. Its contents are never printed by the builder.
- **Key source (official docs, checked 2026-10-14):** a Nebius **Token Factory** API key, from https://tokenfactory.nebius.com/project/api-keys ("Create API key" → name → "Create"; shown once). Sent as `Authorization: Bearer <key>` to the base URL above. This is not a Nebius AI Cloud IAM service-account key.
- **Not done:** no API call, no model selection, no Docker.

## Publication readiness (pre-check 2026-10-14, for `lainx06/atlas`; published as a private repository)
- **State:** branch `main`; working tree clean apart from this acceptance record; **no remotes**.
- **Authors:** all 11 commits are authored and committed as `Adnan Hossain <adnan.hossain0802@gmail.com>`, the expected identity.
- **History scan:** every blob reachable from all refs (185 blobs, 11 commits) was checked.
  - No private-key blocks, cloud/GitHub/OpenAI/Slack/Google tokens, JWTs, or non-placeholder key/secret/token/password assignments.
  - No sensitive paths were ever committed (`.env*` other than `.env.example`, keys, local settings, `runs/`, `.dev/`, `.venv/`, caches, logs, raw data).
  - No blob is over 1 MB.
- **Ignore rules verified with `git check-ignore`:** `runs/` (including the preserved Codex review evidence), `.dev/` vendor clones, `.venv/`, `.env`/`.env.*`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/` and `.claude/settings.local.json` are all ignored, and none is tracked.
- **Publication blockers found:** none.
- **Non-blocking considerations for the user:**
  1. **Visibility and personal context:** `docs/handoff/ATLAS_Master_Prompt.md` describes the user's education and internship, home hardware, and family funding of the Claude plan; `docs/handoff/ATLAS_Build_Playbook.md` mentions the family funding and a public Devpost credit code. No secrets, but a public repository would publish them. `docs/handoff/` is read-only under AGENTS.md, so redaction would need the user's explicit exception.
  2. **Local paths:** absolute local Windows user paths appear in `DECISIONS.md` and `docs/TOOLING.md`.
  3. **No LICENSE or README yet:** both are planned for T-13. A public repository without a LICENSE is all-rights-reserved by default. The vendored skills carry their own MIT licenses.
  4. **Codex checkpoint ref:** a local ref `refs/codex/turn-diffs/checkpoints/…` points to a working-tree snapshot (a tree, not a commit), with no extra paths and fully covered by the scan. Push only `main`; don't use `git push --all` or `--mirror`.
  5. **Email visibility:** the commit email will be visible in public history. If GitHub's "block command line pushes that expose my email" setting is enabled, the push will be rejected until that is resolved.

## Next task
1. **User (private, local):** in VS Code, open `.env` at the repository root and replace `replace_with_local_secret` on the line `NEBIUS_API_KEY=replace_with_local_secret` with a Token Factory API key.
   - Create the key at https://tokenfactory.nebius.com/project/api-keys; it is shown only once.
   - Never paste the key into chat, commit it, or put it in any other file.
2. **Then T-04 (separate go-ahead):** create `scripts/nebius_smoke.py`, list models with an authenticated `GET /models`, make one capped structured-output call, and save sanitized evidence. The key is never printed. `ATLAS_MODEL_PRIMARY` is set only from a verified model ID.
3. Docker/isolation (T-05) and T-02 are not started.

## Unresolved questions
- Remaining gated questions, each with an owner and gate: docs/SPEC.md §14. These are the repeated-measures rule (before T-02 acceptance), the T-02 assertions, synthetic generator settings (before any benchmark measurement), UCI HAR containment evidence (T-09), scoring answer keys (before T-10/T-11 measurement), the frozen procedure-store hash (T-11), and hosting checks (T-03).
- Hosting/access checks before choosing a host or enabling paid usage: DECISIONS.md "Open hosting and access checks".
