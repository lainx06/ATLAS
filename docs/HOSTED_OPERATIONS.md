# Hosted demo operations (T-12)

How the limited hosted demo (SPEC §13) is configured, stopped, restored and inspected. Every cap change, credential change and deployment step needs the user's approval. Nothing here has been run against the deployed host or Neon yet: the hosted build is **built, awaiting review and deployment**.

## 1. What the hosted demo does

- **Selected only by `ATLAS_HOSTED=1`.** Without it, `app.py` is the unchanged local UI.
- **Recorded runs (always available).** The three bundled runs in `demo/recorded/` (live run 6 and the two HAR audit runs) are shown in the recorded-run viewer. Every recorded hash is recomputed before anything is shown; a changed byte shows "evidence changed since recording". Replay is disclosed on the page.
- **One live session per visitor session.** Nemotron (`nvidia/nemotron-3-super-120b-a12b`) inspects s01_faulty and may propose revisions. Each proposal passes `validate_diff` and is recorded "not executed here"; no candidate code runs on the host and no approval is asked. The original's findings come from live run 6's recorded, hash-verified trusted evaluation, labelled "computed by ATLAS's trusted evaluation functions (recorded 2026-10-18)".
- **Spending is enforced server-side** in Neon Postgres (`src/atlas/hosted/budget_store.py`) before every request, and the store fails closed.
- **The hosted environment executes nothing** (T-12 fix pass 1). With `ATLAS_HOSTED=1` every execution entry point refuses before any approval, file write, subprocess or network access, raising `atlas.hosted.HostedExecutionRefused` (a fixed message naming what was refused, never an environment value). Only exactly `1` counts; any other value or none leaves the local build unchanged. The entry points:
  1. `atlas.agent.controller.run_agent` with `hosted=False` (any local run, fixture or live; checks the process environment and a given `env`). `hosted=True` is unchanged: `NotExecutedHere` and the recorded original;
  2. `atlas.runner.docker.run_candidate`, the Docker runner's entry for the original and every candidate, before its run directory or the Docker CLI;
  3. `atlas.runner.trusted.run_trusted_fixture`, before its host subprocess;
  4. `atlas.agent.execute.execute_and_reevaluate` and `atlas.agent.controller.docker_original` (defense in depth; both also reach 2);
  5. `atlas.ui.worker.Registry.start`, before its run directory or worker process;
  6. `atlas.cli`, first after argument parsing, for every mode (audit, agent, live): a fixed message on stderr, exit 2, nothing run and no run directory;
  7. (T-12 fix pass 2) every process start in `atlas.runner.docker`: the two process helpers `_docker` (every short Docker CLI call) and `_spawn` (the container run), so no subprocess in that module can start; and, for a clear refusal at the entry, the maintenance entries `build_image`, `probe` and `python -m atlas.runner.docker build|probe` (`main`: a fixed message on stderr, exit 2, nothing started). `docker_evidence.verify_runner_image` refuses through `probe`. None of these is reached by the hosted page.

  Tests: `tests/hosted/test_hosted_boundary.py`.
- **A render failure shows no partial result** (T-12 fix pass 2). A finished run's results (the analysis, the outcome headline with its label and caveat, the tables, revision, comparison, trust and export) render into one clearable container (`atlas.ui.results.finished_run`, shared by the hosted live session, both recorded-run viewers and the local page). If any exception occurs while rendering it, the container is cleared, so no headline or partial result remains, and one fixed error is shown: "The results could not be displayed. The saved run record is unchanged; open it in the recorded-run viewer." No exception text is shown; the server log records only the fixed event code `results_render_failed` (no exception text, paths or values). The saved run record is not changed. Tests: `tests/hosted/test_render_failure.py`.

## 2. Secrets (Streamlit Community Cloud, app settings → Secrets)

Root-level TOML keys. Community Cloud also exposes root-level secrets as environment variables, which is how `ATLAS_HOSTED` reaches `app.py`. Placeholders only: never commit real values.

```toml
ATLAS_HOSTED = "1"
HOSTED_LIVE_ENABLED = "false"          # the kill switch; only the exact string "true" enables live calls
NEBIUS_API_KEY = "<the Token Factory key>"
DATABASE_URL = "postgresql://<user>:<password>@<host>/<db>?sslmode=require"
JUDGE_ACCESS_CODE = "<a long random code, at least 32 characters>"
```

