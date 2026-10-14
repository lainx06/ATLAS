# ATLAS — start here, then follow one step at a time

Revision 5 • October 14, 2026 • For Adnan Hossain

**Start in a new ChatGPT lead chat. Claude Code is your first coding workspace after the short kickoff.** You do not need to configure Gemini, agents, or every skill before starting.

This guide is the operating sequence. ATLAS_Master_Prompt.md instructs the lead; ATLAS_Build_Playbook.md is the technical reference. These documents prepare the build. They do not mean the app or any tools are already installed.

## The setup we will use

Default: Windows, VS Code, Claude Code in its terminal, and the Codex extension in the same editor. Keep one local ATLAS folder. If you already have a working WSL setup, tell the lead before installing anything; it should adapt the commands rather than create a second copy.

| Place | What you do there | Model to start with |
| --- | --- | --- |
| ChatGPT lead chat in your browser | Get the next task, resolve decisions, reconcile reviews | Astra High, if offered |
| Claude Code in the ATLAS folder | Set up tools, write files, run tests, fix bugs | Opus High for core work; Sonnet Medium for routine work |
| Codex panel in VS Code | Independently inspect actual code and test evidence | Astra High if offered; otherwise available GPT-6 coding model at High |
| Gemini browser conversation | Challenge the science; later critique the video | Argon High for science; Medium for the video |

These are project defaults, not proof one model is universally better. Record the actual versions. A model absent from the picker is unavailable in that interface; do not buy another product just to match a name. Claude Max is a subscription, not a reasoning setting. Existing ChatGPT/Gemini accounts and Claude Max do not fund Nebius runtime usage.

A **repository/repo** is your project folder tracked by Git. A **commit** is a named checkpoint. A **terminal** runs commands. A **skill** is a reusable instruction folder, sometimes with scripts. An **MCP tool** connects an agent to a capability such as a browser. Development skills help build ATLAS; ATLAS's learned evaluation procedures are a separate product feature.

## Which files does each assistant get?

ChatGPT gets all three MDs once at kickoff. Claude Code reads all three from docs/handoff/ once during setup, then reads the current task and changed specifications. Gemini normally gets PROJECT_BRIEF.md, the relevant specification/evidence, and its focused review packet. You may attach all three to Gemini for a one-time orientation, but they are not required for each review. None of these chats automatically shares messages. Same-folder Claude Code and local Codex can share files; browser chats need attachments or pasted packets.

## What we are building

ATLAS is a research and engineering workspace that checks whether a machine-learning experiment supports the claim being made about it. LENS is its first capability: inspect a supported project, execute concrete evaluation checks, propose a bounded code revision, compare the resulting evidence, and save a procedure only with verified prerequisites. The central demonstration is a misleading evaluation being diagnosed and corrected, followed by justified reuse—or refusal to reuse—on another project. A lower score can be the honest result. V1 aims for a hosted browser interface with curated examples; deployment is not yet complete.

## Step 1 — Open the lead chat

**You do this.** Open a new ChatGPT chat, select Astra High if available, paste ATLAS_Master_Prompt.md, and attach this guide plus ATLAS_Build_Playbook.md.

Add:

> Begin at Start Here Step 1. Guide me one step at a time. I am using Windows. First establish whether you can actually access my PC or only a cloud workspace. Give me the next action with the application, model/effort, exact command or prompt, expected result, and what to bring back. Do not build a separate cloud copy while I set up the local repository.

Full-day availability is already confirmed. Tell it whether Claude Max and Nebius are active. Plan substantial daily milestones without the previous 2–3-hour cap; keep the existing scope and verification gates. It should select the next step, not generate another long project plan.

**Done when:** you know the current step, chosen local setup, and today's deliverable. Allow about 10 minutes for kickoff; setup can take longer.

## Step 2 — Handle the accounts that need you

**Stay in the browser. No model change.**

- Sign in to the Claude account your Max subscription will use. Account purchase and sign-in are yours to complete; do not send passwords to a chat.
- Join the Devpost event if you have not already, confirm the eligibility questions, and create a draft entry for **Coding and Agentic Engineering**.
- Open your Nebius account and check whether Token Factory access and promotional credits are actually available. Record access as ready/pending in the lead chat. The builder will prepare a secure configuration file later; do not paste a key now.

