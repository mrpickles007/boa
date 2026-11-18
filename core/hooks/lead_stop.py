#!/usr/bin/env python3
"""BOA lead stop hook: when the lead's turn ends while the project is paused, write the lead's resume file.

Purpose:  a paused project resumes losslessly in a fresh session: <lead dir>/RESUME-LEAD.md holds the pause time and
          reason, the read order, the lane resume files copied at the pause, what resuming does and the full status at
          the stop (the project's own daemons are the lead's to stop, /pause-project).
When:     runs by itself at the end of every lead turn; acts only while <lead dir>/PAUSE exists.
Wire:     the runtime's end-of-turn of the lead, mapped onto the neutral `stop` event (no agent_id), piped to
          `<BOA_PYTHON> -I .boa/hooks/lead_stop.py`, `2>/dev/null || true`, timeout 30.
Verify:   set the pause flag, end a lead turn: <lead dir>/RESUME-LEAD.md holds the block, whose first line after the
          begin marker starts "# RESUME-LEAD — PAUSED".
Outputs:  the generated status as ONE marked block of <lead dir>/RESUME-LEAD.md, between the lines
          `<!-- boa:lead-stop:begin -->` and `<!-- boa:lead-stop:end -->`: replaced in place on every stop; every byte
          outside it (the lead's notes, a project's own hand-written handover) is kept as it was; a file without the
          markers keeps its whole content, the block going on top; a new file is created 0600, an existing one keeps
          its mode; written atomically (a temporary file beside it, then a rename). A verdict `message` instead of a
          write when the markers are broken (not exactly one begin line before one end line; a byte-order mark
          before a marker is no break) or the path is a symlink or not a file, when the file cannot be read or
          written (naming the file and the error), and when config.env is unreadable (naming the line).
Limits:   a sub-agent's stop (agent_id present) is ignored; the status part is bounded to 20 s. Fail-safe: never blocks the stop (no decision is printed), exits 0.
Environment (tests): BOA_LEAD_DIR, BOA_STOP_NOW (epoch).
"""

from __future__ import annotations

import os
import re
import stat
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import boa_tool as bt  # noqa: E402
import hook_contract as hc  # noqa: E402


def first(lines: list[str], key: str) -> str:
    return next((x[len(key) + 1:] for x in lines if x.startswith(key + "=")), "")


BEGIN, END = "<!-- boa:lead-stop:begin -->", "<!-- boa:lead-stop:end -->"


def merge(old: bytes | None, body: str) -> bytes | None:
    """The resume file with `body` as the hook's block: the block replaced in place, every byte outside it kept; a
    file without the markers keeps its whole content below a new block; None when the markers are broken (anything
    but one begin line before one end line: nothing may be guessed, so nothing is written)."""
    body = "\n".join("\\" + x if x.strip() in (BEGIN, END) else x for x in body.rstrip("\n").split("\n"))   # never a marker
    block = f"{BEGIN}\n{body}\n{END}\n"
    if not old:
        return block.encode("utf-8")
    text = old.decode("utf-8", "surrogateescape")   # undecodable bytes come back unchanged
    lines = [x.lstrip("\ufeff").strip() for x in text.split("\n")]   # a byte-order mark never hides a marker
    begins = [i for i, x in enumerate(lines) if x == BEGIN]
    ends = [i for i, x in enumerate(lines) if x == END]
    if not begins and not ends:
        return (block + "\n").encode("utf-8") + old
    if len(begins) != 1 or len(ends) != 1 or begins[0] > ends[0]:
        return None
    return bt.replace_generated(text, BEGIN, END, body).encode("utf-8", "surrogateescape")


def render(env: bt.Env) -> str:
    """The core: under the pause flag, write the hook's block of RESUME-LEAD.md; returns the warning, or ""."""
    lead_rel = env["BOA_LEAD_DIR"]
    lead = env.path(lead_rel)
    flag = os.path.join(lead, "PAUSE")
    paused, kind = bt.pause_state(flag)   # never opened unless a regular file: a FIFO would hang the stop
    if not paused:
        return ""
    if kind:
        return f"BOA lead stop: the pause flag {flag} is {kind}, not read: the status at the pause was not written"
    with open(flag, encoding="utf-8", errors="replace") as fh:
        fl = fh.read().splitlines()
    at, reason = first(fl, "paused_at"), first(fl, "reason")
    ts = bt.utc(int(os.environ.get("BOA_STOP_NOW") or time.time()))
    out = os.path.join(lead, "RESUME-LEAD.md")
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
    text = (f"# RESUME-LEAD — PAUSED since {at or '?'} (rendered {ts} by the lead's stop hook)\n\n"
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
            + "\n\n" + f"## Status at the stop\n```\n{status}\n```\n")
    # the file is read only now, after the status (up to 20 s): an edit made meanwhile is not lost
    if os.path.islink(out) or (os.path.lexists(out) and not os.path.isfile(out)):
        return f"BOA lead stop: {out} is a symlink or not a file: the status at the pause was not written (fix it by hand)"
    old, mode = None, 0o600
    try:
        if os.path.lexists(out):
            with open(out, "rb") as fh:
                old = fh.read()
            mode = stat.S_IMODE(os.stat(out).st_mode)
    except OSError as exc:
        return f"BOA lead stop: {out} could not be read ({exc}): the status at the pause was not written"
    data = merge(old, text)
    if data is None:
        return (f"BOA lead stop: {out} has broken {BEGIN} / {END} lines (not one begin line before one end line): the "
                "status at the pause was not written and the file was not touched (fix the markers by hand)")
    os.umask(0o077)
    tmp = f"{out}.tmp.{os.getpid()}"
    try:
        if os.path.lexists(tmp):   # a leftover (a FIFO, a link, a file): removed, never opened or written through
            os.remove(tmp)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_BINARY", 0), 0o600)   # O_BINARY: no CRLF from the Windows C runtime
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, out)
    except OSError as exc:
        return f"BOA lead stop: {out} could not be written ({exc}): the status at the pause was not written, the file is as it was"
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return ""


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
            msg = render(env)
            if msg:
                print(hc.write_verdict(hc.Verdict(message=msg)))
    except Exception:  # noqa: BLE001 - a hook never blocks the stop
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
