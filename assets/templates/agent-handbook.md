# Agent handbook — everything an agent needs to work in this repository

> **OR-26:** one always-current file, linked from [AGENTS.md](../AGENTS.md), with everything any agent needs to work
> here at any moment: where every piece of information lives and every tool — what it does, when to use it, how, who.
> It points to the authoritative home of each rule instead of copying it (DRY): when this file and its source
> disagree, the source wins and this file gets fixed. The drift check `python3 -I .boa/tools/handbook_drift.py` fails
> when a tool exists but is not named here, or when this file names one that no longer exists (§9).

Contents: [1 Start here](#1-start-here) · [2 Map of information](#2-map-of-information) · [3 Tools](#3-tools) ·
[4 Test suites](#4-test-suites) · [5 Workflows](#5-workflows) · [6 Lead-local state](#6-lead-local-state) ·
[7 Safety and hard rules](#7-safety-and-hard-rules) · [8 Talking to the owner](#8-talking-to-the-owner) ·
[9 Keep this file current](#9-keep-this-file-current)

Paths: `<main>` = the main checkout; `<wt>` = a lane worktree `{{BOA_WT_DIR}}/<T>`; `<T>` = a task id
(`T-NNN`); `<scratch>` = the session scratch root `{{BOA_SCRATCH_ROOT}}` (shared by every lane; each
agent owns only `<scratch>/<T>-<role>/`); `<lead>` = `<main>/{{BOA_LEAD_DIR}}`. Every BOA tool lives under `.boa/`
and reads `.boa/config.env`; each script's header comment (and `--help`) is its full reference, the rows below are
the summary. `.boa/` is a tool, never the project (OR-68): git-ignored, reinstalled with `boa install`, never part of
the product or its releases; what you write for the project (memory bank, plan, specs, this file) stays versioned.

## 1. Start here

| You are | Read, in order | Then |
|---|---|---|
| **Any agent** | [AGENTS.md](../AGENTS.md) → this file → [memory-bank/RESUME.md](../memory-bank/RESUME.md) → every `memory-bank/*.md` (08 and 09 are binding) | your brief, your role contract in [.boa/agents/](../.boa/agents/) |
| **The lead** (orchestrating session) | as above, then `<lead>/` (§6) | `.boa/bin/lead-status.sh` (§3.2); 09 §1 is the session-start checklist |
| **A sub-agent** (builder, builder-mid, reviewer, tester, integrator, analyzer) | as above; the lead's brief carries `<lead>/brief-common.md` | stay in your worktree and your scratch subdir |
| **A runtime without hooks or sub-agents** | as above; wire what it can as [AGENTS.md](../AGENTS.md) "Wiring" says; what your runtime cannot run, apply by discipline (run the status screen yourself, apply §7) | never write to `<lead>/` or the main checkout |

One-line state of the project: `python3 -I .boa/tools/plan_lanes.py` (progress table) or the last line of
`.boa/bin/lead-status.sh` (DONE/total).

## 2. Map of information

### 2.1 The memory bank (`memory-bank/`, protocol: [memory-bank/README.md](../memory-bank/README.md))

| File | What it is for | Who writes it |
|---|---|---|
| [00-PROJECT-BRIEF.md](../memory-bank/00-PROJECT-BRIEF.md) | north star: what, why, who, scope, constraints | lead, on scope change |
| [01-BLUEPRINT.md](../memory-bank/01-BLUEPRINT.md) | map of all functionality (existing + target) and the verification backlog | when functionality is discovered or re-scoped |
| [02-SPECIFICATIONS.md](../memory-bank/02-SPECIFICATIONS.md) | specs and the contracts index; details in `docs/specs/`, `docs/api/` | spec tasks, before the build tasks |
| [03-IMPLEMENTATION-PLAN.md](../memory-bank/03-IMPLEMENTATION-PLAN.md) | every task (acceptance, deps), the machine-readable plan block (`<!-- plan-lanes:begin -->` … `<!-- plan-lanes:end -->`), the status ledger, the coverage checklist | lead (new rows, via the pending fold), integrator (`; DONE — PR #NN` appended, never rewritten) |
| [04-ARCHITECTURE.md](../memory-bank/04-ARCHITECTURE.md) | architecture, modules, stack, data model, third-party contracts, glossary, the **environment** in use, the **residue register** (parsed by `trace_check.py` and the project's residue check) | when structure or environment changes |
| [05-PROGRESS.md](../memory-bank/05-PROGRESS.md) | chronological log, one `@@@memory` block (type `outcome`) per stage | every agent at the end of its stage (append only) |
| [06-DECISIONS.md](../memory-bank/06-DECISIONS.md) | decision records as `@@@memory` blocks: `ADR-NNN` (type `adr`, architecture) and `EDR-NNN` (type `edr`, execution); append-only, numbers from the lead | lead, tasks that decide |
| [07-SECURITY.md](../memory-bank/07-SECURITY.md) | threat model, known vulnerabilities, the standing checklist | security tasks, the reviewer's reference |
| [08-OWNER-RULES.md](../memory-bank/08-OWNER-RULES.md) | **binding**: every owner rule (OR-IDs) with why, how to apply, where enforced | the integrator folds `<lead>/owner-rules-pending.md` at each train |
| [09-OPERATING-PROCEDURES.md](../memory-bank/09-OPERATING-PROCEDURES.md) | **binding**: how the work is done in practice | same train as the procedure change |
| [10-METALEARNING.md](../memory-bank/10-METALEARNING.md) | curated lessons about the way of working, each with the change it caused | lead, at each train |
| [active-context.md](../memory-bank/active-context.md) | "where are we now": milestone, lanes, Open HITL, deployment | **lead only** (the integrator edits the lines the lead names) |
| [RESUME.md](../memory-bank/RESUME.md) | pointer file: read order and where live state is; holds no state | only when the read order or a location changes |

### 2.2 Documentation (`docs/`)

| Path | Contents |
|---|---|
| [docs/agent-handbook.md](agent-handbook.md) | this file |
| `docs/specs/` | detailed specs (one file per area), referenced from 02 |
| `docs/api/` | interface contracts (APIs, formats, protocols) |
| `docs/parity/features.toml` | the feature inventory (§5.11), checked by `trace_check.py` |
| `docs/clean-room.md` | only in a clean-room project: the protocol (sides, allowed and forbidden sources, Provenance) |

### 2.3 Code, tests and the rest
<!-- The lead fills this section at bootstrap and keeps it current: source layout, test layout, build output,
     configuration, the deployment files. -->

| Path | Contents |
|---|---|
| `IDEA.md` | the idea or refactor brief (greenfield/refactor input) |
| `tests/` | the project's test suites (§4) |

### 2.4 Other discipline files (not in the memory bank)

Every file that is part of the working discipline is listed here, in any format, so no agent forgets one. Each stays
plain readable text (no binary, no generated-only content without its source) and is split or rotated when it grows
too large to read.

| Path | What it is | Read it when | Updated by |
|---|---|---|---|
| `.boa/config.env` | the project's BOA settings, one `KEY=value` per line | a tool needs a value | the agent, at wiring and when a value changes |
| `.boa/markers.json` | the machine-recognised words: the report sections and the Leftovers section the stop hook reads (and its "none"), the review classes, the fold marker, the plan columns; English always kept as aliases | before changing the product language; when a hook does not recognise a report | `boa language set` only (`boa language show` / `check` / `regen`) |
| `.boa/memory-types.json` | the memory types, their routes and recall moments | before writing or recalling a memory | the lead, when a type changes |
| `protected-commands.conf` (in `.boa`) | the project's protected commands and patterns the guard refuses (versioned, like `config.env` and `memory-types.json`) | before adding a protection; when the guard refuses a command | the agent, under a task (project-wiring "project protections") |
| `embed.json` (in `.boa`, when the semantic search is on) | the pinned embedding library and model of the semantic memory search | when the semantic search is switched on or upgraded | the installer |
| `installed.list` (in `.boa`) | the manifest of what the install wrote (the uninstall reads it) | after an install or before an uninstall | the installer only |
| the `pending` dir (in `.boa`, only after a conflict) | the installer's renderings that conflict with a project file, waiting to be merged by hand | after every install that reports a `conflict` or `kept` line | the agent merges, then removes them |
| `<BOA_LOG_DIR>/guard-denials.jsonl` | every denial of the guard (agent, tool, capped reason) and every use of the lead's override | at every train (OR-22) | the guard only |
| `<BOA_STATE_DIR>/agent-bindings.jsonl` | the agent-to-task binding the guard and the pause guard read | when a sub-agent is refused outside its lane | `agent_binding.py` only |
| `memory-bank/.memory-ids.jsonl` | the id ledger of the memories | never by hand | `memory_write.py` only (append-only) |
| the capabilities record (`memory-bank/04-ARCHITECTURE.md` "Environment") | what the machine and the runtime give the agent, the substitutes and what is not enforced, and the decisions taken from it | at session start, before starting lanes | the lead, when the runtime or its version changes |
| the wiring checklist (`references/project-wiring.md` of the BOA package) | what the agent wires for this project | at install, and when a part is rewired | its rows become plan rows; the lead closes them |
| the residue register (in 04) | the kept leftovers with an owner and a removal step | before a lane closes, and at the end | the lead |
| `<lead>/` files (§6) | the live lane state, ledgers and pending folds | session start | the lead |

A new discipline file is added to this table in the same change that creates it (§9).

## 3. Tools

"Who": **lead**, **builder**, **reviewer**, **tester**, **integrator**, **analyzer**, **anyone**.

### 3.1 Quality gate and checks

BOA ships no gate: the project's gate, its self-test, its secret scanner and its git hooks (the pre-commit runs
`memory_lint.py --staged`) are built from the BOA package's `references/project-wiring.md` ("the project gate",
"secret scanning", "git hooks"); their rows go here when the project has them.

### 3.1b The stack plug-in (`.boa/stack/`, stack `{{BOA_STACK}}`)

The rows between the markers come from the stack plug-in: `boa install` replaces the block with the plug-in's
`stacks/<stack>/handbook-rows.md` (a complete table naming every file the plug-in installs under `.boa/stack/`, the
rows file included, literal text with no placeholder); the drift check (§9) compares the block with
`.boa/stack/handbook-rows.md`.

<!-- boa:stack-rows:begin -->
| Tool | What, when, how | Who | Side effects / safety |
|---|---|---|---|
| `.boa/stack/plugin.env` | the generic plug-in's settings: TEST_COMMANDS (test-file glob → command), TEST_RUNNER_MAX_FILES, TEST_HEAVY_IMAGE (the image of the service the heavy tests need; no default); the agent configures the project's tools here at bootstrap | lead at bootstrap; read by the tools | assignments only |
| `.boa/stack/test-runner.sh` | the targeted test runner: explicit test files only (refuses directories, globs and symlinks); shell suites with bash, every other kind through the command TEST_COMMANDS maps to it; its header states the contract a project's runner fulfils (explicit files, a case filter `--filter=<pattern>`, a heavy switch `--heavy` with its image setting, a per-call cap) | builder, tester | none beyond the tests |
| `.boa/stack/handbook-rows.md` | this stack's rows of the handbook (the block above) | — | — |
<!-- boa:stack-rows:end -->

### 3.2 Lanes, lead state and clock

| Tool | What, when, how | Who | Side effects / safety |
|---|---|---|---|
| `.boa/tools/plan_lanes.py` | **the lane calculator**: checks the plan block (unique ids, deps, no cycle, split parents, DONE consistency, closing tasks), waves (wave 1 = eligible now), hotspot serialisation, critical path, progress (DONE/total and work-weighted). `python3 -I .boa/tools/plan_lanes.py`, `--check` (green after any plan edit) | lead; anyone editing 03 | read-only |
| `.boa/tools/markers.py` (`boa language`) | the **product-language change** and the markers file: `show`, `check`, `texts <key>`, `set <lang> --texts FILE` (every translation required, memory/block syntax refused, every hook self-checked on samples in the new language before the switch, English kept as aliases, the marker sections of the installed files regenerated), `regen [--check]` | lead (09 §31) | `set` rewrites `.boa/markers.json` |
| `.boa/tools/report_capture.py` | the **report capture** of the sub-agent stop hook (never run on its own): a report's Leftovers items into `<lead>/open-items.md` with owner, role and agent; a task agent's report without a Leftovers section flagged (queue line + the hook's warning); a reviewer's non-blocking findings with no blocking one queued; labels from `.boa/markers.json`; reads only the neutral event's `last_message` | the stop hook | appends to `<lead>/open-items.md` |
| `.boa/tools/metalearning.py` | checks `10-METALEARNING.md`'s format and lists lessons seen more than once (rule, brief or tooling candidates) | lead at each train | read-only |
| `.boa/tools/trace_check.py` | the one **traceability check** (OR-49, 09 §26; parity OR-45): plan tasks ↔ contract clauses ↔ specs ↔ features (of the baseline and new) ↔ tasks ↔ proving tests (`@covers-contract`, `@covers-feature`) ↔ the `Managed by` owner ↔ contract versions and their ADRs ↔ residue register ↔ transit queue ↔ pending folds, from the markers of 02/03, `docs/parity/features.toml`, the test headers and the ledgers; one line per mismatch and `MISMATCHES: <n>`. `--report`: the feature report first. `--close`: the train checks PLUS every contract `closed`, an empty transit queue, zero pending folds, the residue register empty (the project's residue check in final mode runs beside it), no open bug. Exit 0 only at 0 mismatches, 1 otherwise, 2 usage error | builder/tester (the task's rows and features), integrator (every train), lead at close-out (must be 0) | read-only |
| `.boa/tools/memory_write.py` | the ONLY way to write a memory (OR-50): `--format-only` formats a block without an id (lanes, into `.lane-resume/memories.md` and their report); `--ingest <file>` runs ONLY in the integrator's train fold (the train's single `docs(memory)` commit: ONE `--ingest` call with all the staging files and every lane's `.lane-resume/memories.md` as one batch, ordered by the tool topologically (every `supersedes` target first), otherwise by datetime, the staging-file and lane order only a tie-break; rebuilt from scratch when a lane bounces; ids never reused on main): final progressive ids in order, routed by type, `superseded-by` stamped on each superseded block; `datetime` (`YYYY-MM-DDTHH:MM:SSZ`) from the clock; a `--format-only` block may carry `supersedes="memory-N"` (a final id) or `supersedes-brief="<brief>"` (a new block of the same batch), resolved by `--ingest`, which stamps both directions atomically and records every id in the ledger `memory-bank/.memory-ids.jsonl` (written only by the tool). Agents NEVER write `@@@memory-<N>` ids or `superseded-by` by hand. Drafts are never consumed: `memory_write.py --ingest` never modifies or deletes a draft. A lane's drafts (`.lane-resume/memories.md`) disappear with its worktree, which is removed only after the lane's fold has landed; the lead's staging files keep the fold marker the lead writes once the fold is on main, which is the record — `--ingest` reads a staging file only below its last single-`#` `Folded by` marker. `--ingest` emits an ingest receipt (per staging file, the ingested prefix: lines 1..N + the sha256 of that whole prefix); `--mark <receipt> --train TRAIN-NNN` (the lead, after the merge) inserts the `Folded by` marker immediately after line N, refusing when the prefix hash no longer matches, never at the end of the file | lanes and the lead (`--format-only`), the integrator's fold (`--ingest`), the lead after the merge (`--mark`) | appends only; the `superseded-by` stamp is the only edit to an existing block |
| `.boa/tools/memory_lint.py` | validates every `@@@memory` block (OR-50): an id not in the ledger `memory-bank/.memory-ids.jsonl` (a hand-written id) fails; a memory superseded twice (a fork) fails; a supersession whose `datetime` is not strictly later than the memory it supersedes fails; the four fields present, `datetime` valid UTC ISO-8601, `type` a type of `.boa/memory-types.json`, `@endmemory` closing it | tester (docs changes), integrator (every train) | read-only |
| `.boa/tools/boa_config.py` | the ONE reader of `config.env` for the tools (read, never executed; one grammar for every tool, the lead and lane hooks, `boa` and the renderer; environment first, then the file, then defaults) and the main-checkout finder | the tools | read-only |
| `.boa/tools/boa_lock.py` | portable file locks (one lock file per target under the state dir) and path helpers shared by the Python tools | the tools | lock files under the state dir (created 0700) |
| `.boa/tools/boa_tool.py` | the shared start-up of the lead and lane tools and their hooks: home, checkout, main checkout, the config with its defaults (through `boa_config.py`), locked appends, bounded child processes | the tools | — |
| `.boa/tools/hook_contract.py` | BOA's neutral hook contract: every hook reads one neutral event (JSON on stdin) and answers one neutral verdict; the runtime's wiring converts both (the BOA package's `references/hook-contract.md`) | the hooks | — |
| `.boa/tools/memory_types.py` | the memory-types configuration `.boa/memory-types.json` (types, routes, recall moments): `--check` validates it, `--render-tables` prints the doc tables (types, routes, recall) the templates carry | anyone changing a type; the gate | read-only |
| `.boa/tools/memory_search.py` | finds memories by keyword, type, task id (`T-NNN`) or date; `--query "<words>"` ranks them best first (BM25, then the matching sentences re-ranked by embedding similarity; fewer hits than `--limit` = every memory also compared by meaning; a `WARNING` line = the environment is missing: re-run `boa install`); `--chain <id>` shows a memory's supersession chain and its current head (supersede the head, never an already-superseded memory) across the memory bank, the lead dir and the journals | anyone | read-only |
| `.boa/tools/memory_embed.py` | the memory search environment (an isolated venv with the pinned embedding library and model, machine-local and git-ignored, in the main checkout's BOA directory): built by `boa install`, removed by `boa uninstall`; run by memory_search, never by hand | `boa install`, memory_search | writes the environment (install only) |
| `.boa/tools/handbook_drift.py` | the handbook drift check (§9) | tester, integrator, anyone changing a tool | read-only |
| `.boa/bin/lead-status.sh` | (`.boa/tools/lead_status.py`) "where is everything" on one screen: every lane (head, ahead, PR, last journal verdict, suggested next step, newest registry line), admission (load, free memory, lane cap {{BOA_LANE_CAP}}), warnings (pending rules or plan lines older than 24 h, stale journals, stages over budget in the registry, open items), resume files, the pause flag, open PRs, Open HITL, new guard denials, DONE/total. `--guards`: only the GUARD DOWN lines | lead | reads only; bookmark `<lead>/lead-status.seen` |
| `.boa/bin/lane-worktree.sh` | (`.boa/tools/lane_worktree.py`) lean lane worktrees: `add <T> <branch>` (from current main; sparse and dependency rules of the stack plug-in), `remove <T> [--force]` (refuses unpushed or uncommitted work) | lead (add), integrator (remove) | never edit a hard-linked dependency file in place |
| `.boa/bin/lane-journal.sh` | the lane journal writer (`.boa/tools/lane_journal.py`): appends a sub-agent's final report (capped, copied as written) to `<lead>/lanes/<T>.md`; called by the sub-agent stop hook; `--task` names the task an entry goes to | — (the hook calls it) | never prints, never blocks; the report is the journal entry, so it must stand alone |
| `.boa/bin/pause-flag.sh` | (`.boa/tools/pause_flag.py`) the pause flag: `set "<reason>"` (writes `<lead>/PAUSE`), `clear`, `status` | lead (`/pause-project`, `/resume-project`) | the pause guard reads it |

### 3.3 Agent runtime configuration (the runtime's own files)

The agent renders BOA's runtime-neutral sources into its runtime's own files when it wires BOA (AGENTS.md §13, the
BOA package's `references/runtimes.md`: one profile per known runtime) and writes here where they live, so a later
session finds them; their names go in `BOA_RUNTIME_CONFIG` (the guard keeps shell writes off them).

| What | Where |
|---|---|
| the role contracts of `.boa/agents/` (§3.6) in the runtime's agent format | the runtime's agents directory (written at wiring) |
| the commands of `.boa/commands/` (§3.7) as the runtime's commands or skills | the runtime's commands directory (written at wiring) |
| BOA's hooks, the cleanup allowlist, the permissions and the options (the sub-agent prompt-cache TTL where the runtime has one; the main one only when the user agrees, OR-36) merged into the runtime's settings, keeping the project's own: **session-start**: `.boa/hooks/session_status.py` (injects the resume protocol and the status top); **post-tool of a sub-agent**: `.boa/hooks/agent_binding.py` (the agent→task binding); **subagent-stop**: `.boa/hooks/subagent_stop.py` (report capture and pause capture); **stop** of the lead: `.boa/hooks/lead_stop.py`; **pre-tool** of a shell, file-write or file-read call: the guard; **pre-tool** of every call: the pause guard; **post-tool of a file-write**: `.boa/hooks/memory_check.py`; **post-tool-failure**: `.boa/hooks/memory_recall.py`; **pre-compact**: `.context-gate/hooks/precompact.sh` (the inventory: `references/runtimes.md` "The hooks"; the cleanup allowlist and deny rules: §7) | the runtime's settings (written at wiring) |
| the context-gate skill (light profile where the runtime can extend the compaction prompt, L0-only otherwise): at every compaction a byte-exact, append-only snapshot of the raw transcript into `.context-gate/conversations/`, plus the extension of the native compaction prompt; its own `SKILL.md` documents it | the runtime's skills directory, where it has one |
| the runtime's instruction file, only for a runtime that does not read AGENTS.md natively: an import of or a pointer to AGENTS.md, never a rule | the runtime's instruction file |

Only the loggers' wiring ignores their failures (`|| true`: a logger never breaks the session); a GUARD's wiring
refuses the call on a deny verdict, a non-zero exit or a timeout (`|| exit 2`, never `|| true`: the guards fail
closed). The Python hooks run as `"{{BOA_PYTHON}}" -I` (quoted)
(the absolute interpreter the agent checked at install, so a missing or shadowed `python3` on `PATH` cannot turn a
guard off silently; `session_status.py` warns at session start when a guard cannot start). Each hook reads BOA's
neutral event on stdin and answers with the neutral verdict; the agent's wiring converts the runtime's payload and
the verdict (the BOA package's `references/hook-contract.md`).
Agent models (frontmatter `model` / `effort`, the AGENTS.md §6 roster, OR-27): builder, reviewer and analyzer
`{{BOA_MODEL_FRONTIER}}` / high; builder-mid, tester and integrator `{{BOA_MODEL_MID}}` / high. Rate-limit fallback
only after an actual stop (OR-33); trailers name the real model.
Agent descriptions in a sub-agent spawn must **start with the lane's task id** (`<T> build`, `<T> review r2`): the lane
journal binds the agent to it (09 §11).

### 3.4 Hooks (`.boa/hooks/`)

| Hook | What | Notes |
|---|---|---|
| `.boa/hooks/guard_destructive.py` | the role-aware **guard** (PreToolUse): deletions only on provably-own paths; sub-agent writes confined to their lane; no other lane, no other project (reads included for sub-agents), no `/dev` targets, the project's protected commands (its `protected-commands.conf` under .boa, written by the agent; the BOA package's `references/safety.md`), no pushes to main by sub-agents, no host damage; the lead's override `{{BOA_ENV_PREFIX}}GUARD_LEAD_VERIFIED=<token> ` (always logged). Non-blocking deny with a reason; fails closed (naming the override as the escape); logs every denial | 09 §11, §7 here |
| `.boa/hooks/hook_config.py` | the configuration the Python hooks share: reads `.boa/config.env` through the one reader `.boa/tools/boa_config.py` (never sources it; a line outside its grammar makes the guards refuse every call), rooted at the repository that holds the hook; the guards' path form on every OS | imported by the hooks |
| `.boa/hooks/agent_binding.py` | lane orchestration's agent-to-task binding: the hook on the lead's sub-agent spawn (the post-tool event of a `sub-agent` call) records agent id → the first task id of the spawn description in `<BOA_STATE_DIR>/agent-bindings.jsonl`; the guard and the pause guard read it to keep a bound sub-agent in its own lane; `--task-of <agent id>` prints the binding | a project clock may read or extend the file |
| `.boa/hooks/shell_lexer.py` | the shell lexer of the pause guard (quotes, substitutions, here-documents, segments with their operators) | imported by `pause_guard.py` |
| `.boa/hooks/pause_guard.py` | while `<lead>/PAUSE` exists a sub-agent may only: write its own `.lane-resume/<role>.md`; append (only) to its lane's `.lane-resume/memories.md`; run read-only git; `git add` / `git commit` in its own worktree; `rm` its own scratch subdir; `kill` its own PIDs (the cleanup needs the task: the agent binding, else the lane worktree's name); everything else is denied with the instruction to do exactly these and end its turn | 09 §13 |
| `.boa/hooks/session_status.py` | SessionStart: injects the resume protocol and the top of `lead-status.sh` into the context, a three-line memory-writing reminder, the current memories for every active task id (OR-51) (write memories only through `memory_write.py`, the most specific type, supersede — never edit), and warns when a guard hook cannot start (its interpreter `{{BOA_PYTHON}}` missing, a hook file missing or failing its self-check) | — |
| `.boa/hooks/subagent_stop.py` | SubagentStop: appends the agent's final report to its lane journal `<lead>/lanes/<T>.md` (through `lane_journal.py`; a report over 20 KiB is kept whole in `<lead>/lanes/<T>.full/` and the cut names it); queues the report's Leftovers items in `<lead>/open-items.md` and flags a task agent's report without a Leftovers section (through `report_capture.py`, labels from `.boa/markers.json`); under the pause flag also copies the agent's `.lane-resume/<role>.md` to `<lead>/lanes/<T>-<role>.md` and journals "paused" (warns when there is none) | 09 §13 |
| `.boa/hooks/memory_check.py` | PostToolUse on Write, Edit, MultiEdit: when the touched file is a memory file, lints it (as `memory_lint.py`, below the `<!-- boa:memory-cutoff -->` line if there is one) and flags broken ids or links | OR-50 |
| `.boa/hooks/memory_recall.py` | PostToolUseFailure (any tool): searches the memory for the failed call's error text and injects the matching gotcha/trap/lesson ids into the agent's context (OR-51); a sub-agent gets its task's memories through its brief (09 §4) | — |
| `.boa/hooks/lead_stop.py` | Stop (the lead): under the pause flag renders `<lead>/RESUME-LEAD.md` from the status screen | 09 §13 |
| `.context-gate/hooks/precompact.sh` | PreCompact: the context-gate snapshot and prompt extension | §3.3 |

### 3.5 Disk, residue, environment, remote runner

The disk measurement, the residue check, the capabilities record and the remote runners are the project's own
(project-wiring "measure commands", "deployed-instance objects", "capabilities record", "remote runners"); their rows
go here when the project has them.

| Tool | What, when, how | Who | Side effects / safety |
|---|---|---|---|
| `.boa/bin/render.py` | renders the templates with `.boa/config.env` | `/boa` install | — |
| `.boa/bin/boa` | **the one command-line entry point** `boa <subcommand>` (POSIX sh): checks git 2.31+ and Python 3.11+ first without Python (exit 3, which no tool uses = something missing, nothing done: the agent tells the user how to install it on this OS and installs it only with their yes), then runs `.boa/tools/boa.py`; `boa help` lists the subcommands | everyone | none of its own |
| `.boa/bin/boa.cmd` | the same entry point on Windows (`cmd`), same checks and exit codes | everyone on Windows | none of its own |
| `.boa/tools/boa.py` | the dispatcher behind the launchers: `install`, `uninstall` built in; `boa memory write` → `tools/memory_write.py`, `boa status` → `lead-status.sh`, `boa lane …` → `lane-worktree.sh`, any other tool by its name | through `boa` | as the tool it runs |
| `.boa/tools/boa_install.py` | `boa install` / `boa uninstall`: installs BOA's files into the project (under `.boa/`, the project documents, marked blocks in existing files, `.gitattributes` LF pin, git excludes) and removes exactly what it installed; seeds the memory id ledger of a bank that has none (so the memory lint passes at once); with no `.boa/config.env` it writes the commented template there and stops (the agent fills it in); one install at a time; writes no runtime setting: the agent wires the runtime | `/boa`; `boa uninstall` at removal | never overwrites the project's own files |
| `.boa/tools/boa_paths.py` | the installer's library: the interpreter check, the names BOA owns under `.boa/` (case-insensitive), physical paths and the worktrees-dir rule (POSIX and Windows paths) | the tools | — |

### 3.6 Role contracts (`.boa/agents/`, every runtime)

The source of truth of each role, installed in every runtime (the runtime's own agent files are rendered from them,
§3.3; a change re-renders them in the same commit).

| Path | What |
|---|---|
| `.boa/agents/analyzer.md` | read-only deep analysis, fanned out by area |
| `.boa/agents/builder.md` | implements one task on its lane; delta fixes on bounces (delicate or non-trivial work) |
| `.boa/agents/builder-mid.md` | the same builder contract on the model below the frontier, for simple low-risk work only (OR-34); hands back if the work turns out delicate |
| `.boa/agents/reviewer.md` | adversarial review of code changes; delta re-reviews; read-only |
| `.boa/agents/tester.md` | acceptance map, touched suites, static analysis, the lane's only targeted mutation run (or planted faults) |
| `.boa/agents/integrator.md` | merge trains: rebase, `docs(memory)`, one gate, merge, residue, cleanup, durations |
| `.boa/agents/sub-lead.md` | runs one delegated stream of tasks for the lead (own lanes, reports to the lead; never merges, never creates tasks; lead-only powers stay with the lead, OR-61, 09 §28) |

### 3.7 Commands and settings (`.boa/commands/`, every runtime)

The sources of truth, installed in every runtime; the agent wires them: the commands rendered as the runtime's
commands or skills, and BOA's hooks and cleanup allowlist (the inventory in the BOA package's
`references/runtimes.md`) **merged** into the runtime's settings, keeping the project's own keys, hooks and
permissions (§3.3). A runtime without commands runs a command by following its file (AGENTS.md §13).

| Path | What |
|---|---|
| `.boa/commands/run-project.md` | `/run-project`: mode bootstrap, then the autonomous loop |
| `.boa/commands/pause-project.md` | `/pause-project`: the pause flag, every agent leaves a resume file, state flushed |
| `.boa/commands/resume-project.md` | `/resume-project`: clear the flag, restart daemons, per-lane resume plan |
| `.boa/commands/close-project.md` | `/close-project`: the close-out questionnaire, secret scan of tree and history, residue, open items, final report |
| `.boa/commands/run-task.md` | optional manual shortcut: one task through the pipeline |
| `.boa/commands/sync-memory.md` | optional manual shortcut: flush state into the memory bank |

### 3.8 Tool cards

One card per BOA tool, library or group of files that work together; every file under `.boa/bin/`, `.boa/hooks/`
and `.boa/tools/` is named on one card's "Files" line (the drift check refuses a file without one, §9). A tool the
project adds there gets its card in the same commit. "Wire" says what connects the tool to the agent's runtime
(the neutral events: the BOA package's `references/hook-contract.md`); "nothing" means it is run by hand or by
another tool.

#### Tool card: boa command
- Files: `.boa/bin/boa`, `.boa/bin/boa.cmd`, `.boa/tools/boa.py`
- Purpose: the one command-line entry point; checks git and Python first, then dispatches to the tools.
- When: whenever a BOA command is run (`boa help`, `boa status`, `boa lane …`, `boa memory …`, `boa install`).
- Wire: nothing (on `PATH` or called by its path).
- Verify: `boa help` lists the subcommands and exits 0.
- Limits: exit 3 means a prerequisite is missing and nothing was done.

#### Tool card: install and render
- Files: `.boa/tools/boa_install.py`, `.boa/tools/boa_paths.py`, `.boa/bin/render.py`
- Purpose: install, re-install and uninstall BOA's files; render the templates with `.boa/config.env`.
- When: at bootstrap, after a new BOA package, and at removal (`boa uninstall`).
- Wire: nothing (writes no runtime setting: the agent wires the runtime itself).
- Verify: `boa help` runs from the installed `.boa/`; `boa uninstall` removes exactly what the install recorded.
- Limits: one install at a time; refuses a config line outside the grammar or an empty required key.

#### Tool card: lead status
- Files: `.boa/bin/lead-status.sh`, `.boa/tools/lead_status.py`
- Purpose: everything on one screen: lanes, admission, warnings, resume files, pause flag, HITL, guard state.
- When: at session start (the session-start hook shows its top), before filling lanes, after every train.
- Wire: nothing (the session-start hook runs it).
- Verify: `boa status --guards` prints no GUARD DOWN line.
- Limits: reads only (its bookmark file excepted).

#### Tool card: lane worktrees
- Files: `.boa/bin/lane-worktree.sh`, `.boa/tools/lane_worktree.py`
- Purpose: lean lane worktrees from current main; removal refuses unpushed or uncommitted work.
- When: the lead at lane start (`add`), the integrator after the merge (`remove`).
- Wire: nothing.
- Verify: `boa lane add <T> <branch>` creates `<wt>`; `remove` on a clean, pushed lane deletes it.
- Limits: never edit a hard-linked dependency file in place.

#### Tool card: lane journal and report capture
- Files: `.boa/bin/lane-journal.sh`, `.boa/tools/lane_journal.py`, `.boa/tools/report_capture.py`, `.boa/hooks/subagent_stop.py`
- Purpose: every sub-agent's final report appended to `<lead>/lanes/<T>.md`; its Leftovers items into `<lead>/open-items.md` (a task agent's report without a Leftovers section flagged); the pause capture under the flag.
- When: at every sub-agent stop.
- Wire: the runtime's sub-agent stop, as the neutral `subagent-stop` event.
- Verify: after a sub-agent ends, its report is the newest entry of its lane's journal.
- Limits: the report is capped (with a marker); a logger: its failures never stop the session.

#### Tool card: language and markers
- Files: `.boa/tools/markers.py`
- Purpose: the product-language change: the machine-recognised words (report sections, the Leftovers section and its "none", review classes, the fold marker, plan columns) live in `.boa/markers.json`; `boa language set <lang> --texts FILE` switches only when every hook passes on samples in the new language.
- When: the user changes the product language (lead procedure: `boa language set` first); `show` and `check` at bootstrap and when a marker is in doubt.
- Wire: nothing (a command; the hooks and tools read the markers file).
- Verify: `boa language check` exits 0 and `boa language show` names the current language.
- Limits: the memory block syntax is never a marker and never translated; a refused `set` changes nothing; the agent copies the regenerated agents and commands into its runtime again.

#### Tool card: pause
- Files: `.boa/bin/pause-flag.sh`, `.boa/tools/pause_flag.py`, `.boa/hooks/pause_guard.py`, `.boa/hooks/shell_lexer.py`, `.boa/hooks/lead_stop.py`
- Purpose: the pause flag, the guard that lets a paused sub-agent only save its state, and the lead's resume file.
- When: `/pause-project` and `/resume-project`; the guard judges every call.
- Wire: the pause guard on the runtime's pre-tool event for every tool (it must be able to deny); the lead's stop as `stop`.
- Verify: with the flag set, a sub-agent's ordinary command is denied and its resume-file write allowed.
- Limits: a guard fails closed: a broken or slow guard refuses the call.

#### Tool card: guard
- Files: `.boa/hooks/guard_destructive.py`, `.boa/hooks/hook_config.py`, `.boa/hooks/agent_binding.py`
- Purpose: the role-aware safety net (deletions, writes, other lanes and projects, protected commands, pushes) and the agent-to-task binding it confines sub-agents with.
- When: every shell, file-write and file-read call; the binding at every sub-agent spawn.
- Wire: the runtime's pre-tool event for shell, file-write and file-read calls (it must be able to deny); the spawn's post-tool event of a `sub-agent` for the binding.
- Verify: `boa status --guards` shows no GUARD DOWN line; `python3 -I .boa/hooks/hook_config.py` prints the derived paths.
- Limits: a safety net against accidents, not a sandbox; fails closed (the lead's logged escape is the way out).

#### Tool card: session status
- Files: `.boa/hooks/session_status.py`
- Purpose: the resume protocol, the top of the status screen and the memory reminder at session start.
- When: every session start.
- Wire: the runtime's session start, as `session-start`.
- Verify: a new session shows the resume protocol in its first context.
- Limits: a logger: it never blocks the session.

#### Tool card: memory
- Files: `.boa/tools/memory_write.py`, `.boa/tools/memory_lint.py`, `.boa/tools/memory_search.py`, `.boa/tools/memory_types.py`, `.boa/tools/memory_embed.py`, `.boa/hooks/memory_check.py`, `.boa/hooks/memory_recall.py`
- Purpose: write, validate and search the memory; lint after a write; recall lessons on an error.
- When: writing a lesson (`memory_write.py`), at every train (lint), when recalling (search), on a failed call (recall).
- Wire: the lint hook on the post-tool event of a `file-write`; the recall hook on `post-tool-failure`.
- Verify: `python3 -I .boa/tools/memory_lint.py` reports 0 findings; a search finds a memory just written.
- Limits: ids only through `memory_write.py --ingest`; a search beyond `--limit` says how many it left out.

#### Tool card: plan lanes
- Files: `.boa/tools/plan_lanes.py`
- Purpose: checks the plan and computes waves, hotspots, the critical path and progress.
- When: after every plan edit (`--check`), before filling lanes.
- Wire: nothing.
- Verify: `python3 -I .boa/tools/plan_lanes.py --check` exits 0.
- Limits: reads only.

#### Tool card: traceability
- Files: `.boa/tools/trace_check.py`
- Purpose: the one traceability check (tasks, contracts, specs, features, tests, registers, folds).
- When: per task (its rows), every train, at close-out (`--close`, must be 0).
- Wire: nothing (the project gate runs it).
- Verify: `MISMATCHES: 0` at close-out.
- Limits: reads only; exit 1 on any mismatch.

#### Tool card: metalearning
- Files: `.boa/tools/metalearning.py`
- Purpose: `append` turns the lead's own notes and traces (`--task lead`) into id-less drafts in the inbox (the
  sub-agents' traces reach 10 through their lanes' memories at the fold, never as copies in the inbox); `curate`
  lists the lessons of 10 and the inbox seen more than once.
- When: the lead at each train.
- Wire: nothing.
- Verify: `python3 -I .boa/tools/metalearning.py curate` ends with a `METALEARNING:` line.
- Limits: a lesson over 600 characters is cut with a marker naming the lane journal entry.

#### Tool card: handbook drift
- Files: `.boa/tools/handbook_drift.py`
- Purpose: checks that this file maps every tool, path and card (§9).
- When: every change to a tool, path or procedure; the project gate.
- Wire: nothing (the project gate runs it).
- Verify: `SUMMARY: 0 drift finding(s)`.
- Limits: knows no agent runtime: the runtime's own files are checked by the project.

#### Tool card: shared libraries
- Files: `.boa/tools/boa_config.py`, `.boa/tools/boa_lock.py`, `.boa/tools/boa_tool.py`, `.boa/tools/hook_contract.py`
- Purpose: the one config reader, file locks, the tools' shared start-up and the neutral hook contract.
- When: imported by the tools and hooks, never run on their own.
- Wire: nothing.
- Verify: the tools that import them run (`boa help`, `boa status`).
- Limits: a config line outside the grammar is refused, naming the line.

## 4. Test suites

### 4.1 The project's suites
<!-- The lead fills the stack's test layout here at bootstrap. -->
Shell suites (where the project has them) are plain bash, offline unless stated, clean up their own temp dirs.
Header markers: the ones the project gate reads (how it selects, serialises or tiers a suite) are defined by that
gate (project-wiring "the project gate") and listed here at bootstrap; `@covers-feature F-ID <T>` (parity, §5.11)
and `@covers-contract` are read by `trace_check.py`. Where the gate runs suites in parallel it starts the longest
first (from its timing records), so a step's wall time is about its critical-path suite.

### 4.2 Stack test tooling and mutation (OR-29, OR-30; 09 §24)
- Targeted tests: `.boa/stack/test-runner.sh <test files>` (explicit files only).
- Static analysis and lint: the project gate's static steps (project-wiring "the project gate").
- **Mutation:** only the stack's mutation wrapper; only delicate code the task changed; only the covering tests; a cap
  per batch (the wrapper splits into batches by itself; a single file over the cap = "scope too wide": narrow the
  covering tests, then report to the lead, who alone raises a cap for one run with a written reason) and a total
  bound per call; host-aware slots (about 2 runs on a shared development host, a quarter of the CPUs on a runner;
a wait-and-retry option); 0 skipped mutants; a control run rejects false kills (a kill counts only if the test is green
  without the mutation); thresholds per risk class from 06; receipts per file pinning what decides its verdict, reused
  by the train (the wrapper's receipt reuse), never deleted before a run ends. An equivalent-mutant ignore needs a proof and the lead's
approval. The tester's runs are the lane's only ones (one per tester round, at most 3 per lane across bounces). Full scope only
  at milestone closure (the milestone mode, on the runner when configured). Where no mutation tool fits: planted
  faults.

## 5. Workflows

### 5.0 Filling lanes (lead; 09 §3)
`python3 -I .boa/tools/plan_lanes.py` → wave 1, hotspots serialised, product first → admission from
`lead-status.sh` → `.boa/bin/lane-worktree.sh add <T> <branch>` → a registry line → the builder tier (OR-34) and a
full brief (09 §4); the Agent description starts with the task id.

### 5.1 The per-lane pipeline (AGENTS.md §6, 09 §5)
Builder (own tests, static steps on changed paths; no mutation) → reviewer (adversarial; `[SEV] [BLOCKING|NON-BLOCKING] file:line — failure
— fix`; delicate lines for the tester) → builder delta ⇄ reviewer delta until the review exit rule (OR-52) → tester (acceptance map,
touched suites, the lane's only mutation runs: one per tester round, at most 3 per lane across bounces) → integrator. Docs-only: no review (OR-01).
**Sub-agent lifecycle (OR-16, 09 §5.3):** every spawn is recorded by the project's clock (project-wiring "usage clock and throughput": task | role |
agent id | model | started | state; the one home of agent ids); the same task and role → resume the same agent by id
for every later round (how the runtime resumes an agent: its profile in `references/runtimes.md`, verified at
install); new task or new work → a new agent; train integrators resumed
for the same train, new for a new one; a lost agent → a new one briefed from `.lane-resume/<role>.md`.

### 5.2 Loop guard (09 §6, OR-06)
3 failed builder attempts on the same finding → stop the lane, ask the owner; recommended: one final targeted attempt.

### 5.3 Merge trains (09 §7, OR-04, OR-31)
3–4 green lanes → rebase and stack on current main → ONE `docs(memory)` commit on top of the stack (it lands with
the last lane's merge) (+
the folds, the memory ingest, the handbook) →
PRs → one pre-merge run of the project's gate (receipts reused) on the stack tip (on the runner when configured) → timing check with
per-step verdicts → merge in order pinned to the gated head → the deployment steps on main where the stack has them →
residue per lane = 0, worktree and branches removed → report (durations, correspondence, unblocked tasks). Hold rule:
3 green or the oldest waited 60 min; a critical-path lane or red-main fix alone or at the bottom of the next train.
Refresh a lane's dependencies after a lockfile change before gating. Red gate → bisect, bounce only the breaking
lane, re-stack, re-gate; a failure main itself causes is a red-main fix task. Builders grep main for callers of every
signature they change (combination effects).

### 5.4 Running stack tools in a lane
Only the targeted forms (§4.2) locally; anything heavy through the project's runner command (project-wiring "remote runners") when a
runner is configured.
Throwaway containers `--rm --name {{BOA_NAME_PREFIX}}<T>-<what> --label {{BOA_LABEL_KEY}}=<T>`.

### 5.5 Lane worktrees
`lane-worktree.sh add` (lead), `remove` (integrator, after the merge), `git worktree prune`; never orphans.

### 5.6 Clock (09 §22)
The project's clock (project-wiring "usage clock and throughput"): start, `<step>-start|-end` around long steps, stop and an
elapsed line in every report; its report feeds size estimates and the throughput review.

### 5.7 Residue and zero residue (OR-09)
The project's residue check (project-wiring "deployed-instance objects") per lane, in closing mode at milestone, in final
mode at close-out; kept items only via the register in 04.

### 5.8 Disk watch and durations (OR-08, OR-20; 09 §10, §15)
Disk (project-wiring "measure commands"): started at start/resume, stopped at pause, snapshot and alert read around heavy steps and at every train.
Durations (project-wiring "suite timings and duration control"): the timing check at every train and milestone (total, per step, critical-path suite, dominance);
the lead opens a speed-up task at once for an over-budget, trending or dominated step; throughput proposals;
speed never trades coverage.

### 5.9 Freshness (OR-46, 09 §19)
At milestone closure and release: zero outdated pins except documented holds.

### 5.10 Clean-room and provenance (optional, 09 §21)
Only when the clean-room rule is adopted: `docs/clean-room.md`, the Provenance line everywhere, the contamination
check in review and gate.

### 5.11 Parity registration (09 §20)
Every task in `docs/parity/features.toml` (feature or categorised not-feature); before DONE a running test carries
`@covers-feature F-ID <T>`; `trace_check.py`.

### 5.12 Deployment operations (lead only, 09 §12)
<!-- The lead writes the project's own deployment procedure here (backup → deploy → restart only what changed →
     health check with an expected answer → registry line). Lanes never touch the deployment. -->

### 5.13 Pause and resume (09 §13)
`/pause-project` → `pause-flag.sh set` → the pause guard leaves every sub-agent only the pause set (its resume file,
read-only git, add/commit in its worktree, rm of its scratch subdir, kill of its own PIDs; any other resource of the
lane is named in its resume file and removed by the lead; 09 §13); the integrator stops BEFORE starting the next merge; a merge command already running
completes; it never leaves a half-merged train unreported (its resume file states the stack state: which lanes
merged and at which SHAs, which are stacked and gated, which are not) → `subagent_stop.py` copies the resume files
to `<lead>/lanes/` → `lead_stop.py` renders
`RESUME-LEAD.md`. `/resume-project` → `pause-flag.sh clear`, daemons, status, per-lane plan.

### 5.14 Close-out (09 §14)
Milestone: full-scope mutation round, every tier, the residue check (closing), the secret scan of the tree, freshness,
duration review, tag. Project: `/close-project`, in this order: questionnaire → the chosen closing steps (through the
pipeline) → THEN the checks (the secret scan of tree and history, project-wiring "secret scanning", parity 100 %, open items and folds 0,
`trace_check.py --close` = 0, the residue check (final) = 0) → uninstall LAST if chosen (the checks ran before it) →
final report.

### 5.15 Heavy runs on the remote test runner (09 §18, OR-32; `BOA_RUNNER={{BOA_RUNNER}}`)
With a runner, every heavy run is the project's runner command (project-wiring "remote runners"); the local guards do not see inside the
runner session (the runner's own allowlist does); agents never edit the runner config, never change the runner's
provisioning outside its planned task, never open a session to it by hand; its address lives only in its config. Without a runner, heavy runs stay local, serial or parallel as the project's test-execution decision
records (project-wiring "light and heavy suites"; record it here: where, serial or parallel, how many at once).

### 5.16 Contracts (OR-48, 09 §25)
Contracts first: `docs/api/` and `docs/specs/`, indexed in 02 with version, consumers and contract tests;
spec-side tasks before build tasks; a missing or ambiguous contract is a spec question; a contract change is an ADR
with its compatibility impact, then a spec-side task, then the build. Contract tests (lint, contract/golden, schema,
compatibility) run in the gate.

### 5.17 Correspondence (OR-49, 09 §26)
Keep the markers current in every task (03 `Contract / spec` column, 02 contracts index, `@covers-contract` /
`@covers-feature` headers, the register, the ledgers); `trace_check.py` at every train (integrator report) and at
close-out (0 mismatches or not done).

### 5.18 Memory recall (OR-51, 09 §27)
Search before acting (`memory_search.py`) at task start/resume, on any error, before decisions and contract changes,
when reviewing/testing, planning and closing (AGENTS.md §14); follow or supersede; cite `Memories used:` in every
report; write the memory when you solved something non-obvious. `memory_recall.py` injects matching ids after a
failed tool call; a sub-agent gets its task's memories through its brief (mandatory).

## 6. Lead-local state (`<lead>/`)

`<lead>/` is machine-local (git-excluded), never committed. Agents may **read** it; only the lead writes it (the guard
refuses sub-agent writes). Durable rules never live there.

| File | Purpose |
|---|---|
| `README.md` | what lives in the lead dir |
| `lanes.md` | the registry: append-only, one UTC line per stage change; newest per lane wins; train lines; override evidence |
| `lanes/<T>.md` | the lane journal (SubagentStop hook); never edited by hand |
| `lanes/<T>-<role>.md` | resume or closure copies of `.lane-resume/<role>.md` |
| `brief-common.md` | the rules pasted into every brief (generic + project lessons) |
| `open-items.md` | the transit queue (OR-25): `- [ ]` lines with their date and owner (the stop hook's Leftovers, the lead's and owner's notes), placed in the plan — the only source of work — by the next fold; empty at close-out |
| `lanes/<T>.full/` | the whole text of a report over the journal's 20 KiB cap, one file per report (named by the cut marker); removed with the lane |
| `owner-rules-pending.md` | owner rules said in chat, folded into 08 at the next train |
| `plan-additions-pending.md` | plan rows and notes, folded into 03 at the next train (fold marker lines) |
| `metalearning-inbox.md` | the lead's own notes and curations (never copies of lane lessons), folded into 10 at each train |
| `PAUSE` | the pause flag (only during a pause) |
| `RESUME-LEAD.md` | written at a pause: what to do first on resume |
| `lead-status.seen` | the status screen's bookmark |

**If `<lead>/` is absent** (a fresh clone elsewhere): there is no live lane state; rely on the memory bank, `git
worktree list` and the forge's open PRs, and start lanes fresh.

## 7. Safety and hard rules

Authoritative: AGENTS.md §4, §9, [08-OWNER-RULES.md](../memory-bank/08-OWNER-RULES.md),
[09-OPERATING-PROCEDURES.md](../memory-bank/09-OPERATING-PROCEDURES.md) §4, §11, §17.

- **Other projects, the deployment, the host:** never touch other projects (sub-agents never even name their paths),
  the project's deployed instance (lead only), `/dev`, `/etc`, services or package managers (OR-10).
- **Destructive commands** only on provably-ours paths, literal absolute paths, one `rm` per command, no `cd && rm`,
  only the allowlisted shapes of the runtime's settings (OR-11). Never "test" a destructive command on the host:
  JSON payloads or a throwaway container (OR-24).
- **Containers** (when the project uses a container engine): removed on exit, name `{{BOA_NAME_PREFIX}}<T>-<what>`,
  label `{{BOA_LABEL_KEY}}=<T>`; never the deployment's own project or labels.
- **Never write at `/`** or outside your worktree and your scratch subdir; the mktemp check and `set -u` (09 §17).
- **No synthetic CPU load** (OR-05). **No permission prompts:** the runtime's file-editing tools, scripts in your scratch, no compound
  `cd <main> && …`.
- **Secrets:** never printed, never on argv, never committed (OR-41).
- **Third-party contracts never break** (OR-13); **built-in → extend → from scratch** (OR-07); **latest stable
  stack** (OR-46).
- **Git:** branch `{{BOA_BRANCH_GRAMMAR}}`; conventional commits with the session's trailers (OR-42); one PR per task;
  never commit or push to `{{BOA_MAIN_BRANCH}}` (OR-38); sub-agents never push; merges only pinned to the gated head;
  never let the forge delete a branch whose worktree holds live state (OR-18).
- **Heavy runs** on the runner when one is configured; unreachable = stop and report (OR-32).
- **The guard** (OR-37…OR-40): sub-agents bound to the lane of the first task id of their description; the lead's
  override only as `{{BOA_ENV_PREFIX}}GUARD_LEAD_VERIFIED=<single_token> ` at the start of a command, after proving
  the target is ours, evidence in `<lead>/lanes.md`; never for sub-agents. **Known limits** (it is a net, not a
  sandbox; fails closed): 09 §11.
- Lanes never edit `memory-bank/active-context.md`; ADR and EDR numbers come from the lead; the guard may refuse a
  command:
  adapt, never work around it.

## 8. Talking to the owner

- Replies in {{BOA_REPLY_LANGUAGE}}, plain and short (code and docs stay {{BOA_DOC_LANGUAGE}}; 09 §9).
- A status question = first line DONE on main / total tasks (%), work-weighted %, how many tested and waiting to merge
  (OR-15; `plan_lanes.py`).
- HITL only for owner decisions, with 2–4 self-contained options, the recommended one first, "(Recommended)" (OR-12).
  Technical forks are the lead's (ADR). Sub-agents escalate to the lead, never to the owner.

## 9. Keep this file current

- **OR-26:** any change that adds, changes, renames or removes a script, tool, suite, agent, hook, command, path or
  procedure updates this file **in the same commit**; otherwise the task is not done.
- **Drift check** `python3 -I .boa/tools/handbook_drift.py` fails when:
  - a file under `.boa/bin/`, `.boa/hooks/`, `.boa/tools/`, `.boa/stack/`, `.boa/agents/` or `.boa/commands/` is not
    named here by its path, or this file names a `.boa/` path that does not exist;
  - a file under `.boa/bin/`, `.boa/hooks/` or `.boa/tools/` is named on no tool card's "Files" line, or a card
    lacks one of its fields (§3.8);
  - the stack block (`<!-- boa:stack-rows:begin -->` … `end`) is missing or differs from
    `.boa/stack/handbook-rows.md`;
  - [AGENTS.md](../AGENTS.md) does not link this file; `memory-bank/RESUME.md` does not point to `AGENTS.md`; a role
    contract lacks its "Agent handbook" section or the section never names `docs/agent-handbook.md`;
  - a relative link in `AGENTS.md` or this file is broken.
  It knows no agent runtime: the runtime's own files (its renderings of the agents and commands, its settings, its
  instruction file) are kept in step with their `.boa/` sources by the agent that wired them, and checked by the
  project (the BOA package's `references/runtimes.md`).
- **Names:** a path counts as named when it appears whole (letters, digits and `_ . / -`), bounded by any other
  character. Project-specific tools the lead adds (under `scripts/` or elsewhere) get their own rows in §2.3 or §3.
- **Who updates what** (each agent's contract, section "Agent handbook (OR-26)"):
  - builder: updates this file in the same commit as the tool, path or procedure change;
  - reviewer: a code change touching any of those without a matching update is a finding (major, blocks);
  - tester: runs the drift check whenever the change touches `.boa/`, the runtime's wiring, the suites or the docs it pins;
  - integrator: the gate includes the drift check; refuses undocumented tool changes; updates this file in the
    train's `docs(memory)` commit when a fold changes a procedure or tool;
  - analyzer: reports any tool or path its findings reveal that this file lacks;
  - lead: keeps §6 and §5.12 current; reviews the whole file at each milestone closure.
- **The map stays whole:** a file without an entry in §2, or an entry without its file, is a finding of the reviewer
  and of the milestone review; the lead's review of this file also walks the map against the repository.
