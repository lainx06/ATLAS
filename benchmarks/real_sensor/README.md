# Real-data example: UCI HAR (T-09)

Two ATLAS-authored evaluations of the UCI HAR training partition, for the claim "The activity classifier works on people absent from training." (`unseen_group` by `subject_id`). Attribution and license: `ATTRIBUTION.md`. Protocol, evidence and results: `docs/T09_CONTAINMENT.md`.

| Project | What it does |
| --- | --- |
| `har_flawed` | **ATLAS-authored flawed variant.** It fits the scaler and SelectKBest(k=50) on every training row before splitting, then uses a random row-level 5-fold KFold, so subjects and their overlapping windows cross every fold. It reports its own (inflated) balanced accuracy. |
| `har_clean` | Clean control: GroupKFold(5) by subject within the training subjects; scaler, SelectKBest(k=50) and LogisticRegression all fit inside each fold. The same model family and the same claim. |

**Partitions.** The tables hold the official training partition only (21 subjects, 7,352 windows, 561 features). The official test partition (9 subjects, 2,947 windows) is downloaded and hashed, but neither project reads it: it is not used for development, tuning or any score.

**Provenance.** Coverage begins at the supplied feature table. The 561 features were computed and normalized upstream ("Features are normalized and bounded within [-1,1]", README.txt). Whether that normalization was fit globally across subjects, or across the training and test partitions, is **not established**.

**Commands** (Docker Desktop running; no model is called):

```powershell
uv run --locked python benchmarks/real_sensor/retrieve.py      # download or verify, build tables
uv run --locked python benchmarks/real_sensor/run_audit.py     # both projects, Docker, runs/t09/
uv run --locked python benchmarks/real_sensor/run_audit.py --repeat 3
```

`run_audit.py` explains why it does not use `atlas.cli audit --mode audit`: that mode runs only allowlisted trusted fixtures, on the host.
