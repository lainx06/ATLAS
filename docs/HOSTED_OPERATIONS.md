# Hosted demo operations (T-12)

How the limited hosted demo (SPEC §13) is configured, stopped, restored and inspected. Every cap change, credential change and deployment step needs the user's approval. Nothing here has been run against the deployed host or Neon yet: the hosted build is **built, awaiting review and deployment**.

## 1. What the hosted demo does

- **Selected only by `ATLAS_HOSTED=1`.** Without it, `app.py` is the unchanged local UI.
- **Recorded runs (always available).** The three bundled runs in `demo/recorded/` (live run 6 and the two HAR audit runs) are shown in the recorded-run viewer. Every recorded hash is recomputed before anything is shown; a changed byte shows "evidence changed since recording". Replay is disclosed on the page.
- **One live session per visitor session.** Nemotron (`nvidia/nemotron-3-super-120b-a12b`) inspects s01_faulty and may propose revisions. Each proposal passes `validate_diff` and is recorded "not executed here"; no candidate code runs on the host and no approval is asked. The original's findings come from live run 6's recorded, hash-verified trusted evaluation, labelled "computed by ATLAS's trusted evaluation functions (recorded 2026-10-18)".
- **Spending is enforced server-side** in Neon Postgres (`src/atlas/hosted/budget_store.py`) before every request, and the store fails closed.

## 2. Secrets (Streamlit Community Cloud, app settings → Secrets)

Root-level TOML keys. Community Cloud also exposes root-level secrets as environment variables, which is how `ATLAS_HOSTED` reaches `app.py`. Placeholders only: never commit real values.

```toml
ATLAS_HOSTED = "1"
HOSTED_LIVE_ENABLED = "false"          # the kill switch; only the exact string "true" enables live calls
NEBIUS_API_KEY = "<the Token Factory key>"
DATABASE_URL = "postgresql://<user>:<password>@<host>/<db>?sslmode=require"
JUDGE_ACCESS_CODE = "<a long random code, at least 32 characters>"
```

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
- judge route: `judge_code_accepted`, `judge_code_rejected`, `judge_code_unconfigured`.

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

- **Stage B:** one authenticated `GET /models` from the deployed host, approved for later (decision 4).
- **Stage C:** the full locked build on the host, approved for later (decision 4).
  - `requirements.txt` is `uv export --frozen --no-dev --no-hashes` of `uv.lock` (56 pinned packages plus `-e .`). Which dependency file Community Cloud uses when both `uv.lock` and `requirements.txt` exist must be observed there.
  - `.streamlit/config.toml` sets `server.address = "localhost"` for the local build. Whether Community Cloud overrides it must be observed at stage C; it is not changed here.
- **Neon:** the store was tested only on a disposable local PostgreSQL 17 container; the stage D probe ran once on Neon PostgreSQL 18. The production tables are created by the app on first use (`CREATE TABLE IF NOT EXISTS`).
- **Review:** the Codex T-12 security-and-spend review.
