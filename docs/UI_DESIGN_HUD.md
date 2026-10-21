# ATLAS HUD visual system (UI design pass, phases 1 and 2)

Status: **design spec for the `ui-hud` branch, phases 1 and 2, and the story layout slices 1 to 3 on `ui-story` (§12–§14).** It supersedes the palette, type and spacing of `docs/UI_SPEC.md` §7 on this branch only. The truth rules of `docs/UI_SPEC.md` §1 are unchanged and override everything here. Phase 1 (§1–§10) covers the recorded-run viewer (the local "Open a recorded run" view and the hosted "Recorded runs" view, which share `atlas.ui.results.finished_run` and the recorded banner) and the hosted page header and sidebar. Phase 2 (§11) rolls the HUD out to every view (the local run, the typed-approval panel, the hosted live session, the failure and honest-empty states, the tables) and adds the deterministic briefing, the evidence drill-down and the live mission track. **Slice 1 of the story layout (§12, branch `ui-story`)** reorganizes the views into four pages and the Overview & Cases story; plain English by default, Expert view on demand.

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
| 1 | Integrity ring | `recorded.verify` checks: one segment per item (`Check.item`), lit when `matches` | SVG ring, segments in `accent`; tampered: differing items' segments `red`, centre "EVIDENCE CHANGED". Centre "<n>/<n> INTACT", caption the integrity count (§11.2b: "<n> of <n> recorded items verified now (<h> file hashes, <c> outcome comparisons)"), then the line "recomputed now from the bundled files" (hosted) or "from the run's files" (local). Each segment's `<title>` names its item and status. `role="img"`, `aria-labelledby` its title/desc |
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
| A finished local run | Verified first (`results.finished_verified`, the same `recorded.verify` as a recorded run). Intact: briefing, hero, evidence block, integrity card, then the cards. Changed: only the evidence-changed panel (the ring and the table of differing items); no outcome, briefing, HUD or card (release review 1, F1: `results.gate`, repeated inside `finished_run`) | `results.finished_verified` |
| Typed approval | §11.4 | `views.approval_panel` |
| Hosted live session | The recorded original's ring and reticle (original only, headed "Original"); the start form or the live-unavailable state; while running, the live track and gauge (§11.6); finished: the Route line (Plex Mono), the session verified with its briefing, HUD, track and gauge; proposals "not executed here" in the model-written frame. Changed evidence (the bundled original, or the finished session's own files): only the evidence-changed panel, through the same `results.gate` | `hosted/page.py` |
| Failure and honest-empty states | §11.5 | `views.state_panel` |
| Agent trace, check details, comparison, integrity and export tables | Hairline rows, Plex Mono data in `text`, 7 px / 12 px cells, HUD-label column heads; still `st.table` (tests read the cells); cells wrap anywhere at phone width. "Check details" uses the inspection frame's field rows instead of the JSON viewer | `views.CSS`, `views.assertion_details` |

### 11.2 Briefing (`hud.briefing_lines`, `hud.briefing`)

A pure function of the run's verified files and the fixed assertion labels (`src/atlas/ui/assertion_labels.json`, §11.2a) only. From the report it reads only the proposals' outcome codes. It never reads model text, a rationale, a proposal's text, a diff, a complete file or a reply. Built only when `recorded.verify` reports the run intact; changed evidence gets the evidence-changed panel and no briefing. In order, each line only when its data is recorded:

1. "Evidence intact: <n> of <n> recorded items verified now (<h> file hashes, <c> outcome comparisons)." (the one integrity count, §11.2b; live6 reads "49 of 49 recorded items verified now (46 file hashes, 3 outcome comparisons)", the same words as its ring);
2. "Original outcome: <code>. Required checks: <f> FAIL, <na> NOT_ASSESSED, <e> ERROR (of <n>)." (`original/outcome.json`; an audit run's root `outcome.json`);
3. up to four "<assertion> (FAIL): <label>" (for example "split.no_group_overlap (FAIL): the same subjects appear in training and testing"), then "and <k> more";
4. "Revision <candidates/c>, executed and verified: <code>; <k> FAIL → PASS." (the §4 "after" candidate only);
5. "Proposals were checked by ATLAS validation and not executed here." (a proposal with outcome `not_executed_here`);
6. "<Metric> (pooled), descriptive only: original <x>[, candidate <y>]." (`descriptive[metric.recomputed_primary]`, 4 decimals as the cards);
7. "This does not say the scientific claim is true or false." (always).

Each line carries its source in a `title`; the panel's source line says "from the run's verified files and fixed labels (src/atlas/ui/assertion_labels.json) only; no model-written text".

#### 11.2a Assertion labels (`src/atlas/ui/assertion_labels.json`)

One short plain-English label (at most 90 characters, plain words) per canonical assertion ID in `evaluation/assertion_definitions.json`, each saying what a FAIL of that assertion means. Fixed product copy written by the project: never generated at runtime and never taken from model output or from a run's files. A test requires exactly the same ID set as the frozen definitions. The briefing shows the label; the formal definition stays in the drill-down (§11.3) as "definition (policy-v1.3)". A missing label renders "label not recorded." (it cannot happen while the test passes).

#### 11.2b The integrity count (`hud.integrity_count`)

`recorded.verify` returns the checks; `hud.IntegrityCount` counts them once: file hashes recomputed from disk (`hashes`), report outcomes compared with their verified `outcome.json` (`comparisons`, the report-key checks) and the items that differ. The unit is "recorded items" and the wording is `"<n> of <total> recorded items verified now (<h> file hashes, <c> outcome comparisons)"` (changed evidence: `"<k> of <total> recorded items differ (...)"`), with the breakdown computed, never written by hand. The ring's accessible title and its caption, the briefing's first line, the evidence panel (intact, changed and unverified states) and the hosted live view's caption all use it, so the same run never shows two numbers. (Before fix pass 1 the briefing counted only the file hashes, 46, while the ring counted every check, 49.)

### 11.3 Evidence drill-down (`hud.inspect_records`, `hud.inspection`, `hud.record_body`)

Each FAIL, NOT_ASSESSED or ERROR tile of the check matrix (original and verified revision) is a `<details>` whose `<summary>` is the tile itself: no Streamlit widget, no rerun. Enter and Space toggle it (native); Chromium exposes the summary as a disclosure with its expanded state (read from its accessibility tree: false, true, false), so no static `aria-expanded` is written (it would go stale). The open frame carries the accent corner brackets and shows, from the assertion's verified check file (or the run's verified `outcome.json` when no check file lists it): status, reason, evidence_valid, the assertion's frozen formal definition ("definition (policy-v1.3)", in full, Markdown marks removed, from `evaluation/assertion_definitions.json`), limitations, each evidence artifact with its full sha256 (wrapped, `text`), and the observed object as key/value rows (nested objects as dotted keys two levels deep; lists as "<n> items: a; b; … and <k> more", six shown; deeper values summarised by size). The source line names the file and `assertions[assertion_id=…]`. IDs: `atlas-insp-sum<letters>-<scope>-<runhash8>-<instance>`; the frame is `aria-labelledby` its summary. The tile's direction and its "Inspect"/"Close" cue share the tile's end slot, so paired columns keep equal widths. The frame fades in over 120 ms when opened (a response to the person's action; none under reduced motion).

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
| Hosted live unavailable | stone | LIVE UNAVAILABLE | open Overview & Cases |
| Hosted budget exhausted | amber | BUDGET_EXHAUSTED | open Overview & Cases |
| Hosted session crashed | violet | ERROR | open Overview & Cases |

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

