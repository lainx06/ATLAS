# Project-owned evaluation script, observed by an in-container recorder

Status: proposed (2026-10-14, Step 7 Q3); acceptance follows the Step 8 review of the recorder design.

ATLAS runs the project's own `evaluate.py`, which uses a small adapter, inside the isolated container. A trusted, read-only recorder wraps an enumerated set of scikit-learn operations to trace fit inputs and row lineage. We rejected an ATLAS-owned training harness: it would give complete provenance by construction, but ATLAS could then never observe, diagnose, or test a correction to a project's actual flawed evaluation code, which is the product's central demonstration. The cost is that observation happens inside candidate Python and is not tamper-proof. Coverage gaps therefore yield NOT_ASSESSED, missing traces never prove absence, and bypass tests are required before the recorder's results are trusted (SPEC §4, §14.1).
