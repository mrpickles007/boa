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

**Probe, never recall.** The facts below were verified where marked; runtimes change fast. Before relying on a
capability, check it in the installed version (its `--help`, its documentation, its settings schema) and record
the evidence in the decisions log. `BOA_RUNTIME=<claude-code|codex|gemini-cli|opencode|other>` in `.boa/config.env`
records the runtime you wire (the installer writes the same `.boa/` sources for every runtime).

## Getting the skill into a runtime

The package is one skill folder, `build-on-autopilot`: the release archive unpacked (it unpacks to `boa/`; rename the
folder) or a clone of the public repository `boa` (whose root is the skill). Where each runtime reads a skill folder
(verified 2026-11-16 on each runtime's official skills page; verify again in the installed version):

| Runtime | Skill folder (user level; project level) | Other channel | Invoked as |
|---|---|---|---|
| Claude Code | `~/.claude/skills/build-on-autopilot/`; `.claude/skills/build-on-autopilot/` | plug-in marketplace: the repository's `.claude-plugin/marketplace.json` lists the plug-in `boa` (the repository root, never the archive): `/plugin marketplace add <owner>/boa#v1.2.3` (pins the release tag; without `#<tag>` it follows the default branch), then `/plugin install boa@boa` | `/build-on-autopilot` (skill folder), `/boa:build-on-autopilot` (plug-in) |
| Codex CLI | `~/.agents/skills/build-on-autopilot/`; `.agents/skills/build-on-autopilot/` | the built-in `$skill-installer`, pointed at the repository | `$build-on-autopilot` or `/skills` |
| Gemini CLI | `~/.gemini/skills/build-on-autopilot/` or `~/.agents/skills/build-on-autopilot/`; `.gemini/skills/` or `.agents/skills/` | `gemini skills install <repository URL>` | its skill selection |
| OpenCode | `~/.config/opencode/skills/build-on-autopilot/` (it also reads `~/.agents/skills/` and `~/.claude/skills/`); `.opencode/skills/` | none | its skill selection |
| any other | the runtime's skills folder, if it has one | paste `KICKOFF.md` into the session | - |

The marketplace route installs the repository at the pinned tag; the repository, the archive and a skill folder hold
the same shipped files. A plug-in install prefixes the skill
with the plug-in name: users of that route start BOA with `/boa:build-on-autopilot <mode> [idea-file]` wherever the
documents say `/build-on-autopilot` (the marketplace syntax: the runtime's plug-in install page, verified 2026-11-16).

## The runtime profile (what you record for your runtime)

BOA's code knows no runtime: every runtime fact below is yours to read from the installed runtime and to write into
the project (the config and the capabilities record in `memory-bank/04-ARCHITECTURE.md` "Environment"), as a
project-wiring checklist item. For your runtime,
record:

- **config directory and its behaviour**: where the runtime keeps project and user settings, and what it does when
  an agent writes there (some runtimes ask the user for every write in their config directory, whatever the
  allow-list: warn the user before a lane edits it, keep those edits few). Pass the top-level names it uses in the
  project (its settings directory, its own instruction file) as `BOA_RUNTIME_CONFIG`: the guard then keeps every
  shell write off them and sub-agents away from them (until it is set, the guard knows no runtime file);
- **scratch root**: the temporary directory the runtime gives a session, and the directory above it that holds
  every session of this project. Read it from the runtime (the path it shows the session); never rebuild it from a
  rule you remember: runtimes derive it from the project path with their own character replacement and length
  limits, which change between versions. Pass it as `BOA_SCRATCH_ROOT` (absolute, at least two levels deep) and the
  layout of the task entries under it as `BOA_SCRATCH_GLOB` (e.g. `*/scratchpad/*` when each session has its own
  directory with a scratch directory inside; `*` when task entries sit directly under the root, the default);
- **private memory**: where the runtime keeps its own memory for the project, if any. It is never the project's
  memory (the memory bank is); say so in the capabilities record (04 "Environment") and keep the two apart;
- **hook events**: the mapping of the runtime's events and payload to the neutral event contract of BOA's hooks
  (`references/hook-contract.md`): which neutral events it can deliver, how a tool call is classed (`sub-agent`,
  `shell`, `file-write`, `file-read`, `other`), how a verdict maps back (deny, block, context, message), and the
  events it cannot deliver with the fallback that catches them later (a project check, a step of the lead's loop);
- **models and options**: the model list and the runtime options BOA relies on (below).

## What BOA needs from a runtime

| Need | Why |
|---|---|
| instructions file loaded every session | the constitution and the read order |
| sub-agents with their own model and effort | builder, reviewer, tester, integrator, analyzer, builder-mid |
| commands (or skills) | `run-project`, `pause-project`, `resume-project`, `close-project` (+ `run-task`, `sync-memory`) |
| pre-tool hook that can deny with a reason | the role-aware guard (with the project's protected-command rules), pause guard |
| session start/end, sub-agent start/stop, permission-request, pre-compaction, stop hooks | status injection, report journal, context-gate, pause capture (and the project's own clock and permission log, `references/project-wiring.md`) |
| a way to tell the lead from a sub-agent in a hook | the guard's lane confinement and lead-only override |
| prompt-cache TTL control | sub-agents wait on long runs; a short cache expires between their turns |

## Self-wire at bootstrap

The agent and command files BOA ships are runtime-neutral: a header of neutral metadata, then a body that is the
contract itself. At bootstrap (SKILL step 7) you convert them into your runtime's format. Nothing is converted for
you: BOA ships no runtime adapter. Every example below is an example; none is the default, and each is verified
against the runtime's official documentation at the date given in its section. For a runtime that is not listed, or
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
| `tools` | tool names as written (`Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob`, `WebSearch`, `WebFetch`), each naming a capability | not used | the runtime's tool names or permission rules; a runtime that cannot restrict tools per agent runs the role with the parent's tools and says so |
| `argument-hint` | not used | the arguments the command takes | the runtime's argument hint; `$ARGUMENTS`, `$1` in the body become its placeholders |

The body is copied unchanged as the agent's instructions or the command's prompt. Keep the BOA files in `.boa/` as the
source of truth and generate the runtime's files from them; a file the project already has is never overwritten.
Re-generate a runtime file in the same commit as its `.boa/` source changes, and check them against each other in the
project (a step of the project gate or a test): the handbook drift check covers `.boa/` only and knows no runtime.

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
**Upgrading BOA:** after a `boa install` of a newer package, unwire the hooks of tools that are no longer shipped
(compare your runtime's registrations with the inventory above) and remove old copies of BOA's git hooks from
`.git/hooks`.

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
  PermissionRequest, PermissionDenied, SessionStart (can inject `additionalContext`), SessionEnd, SubagentStart,
  SubagentStop, Stop, PreCompact. The hook payload carries `agent_id` inside a sub-agent and inside an in-process
  agent-team teammate; `agent_type` also appears in a session started with `--agent`. The wiring and the guard tell
  the lead from a sub-agent by `agent_id` only (a teammate is therefore treated as a sub-agent; a sub-lead runs as a
  sub-agent, never as a peer session, 09 §28).
- Event mapping to the neutral contract: SessionStart → `session-start`, SessionEnd → `session-end`,
  SubagentStart → `subagent-start`, SubagentStop → `subagent-stop`, Stop → `stop`, PreToolUse → `pre-tool`,
  PostToolUse → `post-tool`, PostToolUseFailure → `post-tool-failure`, PermissionDenied → `permission-denied`,
  UserPromptSubmit → `prompt`. Tool kinds: the agent-spawning tool (Task/Agent) → `sub-agent`, Bash → `shell`,
  Write/Edit/MultiEdit/NotebookEdit → `file-write`, Read/Grep/Glob → `file-read`, anything else → `other`. Fields:
  `agent_id`, `agent_type`, `session_id`, `cwd` as given; `tool_input` from the payload; the spawned agent's id,
  status and token count from `tool_response`; at SubagentStop `last_assistant_message` → `last_message` (the
  report text) and `agent_transcript_path` → `transcript_path`; a sub-agent's brief and final report from its
  transcript when the payload lacks them. Verdicts: `deny` → `hookSpecificOutput.permissionDecision: "deny"` with the reason;
  `context` → `hookSpecificOutput.additionalContext`; `block` → `{"decision": "block", "reason": …}`;
  `message` → `systemMessage`. PreCompact feeds the context-gate (its own instructions), PermissionRequest the
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
  When wiring, the agent sets `subagentPromptCacheTtl: "1h"` in the project's `.claude/settings.json` and
  `promptCacheTtl: "1h"` only when the user agrees; it never writes user-level settings without asking, and it
  checks the effective value (environment, local settings, a managed policy may keep a lower one) and tells the
  user the exact change to make.
- Resuming an agent (AGENTS.md: the same agent per role and task): `SendMessage` to its agent id.
- Wiring: no `CLAUDE.md` of BOA's own (only a marked block with the import `@AGENTS.md` in an existing `CLAUDE.md`,
  `.claude/CLAUDE.md` or `CLAUDE.local.md`, or where native reading is unavailable), the agents and
  commands into `.claude/agents/` and `.claude/commands/` (never over a project file of the same name), and BOA's
  hooks (the inventory above) and the cleanup allowlist (below) into `.claude/settings.json` (append BOA's hook
  groups and permission entries, keep the project's own).
- Self-wiring (verified 2026-11-15 in the official Claude Code docs, sub-agents, hooks and skills pages):
  - agents: `.claude/agents/<name>.md`, the same Markdown with YAML header; `name`, `description`, `model`, `effort`
    and `tools` (a comma-separated list; omitted = every tool) map one to one, the body is the system prompt;
  - commands: `.claude/commands/<name>.md` (`description`, `argument-hint`; `$ARGUMENTS`, `$1`); they keep working
    next to the newer form, a skill `.claude/skills/<name>/SKILL.md`;
  - hooks: the `hooks` object of `.claude/settings.json`: event, then groups of `{matcher, hooks: [{type: "command",
    command, timeout}]}` (timeout in seconds), the shape of the inventory above;
  - report capture: the `SubagentStop` payload carries `agent_id`, `agent_type`, `agent_transcript_path` and
    `last_assistant_message` (the final text); the lead's `Stop` payload has no `agent_id`. From v2.1.271 a sub-agent
    running in auto mode delivers its report through the `SubagentHandback` tool, and then `last_assistant_message`
    is not the report: also register a `PostToolUse` hook with matcher `SubagentHandback` and read
    `tool_input.message`.
- Cannot: hooks do not stop an agent in the middle of a long tool call (a pause is seen at its next tool call);
  the guard is a net, not a sandbox (it fails closed: a deny verdict, a non-zero exit or a timeout must refuse the
  call; in Claude Code the guard's command exits 2 for those, never `|| true`).

## Codex CLI

- Reads `AGENTS.md` (repository and global); BOA's entry works as is.
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
    JSON on stdout (never plain text). The docs call tool hooks a guardrail, not a complete enforcement boundary;
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

## Gemini CLI

- Reads `GEMINI.md` by default; set its context file name to `AGENTS.md` in the project settings
  (`.gemini/settings.json`) so it reads BOA's entry (verify the key name in the installed version).
- Self-wiring (verified 2026-11-15 in the official Gemini CLI docs, hooks, subagents and custom-commands pages):
  - agents: Markdown with a YAML header, `.gemini/agents/<name>.md` (project) or `~/.gemini/agents/`; `name` (lowercase
    letters, digits, hyphens, underscores; it is also the tool name), `description`, `tools` (a YAML list of Gemini
    tool names, `*` wildcards; omitted = all of the parent's), `model`, plus `temperature`, `max_turns`,
    `timeout_mins`; the body is the system prompt. The neutral `effort` has no field: drop it and say so. The main
    agent calls a sub-agent as a tool of the same name, or the user forces it with `@name`; check whether the
    installed version needs sub-agents switched on;
  - commands: TOML files `.gemini/commands/<name>.toml` with `prompt` (the command body) and `description`; the
    arguments are `{{args}}`; a subdirectory makes a namespaced command (`git/fix.toml` is `/git:fix`); reload with
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
- Config directory: `.gemini/` in the project (`settings.json`, agents, commands) and `~/.gemini/` for the user;
  verify in the installed version whether writes there ask the user.
- Prompt-cache TTL: unknown, verify (provider-side implicit caching; no TTL setting known to BOA).

## OpenCode

- Reads `AGENTS.md`.
- Self-wiring (verified 2026-11-15 in the official OpenCode docs, agents, commands and plugins pages; the docs carry
  two versions, V1 and V2: check which the installed one is, the names differ):
  - agents: Markdown with a YAML header, `.opencode/agents/<name>.md` (project) or `~/.config/opencode/agents/`
    (the file name is the agent id); `description`, `mode: subagent`, `model` (`provider/model`, optionally
    `#variant`), and `permissions`, an ordered list of `{action, resource, effect}` rules (`effect`: allow, ask,
    deny; the last match wins; actions such as `edit`, `shell`, `read`, `webfetch`, `subagent`); the body is the
    system prompt. The neutral `tools` becomes permission rules (deny what the list leaves out); the neutral
    `effort` has no documented field, so use a model variant if the installed version defines one, else drop it
    and say so. In the older version the field is `permission` and tools are switched in a `tools` map;
  - commands: Markdown `.opencode/commands/<name>.md` (project) or `~/.config/opencode/commands/`; header
    `description`, `agent`, `model`, `subagent`; the body is the template; `$ARGUMENTS`, `$1`, `$2`;
  - hooks: plugins, JS or TS, loaded from `.opencode/plugins/` or the `plugins` list of `opencode.json(c)`. In the
    current plugin API a server plugin registers `ctx.tool.hook("execute.before" | "execute.after", ...)`, session
    hooks and a permission hook, and can read the event stream with `ctx.event.subscribe`. The plugin is a thin
    wrapper you write for the project: it builds the neutral JSON event, runs BOA's hook command, and turns its
    answer back (deny, context, message); it holds no BOA logic;
  - not verified, check in the installed version and record the mapping: how a before-tool hook denies, and which
    event or hook marks the end of a sub-agent (its report) and the end of the main agent's turn; until then the
    sub-agent-stop and stop hooks are declared not wired and the report-journal substitute above applies.
- Config directory: `.opencode/` and `opencode.json(c)` in the project, `~/.config/opencode/` for the user; verify in
  the installed version whether writes there ask the user.
- Event mapping to the neutral contract: whatever the plugin API delivers, mapped by your plugin: a before-tool hook
  to `pre-tool`, an after-tool hook to `post-tool` (a failed call to `post-tool-failure`), session events to
  `session-start` / `stop`; the tool kinds by tool name (shell, edit/write, read), the sub-agent tool to `sub-agent`.
- Prompt-cache TTL: unknown, verify (depends on the configured provider).

## Any other agent (editors, other CLIs)

Most read `AGENTS.md`. Without hooks: run the status screen and the checks by hand as `AGENTS.md`
says, keep the guard's rules as rules, and tell the user that nothing enforces them. Without sub-agents: one
agent plays the roles in sequence, with a fresh context per role where possible (the adversarial review loses
much of its value when the builder reviews its own work: say so).

Prompt-cache TTL for any runtime not listed: unknown — verify.

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
