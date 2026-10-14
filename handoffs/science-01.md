# ATLAS scientific review packet 01 (Start Here Step 8)

```text
TASK: S-08 / science-01
RECIPIENT: Gemini reviewer
ROLE: read-only scientific critique (no implementation, no code review)
SOURCE: branch main; base 6c06d5e; head = the local commit "Draft requirements and prepare scientific review" that adds this packet; no uncommitted patch
ACCESS: attached files only (listed below); no repository access
OBJECTIVE: challenge the draft evaluation design before the first implementation slice (T-01)
ACCEPTANCE: each returned finding is consequential, tied to one question below, and carries a counterexample or a proposed executable check
INVARIANTS: see "Fixed constraints"; do not propose a new product or judge code (none exists)
INPUTS: this packet; docs/SPEC.md; GLOSSARY.md
ACTUAL RESULTS: none. No application code, tests, fixtures or measurements exist (pytest collects 0 tests). Everything below is a proposal.
UNKNOWN: Nebius model availability; Docker isolation on this host; the real-data license and suitability; all effect sizes
REQUEST: at most five findings, format in "What to return"
WRITE OWNERSHIP: none (reviewer edits nothing; the lead records dispositions in DECISIONS.md)
```

## Attach exactly these files

1. `handoffs/science-01.md` (this packet)
2. `docs/SPEC.md` (contracts; read §3–§8, §10 and §14; §5 holds the draft evaluation policy table)
3. `GLOSSARY.md` (exact meanings of claim types, outcomes, coverage and lineage terms)

Do **not** attach credentials, `.env` files, the handoff documents, or any held-out material. No held-out cases exist yet. When they do, they are authored outside this repo and are never shared with the builder or this review.

## Brief

ATLAS (first capability: LENS) checks whether a small Python/scikit-learn tabular **classification** experiment's evaluation supports its stated deployment claim.
- It runs deterministic, evidence-producing checks on the project's own evaluation script.
- It reports one run outcome that summarizes those checks, never the truth of the science.
- A bounded NVIDIA model (via Nebius) may propose a revision of the evaluation script. The user approves it, and it runs in an isolated container and is re-checked.

Users: student researchers and small applied-ML teams. A lower score after correction can be the honest result. ATLAS is not a validity certificate.

## The six agreed decisions (Step 7)

1. **Claim types:** exactly one of `same_population`, `unseen_group`, `future_time`; combined unseen-group-plus-future-time claims are unsupported.
   - `same_population` means new observations from the declared sampling population, recorded with its sampling unit and dependence assumptions.
   - A random row split is conditionally appropriate there, never automatically valid. Declared duplicates, overlapping windows and temporal dependence are not waived.
   - An unsupported claim type gives a run-level `NOT_SUPPORTED`; missing evidence for a supported check gives a check-level `NOT_ASSESSED`.
2. **Run outcome:** `NOT_SUPPORTED`, `VIOLATION_FOUND`, `INCONCLUSIVE` or `NO_VIOLATION_FOUND`, derived from a versioned evaluation policy (never an agent-selected subset).
   - An ERROR elsewhere does not erase a valid FAIL.
   - Results that depend on failed or corrupt evidence are neither FAIL nor PASS.
   - Missing metadata never makes a required check "not applicable".
   - An empty assessed set never yields `NO_VIOLATION_FOUND`.
   - Robustness stays descriptive until a justified rule is predeclared.
3. **Adapter and provenance:** the project's own `evaluate.py` uses a small adapter and runs in the container. A trusted recorder wraps an **enumerated** set of scikit-learn operations, recording the rows and labels supplied to each fit and validating row lineage.
   - Lost or unverifiable lineage never PASSes.
   - Metrics are recomputed outside the candidate process.
   - Final-holdout labels never enter candidate mounts or prompts.
   - The recorder runs inside candidate Python, so it is **not tamper-proof**, and missing traces don't prove that no fits occurred.
4. **Revisions:** the model writes a diff limited to `evaluate.py`, which the user approves (approval bound to the candidate hash) and which runs only in isolation, at most twice per run.
   - Comparison modes: deterministic audit (detection only); agent without memory; agent with memory (same budgets, plus validated procedures as optional guidance).
   - Detection quality is compared across all three modes; repair success and token savings across the two agent modes.
5. **Demo:** a limited hosted demo (generated diffs "not executed here"; trusted corrected-protocol results labeled separately) plus a full local build.
6. **Held-out cases:** two (one flawed, one clean), authored and validated by Codex outside the repo.
   - Separation is procedural, not access-enforced.
   - The cases are frozen with hashes and versions, and evaluated in one predeclared campaign with all results reported.
   - This is limited descriptive evidence.

## Relevant evaluation design (drafts)

- **Checks:** split integrity; preprocessing fit provenance; independent metric and baseline; temporal availability; robustness (descriptive). Statuses: PASS / FAIL / NOT_ASSESSED / ERROR. Required assertions per claim type: SPEC §5. Outcome derivation: SPEC §6.
- **First slice (T-01), as drafted:**
  - checks only the `unseen_group` claim type;
  - implements split integrity (`no_row_overlap`, `no_exact_duplicate_across_partitions`, `no_group_overlap`) and fit provenance (`rows_subset_of_fold_train`, `coverage_complete`). The current draft also includes one identifier assertion from the metric check (`metric.prediction_ids_match_eval_ids`);
  - excludes independent recomputation, baselines, temporal checks and the conditional (R*) assertions;
  - **Fixtures:** a seeded synthetic faulty project, a clean project and unsupported cases.
