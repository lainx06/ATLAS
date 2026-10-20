# Devpost draft (T-13, first draft)

Paste-ready sections for the Devpost fields. Every figure comes from a repository file; the source is in a comment under each section. Anything the records do not contain is marked `[TODO: source needed]`. Nothing here has been submitted or published. Track: Coding and Agentic Engineering (PROJECT_BRIEF.md).

## Project description

<!-- Sources: PROJECT_BRIEF.md; README.md; STATUS.md; TASKS.md T-06 "LIVE RUN 6"; docs/T09_CONTAINMENT.md §2, §6; docs/EVALUATION.md "Results (live, 2026-10-19)" (T-11; claims reviewed by Gemini). -->

**What it is.** ATLAS is a coding agent that audits machine-learning evaluation code for leakage. You give it a small scikit-learn classification project and the claim it makes, for example "the activity classifier works on people absent from training". ATLAS runs executable evidence checks (split integrity, preprocessing fit provenance, independent metric recomputation). If it finds a violation, an NVIDIA Nemotron model proposes a bounded revision of the evaluation code. The revision runs only in an isolated Docker runner, after a typed human approval, and the same trusted evaluator that judged the original judges it. The model proposes; a deterministic evaluator decides.

**Why.** A leaky evaluation inflates a reported score, and the person who wrote it usually cannot see why. A lower score can be the honest result, so ATLAS never counts a rising metric as success: outcomes come only from the trusted evaluator (`VIOLATION_FOUND`, `NO_VIOLATION_FOUND`, `INCONCLUSIVE`, `NOT_SUPPORTED`), and `NO_VIOLATION_FOUND` means every required check passed within the coverage shown, not that the claim is true.

**How, and what we measured.**

- **Live run 6** (2026-10-18, the first complete live end-to-end success): the original was `VIOLATION_FOUND`; Nemotron proposed a full-source revision; the user approved it; it ran in Docker; the trusted evaluator judged it `NO_VIOLATION_FOUND`. Four checks went FAIL -> PASS (`split.no_group_overlap`, `split.sampling_unit_disjoint`, `split.repeated_measures_rule`, `fit.state_dependencies_within_fold_train`). Pooled balanced accuracy went from 0.68125 to 0.675: descriptive only, and lower, as honest correction can be. 5 requests, 0 schema failures, estimated cost $0.0190884 (provider-reported usage at listed prices, not billing).
- **Real data, UCI HAR:** two ATLAS-authored projects on the public data. The flawed one (random row-level folds, global scaler and selector fit) is `VIOLATION_FOUND` with balanced accuracy 0.906; the clean control (subject-grouped folds, fit inside each fold) is `NO_VIOLATION_FOUND` at 0.875. The gap is a descriptive protocol comparison, not a causal claim.
- **Agent against model alone (T-11; development cases, not held-out):** on our four development cases, on which ATLAS's checks were built, Nemotron alone reading the same files named 19 of 23 predeclared violations (19 of 20 on the 8 ATLAS-assessable), with 2 false positives and 3 of 12 replies invalid; the flawed projects' own files describe their flaws in plain text, which may have helped it. ATLAS's deterministic audit (evaluated once per case) found all 8 assessable violations with no false positive and left one NOT_ASSESSED. What ATLAS adds here is evidence you can re-run and fixes verified by execution, not seeing more.
- **Safety by design:** Docker-only execution with no host fallback, typed approval bound to hashes, a trusted evaluator the agent cannot edit, exact reply validation, a 6-request budget, and spending enforced before every request.

**Honest limits.** Fit provenance covers only the bounded supported path; the recorder is not tamper-proof; declared containment (as on HAR) is documented, not verified; container isolation reduces risk and is not proof of safety. Full list: README.md "Limitations".

## Built with

<!-- Sources: PROJECT_BRIEF.md "Stack"; pyproject.toml; docs/HOSTED_OPERATIONS.md; STATUS.md "Docker installation". -->

