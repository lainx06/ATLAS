# ATLAS product requirements (V1, LENS)

Status: **pending scientific review** (Step 8 packet: `handoffs/science-01.md`). Step 7 draft, 2026-10-14. Fully specified for review; **not accepted** until Step 8 findings have dispositions (DECISIONS.md). Nothing described here is implemented yet; see "Planned versus working".

Sources: Revision 5 handoff (`docs/handoff/`), `PROJECT_BRIEF.md`, the Step 7 interview decisions Q1–Q6 in `DECISIONS.md`, and vocabulary in `GLOSSARY.md`. Technical contracts are in `docs/SPEC.md`.

## Problem statement

A student researcher or small applied-ML team reports a classification result and implies a deployment use, for example "this activity classifier works on people absent from training". Their evaluation code may not support that use. Rows from the same person can sit in both training and evaluation, or preprocessing can learn from evaluation rows. A future-prediction model can also see features that would not exist at prediction time. These problems are easy to miss, they inflate results, and reviewers rarely execute the code to find them.

## Solution

ATLAS is an Experimental Verification Workspace; LENS is its first capability. For a supported project, LENS:
1. turns a stated deployment claim into a confirmed, structured claim;
2. runs deterministic, evidence-producing checks against the project's actual execution;
3. reports one run outcome that summarizes those checks, never the truth of the science;
4. lets a bounded NVIDIA model propose a revision of the evaluation script, which the user approves and ATLAS executes in isolation and re-checks;
5. compares the original and revised protocols;
6. saves a reusable procedure only when its prerequisites and evidence are machine-verified, and refuses reuse when they don't hold.

A lower score after correction can be the honest result. ATLAS is not a universal validity certificate.

## Users

- **Primary:** a student researcher or small applied-ML team with a Python/scikit-learn tabular classification experiment and a concrete generalization claim.
- **Secondary:** a hackathon judge meeting the tool for the first time through the hosted demo or the local build.

## Supported scope (V1)

| Area | Supported | Outside V1 |
| --- | --- | --- |
| Claim types | Exactly one of `same_population`, `unseen_group`, `future_time` (GLOSSARY.md), recorded with its sampling unit and dependence assumptions | Combined unseen-group plus future-time claims; any other claim → run outcome `NOT_SUPPORTED` |
| Data | Small CSV/Parquet feature tables with explicit row-ID, target and declared metadata columns | Raw waveforms, images, text, arbitrary uploads, personal data |
| Code | A project `evaluate.py` using the ATLAS adapter and the enumerated supported operations (SPEC §4) | Arbitrary notebooks, deep learning, custom fitting outside supported operations (observable only as a coverage gap) |
| Models in projects | CPU scikit-learn classifiers on the supported list | GPU, training new models |
| Unadapted code | Static suspicions, shown separately; they never change statuses or outcomes | — |
| Runtime model | One verified NVIDIA model through Nebius Token Factory | Any non-NVIDIA runtime model; invented model IDs |

## Workflow

1. Select a curated example (hosted or local) or, in the local build, a supported local project.
2. State the deployment claim in plain words. The model pre-fills the structured claim; with no model, the user fills the form directly. The user confirms the claim type, sampling unit, dependence assumptions and metadata roles.
3. Run the checks and inspect the evidence.
4. Review a candidate revision of `evaluate.py`. In the local build, approve that exact candidate (approval is bound to its hash) to execute it in isolation.
5. Compare the original and revised protocols and their measured results.
6. Export the evidence report, and optionally save a procedure if admission succeeds.

## Outcomes the user sees

**Check statuses:** PASS, FAIL, NOT_ASSESSED, ERROR. Each comes with assertion, applicability, observed values, evidence, coverage and limitations.

**Run outcome:** one headline, derived mechanically by the versioned evaluation policy (DECISIONS.md Q2; SPEC §6). It is always shown with a plain-language label and its limitations:

| Outcome | Plain-language label (draft) |
| --- | --- |
| `NOT_SUPPORTED` | "ATLAS can't assess this claim or project in V1." |
| `VIOLATION_FOUND` | "The evaluation breaks at least one requirement of this claim." |
| `INCONCLUSIVE` | "No violation established, but required evidence is incomplete." |
| `NO_VIOLATION_FOUND` | "Every required check passed within the coverage shown." |

None of these says the scientific claim is true or false.

## User stories

