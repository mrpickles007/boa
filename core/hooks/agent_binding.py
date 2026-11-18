#!/usr/bin/env -S python3 -I
"""The agent-to-task binding of lane orchestration: which lane task each sub-agent was spawned for.

Hook (the lead spawns a sub-agent): reads BOA's neutral event on stdin (tools/hook_contract.py,
references/hook-contract.md) — a `post-tool` event of the tool `sub-agent`, with the brief in
tool_input.description / tool_input.prompt and the spawned agent's id in result.agent_id — and records agent id ->
task id, the task being the first standalone task id (`T-NNN`, no letter or digit right before or after it) of the
description, else of the prompt. A spawn whose result carries no agent id yet (a runtime that gives the id only when
a foreground agent ends) stays unbound: lanes are spawned so that the id is known at the spawn (in the background).
The record is one JSON line {"ts", "agent", "task"} appended to <REPO>/<BOA_STATE_DIR>/agent-bindings.jsonl (dir
0700, file 0600; machine-local, git-ignored with .boa/). It prints nothing and always exits 0: a binding that is not
written leaves the agent unbound, which the guards handle (confined to the lane worktrees, logged); a state file that
is not a regular file (a FIFO, a device, a directory) is stat'ed, never opened: nothing is written or read, the agent
stays unbound.
Known limits: an agent's first tool calls can run before its binding lands (the spawn result arrives after the agent
starts), so it is unbound for those calls; a description whose first task id is the wrong one binds the wrong lane,
which fails toward deny (its own worktree is then "another lane"); the spawn rule that every description starts with
the lane's task id covers it.

Library (loaded by path by guard_destructive.py and pause_guard.py): task_of(cfg, agent_id) -> the newest task bound
to that agent id, or None (reads at most the file's last 256 KiB). A project clock may read or extend the file.
CLI: `agent_binding.py --task-of <agent id>` prints the bound task (nothing when unbound); a config it cannot read:
the error on stderr, exit 2.
Python 3 standard library only; invoked as `<BOA_PYTHON> -I <hook>`.
"""
import importlib.util
import json
import os
import re
import stat
import sys
import time

sys.dont_write_bytecode = True
FILE = "agent-bindings.jsonl"
AGENT_ID = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
TAIL = 256 * 1024
RECORD_MAX = 4096   # characters: a record is one flat object of three short strings; a longer line is never one


def _config():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook_config.py")
    spec = importlib.util.spec_from_file_location("boa_hook_config", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def first_task(cfg, text):
    """The first standalone task id of text, or None."""
    m = re.search(r"(?<![A-Za-z0-9])(" + cfg["task_re"] + r")(?![A-Za-z0-9])", str(text or ""))
    return m.group(1) if m else None


def spawn_fields(ev):
    """(agent id, task texts) of a neutral spawn event (post-tool of a sub-agent); ("", []) for any other event."""
    if ev.kind != "post-tool" or ev.tool != "sub-agent":
        return "", []
    texts = [ev.tool_input.get("description"), ev.tool_input.get("prompt")]
    return ev.result_agent, [t for t in texts if isinstance(t, str) and t]


def regular_or_missing(path):
    """True when nothing is at path or a regular file is: one stat, never an open (a FIFO would hang the spawn hook
    or a guard's verdict). Anything else (a FIFO, a device, a directory, a path that cannot be checked) is False: the
    binding is then neither written nor read, the agent stays unbound (the guards' fail-safe case)."""
    try:
        return stat.S_ISREG(os.stat(path).st_mode)
    except FileNotFoundError:
        return True
    except OSError:
        return False


def record(cfg, agent, task):
    path = os.path.join(cfg["state_dir"], FILE)
    os.makedirs(cfg["state_dir"], 0o700, exist_ok=True)
    if not regular_or_missing(path):
        return
    line = json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "agent": agent, "task": task})
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_BINARY", 0), 0o600)   # O_BINARY: no CRLF from the Windows C runtime
    with os.fdopen(fd, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")


def task_of(cfg, agent_id):
    """The newest task bound to agent_id, or None."""
    if not AGENT_ID.fullmatch(str(agent_id or "")):
        return None
    path = os.path.join(cfg["state_dir"], FILE)
    if not regular_or_missing(path):
        return None
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - TAIL))
            lines = fh.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        if len(line) > RECORD_MAX or not line.startswith("{"):
            continue   # never a record; a pathologically nested line is not even parsed (a deep enough one can
            # exhaust the C stack of the interpreter's JSON decoder, smaller on Windows, instead of raising)
        try:
            rec = json.loads(line)
        except (ValueError, RecursionError):
            continue   # a cut first line, a torn last one, a nested one under the limit
        if isinstance(rec, dict) and rec.get("agent") == agent_id:
            task = rec.get("task")
            return task if isinstance(task, str) and re.fullmatch(cfg["task_re"], task) else None
    return None


def main(argv):
    config = _config()
    if argv[:1] == ["--task-of"] and len(argv) == 2:
        try:
            cfg = config.load(here=os.path.abspath(__file__))
        except Exception as exc:   # noqa: BLE001 - a named message (a config line outside the grammar), no traceback
            print(f"agent_binding: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        task = task_of(cfg, argv[1]) if cfg else None
        if task:
            print(task)
        return 0
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
        import hook_contract as hc
        ev = hc.read_event(sys.stdin.buffer.read(4 * 1024 * 1024).decode("utf-8", "replace"))
        agent, texts = spawn_fields(ev)
        if not agent:
            return 0
        cfg = config.load(here=os.path.abspath(__file__))
        if cfg is None or not AGENT_ID.fullmatch(agent):
            return 0
        task = next((t for t in (first_task(cfg, x) for x in texts) if t), None)
        if task:
            record(cfg, agent, task)
    except Exception:  # noqa: BLE001  (a hook never fails)
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
