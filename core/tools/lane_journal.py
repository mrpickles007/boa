"""BOA lane journal: every sub-agent's final report appended to the lead's machine-local journal.

Purpose:  keep what each lane's last agent actually said, so a new lead session (or any agent) resumes the lane from
          it; the task an agent's entry belongs to is resolved one way for every hook (`--task`).
When:     a sub-agent stop hook (runs by itself when an agent ends); the lead reads `<lead dir>/lanes/<task>.md` when
          it resumes a lane; the pause capture asks it for the task (`--task`).
Wire:     the runtime's sub-agent stop, mapped onto the neutral `subagent-stop` event, piped to
          `.boa/bin/lane-journal.sh` (or `python3 -I .boa/tools/lane_journal.py`), `2>/dev/null || true`, timeout 10.
Verify:   after an agent stops, `<lead dir>/lanes/<task>.md` ends with its `## <time> | <type> | <id> | stopped` entry.
Outputs:  `<main checkout>/<BOA_LEAD_DIR>/lanes/<task>.md` (`_unassigned.md` when no task is found; 0600, lanes/ 0700).
Limits:   the report is capped at 20 KiB in the journal; a longer one is kept whole in
          `<lead dir>/lanes/<task>.full/<time>-<agent id>[-<n>].md` (0600; a counter keeps two reports of one second
          apart) and the cut marker names that file (no silent loss; close-out removes the lane's .full/ with it); the report is copied as the agent wrote it (the journal is
          private, 0600, and git-excluded; a project that needs redacted journals wires its own redactor); the event
          is read up to 16 MiB; the report and the brief come in the event (the agent's wiring
          extracts them: this tool reads no runtime transcript).

Usage: .boa/bin/lane-journal.sh            (hook mode: the neutral subagent-stop event on stdin)
       .boa/bin/lane-journal.sh --task     the same event on stdin -> the task (or TRAIN-<n>, or
                                                   _unassigned) the entry would go to, on stdout
Entry, appended to <main checkout>/<BOA_LEAD_DIR>/lanes/<task>.md:
    ## <UTC ISO time> | <agent type> | <agent id> | <status>
    <final report: the event's last_message>
- status = "stopped", or "stopped (stop hook re-entry)" when the stop hook is already active.
- Task: the event's `task` (when the wiring knows it: a task id or TRAIN-<n>), else the first task id of the event's
  `prompt` (the agent's brief), standing alone (no letter or digit right before or after it); for an integrator a
  merge train's TRAIN-<n> wins over the lane ids it lists.
- The report is the event's `last_message` (the same neutral field for every runtime); a `transcript_path` given in
  the event is noted as the entry's last line "(transcript: <path>)", never read.
- A report line shaped like an entry header gets a leading space (no fake entry). Internal agents of the runtime
  (empty agent type) are skipped. Fail-safe: never blocks the agent, never prints (except --task), exits 0; the
  append runs under the file's lock (bounded wait, 3 s). The lead dir is git-excluded: never committed.
Environment (tests): BOA_LEAD_DIR (absolute: the journal root), BOA_JOURNAL_NOW (epoch seconds used as "now").
"""

from __future__ import annotations

import os
import re
import sys
import time

sys.dont_write_bytecode = True   # no __pycache__ next to the installed tools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_tool as bt  # noqa: E402
import hook_contract as hc  # noqa: E402

REPORT_CAP = 20480


def ident(x: str) -> str:
    """An agent id or type as journaled: only [A-Za-z0-9_.:-], at most 64 characters."""
    return re.sub(r"[^A-Za-z0-9_.:-]", "", x)[:64]


def first(pattern: str, text: str) -> str:
    m = re.search(r"(?<![A-Za-z0-9])" + pattern + r"(?![A-Za-z0-9])", text)
    return m.group(0) if m else ""


