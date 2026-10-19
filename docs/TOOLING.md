# Tooling record

Observed versions and settings. Only values actually printed by a command or shown in a client are recorded; anything else is marked unknown.

## Host (observed 2026-10-14)
| Tool | Version | How observed |
| --- | --- | --- |
| OS | Windows 11 Home 10.0.26200 | session environment |
| Windows PowerShell | 5.1.26100.9444 | `$PSVersionTable.PSVersion` |
| WinGet | 1.29.380 | `winget --version` |
| Git | 2.55.0.windows.5 | `git --version` |
| uv | 0.13.1 (62faed335 2026-10-13) | `uv --version` |
| Claude Code (application) | 2.1.292 | `claude --version` |
| VS Code | 1.99.3 | `code --version` |
| Python (project) | CPython 3.11.17, uv-managed | `uv python install 3.11` |
| Python (system, unused) | CPython 3.12.10 | `uv python list --only-installed` |
| Docker | not on PATH (not installed or not configured) | `Get-Command docker` |

Notes: MSYS2 Pythons at `C:\msys64\ucrt64\bin` are on PATH; uv prints "Failed to inspect Python interpreter" warnings for them. Harmless, as the project uses the uv-managed 3.11. `C:\Users\Lain\.local\bin` is not on PATH; irrelevant because commands use `uv run`.

## Builder model (Claude Code session)
- Model: Opus 5.5 (`claude-opus-5-5`), set via `/model opus` in this session.
- Effort: high, set via `/effort high` in this session.
- The Claude Code application version (2.1.292) is a separate thing from the model version.

## Python dependencies (resolved in `uv.lock`, 61 packages)
Direct runtime: numpy 2.4.6, pandas 3.0.6, scikit-learn 1.9.1, pydantic 2.14.1, streamlit 1.66.0, openai 3.31.0, python-dotenv 1.2.4.
Dev group: pytest 9.1.1, ruff 0.17.0.
Notable transitive: scipy 1.17.1, pyarrow 26.0.0.
Build backend: `uv_build>=0.13.1,<0.14.0`.

## Development skills (Start Here Step 6, installed 2026-10-14)

Selective project-local copies per playbook Section 22.2. No plugin, marketplace, hook, command pack, or global instruction was installed or changed.

### Pinned sources
Clones live in `.dev/skill-sources/` (git-ignored; verified with `git check-ignore`). SHAs from `git rev-parse HEAD` immediately after `git clone`.

| Key | Repository | Commit | Commit date / subject | License |
| --- | --- | --- | --- | --- |
| matt | https://github.com/mattpocock/skills | `49dd158d1076134a641b33efb035946536778336` | 2026-10-09, "wizard: template fixes (#1237)"; plugin.json version 1.3.1 | MIT, (c) 2026 Matt Pocock |
| addy | https://github.com/addyosmani/agent-skills | `aeac41d4d005999432bb7312f7ff06383a91d59d` | 2026-10-13, "chore(release): bump plugin manifests to 0.6.13" | MIT, (c) 2025 Addy Osmani |

Do not pull new revisions during the sprint. An update means: fetch, re-inspect, edit `PINS` in `scripts/sync_skills.py`, delete the old copies deliberately, re-run.

### Installed skills
Each folder is copied whole from the pinned commit object, plus the upstream `LICENSE` (the only file not present in the upstream folder). Destinations: `.claude/skills/<name>/` (Claude Code) and `.agents/skills/<name>/` (Codex).

| Invocation name | Upstream path | Why installed | Who can invoke |
| --- | --- | --- | --- |
| `setup-matt-pocock-skills` | matt `skills/engineering/setup-matt-pocock-skills/` (+ `domain.md`, `issue-tracker-{github,gitlab,local}.md`, `triage-labels.md`, `agents/openai.yaml`) | Selected | User only (`disable-model-invocation: true`; Codex `allow_implicit_invocation: false`). Claude: `/setup-matt-pocock-skills` |
| `grill-with-docs` | matt `skills/engineering/grill-with-docs/` | Selected | User only. Claude: `/grill-with-docs` |
| `grilling` | matt `skills/productivity/grilling/` | Required companion: grill-with-docs body is "Call the Skill tool twice, for "grilling" and "domain-modeling"" | Model or user |
| `domain-modeling` | matt `skills/engineering/domain-modeling/` (+ `ADR-FORMAT.md`, `GLOSSARY-FORMAT.md`) | Required companion (as above) | Model or user |
| `to-spec` | matt `skills/engineering/to-spec/` | Selected | User only. Claude: `/to-spec` |
| `code-review-and-quality` | addy `skills/code-review-and-quality/` | Selected | Model or user (broad auto-trigger description) |
| `debugging-and-error-recovery` | addy `skills/debugging-and-error-recovery/` | Selected | Model or user |
| `test-driven-development` | addy `skills/test-driven-development/` | Selected | Model or user (broad auto-trigger description) |

