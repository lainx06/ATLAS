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
A check-level status: the check applies to a supported claim, but it could not be decided. It always carries a specific reason, such as an unimplemented assertion, missing metadata, or unknown ancestry.
_Avoid_: skipped, unknown, pass-by-default

## Projects and evidence

**Supported project**:
A project that supplies a table, a manifest, and an evaluation script using the ATLAS adapter, within the enumerated supported operations.
_Avoid_: compatible repo, any sklearn project

**Supported operation**:
An estimator, transformer, or adapter operation on ATLAS's enumerated, tested list, for which identity, ancestry, and fitted-state dependencies can be recorded.

**Supported path**:
The bounded route from adapter-loaded data, through supported operations and supported row selection, to recorded predictions. Only this route can provide complete coverage.
_Avoid_: pipeline (when the observed route is meant)

**Row identity**:
Which rows of the supplied table a piece of data corresponds to. A valid row index establishes row identity, not ancestry.
_Avoid_: lineage (when only identity is meant)

**Ancestry**:
The recorded chain of supported operations and inputs that produced a piece of data. Data without recorded ancestry is untraced, even if its row identity is valid.
_Avoid_: provenance (loosely), history

**Lineage**:
The verified correspondence between the rows an operation received and the rows it produced.
_Avoid_: index, row order

**Fitted state**:
What a supported operation learned in one fit. Each new fit creates a new version.
_Avoid_: model (for transformers), weights

**State dependency**:
The set of training rows that contributed to a fitted state, directly or through fitted states upstream of its input.
_Avoid_: fit rows (when upstream contributions are meant)

**Use event**:
One application of a fitted state (a transform or a prediction) within a fold. Contamination is judged where a state is used, not where it was fitted.

**Coverage gap**:
Any part of the evaluated path that ATLAS could not trace: unexplained mutation, reconstructed data, an unsupported operation, or missing prediction ancestry. It yields NOT_ASSESSED, never PASS.
_Avoid_: minor gap, warning

**Labels supplied / labels used**:
Labels supplied were passed to a fit operation; labels used were demonstrably consumed by a known supervised component. Supplied does not imply used.

**Source observation**:
The real-world measurement a row records. Two rows share a source observation only when declared identity or documented duplication evidence says so.
_Avoid_: duplicate row

**Duplicate candidate**:
A pair of rows with identical feature and target values. Equality alone does not establish a shared source observation.
_Avoid_: duplicate, leaked row

**Source stream**:
The continuous recording that windows are cut from. Windows can overlap only within the same stream, and stream identity is never guessed.

**Window interval**:
A window's span as a half-open interval [start, end). Two windows overlap when they share a positive span in the same stream.

**Containment evidence**:
Documented or table-derived evidence that every instance of one unit (for example, a stream or a repeated-measures unit) lies within a single group.

**Separation rule**:
A declared minimum separation in time between training and evaluation data. Checking it verifies the rule, not statistical independence.
_Avoid_: independence test

**Class support**:
The classes present in each fold's partitions. Missing class support is reported; it is not a split violation.

**Static suspicion**:
A pattern noticed by reading code without observing its execution. It never changes a check status or run outcome.
_Avoid_: finding, violation

**Development evaluation**:
Evaluation on labeled data the project and its revisions may see and iterate on.
_Avoid_: test set (ambiguous)

**Final holdout**:
Data whose labels are held only by the trusted evaluator and never reach candidate code, mounts, or model prompts.
_Avoid_: test set (ambiguous), validation set

## Time (future_time)

**Time basis**:
The declared time unit and documented reference time that all temporal values in a project use.

**Prediction time**:
The moment a prediction for a row would be made in deployment.

**Feature availability**:
The moment a feature value becomes known, given as a timestamp or an offset from prediction time.

**Label availability**:
The moment a row's label becomes known, including its horizon and any reporting delay.

**Training cutoff**:
The latest moment whose information a fold's training may use. Training labels must be available by it.
_Avoid_: split date (loosely)

**Gap**:
A declared, nonnegative interval between a fold's training cutoff and its earliest evaluation prediction.

## Revisions and memory

**Candidate**:
A proposed revision of a project's evaluation script, identified by its content hash.
_Avoid_: fix, patch (when the hashed artifact is meant)

**Approval**:
The user's explicit consent to execute one exact candidate in isolation, bound to that candidate's hash.
_Avoid_: confirmation, sign-off

**Procedure**:
A saved evaluation workflow, offered to the agent as optional guidance. It is verified for its recorded scope only when every applicable required assertion of the corrected evaluation has a valid PASS.
_Avoid_: skill, memory (as a noun for one record), template

**Reuse**:
Applying a procedure after its prerequisites are re-checked and the full required set is re-executed on the new project with valid PASSes. A claim-type mismatch rejects reuse. A fresh repair attempt after a rejected reuse is not reuse.

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

## Scoring

**Canonical assertion ID**:
The stable identifier of one assertion in the evaluation policy (for example, `split.no_group_overlap`), used as the unit for scoring findings.

**Expected violated assertions**:
The assertion IDs a labeled case is designed to violate, fixed before measurement.
_Avoid_: answer (loosely), ground truth (for the whole case)

**False-violation run rate**:
The share of runs on clean cases whose outcome is VIOLATION_FOUND.

