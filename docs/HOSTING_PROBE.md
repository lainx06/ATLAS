# T-03 hosting probe: research and local design

Status: **research and local design complete (2026-10-15); stage A deployed by the owner and first observations recorded (§7a); one public sleep/wake cycle observed (2026-10-16, §7a); stage D run once on the host against Neon, all results ok (2026-10-16, §5b "Hosted results"); lead decisions recorded (2026-10-16, DECISIONS.md "T-03 hosting decisions"); T-03 is NOT accepted** (mapping against the acceptance criteria: §9). Lead decisions of 2026-10-15 (DECISIONS.md "Hosting probe decisions") are applied below. The builder deployed nothing and linked no account; every deployment, secret and button press was the owner's. No Nebius request was made by any stage. Written under TASKS.md T-03 (Sonnet 5.5, medium effort); the lead decides, and the decision goes in DECISIONS.md.

**Evidence labels** used on every conclusion:

| Label | Meaning |
| --- | --- |
| **documented** | Stated on an official page, fetched 2026-10-15 (sources in §10) |
| **locally tested** | Run on this machine in the locked environment |
| **proposed** | A design or number chosen here; not yet reviewed or measured |
| **unknown** | Not established. Unknown stays unknown; "no end date is listed" is never read as "available through 15 December" |

## 1. Recommendation (summary)

| | Choice | Why |
| --- | --- | --- |
| **Host** | **Streamlit Community Cloud** (limited hosted demo) | Free; honors `uv.lock` (documented); secrets store (documented); an app from a private repository can be made public without making the repository public (documented). |
| **Fallback** | **Hugging Face Docker Space, "protected" visibility** | Keeps source private while the app is public (documented). Needs a paid PRO plan ($9/month, documented) and spending approval. Free CPU Basic hardware sleeps when unused, and staying awake needs paid hardware (CPU Upgrade, $0.03/hour, which would be about $38 over 53 days, over the $20 allowance), so the fallback would sleep and wake on visit. |
| **Last resort** | Recorded-example site plus the local build | Already the agreed fallback for submission (docs/SUBMISSION_CHECKLIST.md); loses live judge access. |
| **Execution mode** | **Limited hosted** (curated examples; fixed trusted evaluation functions; generated diffs shown as "not executed here") | Agreed default (SPEC §13); chosen for V1 by the lead on 2026-10-16, with full local Docker execution and full hosted as a stretch goal. Full hosted execution is **not demonstrated** (§4). |
| **Expected cost** | Hosting $0 (Streamlit) or about $18 for two months (HF PRO, with a sleeping app); inference about $0.02 per normal live run and about $0.05 per run at the proposed ceilings (§5) | Both are within the $20 hosting and $30 inference planning allowances, which are not authorization to spend. |

## 2. Hosts compared

| Question | Streamlit Community Cloud | Hugging Face Spaces |
| --- | --- | --- |
| Source from a **private** repo | Supported. Needs a read-only GitHub deploy key and the `repo` OAuth scope, and administrative permission on the repository. **Documented** | Space code lives in a git repository on the Hub, not on GitHub; a GitHub repo is not deployed directly. Source can be private (protected or private visibility). **Documented** |
| **Public app access** while source stays private | An app from a private repository is **private by default**; its privacy can be changed independently of the repository (Sharing settings, or the Share button: "This app is public and searchable"). **Documented** | **Protected** visibility: source private, running app public at `<space>.hf.space`. Protected is a PRO / Team / Enterprise feature. **Documented** |
| Required plan | Free (Community Cloud). **Documented** | Creating a Docker or Gradio Space needs a paid plan: PRO for a personal account ($9/month). Static Spaces are free but cannot run Python. Streamlit is not listed as a Space SDK; a Streamlit app would run as a Docker Space. **Documented** |
| Account permissions | GitHub OAuth. Admin rights on the repo, and `repo` scope for private repos. For a **public** repo the required scope is **not stated** on the pages read. **Unknown** | Hugging Face account, plus PRO for this use. **Documented** |
| Limit on private apps | **One private app at a time**; make it public or delete it first. **Documented** | None found. **Unknown** |
| Dependencies | Searches for `uv.lock` first, then Pipfile, environment.yml, requirements.txt, pyproject.toml; uses the first file found, and only one file should exist. "Implies" lockfiles are honored; honoring of the exact locked set is not explicitly confirmed. **Documented, partly implied** | Whatever the Dockerfile installs. **Documented** |
| Python version | Chosen at deployment; "released versions still receiving security updates". Whether 3.11.17 exactly is available is **unknown** | Dockerfile; any base image. **Documented** |
| Secrets | App settings, "Secrets" field (TOML, read with `st.secrets`). **Documented** | Settings → secrets; exposed as environment variables, private, not readable again from the settings page; secrets are not copied when a Space is duplicated. **Documented** |
| Resources | Approx. 0.078–2 CPU cores, 690 MB–2.7 GB memory, up to 50 GB storage "as of Feb 2024". The page is dated, and the figures are not confirmed current. **Documented, dated** | CPU Basic: 2 vCPU, 16 GB RAM, 50 GB non-persistent disk; free hardware itself, though creating the Space needs PRO. **Documented** |
| Sleep | Apps with no traffic for **12 hours** go to sleep; anyone with access can wake them with a button. **Documented**. Wake time: about 23–24 s in **one observed** cycle (2026-10-16, §7a); not a guaranteed figure | "On free hardware, your Space will go to sleep ... after a period of time if unused"; running indefinitely needs paid hardware. CPU Basic is the free tier, so a PRO-plan Space on CPU Basic would still sleep. **Documented**, period **unknown** |
| Persistence | Container restarts clear memory (documented); disk persistence across restarts/sleep is not documented, so treat as **non-durable** | Docker Space disk is lost on restart; a storage bucket can be attached. **Documented** |
| Multiple instances / scaling | Not documented; fixed resource limits. **Unknown** | Not documented here. **Unknown** |
| Service end date, SLA | The pages read give none. That is not evidence of availability through 15 December. **Unknown** | Same. **Unknown** |
| Outbound network | Not documented on the pages read. **Unknown** (tested by the probe) | Ports 80, 443 and 8080 only. **Documented** |

**Does deploying ATLAS require a public repository?** For Streamlit: no, not for app visibility (privacy is configured separately). A private repo needs a deploy key and the `repo` scope. The Devpost rules separately require public licensed source by submission (docs/SUBMISSION_CHECKLIST.md), so the repository becomes public at T-13 regardless. Making `atlas` public earlier would expose the personal content in `docs/handoff/` (flagged in STATUS.md); that is the lead's decision and is not needed for the probe.

