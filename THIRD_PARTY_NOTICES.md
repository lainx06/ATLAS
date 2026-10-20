# Third-party notices

ATLAS itself is Apache-2.0-licensed (see `LICENSE` and `NOTICE`). It depends on the packages below, ships vendored agent skills and fonts, and cites one dataset. This file is a first draft for the release check (T-13); it is not legal advice.

How the licenses were read: the runtime list is the 56 pinned lines of `requirements.txt` (`uv export --frozen --no-dev --no-hashes` of `uv.lock`; `docs/HOSTED_OPERATIONS.md` §9). Versions are those pins. Licenses come from each package's installed metadata (`importlib.metadata`, offline, from the Python 3.11 environment), in this order: the `License-Expression` field, else the `License` field, else the license classifier. Where a package gave none of them, the cell says `[TODO]`. A license text that the metadata only names, and that was not read in full, is not reproduced here.

## Runtime dependencies

| Package | Version | License (from metadata) |
| --- | --- | --- |
| altair | 6.3.0 | BSD License (classifier; the `License` field holds the copyright line "Vega-Altair Developers") |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| attrs | 26.1.0 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| charset-normalizer | 3.5.2 | MIT |
| click | 8.5.0 | BSD-3-Clause |
| cloudpickle | 3.1.2 | BSD-3-Clause |
| h11 | 0.16.0 | MIT |
| httpcore2 | 2.13.1 | BSD-3-Clause |
| httpx2 | 2.13.1 | BSD-3-Clause |
| httpx2-jsfetch | 1.0 | Not installed on the tested Windows environment. It is a dependency of `httpx2` only under the marker `python_full_version >= '3.12' and sys_platform == 'emscripten'` (`uv.lock`, `requirements.txt`). [TODO] license not read, since it is not installed |
| idna | 3.20 | BSD-3-Clause |
| itsdangerous | 2.2.0 | BSD License (classifier) |
| jinja2 | 3.1.6 | BSD License (classifier) |
| jiter | 0.17.0 | MIT |
| joblib | 1.6.0 | BSD-3-Clause |
| jsonschema | 4.26.0 | MIT |
| jsonschema-specifications | 2025.9.1 | MIT |
| markupsafe | 3.0.4 | BSD-3-Clause |
| narwhals | 2.27.1 | MIT |
| numpy | 2.4.6 (Python < 3.12), 2.5.4 (otherwise) | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 (read from 2.4.6; [TODO] confirm for 2.5.4 if it is released) |
| openai | 3.31.0 | Apache-2.0 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pandas | 3.0.6 | BSD 3-Clause License (the `License` field; classifier BSD License) |
| pillow | 12.3.0 | MIT-CMU |
| protobuf | 7.36.2 | 3-Clause BSD License (the `License` field) |
| psycopg | 3.3.6 | LGPL-3.0-only |
| psycopg-binary | 3.3.6 | LGPL-3.0-only (the compiled libraries it bundles may carry their own licenses: [TODO] not in the metadata) |
| pyarrow | 26.0.0 | Apache-2.0 |
| pydantic | 2.14.1 | MIT |
| pydantic-core | 2.50.1 | MIT |
| pydeck | 0.9.3 | Apache License 2.0 (the `License` field) |
| python-dateutil | 2.9.0.post0 | "Dual License" (the `License` field); classifiers BSD License and Apache Software License |
| python-dotenv | 1.2.4 | BSD-3-Clause (the `License` field) |
| python-multipart | 0.0.32 | Apache-2.0 |
| referencing | 0.37.0 | MIT |
| requests | 2.34.2 | Apache-2.0 (the `License` field) |
| rpds-py | 2026.9.1 | MIT |
| scikit-learn | 1.9.1 | BSD-3-Clause |
| scipy | 1.17.1 (Python < 3.12), 1.18.1 (otherwise) | BSD License (classifier; the `License` field holds the copyright text, read from 1.17.1; [TODO] confirm for 1.18.1) |
| six | 1.17.0 | MIT |
| sniffio | 1.3.1 | MIT OR Apache-2.0 (the `License` field) |
| starlette | 1.8.0 | BSD-3-Clause |
| streamlit | 1.66.0 | Apache-2.0 |
| threadpoolctl | 3.7.0 | BSD-3-Clause |
| truststore | 0.10.5 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |
| tzdata | 2026.5 | Apache-2.0 (the `License` field) |
| urllib3 | 2.8.0 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause |
| watchdog | 6.0.0 | Apache-2.0 (the `License` field) |
| websockets | 17.2 | BSD-3-Clause |

Two points for the release check:

- `psycopg` is LGPL-3.0-only. Lead disposition (2026-10-18): acceptable for the release. `psycopg` and `psycopg-binary` are installed unmodified from PyPI as separate dependencies; ATLAS does not vendor or modify them; their license is named here.
- `certifi` is MPL-2.0 and is used unmodified.

Development-only tools (the `dev` group of `pyproject.toml`; not part of the runtime list), read with the same method:

| Package | Version | License (from metadata) |
| --- | --- | --- |
| pytest | 9.1.1 | MIT |
| pytest-playwright | 0.10.0 | Apache Software License (classifier; the `License` field holds the Apache License 2.0 text) |
| ruff | 0.17.0 | MIT |

## Vendored agent skills

These folders are byte-for-byte copies from pinned upstream commits (`docs/TOOLING.md` "Pinned sources" and "Installed skills"), kept in both `.claude/skills/` and `.agents/skills/`. Each carries its upstream license file. They are development tooling for the agents that built ATLAS; the ATLAS application does not import them.

