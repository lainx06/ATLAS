# ATLAS HUD visual system (UI design pass, phases 1 and 2)

Status: **design spec for the `ui-hud` branch, phases 1 and 2.** It supersedes the palette, type and spacing of `docs/UI_SPEC.md` §7 on this branch only. The truth rules of `docs/UI_SPEC.md` §1 are unchanged and override everything here. Phase 1 (§1–§10) covers the recorded-run viewer (the local "Open a recorded run" view and the hosted "Recorded runs" view, which share `atlas.ui.results.finished_run` and the recorded banner) and the hosted page header and sidebar. Phase 2 (§11) rolls the HUD out to every view (the local run, the typed-approval panel, the hosted live session, the failure and honest-empty states, the tables) and adds the deterministic briefing, the evidence drill-down and the live mission track.

Skills read before this spec: Anthropic `frontend-design`, Streamlit `developing-with-streamlit` 1.66.0 (`SKILL.md`, `references/theme.md`), Addy `frontend-ui-engineering` (`docs/TOOLING.md` "UI HUD pass skills").

## 1. Concept

**A real instrument, not a movie prop.** The page is the readout of one evaluation instrument. Every element and every motion is bound to a value in the run's own verified files, or to a real event such as the page receiving a verified run. Nothing is decorative telemetry.

- **Subject.** An engineer or judge checking whether an evaluation supports a deployment claim.
- **Primary job.** In the first viewport, without scrolling or clicking: what the evidence integrity is, what the original's outcome is, and what the executed, verified revision's outcome is. Then the two leak mechanisms (group overlap and fit scope), drawn from the evidence, side by side.
- **Where boldness is spent.** On the outcome reticle: one large status-coloured code inside corner brackets, with the page's only glow. Everything around it is quiet: hairlines, neutral data text, one accent.

Where this brief pins a choice (dark only, uppercase condensed HUD labels, monospace data, a middle dot in source captions), the brief wins over the frontend-design skill's generic defaults list.

## 2. Tokens

### 2.1 Colour

| Token | Value | Use |
| --- | --- | --- |
| `bg` | `#0A0F14` | Page background (theme `backgroundColor`); insets (code, check tiles, model-written frame) |
| `grid` | `rgba(148,163,184,0.04)` lines, 24 px pitch | Engineering grid on the HUD page container only (composite `#10151B`) |
| `panel` | `#0F1720` | Cards and HUD panels (theme `secondaryBackgroundColor`) |
| `hairline` | `#1E2A36` | 1 px solid border on every card and panel (theme `borderColor`) |
| `text` | `#E2E8F0` | Body and all data, hashes, IDs and multi-line values |
| `muted` | `#94A3B8` | HUD labels, captions inside HUD markup, axis labels |
| `accent` | `#67E8F9` | Interactive elements (focus rings, toggles, links, theme `primaryColor`) and "verified" signals (lit ring segments, the INTACT count). Never a status colour |
| `red` | `#F87171` | VIOLATION_FOUND, FAIL, "on both sides", FAIL flow lines |
| `green` | `#4ADE80` | NO_VIOLATION_FOUND, PASS |
| `amber` | `#FBBF24` | INCONCLUSIVE, NOT_ASSESSED, BUDGET_EXHAUSTED / NEEDS_INPUT; the model-written badge |
| `violet` | `#C084FC` | ERROR |
| `stone` | `#A8A29E` | NOT_SUPPORTED; "0 shared"; NON-LIVE |
| `red-tint` | `rgba(248,113,113,0.18)` | Fill of an "on both sides" cell (composite on panel `#39272F`) |
| `model-dash` | `rgba(251,191,36,0.35)` | 1 px dashed model-written frame |

Every status colour is printed next to its code; colour never carries meaning alone. Streamlit's palette keys map as: `red`/`green`/`orange`/`violet`/`gray` → the five status colours (`*Color` and `*TextColor` set exactly). `blue` maps to the neutral `text` colour: blue badges (LIVE RUN, Recorded run, stage labels) carry no meaning beyond their words, and the one accent stays reserved. Badge and alert backgrounds are set explicitly to the status colour at 14 % over `panel`: red `#30242B`, green `#17332D`, orange `#302F21`, violet `#28263F`, gray `#242A32`, blue `#2D343D`.

Primary buttons (none on the HUD screen) get `bg` text on the accent through keyed wrappers (`st-key-primary-*`), because Streamlit draws white text on `primaryColor` (1.45:1 on the accent, measured in the prototype).

### 2.2 Type

Fonts are vendored, never fetched: `static/fonts/` (SIL OFL 1.1, `static/fonts/OFL.txt`), served by `[server] enableStaticServing = true` and declared with `[[theme.fontFaces]]` (Streamlit `references/theme.md` "Self-hosting custom fonts").

