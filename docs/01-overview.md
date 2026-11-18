# 01 Overview

## What BOA is

BOA (Build On Autopilot) is one skill, `build-on-autopilot`, that teaches an AI agent how to run a project end to
end: start it, work it, pause it, resume it and close it, with the whole working discipline (plan, lanes, review,
test, merge trains, memory, measuring, safety). The agent that runs the skill becomes the **lead**: it designs,
plans and measures; specialised sub-agents (analyzer, builder, builder-mid, reviewer, tester, integrator) execute.

BOA ships that discipline plus the few generic tools the discipline needs. It is not a tangle of adapters: the
project-specific part of the discipline (stack, gate, CI, runners, services, protections, models, scripts) is done
**by the agent, in the project, under the discipline itself**. When in doubt, BOA teaches; it does not code.

BOA is project-agnostic and harness-agnostic: no project, person, host, stack or agent runtime is built in. Runtime
facts live only in the runtime profiles of [references/runtimes.md](../references/runtimes.md), which the agent
reads to wire BOA into the runtime it runs in.

## What ships as code

The shipped code is exactly this list; each tool has a card in the installed handbook
([tool cards](../assets/templates/agent-handbook.md#38-tool-cards)):

| Tool | Files (installed under `.boa/`) | Card |
|---|---|---|
| the `boa` entry point | `bin/boa`, `bin/boa.cmd`, `tools/boa.py` | [boa command](../assets/templates/agent-handbook.md#tool-card-boa-command) |
| the installer (`boa install`, `boa uninstall`, render) | `tools/boa_install.py`, `tools/boa_paths.py`, `bin/render.py` | [install and render](../assets/templates/agent-handbook.md#tool-card-install-and-render) |
| the destructive-command guard, with the project's protected-command rules (the agent writes the rules) | `hooks/guard_destructive.py`, `hooks/hook_config.py` | [guard](../assets/templates/agent-handbook.md#tool-card-guard) |
| the agent-to-task binding (confines a sub-agent to its own lane) | `hooks/agent_binding.py` | [guard](../assets/templates/agent-handbook.md#tool-card-guard) |
| the pause (flag, pause guard, the lead's resume file) | `bin/pause-flag.sh`, `tools/pause_flag.py`, `hooks/pause_guard.py`, `hooks/shell_lexer.py`, `hooks/lead_stop.py` | [pause](../assets/templates/agent-handbook.md#tool-card-pause) |
| the memory system (write, lint, search, types, embeddings, the lint and recall hooks) | `tools/memory_*.py`, `memory-types.json`, `embed.json`, `hooks/memory_check.py`, `hooks/memory_recall.py` | [memory](../assets/templates/agent-handbook.md#tool-card-memory) |
| lane orchestration: the status screen | `bin/lead-status.sh`, `tools/lead_status.py` | [lead status](../assets/templates/agent-handbook.md#tool-card-lead-status) |
| lane orchestration: lane worktrees | `bin/lane-worktree.sh`, `tools/lane_worktree.py` | [lane worktrees](../assets/templates/agent-handbook.md#tool-card-lane-worktrees) |
| lane orchestration: the lane journal and the report capture (sub-agent stop hook) | `bin/lane-journal.sh`, `tools/lane_journal.py`, `tools/report_capture.py`, `hooks/subagent_stop.py` | [lane journal and report capture](../assets/templates/agent-handbook.md#tool-card-lane-journal-and-report-capture) |
| lane orchestration: the session status hook | `hooks/session_status.py` | [session status](../assets/templates/agent-handbook.md#tool-card-session-status) |
| the plan check (waves, hotspots, critical path) | `tools/plan_lanes.py` | [plan lanes](../assets/templates/agent-handbook.md#tool-card-plan-lanes) |
| the traceability check | `tools/trace_check.py` | [traceability](../assets/templates/agent-handbook.md#tool-card-traceability) |
| the handbook drift check | `tools/handbook_drift.py` | [handbook drift](../assets/templates/agent-handbook.md#tool-card-handbook-drift) |
| metalearning | `tools/metalearning.py` | [metalearning](../assets/templates/agent-handbook.md#tool-card-metalearning) |
| the language change (`boa language set`, `markers.json`) | `tools/markers.py`, `markers.json` | [language and markers](../assets/templates/agent-handbook.md#tool-card-language-and-markers) |
| the shared libraries (config reader, locks, start-up, the neutral hook contract) | `tools/boa_config.py`, `tools/boa_lock.py`, `tools/boa_tool.py`, `tools/hook_contract.py` | [shared libraries](../assets/templates/agent-handbook.md#tool-card-shared-libraries) |
| the context-gate (a standalone skill the agent wires) | `context-gate/` of the package | [the context-gate](02-install-and-wiring.md#the-context-gate) |
| the generic stack plug-in TEMPLATE (no bundled plug-in) | `stacks/generic/`, installed as `.boa/stack/` | [writing a stack plug-in](11-modes.md#writing-a-stack-plug-in) |

Plus the templates of the discipline: `AGENTS.md` (every rule), the agent handbook, the memory bank, the agent
contracts, the commands, the lead's files, the forge's PR/MR template, the parity file and the residue register.

## What BOA teaches as discipline

Everything not on that list is discipline: an item of the **project-wiring checklist**
([references/project-wiring.md](../references/project-wiring.md)) that the agent turns into a plan task at bootstrap
and builds, reviewed and tested, with the project's own library or tool. The items: the config, the capabilities
record, light and heavy suites, the project protections, the git hooks, secret scanning, the project gate (and its
self-test), the remote runners, the usage clock and throughput, the measure commands (disk), the deployed-instance
objects (residue), the suite timings and duration control, the licence and dependency audit, the optional clean-room
check, the permission log, the runtime wiring, the model roster, the stack plug-in and, with your consent, CI. Each is described in
[02 Install and wiring](02-install-and-wiring.md#the-project-wiring-checklist).

## The three modes

| Mode | You give | The bootstrap |
|---|---|---|
| `greenfield` | the idea: what to build (a file, or the conversation) | IDEA, then blueprint, specifications, contracts and the plan |
| `brownfield` | an existing repository | analyzers read every line and reconstruct the architecture, the contracts the code honours and goldens |
| `refactor` | an existing repository and the idea: the target (a file, or the conversation) | brownfield first; goldens pin today's behaviour; the target becomes contract changes recorded as decisions |

Details: [11 Modes](11-modes.md).

## The commands

- `/build-on-autopilot <mode> [idea-file]`: install BOA into the project and hand over to `run-project`.
- `run-project`: the mode's bootstrap on the first run, then the autonomous loop (lanes, pipeline, merge trains)
  until the project is complete or a decision only you can take blocks everything.
- `pause-project`: a stop signal for the lead and every sub-agent; each leaves a resume file.
- `resume-project`: resumes from the persisted state and reports.
- `close-project`: asks how the project ends, runs every closing check and step, reports.
- Optional shortcuts: `run-task` (one task through the pipeline) and `sync-memory` (flush state into the memory bank).

The commands ship as runtime-neutral files under `.boa/commands/`; the agent converts them into its runtime's
command format. The flow of each: [03 The workflow](03-the-workflow.md) and
[10 Pause, resume, close](10-pause-resume-close.md).

## What changes in your repository

The installer writes under `.boa/` (git-ignored, except what the agent writes or adapts for the project:
`.boa/config.env`, `.boa/protected-commands.conf`, `.boa/memory-types.json`, `.boa/markers.json`, the stack plug-in
`.boa/stack/`) and,
outside it: `AGENTS.md` (a marked block in an existing one; with `BOA_AGENTS_BLOCK=pointer` only a short pointer to
`docs/boa-rules.md`, which then holds BOA's rules), `memory-bank/`, `docs/agent-handbook.md`, `docs/boa-notice.md` (the
attribution of BOA's files and their licences), `docs/parity/`, the lead directory
(git-excluded), the forge's PR/MR template, and marked blocks in `.gitignore`, `.gitattributes`, `.git/info/exclude`
and an existing `memory-bank/04-ARCHITECTURE.md`. It never overwrites a file of yours. The full list:
[02 Install and wiring](02-install-and-wiring.md#what-the-installer-writes).

BOA is a tool, never the project: its files, tests, logs and tasks are never mixed with the project's and nothing of
it goes into the product or its releases.

## Assess, decide, ask

Before anything else the agent assesses what its runtime really gives it (hooks and their events, sub-agents,
background tasks, worktrees, a model per sub-agent, permission modes, network), by checking, never from memory. It
then decides how it implements each part of the discipline with those capabilities, declaring every substitute and
every part it cannot provide, and records the result as a capabilities record and decision entries. Whatever it
cannot know or decide it asks you: one question at a time, with options and its recommendation first. It never
guesses an unknown: it stops that item, asks, and keeps working on the rest. The capabilities are re-checked when
the runtime or the machine changes.

Owner decisions (product and business trade-offs, legal and licensing, money, anything destructive or irreversible
outside the repository, a genuine fork with no objective winner) always go to you; everything technical the agent
decides by the standards and records. See [03 The workflow](03-the-workflow.md#asking-the-user-hitl).

## Product language and user language

The product language (code, comments, docs, commits) is English by default; the user language (the conversation
with you, the content of memories, the free text of reports and plans) is the one you speak. The memory syntax is
always English. Changing the product language later goes through `boa language set` first
([07 Memory and state](07-memory-and-state.md#the-language-change)).

## Never reinvent the wheel

For every project-specific part the agent uses the built-in feature first, then extends it, then adopts an existing
library or tool whose upkeep is cheap against the benefit; it writes from scratch only for a proven gap, and says so.