1. As a researcher, I want to state my deployment claim in plain words and confirm a structured version, so that ATLAS checks the question I actually mean.
2. As a researcher, I want ATLAS to tell me when my claim type is outside V1, so that I don't mistake silence for approval.
3. As a researcher, I want to declare my sampling unit and dependence assumptions, so that a random row split is judged in context rather than accepted or rejected automatically.
4. As a researcher making a `same_population` claim, I want known duplicates and overlapping windows still checked, so that choosing that claim doesn't hide a dependence problem.
5. As a researcher making an `unseen_group` claim, I want ATLAS to show whether any group appears in both training and evaluation, so that I know whether my result says anything about new groups.
6. As a researcher making a `future_time` claim, I want ATLAS to show whether any feature was unavailable at prediction time, so that I don't report a result that relies on the future.
7. As a researcher, I want to see which rows and labels each supported fit operation received, so that I can tell whether preprocessing learned from evaluation rows.
8. As a researcher, I want "labels supplied" kept separate from "labels used by a supervised component", so that I'm not accused of leakage that didn't happen.
9. As a researcher, I want fits ATLAS couldn't attribute to rows reported as coverage gaps (NOT_ASSESSED), so that missing evidence never looks like a pass.
10. As a researcher, I want my metrics recomputed independently from predictions keyed by row ID, so that a reporting error can't hide in my own scoring code.
11. As a researcher, I want a dummy baseline (and a simple linear one where it makes sense), so that I can judge my number in context.
12. As a researcher, I want variation across predeclared seeds and groups shown descriptively, so that I see instability without a false significance claim.
13. As a researcher, I want one run outcome with a plain-language label and its limitations, so that I understand the result at a glance without over-reading it.
14. As a researcher, I want an ERROR in one check shown alongside a valid finding from another, so that neither hides the other.
15. As a researcher, I want static suspicions about unadapted code clearly separated from evidence, so that I know which statements were observed.
16. As a researcher, I want the model to propose a revision of my evaluation script as a readable diff, so that I can see exactly what would change.
17. As a researcher, I want to approve one exact candidate before it runs, and have a changed candidate need fresh approval, so that nothing executes without my consent.
18. As a researcher, I want candidates to run only in an isolated environment, so that generated code can't touch my machine or credentials.
19. As a researcher, I want to be told plainly when isolation is unavailable and nothing will execute, so that I don't mistake a displayed diff for a tested one.
20. As a researcher, I want the original and revised protocols compared side by side with matching evaluation context, so that I can attribute the change in results.
21. As a researcher, I want at most two revision attempts per run, so that cost and time stay bounded.
22. As a researcher, I want to save a procedure only after its prerequisites and evidence are verified, so that reuse is trustworthy.
23. As a researcher, I want ATLAS to reuse a saved procedure on a compatible project only after re-checking prerequisites and re-running assertions, so that reuse is justified rather than assumed.
24. As a researcher, I want ATLAS to refuse an inapplicable procedure and name the failed prerequisite, so that similar-looking projects don't inherit the wrong protocol.
25. As a researcher, I want to export a report that cites evidence artifacts, versions and limitations, so that others can check my result.
26. As a judge, I want to try curated examples in a hosted demo without paying or installing anything, so that I can evaluate the project easily.
27. As a judge, I want the hosted demo to mark generated diffs "not executed here" and label the trusted corrected-protocol results separately, so that I'm not misled about what ran.
28. As a judge, I want any replay clearly disclosed, so that I never mistake a recording for a live model call.
29. As a judge, I want a reserved judging path that public traffic can't exhaust, so that the demo works when I try it.
30. As a judge, I want to see the actual model identity, timings and call counts for a run, so that the NVIDIA runtime use is verifiable.
31. As a maintainer, I want every quoted metric to be regenerable from the release, so that the submission's claims are reproducible.
32. As a maintainer, I want held-out results reported from one predeclared campaign, including failures, so that the evaluation isn't cherry-picked.

## Benchmarks and evaluation requirements

All of these are planned and none exists yet. Scientific details go to the Step 8 review.

