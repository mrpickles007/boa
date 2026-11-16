#!/usr/bin/env python3
"""BOA lead stop hook: when the lead's turn ends while the project is paused, write the lead's resume file.

Purpose:  a paused project resumes losslessly in a fresh session: <lead dir>/RESUME-LEAD.md holds the pause time and
          reason, the read order, the lane resume files copied at the pause, what resuming does and the full status at
          the stop (the project's own daemons are the lead's to stop, /pause-project).
When:     runs by itself at the end of every lead turn; acts only while <lead dir>/PAUSE exists.
Wire:     the runtime's end-of-turn of the lead, mapped onto the neutral `stop` event (no agent_id), piped to
          `<BOA_PYTHON> -I .boa/hooks/lead_stop.py`, `2>/dev/null || true`, timeout 30.
Verify:   set the pause flag, end a lead turn: <lead dir>/RESUME-LEAD.md exists and starts "# RESUME-LEAD — PAUSED".
Outputs:  <lead dir>/RESUME-LEAD.md (0600, replaced atomically); a verdict `message` naming the line when
          config.env is unreadable; a "## Lead notes" section the lead wrote into an earlier
          copy is kept verbatim at the end.
Limits:   a sub-agent's stop (agent_id present) is ignored; the status part is bounded to 20 s. Fail-safe: never blocks the stop (no decision is printed), exits 0.
Environment (tests): BOA_LEAD_DIR, BOA_STOP_NOW (epoch).
"""

from __future__ import annotations

import os
import re
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import boa_tool as bt  # noqa: E402
import hook_contract as hc  # noqa: E402


def first(lines: list[str], key: str) -> str:
    return next((x[len(key) + 1:] for x in lines if x.startswith(key + "=")), "")


def render(env: bt.Env) -> None:
    """The core: under the pause flag, render RESUME-LEAD.md."""
    lead_rel = env["BOA_LEAD_DIR"]
    lead = env.path(lead_rel)
    flag = os.path.join(lead, "PAUSE")
    if not os.path.isfile(flag):
        return
    with open(flag, encoding="utf-8", errors="replace") as fh:
        fl = fh.read().splitlines()
    at, reason = first(fl, "paused_at"), first(fl, "reason")
    ts = bt.utc(int(os.environ.get("BOA_STOP_NOW") or time.time()))
    out = os.path.join(lead, "RESUME-LEAD.md")
    notes = ""
    try:
        with open(out, encoding="utf-8", errors="replace") as fh:
            old = fh.read().split("\n")
        idx = next((i for i, x in enumerate(old) if x.startswith("## Lead notes")), None)
        if idx is not None:
            notes = "\n".join(old[idx:]).rstrip("\n")
    except OSError:
        pass
    argv = [sys.executable, "-I", "-B", os.path.join(env.home, "tools", "lead_status.py"), "--no-gh", "--no-mark"]
    status = bt.run_bounded(argv, 20, tag="lead-stop")[1].rstrip("\n")
    since = bt.from_utc(at) or 0
    copies = []
    lanes = os.path.join(lead, "lanes")
    try:
        for n in sorted(os.listdir(lanes)):
            p = os.path.join(lanes, n)
            if os.path.isfile(p) and not os.path.islink(p) and os.stat(p).st_mtime > since \
                    and re.fullmatch(r"(?:" + bt.TASK_RE + r")-[a-z][a-z-]*\.md", n):
                copies.append(f"- {n}")
    except OSError:
        pass
    text = (f"# RESUME-LEAD — PAUSED since {at or '?'} (rendered {ts} by the lead Stop hook)\n\n"
            f"Reason: {reason or '?'}\n\n"
            "## Read order for a fresh lead session\n"
            "AGENTS.md -> docs/agent-handbook.md -> memory-bank/RESUME.md -> 08-OWNER-RULES.md + "
            "09-OPERATING-PROCEDURES.md\n"
            f"-> all memory-bank/*.md -> THIS file -> {lead_rel}/open-items.md -> {lead_rel}/lanes.md (newest lines win) "
            f"-> {lead_rel}/lanes/<task>-<role>.md.\n"
            "Agent ids do not survive a session: resume each lane with a NEW agent given its resume file.\n\n"
            "## Resume\n/resume-project: clears the pause flag (.boa/bin/pause-flag.sh clear), prints the status and "
            "the\nper-lane plan below.\n\n"
            f"## Lane resume files copied at the pause ({lead_rel}/lanes/)\n" + ("\n".join(copies) or "(none yet)")
            + "\n\n" + f"## Status at the stop\n```\n{status}\n```\n" + (f"\n{notes}\n" if notes else ""))
    os.umask(0o077)
    tmp = f"{out}.tmp.{os.getpid()}"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, out)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def main(argv: list[str]) -> int:
    bt.on_term_exit(0)   # a stop still removes its status child and the temp file; a hook exits 0, silent
    if "-h" in argv or "--help" in argv:
        sys.stdout.write(bt.help_text(__doc__))
        return 0
    try:
        ev = hc.read_event(sys.stdin.buffer.read(1048576).decode("utf-8", "replace"))
        if ev.kind == "stop" and not ev.agent_id:
            try:
                env = bt.Env(os.path.join(os.path.dirname(__file__), "..", "tools", "boa_tool.py"))
            except bt.ToolError as exc:   # never a silent failure: say why nothing could be rendered
                print(hc.write_verdict(hc.Verdict(message=f"BOA lead stop: {exc}: the pause flag could not be read and "
                                                          "RESUME-LEAD.md was not rendered (fix .boa/config.env)")))
                return 0
            render(env)
    except Exception:  # noqa: BLE001 - a hook never blocks the stop
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