- NVIDIA Nemotron (`nvidia/nemotron-3-super-120b-a12b`) served through Nebius Token Factory
- Python 3.11, uv, numpy, pandas, scikit-learn, Pydantic (strict reply schemas)
- the OpenAI Python SDK (OpenAI-compatible client pointed at Token Factory)
- Docker (isolated runner: no network, non-root, read-only root filesystem)
- Streamlit (local UI and the limited hosted page), Neon Postgres via psycopg (server-side budget store), Streamlit Community Cloud (the limited hosted page: deployed on Streamlit Community Cloud and smoke-tested on both routes (2026-10-19); public at submission)
- pytest, Playwright (browser tests), Ruff
- UCI HAR dataset (CC BY 4.0, non-commercial note; precomputed results only)

## How Nemotron and Token Factory are used

<!-- Sources: DECISIONS.md "Initial model and response approach", "T-06 slice 4 live-run decisions (lead)", "Lead decisions, 2026-10-17" items 10-14; docs/SPEC.md §11; STATUS.md "Nebius smoke". -->

Nemotron is the agent's reasoning step, called through the OpenAI-compatible Token Factory endpoint (`https://api.tokenfactory.nebius.com/v1/`).

- **What the model does.** In a bounded loop it chooses one typed action per reply: list the project's files (`list_project_files`), read one project file (`read_project_file`), inspect the original's recorded evidence for one check family (`inspect_evidence`: split integrity, fit provenance, independent metrics or temporal availability), propose a revision of the entry point (`propose_patch`: a unified `diff` or the complete `new_source`, with a rationale), or finish (`finish`, with a summary). ATLAS itself runs the deterministic checks before any model request and, after a typed human approval, executes an accepted revision in Docker and re-evaluates it; the model can do neither.
- **Exact reply validation.** The prompt requests one raw JSON object; ATLAS validates the whole reply with strict Pydantic schemas (one action, no duplicate keys, no undeclared fields). No NVIDIA model on Nebius lists `json_mode` or `structured_outputs`, so this is application-validated, not provider-enforced. Replies are never repaired. Up to two consecutive schema failures get a corrective turn built from the schema and fixed text only.
- **Bounds.** At most 6 requests, 12 tool operations, 2 revisions, 60 s per request, 12,000 input tokens (an ATLAS estimate) and 8,000 output tokens. Estimate cap $0.0648 per run; $0.51 maximum authorized per live run.
- **Cost accounting.** Each request is reserved before it is sent, settled at provider-reported usage, and held at its ceiling if usage is unknown. Totals are labelled estimates, not billing. Total estimated live spend, runs 1 to 6, the T-11 comparison and the hosted smoke test: about $0.133 ($0.1333011; not billing).
- **Pre-run model check.** One free authenticated `GET /models` must list the model with exactly the configured prices and context length, or the run aborts before any completion.
- **Authority.** A model proposal passes only `validate_diff`, then a typed human approval, then Docker execution, then the trusted evaluator. The model never decides an outcome.

## Challenges and learnings

<!-- Sources: TASKS.md T-06 "LIVE RUN 1" to "LIVE RUN 6" and "SLICE 4c" to "SLICE 4h RESULT"; DECISIONS.md "Lead decisions, 2026-10-17" items 4, 10-15; STATUS.md; docs/EVALUATION.md "Results (live, 2026-10-19)". -->

We ran the live agent six times (run 3 was declined at the approval prompt and retried as run 3b). Each failure was recorded as measured, and each fix was a small, reviewed change. We never made the evaluator more lenient to get a pass.