- **Sensor generalization (synthetic, seeded):** subjects, sessions, correlated windows, a modest genuine signal and subject/session confounding. Two separate planted defects: a random-row split, and global supervised feature selection observed via the fit trace. A 2×2 factorial run (split × preprocessing) attributes the changes. Labeled synthetic; never presented as biomedical data.
- **Procedure transfer (synthetic):** Variant A (compatible `unseen_group`, renamed schema) for reuse and the memory comparison; Variant B (`future_time` with a post-prediction feature) for refusal. No token-savings claim from an early-exit mismatch.
- **Clean control:** an `unseen_group` project with a grouped protocol and fold-local preprocessing with observed traces. Expected outcome `NO_VIOLATION_FOUND` with limitations visible, and no fabricated violation.
- **Real data:** a licensed public sensor dataset with subject metadata. UCI HAR is the candidate, pending license and suitability checks (S14). Subject IDs and the original split metadata are preserved, limitations documented, and no invented timestamps.
- **Held-out cases (Q6):** two (one flawed, one clean), authored and validated by Codex outside this repo. They are frozen with recorded hashes, versions and date, and evaluated in one predeclared campaign with all results reported. This is limited descriptive evidence.
- **Three-way comparison (Q4):**
  - Modes: deterministic audit (detection/reporting baseline, no repair), agent without memory, and agent with memory (same workflow and budgets, plus access to validated procedures).
  - Detection quality is compared across all three modes; repair success and token savings only between the two agent modes.
  - Retrieval and prerequisite checking count toward the memory mode's budget, and procedure-creation cost is reported separately.
  - A three-repetition paired pilot is descriptive, not statistical proof.
- **Metrics:** supported-finding precision/recall on labeled cases, false positives on clean cases, unsupported-case handling, patch validity, task completion, tool calls, returned tokens, wall-clock time, retries, and cost estimates once prices are verified.
- **Performance target (proposed):** under 10 s numerical evaluation per sensor example after environment startup, excluding model latency. Measured on the actual machine.

## Demo and access requirements (Q5)

- **Baseline:** a limited hosted demo plus a full local build. Full hosted execution via a separately isolated worker is evaluated at the early hosting probe and adopted only if isolation, cost, reliability and delivery time are demonstrated.
- **Hosted:**
  - curated examples only;
  - live capped NVIDIA calls through server-side keys;
  - generated diffs marked "not executed here";
  - trusted corrected-protocol results labeled separately, never presented as validating the displayed patch.
- **Local build:** the full workflow, including approval-bound isolated execution. The video identifies which environment each segment shows.
- **Judge access:**
  - server-side cost controls;
  - a reserved judge route or capacity;
  - defined budget-exhaustion and restoration behavior through Dec 15, 2026;
  - replay only as a disclosed fallback.
- **Budget:** $30 inference and $20 hosting are planning allowances, not purchase authorization. The open checks are listed in DECISIONS.md.

## Release-level acceptance criteria

Each criterion needs executed evidence; reviewer approval doesn't substitute for it.

1. The faulty sensor example ends `VIOLATION_FOUND`, with findings that cite fit traces and split evidence. The clean control ends `NO_VIOLATION_FOUND` with stated coverage. An adapter-violating project yields NOT_ASSESSED checks and `INCONCLUSIVE`. An unsupported claim yields `NOT_SUPPORTED`.
2. A candidate revision executes only in isolation after hash-bound approval, and the evaluator re-checks it. Tampering attempts (evaluator paths, labels, policy, path escapes) are rejected by tests.
3. A real NVIDIA model call through Nebius is visible in a run, with model ID, usage and timings logged.
4. Procedure reuse succeeds on Variant A and is refused on Variant B, naming the failed prerequisite.
5. The three-way comparison and the held-out campaign are reported as measured, including failures and limitations.
6. Browser scenarios (playbook §20) pass against the actual running build: faulty, clean, unsupported, provider failure, procedure refusal, and rerun/duplicate-action.
7. A fresh install runs the documented offline example, and every quoted metric regenerates from the release.

## Planned versus working (2026-10-14)

| Capability | State |
| --- | --- |
| Python 3.11 environment, locked dependencies, import check | Working (STATUS.md) |
| Development skills | Installed; see docs/TOOLING.md |
| Everything in this PRD (checks, adapter, runner, agent, procedures, UI, benchmarks, hosting) | **Planned, not implemented** |
| Nebius access, Docker isolation | Not verified (Step 10) |

## Out of scope

Hardware, voice, custom OS, sEMG acquisition, deep learning, raw-signal processing, arbitrary notebooks or uploads, autonomous package installation, arbitrary cloud shell, unrelated integrations, causal validity, "all leakage" detection, combined claim types, and statistical significance claims from small pilots.

## Further notes

- Dual-model routing is a measured optimization after the single-model path works.
- If progress slips, cut routing and extras before weakening correctness or release evidence (playbook §12).
- Open scientific questions are listed in docs/SPEC.md §14 and DECISIONS.md.
