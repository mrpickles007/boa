# The hook contract (agent-agnostic hooks)

Every hook BOA ships keeps its logic in a runtime-neutral core: it reads ONE normalised event and returns ONE
normalised verdict. BOA ships no adapter for any runtime: the agent that installs BOA wires its own runtime's hooks
against this contract (the hook command turns the runtime's payload into the event and the verdict into the runtime's
output) — the hooks never change. The runtime profiles (`references/runtimes.md`) say, per runtime, which events it can
deliver.

## Calling a hook

Every hook entry point reads the neutral event (one JSON object) on stdin and prints the neutral verdict (one JSON
object) on stdout, only when the verdict says something: no output means decision `none`. Anything on stdin that is
not one JSON object is no event: the hook does nothing (a guard refuses instead, below).

| Hook (entry point) | Events it acts on | What it does | Verdict |
|---|---|---|---|
| `.boa/hooks/session_status.py` | session-start | — | `context`: resume protocol, status, memory block |
| `.boa/hooks/subagent_stop.py` | subagent-stop | journals the final report (`last_message`) into `<lead dir>/lanes/<task>.md`, the task from `prompt`; while paused also copies the agent's resume file and journals the pause | `message` when, paused, the resume file is missing |
| `.boa/hooks/lead_stop.py` | stop of the lead (no `agent_id`), while paused | renders `<lead dir>/RESUME-LEAD.md` | none |
| `.boa/hooks/memory_check.py` | post-tool of a `file-write` | lints the memory bank after a memory file is written; regenerates the memory-type tables after the types file is written | `block` with the findings; `context` after a regeneration |
| `.boa/hooks/memory_recall.py` | post-tool-failure | finds the memories for the error | `context` with the memories |
| `.boa/hooks/agent_binding.py` | post-tool of a `sub-agent` (the lead's spawn) | records the spawned agent (`result.agent_id`) and the task of its brief, which the guards read to confine it to its lane | none printed |
| `.boa/hooks/guard_destructive.py` | pre-tool of a `shell`, `file-write` or `file-read` call | judges the call against the safety rules (`references/safety.md`; the fields it reads are listed there) | `deny` with `reason` to refuse; nothing to allow |
| `.boa/hooks/pause_guard.py` | pre-tool of every tool kind, while `<lead dir>/PAUSE` exists | lets a paused sub-agent only save its state and end its turn (`references/pause-resume.md`) | `deny` with `reason` to refuse; nothing to allow |

`lane_journal.py` is the journal writer the sub-agent stop hook calls (and `--task` names the task an entry goes to):
wire `subagent_stop.py` only, never both on the same event. The safety hooks (the destructive-command guard and the
pause guard) are described with their own rules in `references/safety.md` and `references/pause-resume.md`.

**The guards fail closed.** A guard judges only `pre-tool` events (any other neutral event: no output). Everything
that stops it from judging refuses the call with a `deny` verdict naming the lead's logged escape, never "does
nothing": stdin that is not one JSON object or is over 4 MiB, an unknown `event` or `tool`, a `shell` event without a
string `tool_input.command`, a `file-write` event without `tool_input.file_path`, a field of the wrong type, a hook file
not installed in a checkout, a `.boa/config.env` line outside its grammar, an internal error, or no verdict within its
watchdog. The wiring refuses the call too when a guard exits non-zero, prints something that is not a verdict or
times out (`references/safety.md`).

Every other hook never fails the runtime: on any problem it exits 0. It prints nothing, except that the stop hooks never lose a
report silently: when `.boa/config.env` is unreadable (the line is named) or the journal cannot be written, the verdict's
`message` says the report was not captured (and, at the lead's stop, that RESUME-LEAD.md was not rendered).

## The neutral event

One JSON object; every field optional except `event`.

| Field | Meaning |
|---|---|
| `event` | `session-start`, `session-end`, `subagent-start`, `subagent-stop`, `stop`, `pre-tool`, `post-tool`, `post-tool-failure`, `permission-denied` (the runtime refused a call), `permission-request` (the runtime is about to ask the user to approve a call; no shipped hook acts on it, a project's permission log may), `prompt`; anything else: not handled (a guard refuses it) |
| `tool` | the tool kind of a `*-tool` event: `sub-agent`, `shell`, `file-write`, `file-read`, `other` |
| `tool_input` | object: `command` (shell), `file_path` (file-*: the file written or read), `path` (file-read: a directory searched), `glob` (file-read: a path pattern searched), `description`, `prompt`, `subagent_type`, `model` (sub-agent) |
| `tool_use_id` | the runtime's id of the tool call |
| `result` | object: `status` (`completed` ends a foreground run; any other value binds a background one), `agent_id` (the spawned agent), `tokens` (integer, when the runtime reports them) |
| `error`, `interrupted` | the error text of a `post-tool-failure`; `true` when the user cut it |
| `session_id`, `agent_id`, `agent_type` | the session; the agent that fires the event and its role (empty type: an internal agent of the runtime, ignored) |
| `model`, `source`, `reason` | the model named at a spawn; why a session started; why it ended |
| `cwd`, `prompt`, `last_message`, `stop_hook_active` | the working directory; the agent's brief (its first message: a sub-agent's task id is read from it when `task` is absent); its final report — the report text, one neutral field for every runtime (the lane journal saves it verbatim; report checks read it); `true` on a re-entered stop hook |
| `task`, `transcript_path` | the agent's task id (or `TRAIN-<n>`) when the wiring knows it (it wins over `prompt`); the agent's transcript, if the runtime keeps one (noted with the journal entry, never read by a hook) |

The wiring extracts every field from the runtime (its payload, its transcripts, its usage figures): no hook reads a
runtime's own formats.

## The neutral verdict

| Field | Meaning |
|---|---|
| `decision` | `none`, `allow`, `deny` (refuse a pre-tool call), `block` (tell the agent to act now) |
| `reason` | why (deny, block) |
| `context` | text added to the agent's context |
| `message` | a warning shown to the user |

## Wiring a runtime

1. Map the runtime's hook events to the neutral events it can deliver; list the ones it cannot, with the fallback that
   catches them later (a project check, a step of the lead's loop), in its runtime profile (`references/runtimes.md`)
   — never fake an event.
2. For each event, build the neutral JSON from the runtime's payload and pipe it to the hook entry point
   (`<BOA_PYTHON> -I .boa/hooks/<hook>.py`): the event name, the tool kind (the runtime's sub-agent tool is
   `sub-agent`, its shell tool `shell`, its file-writing tools `file-write`, its file-reading and search tools
   `file-read`), the spawned agent's id and status from the tool's result, the agent's brief and final report (from
   the payload, or from the agent's transcript when the payload lacks them). A payload that may be large or cut short
   is the wiring's to read; the hook only ever gets the event.
3. Map the verdict back: `context` to the runtime's way of adding context, `message` to a user warning, `deny` to a
   refusal of the tool call, `block` to the runtime's "tell the agent" channel; no output = nothing.
4. Check it: `printf '{"event":"session-start"}' | python3 -I .boa/hooks/session_status.py` prints a verdict whose
   `context` starts with "Resume protocol:"; `.boa/bin/lead-status.sh --guards` prints no GUARD DOWN line (it sends
   every hook a harmless neutral pre-tool event, shell `true`, and reports one that crashes or hangs).
