# ATLAS

ATLAS is a coding agent that audits machine-learning evaluation code for leakage. Given a small scikit-learn classification project and the claim it makes ("the classifier works on people absent from training"), it runs executable evidence checks, and when it finds a violation it asks an NVIDIA Nemotron model to propose a bounded revision of the evaluation code. **The model proposes; a deterministic evaluator decides.** Every candidate runs only in an isolated Docker runner, after a typed human approval, and is judged by the same trusted evaluator that judged the original. A lower score can be the honest result.

<!-- Sources for this section: PROJECT_BRIEF.md; AGENTS.md "Scope" and "Isolation"; docs/SPEC.md §9, §11. -->

- Outcome codes are exactly `VIOLATION_FOUND`, `NO_VIOLATION_FOUND`, `INCONCLUSIVE` and `NOT_SUPPORTED`. `NO_VIOLATION_FOUND` means every required check passed within the coverage shown; it does not say the claim is true.
- Status: hosted demo built offline, **not deployed**; demo URL [TODO: source needed]. Public repository URL [TODO: source needed].

## Headline results

All figures come from the project's own records; none is a benchmark of detection rates.

### Live run 6: the first complete live end-to-end success (2026-10-18)

`VIOLATION_FOUND` -> Nemotron proposes a fix -> human approval -> Docker -> `NO_VIOLATION_FOUND`.

| | |
| --- | --- |
| Project | `benchmarks/t01/s01_faulty` (synthetic) |
| Original | `VIOLATION_FOUND` |
| Revision 1 (`new_source`) | approved by the user, executed in Docker, judged `NO_VIOLATION_FOUND` |
| Checks FAIL -> PASS | `split.no_group_overlap`, `split.sampling_unit_disjoint`, `split.repeated_measures_rule`, `fit.state_dependencies_within_fold_train` (4) |
| Balanced accuracy, pooled | original 0.68125, candidate 0.675 (descriptive only; never part of an outcome) |
| Run end state | `BUDGET_EXHAUSTED`: revision 2 was rejected by `validate_diff` (`syntax_error`) and attempt 5 hit the 2-revision limit |
| Requests / cost | 5 requests, 0 retries, 0 schema failures; estimated $0.0190884 (provider-reported usage at listed prices; **not billing**) |

Source: TASKS.md T-06 "LIVE RUN 6"; STATUS.md. The candidate scored *lower*: removing the leakage cost accuracy, which is the point.

The six live runs ended differently, and all are recorded: run 1 two proposals rejected, no candidate executed; run 2 `ERROR` (`not_json`); run 3 declined approval (`NEEDS_INPUT`); run 3b `ERROR` (`incomplete`); run 4 both candidates `INCONCLUSIVE` (`KeyError: 'subject_id'`); run 5 `ERROR` (`not_json`); run 6 success above. Estimated total live spend, runs 1 to 6: about $0.058 ($0.0580317; not billing). Source: STATUS.md.

### UCI HAR: real data, a flawed protocol against a clean control

Both projects are **ATLAS-authored** on the public UCI HAR data (21 training subjects, 7,352 windows; the official test partition is never read). Same model family, different protocols.

| Project | Protocol | Outcome | Balanced accuracy, mean over development folds |
| --- | --- | --- | --- |
| `har_flawed` | random row-level folds; scaler and selector fit on all rows | `VIOLATION_FOUND` | 0.906 |
| `har_clean` | subject-grouped folds; everything fit inside each fold | `NO_VIOLATION_FOUND` | 0.875 |

The 0.906 against 0.875 gap is a **descriptive** comparison of two protocols, not a causal decomposition. ATLAS recomputes the flawed project's metric from its own predictions, so the reported-metric check correctly passes there; the inflation shows only against the clean control. The clean control's `split.no_window_overlap` passes only through documented containment (conditional, not independently verified). Source: `docs/T09_CONTAINMENT.md` §2, §3, §6; DECISIONS.md "Lead decisions, 2026-10-17" item 7.

### Safety controls and their reviews

- Typed approval bound to the snapshot and code hashes; a wrong or truncated confirmation declines. Docker-only execution, no host fallback. The trusted evaluator, holdout labels and pass criteria are immutable to the agent (AGENTS.md; SPEC §9-§10).
- Reviews: Gates 1-3 PASS; Gate 4 FAIL (two P2), resolved by slices 4c-4h; combined review FAIL (three P2), re-verified and closed; T-06 accepted by the lead within its documented scope (`f059554`, on the code at `199a173`). The Codex security-and-spend review of the hosted build (T-12) is **pending**. Source: STATUS.md; TASKS.md T-06 "ACCEPTANCE".
- Suite at the T-12 build: 1485 passed, 1 skipped with Docker required (`runs/t12/full.log`, git-ignored).

## How ATLAS uses NVIDIA Nemotron on Nebius Token Factory

