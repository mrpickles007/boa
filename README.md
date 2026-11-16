# BOA - Build On Autopilot

<p align="center"><img src="docs/assets/logo.png" alt="BOA - Build on autopilot" width="664"></p>

*Constrict your code to be right.*

BOA is one skill, `build-on-autopilot`, that teaches an AI agent to run a software project end to end: start it,
work it, pause it, resume it and close it, with a complete working discipline. A lead agent plans and measures;
sub-agents build, review adversarially, test and integrate, in parallel lanes, under rules that keep the work
correct, traceable and safe.

BOA is **scaffolding: mainly discipline, few tools.** It ships the discipline (the rules, the procedures, the agent
contracts, the commands, the memory bank and the lead's files as templates) plus the few generic tools the
discipline needs. Everything that depends on your project (its stack, its gate, its CI, its runners, its
protections, its models) is built by the agent, in your project, under the discipline itself. BOA is
**project-agnostic** (any project, any programming language) and **harness-agnostic** (no agent runtime is the
default; the agent wires BOA into the runtime it runs in).

- What BOA ships as code and what it teaches: [docs/01-overview.md](docs/01-overview.md#what-ships-as-code)
- The full documentation set: [Documentation](#documentation)

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
- **The repository**: a clone of `boa` is a skill folder too (its root holds `SKILL.md` and only the skill's files).
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
   Python every hook calls, the scratch root of its runtime, ...). Every `REQUIRED` key gets a value.
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
| [02 Install and wiring](docs/02-install-and-wiring.md) | prerequisites, the install flow, the config, the runtime wiring, the project-wiring checklist |
| [03 The workflow](docs/03-the-workflow.md) | plan, lanes, the pipeline, tests and plant rounds, merge trains, HITL |
| [04 Roles](docs/04-roles.md) | the lead, sub-leads and every sub-agent; models; reports |
| [05 Safety](docs/05-safety.md) | the guards, the lead's override, protected commands, the project's own protections |
| [06 Rules pool](docs/06-rules-pool.md) | the generic rules, how to adopt, adapt and add them |
| [07 Memory and state](docs/07-memory-and-state.md) | memory bank, memory blocks and search, lead state, metalearning |
| [08 Measuring](docs/08-measuring.md) | the status screen, traceability, durations, disk, residue, logs |
| [09 Remote runner](docs/09-remote-runner.md) | heavy runs off the development machine (discipline) |
| [10 Pause, resume, close](docs/10-pause-resume-close.md) | the three commands step by step |
| [11 Modes](docs/11-modes.md) | greenfield, brownfield, refactor; stack choice; writing a stack plug-in |
| [12 Uninstall](docs/12-uninstall.md) | removing BOA and the wiring |
| [13 FAQ and limits](docs/13-faq-and-limits.md) | honest limits and common questions |
| [14 Contract-driven development](docs/14-contract-driven-development.md) | contracts first, code second, contracts enforced by tests |

The skill itself is [SKILL.md](SKILL.md); the references the agent reads on demand are in the `references/` folder.

## Licence

Copyright (C) 2026 Giulio Alberello

BOA uses two standard licences, mapped file by file in `REUSE.toml` (the REUSE convention); their exact texts are in
the LICENSE file and the LICENSES folder. In plain words:

- **BOA itself is free software under the GNU AGPL-3.0-only:** its tools, launchers and hooks (`core/`), its build
  script and its documentation. If you change BOA and distribute it, or let people use a changed BOA over a network, your version
  stays under the AGPL-3.0-only, and they are entitled to its source.
- **The templates, the references, the context-gate skill and every other file BOA writes into your project are MIT-0**
  (MIT No Attribution): the templates of `AGENTS.md`, the memory bank, the agent contracts, the commands, the
  handbook and the lead's files, the documents rendered from them, the config template, the stack plug-in template,
  the references the agent reads and the context-gate skill with its scripts, hooks and assets. You may use, change
  and keep them private, with no attribution and no obligation.
- **What you build with BOA is yours.** BOA's licence does not cover your software just because BOA helped make it.
- **Only the tool copies in `.boa/` stay under the AGPL-3.0-only.** They are git-ignored (your project's own config
  files there are versioned, and are yours) and are not meant to be redistributed: every clone gets them back from
  `boa install`.

The logo (`docs/assets/logo.png`) is not covered by the code or template licences: all rights reserved; it may be
displayed in copies and modified versions of BOA to identify BOA; no other right is granted.

Contributions are accepted under the licence of the files they touch: AGPL-3.0-only for code, MIT-0 for templates.

This is a summary: the licence texts in `LICENSE` and `LICENSES/`, and the file mapping in `REUSE.toml`, are what
counts.