**Done when:** each account is marked ready or pending. A pending Nebius account does not prevent offline checks, but must be resolved before the live agent milestone.

## Step 3 — Install the four starting tools

**You do this in Windows PowerShell, not in an AI message box.** Search the Windows Start menu for PowerShell and open it. Run one line at a time. Skip a tool if it is already working.

~~~powershell
winget install --exact --id Microsoft.VisualStudioCode
winget install --exact --id Git.Git
winget install --exact --id Anthropic.ClaudeCode
winget install --exact --id astral-sh.uv
~~~

Close and reopen PowerShell after installation. Run:

~~~powershell
git --version
claude --version
uv --version
~~~

You should see three version numbers. Open VS Code from the Start menu to confirm it launches. If a command fails, stop that step and send the lead the command and exact error, with private details removed. Do not paste Linux commands into PowerShell or change machine security settings to force an installer through.

These commands are for native Windows. Git and Claude/uv installation methods are documented in playbook sources S28–S32. The lead checks the package identity before using an alternative installer.

**Done when:** VS Code opens and Git, Claude Code, and uv report versions. Python packages, Docker, browser testing, and selected skills come next through the builder; do not install a giant toolbox now.

## Step 4 — Make the project folder and put the handoff inside

In PowerShell:

~~~powershell
$atlasRoot = Join-Path $env:USERPROFILE "source\atlas"
New-Item -ItemType Directory -Force -Path (Join-Path $atlasRoot "docs\handoff")
Set-Location $atlasRoot
code .
~~~

If "code" is not recognized, open VS Code normally and use **File → Open Folder** to open the atlas folder under your user profile's source folder. If that folder already contains unrelated work, stop and choose an unused folder with the lead.