## 3. Isolation: limited hosted vs. full hosted

Default: **limited hosted** (SPEC §13): only reviewed evaluation functions with schema-validated parameters; no generated code executes; generated diffs are labelled "not executed here".

Full hosted execution would have to meet the actual contract (SPEC §10; T-05): no network, no secrets, read-only root, memory/PID/time limits, bounded output collection, confirmed removal. A separate worker **does not inherently need nested Docker**: a web app could send an approved candidate to a distinct Linux host that runs the existing T-05 runner next to a normal Docker daemon. The classification of each option:

| Option | Class | Basis |
| --- | --- | --- |
| Run candidate code inside the Streamlit Community Cloud app | **Unsupported by this host** | **Documented absence**: the pages read describe no container control, only a fixed-resource app process. Never run generated code in the app process (playbook §22.5). Not tested. |
| Hugging Face Docker Space launching sibling containers | **Not demonstrated** | The container runs as user ID 1000 and the docs describe no Docker socket or privileged mode (**documented**); whether any facility exists is not established, and mounting a host Docker socket into a public app is prohibited anyway. |
| Separate worker VM running the T-05 runner, called from the web app | **Not demonstrated; cost unknown** | Requires a Linux Docker host, a service interface, authentication between app and worker, and its own security review. T-05 was accepted only for "this Windows 11 Home / Docker Desktop host and image" (TASKS.md T-05 ACCEPTANCE), so a Linux worker is a new, unverified environment. No VM price was researched; **whether it fits in the $20 allowance is unknown**, not "infeasible". |

Bounded conclusion (**proposed**): do not pursue full hosted execution for the submission; the local build demonstrates patch execution (SPEC §13). This note does not design an execution platform.

## 4. Costs

### 4.1 Verified current model price

`nvidia/nemotron-3-super-120b-a12b` on Nebius Token Factory: **$0.30 per 1M input, $0.90 per 1M output tokens**, $0 per request. **Documented/observed**: from the authenticated `GET /models?verbose=true` on 2026-10-14 (runs/nebius_smoke, local) and consistent with a third-party listing seen 2026-10-15. Reasoning tokens are counted inside completion tokens and billed at the output rate (observed in the smoke usage, STATUS.md). No call was made today; the price is a historical checkpoint, re-checked live before any run.

### 4.2 Three separate cost figures

Per-run estimates use the SPEC §11 ceiling of **6 model calls** per run. The ceilings below are **proposed** values for planning, not set in code or DECISIONS.md. They are larger than the smoke script's 1,024-token cap, which only suited a one-line reply.

| Stage | Calls | Normal in / out (incl. reasoning) | Proposed ceiling in / out | Ceiling cost |
| --- | --- | --- | --- | --- |
| Claim translation | 1 | 2,000 / 1,500 | 3,000 / 3,000 | $0.0036 |
| Diagnosis | 1 | 8,000 / 3,000 | 12,000 / 6,000 | $0.0090 |
| Revision (up to 2 candidates) | 2 | 10,000 / 4,000 each, 1.5 on average | 12,000 / 8,000 each | $0.0216 |
| Report | 1 | 6,000 / 2,000 | 8,000 / 4,000 | $0.0060 |
| Spare call (largest stage) | 1 | not used normally | 12,000 / 8,000 | $0.0108 |
| **Per run** | 6 | **31,000 / 12,500 → about $0.021** | **59,000 / 37,000 → $0.051** | |

| Figure | Value | Label |
| --- | --- | --- |
| **Observed smoke costs** | $0.0000519 (32 in / 47 out) and $0.0000609 (47 in / 52 out), 2 calls | observed (STATUS.md) |
| Smoke script's configured bound | $0.001075 per call (512 in / 1,024 out). Valid only for that script | documented in the script |
| **Estimated normal run** | about **$0.021** (calculation: `hosting_probe/cost_calc.py`) | proposed |
| **Configured worst case per run** | **$0.051** at the ceilings above | proposed |

**Retries without double-counting. Decided (DECISIONS.md, 2026-10-15):** the six-call limit counts every attempted inference request, retries included, so the worst case is 6 requests, **$0.051** per run. (Had retries been extra calls, 12 requests would have cost about $0.102.) A dispatched request counts even if it fails with no usage.

Capacity at these figures (arithmetic only): $50 of awarded credits is about **2,400 normal runs** or **980 worst-case runs**; the $30 inference allowance is about 590 worst-case runs. The remaining balance is unverified (§6), so this is an upper bound on what the credits could fund, not a promise.

Hosting: Streamlit Community Cloud $0 (**documented**). HF PRO is $9/month (**documented**), so about $18 through mid-December with a sleeping app; keeping it awake on CPU Upgrade ($0.03/hour, **documented**) would add about $38 for 53 days, over the $20 allowance. Neither is authorized.

## 5. Judge access design (proposed)

Requirement: a free working path through **15 December 2026** (docs/SUBMISSION_CHECKLIST.md), with public traffic unable to exhaust judges' access.

**Modes shown to the user (always labelled):**

| Mode | Meaning | When |
| --- | --- | --- |
| **Live** | A real Nebius call is made now | A budget reservation succeeded |
| **Recorded example** | A stored real run, replayed and labelled "recorded on <date>, not live" | Any budget is exhausted, the store is unreachable, or the model fails |
| **Unavailable** | A clear message with the restoration procedure, no result | Even recorded examples cannot load |

**Budgets and concurrency (proposed).** Per-session, per-route and daily caps, plus a separate reserved judge budget, enforced by **reserving before calling**:

1. Estimate the call's ceiling cost; atomically add it to the relevant counters (judge pool or public pool; per-session; daily). If any would exceed its cap, refuse and serve a recorded example.
2. Make the call; after it returns, replace the reservation with the actual usage.
3. **Decided:** a reservation for a request that was *dispatched* is not released because a lease expires. If its usage is unknown (crash, timeout, lost response), the ceiling-cost reservation stays reserved until reconciled with the actual usage (for example from the logged response usage or the Nebius Usage tab). Only a reservation that was never dispatched may expire. Unreconciled reservations therefore reduce capacity conservatively, and reconciliation needs a durable store and an owner procedure.

Planning caps: judge pool $10 (about 196 worst-case runs); public pool at most $0.30 per day (about 5 worst-case runs a day), about $16 over about 53 days; 2 live runs per public session. Public and judge pools draw on separate counters, so public traffic cannot spend judge capacity. These are **proposed**, to be tuned with measurements.

