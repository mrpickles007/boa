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
5. **The agent fills in the config** ([The config file](#the-config-file)); on a brownfield or refactor project whose
   `AGENTS.md` already holds its own rules it suggests the pointer block mode and asks you
   ([The AGENTS.md block mode](#the-agentsmd-block-mode)).
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

## The AGENTS.md block mode

`BOA_AGENTS_BLOCK` decides where BOA's rules go:

- **`full`** (the default, for greenfield): the whole of BOA's rules are a marked block of `AGENTS.md`
  (`<!-- boa:start -->` ... `<!-- boa:end -->`; the whole file when there is none).
- **`pointer`**: BOA's rules go into their own versioned file, `docs/boa-rules.md` (installed, recorded in the
  manifest and uninstalled like BOA's other files; its links point from `docs/`), and `AGENTS.md` gets only a short
  marked block that points to it. That block also says that wherever a BOA file says `AGENTS.md` for one of BOA's
  rules, the rule is read in `docs/boa-rules.md`, and it states the precedence: where your own rules and BOA's
  conflict, yours win until the rules reconciliation is done. The reconciliation is a bootstrap task of the
  brownfield and refactor modes ([11 Modes](11-modes.md#reconciling-the-rules-of-an-existing-agentsmd)).

For a brownfield or refactor project whose `AGENTS.md` already holds its own rules, the agent suggests `pointer`
(BOA's numbered rules and placeholders would otherwise sit beside, and contradict, rules your project already
follows) and asks you; `full` stays the default everywhere else. It also suggests `pointer` when your `AGENTS.md`
plus BOA's full block would exceed the instruction-file size cap of a runtime you use and that runtime cannot raise
the cap in its project-level configuration: BOA's block is appended after your text, so the runtime would cut it. Switching later is a re-install with the new value:
the marked block is replaced in place (a block someone edited is kept and the new one parked, as on any update),
`docs/boa-rules.md` is installed (from `full` to `pointer`) or removed
(from `pointer` to `full`; a copy someone changed is kept and reported, as any installed file), and your own text in
`AGENTS.md` is never touched. A switch with an edited block or file is no update merge; never merge the old mode's text with the new
one, or BOA's full rules end up in both files. Per direction: first put the new mode's block or file in place (the parked
block in place of the old one in `AGENTS.md`, or the new `docs/boa-rules.md`), then re-apply your edits there (the block
in `AGENTS.md` for `full`, `docs/boa-rules.md` for `pointer`); from `pointer` to `full` also delete the kept
`docs/boa-rules.md`, since the rules now live only in the `AGENTS.md` block.
`boa uninstall` removes exactly what the mode installed.

## What the installer writes

- **Under `.boa/`:** the tools (`bin/`, `tools/`, `hooks/`), `memory-types.json`, `embed.json`, `markers.json`, the
  runtime-neutral agents and commands (`agents/`, `commands/`), the stack plug-in template (`stack/`), the manifest `installed.list`, the merge bases `merge-base/` (the package's memory types and markers as last
  merged into the project's, read by the next update) and, after the embedding
  step, `embed/`. All of it is git-ignored and put back by `boa install` in every clone, except what the agent
  writes or adapts for the project, which stays versioned: `.boa/config.env`, `.boa/protected-commands.conf`,
  `.boa/memory-types.json`, `.boa/markers.json` (the marker words: `boa language set`, the plan's column aliases)
  and the stack plug-in `.boa/stack/` (a plug-in file or a `markers.json` the project adapted is never overwritten
  by a re-install, also on a fresh clone: it is reported `kept` and the package's version waits in
  `.boa/pending/`).
- **Project documents:** `AGENTS.md` (every rule; a marked block `<!-- boa:start -->` ... `<!-- boa:end -->` in an
  existing one; in the pointer mode only the pointer block, and BOA's rules in `docs/boa-rules.md`), `memory-bank/`, `docs/agent-handbook.md`,
  `docs/boa-notice.md` (the attribution the licences of BOA's files ask for: the credit, which licence covers which
  file, the MIT text; keep it while BOA's files are in the project), `docs/parity/`, the lead directory (default `.lead/`,
  git-excluded) and the forge's PR/MR template (`.github/pull_request_template.md` or
  `.gitlab/merge_request_templates/Default.md`, only for the configured forge).
- **Marked blocks** in `.gitignore`, `.gitattributes` (BOA's files checked out with LF on every platform: the
  launchers and hooks break with CRLF), `.git/info/exclude` (the lead directory, `.lane-resume/`) and your own
  `memory-bank/04-ARCHITECTURE.md` (the residue register).

Rules: a file of yours is never overwritten (the rendering goes to `.boa/pending/<path>` and the conflict is
reported); a file that equals BOA's rendering is left alone; a file BOA installed and someone changed since is kept
the same way; nothing is written through a symlink; everything that can fail is checked before the first write. A
file of yours in the lead directory that one of BOA's hooks writes later (`RESUME-LEAD.md`: the lead stop hook writes
its status block into it at a pause; `open-items.md`: the sub-agent stop hook appends to it) gets a second warning
naming the hook, so its rendering is merged before the first pause. On
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
default) and the neutral hook contract [references/hook-contract.md](../references/hook-contract.md), each format,
event and key checked in the runtime's latest official documentation and the installed version every time, never
from memory (when the installed version is older, it follows that version and tells you an update exists):

- the agents of `.boa/agents/` in the runtime's sub-agent format, with the configured model per tier;
- the commands of `.boa/commands/` in its command or prompt format;
- the hooks, each event mapped to BOA's neutral event: session start (status), pre-tool (the guard and the pause
  guard, which must be able to deny), post-tool of a file write (memory lint), post-tool of a sub-agent spawn (the
  agent-to-task binding), sub-agent start (the memory reminder and every active lane's memories, where the runtime
  injects context there), post-tool failure (memory recall), sub-agent stop (report capture), the lead's stop (the
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
| suite timings and duration control | the budgets file with its timeout cap, every suite run bounded by a timeout derived from its recorded duration, the gate's timings judged at every train ([08](08-measuring.md#duration-control)) |
| licence and dependency audit | licences against an approved allowlist, dependencies against advisory and malware databases, as gate steps |
| clean-room check (optional) | only for a rewrite of a product it may not copy: copied passages and a missing provenance line refused |
| permission log | every permission request and denial, capped and redacted |
| wire BOA into your runtime | as above |
| model roster per runtime | the frontier and mid models, confirmed with you |
| existing tooling (brownfield) | before the install on a project with its own tooling: each item BOA ships kept, adopted or merged (recorded), never two of the same function on one event ([references/modes/brownfield.md](../references/modes/brownfield.md)) |
| stack plug-in | `.boa/stack/` adapted into the project's plug-in ([11](11-modes.md#writing-a-stack-plug-in)) |
| CI (only with consent) | the project's CI running its gate's heavy steps (BOA's static checks stay local), lean triggers, pinned actions, a minutes budget |

## Verifying the install

At minimum: the config parses (`sh .boa/bin/boa render --config .boa/config.env --get BOA_PROJECT_SLUG`), the manifest
`.boa/installed.list` exists, a second `boa install --target . --package <skill> --dry-run` reports every file `same`
(the install is idempotent and complete) apart from the marked blocks, which always report `block`, and conflicts
kept on purpose, no prerequisite is missing, and
`sh .boa/bin/boa status --guards` prints no `GUARD DOWN` line once the runtime is wired. A failure is reported and the
flow stops: a half-install is never reported as done.

## Re-installing and upgrading

`boa install` is idempotent: it updates unchanged installed files, replaces its blocks (`AGENTS.md`'s only while
unchanged) and removes installed files the new config no longer produces (unless changed); a changed
`BOA_AGENTS_BLOCK` switches the mode this way ([The AGENTS.md block mode](#the-agentsmd-block-mode)). A file BOA
installed and the project changed since is never overwritten: the install reports it `kept` and writes the new
version to `.boa/pending/<path>`.

**Updating BOA to a new release.** The lead runs the update as a task of its own, outside a train, and loses
nothing the project or its agent changed. In order:

1. **Versions.** The installed version is the one the capabilities record names (`memory-bank/04-ARCHITECTURE.md`
   "Environment", written at the install and at every update, read from the skill's `VERSION` file); the new one is
   the new skill's `VERSION` file (`X.Y.Z`, the release tag without its `v`). When the record names no version, BOA
   was installed by a release that had no `VERSION` file, 1.0.1 or earlier: the `install_date` line of
   `.boa/installed.list` dates that install, so take the newest release published before that date as the installed
   one (and the old package of step 2 from it), and write the version into the record at step 11. Read the release
   notes. An older version than the installed one is a downgrade: ask the user first.
2. **Keep the old package.** Copy the skill's directory (the runtime tells you where it loaded the skill from) to
   your scratch directory before you touch it: it is the base of every merge below. Delete the copy only at the end.
3. **Update the skill** through the channel that installed it (the release archive, a clone of the repository, a
   runtime's plug-in marketplace or skill installer):
   [references/runtimes.md](../references/runtimes.md#getting-the-skill-into-a-runtime).
4. **See what changed:** `diff -r <old copy> <skill>` on `assets/templates/`, `assets/config.env`, `core/` and
   `stacks/`: the agent and command templates, the config keys, the tools and hooks added, changed or dropped.
5. **New config keys.** The install never writes `.boa/config.env`: add each key the new template adds, with its
   default or the value you decide with the user, and never change an existing value. A template that needs a key
   the config lacks is refused before any write, naming the key.
6. **Dry run, shown to the user:** `sh <skill>/core/bin/boa install --target . --package <skill> --dry-run`. Each
   line is what the install will do (`update`, `create`, `remove`, `kept`, `conflict`, `block`, `merge`); go on
   with the user's yes. `AGENTS.md`'s block is written again only while it is as BOA last wrote it (the manifest
   records its sha256): a block the project changed, or one written by a release that did not record it, is `kept`
   and the new block parked. The residue register BOA adds to a project's own `memory-bank/04-ARCHITECTURE.md` is
   handled the same way for its text, while the rows agents write into its table are carried into the new register,
   in order (the `block` line counts them) while the table's header and separator lines are unchanged; a release
   that changes the columns keeps the register with its rows, `kept`, the rendering parked. `merge` lines name each entry the install adds to the project's memory types and
   markers (a type by its name, a recall moment by its id, a keyword route by its keyword and type, a marker by its
   key): only the entries the new package has and the package version last installed or merged (the merge base,
   kept in `.boa/merge-base/`, BOA's own and git-ignored) had not. The project's own entries are never changed or
   removed, and one it deleted, renamed or narrowed never comes back. With no merge base recorded (BOA installed by a
   release before it, or a fresh clone, where `.boa/merge-base/` is absent) nothing is merged: a `kept` line says so,
   the package's version is parked and becomes the base for the next release. A merge that would leave the file
   invalid (a new marker with no text in the project's language, a route priority the project already uses) or a
   file that does not parse is left as it is, said in a `kept` line. Two lines need care: a document the project
   deleted on purpose comes back as `update` (delete it again after the install); and the other marked blocks are
   written again whole, so a line the project wrote inside `# boa:start` ... `# boa:end` (`.gitignore`, `.gitattributes`, `info/exclude`) is lost: move it
   outside the block first.
7. **Install:** the same command without `--dry-run`.
8. **Reconcile every `kept` and `conflict` line**, one file at a time, in the project's file (never in
   `.boa/pending/`: every install writes it again):
   - the pending copy's sha256 equals the line for that path in `.boa/installed.list`: the release did not change
     the file; nothing to merge, delete the pending copy;
   - otherwise rebuild the base, what the old package installed: a rendered template with the old package's
     renderer, `python3 -I <old copy>/core/bin/render.py --config .boa/config.env --set BOA_INSTALL_DATE=<the
     manifest's install_date> <old copy>/assets/templates/<template>` (leave out `--set` when the config sets that
     key); a copied file as the old package holds it (`core/<path>` for `.boa/<path>`, `stacks/<stack>/<path>` for
     `.boa/stack/<path>`). Its sha256 must be the manifest's line; when it is not, the config changed since: render
     with the config of that time (`git show <the install commit>:.boa/config.env`);
   - merge with git: `git merge-file <path> <base> .boa/pending/<path>` brings the release's changes into the
     project's file and marks each place where both changed the same lines; decide each by judgement (keep what the
     project meant, take BOA's fix), and ask the user when unsure;
   - `AGENTS.md`: its pending copy is the new block only. Rebuild the old block the same way (the old package's
     `AGENTS.md` template, or `AGENTS-pointer.md` with `BOA_AGENTS_BLOCK=pointer`); when it equals the lines inside
     the project's block, nothing was edited: put the pending copy in their place; otherwise merge the three as above
     and put the result there. The next install writes the block and records it. After a switch between `full` and
     `pointer` the old block and the pending one belong to different modes: never merge them. Put the new mode's
     block in place first (the pending copy in place of the old block), then re-apply the project's edits in the new
     mode's home (the `full` block, or `docs/boa-rules.md` for `pointer`); from `pointer` to `full` also delete the
     kept `docs/boa-rules.md`;
   - the memory types and the markers already hold the release's new entries (the `merge` lines): compare the
     pending copy for the shipped entries the release changed, take what the project wants, add by hand what a `kept`
     line refused or what a file with no merge base did not get (diff the old package's file with the pending copy:
     the entries the release added), then `python3 -I .boa/tools/memory_types.py --write` and `--check`;
   - a `no longer installed but changed` line: the release dropped the file and it is now the project's own; keep
     it or delete it, and say which;
   - record each decision in the decisions log, then delete the pending copy.
9. **Re-wire the runtime** (SKILL.md step 7): re-generate your runtime's agents and commands from the updated
   `.boa/agents/` and `.boa/commands/`, applying the template changes of step 4 and keeping the project's own
   customisations (the wiring record lists them), each format checked again in the runtime's latest official
   documentation and the installed version (OR-63); wire what is new; unwire the hooks, agents and commands no longer
   shipped (compare your registrations with the hook inventory) and remove old copies of BOA's git hooks from
   `.git/hooks`.
10. **Self-tests** (SKILL.md step 8): a second dry run reports every file `same` apart from the blocks and the
    conflicts kept on purpose; then the project's gate.
11. **Record and commit:** the new version in the capabilities record, the commit `chore: update BOA to vX.Y.Z` on a
    branch, the pull or merge request as usual; then delete the old package's copy.

A fresh clone installs from the skill its user has: when that version differs from the one the capabilities record
names, install the recorded version first (the clone adopts the files that equal its rendering), then update with
this procedure. The operating procedures check for a new release periodically (section 30 of
`memory-bank/09-OPERATING-PROCEDURES.md`).

## Locks and concurrent runs

One install runs at a time per repository: a lock file in the git directory (`boa-install.lock`), present only while
BOA is installed. BOA's file locks are operating-system locks (`fcntl.flock` on Linux and macOS, `msvcrt.locking` on
Windows), released by the system when their process ends, so a lock is never left stale; a platform with neither is
refused, with no weaker fallback. Known limits: [13 FAQ and limits](13-faq-and-limits.md#locks).
