# Agent runtimes: how BOA wires itself, and what each cannot do

BOA is runtime-neutral: every runtime reaches the same discipline through `AGENTS.md`, the universal entry file (read
order, rules, tools, where everything is). BOA provides the tools and hooks; the agent wires them, in its own
runtime's format, at bootstrap (below, "Self-wire at bootstrap"). The installer writes the runtime-neutral sources
into `.boa/` only: agent definitions in `.boa/agents/` and commands in `.boa/commands/`; BOA's hooks are the
inventory below ("The hooks") and the cleanup allowlist is in "The cleanup allowlist". No runtime-specific file ships
(no instruction file, no settings file). It writes no runtime directory and no runtime setting: the agent registers those sources in its own runtime, merging into the
project's own runtime files without replacing them, records what it wired, and undoes exactly that before an
uninstall. Every runtime sets its own models: `BOA_MODEL_FRONTIER` (builder, reviewer, analyzer) and `BOA_MODEL_MID` (builder-mid, tester,
integrator), the frontier model and the one just below it, from the runtime's current model list. What a runtime cannot do is declared to the
user and written into the capabilities record (`memory-bank/04-ARCHITECTURE.md` "Environment") as a manual step,
never faked.

**Probe, never recall.** The facts below were verified where marked; runtimes change fast, and a date or version
written here is evidence of a past check, never permission to skip one. At every adaptation to your runtime (wiring
or re-wiring hooks with their events and fields, agents with their header: model names and aliases, effort, tools;
commands, settings keys, permission modes, the context-gate profile, the protected-command rules, the runtime part of
an update), check the runtime's latest official documentation and the installed version (its `--help`, its settings
schema, a harmless trial), every time and never from memory, and record what you checked, where and when in the
decisions log. When the installed version is older than the documentation, follow the installed version's behaviour
and tell the user an update exists (the rule is OR-63 of `references/rules-pool.md`). `BOA_RUNTIME=<claude-code|codex|gemini-cli|opencode|other>` in `.boa/config.env`
records the runtime you wire (the installer writes the same `.boa/` sources for every runtime).

## Getting the skill into a runtime

The package is one skill folder, `build-on-autopilot`: the release archive unpacked (it unpacks to `boa/`; rename the
folder) or a clone of the public repository `boa` (whose root is the skill). Where each runtime reads a skill folder
(verified 2026-11-16 on each runtime's official skills page; the Codex CLI and Gemini CLI rows were also run, install,
update and uninstall, on Codex CLI 0.169.0 and Gemini CLI 0.68.0 on 2026-11-17, with the exact commands in their
profiles below; verify again in the latest official documentation and the installed version, OR-63):

| Runtime | Skill folder (user level; project level) | Other channel | Invoked as |
|---|---|---|---|
| Claude Code | `~/.claude/skills/build-on-autopilot/`; `.claude/skills/build-on-autopilot/` | plug-in marketplace: the repository's `.claude-plugin/marketplace.json` lists the plug-in `boa` (the repository root, never the archive): `/plugin marketplace add <owner>/boa#v1.2.3` (pins the release tag; without `#<tag>` it follows the default branch), then `/plugin install boa@boa` | `/build-on-autopilot` (skill folder), `/boa:build-on-autopilot` (plug-in) |
| Codex CLI | `~/.agents/skills/build-on-autopilot/`; `.agents/skills/build-on-autopilot/` (in any directory from the working directory up to the repository root) | the built-in `$skill-installer`, from GitHub only, into `~/.codex/skills/build-on-autopilot/` (the Codex CLI profile); its plug-in marketplace does not list the skill | `$build-on-autopilot` or `/skills` |
| Gemini CLI | `~/.gemini/skills/build-on-autopilot/` or `~/.agents/skills/build-on-autopilot/`; `.gemini/skills/` or `.agents/skills/` | `gemini skills install <local directory or repository URL>` or `gemini skills link <local directory>`, `--scope user` or `workspace` (the Gemini CLI profile) | its skill selection |
| OpenCode | `~/.config/opencode/skills/build-on-autopilot/` (it also reads `~/.agents/skills/` and `~/.claude/skills/`); `.opencode/skills/` | none | its skill selection |
| any other | the runtime's skills folder, if it has one | paste `KICKOFF.md` into the session | - |