| Role | Face | Size / weight | Colour |
| --- | --- | --- | --- |
| Prose, UI text | IBM Plex Sans | 15 px / 400, line height 1.5 (theme `font`, `baseFontSize = 15`) | `text` |
| Headings | IBM Plex Sans | 22 / 18 / 16 / 15 / 14 / 13 px, 600 | `text` |
| Data, hashes, IDs, code | IBM Plex Mono | 13 px / 400 (theme `codeFont`, `codeFontSize`) | `text` (never coloured when multi-line) |
| Coloured monospace (status codes, accent counts) | IBM Plex Mono | at least 12 px, weight 500 | status colour or `accent` |
| HUD labels | IBM Plex Sans Condensed | 11 px / 500, uppercase, letter-spacing 0.08em | `muted` |
| Reticle code | IBM Plex Mono | 30 px / 600 (26 px below 1024 px) | status colour |

Files: Plex Sans Regular, Italic, Medium, SemiBold; Plex Mono Regular, Medium, SemiBold; Plex Sans Condensed Medium, SemiBold (woff2, from the `@ibm/plex-sans` 1.1.0, `@ibm/plex-mono` 2.5.0 and `@ibm/plex-sans-condensed` 2.0.0 npm packages, published integrity verified).

### 2.3 Space, radius, borders

- Spacing scale (px): 4, 8, 12, 16, 24, 32. Cards padded 16 / 20; HUD panels 12 / 16; 16 between panels.
- Radius: 4 px cards and widgets (`baseRadius`, `buttonRadius`); 2 px tiles and cells.
- Borders: 1 px solid `hairline` on every card and panel. **HUD corner brackets only on the outcome reticle (status colour) and on the active frame (accent):** phase 2's typed-approval panel and an open inspection frame. Never on other cards.
- Theme `paddingTop = "1rem"` so the hero clears the first viewport.

## 3. Layout

### 3.1 Recorded run with an executed and verified candidate (live6)

First viewport at 1440 × 900 and 1280 × 800, sidebar open, no scrolling and no clicks:

```text
+-- banner: LIVE RUN / NON-LIVE · run's own banner · Recorded run, finished <t>; not re-executed here --+
| Does the evaluation support the claim?                                                               |
+-- HERO: BEFORE -> VERIFIED REVISION ------------------------------------------------------------------+
|  ( ring )   ⌜ VIOLATION_FOUND      ⌝   ->   ⌜ NO_VIOLATION_FOUND           ⌝                          |
|  49/49      ⌞ 4 of 9 required FAIL ⌟        ⌞ 4 FAIL -> PASS · Docker, typed approval ⌟               |
|  INTACT       label · caveat · original/outcome.json   label · caveat · candidates/c1/outcome.json   |
+------------------------------------------------------------------------------------------------------+
| LEAK MAP original (checks/split_integrity.json)    | LEAK MAP candidate (candidates/c1/checks/…)     |
|        fold0  fold1  fold2  fold3                   |        fold0   fold1   fold2   fold3            |
|  S01   [both] [both] [both] [both]                  |  S01   0 shared ...                             |
+----------------------------------------------------+-------------------------------------------------+
| FIT SCOPE original (checks/fit_provenance.json)    | FIT SCOPE candidate (candidates/c1/checks/…)    |
|  [160 rows] -> SelectKBest (fit: global) ==> fold0: StandardScaler.transform, LogisticRegression...  |
+------------------------------------------------------------------------------------------------------+
  (below the fold) CHECK MATRIX original | candidate, then the existing cards 1–6
```

Phase 2: the **Briefing** (§11.2) now leads the run, between the title and the hero. The first viewport at 1440 × 900 and 1280 × 800 holds the banner, the title, the briefing, the ring and both reticles; the leak maps and flows follow directly below the hero (scenario 8 asserts both).

- The hero renders inside `finished_run`'s single clearable slot: a render failure clears the hero with every other card (the T-12 fix pass 2 boundary stays).
- The integrity card (the intact line, the item table in an expander and the detection caveat) follows the hero, and the existing cards (claim, 2. Analysis to 6. Trust and export) follow it unchanged in content.
- Original and candidate are separate evaluations of separate executions. They sit side by side, each with its own source path; nothing morphs or re-routes one into the other.

### 3.2 Recorded run without an executed candidate (the two HAR bundles)

The ring and one reticle; the leak map and the fit-scope flow side by side, original only. No candidate column, reticle, diagram or "after" wording appears.

### 3.3 Tampered copy

The banner and title, then the integrity card: the ring with the differing items' segments in red and the centre reading "EVIDENCE CHANGED", then the existing "evidence changed since recording" panel and its table. No outcome, no reticle, no diagram, no card.

### 3.4 Narrow screens

- When the recorded page itself is narrower than 760 px (every viewport below 1024 px, and 1024 px with the sidebar open; build note N13): each original/candidate pair stacks (the reticles) or switches with a CSS-only toggle in the same markdown block (the evidence block: leak maps, flows and the check matrix). The toggle is two visually hidden radio inputs with labels ("Original" / "Candidate"); no Streamlit widget and no rerun. The panes cross-fade (200 ms, opacity only; both share one grid cell, so nothing moves).
- At 480 px and below, the leak map sits in a horizontal scroll region (`overflow-x: auto; tabindex="0"; role="region"`, `aria-label` naming the table). Cells show a compact code ("B" = on both sides, "0" = 0 shared) with a legend; the full text stays in each cell's `title` and `aria-label`.
- No page-level horizontal scroll at 390 × 844.