Model: `nvidia/nemotron-3-super-120b-a12b` (listed $0.30 / $0.90 per 1M input / output tokens, context 262,144), through the OpenAI-compatible Token Factory API at `https://api.tokenfactory.nebius.com/v1/`. Sources: DECISIONS.md "Initial model and response approach" and "T-06 slice 4 live-run decisions (lead)"; docs/SPEC.md §11.

- **Bounded loop.** At most 6 model requests, 12 tool operations, 2 candidate revisions, 5 active minutes per run, 30 s per candidate execution and a 60 s request timeout. Ceilings: 12,000 input tokens (an ATLAS estimate, not a guarantee) and 8,000 output tokens. No retry raises a cap.
- **Exact reply validation.** The model must return one raw JSON object (one action, no duplicate keys, no undeclared fields). Application-validated by strict Pydantic schemas, **not** provider-enforced structured output: no NVIDIA model on Nebius lists `json_mode` or `structured_outputs`. Reply text is never repaired or leniently parsed. Up to two consecutive schema failures get a corrective turn built from the schema and fixed text only, inside the 6-request budget.
- **Cost accounting.** Each request is reserved before it is sent; usage is validated before accounting; the run stops unsent if the next ceiling would pass the estimate cap of $0.0648 per run. At most $0.51 per run is authorized (the provider-enforced worst case, which ATLAS has not verified). Figures are estimates from provider-reported usage, **not billing**.
- **Pre-run model check.** Before any completion, one free authenticated `GET /models` must list the model with exactly the configured prices and context length, or the run aborts.
- **Roles.** The model reads files, runs checks through typed tools and proposes a revision (`diff` or complete `new_source`). `validate_diff` is the only gate for a proposal; the trusted evaluator is the only source of an outcome.

## Architecture

```mermaid
flowchart LR
    P[Project + manifest + claim] --> I[Intake]
    I --> C[Deterministic checks]
    C --> O1[Original outcome]
    C --> A[Agent loop: Nemotron proposes]
    A -->|propose_patch| V[validate_diff]
    V -->|passes| H[Typed human approval]
    H --> D[Docker runner: no network, non-root, read-only]
    D --> E[Trusted evaluator]
    E --> R[Report + hashed evidence]
    O1 --> R
```

Source: docs/SPEC.md §6, §9-§11; docs/T09_CONTAINMENT.md §5.

| Mode | Executes | Model | Labelled |
| --- | --- | --- | --- |
| Local build (full) | Original and every candidate in the isolated Docker runner after typed approval | live (CLI, explicit authorization) or fixture | LIVE or NON-LIVE banner |
| Limited hosted (built, **not deployed**) | Nothing from a project; the original's findings come from a recorded, hash-verified trusted run; proposals are "not executed here" | one capped live session per visitor session; kill switch off by default | disclosed replay, "not executed here" |
| Fixture | Same loop with scripted model replies | none | NON-LIVE |

Source: docs/SPEC.md §13; docs/HOSTED_OPERATIONS.md §1. The hosted caps are $3.00 public ($1.00 per UTC day), $5.00 judge, $0.0648 and 6 requests per session, enforced in Neon Postgres; they are tested only on a local PostgreSQL container so far.

## Setup and running