| Run | What happened | What the fix changed |
| --- | --- | --- |
| 1 (2026-10-17) | The original was `VIOLATION_FOUND`; 5 of 6 requests; both proposals were rejected by `validate_diff`, with no recorded reasons. Codex's Gate 4 review failed it: `comparison.model` was hardcoded to "none" in a LIVE report, and rejected proposals vanished from the report. | Slice 4c: `propose_patch` takes a full `new_source` (ATLAS builds the diff), every proposal is recorded with its outcome and a bounded reason, and the report names the live model. |
| 2 | `ERROR`, `schema_failure: not_json` on attempt 2 (1,606 completion tokens). The cause could not be known: raw replies were not stored. | Slice 4d: raw replies stored (untrusted, never evidence), one corrective turn inside the 6-request budget, a stricter prompt with a valid example. |
| 3 / 3b | Run 3: the user typed the wrong confirmation, so the original's approval was declined (`NEEDS_INPUT`, $0). Run 3b: attempt 2 added an undeclared `rationale`; attempt 3 hit the 8,000-token output limit with no content (`incomplete`). | Slice 4e: an optional bounded `rationale` on every action; an empty length-limited reply gets the corrective turn; one prompt sentence asking for brief reasoning. |
| 4 | The first live loop with candidates executed: both approved and run in Docker, both `INCONCLUSIVE`. Each read `X['subject_id']`, which `adapter.load_table()` does not return. The model never saw the traceback. | Slice 4f: a bounded, sanitized, untrusted error summary goes back to the model, plus a fixed adapter reference in the system prompt. |
| 5 | `ERROR`: an undeclared `summary` field, then a trailing comma (`not_json`), two failures in a row. | Slice 4g: up to two corrective turns, built from the schema and fixed text, never quoting the reply. |
| 6 | Success: revision 1 `NO_VIOLATION_FOUND`, four checks FAIL -> PASS. Revision 2 was a `syntax_error`, and the run ended `BUDGET_EXHAUSTED` instead of finishing after the success. | Slice 4h: one fixed finish-after-success line and a recorded-run viewer that re-verifies every hash and never re-executes. |

Learnings:

- **Schema failures were the main obstacle.** Format failures ended 3 of 6 live runs (2, 3b, 5). Storing raw replies was what let us diagnose them; before that, run 2's cause was unknowable.
- **Show the model its own errors.** Run 4's two candidates failed identically because the traceback never reached the model.
- **Review caught real reporting defects.** Gate 4 (two P2) and a combined review (three P2: a host-path redaction bypass, a missing approval regression test, a CRLF-sensitive byte-exact test) were each fixed and re-verified. T-06 was then accepted within its documented scope.
- **A capable model finds most flaws by reading.** Our predeclared comparison showed Nemotron alone close to ATLAS on detection for our four development cases (not held-out; ATLAS's checks were built on them, and the flawed projects' own files describe their flaws in plain text). We report it as measured; what the deterministic layer adds is evidence you can re-run (deterministic by design (evaluated once per case here)), no false positive in this comparison, and fixes verified by execution.
- **A rising metric is not the goal.** In run 6, after the four violations were removed, the pooled balanced accuracy was lower (0.68125 → 0.675); the difference is descriptive and is not attributed to a single cause.
- **Guardrails shaped the design.** Because the model is untrusted, the hosted demo never executes project code: it replays hash-verified recorded runs and shows live proposals as "not executed here".

## What was significantly updated during the submission period

<!-- Sources: the user's statement (2026-10-18); git log --reverse (first commit 7a0f155, 2026-10-14); THIRD_PARTY_NOTICES.md. -->

ATLAS was started and built entirely during the submission period. No ATLAS code, data or documents existed before the repository's first commit (`7a0f155`, 2026-10-14, "Initial project setup"); every later commit is part of the event work. Used unmodified and predating the event: the open-source Python dependencies, the vendored agent skills (pinned upstream commits, `THIRD_PARTY_NOTICES.md`), the public UCI HAR dataset (not redistributed) and the NVIDIA Nemotron model, called through Nebius Token Factory.

## Testing instructions (for the Devpost field)

