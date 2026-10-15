# ATLAS status

WRITER: Claude Code
MODEL: Opus 5.5 (`claude-opus-5-5`), effort high
CURRENT STEP: Start Here Step 11. **T-03 hosting probe: research and local design done (2026-10-15); not accepted, because feasibility evidence is missing** (`docs/HOSTING_PROBE.md`; TASKS.md T-03 "RESULT"). T-01, T-02, T-04 and T-05 are accepted.
- **T-02 (policy-v1.3, manifest schema 0.3):** **accepted by the lead at `75a98f4` within its documented trusted-fixture scope (2026-10-15)**. The decision rests on Codex's final verification (`runs/t02-verification-final/review.md`) and the earlier independent verification records. Record: TASKS.md T-02 "ACCEPTANCE".
  - **Path to acceptance:**
    - implemented at `487664e`;
    - Codex review 1 found four P2s, verified fixed at `0cf955d` (pass 1);
    - split-evidence decoding was verified at `bb9bac8` (pass 2);
    - provenance and index decoding (pass 3) were verified at `3bc38ff`;
    - the wrong-shape checks (pass 4) and split structure plus fit `input_status` presence (pass 5) were verified at `75a98f4`.
  - **Latest independent verification (at `75a98f4`):** 51 focused tests passed, 24 deselected. Codex also reran copied consumer-shape, referential and compatibility probes, all exit 0. That was a focused run: the full suite was **not** rerun at this commit. The last full unit + integration run was 534 passed, 1 skipped, at repair pass 1.
  - **Scope:**
    - the T-02 window, separation, temporal and reported-metric rules, plus descriptive recomputation, baselines and class support;
    - trusted synthetic fixtures (`benchmarks/t01/`, `benchmarks/t02/`), with the declared clock, cutoff and containment semantics;
    - the supported provenance path, and evidence that is structurally checked for the fields the evaluator reads.
  - **Limitations (not covered):**
    - not proof of statistical independence;
    - cutoffs and folds are declared by the evaluated code;
    - documented containment is not verified (UCI HAR is T-09);
    - times are compared as float64;
    - no final-holdout label store;
    - splitter requirements are unavailable, and the linear baseline is deferred;
    - performance at large scale is untested;
    - very long manifest numbers give a position-only diagnostic;
    - the adapter accepts duplicate fold names (the metrics refuse them);
    - structural checks are bounded to consumed fields;
    - no Docker-runner integration (T-06).
  - **Evidence:** the restoration incident stays recorded as overwritten and reconstructed (Codex's wording, TASKS.md). All other review evidence is preserved.
- **T-04 (Nebius):** **Credits (user-reported, 2026-10-15): an additional $25 Token Factory award, so $50 in total has been awarded.** The remaining balance and the expiry are not verified, and spending authorization is unchanged (no new calls). Earlier, the user reported the first $25 promo credits available and the key is in `.env` (checked set and non-placeholder; value never printed). **T-04 accepted by the user within its documented smoke-test scope** (2026-10-14; TASKS.md T-04 "RESULT"). Model `nvidia/nemotron-3-super-120b-a12b` (DECISIONS.md "Initial model and response approach"; `ATLAS_MODEL_PRIMARY` set in the local `.env`). Responses use prompt-requested JSON with strict Pydantic validation: application-validated, not provider-enforced. Two capped smoke calls (2026-10-15 UTC), both successful; see "Nebius smoke".
- **T-05:** **accepted by the lead at `eed73ee` within its documented scope (2026-10-15)**, based on Codex's independent verification of repair pass 2. Record: TASKS.md T-05 "CODEX VERIFICATION OF REPAIR PASS 2" and "ACCEPTANCE".
  - Codex verified both remaining parser findings (PAX padding, JSON encoding) fixed, with no remaining parser blocker. Its contract run: 28/28 with Docker required; 13 containers, all with removal confirmed. Unit tests: 261 passed, 1 skipped, after the path retry below.
  - **P3 Windows path length (pre-existing; documented, not fixed):** Codex's first unit run failed one test. A valid 150-character file name reached a 260-character absolute path under its longer temporary directory, and `open(target, "xb")` raised `FileNotFoundError`. The unchanged suite passed with a shorter temporary directory (253 characters). In a live run this would end `collection_failed`/`write_failed`, which is not a false success.
  - Limitations not covered by acceptance:
    - stable, trusted host directories (the intermediate-directory race);
    - the narrow archive format and Python 3.11.17 `tarfile` assumptions;
    - programmatic approval only;
    - candidate-produced provenance;
    - unknown physical cleanup when Docker APIs fail;
    - Windows path length;
    - tested only on this host.
  - **Pending T-06:** candidate re-evaluation, and `audit.py` accepting Docker execution records. Audits stay `trusted_pipeline_only` until then.
  - All review evidence is preserved unchanged under `runs/review-t05/` (`session-f494c95-20261015/`, `repair1-44c5a84/`, `repair2-eed73ee/`).
- T-01 accepted at `f5aa4dc`. GitHub setup complete (private `lainx06/atlas`). **T-03: research done, not accepted.**
- **Learning guide:** `docs/ATLAS_Learning_Guide.md` is the canonical guide (tracked since `44c5a84`; maintenance rule in AGENTS.md "Learning guide"). It marks T-02 accepted at `75a98f4` within its documented scope; explains the decoding and structure boundaries; corrects the overstated aggregate-completeness claim (duplicate fold names had defeated it);
  - explains the four review findings as beginner lessons;
  - adds a beginner section, "Time, windows and honest metrics": label availability, half-open windows, local versus global clocks, documented versus verified containment, incomplete aggregates, and floating-point boundaries.

  The untracked copy at the repository root is the user's and is left alone.
CHECKPOINT: `origin` = `https://github.com/lainx06/atlas.git` (**private**, published by the user via VS Code). `origin/main` is at `35dbb63` (verified earlier with `git ls-remote`). Local `main` is ahead by unpushed commits (`f2660f2`, `ddb84fa`, `ddde27e` (T-04), `f494c95` (T-05), `2e58280` (T-05 repair pass 1), `44c5a84` (learning guide), `eed73ee` (T-05 repair pass 2), `52c99c8` (T-05 acceptance), `487664e` (T-02), `0cf955d` (T-02 repair pass 1), `bb9bac8` (T-02 repair pass 2), `5af1b6e` (T-02 repair pass 3), `3bc38ff` (T-02 repair pass 4), `75a98f4` (T-02 repair pass 5), and the T-02 acceptance commit containing this update). Nothing is pushed.
LAST UPDATED: 2026-10-15

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

- **T-01 (accepted at `f5aa4dc`; the results below are from its repair pass 2):** deterministic audit of trusted synthetic fixtures (`benchmarks/t01/`).
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
- T-02 is accepted (`75a98f4`) within its trusted-fixture scope. The adapter still accepts duplicate fold names; only the metric checks refuse them. The linear baseline is deferred; splitter minimum requirements are not recorded.
- Not implemented: `load_holdout_features()` and the evaluator-only holdout label store (`final_holdout` reported metrics are NOT_ASSESSED); candidate re-evaluation of the required set after isolated execution (T-06); model calls and the agent loop; procedures; UI; hosting; real-data and held-out evaluation. Under policy-v1.3 every required assertion is implemented.
- No `atlas` console-script entry point (`python -m atlas.cli` only). No static analyzer for unadapted code.
- `docs/specs/` holds one spec, `t02-contract.md`. `handoffs/` holds only the Step 8 packet.
- Exactly two Nebius inference requests made (text smoke, JSON-validation smoke). No provider-enforced structured output is available or used. No production model client, schemas or agent loop (T-06); diagnosis, tool-use and repair quality untested.
- The Docker runner is accepted (T-05) but not integrated: `audit.py` still accepts only trusted-runner records, so audits remain `trusted_pipeline_only` until T-06. No user-facing candidate approval step exists yet. Output writes have no Windows extended-length path handling (T-05 P3).

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
10. T-05: `docker pull python:3.11-slim`; `uv run --locked python scripts/runner_requirements.py`; `uv run --locked python -m atlas.runner.docker build`; the new offline unit tests; `ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_runner_contract.py` (28 passed); the T-01 suite once (165 passed); ruff.
11. T-05 repair pass 1 (2026-10-15):
    - the new regression tests, first against `f494c95` (25 failed) and then after the repair;
    - `uv run --locked pytest tests/unit -q` (219 passed, 1 skipped);
    - the four intake-dependent T-01 integration files (67 passed);
    - `ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_runner_contract.py` (28 passed);
    - scratch copies of Codex's probes;
    - ruff.
12. T-05 repair pass 2 (2026-10-15):
    - the new regression tests, first against `44c5a84` (31 failed) and then after the repair;
    - `uv run --locked pytest tests/unit -q` (261 passed, 1 skipped);
    - `ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_runner_contract.py` (28 passed);
    - copies of Codex's `parser_disagreement.py` and `lifecycle_matrix.py`;
    - the differential parser fuzz, 4 seeds (0 problems);
    - ruff.
13. T-02 (2026-10-15):
    - `uv run --locked python benchmarks/t02/generate.py` (byte-identical regeneration);
    - `uv run --locked python -m atlas.runner.trusted allowlist benchmarks/t01 benchmarks/t02` (T-01 entries unchanged; 5 added);
    - `uv run --locked pytest tests/unit tests/integration --deselect tests/integration/test_runner_contract.py` (500 passed, 1 skipped);
    - `ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_runner_contract.py` (28 passed);
    - `uv run --locked python runs/t02/probe_mutations.py` (10/10 defects caught);
    - ruff.
14. T-02 repair pass 1 (2026-10-15):
    - the new regressions against a `git archive` copy of `487664e` (31 failed, 3 passed);
    - `uv run --locked pytest tests/unit tests/integration -q --ignore=tests/integration/test_runner_contract.py --basetemp=runs/t02r/f` (534 passed, 1 skipped);
    - copies of Codex's `probe.py` and `evaluate_probes.py` in `runs/t02r/probes/`;
    - ruff.
15. T-02 repair pass 2 (2026-10-15):
    - the new regression against a `git archive` copy of `0cf955d` (4 failed);
    - the audit and evidence-error suites: T-01 scenarios, both T-01 review suites, T-02 scenarios, CLI and policy (108 passed);
    - a copy of Codex's `json5000_runtime` case in `runs/t02r2/`;
    - ruff.
16. T-02 repair pass 3 (2026-10-15):
    - the new regressions against a `git archive` copy of `bb9bac8` (5 failed);
    - the evidence-error and recovery suites (113 passed);
    - an unchanged copy of Codex's `decoder_probes.py` (initial and siblings);
    - `runs/t02r3/shape_probe.py` (report only);
    - ruff.
17. T-02 repair pass 4 (2026-10-15):
    - the new wrong-shape regressions against a `git archive` copy of `5af1b6e` (15 failed, 1 passed);
    - the decoding, shape and recovery suites (206 passed);
    - copies of `shape_probe.py` and Codex's `decoder_probes.py` in `runs/t02r4/`;
    - ruff.
18. T-02 repair pass 5 (2026-10-15):
    - pre-repair hash manifests saved in `runs/t02r5/preservation/`;
    - the new regressions against a `git archive` copy of `3bc38ff` (17 failed, 5 controls passed);
    - the evidence-error and recovery suites (228 passed);
    - copies of Codex's `consumer_shapes.py` and a report-only `referential_probe.py` in `runs/t02r5/`;
    - ruff.
19. T-03 research (2026-10-15): public documentation read (Streamlit, Hugging Face, Nebius); `hosting_probe/cost_calc.py`; the stub's 4 local AppTest tests (`uv run --locked python -m pytest hosting_probe/test_stub.py`); ruff. No deployment, account, secret or API call.

## Blockers
- **Nebius:** none. $50 in Token Factory credits awarded in total (user-reported; balance and expiry not verified), key set, text and JSON-validation smoke calls succeeded.
- **Docker isolation (T-05):** none. Accepted at `eed73ee`.
- None for T-01 (accepted). The T-01 limitations are recorded in TASKS.md (T-01 "ACCEPTANCE").
- **T-02:** none. Accepted at `75a98f4`.
- `/grill-with-docs` slash discovery/invocation: **unverified** (Step 7 followed the wrapper manually). `/to-spec`: **unverified** (not used; PRD/SPEC were synthesized directly, which Start Here Step 7 permits).
- Codex skill discovery: the `code-review-and-quality` skill was discovered through Codex's normal skill catalog during review 1 (reported by the user).

## Nebius configuration (Step 10 preparation, 2026-10-14)
- **Contract:** `.env.example` and SPEC §11. The key goes in variable `NEBIUS_API_KEY`, in the git-ignored file `.env` at the repository root (loaded with `python-dotenv`). Base URL `NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/`. `ATLAS_MODEL_PRIMARY=nvidia/nemotron-3-super-120b-a12b` in the local `.env` (verified by `GET /models`; set 2026-10-14 by a one-line in-place edit that left the key and the other 3 settings unchanged, checked by value/hash comparison without printing). `ATLAS_MODEL_MODE=fixture` until the T-06 client exists.
- **`.env`:** created from `.env.example` (byte-identical: placeholders only). `git check-ignore -v .env` → `.gitignore:2:.env`; it is not tracked and does not appear in `git status`. Its contents are never printed by the builder.
- **Key source (official docs, checked 2026-10-14):** a Nebius **Token Factory** API key, from https://tokenfactory.nebius.com/project/api-keys ("Create API key" → name → "Create"; shown once). Sent as `Authorization: Bearer <key>` to the base URL above. This is not a Nebius AI Cloud IAM service-account key.
- **Done since:** model list, model selection and two smoke calls (below).

## Nebius smoke (prepared 2026-10-14; two calls run 2026-10-15 UTC)
- **Key:** `NEBIUS_API_KEY` present in `.env`, not the placeholder, no stray whitespace/quotes (checked with `dotenv_values`; value not printed).
- **`GET /models?verbose=true`** (free; HTTP 200, request ID `c96ab955d91408a5fd680317da6e5d0e`): 25 models; NVIDIA: `nvidia/nemotron-3-super-120b-a12b`, `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/Nemotron-3_5-Lightning`, `nvidia/Nemotron-3-Ultra-550b-a55b`. Archived as `runs/nebius_smoke/models-verbose-20261014.json` (git-ignored; checked free of the key).
- **Initial model (decided; DECISIONS.md):** `nvidia/nemotron-3-super-120b-a12b`: $0.30 / $0.90 per 1M input / output tokens, $0 per request, context 262,144, 200k TPM / 300 RPM, features `tools`, `reasoning`.
- **No NVIDIA model lists `json_mode` or `structured_outputs`** in `supported_features` (other models do). T-04's "structured-output call" and SPEC §11 need prompt-instructed JSON + Pydantic validation (or tools); decided: prompt-requested JSON + strict Pydantic validation (DECISIONS.md "Initial model and response approach").
- **Output limit:** the Nebius API reference documents `max_completion_tokens` as "an upper bound for the number of tokens that can be generated for a completion, including visible output tokens and reasoning tokens"; its `max_tokens` text does not say. The script sends only `max_completion_tokens=1024`.
- **Bound:** 512-token prompt ceiling × $0.30/M + 1,024 × $0.90/M = **$0.001075** (limit $0.01). It relies on the server honoring the documented cap; the script verifies `usage` afterwards.
- **Script:** `uv run --locked python scripts/nebius_smoke.py [--test text|json]` = dry run (free price re-check, prints request and bound; ran, exit 0). `--execute` sends one `POST /chat/completions` (`max_retries=0`, 60 s timeout, `n=1`, no stream, no tools, no loop) and saves sanitized evidence to `runs/nebius_smoke/`.
- **Text result** (`--execute`, run once, exit 0; evidence `runs/nebius_smoke/call-20261015T023151Z.json`, git-ignored): HTTP 200, request ID `21e9f6c61d8e720ca44abebf1ea374ea`, 0.703 s, 0 retries. Model `nvidia/nemotron-3-super-120b-a12b`, finish `stop`, content `"\n\nATLAS smoke OK"` (the exact text after two leading newlines). Usage: prompt 32, completion 47 (of which reasoning 39), total 79. Cost from listed prices: **$0.0000519**. Within caps (32 ≤ 512, 47 ≤ 1,024). Reasoning tokens are counted inside `completion_tokens`, so they are billed at the output rate and fall under `max_completion_tokens`.
- **JSON-validation result** (`--execute --test json`, run once, exit 0; evidence `runs/nebius_smoke/json-20261015T023413Z.json`, git-ignored):
  - Request: the prompt asks for exactly `{"project":"ATLAS","status":"ok"}` with no Markdown. No `response_format` and no tools are sent; the other caps are the same as the text test (bound $0.001075; prices re-checked live first).
  - Validation: strict Pydantic `SmokeReply` (`project: Literal["ATLAS"]`, `status: Literal["ok"]`, `extra="forbid"`, `strict=True`) over the whole content after stripping surrounding whitespace only; no extraction from prose, no repair. Checked offline first against 12 good/bad replies (fences, prose, extra field, wrong case, missing field, truncated, array, empty, `None`): all classified as intended.
  - Response: HTTP 200, request ID `e09ff0092fd1ad16e93c4412490a4247`, 0.687 s, 0 retries; model `nvidia/nemotron-3-super-120b-a12b`; finish `stop`; content `"\n\n{\"project\":\"ATLAS\",\"status\":\"ok\"}"`. **Validation passed.**
  - Usage: prompt 47, completion 52 (of which reasoning 38), total 99. Cost from listed prices **$0.0000609**. Within caps.
  - **Classification: application-validated output, not provider-enforced structured output.** Nothing on the provider side constrained the format; one passing call does not show the model always complies.

## Docker installation (complete; the restricted runner (T-05) was accepted at `eed73ee` after two repairs and Codex's verification)
**Reported by the user** (observed earlier; not re-run by the builder):
- WSL 3.0.3.0, default version 2.
- Docker Desktop 4.95.0, Engine 29.8.2.
- Context `desktop-linux`; server `linux/amd64`; `docker info` reported `linux`.
- `docker run --rm hello-world` succeeded.

**Builder read-only checks (2026-10-14; nothing installed, started or changed):**
- `wsl --version` → WSL 3.0.3.0. `wsl -l -v` → `docker-desktop`, version 2.
- Docker Desktop is a **per-user install** at `%LOCALAPPDATA%\Programs\DockerDesktop`. Its `resources\bin` is on the **user** PATH, but not on the PATH of a shell that started before the install (this Claude Code session); the full path works. T-05 must resolve the CLI explicitly or require a fresh shell.
- `docker version` → client and server 29.8.2, API 1.56, `linux/amd64`. `docker context show` → `desktop-linux`.
- `docker info` → `OSType=linux`, kernel `6.18.54.1-microsoft-standard-WSL2`, cgroup v2, 16 CPUs, ~16.3 GB memory for the VM, security options `seccomp` (builtin profile) and `cgroupns`, default runtime `runc`.
- Local images: only `hello-world:latest`; no containers.

**Installation evidence only.** Per Start Here Step 10, hello-world does not show isolation. The T-05 contract tests do; see TASKS.md T-05 "RESULT". Building the runner image requires the per-user Docker bin directory on the CLI's PATH, for `docker-credential-desktop`. The runner adds it automatically.

**Superseded:** the pre-install check of 2026-10-14 (Docker and WSL absent; Windows 11 Home; the open question about Home support) is preserved in git history at `ddde27e`. The OS, RAM and virtualization facts still hold: Windows 11 Home 25H2 build 26200.9457, 31.2 GB RAM, AMD SVM enabled.

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
1. **T-03 hosting probe:** stage A (canary only; no Nebius request; no key) is prepared locally and awaiting the owner's manual steps: create `lainx06/atlas-hosting-probe`, add the two files from `hosting_probe/stage_a/`, deploy on Streamlit Community Cloud, add a `CANARY` secret. The probe is kept until a sleep/wake observation is recorded. T-03 is not accepted. Credit facts: Nebius Builder terms say credits expire 90 days after issuance, but the user's issue dates, balance and expiry are unverified; payment information is already on the account and billing is unchanged, so the balance is not a hard ceiling. Details: `docs/HOSTING_PROBE.md`; DECISIONS.md "Hosting probe decisions".
2. T-06 (bounded live agent loop): its inputs T-02, T-04 and T-05 are accepted, but it waits until T-03 is done. No further Nebius calls are planned before T-06.

## Unresolved questions
- Remaining gated questions, each with an owner and gate: docs/SPEC.md §14. T-02's assertions are closed (accepted at `75a98f4`). The remaining items are synthetic generator settings (before any benchmark measurement), UCI HAR containment evidence (T-09), scoring answer keys (before T-10/T-11 measurement), the frozen procedure-store hash (T-11), and hosting checks (T-03).
- Hosting/access checks before choosing a host or enabling paid usage: DECISIONS.md "Open hosting and access checks".
