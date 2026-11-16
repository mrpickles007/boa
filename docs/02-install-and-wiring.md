# 02 Install and wiring

## Prerequisites

| Needed | Checked by | When missing |
|---|---|---|
| git 2.31 or newer | the `boa` launcher, before Python | exit 3, nothing done |
| Python 3.11 or newer (standard library only) | the `boa` launcher, without Python | exit 3, nothing done |
| an agent runtime that runs the skill (or the paste-in [KICKOFF.md](../KICKOFF.md)) | the agent's self-assessment | the agent tells you |
| on Windows, Git for Windows | the launcher (`boa.cmd`) checks git | exit 3 |
| a Python in the embedding library's range (`core/embed.json`, today 3.11 to 3.14) with its `venv` module | `boa install` | the install says what is missing and exits 1; the files stay installed |
| network access to the package index and the model hub, once | `boa install` | as above; behind a proxy set `HTTPS_PROXY` (credentials included: `~/.netrc` is not read) |

The launcher looks for the interpreter named by `BOA_PYTHON` in the config beside it, then the first working
`python3` on `PATH`, then `python3.<n>` from newest to oldest, `python` and the usual absolute paths. On exit 3 it
prints what is missing, the version found and where to get it for your OS. The agent then tells you how to install
it on this OS, and installs it only with your explicit yes and the rights to do it; it never continues while one is
missing. Nothing else is installed or changed on the machine without your consent.

## The install flow