- Hosted demo: [TODO: demo URL]. Recorded runs work without any code; every recorded hash is re-verified before a result is shown.
- Live session: judges enter the private access code (given only in Devpost's private judging field, never here) to use the separate judge budget; each session makes at most 6 model requests, is capped at $0.0648 and never executes code on the host (proposals are marked "not executed here").
- If the page says the app has gone to sleep, click the wake button and wait about 30 seconds; if the tab keeps spinning, refresh with Ctrl+Shift+R.
- Full workflow (Docker execution of the original and candidates, typed approval): run locally as described in README.md "Setup and running".

## What's next

<!-- Sources: STATUS.md "Next task"; TASKS.md T-12 "ACCEPTANCE", T-10; DECISIONS.md "T-11 re-scope and T-10 (lead, 2026-10-19)"; DECISIONS.md "Lead decisions, 2026-10-17" items 2, 13; docs/HOSTED_OPERATIONS.md §9. -->

- Publish the limited hosted demo: it passed Codex's security-and-spend review (two reviews with fault injection, all findings fixed and re-verified) and is deployed on Streamlit Community Cloud and smoke-tested on both routes (2026-10-19); public at submission. The remaining steps each need their own approval: make the app public, a signed-out check, live sessions switched on through the judging period, and the demo URL here.
- Held-out cases authored outside the builder's view (T-10, cut for the submission), so detection claims rest on more than development cases.
- An evaluator-only final-holdout label store, so `final_holdout` reported metrics can be assessed rather than `NOT_ASSESSED`.
- Native tool calling for the model, held in reserve because it changes the decided request contract and needs its own decision and review.
- Testing beyond one Windows host.

## Token Factory and Nemotron feedback (for the "Most Valuable Feedback" prize)

<!-- Sources: STATUS.md "Nebius smoke" and "Nebius configuration"; TASKS.md T-06 live runs 1-6, Gate 3 (runs/g3w, g3x, g3y); DECISIONS.md "Initial model and response approach"; docs/SPEC.md §11. All observations are from our own records on one model, one project and six runs; they are not general claims. Provider spend figures are our estimates, not billing. -->

What worked well:

- **The free `GET /models?verbose=true`** returned price, context length, rate limits and `supported_features` for each model, which made an exact pre-run check possible (model present, prices and context length equal to configuration). It returned HTTP 200 in our checks.
- **Prompt-requested JSON worked** when the model complied: both smoke calls passed strict validation, and live run 6 had 0 schema failures over 5 requests.
- **Low cost.** Run 6 cost an estimated $0.0190884; the six runs, the T-11 comparison and the hosted smoke test about $0.133 in total (not billing).

Specific observations and suggestions:

1. **Reasoning tokens count inside `completion_tokens` and can consume the whole output cap with no content.** In the smoke calls, 39 of 47 and 38 of 52 completion tokens were reasoning. In live run 3b, attempt 3 ended with finish reason `length` at the 8,000-token cap and returned no content, which ended the run. The API reference documents `max_completion_tokens` as covering visible output and reasoning tokens, but its `max_tokens` text does not say. *Suggestion:* document this for `max_tokens` too, expose reasoning tokens as a separate `usage` field, and offer a reasoning-effort or reasoning-budget parameter so callers can reserve room for the visible answer. We send no such parameter today (the request body is `model`, `messages`, `max_completion_tokens`, `n`), so we could only ask for "brief reasoning" in the prompt.
2. **JSON-format reliability without provider-enforced structured output.** No NVIDIA model in the listing advertises `json_mode` or `structured_outputs` (other models do). We validate in the application, and format failures ended 3 of 6 live runs: a `not_json` reply of 1,606 completion tokens (run 2), an undeclared field then an empty length-limited reply (run 3b), and an undeclared field then a trailing comma (run 5). *Suggestion:* support constrained decoding or `response_format` for the Nemotron models, or document which models support it and why not these.
3. **The listing's price-string format.** In the listing, prices are per-token decimal strings (`0.0000003` and `0.0000009`, nine characters each) while the context length is an integer; humans quote the same prices per million tokens ($0.30 / $0.90). We parse them as exact decimals and abort if a listed price differs from configuration, and our review stage range-checks exponent-style strings such as `1E+31` from the decimal's digits and exponent before any formatting; a zero with a large exponent (`0E+200`) is still rejected, failing closed, as a recorded known limitation (DECISIONS.md "Gate 3 re-verification dispositions (lead, 2026-10-17)"). *Suggestion:* state the unit and the allowed string forms in the API reference, and consider also returning a per-million field.
4. **Request IDs and served-model reporting were useful, and we depend on them.** `GET /models` and completions returned request IDs, and replies report the served model and usage; we log them (only after checking they are plain identifiers that do not contain the key) so a spend or behavior question can be traced to a request. *Suggestion:* keep both stable and documented (the request-ID location and the served-model field), so audit trails like ours stay reliable.
5. **Usage in error responses.** Our client validates usage on replies and on errors alike and treats a dispatched request with unknown usage as held at its ceiling. A documented guarantee about usage and billing for timeouts and failed requests would let callers release that hold sooner. We have not verified provider-side enforcement of `max_completion_tokens` or billing, and say so.

Everything above is reproducible from the run records named in TASKS.md T-06 (git-ignored `runs/live1` to `runs/live6`; the recorded bundle `demo/recorded/live6/`).
