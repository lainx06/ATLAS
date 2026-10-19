# Hosted demo bundle

`demo/recorded/` holds the recorded runs the hosted demo shows (T-12; `docs/HOSTED_OPERATIONS.md`). They are byte-exact copies, never moved and never edited, so the recorded-run viewer's hash checks pass. `BUNDLE.json` lists each run's source and the SHA-256 of every file. `scripts/check_recorded.py` re-checks the copies and scans them for publication.

| Run | Source | Original outcome |
| --- | --- | --- |
| `live6/agent-s01_faulty-877f8245a8a2` | live run 6 (2026-10-18), the first complete live run | VIOLATION_FOUND |
| `t09/agent-har_flawed-1e2267f662c0` | T-09 audit run, repeat 1 (2026-10-17) | VIOLATION_FOUND |
| `t09/agent-har_clean-ac63eaecd7a8` | T-09 audit run, repeat 1 (2026-10-17) | NO_VIOLATION_FOUND |

Rebuild (it refuses to overwrite):

```
uv run --locked python scripts/build_recorded_bundle.py SOURCE=DEST ...
```

`demo/recorded/**` is marked `-text` in `.gitattributes` and excluded from ruff, so neither git nor a formatter can change a byte.

## UCI HAR data

The two `har_*` runs evaluate ATLAS-authored projects on the UCI HAR dataset:

> Reyes-Ortiz, J., Anguita, D., Ghio, A., Oneto, L., & Parra, X. (2013). Human Activity Recognition Using Smartphones [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C54S4K

- **License.** The dataset page grants **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/).
- **Non-commercial note.** The archive's own 2012 `README.txt` adds: "Any commercial use is prohibited."
- **No redistribution.** The hosted demo shows **precomputed results only** and does not distribute the dataset. The feature table (`table.parquet`, two copies per HAR run) is left out of the bundle; `BUNDLE.json` lists each left-out file with its size and SHA-256.
  - The bundle does keep the runs' derived evidence: row and subject identifiers in the split and check records, the model's predicted classes, and the check results.
  - It holds no feature values and no per-row activity labels (only class counts per fold).
- **Changes and attribution:** `benchmarks/real_sensor/ATTRIBUTION.md`.

DECISIONS.md "T-12 decisions (user, 2026-10-18)", item 1.