1. **Get the release** (the release archive from the project's releases page; the other channels:
   [README](../README.md#get-boa)) and install the skill folder,
   named `build-on-autopilot`, in your runtime's skills directory (per runtime:
   [references/runtimes.md](../references/runtimes.md#getting-the-skill-into-a-runtime)). Without skills, paste [KICKOFF.md](../KICKOFF.md).
2. **`/build-on-autopilot <greenfield|brownfield|refactor> [idea-file]`** in a session at the top of the project.
3. **Capability self-assessment and environment check** ([01 Overview](01-overview.md#assess-decide-ask), the
   project-wiring item "capabilities record"). Questions only for what the checks and documents cannot decide.
4. **The config template:** `sh <skill>/core/bin/boa install --target . --package <skill>`. With no
   `.boa/config.env` it writes the commented template there, installs nothing else and exits 1.
5. **The agent fills in the config** ([The config file](#the-config-file)).
6. **Install:** the same command again; on an existing project `--dry-run` first, with the plan shown to you. It
   renders the templates, copies the tools, writes the marked blocks, records everything in `.boa/installed.list`,
   builds the [memory search environment](#the-memory-search-environment) and warms its vectors.
7. **Conflicts:** for every `conflict` or `kept` line of the report, the agent merges the rendering waiting in
   `.boa/pending/<path>` into your file by hand (your content kept, BOA's added) and re-runs the installer.
8. **Self-wiring** of the runtime ([Wiring BOA into your runtime](#wiring-boa-into-your-runtime)).
9. **Self-tests** ([Verifying the install](#verifying-the-install)), then the commit `chore: install BOA` (on a
   branch of the configured grammar, or as the initial commit of an empty repository) and only the forge steps you
   said yes to ([references/forge.md](../references/forge.md)).
10. **Hand-over:** a short report (environment, capabilities and substitutes, choices with reasons, what was
    installed and wired, what is left to you), then `run-project`.

The whole flow is the skill itself: [SKILL.md](../SKILL.md).

`boa install` options: `--target DIR` (the project; default the git top level of the current directory),
`--package DIR` (the BOA package; required when run from `.boa/`), `--dry-run`. Exit codes: 0 done (conflicts are
reported, not fatal), 1 error (or the template just written, or the memory search environment not built), 2 usage,
130/143 interrupted (the manifest of everything touched is written). The launchers alone use exit 3.

## The config file

`.boa/config.env` holds the project's settings, read by every BOA tool, hook and template: `KEY='value'` lines,
single-quoted, parsed without executing anything (a line outside that grammar is refused, naming the line). The
template's comments give every key its rule and, where one fits, its default. The installer refuses while a
`REQUIRED` key is empty or a value is invalid, naming the key: `BOA_PROJECT_NAME`, `BOA_PROJECT_SLUG`,
`BOA_MODEL_FRONTIER`, `BOA_MODEL_MID`, `BOA_PYTHON`, `BOA_WT_DIR`, `BOA_SCRATCH_ROOT`, `BOA_LABEL_KEY`. The agent
checks the values the way a validator would (the slug's charset, a branch grammar holding `<task>` and `<slug>`, the
worktrees dir and scratch root outside the project, the interpreter runs) and records your choices in the decisions
log. The model roster has no default: the agent picks the runtime's frontier model and the one just below it from
the runtime's current list and confirms them with you. The checklist item: "Config" in
[references/project-wiring.md](../references/project-wiring.md).

## What the installer writes

- **Under `.boa/`:** the tools (`bin/`, `tools/`, `hooks/`), `memory-types.json`, `embed.json`, `markers.json`, the
  runtime-neutral agents and commands (`agents/`, `commands/`), the stack plug-in template (`stack/`), the manifest `installed.list` and, after the embedding
  step, `embed/`. All of it is git-ignored and put back by `boa install` in every clone, except the three files the
  agent writes for the project, which stay versioned: `.boa/config.env`, `.boa/protected-commands.conf`,
  `.boa/memory-types.json`.
- **Project documents:** `AGENTS.md` (every rule; a marked block `<!-- boa:start -->` ... `<!-- boa:end -->` in an
  existing one), `memory-bank/`, `docs/agent-handbook.md`, `docs/parity/`, the lead directory (default `.lead/`,
  git-excluded) and the forge's PR/MR template (`.github/pull_request_template.md` or
  `.gitlab/merge_request_templates/Default.md`, only for the configured forge).
- **Marked blocks** in `.gitignore`, `.gitattributes` (BOA's files checked out with LF on every platform: the
  launchers and hooks break with CRLF), `.git/info/exclude` (the lead directory, `.lane-resume/`) and your own
  `memory-bank/04-ARCHITECTURE.md` (the residue register).

Rules: a file of yours is never overwritten (the rendering goes to `.boa/pending/<path>` and the conflict is
reported); a file that equals BOA's rendering is left alone; a file BOA installed and someone changed since is kept
the same way; nothing is written through a symlink; everything that can fail is checked before the first write. On
a fresh clone of an installed project (BOA's `.gitignore` block present, no manifest) identical files are adopted.
The installer writes no runtime directory and no runtime setting.

## The memory search environment

`boa install` builds `.boa/embed/`: an isolated virtual environment of BOA's own (never the system Python's
packages) holding the embedding library pinned in `.boa/embed.json`, and the model's files downloaded once at a
pinned revision and checked against their sha256 before anything loads them. It is built in `.boa/embed.partial/`,
checked, then swapped in, so a failure leaves nothing half-installed; an up-to-date environment is left alone. Then
the install computes the search vector of every memory once (best effort). At query time nothing goes to the network.
When the step fails, the install says what is missing and how to fix it and exits 1 with the files installed; until
it is fixed, memory search ranks by BM25 alone and warns. The agent asks you before changing anything on the machine
to fix it. How search uses it: [07 Memory and state](07-memory-and-state.md#recall-and-memory-search).

## Wiring BOA into your runtime

BOA provides the tools and hooks; the agent wires them into its runtime, in the runtime's own format, from
[references/runtimes.md](../references/runtimes.md) (a profile per known runtime, each an example, none the
default) and the neutral hook contract [references/hook-contract.md](../references/hook-contract.md):

- the agents of `.boa/agents/` in the runtime's sub-agent format, with the configured model per tier;
- the commands of `.boa/commands/` in its command or prompt format;
- the hooks, each event mapped to BOA's neutral event: session start (status), pre-tool (the guard and the pause
  guard, which must be able to deny), post-tool of a file write (memory lint), post-tool of a sub-agent spawn (the
  agent-to-task binding), post-tool failure (memory recall), sub-agent stop (report capture), the lead's stop (the
  resume file at a pause), pre-compaction (the context-gate);
- the instructions: every rule lives in `AGENTS.md`; only a runtime that does not read it natively gets its own
  instruction file, holding nothing but an import of or a pointer to `AGENTS.md`;
- the runtime options: permissions, the cleanup allowlist ([05 Safety](05-safety.md#the-cleanup-allowlist)) and the
  prompt-cache lifetime (sub-agents the longest the runtime allows; the main conversation only with your yes, since
  it may cost more).

The guards fail closed and so must their wiring: a deny, a crash, a timeout or an output that is not a verdict
refuses the call. Where the runtime lacks a feature, the agent picks the closest faithful equivalent and declares
it. It merges into your runtime files, never replaces them, and records every entry so the wiring can be undone.
The tool cards say what each tool needs wired and how to verify it
([tool cards](../assets/templates/agent-handbook.md#38-tool-cards)).

## The context-gate

The context-gate is a standalone skill shipped in the package ([context-gate/SKILL.md](../context-gate/SKILL.md)):
at every compaction it keeps a byte-exact snapshot of the transcript, and where the runtime allows it extends the
compaction prompt (light profile); where it does not, it falls back to the snapshot alone. Agents follow its "after a
compaction" rule: re-read the files and the lane state, and read the raw transcript when in doubt. The agent wires it
from its own instructions ([context-gate/INSTALL.md](../context-gate/INSTALL.md)), or finds an equivalent where the
runtime has no compaction hook.

## The project-wiring checklist

Everything project-specific is discipline: each item below becomes a plan task at bootstrap and is built, reviewed
and tested like product work, with the project's own library or tool. Nothing on the list is pre-filled by BOA.
The reference for each: [references/project-wiring.md](../references/project-wiring.md).

| Item | What the agent builds in the project |
|---|---|
| Config | `.boa/config.env` filled in, re-run of `boa install` until exit 0 |
| capabilities record | what the machine and runtime have, in `memory-bank/04-ARCHITECTURE.md` "Environment"; the lane cap and admission keys from measured figures |
| light and heavy suites | the test-execution choice (where, serial or parallel, how many) decided with you from measured load; protected-command rules that keep heavy runs off a shared machine |
| project protections | the project's protected paths, commands and wrapped tools, as guard rules |
| git hooks | no direct or force push to main (server-side protection first), commit-message check, memory lint at commit |
| secret scanning | a maintained scanner on every commit's staged lines and on the whole history at close-out |
| the project gate | the project's ONE gate, calling BOA's kept checks; its self-test plants a defect per step |
| remote runners | heavy runs on a Linux server: allowlist, isolation, cleanup, no secrets in logs ([09](09-remote-runner.md)) |
| usage clock and throughput | time per task and role, tokens per agent run (or "declared unavailable"); the throughput review with proposals |
| measure commands | the project's own disk footprint against the warning and hard thresholds |
| deployed-instance objects | the residue check against the residue register |
| suite timings and duration control | the gate's timings judged at every train ([08](08-measuring.md#duration-control)) |
| licence and dependency audit | licences against an approved allowlist, dependencies against advisory and malware databases, as gate steps |
| clean-room check (optional) | only for a rewrite of a product it may not copy: copied passages and a missing provenance line refused |
| permission log | every permission request and denial, capped and redacted |
| wire BOA into your runtime | as above |
| model roster per runtime | the frontier and mid models, confirmed with you |
| stack plug-in | `.boa/stack/` adapted into the project's plug-in ([11](11-modes.md#writing-a-stack-plug-in)) |
| CI (only with consent) | the project's CI running its gate, lean triggers, pinned actions, a minutes budget |

## Verifying the install

At minimum: the config parses (`sh .boa/bin/boa render --config .boa/config.env --get BOA_PROJECT_SLUG`), the manifest
`.boa/installed.list` exists, a second `boa install --target . --package <skill> --dry-run` reports every file `same`
(the install is idempotent and complete) apart from the marked blocks, which always report `block`, and conflicts
kept on purpose, no prerequisite is missing, and
`sh .boa/bin/boa status --guards` prints no `GUARD DOWN` line once the runtime is wired. A failure is reported and the
flow stops: a half-install is never reported as done.

## Re-installing and upgrading

`boa install` is idempotent: it updates unchanged installed files, replaces its blocks and removes installed files
the new config no longer produces (unless changed). After installing a newer package the agent unwires the hooks of
tools no longer shipped, removes old copies of BOA's git hooks from `.git/hooks`, and re-generates its runtime
renderings of the agents and commands.

## Locks and concurrent runs

One install runs at a time per repository: a lock file in the git directory (`boa-install.lock`), present only while
BOA is installed. BOA's file locks are operating-system locks (`fcntl.flock` on Linux and macOS, `msvcrt.locking` on
Windows), released by the system when their process ends, so a lock is never left stale; a platform with neither is
refused, with no weaker fallback. Known limits: [13 FAQ and limits](13-faq-and-limits.md#locks).
