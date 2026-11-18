# BOA - Build On Autopilot

<p align="center"><img src="docs/assets/logo.png" alt="BOA - Build on autopilot" width="664"></p>

*Constrict your code to be right.*

[![Licence: AGPL-3.0 + MIT + CC BY 4.0](https://img.shields.io/badge/licence-AGPL--3.0%20%2B%20MIT%20%2B%20CC%20BY%204.0-blue)](#licence) [![Latest release](https://img.shields.io/github/v/release/mrpickles007/boa)](https://github.com/mrpickles007/boa/releases/latest) [![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](#prerequisites) [![Linux | macOS | Windows](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey)](#prerequisites)

BOA is an agent skill, `build-on-autopilot`, that teaches an AI coding agent to run a software project end to end:
start it, work it, pause it, resume it and close it, with a complete working discipline. A lead agent plans and
measures; sub-agents (builder, adversarial reviewer, tester, integrator, analyzer) build, review, test and integrate
in parallel lanes on git worktrees, landed by merge trains, under rules that keep the work correct, traceable and
safe. A typed project memory with hybrid search keeps every lesson and decision across sessions. BOA starts a new
project (greenfield), takes over an existing one (brownfield) or refactors one (refactor).

**Works with** Claude Code, Codex CLI, Gemini CLI and OpenCode ([their profiles](references/runtimes.md)) and, with [the declared fallbacks](references/runtimes.md#any-other-agent-editors-other-clis), any other agent that reads `AGENTS.md`.

BOA is **scaffolding: mainly discipline, few tools.** It ships the discipline (the rules, the procedures, the agent
contracts, the commands, the memory bank and the lead's files as templates) plus the few generic tools the
discipline needs. Everything that depends on your project (its stack, its gate, its CI, its runners, its
protections, its models) is built by the agent, in your project, under the discipline itself. BOA is
**project-agnostic** (any project, any programming language) and **harness-agnostic** (no agent runtime is the
default; the agent wires BOA into the runtime it runs in).

- What BOA ships as code and what it teaches: [docs/01-overview.md](docs/01-overview.md#what-ships-as-code)
- The full documentation set: [Documentation](#documentation)

## Quick start

```
npx skills add mrpickles007/boa
```

That installs the skill `build-on-autopilot` into the skills folder of the agents you pick, through the open
agent-skills CLI (`npx` needs Node.js; without it, use the release archive: [Install](#install)). Then, in an agent
session at the top of your project:

```
/build-on-autopilot <greenfield|brownfield|refactor> [idea-file]
```

In Claude Code 2.1.275 or later, one command installs it as a plug-in: `/plugin install boa --marketplace mrpickles007/boa` (it then starts as `/boa:build-on-autopilot`).

BOA itself needs only Python 3.11+ and git 2.31+; its install builds the memory search environment once (a Python
in the range given under [Prerequisites](#prerequisites) and a download of about 480 MB).

## The memory layer

BOA gives your project a persistent, searchable memory, so no lesson, decision, constraint or defect is lost between
sessions, agents or context compactions:

- **Typed memories.** Every memory is one block with a type. BOA ships 17 base types: lesson, gotcha, edgecase,
  constraint, contract, adr, edr, outcome, trap, heuristic, invariant, goal, nogoal, requirement, deferred, security
  and bug. Each type says what it records, when to write it, what it must contain, which memory-bank file it goes to
  and at which moments it is recalled.
- **Written and recalled by rule.** Agents write memories as they work and search them before they act: at the start
  of a task, on an error, before a decision, a contract change, a review, a plan or a close. Where the runtime allows
  it, hooks inject the relevant memories automatically.
- **Hybrid search.** Keyword ranking (BM25) re-ranked by meaning with a local multilingual model, and a fallback that
  never answers a false "nothing found". It runs offline once installed.
- **Never rewritten.** A memory is never edited: a newer one supersedes it, and the history stays readable.
- **Easy to extend.** Every type, route and recall moment lives in one file, `.boa/memory-types.json`. Add a type with
  its fields, run `memory_types.py --check`, and the new type works at once in the writer, the lint, the search, the
  hooks and the tables the agents read. How:
  [references/memory-types.md](references/memory-types.md) (the section on adding a memory type);
  the whole layer: [docs/07-memory-and-state.md](docs/07-memory-and-state.md).

**Speed**, measured 2026-11-18 on a quiet CPU-only host with 8 CPUs: a `--query` search takes a fixed part of
about 3 s, mostly starting the local embedding model, plus a part that grows with the memory. Version 1.1.0 shrinks
the growing part, with identical results in the same order; before and after, measured side by side on the same host:
a `--query` search that finds keyword matches, 5.4 to 4.4 s at 10,000 memories, 8.8 to 6.1 s at 20,000 and 14.3 to
7.8 s at 50,000; one that finds none and falls back to meaning, 8.3 to 4.7 s, 13.8 to 6.6 s and 31.9 to 11.6 s; a
search by keyword or type, without `--query` (it never loads the model), 1.5 to 0.4 s, 2.9 to 0.7 s and 6.9 to 1.3 s;
1,000 new memories written at once into a bank of 1,000, 10,000 or 50,000, 13.7 to 0.4 s, 94 to 1.2 s and 492 to
5.7 s. Peak memory is equal or lower, and the vector cache file is about 23% smaller.

## Prerequisites

The `boa` launcher checks these first, without Python, and changes nothing while one is missing (exit 3, naming what
is missing and the version found):

- **git 2.31 or newer** (the project is, or becomes, a git repository);
- **Python 3.11 or newer** (`python3`; BOA's tools use the standard library only);
- an agent runtime that can run the skill (or, without skills, the paste-in prompt [KICKOFF.md](KICKOFF.md));
- on Windows, Git for Windows (the launcher there is `boa.cmd`).

The install also builds the memory search environment, so it needs once:

- a Python between the oldest and newest version the pinned embedding library ships for (the range is in
  `core/embed.json`; today 3.11 to 3.14) with its `venv` module;
- network access to the Python package index and to the model hub (about 480 MB, downloaded once into
  `.boa/embed/`; behind a proxy, set `HTTPS_PROXY`, credentials included, because the download runs with a
  redirected home where `~/.netrc` is not read).

Nothing else is required. A container engine, a forge CLI or a remote test runner are your project's choices, wired
by the agent when the project needs them.

## Get BOA

BOA is published as the public repository `boa` (its skill is `build-on-autopilot`), under the licence below. It
reaches you through these channels:

- **The release archive** `boa.tar.gz` (recommended): attached to every release on the repository's releases page,
  tagged `vMAJOR.MINOR.PATCH`. It holds the shipped files only and unpacks to `boa/`; install it as the folder
  `build-on-autopilot` ([Install](#install), step 2).
- **The repository**: a clone of `boa` is a skill folder too: its root holds `SKILL.md` and the skill's files, plus
  one runtime's plug-in marketplace file, the community files under `.github/` and a `.gitignore`.
- **The open agent-skills CLI** (`npx skills`, see [Quick start](#quick-start)): it clones the repository and copies
  the skill folder into the skills folder of the agents you pick.
- **A runtime's plug-in marketplace or skill installer** that reads a git repository: it installs `boa` directly. The
  commands for each runtime are in
  [references/runtimes.md](references/runtimes.md#getting-the-skill-into-a-runtime).

## Install

1. **Get the release.** Download the release archive from the project's releases page and unpack it.
2. **Install the skill** into your agent runtime's skills directory, as a folder named `build-on-autopilot` holding
   the unpacked files. Where that directory is, for each runtime, is in [references/runtimes.md](references/runtimes.md)
   (your runtime's profile). A runtime without skills: paste [KICKOFF.md](KICKOFF.md) into the session instead.
3. **Start it** in an agent session at the top of your project:

   ```
   /build-on-autopilot <greenfield|brownfield|refactor> [idea-file]
   ```

   The idea file is optional and can have any name. In `greenfield` and `refactor`, with no file, the agent takes
   the idea from what you already said, or asks you to describe it, writes it into `IDEA.md` and goes on only after
   you confirm it. In `brownfield` no file is needed.

   The agent first assesses what its runtime can do, checks the machine, and asks you only what it cannot decide
   (one question at a time, each with its recommendation).
4. **The config template.** The agent runs `boa install --target . --package <skill>`. With no `.boa/config.env`
   yet, it writes the commented template there, installs nothing else and exits 1.
5. **The agent fills it in** from what it knows and from your answers (project name, models, forge, runner, the
   Python every hook calls, the scratch root of its runtime, ...). Every `REQUIRED` key gets a value. On an existing
   project whose `AGENTS.md` already holds its own rules (brownfield, refactor), the agent suggests the pointer mode,
   `BOA_AGENTS_BLOCK=pointer`, and asks you: BOA's rules go into their own file, `docs/boa-rules.md`, and `AGENTS.md`
   gets only a short marked block that points to it; where your rules and BOA's conflict, yours win until a
   reconciliation task aligns them. It suggests it too when your `AGENTS.md` plus BOA's rules would pass the
   instruction-file size cap of your runtime. `full` (the whole rules as a marked block of `AGENTS.md`) is the
   default: [the AGENTS.md block mode](docs/02-install-and-wiring.md#the-agentsmd-block-mode).
6. **Install for real.** The agent runs `boa install --target . --package <skill>` again (on an existing project it
   runs `--dry-run` first and shows you the plan). The installer writes BOA's files (under `.boa/`, plus
   `AGENTS.md`, the memory bank, the agent handbook, the lead directory and marked blocks in a few files), never
   overwrites a file of yours (a conflicting rendering waits in `.boa/pending/`), then builds the memory search
   environment in `.boa/embed/` and warms its vectors. It ends with `install: done`.
7. **The agent wires BOA into its runtime**: the agents, the commands, the hooks and the runtime options, in the
   runtime's own format, merged into your runtime files and recorded so it can be undone. BOA writes no runtime
   file itself.
8. **Self-tests, commit, forge.** The agent verifies the install (a second `--dry-run` reports every file `same`,
   apart from the marked blocks, which always report `block`),
   commits `chore: install BOA` and does only the forge steps you said yes to.
9. **Run.** The agent starts `run-project`: the mode's bootstrap (specifications, contracts, plan), then the
   autonomous loop until the project is complete or a decision only you can take blocks everything.

`boa` is the one command-line entry point: `sh <skill>/core/bin/boa` before the install, `sh .boa/bin/boa` after it
(on Windows `boa.cmd` beside it); `boa help` lists the subcommands. Every step in detail:
[docs/02-install-and-wiring.md](docs/02-install-and-wiring.md#the-install-flow).

## Update

Updating to a new release is conservative: it loses nothing your project or its agent changed. Ask the agent to
update BOA; it runs the update as a task of its own, outside a merge train:

1. it compares the installed version (in the project's capabilities record) with the new release's `VERSION`, reads
   the release notes and keeps a copy of the old skill as the base of every merge;
2. it updates the skill through the channel that installed it, adds the config keys the new release brings (never
   changing a value you set) and shows you the plan of `boa install --target . --package <skill> --dry-run`;
3. with your yes it installs: a file BOA installed and your project changed since is never overwritten (the install
   reports it `kept` and parks the new version in `.boa/pending/`), the new memory types and marker words are merged
   into your own files without touching your entries, and the agent merges every parked file with git's three-way
   merge, asking you when a change of yours and one of BOA's meet;
4. it re-wires its runtime, runs the self-tests and the gate, and commits `chore: update BOA to vX.Y.Z` on a branch.

Every step: [docs/02-install-and-wiring.md](docs/02-install-and-wiring.md#re-installing-and-upgrading).

## Uninstall

First the agent undoes the wiring it added to the runtime, then:

```
sh .boa/bin/boa uninstall            # add --dry-run to see the plan first
```

It removes exactly what the install recorded in `.boa/installed.list`, plus BOA's machine-local directories (the
memory search environment, BOA's state and logs). Files you changed since are kept and reported (`--force` removes
them too); `.boa/config.env` is kept. Details: [docs/12-uninstall.md](docs/12-uninstall.md).

## Honest limits

- The guards are a safety net against accidents, not a sandbox against attacks.
- What a runtime cannot do (no hooks, no sub-agents, a hook that cannot deny) is declared by the agent and replaced
  by the closest faithful equivalent, never faked.
- Without the memory search environment, memory search ranks by keywords (BM25) alone and says so.

All of them: [docs/13-faq-and-limits.md](docs/13-faq-and-limits.md).

## Documentation

| Chapter | What it covers |
|---|---|
| [01 Overview](docs/01-overview.md) | what BOA is, what it ships as code, what it teaches, the modes and the commands |
| [02 Install and wiring](docs/02-install-and-wiring.md) | prerequisites, the install flow, the config, the AGENTS.md block mode (full or pointer), the runtime wiring, the project-wiring checklist, updating to a new release |
| [03 The workflow](docs/03-the-workflow.md) | plan, lanes, the pipeline, tests and plant rounds, merge trains, HITL |
| [04 Roles](docs/04-roles.md) | the lead, sub-leads and every sub-agent; models; reports; resuming an agent or starting a fresh one |
| [05 Safety](docs/05-safety.md) | the guards, the lead's override, protected commands, the content rules for everything that leaves the machine, the project's own protections |
| [06 Rules pool](docs/06-rules-pool.md) | the generic rules, how to adopt, adapt and add them |
| [07 Memory and state](docs/07-memory-and-state.md) | the memory layer: 17 base memory types, writing, search and recall, extending it with new types; lead state, metalearning; the product language and the plan's own column names |
| [08 Measuring](docs/08-measuring.md) | the status screen, traceability, durations, disk, residue, logs |
| [09 Remote runner](docs/09-remote-runner.md) | heavy runs off the development machine, on one runner or several (discipline) |
| [10 Pause, resume, close](docs/10-pause-resume-close.md) | the three commands step by step, resuming in another runtime |
| [11 Modes](docs/11-modes.md) | greenfield, brownfield, refactor; stack choice; writing a stack plug-in |
| [12 Uninstall](docs/12-uninstall.md) | removing BOA and the wiring |
| [13 FAQ and limits](docs/13-faq-and-limits.md) | honest limits and common questions |
| [14 Contract-driven development](docs/14-contract-driven-development.md) | contracts first, code second, contracts enforced by tests |

The skill itself is [SKILL.md](SKILL.md); the references the agent reads on demand are in the `references/` folder.

## Licence

Copyright (C) 2026 Giulio Alberello

BOA uses three standard licences, mapped file by file in `REUSE.toml` (the REUSE convention); their exact texts are in
the LICENSE file and the LICENSES folder. In plain words:

- **BOA itself is free software under the GNU AGPL-3.0-only:** its tools (the memory layer included), launchers and
  hooks (`core/`), the skill's own instructions (`SKILL.md`), its build script and its documentation. If you change
  BOA and distribute it, or let people use a changed BOA over a network, your version stays under the AGPL-3.0-only,
  and they are entitled to its source.
- **The texts BOA writes into your project are CC BY 4.0** (Creative Commons Attribution 4.0): the templates of
  `AGENTS.md`, the memory bank, the agent contracts, the commands, the handbook and the lead's files, the documents
  rendered from them, the config template, and the references the agent reads. What your project writes into them
  (its plan, specifications, decisions and memories) and the `.boa/config.env` the agent fills in are yours. You may
  use, change and share BOA's texts, in public or private projects, as long as you keep the attribution.
- **The code BOA copies into your project is MIT:** the context-gate skill with its scripts, hooks, instructions and
  assets, the stack plug-in template, and the memory-types and markers configs your project versions. You may use,
  change and keep them, as long as you keep the copyright and licence notice.
- **The attribution travels on its own:** `boa install` writes `docs/boa-notice.md` into your project, the one notice
  both licences ask for (the credit, which licence covers which of BOA's files, the MIT text), and the context-gate
  skill carries its own `LICENSE`. Keep the notice while BOA's files are in your project (`boa uninstall` keeps it
  while any of them stays; keep it by hand if you keep the runtime copies of BOA's agent and command definitions, the
  context-gate copies or files into which you merged BOA's renderings (the conflicts the install parked in
  `.boa/pending/`), which the uninstall does not see); when you share changed ones, say so there.
- **What you build with BOA is yours.** BOA's licence does not cover your software just because BOA helped make it.
- **Only the tool copies in `.boa/` stay under the AGPL-3.0-only.** They (`.boa/bin/`, `.boa/tools/`,
  `.boa/hooks/`, `.boa/embed.json`) are git-ignored (your project's own config files there, `.boa/config.env` and
  `.boa/protected-commands.conf`, are versioned, and are yours) and are not meant to be redistributed: every clone
  gets them back from `boa install`.

The logo (`docs/assets/logo.png`) is not covered by the code or text licences: all rights reserved; it may be
displayed in copies and modified versions of BOA to identify BOA; no other right is granted.

The public repository's code of conduct (`.github/CODE_OF_CONDUCT.md`, the Contributor Covenant 2.1) is not part of
BOA: it is under CC-BY-4.0 too.

Contributions are accepted under the licence of the files they touch: AGPL-3.0-only for BOA's code, MIT for the code
BOA copies into a project, CC-BY-4.0 for the texts.

This is a summary: the licence texts in `LICENSE` and `LICENSES/`, and the file mapping in `REUSE.toml`, are what
counts.
