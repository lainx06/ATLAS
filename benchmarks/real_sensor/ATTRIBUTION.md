# Attribution: UCI HAR (Human Activity Recognition Using Smartphones)

The T-09 real-data example uses the UCI HAR dataset. No raw data or derived table is committed to this repository. `retrieve.py` downloads the archive into the git-ignored `data/` folder, verifies it against `checksums.json` and builds each project's `table.parquet` (also git-ignored) from the training partition.

## Citation (as given on the dataset page, APA style)

Reyes-Ortiz, J., Anguita, D., Ghio, A., Oneto, L., & Parra, X. (2013). Human Activity Recognition Using Smartphones [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C54S4K.

The dataset's README asks publications to reference:

> [1] Davide Anguita, Alessandro Ghio, Luca Oneto, Xavier Parra and Jorge L. Reyes-Ortiz. A Public Domain Dataset for Human Activity Recognition Using Smartphones. 21th European Symposium on Artificial Neural Networks, Computational Intelligence and Machine Learning, ESANN 2013. Bruges, Belgium 24-26 April 2013.

## Source

- Dataset page: https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones
- Archive: https://archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip (61,005,872 bytes, SHA-256 `c00b803081a5c797cd5e4b83700a9810b38d53d9d84e01917e090e1fdbc81031`, retrieved 2026-10-17)

## License

The dataset page states: "This dataset is licensed under a Creative Commons Attribution 4.0 International (CC BY 4.0) license. This allows for the sharing and adaptation of the datasets for any purpose, provided that the appropriate credit is given." (https://creativecommons.org/licenses/by/4.0/)

**Conflicting term, recorded for the lead.** The `README.txt` inside the archive (from 2012) states: "This dataset is distributed AS-IS and no responsibility implied or explicit can be addressed to the authors or their institutions for its use or misuse. Any commercial use is prohibited." This is stricter than the CC BY 4.0 grant on the dataset page. The use here complies with both: non-commercial, local, attributed, with no redistribution of the data. Before any public or hosted use of the data or its derived tables, the lead should decide which terms govern.

## Changes made (CC BY 4.0 asks that changes be indicated)

- Only the training partition (`train/`, 21 subjects, 7,352 windows) is used to build the project tables. The official test partition (`test/`, 9 subjects) is downloaded and hashed, but no table contains a test row.
- The table adds `row_id` (`w00000` …, upstream row order) and `subject_id` (`S01` …) columns. Feature columns are named `f<index>_<upstream name>`, because upstream names are not unique. Feature values and activity labels (1–6, as in `activity_labels.txt`) are unchanged.
- The projects `har_flawed` (an ATLAS-authored flawed evaluation) and `har_clean` are ATLAS-authored evaluation code. They are not the original authors' protocol, and no flaw is alleged in the original study.