- **Judge access code: at least 32 characters, random, generated at deployment:**

  ```powershell
  uv run --locked python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

  (43 characters.) A configured code shorter than 32 characters disables the judge route: it is treated as not configured, every visitor uses the public route, and each attempt with a typed code records the fixed event `judge_code_too_short` (no code text, no length). The comparison stays constant-time (`hmac.compare_digest`).

- The four secrets are read only on the server (`src/atlas/hosted/secrets.py`: `st.secrets`, then the environment; `.env` is never read).
- No secret is rendered, logged, written to a report or event, or bundled. The key goes only to the production client. Tests check this with synthetic markers (`tests/hosted/test_hosted_browser.py`).
- **Rotation:** change the secret in the app settings. For the judge code, rotate if the events table shows repeated `judge_code_rejected` (§5).

## 3. Kill switch

- **Off:** set `HOSTED_LIVE_ENABLED = "false"`, or delete it (absent means off).
  - New live sessions are refused before anything is contacted.
  - A session in progress is stopped before its next request: the switch is read again before every reservation, which is refused as `live_disabled`.
  - The page says "Live calls are unavailable; recorded runs remain available." Recorded runs keep working.
- **On:** `HOSTED_LIVE_ENABLED = "true"` (exactly; `True`, `1` or `yes` count as off). Turning it on needs the user's approval.

## 4. Caps and the budget store

| Cap row (`atlas_cap.cap_key`) | Cap | Route |
| --- | --- | --- |
| `public` | $3.00 in total | public |
| `public_daily:<YYYY-MM-DD>` (UTC) | $1.00 per day; a new row each day | public |
| `judge` | $5.00 in total | judge (correct access code only) |
| `session:<id>` | $0.0648 and at most 6 requests | the session's route |

Total authorized: **$8.00** (DECISIONS.md "T-12 decisions (user, 2026-10-18)", item 3).

**Spend bounds (what the caps do and do not guarantee).**

- The pool and session caps are **reservation bounds at the estimate ceiling** ($0.0108 per request): a request is admitted only if its ceiling fits every cap of its route and its session.
- Known usage is **settled exactly**, even when it is above the reservation. So usage reported above a reservation can take a pool past its cap by that excess. The caps are not an independently proven maximum invoice.
- The prompt-token ceiling is an ATLAS **estimate** (unchanged known limitation; `agent/budget.py`, `agent/nebius.py`); the provider does not enforce it.
- Daily keys use the **application server's UTC clock**, recomputed per reservation. Up to **$2.00** can therefore be admitted across two adjacent UTC days within any 24 hours, still within the **$3.00** public total.

- **How a request is admitted.**
  - Before each request, its ceiling ($0.0108: 12,000 input and 8,000 output tokens at the listed prices) is reserved against every cap of its route and its session, in one transaction, all or nothing.
  - It is marked dispatched before it is sent.
  - Afterwards it is settled at exact known usage, or held at the ceiling if usage is unknown.
  - It is released only if it was never sent.
  - Public traffic cannot touch the `judge` row.
- **Cap rows are created on first use** with the decided values. After that, the database row is authoritative; the application never resets or raises it.
- **Changing a cap (needs the user's approval each time).** Example, raising the public daily cap for one date:

  ```sql
  UPDATE atlas_cap SET cap_usd = 1.50 WHERE cap_key = 'public_daily:2026-11-02';
  ```

  To change the decided values for future rows, change `HOSTED_DECIDED` in `budget_store.py` (a reviewed code change) and update existing rows explicitly. Never lower `spent_usd` or `reserved_usd` by hand; use reconciliation (§6).
- **Exhaustion.**
  - When any cap cannot take one more request, a new session is refused and a running session stops before sending. The page says "Live demo budget reached for today; recorded runs remain available."
  - Nothing falls back to anything that spends.
  - The daily cap resets with the next UTC date. The public pool does not reset.

## 5. Reading the events table

`atlas_event` holds time, route, a fixed event code and an amount: never the key, an access code (typed or configured), the database URL, prompts or replies.

```sql
-- the last 50 events
SELECT time, route, event, amount_usd FROM atlas_event ORDER BY id DESC LIMIT 50;