All selected names exist at the pinned revisions; none was missing or renamed.

Shared references (Addy): `references/security-checklist.md` and `references/performance-checklist.md` (cited by code-review-and-quality as `../../references/...`) and `references/testing-patterns.md` (cited by test-driven-development) are copied to `.claude/references/` and `.agents/references/` with Addy's `LICENSE`. From `<root>/skills/<name>/`, `../../references/` resolves to `<root>/references/`, so **no SKILL.md was edited**. This addresses the gap upstream documents for per-skill installs (README "Installing one skill?", issue addyosmani/agent-skills#361). Upstream suggests a `references/` folder inside the skill instead; that would have required rewriting the paths in SKILL.md.

### Soft references deliberately not installed
These are mentioned in the selected skills as "see also" pointers or optional branches, not operative calls. The selected skills work without them:
- code-review-and-quality names `security-and-hardening`, `performance-optimization`, `constraint-driven-development`.
- test-driven-development names `browser-testing-with-devtools` and Chrome DevTools MCP (the testing-patterns reference is JS/TS-specific; the principles apply to pytest).
- setup-matt-pocock-skills skips its triage-label section when `triage` is absent.
- to-spec requires the setup skill to have run (it tells the user to run `/setup-matt-pocock-skills`) and applies the `ready-for-agent` label.

