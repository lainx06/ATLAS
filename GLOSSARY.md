# ATLAS

ATLAS checks whether a small machine-learning experiment's evaluation supports the use its author claims for it. LENS is its first capability.

## Claims

**Deployment claim**:
The stated use an experiment's evaluation is meant to justify, expressed as exactly one claim type plus its declared sampling unit and dependence assumptions.
_Avoid_: goal, hypothesis, use case

**Claim type**:
The category of generalization a deployment claim asserts. V1 has three: same_population, unseen_group, future_time.

**same_population**:
A claim about new observations drawn from the declared sampling population, with no claim of generalization to unseen groups or future time. A random row split is conditionally appropriate under it, never automatically valid: known duplicates, overlapping windows, and temporal dependence still count against it.
_Avoid_: same people, same sessions, i.i.d. claim

**unseen_group**:
A claim about groups (for example, subjects or machines) absent from the training data.
_Avoid_: new users, cross-subject (informally)

**future_time**:
A claim about predictions made later than the data used for training, using only features available at prediction time.
_Avoid_: forecasting (informally), temporal claim

**Sampling unit**:
The unit that the deployment claim treats as an independent draw (for example, a row, a session, or a subject).

**Dependence assumption**:
A declared relationship between observations that can break independence, such as repeated measurements of one subject, overlapping windows, or ordering in time.

## Outcomes

**Run outcome**:
The single headline of a run, summarizing its evaluation checks against the confirmed deployment claim. It states nothing about whether the underlying scientific claim is true.
_Avoid_: verdict, validity, score

**VIOLATION_FOUND**:
A run outcome: at least one applicable required assertion has a valid, evidence-backed FAIL.
_Avoid_: contradicted, invalid, leaky

**INCONCLUSIVE**:
A run outcome: no violation is established, but required evidence or assessment is incomplete.

**NO_VIOLATION_FOUND**:
A run outcome: every applicable required assertion passed within explicitly stated coverage.
_Avoid_: valid, supported, clean bill of health

**Required assertion**:
An assertion that the versioned evaluation policy requires for a given claim type.
_Avoid_: selected check, chosen test

**Evaluation policy**:
The versioned, trusted rule set that defines which assertions are required for each claim type and how they combine into a run outcome.
_Avoid_: rubric, config

**Coverage**:
The portion of a project's execution and data that a check actually observed.

**NOT_SUPPORTED**:
A run-level outcome: the claim type or project falls outside V1's supported scope, so ATLAS makes no judgment about it.
_Avoid_: unsupported check, N/A

**NOT_ASSESSED**:
A check-level status: the check applies to a supported claim, but the evidence needed to decide it is missing or uninstrumented.
_Avoid_: skipped, unknown, pass-by-default

## Projects and evidence

**Supported project**:
A project that supplies a table, a manifest, and an evaluation script using the ATLAS adapter, within the enumerated supported operations.
_Avoid_: compatible repo, any sklearn project

**Supported operation**:
An estimator, transformer, or adapter operation on ATLAS's enumerated, tested list, for which row identity and fit inputs can be recorded.

**Lineage**:
The verified correspondence between rows of the original table and the rows an operation received or produced.
_Avoid_: index, row order

**Fit trace**:
The record of which rows, and whether labels, were supplied to a supported fit operation.
_Avoid_: log, provenance (when a single record is meant)

**Labels supplied / labels used**:
Labels supplied were passed to a fit operation; labels used were demonstrably consumed by a known supervised component. Supplied does not imply used.

**Static suspicion**:
A pattern noticed by reading code without observing its execution. It never changes a check status or run outcome.
_Avoid_: finding, violation

**Development evaluation**:
Evaluation on labeled data the project and its revisions may see and iterate on.
_Avoid_: test set (ambiguous)

**Final holdout**:
Data whose labels are held only by the trusted evaluator and never reach candidate code, mounts, or model prompts.
_Avoid_: test set (ambiguous), validation set

## Revisions and memory

**Candidate**:
A proposed revision of a project's evaluation script, identified by its content hash.
_Avoid_: fix, patch (when the hashed artifact is meant)

**Approval**:
The user's explicit consent to execute one exact candidate in isolation, bound to that candidate's hash.
_Avoid_: confirmation, sign-off

**Procedure**:
A saved, validated evaluation workflow with machine-checked prerequisites, offered to the agent as optional guidance.
_Avoid_: skill, memory (as a noun for one record), template

**Reuse**:
Applying a procedure after its prerequisites are re-checked and its assertions re-executed on the new project. A fresh repair attempt after a rejected reuse is not reuse.

**Audit mode**:
The deterministic, model-free mode that detects and reports but never repairs.

## Held-out evaluation

**Held-out case**:
A frozen project, authored and validated independently of the builder, whose contents, answer key and case-specific feedback the builder never receives before the final evaluation.
_Avoid_: test case, benchmark (for this specific meaning)

**Evaluation campaign**:
One predeclared run of the held-out evaluation (protocol, model settings, budgets, repetitions and failure handling fixed in advance), with every scheduled result reported.
_Avoid_: final run, attempt

**Retired case**:
A held-out case whose specific findings guided fixes or prompt changes. It no longer supports an untouched-holdout claim.

