# T-03 hosting probe: research and local design

Status: **research and local design complete (2026-10-15); stage A deployed by the owner and first observations recorded (§7a); sleep/wake observation pending; T-03 is NOT accepted.** Lead decisions of 2026-10-15 (DECISIONS.md "Hosting probe decisions") are applied below. Required feasibility evidence is missing (see §9). Nothing was deployed, no account was linked, no repository or secret was created, and no API call was made. Written under TASKS.md T-03 (Sonnet 5.5, medium effort); the lead decides, and the decision goes in DECISIONS.md.

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
| **Execution mode** | **Limited hosted** (curated examples; fixed trusted evaluation functions; generated diffs shown as "not executed here") | Agreed default (SPEC §13). Full hosted execution is **not demonstrated** (§4). |
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
| Sleep | Apps with no traffic for **12 hours** go to sleep; anyone with access can wake them with a button. **Documented**. Cold-start time: **unknown** (not measured) | "On free hardware, your Space will go to sleep ... after a period of time if unused"; running indefinitely needs paid hardware. CPU Basic is the free tier, so a PRO-plan Space on CPU Basic would still sleep. **Documented**, period **unknown** |
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

**What needs durable storage.** The counters, the reservations, the judge code's quota and the "budget exhausted" state. Community Cloud memory is cleared on restart, sleep or reboot (**documented**) and its disk persistence is not documented, so in-process counters are only a soft limit: a restart resets them. Multiple instances are not documented, so assume more than one process could exist and keep all counters in **one external store with atomic conditional updates**, never in app memory. Which store (a small free-tier database or key-value service) is **unknown**: not researched, and it needs another account and an approval (§8). If the store is unreachable, **fail closed** to recorded-example mode.

**Judge access control.** A hidden URL is not access control. A long random **judge access code** is given privately in the Devpost testing instructions; the app compares it server-side against a stored hash, charges the judge pool, and never exposes it to the browser, prompts, Git or logs. If the public pool is exhausted, judges with the code still reach live mode until the judge pool is exhausted. If both are exhausted, the restoration procedure is: the owner raises the cap in the store (or tops up credits) and the app returns to live mode with no redeploy.

**Backstop.** Nebius documents no per-key spending limit (not found; **unknown**). **Payment information is already on the account (lead, 2026-10-15) and billing settings are not changed.** Because the billing page says a negative balance leads to an automatic card charge (**documented**), the credit balance is **not** a hard ceiling: usage beyond the credits could be charged to the card. The in-application caps above are therefore the real spending control, they fail closed, and the $30 inference allowance is a planning figure, not an authorization. Whether an account with a payment method is auto-paused or charged at zero balance is **unknown**.

## 6. Credits and the 15 December requirement

| Fact | Status |
| --- | --- |
| $50 in Token Factory credits awarded in total (an initial $25, then an additional $25) | **User-reported** (STATUS.md). Remaining balance **unverified** |
| Nebius Builder Program terms: "All promotional credits are nonrefundable, nontransferable, and expire 90 days from the date of issuance" | **Documented** (nebius.com/builders-terms-and-conditions, 2026-10-15). Whether the user's credits fall under these terms is **unknown** |
| If the first $25 was issued on 2026-10-14 (the earliest evidence that the key worked), 90 days ends about **2027-01-12**, after 15 December. The issue date of each award is **unknown**, so this is an illustration, not a finding | **proposed** reading, **unknown** dates |
| The terms say the same programme credits must not be used "for production workloads, large-scale commercial deployment, or any revenue-generating activity beyond prototyping and experimentation", and that Nebius may auto-pause an account whose monthly use exceeds the allocation by more than 30% | **Documented.** Whether a public judging demo counts as prototyping or production is **unknown**; the lead should confirm with Nebius before relying on credits for public traffic |
| Promo-code pages say "usually" a promo has an expiry and do not give a validity after applying | **Documented**, no specific answer |

**The expiry of the user's actual credits, and the balance, are unknown** until someone reads the Nebius console (Usage / balance). Until then, T-03's third acceptance criterion is "marked unknown".

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

**Not yet observed (stage A is incomplete):**
- **Sleep/wake.** Documented: apps with no traffic for 12 hours go to sleep. The 12 hours restart with every visit, including the owner's. The owner's signed-out visit at about 18:44 -0400 restarted the 12 hours, so the earliest sleeping state to test is about **2026-10-16 06:54 -0400** (12 h 10 min after that visit, with **no visits in between**). The test is: visit, time how long the wake-up button and the page take, and read `process_uptime_s` (a small value shows a fresh process).
- **Outbound network** from the host: untested by design (stage A has none).
- **Full locked environment** (61 packages, stage C): untested. This build installed Streamlit only.
- **Availability through 15 December:** not established by a single day's observation.

The probe stays deployed until the sleep/wake observation is recorded. Deletion is a later, explicit action.

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

T-03 requires each open check answered by a dated source or an observed test. Answered here by documentation: plans and permissions, private-source behavior, sleep rule, secrets support, price, 90-day credit term. **Still missing:**

- cold-start / sleep-wake time is not yet observed (the stage A build and canary were observed, §7a); outbound network is untested;
- credit balance and the real expiry of the user's credits are unknown;
- the Nebius account's behavior at zero balance is unknown, and no per-key limit was found;
- the durable store for counters is not chosen;
- full hosted isolation is not demonstrated (a classification, not a negative result);
- Streamlit's availability through 15 December is not established by anything read.

**Recommendation to the lead (proposed):** approve stage A; record the limited hosted mode as the plan in DECISIONS.md; clarify the retry rule (§4.2); decide the durable store; confirm the credit terms with Nebius. T-03 can be accepted once stage A's observations and the credit facts are recorded.

## 10. Sources (all fetched 2026-10-15)

- Streamlit: [Status and limitations](https://docs.streamlit.io/deploy/streamlit-community-cloud/status) (supported Python versions, private repos: deploy key, `repo` scope, admin permission); [Share your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app) and [share apps with viewers outside an organization](https://docs.streamlit.io/knowledge-base/deploy/share-apps-with-viewers-outside-organization) (private by default; one private app; public toggle independent of the repo); [App dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies) (`uv.lock` first); [Manage your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app) (12-hour sleep, Feb 2024 resource figures, restarts); [Secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management) (seen through a search summary, not fetched directly: its page URL returned 404).
- Hugging Face: [Spaces overview](https://huggingface.co/docs/hub/spaces-overview) (visibility, plans, hardware, secrets, networking, lifecycle); [Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker) (user ID 1000, secrets, persistence); [Pricing](https://huggingface.co/pricing) (PRO $9/month).
- Nebius: [Builder Program terms](https://nebius.com/builders-terms-and-conditions) (credit amounts, 90-day expiry, use restrictions); [Token Factory billing](https://docs.tokenfactory.nebius.com/other-capabilities/billing-new) (trial credit, usage tab, negative-balance charging); [promo codes](https://docs.nebius.com/signup-billing/payments/promo-codes). Price: the project's own authenticated `GET /models` on 2026-10-14 (local, git-ignored).
- Project: SPEC §10, §11, §13; DECISIONS.md "Open hosting and access checks"; playbook §22.5; docs/SUBMISSION_CHECKLIST.md; TASKS.md T-05.
- Calculation: `hosting_probe/cost_calc.py` (committed; arithmetic only, no API calls).