### 3.5 Hosted header and sidebar

- Sidebar: the ATLAS heading and line, the View radio, the **Recorded run** picker (moved here from the main column so the hero fits the first viewport), then Capability: "Hosted demo: limited", "Candidate code is not executed here", "Live: available / unavailable" with the unavailable message.
- Main: one compact replay line ("Recorded runs" badge plus the replay disclosure), the HAR citation for HAR runs, then the recorded page.

## 4. Components (pure functions in `src/atlas/ui/hud.py`)

Each takes values read from the run's verified files and returns an HTML/SVG string; Streamlit only places it (`st.markdown(..., unsafe_allow_html=True)`; `st.html` strips SVG, see §8). Every value is read only after `recorded.verify` reports the run intact, and only from files whose relative path is in the verified set (a `Check` with status `matches`). A missing file or field renders "not recorded" for that field; nothing is inferred. Every visible number carries its source in a caption or `title` (file and field). Every component has a text alternative.

| # | Component | Source (file: field) | Rendering |
| --- | --- | --- | --- |
| 1 | Integrity ring | `recorded.verify` checks: one segment per item (`Check.item`), lit when `matches` | SVG ring, segments in `accent`; tampered: differing items' segments `red`, centre "EVIDENCE CHANGED". Centre "<n>/<n> INTACT", line "recomputed now from the bundled files" (hosted) or "from the run's files" (local). Each segment's `<title>` names its item and status. `role="img"`, `aria-labelledby` its title/desc |
| 2 | Outcome reticle | Original: `agent_report.json: scientific_outcomes.original` (verified equal to `original/outcome.json: outcome`), `comparison.original.required_set[].status`. Candidate: `comparison.candidates[i].scientific_outcome`, `.status_by_assertion[]`, `.execution.runner` / `.status`, and the `agent_log.jsonl` approval event for its `candidate_hash` (`decision`, `approver_reason`) | Code in 30 px Plex Mono 600, status colour, one subtle `text-shadow` glow (the page's only glow); HUD corner brackets; PRD label; the fixed caveat; the detail line ("4 of 9 required checks FAIL" / "4 FAIL → PASS"); the candidate's "executed in the isolated Docker runner after typed approval" only when runner `docker_isolated`, status `completed`, and an approval event `decision approved`, `approver_reason confirmed` for that hash are all recorded; the source path |
| 3 | Check matrix | `comparison.original.required_set[]` (`assertion_id`, `status`); with a candidate, `comparison.candidates[i].status_by_assertion[]` (`original`, `candidate`) | Tiles (status code + assertion ID) in an original column and a candidate column; a changed tile states its direction ("FAIL → PASS") |
| 4 | Mission track | `agent_report.json: states[]` (`state`, `detail`, `time_utc`), `budget.used.attempts` / `budget.limits.model_attempts`, `budget.used.tool_operations` / `budget.limits.tool_operations`, `budget.used.revisions` / `budget.limits.candidate_revisions` | Ordered list of the recorded stages as a horizontal, wrapping track; the terminal stage in its state colour with its code; counters "<used> of <limit>". Renders a partial list (phase 2 feeds it live) |
| 5 | Budget gauge | `cost.entries[]` (one per provider request) of `spending.max_attempts`; `cost.estimated_total_usd` of `spending.estimate_cap_usd`; fixture runs: `cost.reason` | Two bars with their numbers, labelled "estimate, not billing" |
| 6 | Model-written frame | `model_text[]` (`text`, `label`), proposal details and diffs | A 1 px dashed `model-dash` border around the text on `bg`; the full amber only on the header badge "MODEL-WRITTEN · UNTRUSTED" (Streamlit's orange badge: `amber` on #302F21), then the engine's label as a caption. Header and text are native elements rendered in one pass; the untrusted text is `st.text` (never parsed as HTML or Markdown). Never outcome styling; never animated |
| 7 | Leak map | `checks/split_integrity.json: assertions[assertion_id=split.no_group_overlap]`: `status`, `observed.overlapping_groups`, `observed.column`; folds from `splits.json[].fold` | HTML table. Y-axis label exactly "Groups with recorded overlap in the original (observed.overlapping_groups)"; rows exactly those groups in the original's order (first appearance over folds in file order). A cell is "on both sides" when that group is listed for that fold in that evaluation's own file, otherwise "0 shared". "On both sides": `red-tint` fill, 2 px solid `red` border, bold text; "0 shared": transparent fill, 1 px dotted `stone` border, `stone` text (they read apart in greyscale). The candidate grid uses the original's rows with values from `candidates/<c>/checks/split_integrity.json` and folds from `candidates/<c>/splits.json`. A run whose list is empty shows the folds and "No group is listed in observed.overlapping_groups" |
| 8 | Fit-scope flow | `checks/fit_provenance.json: assertions[assertion_id=fit.state_dependencies_within_fold_train]`: `status`, `observed.origins[]` (`class`, `fit_scope`, `contributing_rows`, `affected_folds`, `affected_uses`), `observed.judged_uses`, `observed.unknown_uses`, `observed.violations` | SVG schematic "[<contributing_rows> rows] → <class> (fit: <fit_scope>)" with a flow line from each origin to each `affected_uses` entry, grouped by fold; lines and arrowheads `red` when the assertion FAILs. The candidate's own schematic from its own file: no red when it PASSes; with no origins (empty or absent, the latter shown as "not recorded"), the PASS state with the observed counts only |

Captions on 7 and 8 name the file, the assertion and the field, for example `candidates/c1/checks/split_integrity.json · split.no_group_overlap · observed.overlapping_groups`.

**Which candidate is "after".** The last entry of `comparison.candidates[]` with `execution.status == "completed"`, `evaluated` true, a recorded outcome, and its `candidates/<c>/outcome.json` in the verified set. A proposal that was not executed (rejected, declined, unavailable, hosted "not executed here") never gets an "after" column, reticle, outcome or diagram.

## 5. Motion system

CSS and SVG only, `ease-out`. Motion plays once per run per Streamlit session: the page keys it to the run ID in `st.session_state` and renders every later rerun with `played = True`, which emits no animation classes, so a rerun shows the final state. (A full browser reload is a new Streamlit session and counts as a new first load.) Nothing loops, pulses, scans or types; no metric counts up; motion never precedes the data it represents (an element's resting state is its final state, and animations only use `animation-fill-mode: backwards` from a blank or unlit start, never from a false value). Under `prefers-reduced-motion: reduce` no animation or transition runs and the final state shows immediately.

| Beat | Time | What moves | Bound to |
| --- | --- | --- | --- |
| 1 | 0–0.4 s | The ring's segments light in order to the verified count (each fades from the unlit track); both reticles' corner brackets lock on (8 px outward → in place, opacity 0 → 1) | `verify` items; the reticles present |
| 2 | 0.4–0.7 s | Only the check tiles that changed flip in (rotateX 90° → 0) to the recorded candidate status | `status_by_assertion[]` rows where `original != candidate` |
| 3 | 0.4–1.2 s | Leak map "on both sides" cells light fold by fold (fold k of F starts at 0.4 + k·0.8/F s, lasting 0.8/F s), original and candidate together; fit-scope flow lines draw (`stroke-dashoffset` 1 → 0 on `pathLength="1"`) and their arrowheads fade in over the last 0.1 s | the cells and lines present |

- The mission track and budget gauge render settled on recorded runs (their motion is reserved for live stage updates in phase 2).
- The narrow toggle cross-fades in 200 ms.
- Tampered state: the differing ring segments turn from `accent` to `red` with one short shake (0.3 s, ±3 px, once), then the "evidence changed" panel fades in (150 ms, after 0.35 s); no diagram renders.
- Polish: hover and focus transitions 120 ms on HUD controls; visible 2 px `accent` focus rings (offset 2 px) on the toggle labels and the scroll region; cards fade in once (150 ms) on a run's first render.

## 6. IDs (st.markdown injects into the main document)

Every SVG-internal ID (marker, title, desc, and anything referenced by `url(#…)`, `href="#…"` or `aria-labelledby`) and every radio/label ID is unique per rendered instance:

`atlas-<component>-<part>-<scope>-<runhash8>-<instance>`

- `component`: `ring`, `reticle`, `leak`, `flow`, `matrix`, `track`, `gauge`, `toggle`;
- `scope`: `orig`, `cand` or `run` (a component that is not per evaluation);
- `runhash8`: the first 8 hex characters of SHA-256 of the run ID (the run's label, for example `live6/agent-s01_faulty-877f8245a8a2`);
- `instance`: a short suffix the page passes (`h` for the hero); a second rendering of the same run on one page passes another.

Example: `atlas-flow-arrow-orig-1f0e9a2c-h`. A test renders the original and candidate versions of every component together, and two runs on one page, and asserts no duplicate `id` and that every `url(#…)`, `href="#…"`, `aria-labelledby` and `label for=` reference resolves inside the same instance.

## 7. Contrast (WCAG relative luminance; every text/background pair used)

| Text | Background | Ratio |
| --- | --- | --- |
| `text` #E2E8F0 | `bg` #0A0F14 | 15.61 |
| `text` #E2E8F0 | `panel` #0F1720 | 14.64 |
| `text` #E2E8F0 | grid line composite #10151B | 14.88 |
| `text` #E2E8F0 (bold) | `red-tint` cell #39272F | 11.32 |
| `muted` #94A3B8 | `bg` / `panel` / grid line | 7.50 / 7.04 / 7.15 |
| `accent` #67E8F9 | `bg` / `panel` | 13.27 / 12.45 |
| `red` #F87171 | `bg` / `panel` / `red-tint` cell | 6.96 / 6.52 / 5.04 |
| `green` #4ADE80 | `bg` / `panel` | 11.04 / 10.36 |
| `amber` #FBBF24 | `bg` / `panel` | 11.53 / 10.81 |
| `violet` #C084FC | `bg` / `panel` | 7.28 / 6.83 |
| `stone` #A8A29E | `bg` / `panel` | 7.63 / 7.16 |
| Badge: red / green / amber / violet / stone / neutral | #30242B / #17332D / #302F21 / #28263F / #242A32 / #2D343D | 5.37 / 7.79 / 8.09 / 5.52 / 5.73 / 10.20 |
| Streamlit caption (`text` at 60 %) | `panel` / `bg` (composites #8E949D / #8C9198) | 5.91 / 6.06 |
| `bg` #0A0F14 (primary button text) | `accent` #67E8F9 | 13.27 |

Phase 2 pairs (all also in `atlas.ui.hud.CONTRAST_PAIRS`, checked ≥ 4.5 by a test; non-text marks need 3:1):

| Text or mark | Background | Ratio | Where |
| --- | --- | --- | --- |
| `text` #E2E8F0 | `bg` #0A0F14 | 15.61 | full hashes in the approval panel, the decision inset |
| `text` #E2E8F0 | `panel` #0F1720 | 14.64 | briefing lines, inspection-frame values, state reasons, data-table cells, track nodes |
| `muted` #94A3B8 | `panel` | 7.04 | inspection-frame keys and labels, the briefing caveat, table heads, **disabled buttons** (were dark on nothing, or Streamlit's 40 % text) |
| `muted` #94A3B8 | `bg` | 7.50 | the tile's "Inspect"/"Close" cue, decision-inset labels |
| `accent` #67E8F9 | `bg` | 13.27 | the cue on hover, a tile's focus ring |
| `red` #F87171 | `panel` | 6.52 | the briefing's FAIL code |
| `text` #E2E8F0 | neutral badge #2D343D | 10.20 | changed rows of the per-assertion table (were #EFF6FF under light text, about 1.1:1) |
| state badges: violet / amber / stone / red | #28263F / #302F21 / #242A32 / #30242B | 5.52 / 8.09 / 5.73 / 5.37 | ERROR; NEEDS_INPUT, BUDGET_EXHAUSTED, Docker, incomplete_coverage; NOT_SUPPORTED, LIVE UNAVAILABLE, NO RECORDED RUNS; EVIDENCE CHANGED |
| `text` #E2E8F0 | grid composite #10151B | 14.88 | the hosted Route line |
| `accent` (mark) | `panel` | 12.45 | the active frame's corner brackets |
| state edge (mark): red / amber / violet / stone | `panel` | 6.52 / 10.81 / 6.83 / 7.16 | the 2 px left edge of a state panel |
| `text` (mark) | `panel` | 14.64 | the current stage's outline on a live track |

The 1 px `hairline` (#1E2A36 on `panel`, 1.24:1) is decorative structure, never the only cue: the leak map's two cell states differ by fill, border style and text. Rendered colours are checked in the browser (phase 1 report).

## 8. Implementation constraints and deviations

- Streamlit only; no React, no custom component build step. HUD markup goes through `st.markdown(..., unsafe_allow_html=True)`: the 1.66.0 `st.html` sanitiser uses DOMPurify `USE_PROFILES: {html: true}` and removes every SVG element (observed in a prototype: markers, clip paths, lines and circles all stripped), while `st.markdown` keeps SVG, `<style>`, radio inputs and labels in the main document.
- Untrusted strings in HUD markup (group values, class names, uses, fold names, paths) are escaped for HTML and for Markdown (`<>&"'` and `$ : * _ [ ] \` `` ` `` ~ # |` as character references; newlines as `&#10;`), and each block is emitted as one line so Markdown never leaves the HTML block. Model-written text is never placed in HUD markup.
- Targeted CSS uses only the documented `st-key-*` hooks plus the HUD's own classes inside its markup. The engineering grid therefore sits on the recorded page's own container (`st-key-hud-page`), not on Streamlit's private app background.
- No outbound network at runtime; no 3D, pre-rendered imagery, audio, emoji, or display fonts.

## 9. Phase 1 build notes (2026-10-19)

Choices made while building against the rendered page (screenshots at 1440 × 900, 1280 × 800, 390 × 844). Each stays within §1–§8 and the truth rules.

| # | Note | Why |
| --- | --- | --- |
| N1 | **Statuses come from the verified `outcome.json` files**, not from `agent_report.json`: the reticle detail lines and the check matrix read `original/outcome.json` and `candidates/<c>/outcome.json` `assertions[].status` (the report's `required_set` and `status_by_assertion` are built from the same lists; a test asserts they are equal). The candidate's execution line reads `candidates/<c>/execution.json` (`runner`, `status`, `candidate_hash`) and the `agent_log.jsonl` approval event, all hash-verified. The mission track and budget gauge read the report, as §4 says | `agent_report.json` has no recorded self-hash; where a verified file holds the value, the HUD reads it |
| N2 | **"After" candidate:** the last comparison entry whose `execution.json` says `completed` and whose `outcome.json` records an outcome, both in the verified set | §4 "Which candidate is after" |
| N3 | **No band-label or column-head rows.** The reticle headings ("Before · original", "Verified revision · candidates/c1"), the arrow between them and each panel's label carry the pairing; the band text stays as the hero's accessible name | The two rows cost about 60 px; without them the whole hero fits 1280 × 800 |
| N4 | **Compact sizes in the evidence block:** leak-map cells 15 px high, 10 px neutral text, 2 px spacing; the Y-axis caption 10.5 px; panel padding 8 / 12. Coloured monospace stays at 12 px / 500 | Four folds of "on both sides" fit the 1280 px pane; the hero fits 800 px |
| N5 | **The fit-scope flow scales to its panel** (`width: 100%`, `max-width` its drawn width) and shows the observed counts only when there are no origins (the PASS state) | Counts beside a drawn FAIL schematic repeated it; scaling keeps it inside the pane |
| N6 | **The hosted replay disclosure and the HAR citation are banner captions**, and the run picker is in the hosted sidebar | The separate replay block pushed the flows below 800 px |
| N7 | **The narrow toggle's radios have no `checked` attribute.** `st.markdown` renders through React, which turns `checked` into a read-only controlled input (the toggle did not switch in the browser). "Original" is the CSS default until "Verified revision" is chosen | Found in the browser |
| N8 | **Paired matrix tiles share one grid** (code, ID, a fixed direction slot), so both columns wrap the same way and stay row-aligned; below 1024 px the direction moves under the ID | Long IDs wrapped differently in the two columns |
| N9 | **Recorded page spacing** through its own hook: `.st-key-hud-page { gap: 0.75rem }`, `.st-key-hud-page h1 { padding: 0.25rem 0 0 }`; the banner 6 / 14 px with a 2 px gap; theme `paddingTop = "0.5rem"` | First-viewport fit, documented hooks only |
| N10 | **Primary buttons** (none on this screen) are wrapped in `st-key-primary-*` containers: "Confirm & run" (key renamed `primary-confirm-run`), "Submit confirmation", "Start the live session" | §2.1 |
| N12 | **The model-written header is native, not HUD markup.** A raw-HTML header rendered a moment after the native `st.text` beside it, so the untrusted text was briefly on screen without its label (the scenario 1 approval-panel test caught it intermittently in the full suite). The badge is now `:orange-badge[MODEL-WRITTEN · UNTRUSTED]` and the label a caption, both in the same render pass as the text | Truth rule: model-written text is always labelled |
| N13 | **The stack/toggle breakpoint is the page's own width** (a CSS container query on `st-key-hud-page`, under 760 px), not the 1024 px viewport. At 1024 px with the sidebar open the main column is about 590 px: side by side, the reticle codes broke mid-word and the leak maps clipped into their scroll regions (seen in the review probe). Every viewport under 1024 px still gets the toggle (its page is narrower than 760 px); 1280 and 1440 stay side by side | §3.4's intent: readable pairs |
| N11 | **Motion timing** in the screenshots: the five `s8_09_motion_*` frames are taken at nominal offsets from the moment the browser first saw a reticle; screenshot latency (about 0.1–0.2 s) shifts them later. The test asserts the animations run on first load, are absent after a rerun, and are `none` under emulated reduced motion | Evidence, not a precise timeline |

## 10. Forbidden

Neon glow on everything (one subtle glow, the reticle only); gradients as decoration (the grid is two 1 px line gradients at 4 %, the only gradient); glassmorphism blur; particles or radar; fake terminal streams; typing effects; corner brackets on every card; 3D or pre-rendered imagery; Orbitron/Rajdhani-style display fonts; emoji; stock sci-fi imagery; decorative numbers, random hex or scanning animations; any Marvel/Stark/JARVIS name or likeness ("HUD" is the design term).

## 11. Phase 2: the HUD on every view (2026-10-19)

Skills re-read for this phase: Anthropic `frontend-design`, Streamlit `developing-with-streamlit` 1.66.0, Addy `frontend-ui-engineering`. Everything in §1–§10 still applies: the truth rules, the escaping and one-line markup rule (§8), the motion rules (§5: once per run per session, never on a rerun, nothing loops, none under reduced motion) and the ID scheme (§6).

### 11.1 Roll-out

| View | What it shows now | Source |
| --- | --- | --- |
| Local "Run a project" | The HUD page container (grid, spacing); the claim card; mode controls; an amber Docker-unavailable state for agent runs | `app.py` |
| A run still going (local) | The mission track from the stages the run's log has recorded so far (`agent_log.jsonl` state events; counters "<n> so far" from model_attempt and tool events), each new stage lighting once | `hud.track_live`, the page's existing one-second fragment |
| A finished local run | Verified first (`results.finished_verified`, the same `recorded.verify` as a recorded run). Intact: briefing, hero, evidence block, integrity card, then the cards. Changed: an evidence-changed state ("the cards below are read from the files as they are now"), no HUD, no briefing | `results.finished_verified` |
| Typed approval | §11.4 | `views.approval_panel` |
| Hosted live session | The recorded original's ring and reticle (original only, headed "Original"); the start form or the live-unavailable state; while running, the live track and gauge (§11.6); finished: the Route line (Plex Mono), the session verified with its briefing, HUD, track and gauge; proposals "not executed here" in the model-written frame | `hosted/page.py` |
| Failure and honest-empty states | §11.5 | `views.state_panel` |
| Agent trace, check details, comparison, integrity and export tables | Hairline rows, Plex Mono data in `text`, 7 px / 12 px cells, HUD-label column heads; still `st.table` (tests read the cells); cells wrap anywhere at phone width. "Check details" uses the inspection frame's field rows instead of the JSON viewer | `views.CSS`, `views.assertion_details` |

### 11.2 Briefing (`hud.briefing_lines`, `hud.briefing`)

A pure function of the run's verified files and `evaluation/assertion_definitions.json` only (the policy's frozen definitions). From the report it reads only the proposals' outcome codes. It never reads model text, a rationale, a proposal's text, a diff, a complete file or a reply. Built only when `recorded.verify` reports the run intact; changed evidence gets the evidence-changed panel and no briefing. In order, each line only when its data is recorded:

1. "Evidence intact: <n> of <n> recorded hashes verified now." (`n` counts the recorded file hashes recomputed now; the report-key outcome checks the ring also counts are not hashes, so live6's ring reads 49/49 and its briefing 46);
2. "Original outcome: <code>. Required checks: <f> FAIL, <na> NOT_ASSESSED, <e> ERROR (of <n>)." (`original/outcome.json`; an audit run's root `outcome.json`);
3. up to four "<assertion> (FAIL): <definition's first sentence, Markdown marks removed>", then "and <k> more";
4. "Revision <candidates/c>, executed and verified: <code>; <k> FAIL → PASS." (the §4 "after" candidate only);
5. "Proposals were checked by ATLAS validation and not executed here." (a proposal with outcome `not_executed_here`);
6. "<Metric> (pooled), descriptive only: original <x>[, candidate <y>]." (`descriptive[metric.recomputed_primary]`, 4 decimals as the cards);
7. "This does not say the scientific claim is true or false." (always).

Each line carries its source in a `title`; the panel's source line says "from the run's verified files and evaluation/assertion_definitions.json only; no model-written text".

### 11.3 Evidence drill-down (`hud.inspect_records`, `hud.inspection`, `hud.record_body`)

Each FAIL, NOT_ASSESSED or ERROR tile of the check matrix (original and verified revision) is a `<details>` whose `<summary>` is the tile itself: no Streamlit widget, no rerun. Enter and Space toggle it (native); Chromium exposes the summary as a disclosure with its expanded state (read from its accessibility tree: false, true, false), so no static `aria-expanded` is written (it would go stale). The open frame carries the accent corner brackets and shows, from the assertion's verified check file (or the run's verified `outcome.json` when no check file lists it): status, reason, evidence_valid, limitations, each evidence artifact with its full sha256 (wrapped, `text`), and the observed object as key/value rows (nested objects as dotted keys two levels deep; lists as "<n> items: a; b; … and <k> more", six shown; deeper values summarised by size). The source line names the file and `assertions[assertion_id=…]`. IDs: `atlas-insp-sum<letters>-<scope>-<runhash8>-<instance>`; the frame is `aria-labelledby` its summary. The tile's direction and its "Inspect"/"Close" cue share the tile's end slot, so paired columns keep equal widths. The frame fades in over 120 ms when opened (a response to the person's action; none under reduced motion).

### 11.4 The typed-approval panel

The active frame: hairline border, accent corner brackets (eight solid marks painted as background layers under the hairline, 3 px so 2 px show; solid colour, not a visual gradient). The request first ("Run the ORIGINAL …" / "Run this CANDIDATE …", the entry point, the snapshot and code hashes as HUD-labelled Plex Mono blocks in `text`, wrapping, never truncated); for a candidate, the rationale and the diff each in the model-written frame (badge, the engine's label, then the text; the diff keeps "Proposed diff (untrusted; control characters shown as escapes)"). Then the decision in its own `bg` inset ("Your decision": the confirmation field and Submit confirmation), with "Close without deciding" below a hairline. The request, the single submission, the rule, the timeouts and the declines are the engine's (`atlas.ui.approver`, `atlas.agent.approval`), untouched.

### 11.5 Failure and honest-empty states (`views.state_panel`)

A panel with a 2 px left edge in the status colour, the code as a status-coloured badge, the reason, then "**Next action:** …". Native elements (one render pass); never success styling, never green.

| State | Tone | Code shown | Next action |
| --- | --- | --- | --- |
| Terminal ERROR | violet | ERROR | read the reason code and the trace; a new run starts from the beginning |
| Terminal NEEDS_INPUT | amber | NEEDS_INPUT | nothing more executed; a new run asks again |
| Terminal BUDGET_EXHAUSTED | amber | BUDGET_EXHAUSTED | what was recorded before the limit stands; a new run starts with fresh limits |
| NOT_SUPPORTED | stone | the `## NOT_SUPPORTED` headline (kept) | the intake reason's action |
| Incomplete coverage (INCONCLUSIVE) | amber | incomplete_coverage | the next actions per reason code |
| Evidence changed (recorded or finished run) | red | EVIDENCE CHANGED | restore the files, or treat the results as unverified |
| Run crashed before a report | violet | ERROR | start a new run |
| Docker unavailable (agent mode) | amber | Docker: <state> | start Docker, then reload |
| No recorded runs | stone | NO RECORDED RUNS | finish a run, or set ATLAS_UI_RECORDED_DIR |
| Hosted live unavailable | stone | LIVE UNAVAILABLE | open Recorded runs |
| Hosted budget exhausted | amber | BUDGET_EXHAUSTED | open Recorded runs |
| Hosted session crashed | violet | ERROR | open Recorded runs |

### 11.6 Live mission track

Local: the run view's existing one-second fragment reads the run's log; the track shows the stages so far, the latest outlined in `text` as current (`aria-current="step"`), and each stage lights once (`hud-a-node`, 300 ms opacity from unlit) the first time this page sees it (the lit count is display state in `st.session_state`). Hosted: the page already followed a running session with a one-second `st.fragment` reading `handle.run_dir()/agent_log.jsonl`; the same read now draws the track and the gauge (requests and estimated cost so far from the logged model_attempt events, known plus held, against `budget.DECIDED_SLICE4`'s 6 requests and $0.0648, the limits the session runs with). Display only: no change to how a session runs, reserves, sends or settles; the UI writes no run, store or log state. When the session ends the fragment reruns the page, which renders the finished session without the fragment, so polling stops.

### 11.7 Keyboard (recorded in the browser, `runs/ui-hud/screens2/keyboard_tab_order.json`)

- **Approval panel**, Tab from the request: the page title's and the panel heading's hover links (Streamlit's heading anchors), then (a candidate only) the diff's scroll region and its Copy button, then the confirmation field, Submit confirmation, Close without deciding. The decision controls come after everything they decide on.
- **Drill-down**, Tab from the original's leak-map scroll region: each FAIL tile's summary in matrix order (four for live6), then the candidate's leak-map region. Each summary shows the 2 px accent focus ring (offset 2 px); Enter or Space opens and closes it.

### 11.8 Phase 2 build notes

| # | Note | Why |
| --- | --- | --- |
| P1 | The title's bottom padding is back (0.75rem) under Streamlit's -1rem heading margin | Phase 1 removed it and the hero rode up under the title (A1) |
| P2 | Fit-scope without drawn origins: one summary line from the recorded fields; "not recorded" only where a value is expected | A2 |
| P3 | The flow draws one lane per origin; targets listed once per origin | A3: two origins into five folds crossed |
| P4 | A reticle with nothing executed after it is headed "Original", not "Before · original" | No "before" without an "after" (§3.2) |
| P5 | "not executed here" proposals are gray, not violet | Violet is ERROR |
| P6 | The briefing's failing line reads "<assertion> (FAIL): …" | As "FAIL <assertion> …" it duplicated the check-details expander's label, which scenario 1 clicks by text |
| P7 | Primary buttons keep dark text only when enabled; disabled ones use `muted` | Disabled primary buttons are transparent: the dark text vanished |
| P8 | Field labels in the approval panel are HUD labels with no negative margin | At 390 px a negative margin overlapped the block below |
| P9 | Inspection-frame keys stack above values when the page is under 760 px | Keys wrapped mid-word at 390 px |
| P10 | Data-table cells wrap anywhere | The hosted original's checks table clipped long IDs at 390 px |
| P11 | The briefing leads; the leak maps and flows move just below the first viewport | §3.1, phase 2 note |

### 11.9 frontend-ui-engineering checklist (evidence, not a score)

| Item | Finding | Fix or evidence |
| --- | --- | --- |
| Renders without console errors | none seen in the probes | scenarios 8 to 11, the hosted HUD test |
| Keyboard access | every new control is native (summary, input, buttons) | §11.7; Enter and Space checked in scenario 10 |
| Visible focus | tile summaries had no ring | 2 px accent `:focus-visible` ring on `summary.hud-tile-row` |
| Screen reader | frames are `role="group"` labelled by their tile; states are text; the track marks the current step | §11.3, §11.6 |
| Responsive (390, 1280, 1440) | label overlap, mid-word keys, a clipped table at 390 | P8, P9, P10; no page-level sideways scroll (scenario 10) |
| Loading, empty, error and permission states | Docker, no recorded runs, live unavailable and exhausted had no next action | §11.5 |
| Colour not the only signal | every state prints its code; the frame edge repeats it | §11.5 |
| Design-system adherence | a light #EFF6FF row fill on the dark theme; a one-off violet for "not executed here" | §7 phase 2 pairs; P5 |
| Contrast | disabled buttons unreadable | P7; every new pair at least 4.5 (text) or 3 (marks), §7 |

### 11.10 Evidence

`runs/ui-hud/screens2/` (git-ignored): `p2_01` to `p2_47` at 1440 × 900, 1280 × 800 and 390 × 844 (settled: every finite animation finished first), the live6 load frames `p2_07_motion_*`, the live-track frames `p2_41_live_track_frame*`, two videos (`video_live6_load`, `video_hosted_live_track`) and `keyboard_tab_order.json`; plus the phase 1 scenario screenshots re-taken settled. Full suite: `runs/ui-hud/full2.log`.