The marketplace route installs the repository at the pinned tag; the repository, the archive and a skill folder hold
the same shipped files. A plug-in install prefixes the skill
with the plug-in name: users of that route start BOA with `/boa:build-on-autopilot <mode> [idea-file]` wherever the
documents say `/build-on-autopilot` (the marketplace syntax: the runtime's plug-in install page, verified 2026-11-16).

**Updating the skill** (a step of the update procedure, `docs/02-install-and-wiring.md` "Re-installing and
upgrading": copy the skill's directory to your scratch directory first, as the merge base), by the channel that
installed it:

- a skill folder from the release archive: unpack the new archive outside the skills folder, rename `boa/` to
  `build-on-autopilot`, and put it in place of the old folder (never two copies in the skills folder: the runtime
  would load both);
- a clone of the repository: `git -C <skill> fetch --tags`, then `git -C <skill> checkout vX.Y.Z`;
- Claude Code's plug-in marketplace: `claude plugin marketplace update boa`, then `claude plugin update boa@boa`, and
  restart the session (verified 2026-11-16 with `claude plugin --help` of v2.1.325). A marketplace added with
  `#<tag>` follows that tag; how it moves to a new tag is not verified here: check the plug-in page of the installed
  version (removing the marketplace and adding it again at the new tag is the fallback);
- Codex CLI's `$skill-installer` and Gemini CLI's `gemini skills install`: the exact update steps are in their
  profiles below, verified on the version and date each names; check them again in the runtime's latest official
  documentation and in the installed version before use (OR-63), and record what you checked. `$skill-installer`
  refuses an existing folder, so delete the old one (after the copy) and install the new tag; `gemini skills install`
  replaces an existing folder of the same name whole, and a linked skill needs only the checkout. The skill folder
  route (archive or clone, above) needs no such command;
- OpenCode and any other runtime: the skill folder, as for the archive.

## The runtime profile (what you record for your runtime)

BOA's code knows no runtime: every runtime fact below is yours to read from the installed runtime and to write into
the project (the config and the capabilities record in `memory-bank/04-ARCHITECTURE.md` "Environment"), as a
project-wiring checklist item. For your runtime,
record:

- **config directory and its behaviour**: where the runtime keeps project and user settings, and what it does when
  an agent writes there (some runtimes ask the user for every write in their config directory, whatever the
  allow-list: warn the user before a lane edits it, keep those edits few). Pass the top-level names it uses in the
  project (its settings directory, its own instruction file) as `BOA_RUNTIME_CONFIG`: the guard then refuses
  shell writes and deletions of them in the main checkout, and only that (git verbs, lane worktrees and the lead's own
  file-editing tools are not judged; until it is set, the guard knows no runtime file);
- **scratch root**: the temporary directory the runtime gives a session, and the directory above it that holds
  every session of this project. Read it from the runtime (the path it shows the session); never rebuild it from a
  rule you remember: runtimes derive it from the project path with their own character replacement and length
  limits, which change between versions. Pass it as `BOA_SCRATCH_ROOT` (absolute, at least two levels deep) and the
  layout of the task entries under it as `BOA_SCRATCH_GLOB` (e.g. `*/scratchpad/*` when each session has its own
  directory with a scratch directory inside; `*` when task entries sit directly under the root, the default). The
  guards read it: every level above the last component is shared by the lanes and never deleted, the last level holds
  each lane's `<task>-<role>` entry, which a paused sub-agent may still clean. A glob shallower than the real layout
  lets a lane delete a shared directory (a sub-agent still deletes only inside its own `<task>-<role>` entry), so set
  it before the first lane runs; an invalid value makes the guards refuse every call until it is fixed, and no agent
  binding is recorded meanwhile (a sub-agent spawned then stays unbound after the fix: respawn it). **Upgrading
  BOA:** an install on a runtime with a nested layout that never set the key must set it now (the default `*` is the
  flat layout);
- **private memory**: where the runtime keeps its own memory for the project, if any. It is never the project's
  memory (the memory bank is); say so in the capabilities record (04 "Environment") and keep the two apart;
- **hook events**: the mapping of the runtime's events and payload to the neutral event contract of BOA's hooks
  (`references/hook-contract.md`): which neutral events it can deliver, how a tool call is classed (`sub-agent`,
  `shell`, `file-write`, `file-read`, `report` for a tool that hands back a sub-agent's final report, `other`), how a verdict maps back (deny, block, context, message), and the
  events it cannot deliver with the fallback that catches them later (a project check, a step of the lead's loop);
- **instruction-file size cap**: how many bytes of `AGENTS.md` (and of any instruction file) the runtime puts into
  an agent's context, and how to raise that cap, preferably in the project's own runtime configuration (verified in
  the installed version: render what a fresh agent receives where the runtime can show it, else a harmless trial).
  Compare it with the installed `AGENTS.md`: a block the cap would cut is fixed at wiring (SKILL step 1);
- **models and options**: the model list and the runtime options BOA relies on (below);
- **context window per model**: the context window of the model each role runs on, with its source and the date you
  read it (the latest official documentation of the runtime or the model provider, and the installed version, never
  memory); the lead needs it for the fresh-agent trigger of the agent lifecycle (09 §5.3). Not found: ask the user
  (one question, with a recommendation); until the answer, the size trigger is the cost bound `BOA_AGENT_FRESH_TOKENS` alone
  (a token count the config holds; the trigger is the lower of it and about half the window), and only where a
  context size is reported;
- **prompt-cache lifetime and agent usage reporting**: the cache lifetime (see the TTL item of the profile) and
  whether the runtime reports an agent's context size (the input of its last turn), which is the only figure the size
  trigger compares, or only a per-run token total, which it never compares, and where.

## What BOA needs from a runtime

| Need | Why |
|---|---|
| instructions file loaded every session | the constitution and the read order |
| sub-agents with their own model and effort | builder, reviewer, tester, integrator, analyzer, builder-mid |
| commands (or skills) | `run-project`, `pause-project`, `resume-project`, `close-project` (+ `run-task`, `sync-memory`) |
| pre-tool hook that can deny with a reason | the role-aware guard (with the project's protected-command rules), pause guard |
| session start/end, sub-agent start/stop, permission-request, pre-compaction, stop hooks | status injection, the memory block at a sub-agent's start, report journal, context-gate, pause capture (and the project's own clock and permission log, `references/project-wiring.md`) |
| a way to tell the lead from a sub-agent in a hook | the guard's lane confinement and lead-only override |
| prompt-cache TTL control | sub-agents wait on long runs; a short cache expires between their turns |

## Self-wire at bootstrap

The agent and command files BOA ships are runtime-neutral: a header of neutral metadata, then a body that is the
contract itself. At bootstrap (SKILL step 7) you convert them into your runtime's format. Nothing is converted for
you: BOA ships no runtime adapter. Every example below is an example; none is the default, and each was verified
against the runtime's official documentation at the date given in its section: check it again before you use it
("Probe, never recall", above). For a runtime that is not listed, or
a fact you cannot verify, apply the generic rule here and check your runtime's own documentation (never
invent a format; ask the user when you cannot find out).

**The instruction file: ALL rules live in `AGENTS.md`.** A runtime that reads `AGENTS.md` natively needs nothing
more. A runtime that does not gets its own instruction file holding only an import of, or a pointer to, `AGENTS.md`
(a marked block in an existing one): never a copy of a rule, never a rule of its own. From the sections below (each
verified on its date; verify again in the installed version): Claude Code reads `AGENTS.md` natively from v2.1.277
when no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` sits in the working directory or above it, so it gets
no pointer file (only where one of those exists, or native reading is unavailable, the import `@AGENTS.md` in it);
Codex CLI and OpenCode read
`AGENTS.md` natively; Gemini CLI reads `GEMINI.md` unless its context file name is set to `AGENTS.md` (set it; where
it cannot be set, a `GEMINI.md` that only points to `AGENTS.md`).

**The neutral fields.**

| Header field | Agent files | Command files | Convert to |
|---|---|---|---|
| `name` | the role id (`builder`, `tester`, ...) | the command is its file name | the runtime's agent or command name, in the charset it accepts |
| `description` | when to use the role | what the command does | the runtime's description (the model reads it to choose an agent) |
| `model` | `BOA_MODEL_FRONTIER` or `BOA_MODEL_MID`, rendered to the model you configured | not used | the runtime's model field, spelled as its model list spells it |
| `effort` | reasoning effort | not used | the runtime's reasoning-effort setting; none: drop it and say so in the capabilities record |
| `tools` | the role's capabilities, from BOA's neutral set (defined here, once): `file-read` (read files, list and search their names and contents), `file-write` (create and edit files), `shell` (run commands), `web` (search the web and fetch pages); the first three are the tool kinds of `references/hook-contract.md` | not used | the runtime's tool names or permission rules for each capability (its profile below maps them); a runtime that cannot restrict tools per agent runs the role with the parent's tools and says so |
| `arguments` | not used | the arguments the command takes; the body names them with the neutral placeholder `<arguments>` | the runtime's argument hint, and `<arguments>` in the body becomes the runtime's argument placeholder |

One declared exception: `SKILL.md` is read by the runtime itself, never converted, so its header keeps the
`argument-hint` field and its body the `$ARGUMENTS` placeholder of the skill format; no other shipped file outside
these profiles uses either.

The body is copied unchanged as the agent's instructions or the command's prompt. Keep the BOA files in `.boa/` as the
source of truth and generate the runtime's files from them; a file the project already has is never overwritten.
Re-generate your runtime's files in the same commit as their `.boa/` source changes, and check them against each
other in the project (a step of the project gate or a test): the check fails on a drift of the runtime that works
now and reports another runtime's drift to the user, recorded as an open item, never re-generating it without the
user's yes. The handbook drift check covers `.boa/` only and knows no runtime.

**The hooks.** Every BOA hook reads BOA's neutral event (one JSON object on stdin) and answers with the neutral
verdict (`references/hook-contract.md`); none reads a runtime's own payload. What to register, per neutral event
(`<python>` = `BOA_PYTHON`, `<project>` = the project root as the runtime gives it to a hook; each command gets the
neutral event from your wiring — the small converter you write in the project from the runtime's payload, and the
verdict mapped back — and a logger's ends in `|| true`, so a broken hook never breaks the session, while a guard's
ends in `|| exit 2`, so a broken guard refuses the call (below); the context-gate's ends in neither; timeouts in seconds):

| Neutral event (Claude Code event, matcher) | Command | What for | Timeout |
|---|---|---|---|
| `session-start` (SessionStart, every) | `"<python>" -I "<project>"/.boa/hooks/session_status.py` | status and resume protocol into the context | 8 |
| `pre-tool` (PreToolUse, shell, file and read tools) | `"<python>" -I "<project>"/.boa/hooks/guard_destructive.py` | safety layer with the project's protected-command rules; must be able to deny | 10 |
| `pre-tool` (PreToolUse, every) | `"<python>" -I "<project>"/.boa/hooks/pause_guard.py` | the pause signal; must be able to deny | 5 |
| `post-tool` of a `file-write` (PostToolUse, Write/Edit/MultiEdit) | `"<python>" -I "<project>"/.boa/hooks/memory_check.py` | memory lint after a write | 10 |
| `post-tool` of a `sub-agent` (PostToolUse, Agent) | `"<python>" -I "<project>"/.boa/hooks/agent_binding.py` | the agent→task binding the guards confine a sub-agent with (the result must carry the agent id) | 5 |
| `subagent-start` (SubagentStart, every) | `"<python>" -I "<project>"/.boa/hooks/memory_recall.py --session` | the memory reminder and every active lane's current memories into the starting sub-agent, where the runtime injects context there (it reads no event and prints plain text: your adapter passes that text on as the verdict's `context`; the agent's own task is bound only after it starts, so its brief carries that task's memories; the runtime caps the context a hook injects (the profiles state each cap), and above it the agent sees only a preview, so name the active tasks as arguments when the lanes' memories outgrow it) | 10 |
| `post-tool-failure` (PostToolUseFailure, every) | `"<python>" -I "<project>"/.boa/hooks/memory_recall.py` | matching lessons on an error | 10 |
| `subagent-stop` (SubagentStop, every) | `"<python>" -I "<project>"/.boa/hooks/subagent_stop.py` | **report capture** into the lane journal, and the pause capture | 10 |
| `stop` of the lead (Stop, every) | `"<python>" -I "<project>"/.boa/hooks/lead_stop.py` | resume file at a pause | 30 |
| `pre-compact` (PreCompact, every) | `"<project>"/.context-gate/hooks/precompact.sh` | transcript snapshot (its own instructions) | 60 |

**The guards fail closed, and so must their wiring** (`references/safety.md`). A guard prints a neutral verdict
(`{"decision": "deny", ...}`) or nothing; the command you register for it refuses the call on a `deny` verdict, on a
non-zero exit, on output that is not a verdict and on a timeout: never `|| true` or any equivalent that turns a broken
guard into "allow" (the inventory's `|| true` belongs to the loggers only, whose failures must never stop the
session; in Claude Code exit 2 is the refusal). Run each guard under your adapter's own timeout (10 s for `guard_destructive.py`, 5 s for
`pause_guard.py`) and set the runtime's hook timeout above it, since a runtime-level timeout does not refuse the call
in every runtime; a guard answers within its watchdog (8.5 s, 3.5 s), refusing at once past it, and its backstop ends it 1 s after
the watchdog. Pass a guard only the fields it reads (the table of `references/safety.md`), never a written file's
content: an event over 4 MiB is refused.
**Upgrading BOA:** after a `boa install` of a newer package, unwire from your runtime's wiring (another runtime's only
with the user's explicit yes) the hooks of tools that are no longer shipped
(compare your runtime's registrations with the inventory above) and remove old copies of BOA's git hooks from
`.git/hooks` (the whole procedure: `docs/02-install-and-wiring.md` "Re-installing and upgrading").

**Report capture.** At `subagent-stop`, `subagent_stop.py` saves the stopping agent's final report verbatim into the
lane's journal (`<lead dir>/lanes/<task>.md`, through `lane_journal.py`), so the lead reads it whatever happens to the
session, and adds the pause capture (the agent's resume file) while the project is paused. What your wiring puts in
the neutral event at that event: the agent's id (`agent_id`), its role (`agent_type`, the agent file's name), its
brief (`prompt`, where the task id is read, or `task` itself when the wiring knows it), the text of its final message
(`last_message`, the report text, the same field for every runtime; from the transcript when the text is not in the
payload), the transcript's path if the runtime keeps one (`transcript_path`), the session id and the working
directory. The lead's stop maps onto `stop` without `agent_id`; a session start onto `session-start`. Read what
your runtime really delivers (its hook reference, then a harmless trial), and wire the lead's stop and the session
status the same way. Where the final message is not in the stop payload, look for the event or tool that carries it.

**Where the runtime lacks one of these** (no sub-agents, no commands, no hooks, a hook that cannot deny, no
sub-agent event): decide the closest faithful equivalent under your capability self-assessment and declare it, never
fake it. Examples: no sub-agents: one agent plays the roles in sequence with a fresh context per role, or the lead
starts each role as a separate session given the agent file as its prompt; no commands: the user asks for the
command by name and you follow `.boa/commands/<name>.md`; no sub-agent-stop event: the sub-agent writes its report to
the lane journal itself as its last step (a rule in the brief) and the lead checks it; no pre-tool hook that denies:
the guards are not enforced, so say so and keep their rules as rules in `AGENTS.md`. When the right substitute is not
clear, ask the user, one question with options and your recommendation.

**Record what you wired**: in the capabilities record (what each feature is wired to, each substitute, each part not
enforced), in the handbook (where the runtime's agents, commands and hook configuration live, so a later session finds
them) and in the wiring list used for uninstall.

**Your runtime only; runtimes coexist.** A project may be worked on by more than one runtime: a pause in one is
resumed in another (`references/pause-resume.md` "Resume, step by step"), or a second runtime joins. Wiring a runtime,
at bootstrap, at a resume or at any time, does only what that runtime needs, nothing extra, and never modifies, moves,
regenerates or removes another runtime's wiring (its hooks, agents, commands, settings or skill copies) unless the
user explicitly asks, even when it looks stale or duplicated: report what you found and leave it alone. Each runtime
gets its own line in the capabilities record (where its wiring lives, what it cannot enforce). A partial net, no new
code: add the other runtimes' top-level wiring names (their settings directories, instruction files and skill
folders, as the capabilities record lists them) to `BOA_RUNTIME_CONFIG` next to your own. The guard then refuses
shell writes and deletions of those names in the main checkout, and only that. Declared limits: it does not judge git
verbs on them (`git rm`, `git mv`, `git checkout --`, `git restore`, `git stash`, `git reset`); it does not cover the
same names in a lane worktree, whose commits reach the main branch at the merge; it does not refuse the lead's own
file-editing tools (the lead needs them for its own wiring); and it takes top-level names only (a name holding `/`
is dropped, so wiring nested in a shared directory is kept by discipline alone). Everywhere else the rule is
discipline, with one cheap check where it bites: the reviewer flags a diff that touches another runtime's wiring
without the user's recorded yes. Another runtime's renderings that drift from their `.boa/` source are reported to
the user and recorded as an open item, never re-generated without the user's yes.
Before a runtime's wiring exists no hook of it runs: an agent new to the project reaches the discipline only through
`AGENTS.md`'s read order, which routes a paused project to the resume procedure and a new runtime to its wiring.
A declared limit: runtimes take turns, they never work on the project at the same time (BOA keeps one lead and one
scratch root per project: `BOA_SCRATCH_ROOT` and `BOA_SCRATCH_GLOB` hold the runtime that works now, set again when
another one takes over); resuming in one runtime after another has paused is supported.

## Claude Code

- Files (instruction files verified 2026-11-16 on the official memory page, section "AGENTS.md"): `AGENTS.md`, read
  natively from v2.1.277 when no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` is in the working directory or
  above it, so BOA creates no `CLAUDE.md`. Any of those three takes precedence and stops the native reading: then
  (and in a session where native reading is unavailable: a version before v2.1.277, the built-in plug-in disabled,
  some first sessions after an upgrade from v2.1.276 or earlier) the existing file gets a marked block with the
  import `@AGENTS.md`. Warn the user that adding a personal `CLAUDE.local.md` stops `AGENTS.md` from loading unless
  the user-level setting "Project instructions" is `claude-md-and-agents-md`. Also `.claude/agents/*.md` (frontmatter `model`, `effort`, tools),
  `.claude/commands/*.md`, `.claude/skills/<name>/SKILL.md`, `.claude/settings.json` (hooks, permissions;
  `.claude/settings.local.json` is personal and git-excluded).
- Hooks: PreToolUse (deny with `permissionDecision: deny` + reason), PostToolUse, PostToolUseFailure,
  PermissionRequest, PermissionDenied, SessionStart (can inject `additionalContext`), SessionEnd, SubagentStart
  (can inject `additionalContext` into the starting sub-agent; verified 2026-11-18 in the hooks reference for the
  installed 2.1.327: it cannot block; the text is added before the agent's first prompt; plain stdout is NOT added
  at this event, so the adapter returns JSON; it also runs when a sub-agent is resumed, and re-injects only after a
  compaction discarded the first copy; the context a hook injects is capped at 10,000 characters, measured per string with no setting to raise it: above it the text goes to a file and the agent sees the path with a preview of the first 2,000 characters only), SubagentStop, Stop, PreCompact. The hook payload carries `agent_id` inside
  a sub-agent and inside an in-process agent-team teammate; `agent_type` also appears in a session started with `--agent`. The wiring and the guard tell
  the lead from a sub-agent by `agent_id` only (a teammate is therefore treated as a sub-agent; a sub-lead runs as a
  sub-agent, never as a peer session, 09 §28).
- Event mapping to the neutral contract: SessionStart → `session-start`, SessionEnd → `session-end`,
  SubagentStart → `subagent-start`, SubagentStop → `subagent-stop`, Stop → `stop`, PreToolUse → `pre-tool`,
  PostToolUse → `post-tool`, PostToolUseFailure → `post-tool-failure`, PermissionDenied → `permission-denied`,
  UserPromptSubmit → `prompt`. Tool kinds: the agent-spawning tool (Task/Agent) → `sub-agent`, Bash, Monitor and
  PowerShell (each runs a shell command in `tool_input.command`; verified in 2.1.325) → `shell`,
  Write/Edit/MultiEdit/NotebookEdit → `file-write`, Read/Grep/Glob → `file-read`, SubagentHandback (a sub-agent's
  report hand-back in auto mode) → `report`, anything else → `other`. Fields:
  `agent_id`, `agent_type`, `session_id`, `cwd` as given; `tool_input` from the payload; the spawned agent's id,
  status and token count from `tool_response`; at SubagentStop `last_assistant_message` → `last_message` (the
  report text) and `agent_transcript_path` → `transcript_path`; a sub-agent's brief and final report from its
  transcript when the payload lacks them. Verdicts: `deny` → `hookSpecificOutput.permissionDecision: "deny"` with the reason;
  `context` → `hookSpecificOutput.additionalContext`, except on `Stop` and `SubagentStop`: there the field is
  accepted (verified in 2.1.325, hooks reference) and is reported to keep the agent running so it can act on it
  (stated by the reference, not verified in the binary), so map `context` → `systemMessage` there; `block` → `{"decision": "block",
  "reason": …}`; `message` → `systemMessage`.
  Your adapter (BOA ships none; verified on 2.1.325): a sub-agent's transcript is JSON lines, one record per line:
  split it on the newline byte and decode each line (a text splitter that also breaks at U+2028, U+2029 or U+0085
  inside a string loses records); a resume or a message of the lead to a running sub-agent is a later user record
  marked `isMeta: true` with `origin.kind: "coordinator"`, and starts a new run once assistant activity follows it,
  while a background task's completion is also an `isMeta` user record (`origin.kind: "task-notification"`) and starts
  no run (both seen in 2.1.325 transcripts): start a run only at the lead's records, take the task id from the first
  brief (a resume continues the same task), and take the hand-back and the report of a stop from the CURRENT run, never
  an earlier run's; the guards judge `pre-tool` events only, and nothing the
  adapter runs on `Stop` or `SubagentStop` exits 2 (there exit 2 keeps the agent working, and a loop follows). PreCompact feeds the context-gate (its own instructions), PermissionRequest the
  permission log. Verify the event and field names in the installed version's hook documentation.
- Config directory: `.claude/` in the project (and `~/.claude/` for the user); with the instruction file:
  `BOA_RUNTIME_CONFIG='.claude CLAUDE.md'`. Writes under `.claude/` ask the user
  for permission even when the allow-list covers the command: before a lane edits hooks or settings there, tell the
  user prompts will come and keep the edits to one file per command.
- Scratch root: the session's temporary directory is shown to the agent (the "scratchpad directory" of the session);
  it lies under a per-project directory in the system temp dir whose name the runtime derives from the project path
  (characters outside `[A-Za-z0-9]` replaced by `-`, long names shortened) — read the path, never derive it. Set
  `BOA_SCRATCH_ROOT` to the per-project directory (the parent of the session directories) and `BOA_SCRATCH_GLOB` to
  `*/scratchpad/*`.
- Private memory: an auto-memory directory per project under `~/.claude/projects/`; never used for project memory
  (the guard knows no such directory: the lead edits or retires those files with its file tools).
- Project directory: the hooks get it as `$CLAUDE_PROJECT_DIR`; BOA's hooks never need it (each finds its project
  from where it is installed), so a wiring may use it only to build the hook command's path.
- **Prompt-cache TTL** (verified in 2.1.322, settings schema and resolver): settings `promptCacheTtl` (main
  conversation) and `subagentPromptCacheTtl` (sub-agents, workflows, background and helper requests), values
  `"5m"` or `"1h"`. Resolution, first match wins: `FORCE_PROMPT_CACHING_5M` → 5m; the environment variables
  `CLAUDE_CODE_PROMPT_CACHE_TTL` / `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`; the merged setting (managed > local >
  project > user); for a sub-agent an agent-level override; `ENABLE_PROMPT_CACHING_1H=1` → 1h; otherwise
  automatic: the main conversation gets 1 hour on a Claude subscription within its usage limits and 5 minutes on
  an API key or a cloud provider, sub-agents get 5 minutes. 1-hour cache writes cost more than 5-minute writes;
  reads are cheap either way.
  Both settings re-verified in 2.1.325 (settings reference).
  When wiring, the agent sets `subagentPromptCacheTtl: "1h"` in the project's `.claude/settings.json` and
  `promptCacheTtl: "1h"` only when the user agrees; it never writes user-level settings without asking, and it
  checks the effective value (environment, local settings, a managed policy may keep a lower one) and tells the
  user the exact change to make.
- Agent usage reporting: the result of a finished sub-agent call carries a run total of tokens (`totalTokens`, seen in
  2.1.325; verify), not a context size; no current context size is known to BOA: verify. Context window per model:
  verify in the model documentation.
- Resuming an agent (AGENTS.md: the same agent per role and task): `SendMessage` to its agent id.
- Wiring: no `CLAUDE.md` of BOA's own (only a marked block with the import `@AGENTS.md` in an existing `CLAUDE.md`,
  `.claude/CLAUDE.md` or `CLAUDE.local.md`, or where native reading is unavailable), the agents and
  commands into `.claude/agents/` and `.claude/commands/` (never over a project file of the same name), and BOA's
  hooks (the inventory above) and the cleanup allowlist (below) into `.claude/settings.json` (append BOA's hook
  groups and permission entries, keep the project's own).
- Self-wiring (verified 2026-11-15 in the official Claude Code docs, sub-agents, hooks and skills pages):
  - agents: `.claude/agents/<name>.md`, the same Markdown with YAML header; `name`, `description`, `model`, `effort`
    and `tools` (a comma-separated list; omitted = every tool) map one to one, the body is the system prompt
    (re-verified in 2.1.325: `model` takes `opus`, `sonnet`, `haiku`, `fable`, a full model id or `inherit`); the
    neutral capabilities become `file-read` → `Read, Grep, Glob`, `file-write` → `Write, Edit` (plus
    `NotebookEdit` where notebooks are edited), `shell` → `Bash`, `web` → `WebSearch, WebFetch`; the neutral
    `arguments` becomes `argument-hint` and `<arguments>` becomes `$ARGUMENTS`; a
    sub-agent can start sub-agents of its own, up to three layers below the main conversation by default; a server
    setting may change it (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`; verified in 2.1.325, sub-agents page), so a
    sub-lead can run its lanes where the depth allows it;
  - commands: `.claude/commands/<name>.md` (`description`, `argument-hint`; `$ARGUMENTS`, `$1`); they keep working
    next to the newer form, a skill `.claude/skills/<name>/SKILL.md`;
  - hooks: the `hooks` object of `.claude/settings.json`: event, then groups of `{matcher, hooks: [{type: "command",
    command, timeout}]}` (timeout in seconds), the shape of the inventory above;
  - hook command forms and failures (verified in 2.1.325 in the official hooks reference and in the installed
    binary's own messages): an entry with `args` runs in exec form, `command` the executable and each `args` element
    one argument, no shell, `${CLAUDE_PROJECT_DIR}` substituted in each (a project path with spaces needs no quoting; on
    Windows `command` must be a real executable, not a `.cmd`); without `args` the `command` string goes to a shell.
    `"onFailure": "block"` (from 2.1.295) makes a hook that cannot start, exits with a code other than 0 or 2, prints
    invalid JSON or times out refuse the action as exit 2 does (a PreToolUse call is blocked, a PermissionRequest
    denied); without it any such failure, a timeout included, lets the call go ahead. It has no effect on `Stop`,
    `SubagentStop`, `TaskCompleted` and `TeammateIdle` hooks or on `async`/`asyncRewake` hooks, and an older version
    ignores it silently; separately, with `CLAUDE_CODE_RESTRICT_PERSONAL_CONFIG` set, a failing hook of the user's own
    settings blocks whatever it says. A guard's entry therefore sets `onFailure: "block"` and its wrapper still
    refuses on its own (a deny verdict as `permissionDecision: "deny"` with exit 0, or exit 2, on a deny, a crash or a
    timeout of the guard), so it stays fail-closed on a version without the field;
    edits to hooks in a settings file are picked up while a session runs, so wiring that must not act yet stays inert
    until what it calls is installed;
  - report capture: the `SubagentStop` payload carries `agent_id`, `agent_type`, `agent_transcript_path` and
    `last_assistant_message` (the final text); the lead's `Stop` payload has no `agent_id`. From v2.1.271 a sub-agent
    running in auto mode delivers its report through the `SubagentHandback` tool, and then `last_assistant_message`
    is not the report: also register a `PostToolUse` hook with matcher `SubagentHandback` and read
    `tool_input.message` (re-verified in 2.1.325; `SubagentStop` carries no brief: read it from the first line of
    `agent_transcript_path`). Reading the hand-back from the transcript instead (an assistant `tool_use` named
    `SubagentHandback`) is assumed, not verified: no local transcript holds one.
- Cannot: hooks do not stop an agent in the middle of a long tool call (a pause is seen at its next tool call);
  the guard is a net, not a sandbox (it fails closed: a deny verdict, a non-zero exit or a timeout must refuse the
  call; in Claude Code the guard's command exits 2 for those, never `|| true`).

## Codex CLI

- Reads `AGENTS.md` (repository and global); BOA's entry works as is.
- Verified 2026-11-17 on Codex CLI 0.169.0 (`codex debug prompt-input`, which renders the prompt without a model
  call): a fresh agent of this runtime in a paused BOA project receives `AGENTS.md`'s read order, its routing
  paragraph included, before the user's first message, also when that message invokes the skill. It receives only
  the first 32 KiB of `AGENTS.md` (`project_doc_max_bytes`, default 32768): a full BOA block is cut from its section
  10 on. The project-level way, verified the same day on the same version: `project_doc_max_bytes = 65536` in the
  project's `.codex/config.toml` delivers the whole file once the project is trusted (`[projects."<project>"]
  trust_level = "trusted"` in the user's `~/.codex/config.toml`: a user-level setting, the user's to make); with no trust
  entry the project file is ignored and the cap stays 32 KiB. A project the user marked untrusted gets no `AGENTS.md`
  at all, so neither the routing nor any rule reaches the agent: tell the user to trust the project. Where the project
  layer cannot be trusted, use the pointer block mode.
- Self-wiring (verified 2026-11-15 in the official Codex docs, hooks, subagents, skills and custom-prompts pages):
  - agents: TOML files `.codex/agents/<name>.toml` (project) or `~/.codex/agents/`; required `name`, `description`
    and `developer_instructions` (the body goes there, as a multi-line string); optional `model` and
    `model_reasoning_effort`, which map from the neutral `model` and `effort` (use an effort the model supports).
    There is no `tools` field: tools, sandbox and approvals are inherited from the parent session, and only feature
    keys can switch a capability off; say in the capabilities record that a role's tool limits (a read-only reviewer)
    rest on its contract and on the guard. Agents are spawned on request or by an `AGENTS.md` or skill instruction,
    so the lead's brief says "spawn the agent `builder`";
  - commands: skills, `.agents/skills/<name>/SKILL.md` with `name` and `description` (the command body is the skill
    body), invoked by `$name` or `/skills`; check how arguments reach a skill. Custom prompts
    (`~/.codex/prompts/<name>.md`, `/prompts:<name>`) are deprecated and live in the user's home, not the project;
  - hooks: `<repo>/.codex/hooks.json` or `[hooks]` tables in `<repo>/.codex/config.toml`, the same three levels as
    the inventory above (event, matcher group, handlers `{type: "command", command, timeout, statusMessage}`;
    timeout in seconds). Project hooks load only when the project's `.codex/` layer is trusted, and each hook must be
    reviewed and trusted by the user in `/hooks` before it runs: tell the user, and verify they ran. Events:
    `SessionStart`, `SessionEnd`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `SubagentStart`,
    `SubagentStop`, `Stop`, `UserPromptSubmit`. Neutral mapping: the same names as in the Claude Code mapping above
    (`SessionStart` to `session-start`, `PreToolUse` to `pre-tool`, ...); tool kinds: `Bash` is `shell`,
    `apply_patch` (matchable as `Edit` or `Write`) is `file-write`, MCP tools are `other`. A deny is
    `hookSpecificOutput.permissionDecision: "deny"` with a reason, as in Claude Code. `Stop` and `SubagentStop` expect
    JSON on stdout (never plain text). `SubagentStart` (matcher on `agent_type`; payload `agent_id`, `agent_type`)
    adds plain stdout, or `hookSpecificOutput.additionalContext`, to the starting sub-agent as developer context and
    cannot stop it (checked 2026-11-18 in the official hooks page; installed 0.169.0, not yet run in a session: verify
    with a harmless trial before relying on it). The context a hook adds is capped at about 2,500 tokens by default, per handler, set by `additionalContextLimit` on the handler (a positive number, or 0 for no cap): above it the full text is saved to a file and the agent sees only a head-and-tail preview with the path. The docs call tool hooks a guardrail, not a complete enforcement
    boundary;
  - report capture: `SubagentStop` delivers `agent_id`, `agent_type`, `agent_transcript_path`,
    `last_assistant_message`; `Stop` (the main thread) delivers `last_assistant_message` and no `agent_id`;
  - cannot (verify in the installed version): the `PreToolUse` payload documents no `agent_id`, so a tool hook cannot
    tell the lead from a sub-agent by the payload; the lane confinement of the guards then rests on another signal
    you provide (the working directory of the lane's worktree, or an environment variable set for the role), or is
    declared not enforced.
- Config directory: `.codex/` in the project (loaded only when the user trusts the project layer) and `~/.codex/` for
  the user; each project hook must be trusted in `/hooks` before it runs (above). Verify in the installed version
  whether writes there ask the user.
- Prompt-cache TTL: unknown, verify (caching is automatic on the provider side; no TTL setting known to BOA).
- Installing, updating and removing the skill (verified with Codex CLI 0.169.0 on 2026-11-17, in a throwaway project
  and home, against the official skills and plug-in pages; check the latest official documentation and the installed
  version before use, OR-63):
  - check what Codex loads without a model call: `codex debug prompt-input` prints the prompt the model would get, as
    JSON; its "Available skills" list names `build-on-autopilot` with the path of its `SKILL.md`. A one-shot session
    (`codex exec "Without running any command or reading any file, list only the names of the skills available to
    you in this session, one per line."`, with the cheapest model and low effort) lists the same names. Both also list
    `context-gate`, the package's nested skill (`context-gate/SKILL.md`);
  - the skill folder: put the package (the unpacked archive, or a clone checked out at the release tag:
    `git clone --branch vX.Y.Z <repository URL> .agents/skills/build-on-autopilot`) in `.agents/skills/` or
    `~/.agents/skills/`. Update: through the folder's channel ("Getting the skill into a runtime" above; for a clone,
    `git -C <skill> fetch --tags`, then `git -C <skill> checkout vX.Y.Z`); a new session loads the new version, and
    the docs say to restart Codex when an open session does not. Uninstall: delete the folder. Two folders holding a
    skill of the same name are both loaded, never merged: never leave a second copy in a skills folder;
  - `$skill-installer`: a skill bundled with Codex whose script downloads from GitHub only (no local path, no other
    host), with network access (in a sandbox: network on and write access to the skills folder). In a session:
    `$skill-installer install the skill at the root of the GitHub repository <owner>/boa, ref vX.Y.Z, as
    build-on-autopilot`; it runs the installer skill's GitHub install script with `--repo <owner>/boa --path .
    --ref vX.Y.Z --name build-on-autopilot` (the repository root needs `--name`: without it the script stops with
    "Invalid skill name").
    It installs into `$CODEX_HOME/skills/build-on-autopilot/` (`~/.codex/skills/` by default), a user folder the
    installed version loads although the skills page does not list it. It refuses a folder that exists
    ("Destination already exists"), so an update is: copy the folder to your scratch directory as the merge base,
    delete it, install the new tag. Uninstall: delete the folder;
  - the plug-in marketplace is no channel for BOA: `codex plugin marketplace add <owner>/boa` accepts the
    repository's marketplace file and `codex plugin add boa@boa` installs the plug-in, but Codex looks for a
    plug-in's skills under its `skills/` folder and the package's `SKILL.md` sits at its root, so the skill is not
    loaded (undo with `codex plugin remove boa@boa`, then `codex plugin marketplace remove boa`).
- Agent usage reporting: unknown, verify. Context window per model: verify.

## Gemini CLI

- Reads `GEMINI.md` by default; set its context file name to `AGENTS.md` in the project settings
  (`.gemini/settings.json`) so it reads BOA's entry (verify the key name in the installed version).
- Self-wiring (verified 2026-11-15 in the official Gemini CLI docs, hooks, subagents and custom-commands pages):
  - agents: Markdown with a YAML header, `.gemini/agents/<name>.md` (project) or `~/.gemini/agents/`; `name` (lowercase
    letters, digits, hyphens, underscores; it is also the tool name), `description`, `tools` (a YAML list of Gemini
    tool names, `*` wildcards; omitted = all of the parent's; the names: "Tool names for the neutral tools" below),
    `model`, plus `temperature`, `max_turns`,
    `timeout_mins`; the body is the system prompt. The neutral `effort` has no field: drop it and say so. The main
    agent calls a sub-agent as a tool of the same name, or the user forces it with `@name`; check whether the
    installed version needs sub-agents switched on;
  - commands: TOML files `.gemini/commands/<name>.toml` with `prompt` (the command body) and `description`; the
    arguments are `{{args}}` (the neutral `<arguments>` becomes it); a subdirectory makes a namespaced command (`git/fix.toml` is `/git:fix`); reload with
    `/commands reload`;
  - hooks: the `hooks` object of `.gemini/settings.json` (project; also `~/.gemini/settings.json`): event, then
    groups of `{matcher, sequential, hooks: [{type: "command", command, name, timeout}]}`, with the timeout in
    **milliseconds**. JSON on stdin (`session_id`, `transcript_path`, `cwd`, `hook_event_name`, `timestamp`), JSON
    only on stdout, exit 2 blocks with the stderr text as the reason. Events: `SessionStart`, `SessionEnd`,
    `BeforeAgent`, `AfterAgent`, `BeforeModel`, `AfterModel`, `BeforeToolSelection`, `BeforeTool`, `AfterTool`,
    `PreCompress`, `Notification`. Neutral mapping: `SessionStart` to `session-start`, `SessionEnd` to
    `session-end`, `BeforeTool` to `pre-tool` (deny: `decision: "deny"` with a `reason`; the matcher is a regex on the
    tool name, such as `run_shell_command`, `read_file`, `write_file`), `AfterTool` to `post-tool`, `AfterAgent` to
    `stop` (it carries `prompt_response`, the final text; a logger only: never deny or exit 2 on `AfterAgent`, which
    rejects the response and forces a retry, so a fail-closed wiring there would loop the lead), `PreCompress` to
    `pre-compact`;
  - report capture and what is missing: there is no sub-agent start or stop event, and no permission-request event
    (`Notification` is advisory). A sub-agent is a tool call of the main agent, so register `AfterTool` with the
    agent names as matcher and read the report from `tool_response`: this follows from the docs but is not an
    example in them, so confirm it with a harmless trial before relying on it; the pause capture falls back
    to the declared substitutes above.
- Tool names for the neutral tools (verified 2026-11-17 in Gemini CLI's official tool reference, `docs/tools/`
  of its repository on the main branch: `file-system.md`, `shell.md`, `web-search.md`, `web-fetch.md`; check them
  again at wiring, OR-63): `file-read` → `read_file`, `list_directory`, `glob`, `grep_search`; `file-write` →
  `write_file`, `replace`; `shell` → `run_shell_command`; `web` → `google_web_search`, `web_fetch`.
- Config directory: `.gemini/` in the project (`settings.json`, agents, commands) and `~/.gemini/` for the user;
  verify in the installed version whether writes there ask the user.
- Prompt-cache TTL: unknown, verify (provider-side implicit caching; no TTL setting known to BOA).
- Installing, updating and removing the skill (verified with Gemini CLI 0.68.0 on 2026-11-17, in a throwaway project
  and home, against the official skills and trusted-folders pages of its repository; check the latest official
  documentation and the installed version before use, OR-63). None of these commands needs a login:
  - `gemini skills install <source> --scope user|workspace --consent` (`user`, the default, writes
    `~/.gemini/skills/`; `workspace` writes `.gemini/skills/`; `--consent` skips the confirmation; `--path <sub-path>`
    for a sub-folder of a git source). The source is a local directory, a `.skill` zip file or a git URL
    (`https://`, `http://` or `git@`; a `file://` URL is read as a relative local path and fails with "No valid
    skills found"). A git URL is cloned at the head of
    its default branch, with no way to pin a tag: for a release, clone it at the tag
    (`git clone --branch vX.Y.Z <repository URL> <dir>`) and install from `<dir>`. The install copies every skill it
    finds (each `SKILL.md`): the package gives `build-on-autopilot` (the whole package, a clone's `.git` directory
    included) and a second, separate copy of its nested `context-gate`;
  - `gemini skills link <dir> --scope user|workspace --consent`: a symbolic link instead of a copy, so the skill
    follows the directory (`git -C <dir> checkout vX.Y.Z` is the whole update);
  - `gemini skills list` shows each skill with `[Enabled]` or `[Disabled]` and its location. Workspace skills load
    only in a trusted folder: the installed version treated a new folder as untrusted (the trusted-folders page says
    folder trust is off by default) and printed "No skills discovered" there; trust it in the dialog or with
    `/permissions`, or, headless, with `GEMINI_CLI_TRUST_WORKSPACE=true` (`gemini skills list` refuses the
    session flag `--skip-trust`). User skills need no trust;
  - `gemini skills disable <name>` writes the name into `skills.disabled` of the workspace `.gemini/settings.json`
    (the installed default is `--scope workspace`; the skills page says the in-session `/skills disable` defaults to
    `user`); `gemini skills enable <name>` removes it from the workspace and the user lists;
  - update: copy the skill folder to your scratch directory as the merge base, then install again from the new
    release's directory: an existing folder of that name is deleted and copied again whole ("already exists.
    Overwriting..."), so a file the release dropped disappears. A linked skill needs only the checkout above;
  - uninstall: `gemini skills uninstall build-on-autopilot --scope <scope>`, then the same for `context-gate`; for a
    linked skill it removes the link and leaves the directory;
  - in a session (verified with Gemini CLI 0.68.0 on 2026-11-17, headless, `gemini -m <model> -p "<prompt>"` with an
    API key in `GEMINI_API_KEY` and the workspace trusted as above): the session lists `build-on-autopilot` and
    `context-gate` among its skills. In headless mode the default approval mode leaves `activate_skill` out of the
    session's tools ("Tool \"activate_skill\" not found", a model then reads `SKILL.md` with `read_file` instead).
    Allow that one tool through the policy engine (the official policy-engine page): a user policy file,
    `~/.gemini/policies/<any name>.toml`, holding `[[rule]]`, `toolName = "activate_skill"`, `decision = "allow"`,
    `priority = 100` (the page declares the workspace tier, `.gemini/policies/`, not working yet; `ask_user` counts
    as `deny` in a headless session). The call then activates the skill ("Skill **build-on-autopilot** activated.
    Resources loaded from `<skills folder>/build-on-autopilot`") and returns its instructions. Fallback in this
    version: the flag `--allowed-tools activate_skill`, which works too but is deprecated in favour of the policy
    engine (the installed version warns). The interactive consent prompt: not run (headless only).
- Agent usage reporting: unknown, verify. Context window per model: verify.

## OpenCode

- Reads `AGENTS.md`.
- Self-wiring (verified 2026-11-15 in the official OpenCode docs, agents, commands and plugins pages; the docs carry
  two versions, V1 and V2: check which the installed one is, the names differ):
  - agents: Markdown with a YAML header, `.opencode/agents/<name>.md` (project) or `~/.config/opencode/agents/`
    (the file name is the agent id); `description`, `mode: subagent`, `model` (`provider/model`, optionally
    `#variant`), and `permissions`, an ordered list of `{action, resource, effect}` rules (`effect`: allow, ask,
    deny; the last match wins; actions such as `edit`, `shell`, `read`, `webfetch`, `subagent`); the body is the
    system prompt. The neutral `tools` becomes permission rules (deny what the list leaves out; the actions: "Tool
    names for the neutral tools" below); the neutral
    `effort` has no documented field, so use a model variant if the installed version defines one, else drop it
    and say so. In the older version the field is `permission` and tools are switched in a `tools` map;
  - commands: Markdown `.opencode/commands/<name>.md` (project) or `~/.config/opencode/commands/`; header
    `description`, `agent`, `model`, `subagent`; the body is the template; `$ARGUMENTS`, `$1`, `$2` (the neutral `<arguments>` becomes
    `$ARGUMENTS`);
  - hooks: plugins, JS or TS, loaded from `.opencode/plugins/` or the `plugins` list of `opencode.json(c)`. In the
    current plugin API a server plugin registers `ctx.tool.hook("execute.before" | "execute.after", ...)`, session
    hooks and a permission hook, and can read the event stream with `ctx.event.subscribe`. The plugin is a thin
    wrapper you write for the project: it builds the neutral JSON event, runs BOA's hook command, and turns its
    answer back (deny, context, message); it holds no BOA logic;
  - not verified, check in the installed version and record the mapping: how a before-tool hook denies, and which
    event or hook marks the end of a sub-agent (its report) and the end of the main agent's turn; until then the
    sub-agent-stop and stop hooks are declared not wired and the report-journal substitute above applies.
- Tool names for the neutral tools (verified 2026-11-17 on OpenCode's official Tools and Permissions pages,
  opencode.ai/docs/tools and opencode.ai/docs/permissions, the V2 names; check them again at wiring, OR-63): the
  permission actions are `file-read` → `read`, `glob`, `grep`; `file-write` → `edit` (it covers the `edit`, `write`
  and `patch` tools); `shell` → `shell`; `web` → `webfetch`, `websearch`. In V1 the shell action is `bash` (and the
  sub-agent action `task`).
- Config directory: `.opencode/` and `opencode.json(c)` in the project, `~/.config/opencode/` for the user; verify in
  the installed version whether writes there ask the user.
- Event mapping to the neutral contract: whatever the plugin API delivers, mapped by your plugin: a before-tool hook
  to `pre-tool`, an after-tool hook to `post-tool` (a failed call to `post-tool-failure`), session events to
  `session-start` / `stop`; the tool kinds by tool name (shell, edit/write, read), the sub-agent tool to `sub-agent`.
- Prompt-cache TTL: unknown, verify (depends on the configured provider).
- Agent usage reporting: unknown, verify. Context window per model: verify.

## Any other agent (editors, other CLIs)

Most read `AGENTS.md`. Without hooks: run the status screen and the checks by hand as `AGENTS.md`
says, keep the guard's rules as rules, and tell the user that nothing enforces them. Without sub-agents: one
agent plays the roles in sequence, with a fresh context per role where possible (the adversarial review loses
much of its value when the builder reviews its own work: say so).

Prompt-cache TTL for any runtime not listed: unknown — verify. Agent usage reporting and context window per model
for any runtime not listed: unknown — verify.

## The cleanup allowlist

So that the user can run without removal prompts (OR-11), the agent adds these shapes to its runtime's permission
allow and deny lists (Claude Code spelling; `<scratch>` = `BOA_SCRATCH_ROOT` without a trailing slash, `<wt>` = the
lane worktrees dir as an absolute path, `<branch glob>` = `BOA_BRANCH_GRAMMAR` with every token as `*`, `<projects>` =
the parent of the project; where a parent is a symlink, also each rule in its physical form). Allow: `Bash(rm -rf
<scratch>/*)`, `Bash(rm -fr <scratch>/*)`, `Bash(rm -r <scratch>/*)`, `Bash(rm -f <scratch>/*)`, `Bash(rm
<scratch>/*)`, the same four `rm -rf|-fr|-r|-f` forms under `<wt>/*`, `Bash(git worktree remove *)`, `Bash(git
worktree prune*)`, `Bash(git branch -D <branch glob>)`, `Bash(git push <remote> --delete <branch glob>)`, `Bash(docker
rm -f <name prefix>*)`, `Bash(docker rm <name prefix>*)`, `Bash(docker network rm <name prefix>*)`, `Bash(docker volume
rm <name prefix>*)` (the container rules only where the project uses containers). Deny: `Bash(rm *..*)`, `Bash(rm -rf
/)`, `Bash(rm -fr /)`, `Bash(rm -r /)`, `Bash(rm -rf ~)`, `Bash(rm -rf ~/)`, `Bash(rm -rf /tmp)`, `Bash(rm -rf /tmp/)`,
`Bash(rm -rf <projects>)`, `Bash(rm -rf <projects>/)`. Another runtime writes the same shapes in its own permission
format, or says it has none.