**What needs durable storage.** The counters, the reservations, the judge code's quota and the "budget exhausted" state. Community Cloud memory is cleared on restart, sleep or reboot (**documented**) and its disk persistence is not documented, so in-process counters are only a soft limit: a restart resets them. Multiple instances are not documented, so assume more than one process could exist and keep all counters in **one external store with atomic conditional updates**, never in app memory. The store is **Neon Postgres** (selected by the lead 2026-10-16, §5a and §5b; production integration not built). If the store is unreachable, **fail closed** to recorded-example mode.

**Judge access control.** A hidden URL is not access control. A long random **judge access code** is given privately in the Devpost testing instructions; the app compares it server-side against a stored hash, charges the judge pool, and never exposes it to the browser, prompts, Git or logs. If the public pool is exhausted, judges with the code still reach live mode until the judge pool is exhausted. If both are exhausted, the restoration procedure is: the owner raises the cap in the store (or tops up credits) and the app returns to live mode with no redeploy. Either step is spending and needs its own approval; none is authorized (lead, 2026-10-16).

**Backstop.** Nebius documents no per-key spending limit (not found; **unknown**). **Payment information is already on the account (lead, 2026-10-15) and billing settings are not changed.** Because the billing page says a negative balance leads to an automatic card charge (**documented**), the credit balance is **not** a hard ceiling: usage beyond the credits could be charged to the card. The in-application caps above are therefore the intended spending control. They are **planned controls, not an existing hard spending ceiling**: none is implemented yet (lead, 2026-10-16). They are designed to fail closed, and the $30 inference allowance is a planning figure, not an authorization. Whether an account with a payment method is auto-paused or charged at zero balance is **unknown**.

## 5a. Durable budget store: recommendation (research only, 2026-10-15)

**Selected by the lead (2026-10-16): Neon serverless Postgres, Free plan** (provisional from 2026-10-15 until the hosted connection test passed, §5b; production integration not built). One store holds every counter, reservation and the hashed judge code (§5). Nothing was created, no account opened, no connection made. Only public documentation was read.

### Why this fits the §5 design

| Requirement | Neon Free | Label |
| --- | --- | --- |
| Free-tier limits | **No credit card required; the Free plan is permanent, not a trial** (neon.com/pricing). 1 GB storage per project; 100 compute-unit-hours (CU-hours) per project each month; 100 projects; 5 GB network transfer a month; 6-hour restore history. Storage-increasing operations fail at the cap; compute suspends if the monthly compute allowance is exhausted until the next period | **Documented** (neon.com/pricing and /docs/introduction/plans, 2026-10-15) |
| Size of our need | **Fixed:** the pool and daily cap rows (a handful, plus about one daily row per day of judging) stay small. **Accumulating:** one reservation row per attempted request (up to 6 per run), plus any per-session cap rows, grow with traffic unless pruned. At an assumed 0.5 KB per reservation row including its index (not measured), 60,000 rows (10,000 runs) is about 30 MB, about 3% of 1 GB. Production may prune old rows only under the retention rule below; the 1 GB cap is then not expected to bind, but this is an estimate. **Retention rule (lead, 2026-10-15):** unresolved dispatched reservations must remain accounted for. Pruning old records must **never** release reserved funds or reset cumulative spending: only rows whose effect is already folded into the cap rows' `reserved` and `spent` totals (settled or released reservations) may be deleted, the cap rows' cumulative totals are never reduced by pruning, and a `dispatched` reservation is never pruned until it has been reconciled and settled. | need: **proposed**; row size **unknown** until measured |
| Compute allowance | See the explanation below the table | **Documented**, usage **unknown** |
| Atomic reservation | Ordinary Postgres transactions. A conditional `UPDATE ... WHERE reserved + spent + :amount <= cap RETURNING ...` is one atomic statement; the row lock serializes concurrent callers, so two requests cannot both take the last of a budget. Each cap (judge pool, public pool, daily key, session key) is one row | Standard Postgres behavior (**not tested here**); **proposed** design |
| Restart behavior | All state is in the database, none in app memory. A Community Cloud restart, sleep or second process just reads the same rows. Neon suspends idle compute after 5 minutes (cannot be disabled on Free) and reactivates "within a few hundred milliseconds" on the next query. Free-plan data is not deleted for inactivity (storage, not compute, is what is kept) | **Documented**; first-query latency after suspension **not measured** |
| Failure when exhausted or unreachable | Exhausted compute or storage, an unreachable database, or a connect timeout all make the reservation fail, and the app fails closed to recorded-example mode (§5) | **Proposed** |
| Pausing risk | No inactivity pause or deletion is described for Free projects (unlike Supabase below). A single quiet day does not establish availability through 15 December | **Documented** absence; availability **unknown** |

**What "100 CU-hours" means (documented: neon.com/docs/manage/computes, 2026-10-15).** A compute unit (CU) is a bundle of roughly 4 GB of RAM with associated CPU and local SSD. On the Free plan a compute autoscales between **0.25 and 2 CU**. Usage is **compute size × time the compute is active**; suspended time costs nothing. A compute suspends after **5 minutes with no activity** (not configurable on Free), so each burst of use stays active until 5 minutes after its last query.

| Scenario (arithmetic only) | Result |
| --- | --- |
| 100 CU-hours at the smallest size (0.25 CU) | 400 hours of active time a month |
| 100 CU-hours at the largest size (2 CU) | 50 hours of active time a month |
| One isolated burst at 0.25 CU | at least 5 minutes active, about 0.02 CU-hours |
| A query at least every 5 minutes, so the compute never suspends, at 0.25 CU | 744 hours in a 31-day month = 186 CU-hours, **over the allowance** (it runs out about day 17) |

So the allowance is ample for sporadic judging traffic and **not** for a keep-alive or steady traffic. Never add a keep-alive ping: it keeps the compute active. When the allowance is exhausted, compute stays suspended until the next monthly period (documented), the budget store becomes unreachable, and the app fails closed to recorded-example mode (§5). How much active time real traffic causes, and which size Neon assigns within 0.25–2 CU, is **unknown** until measured; the monthly period also resets the allowance, which matters because judging spans roughly two months.

### Reservation protocol on this store (proposed; implements the 2026-10-15 decisions)

All amounts are integer micro-dollars. Each pool row has `cap`, `reserved` and `spent`.