-- failed judge codes per UTC day (count and time only)
SELECT date_trunc('day', time) AS day, count(*) FROM atlas_event
WHERE event = 'judge_code_rejected' GROUP BY 1 ORDER BY 1;

-- spending per cap
SELECT cap_key, cap_usd, reserved_usd, spent_usd, requests FROM atlas_cap
WHERE cap_key IN ('public', 'judge') OR cap_key LIKE 'public_daily:%' ORDER BY cap_key;

-- unresolved requests (sent, usage unknown): held at their ceiling until reconciled
SELECT request_id, route, amount_usd, created_at FROM atlas_reservation
WHERE state = 'dispatched' ORDER BY created_at;
```

Event codes:

- reservations: `reserved`, `settled`, `held_unknown_usage`, `released`, `refused:<cap>`;
- sessions: `session_opened`, `session_refused:<cap>`, `preflight_abort`;
- judge route: `judge_code_accepted`, `judge_code_rejected`, `judge_code_unconfigured`, `judge_code_too_short` (the configured code is shorter than 32 characters, so the judge route is disabled: replace it, §2).

## 6. Reconciliation of held requests

A dispatched request with unknown usage (a timeout, a lost connection) stays held at its ceiling. It is never released by timeout. To resolve one, after comparing with the provider's usage records and with the user's approval, settle it with the known amount:

```python
from decimal import Decimal
from atlas.hosted.budget_store import BudgetStore, connector