### Matt skill configuration (complete; writes verified 2026-10-14)
`/setup-matt-pocock-skills` was invoked by the user and run with the decisions in DECISIONS.md (2026-10-14):
- Issue tracker = "other": local files. Specs go in `docs/`; `TASKS.md` holds the index and Section 24 task entries; `handoffs/` is for Section 19 transfers only. No `gh`/`glab`, no `.scratch/`. Written to `docs/agents/issue-tracker.md`.
- Triage labels: section skipped (`triage` not installed); no `triage-labels.md`.
- Domain docs: single-context; `GLOSSARY.md`/`docs/adr/` are created lazily. ADRs only for consequential architectural decisions, with a pointer in DECISIONS.md. Written to `docs/agents/domain.md`, adapted from the skill's `domain.md` template.
- `## Agent skills` block appended to AGENTS.md (the skill's default target is CLAUDE.md; overridden by decision). CLAUDE.md got only a one-line pointer update.
- Verified after writing:
  - `sync_skills.py --check` problems 0 (upstream skill files unchanged).
  - Existing paths referenced by the new text checked and present: `docs/agents/issue-tracker.md`, `docs/agents/domain.md`, `docs/PRD.md`, `docs/SPEC.md`, `TASKS.md`, `DECISIONS.md`, `AGENTS.md`, `STATUS.md`, `docs/TOOLING.md`, `docs/handoff/ATLAS_Build_Playbook.md` (Sections 19 and 24), `.claude/skills/domain-modeling/ADR-FORMAT.md`.
  - Planned paths, deliberately not created yet (absence expected): `GLOSSARY.md` and `docs/adr/` (created lazily by domain-modeling), `docs/specs/` (later feature specs), `handoffs/` (first Section 19 transfer).
  - Paths that must not be created: `.scratch/` (not a spec location), `docs/agents/triage-labels.md` (`triage` not installed). Both absent.
  - One `## Agent skills` block (AGENTS.md); AGENTS.md diff append-only; ruff check/format exit 0.

### Sync / verify script
`scripts/sync_skills.py` reads every file with `git show <pinned sha>:<path>` (never the clone's working tree), writes only missing files, and refuses to write anything if an existing file differs or a managed skill folder contains a foreign file. `--check` verifies without writing.
- Install: `uv run --locked python scripts/sync_skills.py` → 64 files written (32 per destination), exit 0.
- Verify: `uv run --locked python scripts/sync_skills.py --check` → "32 files x 2 destinations; problems: 0", exit 0. (Before install it reported 64 MISSING, exit 1.)
- No-overwrite check: after appending a line to `.claude/skills/grilling/SKILL.md`, install printed "DIFFERS ... Refusing to write", exit 1, and left the edit in place. The file was then restored, and `--check` returned to exit 0.
- `.claude/` vs `.agents/`: sha256 of all 32 files identical (`diff` of sorted `sha256sum` lists).
- Against the upstream folders: `diff -r --strip-trailing-cr` reported no differences for all 8 skills and 3 references (excluding the added LICENSE files).
- Relative links resolve in both roots: the 3 `../../references/*.md` paths, the 5 setup templates, and domain-modeling's 2 format files.
- `pyproject.toml` `[tool.ruff] extend-exclude` now includes `.claude/skills`, `.claude/references`, `.agents`. Ruff 0.17 formats Markdown, and before the exclusion it scanned 48 files (vendored Markdown included). After it, 13 files; `ruff format --check .` and `ruff check .` exit 0.

Upstream scripts (`scripts/link-skills.sh`, `skills/engineering/wizard/template.sh`, Addy `hooks/*.sh`, `scripts/*.js`) were read where relevant and **not executed**. Addy's `CLAUDE.md` states it configures that repo only; it was not copied.

### Load and discovery status
| Item | Status | Evidence |
| --- | --- | --- |
| Files for all 8 skills + 3 references, both roots | **installed** | `sync_skills.py --check` exit 0; checksums above |
| Claude Code native discovery: `code-review-and-quality`, `debugging-and-error-recovery`, `test-driven-development`, `grilling`, `domain-modeling` | **verified** (discovery, all 5) | First attempt failed: `Skill("code-review-and-quality")` returned `Unknown skill: code-review-and-quality` (this Claude Code 2.1.292 session started before `.claude/skills/` existed). Minutes later, with no further action, the session announced all 5 model-invocable skills as available. That was new evidence, so one retry was made. |
| Native harmless loading check (`code-review-and-quality` + referenced checklist) | **verified** | Retry `Skill("code-review-and-quality")` printed "Launching skill" with base directory `.claude\skills\code-review-and-quality`. The skill's `../../references/security-checklist.md`, resolved from that base, opened (Threat Modeling and Pre-Commit Checks sections read). Verification-only output below; nothing reviewed, edited, or published. Native loading of the other 4 discovered skills was not exercised. |
| Manual fallback (same check by explicit file path) | **verified** (also run before native discovery appeared) | Installed SKILL.md and checklist read by explicit path |
| Claude `/setup-matt-pocock-skills` | **verified** (discovery and invocation) | 2026-10-14: the user invoked it from the `/` menu; Claude Code loaded it with base directory `.claude\skills\setup-matt-pocock-skills` and its process ran (see "Matt skill configuration" above) |
| Claude `/grill-with-docs` | **slash discovery/invocation unverified**; wrapper **manually followed** | 2026-10-14 Step 7: `/grill-with-docs` arrived as pasted text, not a slash invocation. Its body ("Call the Skill tool twice, for grilling and domain-modeling") was followed manually. |
| `grilling`, `domain-modeling` (as grill-with-docs companions) | **verified** (loaded natively) | 2026-10-14 Step 7: `Skill("grilling")` and `Skill("domain-modeling")` each printed "Launching skill" with base directories under `.claude\skills\` |
| Claude `/to-spec` | **installed; discovery unverified** (user-invoked only; confirm in the `/` menu) | Not run |
| Codex discovery/invocation of `.agents/skills` | **unverified** (Codex not configured) | Copied files alone do not prove Codex loads them |
| Ponytail, pstack, no-mistakes, whole Matt/Addy packs, Addy hooks/commands/agents | **deferred / not installed** | Playbook Sections 18 and 22 |

**Native review-skill check (verification only).** Asked which Step 6 acceptance criteria it would inspect:
- (1) Pinned SHAs → Correctness, Step 5 "Verify the verification", and Security "dependencies from trusted sources".
- (2) Identical copies → Correctness, plus Step 2 "would the tests catch a regression", answered by experiment (the no-overwrite mutation).
- (3) References resolve → Correctness (a missing reference is a silent failure path).
- (4) Licenses → Dependency Discipline item 5.
- (5) No hooks/packs/global changes → Security (the checklist's Threat Modeling item: third-party content is a trust boundary) and Architecture (no unnecessary dependencies).
- Pre-Commit Checks from the checklist apply to the Step 6 commit: no secrets staged; `.gitignore` covers `.env`/`*.pem`/`*.key`; `.env.example` holds placeholders.

**Still to confirm by the user:** the `/` menu shows `/grill-with-docs` and `/to-spec`.

## T-07 UI tooling (installed 2026-10-17, worktree `atlas-t07b`, branch `t07-ui`)

### Anthropic frontend-design (playbook Section 25, S38)
| Item | Value |
| --- | --- |
| Repository | https://github.com/anthropics/skills (cloned to ignored `.dev/skill-sources/anthropic`) |
| Pinned commit | `dbd4588f9e1033efb41dad4bef2f7947c8993d44` (2026-10-09, "Update claude-api skill: dynamic workflows and the four workflow quickstarts (#1995)"), from `git rev-parse HEAD` after the clone. Last commit touching the folder: `41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f` |
| Selected path | `skills/frontend-design/` only: `SKILL.md`, `LICENSE.txt`. No whole collection |
| License | Apache-2.0, `LICENSE.txt` inside the upstream folder (copied with it). `THIRD_PARTY_NOTICES.md` does not mention this skill |
| Dependencies | None: no scripts, references, hooks or companion-skill calls in `SKILL.md` |
| Destinations | `.claude/skills/frontend-design/` and `.agents/skills/frontend-design/`, via `scripts/sync_skills.py` (new `anthropic` pin; `LICENSES` maps it to `None` because the folder carries its own notice) |
| Verification | `sync_skills.py --check`: 4 MISSING before install; install wrote 4 files; then "34 files x 2 destinations; problems: 0". SHA-256 `SKILL.md` `d9197063…c1d3` equals `git show <pin>:skills/frontend-design/SKILL.md`; both destinations identical; `diff -r --strip-trailing-cr` against the clone: no differences |
| Load status | Native `Skill("frontend-design")` in the building session: `Unknown skill` (the session's discovery root is the main checkout, not this worktree). **Loaded by explicit file reference** (manual fallback, Section 22.2) before designing the first screen |

Not installed: Addy `frontend-ui-engineering` (the T-07 build task names only frontend-design; it is for the later Codex UI review), Vercel `web-design-guidelines` (optional per Section 25).

**`sync_skills.py` line endings.** In a fresh worktree checked out with `core.autocrlf=true`, every existing copy compared as DIFFERS (CRLF on disk against LF blobs). The comparison now ignores CRLF/LF (`_lf`); content is still compared byte for byte otherwise. With it, all 30 earlier files compare equal.

### Streamlit bundled guidance (S40)
- Streamlit 1.66.0 (`streamlit version`). `streamlit skills --help`: project mode "creates symlinks from .agents/skills/ and .claude/skills/ to the bundled skills in your Streamlit installation"; global mode writes to the user directory.
- **Project-local route not used:** it is symlink-only, the links point into this machine's `.venv` (not portable, Section 25), and symlink creation is not permitted on this host (`tests/unit/test_candidates.py` skips "symlink creation not permitted on this host"). Global mode would change the user directory (Section 22.2: no global changes).
- **Fallback used (manual-only):** the bundled `developing-with-streamlit` skill is read by explicit path, `.venv/Lib/site-packages/streamlit/.agents/skills/developing-with-streamlit/SKILL.md` (23,067 bytes) and its `references/` (`theme.md`, `layouts.md`, `performance.md`, ...), for the installed 1.66.0.

### Browser tests (Section 22.4)
- `uv add --dev pytest-playwright`: pytest-playwright 0.10.0, playwright 1.64.0 (+ greenlet 3.5.6, pyee 13.0.1, python-slugify 9.1.3, text-unidecode 1.3).
- `uv run playwright install chromium`: Chromium build 1248 (156.0.8078.4), headless shell, ffmpeg and winldd under `%LOCALAPPDATA%\ms-playwright`. Offline smoke check: launched headless Chromium, rendered a page, read it back.

## UI HUD pass skills (installed 2026-10-19, worktree `atlas-ui`, branch `ui-hud`)

Two skills for the HUD design pass, by the Section 22.2 route: canonical repositories fetched over HTTPS into the ignored `.dev/skill-sources/`, SHAs from `git rev-parse` after the fetch, files read from the pinned commit objects by `scripts/sync_skills.py`, copied byte-for-byte into `.claude/` and `.agents/`. No collection, hook, command, plugin or global setting was installed or changed; no fetched script was run.

### Addy `frontend-ui-engineering` (for the UI engineering review; playbook §25)
| Item | Value |
| --- | --- |
| Repository | https://github.com/addyosmani/agent-skills (fresh clone 2026-10-19; `HEAD` was still the existing pin) |
| Pinned commit | `aeac41d4d005999432bb7312f7ff06383a91d59d`, the existing `addy` pin (playbook §25: "Add Addy's frontend-ui-engineering to the existing selected source revision"). Last commit touching the folder: `3e1e0a2db595ab2abe89b1204f7eabb67a24eb90` (2026-10-03, "Bind the frontend error-state retry callback") |
| Selected path | `skills/frontend-ui-engineering/` (one file, `SKILL.md`), plus Addy's `LICENSE` copied into the folder as for the other Addy skills |
| Companion file | `SKILL.md` "See Also" cites `../../references/accessibility-checklist.md`; copied to `.claude/references/` and `.agents/references/` (beside the three existing Addy references and their `LICENSE`), so the path resolves without editing `SKILL.md` |
| License | MIT, (c) 2025 Addy Osmani |
| Not installed | Nothing else is referenced; the skill names no companion skill |

### Streamlit `developing-with-streamlit` (version-matched; for implementation)
| Item | Value |
| --- | --- |
| Inspected | https://github.com/streamlit/agent-skills at `c69a265613f17cdd69d42e6f67b704214178fae5` (2026-07-23, "Deprecate: meta-skill now ships with Streamlit (canonical source of truth) (#29)"). Its README: the repository is deprecated and being archived; the meta-skill there only runs `scripts/discover.py` to locate the skill bundled in the installed Streamlit package (1.57+); `streamlit/streamlit` is the canonical source. Not vendored: the meta-skill resolves against the machine's interpreter (a machine-specific path, §25) and adds no content of its own |
| Repository | https://github.com/streamlit/streamlit, tag `1.66.0` (annotated tag object `59ee618b69947e1bdd968c74b1afbf1d152dcd2c`) → commit `269e552f276f5757b2903174da18e083defb325b` (2026-10-14, "Up version to 1.66.0"); fetched with `git clone --filter=blob:none --no-checkout --depth 1 --branch 1.66.0` |
| Version match | Exact: `uv.lock` pins streamlit 1.66.0. All 57 files of the tagged folder are byte-identical (`cmp`) to the copy inside the installed package, `.venv/Lib/site-packages/streamlit/.agents/skills/developing-with-streamlit/` |
| Selected path | `lib/streamlit/.agents/skills/developing-with-streamlit/` whole: `SKILL.md`, `references/` (29 files), `assets/templates/` (themes and app templates). Every `references/*.md` link in `SKILL.md` and in the references resolves inside the folder; no `../` path |
| Not copied | The sibling `lib/streamlit/.agents/skills/AGENTS.md` and `CLAUDE.md` (authoring rules for Streamlit maintainers, not part of the skill) and `.agents/meta-skill/` (the discovery wrapper above) |
| License | Apache-2.0: the repository's root `LICENSE`, copied into the skill folder as `LICENSE`. The repository's `NOTICES` file lists third-party software contained in the Streamlit product (it opens "THE FOLLOWING SETS FORTH ATTRIBUTION NOTICES FOR THIRD PARTY SOFTWARE…"); none of that software is in the vendored folder, so it is not copied |
| Re-pin rule | The skill matches the Streamlit version. Upgrading Streamlit means re-pinning to the new tag and replacing these copies deliberately |

### Sync and verification
- `scripts/sync_skills.py`: new `streamlit` pin and `LICENSES` entry; `SKILLS` gains `frontend-ui-engineering` and `developing-with-streamlit`; `SHARED` gains `references/accessibility-checklist.md`.
- Before install, `--check`: the 34 existing files unchanged; 61 per destination MISSING (122). Install: 122 files written. After: "95 files x 2 destinations; problems: 0", exit 0.
- `.claude/` and `.agents/`: sorted `sha256sum` lists of the new skill folders and `references/` identical.
- `diff -r --strip-trailing-cr` of `.claude/skills/developing-with-streamlit` (excluding the added `LICENSE`) against the installed 1.66.0 package copy: no differences. `frontend-ui-engineering/SKILL.md` against the clone: no differences.
- Ruff: the new folders sit under the existing `extend-exclude` entries (`.claude/skills`, `.claude/references`, `.agents`).

### Load status
| Item | Status | Evidence |
| --- | --- | --- |
| Files, both roots | **installed** | `sync_skills.py --check` exit 0 |
| Claude native discovery | **unverified** in the building session: its discovery root is the main checkout, which does not have these folders | as for frontend-design in T-07 |
| Manual fallback | **used**: `frontend-ui-engineering/SKILL.md`, `developing-with-streamlit/SKILL.md` and `references/theme.md` read by explicit path (identical to the installed copies, above) before the design spec was written, together with `frontend-design/SKILL.md` | this session |
| Codex discovery of `.agents/skills` | **unverified** | copied files alone do not prove loading |