Requirements: Windows with Docker Desktop (tested with Engine 29.8.2 on Windows 11 only), [uv](https://docs.astral.sh/uv/), Python 3.11 (pinned by `.python-version`).

```powershell
uv sync --locked
copy .env.example .env      # then edit .env; it is git-ignored. Never commit real values.
```

`.env` keys (`.env.example`): `NEBIUS_API_KEY` (a Token Factory key; live runs only), `NEBIUS_BASE_URL`, `ATLAS_MODEL_PRIMARY` (a model ID confirmed by `GET /models`), `ATLAS_MODEL_MODE` (`fixture` or `live`; fixture runs are labelled NON-LIVE). The live entry point reads only the key from `.env`; its model ID and base URL are fixed in code (SPEC §11).

**Offline audit, no model, no Docker** (deterministic; trusted fixtures only, run on the host, not isolated):

```powershell
uv run --locked python -m atlas.cli audit benchmarks/t01/s01_faulty --mode audit --runs-dir runs
```

**Fixture agent demo (NON-LIVE; no key, no spend; Docker Desktop must be running):**

```powershell
$env:ATLAS_MODEL_MODE = 'fixture'
uv run --locked python -m atlas.cli audit benchmarks/t01/s01_faulty --mode agent --fixture-script demo/fixtures/revision.json
```

`demo/fixtures/revision.json` is a scripted list of model replies (NON-LIVE; see `demo/fixtures/README.md`). You type the first 12 characters of the code hash to approve the original and each candidate. The owner-observed run of this kind ended with the original `VIOLATION_FOUND` and four FAILs becoming PASS (STATUS.md "Next task").

**Live run (spends real, small amounts; needs your explicit decision each time):**

```powershell
$env:ATLAS_MODEL_MODE = 'live'
uv run --locked python -m atlas.cli audit benchmarks/t01/s01_faulty --mode agent --live --authorize-spend-usd 0.51
```

The CLI refuses unless `ATLAS_MODEL_MODE=live`, `--live` and the exact authorized amount are all given. The original and each candidate need a typed approval. (docs/SPEC.md §11.)

**Browser UI (Streamlit, local only):**

```powershell
$env:ATLAS_MODEL_MODE = 'fixture'
uv run --locked streamlit run app.py
```

Open http://localhost:8501. The walkthrough is `docs/UI_WALKTHROUGH.md`; "Open a recorded run" re-verifies every recorded hash before showing a run. To fetch the UCI HAR data yourself: `uv run --locked python benchmarks/real_sensor/retrieve.py` (downloads into a git-ignored folder and verifies checksums).

**Tests:**

```powershell
$env:ATLAS_REQUIRE_DOCKER = '1'
uv run --locked pytest tests -q -p no:cacheprovider
uv run --locked ruff check .
```

## Safety and honesty rules

- Candidate code runs only in a disposable restricted container (no network, non-root, read-only root, bounded CPU, memory and time). If isolation is unavailable ATLAS fails closed and never falls back to the host.
- No secrets in Git, prompts, fixtures or containers. The key goes only to the model client; the hosted page keeps it server-side.
- Unsupported or uninstrumented code is `NOT_ASSESSED`, never `PASS`. Metrics are descriptive and never part of an outcome. Model text, candidate output and raw replies are labelled untrusted and are never evidence.
- Fixture and replay are always labelled as such; synthetic data is labelled synthetic.

## Limitations

Copied from `docs/SPEC.md` §15 and the acceptance records; not softened.

- Fit provenance covers only the bounded supported path. The in-process recorder is not tamper-proof, fingerprints don't prove arbitrary preprocessing was observed, and missing traces don't prove absence.
- Provenance begins at the supplied feature table; upstream feature extraction and normalization are not verified.
- Policy cannot detect dependence the user did not declare. Some declared dependence has no supported rule in V1 and stays `NOT_ASSESSED`.
- Duplicate detection without source-observation identity is an exact-value screen and can leave unresolved candidates.
- Temporal assertions verify declared availability and separation rules, and `split.no_window_overlap` verifies declared stream identity and window intervals. None of them is proof of statistical independence.
- A green outcome means only that the listed assertions passed within the stated coverage.
- Held-out evidence comes from two cases: limited and descriptive. Their separation is procedural, not access-enforced.
- Container isolation reduces risk; it is not proof of safety, provenance integrity or scientific correctness.
- T-06 (the live agent) was accepted within its scope with these limitations: the input-token figure is an estimate and provider enforcement and billing are unverified; model format reliability varies (schema failures in 3 of 6 live runs); raw replies are stored only from live run 3b onward; candidate-output redaction is best-effort; tested on one Windows host only.
- The HAR containment declaration is documented, not verified; the upstream normalization's fit scope is not established; both HAR projects are ATLAS-authored and are not independent benchmark evidence (`docs/T09_CONTAINMENT.md` §9).
- Scope: small tabular classification, CPU scikit-learn, exactly three claim types (`same_population`, `unseen_group`, `future_time`); any other claim is `NOT_SUPPORTED`. No final-holdout label store exists yet.
- Not established for the hosted build: behavior on Neon, on Community Cloud or from the host; real-model behavior in hosted mode; the security-and-spend review (TASKS.md T-12 "RESULT").
- Procedures (saving and reusing evaluation procedures) were cut from V1 (DECISIONS.md "Lead decisions, 2026-10-17" item 2).

## License, data and acknowledgements

- Code: MIT, see `LICENSE` (2026 Adnan Hossain). Dependencies and vendored skills: `THIRD_PARTY_NOTICES.md`.
- **UCI HAR** data: Reyes-Ortiz, J., Anguita, D., Ghio, A., Oneto, L., & Parra, X. (2013). Human Activity Recognition Using Smartphones [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C54S4K. The dataset page grants **CC BY 4.0**; the archive's own 2012 `README.txt` adds "Any commercial use is prohibited." No data is redistributed here: the demo shows precomputed results only. Changes and attribution: `benchmarks/real_sensor/ATTRIBUTION.md`; `demo/README.md`.
- Built for the Nebius x NVIDIA Global AI Hackathon, Coding and Agentic Engineering track (PROJECT_BRIEF.md). Thanks to NVIDIA for the Nemotron open models and to Nebius for Token Factory. Agent skills by Matt Pocock and Addy Osmani (MIT) and Anthropic (Apache-2.0) are vendored as development tooling (`THIRD_PARTY_NOTICES.md`). Code review and verification by Codex; scientific review by Gemini (STATUS.md).