Download all three MD files into **atlas/docs/handoff/**, preserving their names. In VS Code, confirm they appear in the left file list. Save the kickoff decisions as **docs/handoff/KICKOFF.md**; the lead should supply the short text.

**Done when:** one folder contains the three handoff documents and your kickoff note. Do not initialize a second GitHub/cloud project with different files.

## Step 5 — Start Claude Code and give it the setup task

In VS Code choose **Terminal → New Terminal**. Confirm the terminal is in the atlas folder, then enter:

~~~powershell
claude
~~~

Complete its sign-in with the Claude account that has Max. Use subscription sign-in rather than adding an API billing account merely for this build.

**Now you are inside Claude Code.** These are Claude commands, not PowerShell commands. Enter them separately:

~~~text
/model opus
/effort high
~~~

If a command or model is unavailable, use its displayed model/effort picker and tell the lead what choices exist. Confirm the setting shown in the session.

Paste:

> You are ATLAS's main builder. Read all four files in docs/handoff/: ATLAS_Start_Here.md, ATLAS_Master_Prompt.md, ATLAS_Build_Playbook.md, and KICKOFF.md. Treat the master prompt as project context; your current assignment is setup, not a second lead conversation. We are at Step 5. Inspect this actual folder without overwriting existing work. Initialize Git if needed; create the shared instructions and state files defined in the playbook. Put WRITER: Claude Code in STATUS.md. Create CLAUDE.md that points to AGENTS.md and the current state. Set up the Python 3.11 uv environment, resolve and lock dependencies, and run a small import check. Do not implement the app yet. Create .env.example and exclude private credentials and generated artifacts from Git. Return actual paths, versions, commands/results, and one next action. If Git needs my name/email, ask for the values; do not invent them.

The builder should do work directly. It may need you to approve normal local tool operations or supply account details; it must explain what and why.

**Done when:** Git is initialized, imports work, uv.lock exists, and STATUS.md records setup and blockers. No automated report counts as tested until it has actually run.

## Step 6 — Have Claude install the selected skills

**Stay in Claude Code, Opus High.** You do not need to navigate hidden folders manually.

Paste:

> Execute the selective skill-install recipe in playbook Section 22. Use project-local folders for Claude Code and Codex. Inspect and pin the canonical sources before installation; include companion skills, referenced files, and license notices. Initially install Matt's setup-matt-pocock-skills, grill-with-docs and to-spec with their dependencies, and Addy's code-review-and-quality, debugging-and-error-recovery, and test-driven-development. Do not install whole workflow packs, automatic hooks, pstack, or no-mistakes. Add Ponytail only after our first working slice. Verify discovery and reference resolution, record real versions in docs/TOOLING.md, and give me the exact invocation names that work in this client. If installation is blocked, report the exact failure and use the inspected runbook manually for now.

Section 22 tells the builder how to fetch, preserve, install, and validate the skill files. It also explains the optional plugin route. Installing files and successfully loading a skill are separate checks.

**Done when:** docs/TOOLING.md distinguishes installed, verified, manual-only, and deferred items. Give the lead its short status. Budget roughly 30 minutes; continue useful work if one optional skill cannot load.

## Step 7 — Settle requirements and produce the first tasks

**Stay in Claude Code, Opus High.**

Use the verified invocation for Matt's setup skill. Choose **local files** as the issue tracker, **docs/** for documents, and TASKS.md for the task index. Then invoke grill-with-docs with:

> Use the handoff decisions as defaults. Ask only questions that change our supported input, evaluation claim, execution boundaries, or demo access. Limit the unresolved-requirements discussion to about 20 minutes. Produce docs/PRD.md and docs/SPEC.md locally. Make TASKS.md a sequence of small demonstrable milestones. Each task needs acceptance criteria, owned files, model/effort, verification commands or an instruction to create them, and its next review gate. Do not publish issues or restart project selection.

The builder can synthesize the spec directly or use the installed to-spec flow configured for local files.

**Done when:** a short PRD, technical spec, and first implementation task exist. Ask the builder to explain the first milestone in plain language; you should be able to describe what would count as failure.

## Step 8 — Give Gemini one scientific review

**Switch to Gemini, Argon High.** Claude first creates **handoffs/science-01.md** with the brief, relevant evaluation design, benchmark definitions, and at most five unresolved questions. Attach that packet and any files it explicitly references. No secrets or held-out labels.

Paste:

> Review this ATLAS design without implementing it. Focus on deployment mismatch versus actual leakage, preprocessing boundaries, clean controls, and fair memory comparisons. Return at most five consequential findings, each with a counterexample or proposed executable check. Do not propose a new product or judge code you cannot see.

Return Gemini's exact findings to the ChatGPT lead. The lead records accepted/rejected/deferred decisions and supplies the first implementation task for TASKS.md. If the lead cannot edit the local folder, it supplies the exact text for Claude to save. Formal upload packets are for major browser reviews; routine local work uses the shared repo.

**Done when:** each finding has a disposition and the next build task is unambiguous. Do not wait for three models to agree on every detail.

## Step 9 — Build and independently review the first slice

**Switch to Claude Code, Opus High.** Point it to the first accepted task in TASKS.md. It should build faulty, clean, and unsupported fixtures; group/split and fit-provenance checks; evidence JSON; and meaningful tests.

When done, ask:

> Update the current TASKS.md/STATUS.md entry with acceptance criteria, base/head checkpoint, changed files, actual test results, and limitations. Give me a short prompt pointing local Codex at that checkpoint and evidence. No separate upload packet is needed. Commit the candidate if appropriate; do not certify your own implementation.

**Switch to Codex for review.** In VS Code open Extensions, search for **Codex**, verify the publisher is **OpenAI**, install it, and sign in with your existing ChatGPT account. Open its panel in the same atlas folder and use a local workspace session. The official extension is openai.chatgpt. Use Astra High if offered; otherwise the available GPT-6 coding model at High. Record the choice.

Paste:

> Read AGENTS.md, STATUS.md, and the current TASKS.md entry at the supplied checkpoint. Review only; do not edit implementation files. Independently inspect the actual diff and run relevant existing checks where permitted. Use the ATLAS rubric in the playbook. Return demonstrated blockers, evidence, the smallest fixes, and tests you actually ran. State whether the selected project-local review skill loaded. A builder summary is not evidence that tests passed.

Codex reads the files directly in this shared local folder. Return its findings to Claude locally; no browser relay is needed for routine fixes. Browser ChatGPT and Gemini need uploaded/pasted packets only for the reviews that call for them. Record each consequential finding once rather than duplicating several reports.

Bring confirmed findings to Claude. Claude repairs and reruns affected checks; Codex reviews the relevant delta if necessary.

**Done when:** the first slice demonstrates a finding, a clean pass, and NOT_ASSESSED with no demonstrated blocker. Record results in STATUS.md. A reviewer unable to run tests must say so.

## Step 10 — Complete Nebius and isolation setup before live execution

**Claude Code, Opus High.** Ask it to implement the environment/model smoke check and container verification described in the playbook.

You privately enter the Nebius key in the local ignored configuration file the builder prepared. The builder must name the exact variable and file before you enter it, and must not echo the value. It should list available models, select a real NVIDIA model ID, and make one capped test call. Save sanitized evidence.

For isolation, use an existing working Docker setup. If none exists, the builder guides installation of Docker Desktop for Windows and its required Linux-container backend. You handle OS prompts/restarts. Verify the client and server are running and the container smoke test succeeds. The lead should diagnose the actual prerequisite if it fails rather than demand a new OS.

**Done when:** NVIDIA runtime access is confirmed separately from a restricted candidate-runner test. A successful Docker hello-world is only installation evidence; the actual runner must also enforce the mounts, network, credentials, resource, and timeout limits in the spec. Until then, use trusted fixtures only. Do not replace the runner with a temporary folder and ordinary subprocess execution of generated code. If the web host cannot provide isolation, use a separately isolated worker or a clearly limited trusted-pipeline demo plus a tested local full build; see playbook Section 22.5.

## Step 11 — Repeat the same build loop through the milestones

Do not manually invent new prompts each day. The lead establishes the milestone order; Claude works through the accepted TASKS.md entries, tests establish the result, and local Codex reviews consequential changes. Browser lead/Gemini reviews happen at major decisions and evidence gates. Full-day availability permits several bounded tasks in a day without requiring a provider switch or new document for each one.

| Milestone | Builder setting | Switch/review trigger | Observable result |
| --- | --- | --- | --- |
| Independent metrics, temporal checks, isolated runner | Opus High | Codex Astra Extra high if offered | Manual candidate revision evaluated; negative cases rejected |
| Nebius tool loop | Opus High | Codex High | Real NVIDIA call → valid action → checks → isolated patch → report |
| Basic Streamlit workflow | Sonnet Medium | Browser verification after behavior changes | A user can complete the supported workflow |
| Procedure admission and reuse | Opus High | Codex High; Gemini High for evaluation claims | Compatible reuse works; mismatch refuses reuse |
| Fair comparison and real-data example | Opus High | Gemini High plus deterministic evidence | Reproducible results, including limitations and null findings |
| README, ordinary UI copy, packaging | Sonnet Medium | Targeted check; no three-provider circuit | A fresh user can run the documented example |
| Final scientific/execution review | Opus High for fixes | Codex Extra high if available | No known release-blocking finding remains |
| Demo critique | No new implementation by Gemini | Gemini Medium | Clear story with supported claims |

Use the playbook calendar to schedule these. Do not equate a target date with completion.

## Step 12 — Add browser tests when the interface exists

**Claude Code, Sonnet Medium initially; Opus High if failures cross into core logic.**

Before the first UI implementation, follow playbook Section 25: Claude Opus High uses Anthropic frontend-design to produce docs/UI_SPEC.md; the builder loads Streamlit's version-matched development skills and implements one complete screen. Use Sonnet Medium for subsequent bounded styling work. Codex High uses Addy's frontend-ui-engineering for a focused review, with actual browser evidence. Install these additions at the UI milestone, not as prerequisites for the first scientific check.

Design the core workspace around the deployment claim, evidence findings, original/revised protocol, patch diff, and procedure prerequisites. Inspect screenshots at realistic desktop and narrow widths; test empty, running, failed, and unsupported states. A polished homepage alone does not complete the UI milestone.

Ask the builder to install Playwright's Python test tooling, create the acceptance scenarios, and capture trace/screenshots on failure. It runs the UI and tests; you perform one normal manual walkthrough too. Optional browser MCP is added only if the evaluator lacks browser access; Section 22 has the setup task.

The loop is: reproduce → save evidence → repair → rerun the same scenario and affected checks. After two failed repair cycles, stop retrying blindly and send the evidence to Codex for diagnosis.

**Done when:** selection, claim confirmation, evidence, revision, procedure mismatch, export, and API-failure behavior have been exercised. An offline browser fixture test does not prove live Nebius integration; run a separately capped live smoke test.

## Step 13 — Freeze, measure, and package

**Claude builds; Codex checks release blockers; Gemini reviews scientific claims/video clarity.** Freeze features around October 25–26. Keep the final unfamiliar evaluation case out of development prompts. Use measured results, not desired numbers. Record failed attempts and procedure-creation cost when discussing savings.

Ask Claude to prepare the README, reproducible release, public demo/test-build instructions, sanitized sample report, and Devpost draft. Use playbook Section 23 to check every deliverable. Target a roughly 2 minute 40 second video; record around October 27–28.

**Done when:** a fresh setup works, the submitted version matches the video, and public statements match evidence. Peers' feedback is useful if actually obtained; do not invent testimonials.

## Step 14 — Submit and keep the release accessible

**You submit in Devpost, with the lead checking the concrete package.** Target October 29. The checked deadline is October 30, 2026, 13:00 New York time; verify it again before submitting.

Check the final repo, demo/test-build, and public YouTube links in a signed-out browser. Use the Coding and Agentic Engineering track. Include sponsor feedback and the required prior-work statement if applicable. Save the submission confirmation privately. Maintain access to the submitted release through judging; later development stays separate.

**Done when:** the entry is submitted and the exact submitted links work. A draft is not a submission.

## How the lead must tell you to switch models

At every task boundary it must provide a short action card:

~~~text
STEP / TASK: current number and identifier
MODEL DECISION: STAY or SWITCH, with one sentence explaining why
OPEN: exact application
SELECT: model family/version if known, effort, and where to change it
SHARE: actual packet/files; or "same local repo, read these paths"
DO / PASTE: one bounded action or exact prompt
EXPECTED RESULT: observable evidence
IF IT FAILS: what error/artifact to capture
RETURN: specific output and destination
~~~

Switch only when the work changes, a review gate is reached, or a concrete problem requires escalation. Do not rotate providers after every message.

- Routine task becoming scientifically ambiguous: checkpoint, then Sonnet Medium → Opus High.
- Two unsuccessful focused repairs: preserve the failing case and ask an independent reviewer; use Extra high for difficult diagnosis if offered.
- Max effort: only for one well-defined unresolved blocker after ordinary diagnosis. Return to the normal setting afterward.
- Usage limit: checkpoint and update WRITER before Codex takes over. Never have both continue editing the same files.
- New chat: provide STATUS.md, PROJECT_BRIEF.md, and the current task. Supply a formal packet when the receiver lacks repo access or the review is substantial; do not assume memory transferred.

Claude model switches use its /model and /effort controls. ChatGPT, Codex, and Gemini use the controls actually visible in their interface. A chat response claiming "I switched your other model" is not a real switch.

## Daily restart and what to do when stuck

At the start of a session, open the same folder and ask the lead or builder to read STATUS.md, state what actually works, and identify one next task. At the end, save the checkpoint, test results, unresolved issue, current writer/model, and next task. Ask the builder to explain one important design choice so you can defend the work in interviews.

If you see an error, send the exact command, application, working folder, and relevant output. If it contains a credential, remove the credential. Do not reinstall everything. If a skill is missing, use its inspected instructions manually while the loader is fixed. If a reviewer lacks access, attach the real files/diff instead of sending an inaccessible PC path.

Begin with **Step 1 only**. The lead should guide the rest at your pace and do accessible technical work directly.