1. **Reserve** (one transaction): atomically add the ceiling cost to the judge-or-public pool, the daily key and the session key. If any statement updates zero rows, roll back and refuse (recorded-example mode).
2. **Mark dispatched before sending.** Commit the reservation's state as `dispatched` **before** the HTTP request leaves. A crash afterwards then leaves a dispatched reservation, which is never auto-released (the decision that unknown usage stays reserved). A retry is a new reservation and counts toward the six-call limit.
3. **Settle** after the response: replace the reservation with the response's actual usage (`reserved` down, `spent` up).
4. **Release** only if the request was never dispatched (for example a validation failure before sending), or an owner reconciles it against the Nebius Usage tab.
5. **Reconcile** unknown-usage reservations by an owner procedure: compare against Nebius usage, then settle manually. It needs a small admin script; none exists.

### Limits and open points

- **Reachability from Community Cloud is unknown.** Neon accepts TLS Postgres connections on port 5432 (documented). Whether Community Cloud allows outbound 5432 is **not documented** on the pages read. A one-connection test is therefore needed (stage D, below). Neon also documents an HTTP/WebSocket driver over port 443, but I could not confirm a usable Python client for it, so treat it as a **fallback to investigate**, not a plan.
- **Cold-connection latency** after suspension is documented only as "a few hundred milliseconds"; it must be measured from the host. Hold no long-lived pool: reconnect per request or use short-lived connections.
- **Account and terms.** Neon advertises Free with no card required (**documented**). Neon's terms for this use, and its retention or deletion rules for abandoned accounts, were **not** researched.
- **A paid fallback is not needed to start** but is unknown in price; no spending is proposed.
- **Backup of truth.** The Nebius Usage tab remains the independent record of actual spend; the store is the control, not the ledger of record.

### Alternatives considered (documented, not chosen)

| Store | Free-tier finding | Why not chosen |
| --- | --- | --- |
| **Supabase Postgres** | 500 MB per project, two free projects. Free projects with low activity over 7 days are **paused**; a paused project can be restored in Studio for 90 days (documented, supabase.com/docs/guides/platform/free-project-pausing). | A budget store that can pause during a quiet week is a failure mode for 15 December. A keep-alive ping would be a workaround that adds its own dependency. |
| **Upstash Redis** | 250 MB, 500K commands a month, one database, atomic commands. The pricing page lists **no persistence/durability** on the free plan, and an unclaimed instance is deleted after 3 days (documented, upstash.com/docs/redis/overall/pricing). | A budget ledger that may lose data on restart breaks the "unknown usage stays reserved" rule. |
| Turso, Cloudflare D1/KV, Google Sheets, others | **Not researched.** Google Sheets has no atomic conditional update. | Out of scope for this bounded step; not ruled out. |

### Stage D (proposed; needs its own approval and a separate new account)