def task_of_agent(atype: str, prompt: str, task: str = "") -> str:
    """The event's `task` when it is a task id or TRAIN-<n>, else the first task id of the agent's brief (TRAIN-<n>
    first for an integrator), else _unassigned. Only the brief's first 256 KiB are searched."""
    if re.fullmatch(r"(?:" + bt.TASK_RE + "|" + bt.TRAIN_RE + r")", task):
        return task
    prompt = prompt[:262144]
    task = (first(bt.TRAIN_RE, prompt) if atype == "integrator" else "") or first(bt.TASK_RE, prompt)
    return task or "_unassigned"


def cap(report: str, full: str = "") -> str:
    """The report cut to REPORT_CAP bytes; the cut says so and names FULL, the file holding the whole report."""
    raw = report.encode("utf-8")
    if len(raw) <= REPORT_CAP:
        return report
    s = report
    while len(s.encode("utf-8")) > REPORT_CAP:
        s = s[:len(s) * REPORT_CAP // len(s.encode("utf-8"))]
    where = f"; the whole report is in {full}" if full else "; the whole report was not kept"
    return s + f"\n[... truncated by lane-journal: {len(raw)} bytes, first {REPORT_CAP} kept{where}]"


def journal(ev: hc.Event, env: bt.Env, task_only: bool) -> str | None:
    """The core: a neutral sub-agent stop event -> the entry appended (or, with task_only, the task returned)."""
    if ev.kind != "subagent-stop":
        return None
    aid, atype = ident(ev.agent_id), ident(ev.agent_type)
    if not atype:
        return None
    if task_only:
        return task_of_agent(atype, ev.prompt, ev.task)
    report = ev.last_message.rstrip("\n")
    report = report or "(no final report in the event)"
    task = task_of_agent(atype, ev.prompt, ev.task)
    lanes = os.path.join(env.path(env["BOA_LEAD_DIR"]), "lanes")
    now = int(os.environ.get("BOA_JOURNAL_NOW") or time.time())
    full = ""
    if len(report.encode("utf-8")) > REPORT_CAP:   # the whole report beside the journal: a cut never loses text
        base = f"{task}.full/{bt.utc(now).replace(':', '')}-{aid or 'unknown'}"
        name, k = f"{base}.md", 1
        while os.path.exists(os.path.join(lanes, name)):   # one file per report: never overwrite an earlier one
            k += 1
            name = f"{base}-{k}.md"
        try:
            os.makedirs(os.path.join(lanes, f"{task}.full"), mode=0o700, exist_ok=True)
            bt.write_atomic(os.path.join(lanes, name), report + "\n")
            os.chmod(os.path.join(lanes, name), 0o600)
            full = f"{env['BOA_LEAD_DIR']}/lanes/{name}"
        except OSError:
            full = ""
    report = cap(report, full).rstrip("\n")
    report = re.sub(r"^(## [0-9]{4}-[0-9]{2}-[0-9]{2}T)", r" \1", report, flags=re.M)
    if ev.transcript_path:
        report += "\n(transcript: " + re.sub(r"[\x00-\x1f]", " ", ev.transcript_path)[:512] + ")"
    status = "stopped (stop hook re-entry)" if ev.stop_hook_active else "stopped"
    bt.append_locked(os.path.join(lanes, f"{task}.md"), f"## {bt.utc(now)} | {atype} | {aid or 'unknown'} | {status}\n"
                     f"{report}\n\n", wait=3, dir_mode=0o700)
    return None


def main(argv: list[str]) -> int:
    if "-h" in argv or "--help" in argv:
        sys.stdout.write(bt.help_text(__doc__))
        return 0
    os.umask(0o077)
    try:
        data = sys.stdin.buffer.read(16777216).decode("utf-8", "replace")
        env = bt.Env(os.path.abspath(__file__))
        task = journal(hc.read_event(data), env, "--task" in argv)
        if task:
            print(task)
    except Exception:  # noqa: BLE001 - a hook never fails the runtime
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
