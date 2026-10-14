# Project-owned evaluation script, observed by an in-container recorder

Status: accepted for V1, with the narrowed provenance contract from the Step 8 review (DECISIONS.md F1, 2026-10-14). Not implemented.

ATLAS runs the project's own `evaluate.py`, which uses a small adapter, inside the isolated container. A trusted, read-only recorder observes a bounded supported path: adapter-loaded data, enumerated scikit-learn operations, supported row selection, and recorded predictions. Along that path it records operation and instance identity, fitted-state versions, input/output lineage, and the training rows each fitted state depends on. Contamination is judged against the training partition of the fold where a state is *used*.

We rejected an ATLAS-owned training harness. It would give complete provenance by construction, but ATLAS could then never observe, diagnose, or test a correction to a project's actual flawed evaluation code, which is the product's central demonstration.

The cost is that observation happens inside candidate Python and is not tamper-proof. A valid row index establishes identity, not ancestry. Fingerprints detect unexpected changes but don't prove arbitrary preprocessing was observed. Unknown ancestry, zero observed fits, unexplained mutation, and missing prediction ancestry therefore yield NOT_ASSESSED, and missing traces never prove absence (SPEC §4.3, §5, §15).