- **Synthetic 2×2 benchmark:**
  - **Data:** subjects, sessions and correlated windows; a modest genuine class signal; subject/session confounding.
  - **Two separate planted defects:** a random-row split, and global supervised feature selection (`SelectKBest(f_classif)` fit on all rows before splitting).
  - **The four runs:** split (random/grouped) × preprocessing (global/fold-local).
  - **Labeling:** synthetic, never presented as biomedical data.
- **Transfer benchmark:** Variant A (compatible `unseen_group`, renamed schema) for reuse and the memory comparison; Variant B (`future_time` with a post-prediction feature) for refusal.
- **Clean control:** a grouped protocol with fold-local preprocessing and observed fit traces. Expected outcome `NO_VIOLATION_FOUND` within stated coverage.
- **Real data candidate:** UCI Human Activity Recognition Using Smartphones (license and suitability not yet checked). Its documentation describes precomputed features from sliding windows and subject IDs with a subject-based train/test partition. These details are to be verified at implementation.
- **Agent comparison:** three paired repetitions, randomized order, cache state recorded. Descriptive only.

## Review questions (prioritized)

**Q1. Recorder limits and the T-01 outcome policy (SPEC §4.3, §6).**
- (a) What can this instrumentation establish within its supported coverage, what bypasses or failures remain possible, and which executable negative tests should define its limits?

  Consider the `global` fit attribution rule, lineage checks on transforms, and labels supplied versus labels used. We are not asking for proof that arbitrary candidate code cannot bypass it.
- (b) T-01 implements only split integrity and fit provenance (plus, in the current draft, the prediction-ID assertion). Should its clean outcome be **explicitly scoped** to the implemented checks, or must it remain **`INCONCLUSIVE`** under the full required policy?

  SPEC §6 does not yet define how a required-but-unimplemented assertion is handled. The answer must not imply that unimplemented checks passed or weaken the full policy.

  Fact from the SPEC §5 table: the six drafted T-01 assertions are exactly the **unconditional** required assertions for `unseen_group`. The conditional (R*) ones, overlapping windows, temporal dependence and the reported-metric match, become required only when the claim declares that dependence or a reported metric. If T-01 were limited strictly to split integrity and fit provenance, `metric.prediction_ids_match_eval_ids` would be a required but unimplemented assertion.

**Q2. Factorial benchmark validity.** Can the planned 2×2 design attribute changes to the split defect versus the global supervised-selection defect without manufacturing an effect? Which non-accuracy evidence (fit traces, overlap counts) should carry the attribution? What disconfirming run would show the design is uninformative?
- *Unresolved thresholds:* number of subjects/sessions/windows; signal and confounding strengths; minimum groups and class coverage per fold; the predeclared seed set; whether any robustness (instability) rule should ever be required rather than descriptive, given correlated windows.

**Q3. Dependence and temporal semantics.**
- How should `split.no_overlapping_windows_across_partitions` and `split.temporal_dependence_respected` be defined under `same_population`?
- Should `split.no_group_overlap` ever be required under `same_population`?
- For `future_time`: what form of feature-availability metadata, gap and label-horizon rules, and what refusal criteria make Variant B's rejection correct rather than arbitrary?
- *Unresolved thresholds:* minimum gap between training and prediction times; label horizon; the window-overlap definition (any shared samples, or a declared fraction); minimum group and class floors for `unseen_group` feasibility ("stop and explain").

**Q4. UCI HAR protocol.** Which claim type, evaluation protocol and clean control are honest for this dataset? Which limitations must be stated (precomputed features, window construction, no session timestamps)? What would make it unsuitable?
- *Unresolved thresholds:* the robustness reporting granularity (per-subject results; seed count).

**Q5. Finding-level scoring and matched agent comparisons.**
- What is the unit of a "finding" for precision and recall against answer keys, and how are partial or duplicate findings matched?
- How are false positives on clean cases counted?
- Are three paired repetitions with randomized order, matched model settings and budgets, and procedure-creation cost reported separately adequate as **descriptive** evidence? What confounds remain (caching, warm starts, nondeterministic model output)?
- *Unresolved thresholds:* the tolerance for `metric.reported_matches_recomputed`; the repetition count; the matching rule for findings.

## Fixed constraints (do not reopen)

Scope (tabular classification, CPU scikit-learn, CSV/Parquet); the five checks and four statuses; the three claim types; the outcome names and rules above; isolation with no host fallback; immutable evaluator and labels; one NVIDIA runtime model; and honest labeling of synthetic data.

## What to return

At most **five consequential findings**, each with:
- the question ID;
- severity: BLOCKER (integrity or core validity), IMPORTANT or OPTIONAL;
- the exact assertion or design element it concerns;
- a counterexample **or** a proposed executable check (inputs, expected status or outcome);
- the smallest change;
- remaining uncertainty.

"No change needed" is a valid answer for a question. Do not propose a new product or judge code you cannot see.
