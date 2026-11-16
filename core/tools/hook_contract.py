"""BOA hook contract: every hook reads one neutral event and answers with one neutral verdict.

Purpose:  keep every hook runtime-neutral: a hook reads ONE normalised event (JSON on stdin) and answers with ONE
          normalised verdict (JSON on stdout); the hooks know no runtime.
When:     imported by every BOA hook (session status, sub-agent stop and its lane journal, lead stop, memory check and
          recall, agent binding); the agent of each runtime maps its own hook events onto this contract when it wires
          the hooks (references/runtimes.md, per runtime).
Wire:     the runtime's hook command turns the runtime's payload into the neutral event, pipes it to the hook, and maps
          the verdict back (references/hook-contract.md describes how, with a worked runtime).
Verify:   `printf '{"event":"session-start"}' | python3 -I .boa/hooks/session_status.py` prints a verdict whose
          `context` starts with "Resume protocol:".
Outputs:  none of its own.
Limits:   only the events below; an event a runtime cannot deliver is declared in its profile with the fallback that
          catches it later (a project check), never faked; an event that is not one JSON object is ignored.

Neutral event (one JSON object; every field optional except `event`):
  event            session-start | session-end | subagent-start | subagent-stop | stop | pre-tool | post-tool |
                   post-tool-failure | permission-denied | permission-request | prompt   (anything else: not
                   handled, the hook does nothing; the guards, which read hooks/hook_config.py, refuse it)
  tool             sub-agent | shell | file-write | file-read | other   (the tool kind of a *-tool event)
  tool_input       object: command (shell), file_path (file-*), path / glob (file-read: a directory / a path
                   pattern searched), description / prompt / subagent_type / model
                   (sub-agent)
  tool_use_id      the runtime's id of the tool call
  result           object: status (`completed` ends a foreground run; any other value binds a background one),
                   agent_id (the spawned agent), tokens (integer, when the runtime reports them)
  error            the error text of a post-tool-failure; interrupted (boolean): it was cut by the user
  session_id, agent_id, agent_type (the agent's role; empty: an internal agent of the runtime, ignored), model,
  source (why a session started), reason (why it ended), cwd, prompt (the agent's brief, its first message: a
  sub-agent's task id is read from it when `task` is absent), last_message (the agent's final report: the report
  text, one field for every runtime), task (the agent's task id or TRAIN-<n>, when the wiring knows it),
  transcript_path (the agent's transcript, if the runtime keeps one: noted with the journal entry, never read),
  stop_hook_active (a re-entered stop hook). The wiring extracts these from the runtime (its payload, its
  transcripts, its usage figures): no hook reads a runtime's own formats.
Neutral verdict (one JSON object; printed only when it says something — no output means decision none):
  decision         none | allow | deny | block   (deny: refuse a pre-tool call; block: tell the agent to act now)
  reason           why (deny, block)
  context          text added to the agent's context (session start, recall)
  message          a warning shown to the user
"""

from __future__ import annotations

import json

EVENTS = ("session-start", "session-end", "subagent-start", "subagent-stop", "stop", "pre-tool", "post-tool",
          "post-tool-failure", "permission-denied", "permission-request", "prompt")


def _s(v: object) -> str:
    if v is None:
        return ""
    return v if isinstance(v, str) else json.dumps(v, separators=(",", ":"), ensure_ascii=False)


class Event:
    """The neutral event (fields as in the module docstring). A plain class: hooks start fast."""

    def __init__(self, kind: str = "", tool: str = "", tool_input: dict | None = None, tool_use_id: str = "",
                 result_status: str = "", result_agent: str = "", tokens: int | None = None, error: str = "",
                 interrupted: bool = False, session_id: str = "", agent_id: str = "", agent_type: str = "",
                 model: str = "", source: str = "", reason: str = "", cwd: str = "", prompt: str = "",
                 last_message: str = "", stop_hook_active: bool = False, task: str = "",
                 transcript_path: str = ""):
        self.kind, self.tool, self.tool_input, self.tool_use_id = kind, tool, tool_input or {}, tool_use_id
        self.result_status, self.result_agent, self.tokens, self.error = result_status, result_agent, tokens, error
        self.interrupted, self.session_id, self.agent_id, self.agent_type = interrupted, session_id, agent_id, agent_type
        self.model, self.source, self.reason, self.cwd = model, source, reason, cwd
        self.prompt, self.last_message, self.stop_hook_active = prompt, last_message, stop_hook_active
        self.task, self.transcript_path = task, transcript_path

    @classmethod
    def from_neutral(cls, d: object) -> "Event":
        if not isinstance(d, dict):
            return cls()
        res = d.get("result") if isinstance(d.get("result"), dict) else {}
        ti = d.get("tool_input") if isinstance(d.get("tool_input"), dict) else {}
        tok = res.get("tokens")
        return cls(kind=d.get("event") if d.get("event") in EVENTS else "", tool=_s(d.get("tool")), tool_input=ti,
                   tool_use_id=_s(d.get("tool_use_id")), result_status=_s(res.get("status")),
                   result_agent=_s(res.get("agent_id")),
                   tokens=tok if isinstance(tok, int) and not isinstance(tok, bool) else None,
                   error=_s(d.get("error")), interrupted=d.get("interrupted") is True,
                   session_id=_s(d.get("session_id")), agent_id=_s(d.get("agent_id")),
                   agent_type=_s(d.get("agent_type")), model=_s(d.get("model")), source=_s(d.get("source")),
                   reason=_s(d.get("reason")), cwd=_s(d.get("cwd")),
                   prompt=d.get("prompt") if isinstance(d.get("prompt"), str) else "",
                   last_message=d.get("last_message") if isinstance(d.get("last_message"), str) else "",
                   stop_hook_active=d.get("stop_hook_active") is True, task=_s(d.get("task")),
                   transcript_path=_s(d.get("transcript_path")))


class Verdict:
    """The neutral verdict: decision none | allow | deny | block, reason, context, message."""

    def __init__(self, decision: str = "none", reason: str = "", context: str = "", message: str = ""):
        self.decision, self.reason, self.context, self.message = decision, reason, context, message

    def says_something(self) -> bool:
        return self.decision != "none" or bool(self.context or self.message)

    def neutral(self) -> str:
        return json.dumps({"decision": self.decision, "reason": self.reason, "context": self.context,
                           "message": self.message}, ensure_ascii=False)


def read_event(data: str) -> Event:
    """The neutral event of a hook call (anything that is not one JSON object: no event)."""
    try:
        return Event.from_neutral(json.loads(data) if data.strip() else None)
    except ValueError:
        return Event()


def write_verdict(v: Verdict) -> str:
    """What the hook prints: the verdict's JSON, or nothing when it says nothing."""
    return v.neutral() if v.says_something() else ""