BudgetStore(connector("<DATABASE_URL>")).settle("<request_id>", Decimal("0.0021"))
```

Settling is idempotent per request ID.

## 7. Retention

- `BudgetStore.prune(days)` deletes only settled or released reservations and events older than `days`.
- It never deletes a reserved or dispatched reservation, and never deletes or resets a cap row: cumulative spending stays on record.
- Suggested: `prune(30)` monthly, with the user's approval. Keep everything until 15 December 2026 if storage allows.

## 8. Restoration through 15 December 2026

| Situation | What visitors see | Restoration |
| --- | --- | --- |
| Daily cap reached | "Live demo budget reached for today; recorded runs remain available." | Automatic at the next UTC date, or a cap change (§4, user approval) |
| Public pool exhausted | The same message on the public route; the judge route still works | A cap change within the $8.00 authorization (user approval) |
| Judge pool exhausted | The same message on the judge route | A cap change (user approval) |
| Kill switch off | "Live calls are unavailable; recorded runs remain available." | `HOSTED_LIVE_ENABLED = "true"` (user approval) |
| Neon unreachable or misconfigured | Live calls unavailable; recorded runs work | Fix `DATABASE_URL` or wait for Neon; nothing is sent meanwhile |
| Nebius failing | The session ends with its recorded error; the cost is held or settled | Wait; the reserved amounts stay accounted |
| Host down | Nothing | The tested local build is the fallback (`uv run --locked streamlit run app.py`) |

## 9. Before the hosted app is declared ready (not done in T-12's offline build)

- **Stage B (satisfied, 2026-10-19):** by the smoke session's own pre-run model check (one authenticated `GET /models` from the deployed host, inside a user-approved, capped session); both the public and the judge route passed it.
- **Stage C (satisfied, 2026-10-19):** the full locked build on the host; after `a45cb19` all three recorded runs verify intact there (live6 49 items; HAR flawed and HAR clean 21 each) and the live session page re-verifies the original (49 items, `VIOLATION_FOUND`). Details and the defect found at stage C follow.
  - `requirements.txt` is `uv export --frozen --no-dev --no-hashes` of `uv.lock` (56 pinned packages plus `-e .`). Which dependency file Community Cloud uses when both `uv.lock` and `requirements.txt` exist must be observed there.
  - `.streamlit/config.toml` sets `server.address = "localhost"` for the local build. Whether Community Cloud overrides it must be observed at stage C; it is not changed here.
  - **Observed by the user on Community Cloud (2026-10-19):** the build succeeded; `ATLAS_HOSTED=1` selected the hosted page; the replay disclosure was shown; the kill switch (off) message was shown; the `localhost` server setting did not prevent serving. Which dependency file the host used was not recorded.
  - **Defect found at stage C (2026-10-19), fixed:** the bundled live6 run showed "evidence changed since recording: 8 of 37 recorded items differ" (fail-closed; no outcome shown). Recorded-run verification reduced the candidate's recorded `run_dir`, a Windows path string, to its last component with the host's path rules (`src/atlas/ui/recorded.py`, `Path(...).name`); on Linux the whole string is one component, so it looked for `candidates/C:\Users\...\c1/...` (6 items missing, 2 derived outcome entries changed). Windows-only testing, including both Codex reviews, could not observe it. Fix: one separator-agnostic helper, `atlas.ui.artifacts.recorded_basename` (PureWindowsPath semantics; None, treated as missing, for an empty, `.`, `..`, drive-only or otherwise unusable value), used at the three places that reduce a recorded path to a name (`ui/recorded.py`, `ui/artifacts.py` exports, `ui/views.py` comparison). No recorded hash, index format or match rule changed; the recorded absolute path is never opened. Acceptance: a Linux container (`python:3.11-slim` with `requirements.txt`, no network, read-only) verified all three bundles intact and a one-byte change in `candidates/c1/outcome.json` on a copy as "evidence changed" (`runs/linuxcheck-20261019/verify.txt`, with the pre-fix source reproducing the 8 of 37). The fix is in the release review's scope; the hosted app must be redeployed from the fixed commit and the live6 replay re-checked there.
- **Neon:** the store was tested only on a disposable local PostgreSQL 17 container; the stage D probe ran once on Neon PostgreSQL 18. The production tables are created by the app on first use (`CREATE TABLE IF NOT EXISTS`).
- **Review:** the Codex T-12 security-and-spend review. Review 1 (2026-10-18): FAIL, one P2 (the execution boundary), fixed in fix pass 1; re-verification by Codex pending.

### Deployment and smoke test (user, 2026-10-19)

- **Neon:** project atlas-budget (Free plan), branch production, database neondb; the app created its tables on first use.
- **Community Cloud:** app from the private repository, branch main, `app.py`, Python 3.11; visibility private (one private app per workspace); secrets set by the user (the names in §2).
- **Reboot:** after an app reboot the server log showed the server started but the tab kept its old session; a hard browser refresh was needed.
- **Smoke test** (kill switch on with user approval, then set back off; sidebar "Live: unavailable"): session 1, public route: pre-run model check passed, 3 of 6 model attempts (`read_project_file`, `propose_patch`, `finish`), 1 revision (`new_source`) passed ATLAS validation and was recorded "not executed here", terminal state `REPORT`, original `VIOLATION_FOUND` (recorded, re-verified). Session 2, judge route ("Route: judge pool (access code accepted)"), new browser session: same shape, estimated $0.0045216, 0 held. Model-written text claiming the claim "is now supported" appeared only in labelled model-written boxes; the ATLAS finding stayed `VIOLATION_FOUND`.
- **Ledger after the smoke test** (read-only SQL by the user): `atlas_reservation`: judge settled 3 requests, reserved $0.0324000, actual $0.0045216; public settled 3, reserved $0.0324000, actual $0.0076857. `atlas_cap`: judge spent $0.0045216 (3 requests); public and `public_daily:2026-10-19` spent $0.0076857 (3 requests); each session cap $0.0648 with its own spend; `reserved_usd` 0 everywhere. Smoke total $0.0122073 (estimate, not billing).
- **Still to do at publication (each with approval):** make the app public, signed-out check, set `HOSTED_LIVE_ENABLED` to "true" through 2026-12-15 12:00 PT, add the demo URL.

### Waking the app

Community Cloud sleeps an app after 12 hours without traffic. A visitor clicks the wake button and waits about 30 seconds (about 23-24 s observed once on 2026-10-16). If the tab keeps spinning, refresh with Ctrl+Shift+R. All budget state is in Neon, so sleep loses nothing.

### Checking the ledger

Read-only queries, run in the Neon SQL Editor:

```sql
SELECT route, state, count(*) AS requests, sum(amount_usd) AS reserved_usd, sum(actual_usd) AS actual_usd FROM atlas_reservation GROUP BY route, state ORDER BY route, state;
SELECT cap_key, cap_usd, reserved_usd, spent_usd, requests FROM atlas_cap ORDER BY cap_key;
```