| Skill | Upstream (pinned commit) | License | Copyright |
| --- | --- | --- | --- |
| `setup-matt-pocock-skills` | https://github.com/mattpocock/skills (`49dd158d1076134a641b33efb035946536778336`) | MIT | 2026 Matt Pocock |
| `grill-with-docs` | same | MIT | 2026 Matt Pocock |
| `grilling` | same | MIT | 2026 Matt Pocock |
| `domain-modeling` | same | MIT | 2026 Matt Pocock |
| `to-spec` | same | MIT | 2026 Matt Pocock |
| `code-review-and-quality` | https://github.com/addyosmani/agent-skills (`aeac41d4d005999432bb7312f7ff06383a91d59d`) | MIT | 2025 Addy Osmani |
| `debugging-and-error-recovery` | same | MIT | 2025 Addy Osmani |
| `test-driven-development` | same | MIT | 2025 Addy Osmani |
| `frontend-design` | https://github.com/anthropics/skills (`dbd4588f9e1033efb41dad4bef2f7947c8993d44`) | Apache-2.0 (`LICENSE.txt` in the skill folder) | no copyright line in LICENSE.txt |
| `frontend-ui-engineering` | https://github.com/addyosmani/agent-skills (`aeac41d4d005999432bb7312f7ff06383a91d59d`) | MIT | 2025 Addy Osmani |
| `developing-with-streamlit` | https://github.com/streamlit/streamlit, tag `1.66.0` (`269e552f276f5757b2903174da18e083defb325b`), path `lib/streamlit/.agents/skills/developing-with-streamlit/` | Apache-2.0 (the repository's root `LICENSE`, copied into the skill folder as `LICENSE`) | no copyright line in the license file; the folder is the skill bundled in the streamlit 1.66.0 package |

The shared reference files copied with the Addy skills (`.claude/references/` and `.agents/references/`: `security-checklist.md`, `performance-checklist.md`, `testing-patterns.md`, `accessibility-checklist.md`) carry the same MIT license (`LICENSE` in each folder).

The Streamlit repository also has a `NOTICES` file; it lists third-party software contained in the Streamlit product, none of which is in the vendored skill folder, so it is not copied (`docs/TOOLING.md` "UI HUD pass skills").

## Fonts (vendored, served by the app)

The UI's typefaces are vendored in `static/fonts/` and served by Streamlit's static file serving (`[server] enableStaticServing = true`, `[[theme.fontFaces]]` in `.streamlit/config.toml`); nothing is fetched at runtime. The files are unmodified copies of the `fonts/complete/woff2/` files in IBM's npm packages, each tarball checked against the registry's published sha1 and sha512 integrity before extraction (2026-10-19). The OFL text is the packages' `LICENSE.txt` (identical in all three), copied byte-for-byte as `static/fonts/OFL.txt` (marked `-text` in `.gitattributes`).

| Family | Files | Source | License |
| --- | --- | --- | --- |
| IBM Plex Sans | `IBMPlexSans-Regular`, `-Italic`, `-Medium`, `-SemiBold` (`.woff2`) | `@ibm/plex-sans` 1.1.0 (npm sha1 `44a45a8e269870221c431eb4e8023dca6ed21ceb`) | SIL Open Font License 1.1 |
| IBM Plex Mono | `IBMPlexMono-Regular`, `-Medium`, `-SemiBold` | `@ibm/plex-mono` 2.5.0 (npm sha1 `152c0b1dda619ef5f032db258bda798cf278125e`) | SIL Open Font License 1.1 |
| IBM Plex Sans Condensed | `IBMPlexSansCondensed-Medium`, `-SemiBold` | `@ibm/plex-sans-condensed` 2.0.0 (npm sha1 `f63bd37ab0028a15948bdf913ba88260c3809d63`) | SIL Open Font License 1.1 |

Copyright © 2017 IBM Corp. with Reserved Font Name "Plex". The files are distributed unmodified and under their own name, as the OFL's Reserved Font Name clause requires; they are not sold by themselves. Repository: https://github.com/IBM/plex.

## Data

- **UCI HAR** ("Human Activity Recognition Using Smartphones", UCI dataset 240): Reyes-Ortiz, J., Anguita, D., Ghio, A., Oneto, L., & Parra, X. (2013). UCI Machine Learning Repository. https://doi.org/10.24432/C54S4K. The dataset page grants **CC BY 4.0**; the archive's own 2012 `README.txt` adds "Any commercial use is prohibited." This repository does **not** redistribute the dataset: the retrieval script downloads it into a git-ignored folder and verifies it against committed checksums, and the hosted demo shows precomputed results only. Citation, license and changes: `benchmarks/real_sensor/ATTRIBUTION.md`, `demo/README.md`, `docs/T09_CONTAINMENT.md` §1. (DECISIONS.md "T-12 decisions (user, 2026-10-18)", item 1.)
- The `benchmarks/t01/` and `benchmarks/t02/` fixtures are synthetic, generated by this repository's scripts, and are labelled synthetic.

## Other components

- **Container base image.** `Dockerfile.runner` builds the isolated runner on `python:3.11-slim` (`docs/TOOLING.md`, `STATUS.md`). [TODO: list the image's own license notices if the release should cover them.]
- **Test-only database image.** The T-12 budget-store tests use `postgres:17-alpine` in a disposable local container (TASKS.md T-12 "RESULT"). It is not shipped.
- **Model.** `nvidia/nemotron-3-super-120b-a12b`, served through Nebius Token Factory. License: NVIDIA Nemotron Open Model License, https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-nemotron-open-model-license/ (named in NVIDIA's API reference for the model, https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-super-120b-a12b; checked by the lead 2026-10-18). ATLAS calls the hosted model over the network and does not redistribute weights.