## 12. Story layout, slice 1 (2026-10-20; branch `ui-story`, not merged, not reviewed)

Goal: a non-expert judge understands a case in about ten seconds and can click to go deeper. Everything in §1–§11 still applies (truth rules, the one verification gate `results.gate` and the `finished_run` guard, escaping, the briefing's provenance, motion once per run per session, the ID scheme). No engine, evaluator, policy, provider, spending or verification logic changed.

### 12.1 Information architecture

Streamlit's native multipage navigation (`st.navigation(position="top")` in `app.py`; one file per page in `app_pages/`), the same four pages in hosted and local mode:

| Page | Hosted | Local |
| --- | --- | --- |
| **Overview & Cases** (default) | the story of each bundled case (`atlas.ui.story`, entry `results.case_page`) | the same, from the same bundle (`demo/recorded`) |
| **Try It Live** | the existing live session (`hosted.page.live_page`) | the existing "Run a project" / "Open a recorded run" page, moved unchanged from `app.py` into `atlas.ui.local_page` |
| **ATLAS Checks vs. Model Alone** (named "AI Agent vs. Model Alone" until the copy fix pass, §15) | "Coming in slice 2" | same |
| **How It Works & Limits** | "Coming in slice 2" | same |

The hosted sidebar (capability badges) is drawn on every page (`hosted.page.sidebar`). The local Overview notes a run waiting for approval and links to Try It Live. `ATLAS_UI_CASES_DIR` (set only by whoever starts the server; the browser tests use it) points the Overview at another folder with the bundle's layout, verified exactly like the bundle.

Overview & Cases, top to bottom:

1. **Header**: "ATLAS", the tagline, and the "Why it matters" line with its source link.
2. **Case cards** (`st.columns`, three; the selection in `st.session_state["story_case"]`, the first by default): the title (the card's button, stretched over the card so the whole card is the click target; its focus ring is the card's), the outcome codes from the case's own verified files (original → executed revision), a one-line description of what the case is (never its outcome), and "Showing this case" on the selected one. A bundle that does not verify shows "evidence changed" and no code.
3. **The selected case** (`results.case_page`): the banner, then the gate. On a failed verification only the evidence-changed panel is drawn: no verdict bar, no step, no outcome (`tests/unit/test_ui_story.py`, `tests/acceptance/test_scenario13_story_tampered.py`).
4. **Verdict bar** (first in the case content; placed at the top, not CSS-sticky, so it does not cover the steps on a phone): the integrity ring ("<n>/<n> INTACT · recomputed now"), the reticles with their caveats, the deterministic verdict line, and the Expert view toggle.
5. **Five steps**, native `st.expander`s (keyed `step-1` … `step-5`; `<details>`/`<summary>`, so keyboard operable with the browser's own expanded state), each headed "<n> · <title> — <summary>" with a summary generated from verified data. Step 2 is open by default.

| Step | Plain | Expert view adds |
| --- | --- | --- |
| 1 The claim | the claim statement from the recorded manifest (verified path only) | its run-relative source, the claim fields |
| 2 What the checks found (named "The leak" until §15) | the compact leak map and the fit-scope flow (original \| verified revision), their reason sentences, the analogies | sources, the drill-down (inspection frames of FAIL / NOT_ASSESSED / ERROR), the Finding card |
| 3 The AI's fix (untrusted) | each proposal: its engine outcome in words, the diff in the model-written frame (`st.code`, `inert`), "Proposed by <model>; ATLAS does not trust this text.", the rationale (`st.text`); or "No revision was proposed." | the Revision card (hashes, complete files, candidate details) |
| 4 Human approval & sealed run | each approval from the verified log, in words; each execution from its verified `execution.json`: isolated Docker runner, no network, non-root user, read-only filesystem (only the facts its recorded `docker_args` state), container removed; "not executed here" for hosted proposals | the approvals table, the sources |
| 5 Verified evidence (named "Verified proof" until §15) | the check tiles before/after ("FAIL → PASS"), the descriptive metric line, the track (stages only), the plain briefing, the recorded-evidence panel (no hash table) | IDs, the drill-down, the Analysis card (track with counters, budget, trace), the Comparison and Trust and export cards, the full briefing and the integrity table |

Expanders may nest in Streamlit 1.66 (only dialogs may not), so the existing cards sit inside their step in Expert view. Each plain step ends in one "Show expert detail" line (step 2: "Show me the evidence"): a button that turns Expert view on.

### 12.2 Plain English and Expert view

- One session-wide setting (`st.session_state["expert"]`, written by the toggle and the step buttons), off by default.
- **Plain** hides assertion IDs, SHA-256 hashes, file paths (run-relative ones too), source captions and source `title`s (the ring segments' included), cost figures and model/request counts. The banner is one line from the report ("Recorded live run · Nemotron · finished 2026-10-18 · not re-run here"; a fixture run says "scripted replies, no model called"); the HAR citation drops its repository file reference. Tiles lead with the assertion's description, then "Found: <failure label>" on a FAIL, its reason sentences, and on a documented-declaration PASS "PASS rests on a documented declaration that ATLAS did not verify."
- **Expert** shows everything shown before this slice, with run-relative paths only.
- **No local filesystem path** in either mode on any page: the local recorded-runs captions name the folder ("the repository's `runs/` folder", "the folder named by ATLAS_UI_RECORDED_DIR"), never its absolute path.
- Model-written text (diffs, rationale) is shown verbatim in its frame in both modes.

### 12.3 The copy files

- `src/atlas/ui/copy.py`: every new user-visible sentence and template (header, pages, cases, banner, verdict lines, step titles and summaries, analogies, reason templates, plain HUD text, the replay disclosure and HAR citation, which `hosted.page` keeps under their old names). Templates take named fields only, filled from verified files; a template with an unrecorded field is not shown. `test_all_new_copy_comes_from_the_copy_files` parses `story.py` and `app_pages/*.py` and fails on any inline sentence literal.
- `src/atlas/ui/assertion_labels.json`: per canonical assertion ID, `failure` (the earlier labels, unchanged; FAIL lines and the briefing) and `description` (what the check verifies; tiles of any status). A test requires exactly the canonical ID set and both fields. The four temporal descriptions were written from their frozen definitions, for review.
- Rules: no claim stronger than its source; NO_VIOLATION_FOUND keeps its caveat; descriptive metrics never get causal words. The case title "A leak caught and fixed" is the task's own fixed copy (UI_SPEC §1.1 otherwise avoids "fixed"; the title is the only place it appears).

### 12.4 Reason sentences (`hud.reasons`)

One fixed template per assertion that records counts (`copy.REASONS`), filled only from that assertion's own `observed` object in its verified outcome; when a needed field is absent or of the wrong type, no sentence (never "null"). Examples (live6 original): "8 subject_id values appear on both sides of the split in 4 of 4 folds"; "SelectKBest was fit once on 160 rows (scope: global) and reused in 4 folds". `split.no_window_overlap` records routes, not counts: status only. Shown under the leak map and the flow, in the tiles and in the drill-down.

### 12.5 Components changed

- **Compact leak map** (both modes, every view): 15 px squares, filled red (on both sides) or a dotted outline (no shared groups), the legend in text at every width, the full cell text in `title` and `aria-label`; no letters in cells. HAR flawed (21 × 5) and live6 (8 × 4) fit their pane at 1280 × 800 without clipping (scenario 12); at 390 px the region keeps `role="region"` and `tabindex="0"`.
- **Ring caption**: no breakdown ("recomputed now", plus where from in Expert view); the breakdown is in the evidence panel (and in the ring's `<title>`).
- **Item 5, the symmetric "after" fit diagram: drawn.** Every candidate `fit` event in `candidates/c1/provenance.jsonl` records `fold` and `class` as fields, so the candidate's flow is one green lane per fold (`hud.fold_fits`, `hud._fold_lanes`), source "candidates/c1/provenance.jsonl · events type fit · fold, class", status from `candidates/c1/checks/fit_provenance.json`. It is read only when the file is in the verified set, and only for a candidate whose assertion PASSes with no origins; if any fit event lacks its fold, nothing is drawn (the fold is never derived from row sets).
- `results._cards` is split into `analysis_section`, `finding_section`, `revision_section`, `comparison_section` and `trust_section` (the same cards in the same order), so Expert view can place them in their steps.

### 12.6 Motion

The three beats in the verdict bar (and step 2's diagrams) play once per case per session (`results.HUD_PLAYED`, keyed by the run label); a step's content reveals in 200 ms when it opens; on narrow screens the leak map's squares fade in (200 ms) when the toggle switches panes. Nothing else is new; nothing loops; none of it runs under `prefers-reduced-motion: reduce`.

### 12.7 Evidence

`runs/ui-story/screens/` (git-ignored; settled full-page captures, top to bottom, at 1440 × 900, 1280 × 800 and 390 × 844): `s12_01_overview_{live6,harflawed,harclean}`, `s12_02_live6_step{1..5}`, `s12_03_live6_expert`, `s12_04_try_it_live_unavailable`, `s12_05_{agent_vs_model,how_it_works}`, `s12_06_tampered_live6`. Full suite: `runs/ui-story/full.log`.

## 13. Slice 2 (2026-10-20; branch `ui-story`)

Everything in §1–§12 still applies. No engine, evaluator, policy, provider, spending, approval or verification logic changed: the tamper demo and the comparison page call the existing `atlas.ui.recorded.verify` and `atlas.ui.artifacts.sha256_file` unchanged. All new copy is in `src/atlas/ui/copy.py` (section "Slice 2"); `test_the_new_modules_carry_no_inline_sentence` checks `versus.py`, `limits.py` and `tamper.py` as slice 1's test checks `story.py` and the page files.

### 13.1 Slice 1 fixes

- **A1, the case card's label.** Streamlit pulls every Markdown block up by 1rem at its bottom (`margin-bottom: -1rem` on `stMarkdownContainer`). That pull-up ate the card's 12 px bottom padding, so "Showing this case" (the card's last line) ran 2 px past the card's bottom edge at 1440 × 900 and 1280 × 800. The card body now keeps its full height (`.st-key-case-body-* [data-testid=stMarkdownContainer] { margin-bottom: 0 }`). Scenario 14 measures, at 1920, 1440, 1366, 1280, 1024, 800 and 390 px wide and for each selected case, that the label and every card's last line end above the card's bottom padding.
- **A2, step 4 of an audit-script run.** When every recorded approval has the T-09 audit script's approval reason (`t09_task_authorized_original`, `story.SCRIPT_REASONS`), no model proposed anything, the run is not live, and only the original ran, in the isolated Docker runner, the step 4 summary is "No AI agent took part: the audit script approved and ran the original in the isolated Docker runner." The approval line in the body reads "approved by the audit script, without a typed confirmation". The rule follows the recorded reason, not the case name: a renamed copy still matches, and the same run with any other reason does not.

### 13.2 ATLAS Checks vs. Model Alone (`atlas.ui.versus`; renamed in §15, file and URL path unchanged)

- **Data:** only `evaluation/results/t11-live-20261019/` (`results.md`, `scores.json`, `suite.json`) and `evaluation/expected.json`.
- **Gate:** before anything is shown, `versus.verify` recomputes each result file's SHA-256 and compares it with the table in that folder's `README.md`. `expected.json` is compared with the hash `suite.json` recorded for it (`inputs`). Any difference, or a missing file, draws only the evidence-changed panel: the code, the count of differing files, their table and the gate note. No result number, chart, caveat, finding, cost or review line appears. This detects changes since recording; it does not authenticate files whose recorded hashes were rewritten too.
- **Order (plain view):**
  1. The question.
  2. One setup sentence.
  3. **The caveats**, always visible (no expander): development cases; the flaw text the model could read; ATLAS evaluated once per case (deterministic by design); invalid replies unscored; small numbers; data seen by ATLAS but not by the model.
  4. The chart.
  5. The data table.
  6. "What this means": findings 1, 2, 3, 5 and 6 of docs/EVALUATION.md "Findings (descriptive)", **copied exactly** (`copy.T11_FINDINGS`; a test compares them with the document). Expert view shows all seven.
  7. A line mapping leg (a) and leg (b) to ATLAS and the model alone.
  8. The cost ("estimate, not billing").
  9. "Claims reviewed by Gemini (2026-10-19)".
  10. The intact count.
- **Expert view adds:** the run folder, model, seed and policy; the file and hash table; the expected IDs per case; ATLAS per case; every model-alone trial; the totals; the sources.
- **The chart** (dataviz skill, followed):
  - **Form:** three measures in different units, so the chart is one figure of three small panels, each with its own axis from zero (never a dual axis).
  - **Panels:** predeclared violations found (as a share: ATLAS 8 of 8 assessable; the model alone 19 of 20 on the same 8 and 19 of 23 overall); false alarms (0 vs 2); invalid answers (none vs 3 of 12, on an axis of the 12 scheduled replies).
  - **Data:** every value comes from `scores.json` (`versus.figures`). "On the same 8" is the expected IDs minus ATLAS's coverage gaps, scored over the valid trials.
  - **Colour and labels:** emphasis form, ATLAS in the one accent `#67E8F9` and the model in neutral `#94A3B8`. Values are printed at the bar ends in text colours (inside the bar in dark ink when it would overflow on phones). The legend is always present. Bars are 18 px with a 4 px rounded data end and square at the baseline; hairline solid grid. No 3D, no motion.
  - **Accessibility:** `role="img"` with `<title>` and a `<desc>` text alternative, a `<title>` tooltip per bar, and the data table.
  - **Layouts:** two (wide: labels left; narrow, under 640 px: labels above), switched by CSS.
  - **Palette validator** (`validate_palette.js`, run in a headless browser on #0F1720 and #0A0F14):
    - pass: CVD separation ΔE 15.2 (deutan), normal-vision ΔE 18.2, contrast 12.4:1 and 7.0:1;
    - fail, expected for this form: the categorical lightness band and chroma floor (the gray is the de-emphasis colour by design; the accent is the design system's own).

### 13.3 How It Works & Limits (`atlas.ui.limits`)

- **How it works**, in five short steps: the evaluation is run; deterministic checks decide; the AI may propose a revision, which ATLAS does not trust; a human approves by typing the code hash; the revision runs sealed and is re-checked by the same checks.
- **The diagram:** a static diagram of those steps, labelled "Diagram", with no number. Its only motion is one 400 ms fade the first time it is shown in a session (`limits_diagram_played`), never under reduced motion.
- **Safety in plain words:** six items. Isolated Docker runner; typed approval bound to the code hash; the AI's text is never evidence; spending reserved before every request, with caps; the hosted demo executes nothing; recorded runs re-verified before display.
- **Limits:** the 13 README "Limitations" in plain words (`copy.LIMITS_PLAIN`; none weakened; a test checks the count and each item's key terms). Expert view adds each item's original wording, read from README.md at render time so the two cannot drift.
- **What ATLAS does not do:** it does not prove a claim true; it does not check data collection or labelling; it supports small tabular classification with three claim types.
- **Expert view** cites each item's README, SPEC or HOSTED_OPERATIONS section.

### 13.4 The tamper demo (`atlas.ui.tamper`; Overview, below the verdict bar)

- **Where:** a bordered "Try tampering" panel, in plain and Expert view, drawn only after the case passed the gate.
- **Files:** the visitor picks one file from a short fixed list (`copy.TAMPER_FILES`), offered only when the run recorded a hash for it:

  | Case | Files offered |
  | --- | --- |
  | live6 | `original/outcome.json`, `candidates/c1/outcome.json`, `original/execution.json`, `agent_log.jsonl` |
  | HAR flawed and HAR clean | `original/outcome.json`, `original/execution.json`, `agent_log.jsonl` |

- **One run of the demo (`run_demo`):**
  1. Scan the run without following links. A symbolic link or other reparse point refuses the demo, and so does a total size over 50 MB (fixed messages).
  2. Verify the original (it must be intact) and hash every file.
  3. Copy the run to `tempfile.mkdtemp(prefix="atlas-tamper-")`, refused if inside the repository.
  4. Change the chosen file's **last byte** (a line break becomes a space, which keeps the JSON valid, so exactly that file's hash differs).
  5. Run `verify` on the copy.
  6. Delete the temporary directory in a `finally` (also on an error).
  7. Verify the original again: every file's hash must equal step 2's. Otherwise `OriginalChanged`, and nothing from the demo is shown.
- **What the page shows:** the real result, for example "1 of 49 recorded items differ: the original's recorded result — outcome withheld". Expert view names the item and shows the recorded and recomputed hashes. Then the statement "This copied the recorded run, changed one byte in the copy, and ran the real check on it. The original recording is untouched.", the byte changed, and the original's re-check ("49 of 49 recorded items verified, and every one of its 85 files is byte-for-byte unchanged"). An error shows one fixed message, never exception text.
- **Limits:** one demo at a time per session (a non-blocking lock) and at most 5 per session per hour (`tamper.SessionLimit`, in the session state); runs over 50 MB are refused.
- **Nothing executes except hashing:** no project code, no subprocess, no network. Hosted mode therefore needs no execution guard on this path, and `refuse_if_hosted` is not called, because nothing it guards runs. A test runs the demo with ATLAS_HOSTED=1 under a tripwire on `subprocess`, `os.system`, `socket.connect` and `refuse_if_hosted`.

### 13.5 Evidence

- **Screenshots:** `runs/ui-story/screens2/` (git-ignored; settled full-page captures at 1440 × 900, 1280 × 800 and 390 × 844): `s14_01_overview_live6`, `s14_02_harflawed_step4`, `s14_03_agent_vs_model_{plain,expert}`, `s14_04_how_it_works_{plain,expert}`, `s14_05_tamper_{before,after}_live6`.
- **Tests:** `tests/unit/test_ui_slice2.py`, `tests/acceptance/test_scenario14_slice2.py`.
- **Full suite:** `runs/ui-story/full2.log`.

## 14. Slice 3 (2026-10-20; branch `ui-story`): report, layout, accessibility

Everything in §1–§13 still applies. No engine, evaluator, policy, provider, spending, approval or verification logic changed, and neither did the T-11 hash gate or the tamper demo's safety rules. All new copy is in `src/atlas/ui/copy.py` (sections "Slice 2" and "Slice 3").

### 14.1 Stale limitations (README, then the page)

- **T-06 limitation:** "schema failures in 5 of 8 live runs (runs 1 to 8)", on the existing basis: runs 1 to 8, with run 3 and its retry 3b counted as one run. Runs with at least one schema failure: 2, 3b, 5, 7, 8; none in 1, 4 or 6. The Devpost draft's "ended" figure keeps its own basis: 4 of 8 (2, 3b, 5, 8).
- **Hosted limitation:** established on 2026-10-19 for the private app (Nebius connectivity, the locked build, the smoke test on both routes); not yet the signed-out check or availability through 2026-12-15 (HOSTED_OPERATIONS.md §9).
- The limits page carries both in plain words; Expert view reads the README's wording at render time.

### 14.2 The comparison page, plain view

- **Plain view:** "What this means" is four plain-words items (`copy.VS_MEANS_PLAIN`). `tests/unit/test_ui_slice3.py` checks every number in them against `scores.json`, the recorded har_flawed outcome or the reviewed findings: 19, 23, 9, 2, the two clean projects, 8, the one coverage gap, 3, and 3 of 12.
- **Expert view:** the reviewed findings exactly, in their place.
- The caveats are visible in both views.

### 14.3 Overview layout

- **C1, the tamper demo:** a collapsed expander directly after step 5, "Try tampering: change one byte in a copy and watch the check catch it". Its behaviour, limits and copy are unchanged. Its file picker has one widget key per view, because a picker redrawn with other labels under the same key could not open its list.
- **C2, the Expert view switch:** beside the page title, top right, on every page that has an Expert view (Overview, ATLAS Checks vs. Model Alone, How It Works & Limits). Try It Live has no Expert view and no switch. On the Overview the switch is not drawn when the selected case fails verification, so that page still shows only the cards and the evidence-changed panel.
- **The report button:** the verdict row now holds the verdict line and "Download audit report".

### 14.4 The one-page audit report (`atlas.ui.report`)

- **Where:** "Download audit report" (`st.download_button`, `on_click="ignore"`).
  - On each verified case view (Overview), file `atlas-audit-<case>-<outcome>.html`.
  - On each verified finished run (`results.finished_run`: the local run page, both recorded-run viewers, the hosted live session), file `atlas-audit-<run folder>-<outcome>.html`.
  - The outcome in the name is the original evaluation's verified outcome code.
- **Gate:** `build` is called only after the gate, and it checks again (`NotIntact`). After a failed verification there is no button.
- **Contents:**
  - ATLAS and the tagline; the case or run, with the banner line.
  - The claim from the verified manifest, which includes the ATLAS-authored-variant note on har_flawed.
  - The outcome before and after, with "This does not say the scientific claim is true or false." and the verdict lines.
  - The required checks: the plain description from `assertion_labels.json`, the canonical ID, and the status before and after.
  - The step 2 summary and the reason sentences of the original's FAILs.
  - The steps 3 and 4 summaries, with the approval and sealed-run lines.
  - The integrity count ("N of N recorded items verified when this report was generated"), the recorded SHA-256 of each outcome file, and each approved code hash.
  - The UCI HAR citation on the HAR runs, and the "Why it matters" line with its source URL as plain text.
  - The footer: the ATLAS commit (read from the git metadata as files, with no git command; left out when unreadable), the policy version, and the UTC time.
- **What it never holds:** model-written text (no rationale, no reply, no diff). A test checks the live6 report against every model text, reply and diff line. Every value is escaped through `hud.esc`.
- **Self-contained:** one inline style sheet; no script, link, image, `src`, `href`, `url(` or `@import`.
- **Print:** a print style (`@page { size: portrait }`, compact type) fits one page on A4 and on Letter. Scenario 15 counts the pages of Chromium's PDF for live6 and har_flawed. *Superseded by §15 (R1): 15 mm margins and 10.5 pt type; the report now prints on two pages.*
- **Deterministic:** byte-identical for the same bundle and an injected clock. It executes nothing (tested with ATLAS_HOSTED=1 under a subprocess, socket and `refuse_if_hosted` tripwire).

### 14.5 Accessibility

- **axe-core:** from the dev-only `axe-playwright-python` 0.1.8, which bundles axe-core 4.12.1 (MPL-2.0; THIRD_PARTY_NOTICES.md). Nothing changed at runtime: `requirements.txt` is the `--no-dev` export.
- **Where it runs:** scenarios 15 (hosted) and 16 (local), on every page at 1440 × 900 and 390 × 844:
  - Overview for each case, plain and Expert;
  - Try It Live, hosted and local;
  - the comparison page and How It Works & Limits, plain and Expert;
  - a finished-run view;
  - the evidence-changed panel.
- **Classification:** each serious or critical node counts as ATLAS's markup (inside `hud*` HTML or a Markdown block ATLAS wrote; colour contrast always counts as ATLAS's) or as Streamlit's.
- **Before the fixes** (28 page states):
  - ATLAS markup: link-in-text-block 14 nodes (the "Why it matters" Source link); scrollable-region-focusable 42 nodes (hashes in `st.table` cells became tiny scroll regions).
  - Streamlit's markup: scrollable-region-focusable 20 nodes.
- **Fixed** (`views.CSS`): links in running text are underlined; table cell content wraps (`overflow-wrap: anywhere` on the cell and its descendants, `overflow: visible`), so no scroll region appears.
- **Remaining** (21 nodes, Streamlit's markup, recorded and not patched): scrollable-region-focusable on Streamlit's own `st.table` scroll wrapper (wide tables) and `st.code`'s `<pre>` (diffs on phones). Moderate and minor findings remain too (heading-order, empty-table-header). They are recorded and not in scope.
- **Required regardless of axe:**
  - **Contrast:** unit tests over every theme token and every CSS `color:` value in the UI modules. Text is at least 4.5:1 on both dark surfaces; the lowest is badge text on its badge, red at 5.37:1. Chart marks and the accent are at least 3:1. The dark ink used on light fills is at least 4.5:1 on each fill. The report's light palette is at least 4.5:1 on white and on its table header.
  - **Focus:** a visible focus indicator on every control reached by Tab. Scenario 15 walks the Overview (23 stops) and the comparison page (9 stops). Added: the navigation links, the focusable main region and the switch (its own outline was drawn on its hidden input).
  - **Charts and diagrams:** every one has `role="img"` and a name (the comparison chart, the HUD's SVGs, and the limits diagram, now `role="img"` with its aria-label; the steps list is its text alternative).
  - **Reduced motion:** respected, as before.
- **Evidence:** `runs/ui-story/a11y/` (git-ignored):
  - `before/` and `after/`: the probe's axe JSON, before and after the fixes;
  - `final/`: the tests' axe JSON, summaries, keyboard-walk JSON and one screenshot per Tab stop (`tab_overview_NN.png`, `tab_agent_vs_model_NN.png`);
  - `SUMMARY.md`.

### 14.6 Evidence

- **Screenshots:** `runs/ui-story/screens3/` (git-ignored; settled full-page captures at 1440 × 900, 1280 × 800 and 390 × 844): `s15_01_overview_live6`, `s15_02_overview_live6_tamper_open`, `s15_03_agent_vs_model_{plain,expert}`, `s15_04_how_it_works_plain`, `s15_05_report_{live6,harflawed}_{screen,print}`.
- **Tests:** `tests/unit/test_ui_slice3.py`, `tests/acceptance/test_scenario15_slice3.py`, `tests/acceptance/test_scenario16_a11y_local.py`.
- **Full suite:** `runs/ui-story/full3.log`.

## 15. Copy accuracy fix pass (2026-10-21; branch `ui-story`)

Gemini Argon (high effort) reviewed all user-facing copy against README, docs/EVALUATION.md, docs/HOSTED_OPERATIONS.md, `evaluation/assertion_definitions.json` and the T-11 `scores.json`. This pass changes user-facing copy and the report's print CSS only; no behaviour changes. Each item's old text, new text and source quote are in `runs/ui-story/copy_changes.md` (git-ignored).

### 15.1 Copy

- **Tagline:** "ATLAS checks a machine-learning evaluation for leaks between training and test data, shows its evidence, and tests a proposed fix in an isolated container." (Overview header and the report.)
- **Steps:** step 2 is "What the checks found" for every case (the report's section too); step 5 is "Verified evidence". The analogies still render only when their check FAILs (none on har_clean).
- **Comparison page:** renamed "ATLAS Checks vs. Model Alone" (title and navigation label; the file `app_pages/agent_vs_model.py` and the URL path `/agent_vs_model` are unchanged).
  - The model's figures are labelled as detections summed over usable answers: "19 of 20 detections" (same 8 problems) and "19 of 23 detections" (all 9 problems). ATLAS's figure is "8 of 8 assessable (1 of 9 not assessed)".
  - One line under the chart explains the count. Plain item 1 now reads 9 planted problems, 5 usable answers, 23 chances, 19 named.
  - Every number is computed from `scores.json` and `expected.json` (`versus.figures`: `expected_total`, `not_assessed`, `flawed_valid`, `clean_valid`) and tested.
  - The wide chart is 820 units with a 300-unit right label margin (container 860 px), so the longer ATLAS value is not clipped; the phone layout is unchanged.
- **Verdict:** a passing revision "passes every required check within the coverage shown".
- **Case cards:** both HAR projects are "written by ATLAS's authors"; har_clean names its protocol (each person on one side of the split; every step fit inside each fold).
- **Leak map:** "Groups on both sides of the split, by test fold" on both panes (Expert: "Groups with recorded overlap (observed.overlapping_groups)").
- **How It Works & Limits:**
  - Approval is bound to the snapshot and code hashes, for the original and each revision.
  - The hosted demo executes no project or candidate code and checks proposals in a hosted live session.
  - The runner sentence states the fail-closed rule.
  - "What ATLAS does not do" names feature extraction and normalisation before the supplied table.
  - The T-06 figure follows README: "schema failures in 5 of the 8 live runs (runs 1 to 8, with 3 and 3b counted as one)".
- **Assertion labels:** the split labels say "within a fold" / "a fold's split", following their definitions. `repeated_measures_rule` names "a unit (or its containing group)" (routes A and B). The cutoff label names the declared gap. The two fit descriptions say "recorded" (and "supported ... on its path"). The briefing's label-length test cap is now 120 characters.
- **Reason sentences, nothing overlapping:** `copy.REASONS_NONE` ("No subject_id value appears on both sides of the split in any of the 5 folds"). This replaces "0 ... in 0 of 5 folds" for the row, source-observation, group, sampling-unit and repeated-measures templates. `hud.reasons` picks it when k = 0.

### 15.2 Report print (R1; supersedes the print line of §14.4)

- `@page { margin: 15mm }`.
- On screen, `main` is at most 190 mm wide, centred.
- In print: 10.5 pt base type (tables 9.5 pt, hashes 8.5 pt), and every cell wraps (`overflow-wrap: anywhere`; hash and ID cells break anywhere).
- Measured in Chromium: every table fits the printable width (A4 681 px, Letter 703 px) with no overflow. The report now prints on **two pages** on A4 and Letter; the same content does not fit one page at this size. Scenario 15 asserts no overflow and at most two pages.
- Content and determinism are unchanged by R1.

### 15.3 Evidence

- `runs/ui-story/copy_changes.md` (old, new, source and disposition per item; the proof/safety grep).
- Screenshots: `runs/ui-story/screens4/`.
- Tests: `tests/unit/test_ui_copy_fix.py`, with the updated slice 1-3 tests.
- `runs/ui-story/check_recorded4.txt` (byte-identical to `check_recorded3.txt`).

## 16. Readability pass: headline first, one idea per screen (2026-10-21; branch `ui-story`)

The task named this "§15"; §15 already records the copy accuracy fix pass, so it is §16. Everything in §1–§15 still applies. Layout, diagrams, navigation and plain-view copy only: no engine, evaluator, policy, `validate_diff`, provider, request body, spending, reservation, access, kill-switch, execution-guard, approval, recorded-run verification, release-review gate, T-11 hash gate, tamper-demo safety, escaping, briefing-provenance or audit-report change. New copy is in `src/atlas/ui/copy.py` ("Readability pass"); each sentence's source, and each moved item's new place, is in `runs/ui-story/copy_changes2.md` (git-ignored).

### 16.1 Plain-view rules

- **Goal:** a judge who is not an ML expert understands each page in about five seconds: one idea per screen, a visual that carries it, a short caption.
- **Plain view** shows an answer sentence or headline, one visual, a few large numbers and one-line items. Every existing detail is one click away ("Show more", "All …", "Data licence details") and in Expert view.
- **Expert view is unchanged:** it renders exactly what it rendered before the pass (`tests/fixtures/ui_readability/before.json`, recorded from `b690af2` by the script beside it; the browser innerText of all five Expert views was also byte-identical).
- **R0 layout:** the main content is at most 1150 px wide and centred (full width at or below 1150 px). Body text is 16 px: the paragraphs and list items of `st.markdown` blocks (one low-specificity rule in `views.CSS`) and the plain text ATLAS styles itself. The theme's base stays 15 px, so the HUD's own markup, captions, labels and tables keep the sizes their layout was tuned for: raising the base to 16 pushed the recorded-run viewer's hero 50 px below the first viewport at 1280 × 800 (scenario 8). Small grey text only for footnotes (captions). Scenario 17 checks the width, the centring and the 16 px body text.
- **R1 glossary:** "New to this? 4 terms", a popover beside the tagline (plain view only): Training data, Test data, Fold, Leak.

### 16.2 Always visible in plain view (never behind a click)

The outcome codes (case cards and the verdict bar); "This does not say the scientific claim is true or false."; "estimate, not billing" on any cost; the evidence-changed panel when verification fails; the claim line; the comparison's caveat line; the four key limits. Also kept visible: the replay disclosure, because its proposed replacement ("Every file is re-checked before display.") overclaims (§16.6).

### 16.3 The Overview story as a stepper (`atlas.ui.story`)

- **Above it:** the verdict bar (unchanged), then "Claim: <recorded claim>" (har_flawed's recorded statement carries its ATLAS-authored-variant note), then the "Show all steps" switch.
- **The stepper:** a step row (`st.segmented_control`, required, one Tab stop, arrow keys inside; "1 Claim · 2 What the checks found · 3 The AI's fix · 4 Approval & sealed run · 5 Verified evidence"), Back and Next (`st.button`, disabled at the ends), and "Step n of 5" in a `role="status"` `aria-live="polite"` region. Visible focus on every control. At most a one-time 200 ms fade when the step changes (a new step's body is a new element), never under reduced motion.
- **Default and state:** every case opens on step 2. The step is kept per case in `st.session_state["story_step_<case>"]` (a plain key; the widget `stepper-row-<case>` is synced from it); selecting another case starts that case at step 2.
- **Each step:** a one-sentence headline (the step's existing summary line), one visual, then "Show more" holding only the rest of the step's previous content (never the headline, a visual or an analogy):
  1. the claim intro and the claim; for an `unseen_group` claim, a concept diagram (two groups of person markers, "Training people" and "Test people", with a gap; caption "The claim: the model works on people it has never seen."); none for other claim types.
  2. the leak map and fit-scope flow (unchanged), then one box with both analogy lines (each still only when its check FAILs).
  3. one chip per proposal from the verified agent report, in order: "Revision n: approved and executed in the sealed runner" (only when its verified `execution.json` records `docker_isolated`, `completed`), "Revision n: rejected by ATLAS validation", or "Revision n: not executed"; with no proposal, the existing "No revision was proposed." line once. Model-written text only in Show more, in its untrusted frame.
  4. a concept diagram ("Code" → "Typed hash" → a locked "Sealed runner: no network · non-root · read-only"), then the step 4 summary line (for the T-09 runs, "No AI agent took part: …").
  5. "What changed" (the checks whose recorded status changed, "<plain label>: FAIL → PASS"), or "What failed" (FAIL, NOT_ASSESSED and ERROR with plain labels), or "All required checks passed"; then the integrity line "Evidence intact: v of t recorded items verified now" (shown once when it is already the headline); Show more holds the check matrix, the metric line, the track, the briefing and the recorded-evidence card.
- **The concept diagrams** carry no number (tested on their rendered text and aria-label), are labelled "Diagram", have `role="img"` and a name, and are static.
- **"Show all steps"** shows the five expanders exactly as before (tested equal to the baseline). **Expert view** shows them as before.
- **The tamper demo** stays a collapsed expander after the stepper (unchanged behaviour).

### 16.4 Streamlit implementation, and verification on every run

- Native widgets: `st.segmented_control`, `st.button`, `st.toggle`, `st.expander`, `st.popover`, `st.metric` in `st.columns`. Custom HTML only for the existing HUD components and the two concept diagrams, escaped through `hud.esc`.
- **The stepper is an `@st.fragment`**, so a step change reruns only the stepper. At the top of every run of the fragment (the full page's and each step change's) it re-reads the agent report and re-runs the same recorded-run verification the page's gate uses (`results.verification`, i.e. `recorded.verify`) from the files on disk. If that is not intact it calls `st.rerun(scope="app")`, and the full page's gate then draws only the evidence-changed panel. The fragment builds the HUD, facts and summaries from that fresh verification only: it never draws step content from a failed or an earlier verification.
- **Nothing is cached:** no `st.cache_data` or `st.cache_resource` on the recorded-run verification, the T-11 hash gate or anything they read (the UI's one cache is the local page's 30-second Docker probe, which no verification reads; a test pins this). "Verified now" stays true on every render, full page or fragment.
- Tested: a byte changed in a copy between two full renders of the same session, and a byte changed after the page rendered followed by a click on Next inside the stepper, both leave only the evidence-changed panel (scenario 17; the second in AppTest too, by making the stepper's own verification fail).

### 16.5 The comparison page and How It Works & Limits (plain view)

- **Comparison (`atlas.ui.versus`):** under the title, one answer sentence ("On these 4 projects, ATLAS's checks found all 8 problems they can assess, with no false alarms. The AI model on its own made 19 of 20 detections on those same 8 problems (19 of 23 overall), raised 2 false alarms, and gave 3 unusable answers out of 12."); the caveat line, then "All caveats (6)"; three stat tiles (bordered columns, two native metrics each, qualifiers as captions: "Problems found" 8 of 8 | 19 of 20, "False alarms" 0 | 2, "Unusable answers" none | 3 of 12); the chart and its note (unchanged); then "Data table", "What this means in detail", "About this comparison" (the question and setup); one footnote line (cost, estimate not billing · review · result files intact). Every number comes from the verified `scores.json` and `expected.json` and is tested.
- **How It Works & Limits (`atlas.ui.limits`):** the diagram (unchanged); five one-line steps under the diagram's short titles; six safety tiles (title and one line; the "Tamper check" tile keeps the existing sentence, §16.6); "Key limits" (four); "All limitations (13), in full" (the intro, the 13 plain limitations and "What ATLAS does not do", unchanged).
- **Try It Live:** R0 applies; its controls and text are unchanged.

### 16.6 Copy not applied (unsupported), and word budgets

- **Not applied** (the existing text is kept): "Every file is re-checked before display." and the tamper tile's "Every recorded file is re-hashed before display; any change shows 'evidence changed'." (only the files with a recorded hash are re-checked: live6 has 85 files, 46 file hashes; `agent_report.json` is not hashed); "Recorded files unchanged since recording: N of N verified now" (N counts 3 outcome comparisons too).
- **Word counts** (innerText of `[data-testid="stMainBlockContainer"]` at 1440 × 900, with the content of closed expanders, `details:not([open]) > :not(summary)` (Streamlit's expander DOM), and closed popovers excluded; words are whitespace-separated tokens with a letter or digit, so icon ligature names count):

  | Page | Before | After | Requested ceiling |
  | --- | --- | --- | --- |
  | Overview, live6, on load (step 2) | 625 | 591 | 220 |
  | Overview, live6, step 1 | (no stepper) | 356 | 220 |
  | ATLAS Checks vs. Model Alone | 570 | 278 | 140 |
  | How It Works & Limits | 975 | 304 | 230 |

  The ceilings are not met without removing items the task keeps visible: on the Overview, everything above the stepper (header, cards, recorded-run box, verdict bar with its outcome codes and caveats, claim line) is about 280 words, and step 2's unchanged leak map and fit-scope flow are 199; on the comparison page the unchanged chart is 85 and the answer and caveat line 77; on the limits page the safety tiles are 119 (40 of them the kept tamper sentence). Scenario 17 holds the pages at or under the measured counts.

### 16.7 Evidence

- Screenshots: `runs/ui-story/screens5/` (45: 15 states at 1920 × 1080, 1440 × 900 and 390 × 844).
- Tests: `tests/unit/test_ui_readability.py`, `tests/acceptance/test_scenario17_readability.py`, the updated slice 1-3 and copy-fix tests (the five-expander assertions now run with "Show all steps"), and the axe states added to scenario 15 (the stepper at steps 1, 3 and 5 with Show more open, "Show all steps", the glossary open, every plain expander open).
- Full suite: `runs/ui-story/full5.log`; `runs/ui-story/check_recorded5.txt` (byte-identical to `check_recorded4.txt`).