A canary-only test that does not touch the sleeping stage A probe: create a Neon account and a throwaway project; deploy a second stub (not yet written) that makes **one** database connection using a `DATABASE_URL` secret, runs one conditional-update statement on a scratch table, and prints only success, latency and row counts. It would settle: outbound 5432 reachability, first-query latency after suspension, and the atomicity of the conditional update under two simultaneous sessions. No Nebius key, no ATLAS code. Requires: a Neon account (permission to sign up), a second Streamlit app (the free plan's app count is **unknown**), and the owner entering the connection string as a secret.

## 5b. Stage D: budget-store feasibility probe (prepared locally, 2026-10-15)

Neon Free was selected **provisionally**, on condition that a hosted connection test succeeded. That test passed once (2026-10-16, "Hosted results" below), and the lead then **selected Neon** (DECISIONS.md, 2026-10-16). Production integration still needs implementation and review. The probe is deliberately small and uses **synthetic integer units, scratch tables, no model-provider key and no model request**. It is an update to the existing Streamlit probe, not a second app. The probe repository received the three files in place of the stage A two **after** the sleep/wake observation, so that observation was not disturbed.

### Files (local; nothing published)

| Path (under `C:\Users\Lain\source\atlas\hosting_probe\stage_d\`) | Purpose |
| --- | --- |
| `app.py` | The stage A page (build, canary) plus a **protected** section. The deployed app is public, so a signed-out visitor could otherwise press the button. The scenarios can run only when both a `DATABASE_URL` and a `PROBE_ACCESS_CODE` secret exist **and** the visitor has typed the matching code (constant-time comparison, empty input never matches); the button does not exist before that. With no code configured the section is disabled (fails closed). Shows result names, pass/fail and counts. It never prints the URL or the code; a connection failure shows only the error type |
| `budget_probe.py` | The database operations and scenarios. Imports no driver; takes a psycopg connection |
| `requirements.txt` | `streamlit` and `psycopg[binary]` (the one extra dependency) |

`hosting_probe/check_publication.py stage_d` confirms exactly these three files, no connection string, credential or project-document wording, no provider reference, and that the only network-related import is `psycopg`.

### Neon project (owner-reported, 2026-10-15)

The owner created the project **`atlas-budget-probe`** on the Neon **Free** plan: **AWS US East 2 (Ohio)**, **PostgreSQL 18**, Postgres only. The optional agent/CLI setup was skipped. **No connection string has been shared** with the builder; the owner entered it only as an app Secret. The project is kept (lead decision). The only ATLAS connections to it are those of the one stage D run from the deployed probe (2026-10-16).

| Version | What has been run |
| --- | --- |
| PostgreSQL 17.11 (local container) | The five scenarios, 3 of 3 runs (below) |
| PostgreSQL 18 (Neon) | The five scenarios, **1 run** from the deployed Streamlit probe, all ok (2026-10-16; "Hosted results" below) |

Hosted test inputs (all entered by the owner as Secrets on the existing probe app, never in chat, Git or screenshots): `DATABASE_URL` (the **direct**, non-pooled Neon string), `PROBE_ACCESS_CODE` (a long random value, generated like the canary but longer) and the existing `CANARY`. A deployed app is public, so the code gate is required before any database step is enabled.

### Database operations (proposed; scratch tables `probe_cap`, `probe_reservation`)

All money is **integer units** (production: integer micro-dollars). Each connection is opened with `autocommit=True` so each `transaction()` block is a real transaction.

| Operation | What it does in one transaction | Property it tests |
| --- | --- | --- |
| `reserve(request_id, amount, cap_keys)` | Inserts the reservation row (`request_id` is the **primary key**; `ON CONFLICT DO NOTHING`), then for each cap key **in sorted order** runs one conditional `UPDATE probe_cap SET reserved = reserved + amount WHERE cap_key = k AND reserved + spent + amount <= cap`. If any update changes no row, it raises and **everything rolls back**, including the reservation row | all-or-nothing across caps; unique request ID; consistent lock order; no overshoot under concurrency |
| `mark_dispatched(request_id)` | Commits `state = 'dispatched'` **before** a request would be sent | a crash after sending leaves the cost retained |
| `settle(request_id, actual)` | Locks the reservation row (`FOR UPDATE`); only a `dispatched` row settles; moves each cap's `reserved` down and `spent` up by the actual units; a repeat returns `already-settled`; an actual above the reservation is retained for reconciliation | no double settlement |
| `release(request_id)` | Releases only a never-dispatched reservation; a dispatched one returns `retained-dispatched` | uncertain cost is never auto-released |

Constraints in the schema (`reserved >= 0`, `spent >= 0`, `reserved + spent <= cap`, state values, `amount > 0`) back the logic with the database itself.

### Scenarios the hosted run would execute

1. **Two concurrent requests compete for a budget that admits only one** (cap 100, each asks 60), 20 rounds, each request on its own connection and thread, released together by a barrier. Pass: exactly one `reserved` and one `refused`, and 60 units held, every round.
2. **A refused multi-cap reservation leaves no partial change** (caps 100 and 50; a 60-unit request to both is refused by the 50 cap). Pass: both caps unchanged and no reservation row.
3. **Opposite cap orders do not deadlock** (two requests naming caps in reversed order, 20 rounds). Pass: both succeed every round.
4. **Duplicate request IDs** reserve once and settle once, including when two attempts are simultaneous.
5. **Uncertain dispatched cost** survives a new connection (standing for a restart or timeout recovery): release is refused, another request is blocked by the retained units, and a later settle with the actual usage frees the difference.

It also reports the time to open the first connection. That is one **combined connection/startup measurement** (name lookup, TLS, login and any compute start); it cannot separate those parts and is **not** a measure of how well the hosting regions match.

### What the probe demonstrates, and what it does not

| It would show (if it passes on the host) | Label |
| --- | --- |
| The Community Cloud host can reach the Neon database (outbound TLS Postgres, port 5432) | to be **observed** |
| The conditional-update design admits only one of two competing requests, rolls back a refused multi-cap reservation, and handles duplicates, lock order and dispatched retention on **Neon's actual Postgres** | to be **observed** |
| One combined first-connection/startup time from the host (not a region comparison) | to be **observed** |

| Not shown, and required for production (not built during T-03) | |
| --- | --- |
| Real micro-dollar accounting, per-session and daily keys, the judge and public pools and judge access code | production implementation |
| Lease handling for never-dispatched reservations, an owner reconciliation procedure and admin script for unknown-usage reservations | production implementation |
| Pruning under the retention rule (never release reserved funds or reset cumulative spending; never prune a dispatched reservation before reconciliation; session cap rows may be dropped only when nothing is reserved against them and their spend is already counted in the pool and daily rows); monitoring of the compute allowance and storage | production implementation |
| Behavior at the Neon compute or storage limit, long outages and restore | not tested |
| Integration with the agent loop, the Nebius usage record, and a security review of the whole budget path | review required before T-06 relies on it |
| A statement that the SQL is correct beyond the five scenarios; concurrency is probed, not proven | limitation |

### Local PostgreSQL 17.11 results (2026-10-15)

**These are results on a disposable local PostgreSQL 17.11. They do not establish Neon connectivity, Neon's durability guarantees, cold-connection latency, or concurrency behavior on the hosted service. The owner's Neon project runs PostgreSQL 18, so verification on Neon 18 is pending; behavior of these statements on 18 is expected but has not been observed.**

| Item | Value |
| --- | --- |
| Image | official `postgres:17-alpine`, resolved digest `sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24` (image created 2026-09-17) |
| Server | PostgreSQL 17.11 (musl, x86_64) |
| Driver | psycopg 3.3.6 (libpq 18.0.4), installed only in a disposable `uv run --locked --isolated --with "psycopg[binary]"` environment. `pyproject.toml` and `uv.lock` were byte-identical before and after |
| Isolation | Port bound to `127.0.0.1:55432` only; throwaway random password; no bind mounts, volumes or Docker socket (`Mounts=[]`, not privileged); data on a 256 MB tmpfs; 512 MB memory and 200-process limits |
| Timeouts | `connect_timeout=15`, `statement_timeout=10000`, `lock_timeout=10000`, `idle_in_transaction_session_timeout=20000` (milliseconds), plus a shell `timeout` on every run |
| Run | The five scenarios passed in **3 of 3** full runs (about 1.3 s each). The probe tests also passed against the database (14 passed); offline they pass with the database tests skipped (12 passed, 2 skipped) |

**Scenario results (shipped code, all three runs):** two concurrent requests for a budget admitting one, 20 rounds each, exactly one reserved and 60 units held every round; the refused multi-cap reservation left both caps unchanged and no reservation row; opposite cap orders produced no deadlock in 20 rounds; a duplicate request ID reserved once and settled once, including concurrent attempts; an uncertain dispatched cost survived a new connection (release refused, another request blocked, later settle freed the difference). The server log for the whole session shows 20 `deadlock detected` errors, all during the deliberate defect run below and none during the shipped-code runs.

**The scenarios can fail.** Three deliberately defective variants of `reserve` were swapped in (the shipped file was not changed), and each was caught by its scenario:

| Defect | Scenario that caught it |
| --- | --- |
| Check the headroom, then write (no conditional `UPDATE`) | Race: more than one request admitted |
| Reservation row and cap updates in separate transactions | Multi-cap refusal left partial changes |
| Caps updated in the caller's order | Opposite orders: `DeadlockDetected` in each of 20 rounds |

**Defects found in the probe:** none in the shipped operations. One defect in a *test* was fixed: the failed-connection check read the rendered tree instead of the displayed values.

**Cleanup:** the container was removed, the pulled image was removed, no volume or other container was left, and port 55432 no longer listens (only closed-connection residue). The Docker images that existed before (`atlas-runner:t05`, `python:3.11-slim`, `hello-world`) were not touched. Evidence (git-ignored): `runs/t03-pg/` (`scenario-results.json`, `run-scenarios.log`, `pytest-*.log`, `container-config.txt`, `cleanup.log`, `run_scenarios.py`).

**Still not shown:** the scenarios are a probe, not a proof; they say nothing about Neon, TLS latency, scale-to-zero resumption, the compute allowance, restarts of the real service, or production accounting.

### Hosted results on Neon PostgreSQL 18 (2026-10-16; user-observed)

**One run, observed and reported by the owner.** The builder did not see the page and did not rerun anything. These results show that the deployed Community Cloud app reached Neon and that the five scenarios passed once there. They do **not** establish production readiness, durability across a database restart, long-term availability, or correctness beyond the five scenarios.

| Item | Value | Label |
| --- | --- | --- |
| Deployed files | The public repository `lainx06/atlas-hosting-probe` (`main`) holds exactly `app.py`, `budget_probe.py` and `requirements.txt`. Each is byte-identical to `hosting_probe/stage_d/` (SHA-256 `157994ad…`, `b6fab8b0…`, `a83b0249…`). The update commit is dated 2026-10-16 16:57:14 UTC (12:57 -0400), after the sleep/wake visit | checked by the builder (read-only download from GitHub; the app itself was not visited) |
| Secrets | `DATABASE_URL`, `PROBE_ACCESS_CODE` and `CANARY` entered by the owner | owner-reported |
| Access gate | A wrong code showed "Not authorized." and no button; the correct code enabled the button | observed (owner-reported) |
| Run time | About 2026-10-16 13:15 -0400, button pressed once | owner-reported |
| Server | Neon project `atlas-budget-probe`, PostgreSQL 18 (from the project settings; the probe page does not display the server version) | owner-reported |
| First connection and setup | **1.04 s**: one combined figure for name lookup, TLS, login and any compute start. Not a region comparison, and it is not known whether the compute was suspended beforehand | observed (owner-reported) |
| 1. Concurrent requests, budget admits one | ok: 20 rounds, exactly one reservation admitted and 60 units held every round | observed (owner-reported) |
| 2. Refused multi-cap reservation | ok: caps unchanged, no reservation row | observed (owner-reported) |
| 3. Opposite lock orders | ok: 20 rounds, no failures | observed (owner-reported) |
| 4. Duplicate request ID | ok: reserved and settled exactly once | observed (owner-reported) |
| 5. Uncertain dispatched cost | ok: the reservation was retained across a new connection and blocked another request, then settled successfully | observed (owner-reported) |
| Total | ok, **57.2 s** measured by the app (local PostgreSQL 17.11: about 1.3 s; the difference was not investigated) | observed (owner-reported) |

**What this settles:**
- Outbound TLS Postgres from Community Cloud to Neon (port 5432, direct string) works.
- The Secrets field holds several secrets.
- The access-code gate behaved as designed on the host.
- The reservation design behaved as intended in these five scenarios on Neon's PostgreSQL 18.

**What it does not settle:**
- Durability across a Neon restart or a long outage.
- Behavior at the compute-hour or storage limit, and how much of the 100 CU-hours this run used (not read).
- Outbound HTTPS to Nebius from the host (stage B, not run).
- The full locked build (stage C, not run).
- Production accounting (the "Not shown" table above).

**Left in place:** the scratch tables `probe_cap` and `probe_reservation` remain in the Neon project, holding synthetic rows from the last scenario. The probe app, its Secrets and the Neon project are kept; deletion and any credential rotation are later explicit actions.

### First account step (owner; nothing created yet)

Sign up at Neon (neon.com) with the Free plan, choosing email or GitHub as you prefer. If GitHub, read the authorization screen and report the scopes. Stop at the dashboard: no card, no paid plan, no project yet. Report whether Neon created a default project automatically.

## 6. Credits and the 15 December requirement

| Fact | Status |
| --- | --- |
| $50 in Token Factory credits awarded in total (an initial $25, then an additional $25) | **User-reported** (STATUS.md) |
| Billing screenshot (owner-reported, 2026-10-15): account balance **$50.00**; a **separate $1.00 trial credit** shown with **29 days remaining**; Token Factory usage **less than $0.01** | **Observed by the owner**, not independently verified by the builder. The $50 balance is consistent with unspent awards and tiny smoke usage. **No expiry is shown for the $50: keep it unknown** |
| Trial credit: "$1 in trial credit, valid for 30 days" | **Documented**. 29 days remaining on 2026-10-15 means it ends about 2026-11-13, well before 15 December; it is not a judging resource |
| Nebius Builder Program terms: "All promotional credits are nonrefundable, nontransferable, and expire 90 days from the date of issuance" | **Documented** (nebius.com/builders-terms-and-conditions, 2026-10-15). Whether the user's credits fall under these terms is **unknown** |
| If the first $25 was issued on 2026-10-14 (the earliest evidence that the key worked), 90 days ends about **2027-01-12**, after 15 December. The issue date of each award is **unknown**, so this is an illustration, not a finding | **proposed** reading, **unknown** dates |
| The terms say the same programme credits must not be used "for production workloads, large-scale commercial deployment, or any revenue-generating activity beyond prototyping and experimentation", and that Nebius may auto-pause an account whose monthly use exceeds the allocation by more than 30% | **Documented.** Whether a public judging demo counts as prototyping or production is **unknown**; the lead should confirm with Nebius before relying on credits for public traffic |
| Promo-code pages say "usually" a promo has an expiry and do not give a validity after applying | **Documented**, no specific answer |

**The balance is now owner-observed ($50.00). The expiry of the $50 is still unknown**: the console view the owner checked showed none. T-03's third acceptance criterion therefore stays "marked unknown". Billing settings and spending authorization are unchanged.

## 7. The smallest probe

Two sets of files exist locally. **Stage A publishes only `hosting_probe/stage_a/`.** The first stub (`hosting_probe/app.py`) contains the optional Nebius check and is **not** published in stage A.

| Check | What it shows | Status |
| --- | --- | --- |
| **1. Build / import** | The page renders, so the host built the environment and started Streamlit; Python and Streamlit versions, process uptime, render time | **Locally tested** (Streamlit `AppTest`, locked environment). **Not tested on any host.** |
| **2. Secret store** | A harmless random `CANARY` secret is read through `st.secrets`; only presence and the first 8 hex digits of its SHA-256 are shown | Locally tested with a fake canary. **Not tested on a host.** |
| 3. Nebius connectivity | Not part of stage A. Exists only in the unpublished first stub | Locally tested with a **mocked** response only; no real request has been made |

**Stage A makes no Nebius request and holds no key.** Its `app.py` imports no network module, and a local test blocks any non-loopback connection or name lookup while the page renders (the guard has its own self-test). No Nebius key is requested for the canary test.

**Exact publication set** (checked by `hosting_probe/check_publication.py`, 2026-10-15):

| File (local path) | Bytes | SHA-256 |
| --- | --- | --- |
| `C:\Users\Lain\source\atlas\hosting_probe\stage_a\app.py` | 1,362 | `2527fc07d812dc94561f900c97ef941392cfa8644bab3a8e49e817f30fce7303` |
| `C:\Users\Lain\source\atlas\hosting_probe\stage_a\requirements.txt` | 10 | `57716129b9bb1b62e7474b384b2b5abeb8c83cd221bdcb001977d81c0c2d433c` |

The checker confirms the set is exactly these two files with no sub-directories; no Nebius, credential, key-shaped, email, `.env`, local-path or project-document wording; no `atlas`, `dotenv`, `openai`, `requests`, `urllib`, `http`, `socket` or similar imports; and `requirements.txt` equals `streamlit`. It states what it checks; it cannot prove the absence of every possible secret, so the files are also small enough to read in full (47 lines for `app.py`).

**Reduced-dependency label:** `requirements.txt` installs only Streamlit. A successful deployment verifies the host, its secret store and its build for a minimal environment. It does **not** verify the locked environment of 61 packages (stage C).

Local commands (no deployment): `uv run --locked python hosting_probe/check_publication.py` and `uv run --locked python -m pytest hosting_probe -q`.

### Probe stages

| Stage | What | Needs |
| --- | --- | --- |
| A | Deploy the two files; check 1 (build) and 2 (canary). Record build time and the page. The probe is **kept** until a sleep/wake observation is also recorded (about 12 hours after the last visit, documented) | Approval (§8) |
| B | Optional `GET /models` from the host (the first stub's button) | Separate approval; a real key entered by the owner |
| C | Full locked-environment build | Separate approval |

## 7a. Stage A observations (2026-10-15)

Deployed by the owner from `lainx06/atlas-hosting-probe` (public; `main`; exactly `app.py` and `requirements.txt`, byte-identical to the local set, checked by a read-only download). App URL: `https://atlas-hosting-probe.streamlit.app/`. All items are **observed** and **owner-reported** unless marked; no Nebius request or key was involved.

| Observation | Value | Label |
| --- | --- | --- |
| GitHub authorization shown to the owner (earlier sign-in) | Public repositories, repository hooks, codespaces, org read, email read; no private-repository scope | observed (owner-reported) |
| Extra permission requested during this deployment | None | observed (owner-reported) |
| Python versions offered | 3.11 to 3.14; 3.11 chosen | observed (owner-reported) |
| Build + deploy time | About 14 seconds (minimal one-package environment) | observed (owner-reported) |
| Python on the host | **3.11.17**, the same patch version as the locked environment | observed (page) |
| Streamlit on the host | 1.66.0 (unpinned `streamlit` resolved to the same version as `uv.lock` today; not a lock verification) | observed (page) |
| Platform | Linux 6.12.94+, x86_64, glibc 2.41 | observed (page) |
| First render | Fresh process (uptime 0.1 s), page rendered at unix 1792104075 = 2026-10-15 18:41:15 -0400 | observed (page) |
| Secret store | `CANARY` present; the page's SHA-256 prefix matched the owner's locally computed prefix | observed (owner-reported match) |
| Canary value on the page | Not shown; only presence and the hash prefix | observed (design) |
| Signed-out access | The page loaded in a private (incognito) window for a signed-out visitor, about 2026-10-15 18:44 -0400 | observed (owner-reported) |

**Sleep/wake (observed once, 2026-10-16; owner-reported):**

| Observation | Value |
| --- | --- |
| Visit | 2026-10-16 12:01 -0400, in a fresh signed-out incognito window |
| Previous visit | 2026-10-15 18:44 -0400 (the signed-out check), so the gap was **17 h 17 min** with no visits in between (owner-reported) |
| Page shown | A wake-up button, not the app |
| Wake time | About **23–24 s** from pressing the button to the app |
| `process_uptime_s` after wake | **0.1**, so a fresh process |

This is **one observed successful public sleep/wake cycle**. It confirms that the documented sleep happens and that a signed-out visitor can wake the app. It does not guarantee future availability, a stable wake time, or the feasibility of hosting the full ATLAS deployment. It was recorded before the stage D files were pushed.

**Not yet observed:**
- **Outbound network:** stage A has none by design. Stage D later showed outbound Postgres to Neon (§5b "Hosted results"); outbound HTTPS to Nebius is untested (stage B).
- **Full locked environment** (61 packages, stage C): untested. The stage A build installed Streamlit only; stage D added `psycopg[binary]`.
- **Availability through 15 December:** not established by one observed cycle.

The probe stays deployed. Deletion is a later, explicit action.

## 8. Approvals needed

**The one minimal deployment action for stage A (explicit approval given for local preparation only; nothing has been created or published):**

1. The owner creates a **new, separate public GitHub repository** `lainx06/atlas-hosting-probe` and adds exactly the two files above at its root (copies; no ATLAS code, history or personal content). The `atlas` repository and the `repo` OAuth scope are not involved. (Whether a public repository needs a lesser scope is **unknown**.)
2. The owner signs in to Streamlit Community Cloud with GitHub and deploys that repository's `app.py`, selecting Python 3.11 if offered.
3. The owner pastes `CANARY = "<a random harmless string>"` into the app's Secrets field. No real key.
4. The observations are recorded (build, canary, page; later a sleep/wake observation). **The app and repository are kept until then; deleting them is a later explicit action.**

| Item | Needed from the lead |
| --- | --- |
| Account access | A Streamlit Community Cloud sign-in via the owner's GitHub account (an OAuth grant) |
| Publication | A new public repo with the two stub files (step 1). **Not** making `atlas` public |
| Spending | None for stage A. HF PRO ($9/month) only if the fallback is chosen. Any inference beyond awarded credits needs separate approval. Billing settings stay unchanged |
| API calls | None for stage A. Stage B is one free `GET /models`; no inference |
| Secrets | The owner enters all secrets personally; the builder never sees or prints a value |
| Credits | Someone reading the Nebius console for balance and expiry |

## 9. What is still missing (why T-03 is not accepted)

T-03 requires each open check answered by a dated source or an observed test. Answered by documentation: plans and permissions, private-source behavior, sleep rule, secrets support, price, 90-day credit term. **Answered by observation (2026-10-15/16, owner-reported):** the minimal build, the secret store, signed-out access, one sleep/wake cycle (§7a), and one hosted run of the budget-store scenarios on Neon PostgreSQL 18, which included outbound Postgres and the access-code gate (§5b). The retry rule is settled (DECISIONS.md, 2026-10-15).

**Lead decisions (2026-10-16, DECISIONS.md "T-03 hosting decisions"):**
1. limited hosted for V1 plus full local Docker execution, with full hosted a stretch goal;
2. Neon selected as the budget store;
3. the availability plan accepted, with recorded examples and the local build as fallbacks and no uptime guarantee;
4. the judge-access and budget design accepted for planning scope, with caps described as planned controls, billing unchanged and no extra spending;
5. credit expiry and promotional-use eligibility kept unknown;
6. stages B and C deferred to T-12, which must test Nebius connectivity and the full locked build on the host before the hosted app is called ready.

### Mapping against the T-03 acceptance criteria (exact wording, TASKS.md T-03)

**Criterion 1: "each open check is answered with a dated source or an observed test".** The open checks are those in DECISIONS.md "Open hosting and access checks":

| Open check | Answer | Basis (dated) | Met? |
| --- | --- | --- | --- |
| Nebius promotional credit amount, arrival and **expiry** relative to 15 Dec 2026 | Amount and arrival: $50 awarded (user-reported); balance $50.00 on the owner's billing view. Expiry: **unknown**, handled under criterion 3 | Owner's screenshot, 2026-10-15 (§6); Builder terms, fetched 2026-10-15 | Yes for amount and arrival; expiry under criterion 3 |
| Per-token prices for the selected model; cost per bounded demo run | $0.30 / $0.90 per 1M tokens. About $0.021 per normal run and $0.051 worst case at the **proposed** per-stage ceilings | Authenticated `GET /models`, 2026-10-14 (observed); `hosting_probe/cost_calc.py`, 2026-10-15 | Yes, as a dated estimate. The per-call ceilings themselves are an open T-06 lead decision (per-stage $0.051 vs. uniform $0.0648), so the run cost is not yet a configured figure |
| Cost and reliability of keeping judging access available through 15 Dec (plan limits, sleep/cold-start) | Hosting $0; 12-hour sleep; one observed wake in about 23–24 s; plan accepted with fallbacks, no uptime guarantee | Streamlit docs, 2026-10-15; observation 2026-10-16 (§7a); lead decision 3 | Yes. Reliability is answered by documentation plus one observation, not by a long-term test |
| Whether a candidate host can run a separately isolated worker meeting the execution contract; its cost and delivery time | Community Cloud: no supported route (documented absence). HF Docker Space: documented constraints, not demonstrated. Separate worker VM: not demonstrated, and **its cost and delivery time were not researched** | Docs fetched 2026-10-15 (§3); lead decision 1 | **Partly.** Answered for the two hosts considered. For a separate worker, cost and delivery time are recorded as unknown, not answered. Q5 adopts full hosted only "if demonstrated", so the V1 decision does not depend on them, and decision 1 makes it a stretch goal. See the readiness note below |
| Judge-access route or reserved capacity, and the restoration procedure when budgets run out | Private judge code checked server-side with a separate judge pool; restoration by the owner raising a cap (needs spending approval) | Design, 2026-10-15 (§5); the probe's code gate and reservation primitives observed on the host, 2026-10-16 (§5b); lead decision 4 | Yes, for planning scope. Not built |
| Server-side cost-control implementation (per-session, per-route, daily caps) and how exhaustion is shown | Reserve-before-call on Neon with atomic conditional updates; on exhaustion, labelled recorded examples, then "Unavailable" | Design (§5, §5a); five scenarios observed on Neon 18, 2026-10-16 (§5b); lead decisions 2 and 4 | Yes, for planning scope. Implementation and verification are T-12/T-06 work |

**Criterion 2: "a recommendation between limited hosted and full hosted, stating its evidence".** §1 and §3 give the recommendation with labelled evidence, and the lead chose limited hosted (decision 1). **Met.**

**Criterion 3: "promotional-credit expiry against Dec 15, 2026, confirmed or marked unknown".** The expiry is **marked unknown** (§6; decision 5), and so is promotional-use eligibility. **Met** (the criterion allows "marked unknown").

**Moved to T-12, not T-03 criteria:** Nebius connectivity from the host (stage B) and the full locked-environment build on the host (stage C). Both must be tested before the hosted app is declared ready (decision 6).

**Readiness (builder's assessment, 2026-10-16):** T-03 is ready for the lead's acceptance decision within its research-and-feasibility scope, with one residue the lead must judge. Criteria 2 and 3 are met as written. Criterion 1 is met for every open check except one: the cost and delivery time of a separate isolated worker are recorded as unknown, not answered. The criterion is not reworded to cover that. Accepting T-03 therefore means the lead judges the residue acceptable because full hosted is a stretch goal; the alternative is a short, documentation-only price search before acceptance. **T-03 is not accepted.**

## 10. Sources (all fetched 2026-10-15)

- Streamlit: [Status and limitations](https://docs.streamlit.io/deploy/streamlit-community-cloud/status) (supported Python versions, private repos: deploy key, `repo` scope, admin permission); [Share your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app) and [share apps with viewers outside an organization](https://docs.streamlit.io/knowledge-base/deploy/share-apps-with-viewers-outside-organization) (private by default; one private app; public toggle independent of the repo); [App dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies) (`uv.lock` first); [Manage your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app) (12-hour sleep, Feb 2024 resource figures, restarts); [Secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management) (seen through a search summary, not fetched directly: its page URL returned 404).
- Hugging Face: [Spaces overview](https://huggingface.co/docs/hub/spaces-overview) (visibility, plans, hardware, secrets, networking, lifecycle); [Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker) (user ID 1000, secrets, persistence); [Pricing](https://huggingface.co/pricing) (PRO $9/month).
- Nebius: [Builder Program terms](https://nebius.com/builders-terms-and-conditions) (credit amounts, 90-day expiry, use restrictions); [Token Factory billing](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new) (trial credit, usage tab, negative-balance charging); [promo codes](https://docs.nebius.com/signup-billing/payments/promo-codes). Price: the project's own authenticated `GET /models` on 2026-10-14 (local, git-ignored).
- Project: SPEC §10, §11, §13; DECISIONS.md "Open hosting and access checks"; playbook §22.5; docs/SUBMISSION_CHECKLIST.md; TASKS.md T-05.
- Calculation: `hosting_probe/cost_calc.py` (committed; arithmetic only, no API calls).
