#!/usr/bin/env python3
"""BOA sub-agent stop hook: the report capture into the lane journal, and the pause capture.

Purpose:  keep what every sub-agent said and lose no lane state at a pause: the stopping agent's final report is
          appended to its lane journal (lane_journal.py, the one journal writer); while the project is paused its
          resume file is also copied into the lead dir and the journal records the pause; a missing resume file is
          reported to the user at once.
When:     runs by itself when a sub-agent stops; the pause capture acts only while <lead dir>/PAUSE exists
          (pause-flag.sh set).
Wire:     the runtime's sub-agent stop, mapped onto the neutral `subagent-stop` event (with `prompt`, the agent's
          brief, and `last_message`, its final report), piped to `<BOA_PYTHON> -I .boa/hooks/subagent_stop.py`,
          `2>/dev/null || true`, timeout 10; the verdict's `message` is the warning to show the user. Wire this hook
          only: it journals the report itself (never wire lane_journal.py on the same event as well).
Verify:   `printf '{"event":"subagent-stop","agent_type":"builder","agent_id":"a1","prompt":"T-001","last_message":"ok"}'
          | python3 -I .boa/hooks/subagent_stop.py` appends a "stopped" entry to <lead dir>/lanes/T-001.md; with the
          pause flag set <lead dir>/lanes/T-001-builder.md appears (or the warning) and T-001.md gets a "paused" entry.
Outputs:  the lane journal entry (lane_journal.py); the report's Leftovers in <lead dir>/open-items.md
          (report_capture.py: a task agent's report without a Leftovers section is flagged there and in the verdict
          `message`); a verdict `message` when the report could not be captured (an
          unreadable config.env, naming its line; an unwritable journal; a pause capture that fails — also with the
          pause flag set and the journal unwritable at once), never a silent loss; <lead dir>/lanes/<task>-<agent type>.md (0600, the copy) and the
          "paused" journal entry
          "## <time> | <agent type> | <agent id> | paused (resume file copied to lanes/<task>-<type>.md)"; without a
          resume file (or a symlink in its place) the entry says "paused, NO resume file at <path>" and the verdict
          carries a warning message.
Limits:   a merge train's integrator (TRAIN-<n>) or an agent with no task gets a "paused" entry only; internal agents
          of the runtime (empty agent type) are skipped; the task comes from the lane journal's own resolution, so the
          two hooks never disagree. Fail-safe: never blocks the agent, exits 0.
Environment (tests): BOA_LEAD_DIR, BOA_WT_DIR, BOA_JOURNAL_NOW.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import boa_tool as bt  # noqa: E402
import hook_contract as hc  # noqa: E402
import lane_journal as lj  # noqa: E402
import report_capture  # noqa: E402


def capture(ev: hc.Event, env: bt.Env) -> hc.Verdict:
    """The core: a neutral sub-agent stop event -> the capture done, and the verdict (a warning message or none)."""
    v = hc.Verdict()
    lead = env.path(env["BOA_LEAD_DIR"])
    flag = os.path.join(lead, "PAUSE")
    if ev.kind != "subagent-stop" or not os.path.isfile(flag):
        return v
    aid, atype = lj.ident(ev.agent_id), lj.ident(ev.agent_type)
    if not atype:
        return v
    task = lj.task_of_agent(atype, ev.prompt, ev.task)
    if not re.fullmatch(r"(?:" + bt.TASK_RE + r"|TRAIN-[0-9]+|_unassigned)", task):
        task = "_unassigned"
    lanes = os.path.join(lead, "lanes")
    os.umask(0o077)
    os.makedirs(lanes, exist_ok=True)
    status = "paused"
    if re.fullmatch(bt.TASK_RE, task):
        resume = os.path.join(env.path(env["BOA_WT_DIR"]), task, ".lane-resume", f"{atype}.md")
        copy = os.path.join(lanes, f"{task}-{atype}.md")
        try:
            if not os.path.isfile(resume) or os.path.islink(resume):
                raise OSError("no resume file")
            shutil.copyfile(resume, copy + ".tmp", follow_symlinks=False)
            os.chmod(copy + ".tmp", 0o600)
            os.replace(copy + ".tmp", copy)
            status = f"paused (resume file copied to lanes/{task}-{atype}.md)"
        except OSError:
            status = f"paused, NO resume file at {resume.replace(os.sep, '/')}"   # `/` on every OS, as the journal text
            v.message = (f"BOA pause: {atype} of {task} stopped without a resume file ({resume}): ask it to write one "
                         "or record the lane state yourself")
        finally:   # any way out (an error, a stop) removes a leftover temp copy
            try:
                os.remove(copy + ".tmp")
            except OSError:
                pass
    reason = ""
    try:
        with open(flag, encoding="utf-8", errors="replace") as fh:
            reason = next((x[7:] for x in fh.read().splitlines() if x.startswith("reason=")), "")
    except OSError:
        pass
    now = int(os.environ.get("BOA_JOURNAL_NOW") or time.time())
    bt.append_locked(os.path.join(lanes, f"{task}.md"),
                     f"## {bt.utc(now)} | {atype} | {aid or 'unknown'} | {status}\nPause capture: {reason}\n\n", wait=3)
    return v


def main(argv: list[str]) -> int:
    bt.on_term_exit(0)   # a stop still removes the temp copy; a hook exits 0, silent
    if "-h" in argv or "--help" in argv:
        sys.stdout.write(bt.help_text(__doc__))
        return 0
    try:
        ev = hc.read_event(sys.stdin.buffer.read(16777216).decode("utf-8", "replace"))
        atype = lj.ident(ev.agent_type)
        if ev.kind != "subagent-stop" or not atype:
            return 0
        try:
            env = bt.Env(os.path.join(os.path.dirname(__file__), "..", "tools", "boa_tool.py"))
        except bt.ToolError as exc:   # never drop a report silently: say why it was not captured
            print(hc.write_verdict(hc.Verdict(message=f"BOA sub-agent stop: {exc}: the report of {atype} was not "
                                                      "captured (fix .boa/config.env)")))
            return 0
        os.umask(0o077)
        lost = ""
        try:
            lj.journal(ev, env, False)   # the report first: a pause capture that fails must not lose it
        except Exception as exc:  # noqa: BLE001 - the pause capture still runs
            lost = f"BOA sub-agent stop: the report of {atype} was not captured ({exc})"
        warn = ""
        try:   # the Leftovers of the report into the transit queue (report_capture.py)
            task = lj.task_of_agent(atype, ev.prompt, ev.task)
            if not re.fullmatch(r"(?:" + bt.TASK_RE + r"|TRAIN-[0-9]+)", task):
                task = "_unassigned"
            warn = report_capture.capture(ev.last_message, task, atype, lj.ident(ev.agent_id), env,
                                          int(os.environ.get("BOA_JOURNAL_NOW") or time.time()))
        except Exception as exc:  # noqa: BLE001 - said, never a silent loss
            warn = f"BOA report capture: the Leftovers of {atype} were not captured ({exc}): copy them by hand"
        try:   # its own guard: a pause capture that fails (an unwritable journal) is said, never swallowed
            v = capture(ev, env)
        except Exception as exc:  # noqa: BLE001
            v = hc.Verdict(message=f"BOA pause: the pause capture of {atype} failed ({exc}): its lane state was not "
                                   "captured; record it yourself")
        v.message = "; ".join(x for x in (lost, warn, v.message) if x)
        out = hc.write_verdict(v)
        if out:
            print(out)
    except Exception:  # noqa: BLE001 - a hook never fails the runtime
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
