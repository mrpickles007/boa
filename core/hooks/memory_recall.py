#!/usr/bin/env python3
"""BOA memory recall hooks: put the relevant CURRENT memories in front of the agent at the moment it needs them.

Purpose:  put the relevant current memories in front of the agent when it needs them: after a failure and at session
          start.
When:     runs by itself on a failed tool call; the session status calls `--session`. A sub-agent gets its task's
          memories through its brief and searches again itself at start.
Wire:     the runtime's failed-tool event, mapped onto the neutral `post-tool-failure` event (with `error`, the error
          text) and piped to `<BOA_PYTHON> -I .boa/hooks/memory_recall.py`, `2>/dev/null || true`, timeout 10; the
          verdict's `context` carries the memories.
Verify:   `python3 -I .boa/hooks/memory_recall.py --session` prints the memory-writing reminder.
Outputs:  the memories as the verdict's context (at most 5, then "+k more: <the memory_search command>"), else
          nothing.
Limits:   word matching, at most 5 memories shown per moment (the rest counted, with the command that lists them).

  post-tool-failure   the failed tool call's error text is searched (memory_search --error: the `error` recall
                      moment's types of .boa/memory-types.json, ranked by shared words) and the matching memories are
                      returned as the verdict's context ("memory-12 gotcha: <brief>", at most 5, then "+k more:
                      .boa/tools/memory_search.py --error '<the error text>' --limit <n>");
  --session [T-NNN...] (no payload) prints the session-start memory block: the 3-line memory-writing reminder and
                      the current memories of the given tasks, or of every lane's task (git worktrees) when none given
                      (at most 5 per task, then "<task>: +k more: .boa/tools/memory_search.py --task <task>").
Prints nothing when nothing matches. Fail-safe: never fails, exit 0. Input: the neutral event on stdin; output: the
neutral verdict, whose `context` carries the memories (tools/hook_contract.py).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

REMINDER = (
    "Memory: record every lesson, gotcha, edge case, decision (adr/edr), outcome, bug… as ONE block through "
    ".boa/tools/memory_write.py (it assigns the id, routes the file, stamps supersession; never hand-write ids or links).",
    "Recall before acting: .boa/tools/memory_search.py --task T-NNN at a task's start, --error '<text>' after a "
    "failure, --moment decision before deciding; cite the memory ids you relied on in your report.",
    "Lanes and reports write drafts (memory_write.py --format-only) into .lane-resume/memories.md; the integrator's "
    "train fold ingests them (--ingest).",
)


RECALL_LIMIT = 5   # memories shown per failure, and per task at session start; more are counted and named


def blocks():
    import memory_lint as ml
    import memory_search as ms
    import memory_types
    types = memory_types.load()
    mdir = ml.memory_dir()
    return types, (ms.load_blocks([mdir], types.names) if os.path.isdir(mdir) else [])


def line(b) -> str:
    return f"{b.mid} {b.fields.get('type')}: {b.fields.get('brief')}"


def for_tasks(tasks: list[str], limit: int) -> list[str]:
    import memory_search as ms
    types, bl = blocks()
    first = set(types.moment_types("start"))
    out = []
    for t in tasks:
        rx = re.compile(r"(?<![A-Za-z0-9-])" + re.escape(t) + r"(?![0-9A-Za-z])")
        hits = [b for b in bl if b.id and b.current and rx.search(ms.hay(b))]
        hits.sort(key=lambda b: (b.fields.get("type") not in first, -(b.id or 0)))
        out += [f"{t}: {line(b)}" for b in hits[:limit]]
        if len(hits) > limit:   # never a silent cut: say how many more and how to see them
            out.append(f"{t}: +{len(hits) - limit} more: .boa/tools/memory_search.py --task {t}")
    return out


def lane_tasks() -> list[str]:
    import memory_lint as ml
    try:
        out = subprocess.run(["git", "-C", ml.ROOT, "worktree", "list", "--porcelain"], capture_output=True,
                             text=True, timeout=3).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    return sorted({m.group(1) for m in re.finditer(r"^branch refs/heads/\S*?(T-\d{3,}[a-z]?)(?:-|$)", out, re.M)})


def main(argv: list[str]) -> int:
    import boa_tool as bt
    bt.on_term_exit(0)   # a stop ends its git child (subprocess.run kills it); a hook exits 0
    if argv and argv[0] == "--session":
        tasks = [t for t in argv[1:] if re.fullmatch(r"T-\d{3,}[a-z]?", t)] or lane_tasks()
        mem = for_tasks(tasks, RECALL_LIMIT)
        print("\n".join(REMINDER + ((f"Current memories of the active tasks ({', '.join(tasks)}):",) + tuple(
            "  " + m for m in mem) if mem else ())))
        return 0
    import hook_contract as hc
    out = hc.write_verdict(recall(hc.read_event(sys.stdin.buffer.read(4 << 20).decode("utf-8", "replace"))))
    if out:
        print(out)
    return 0


def recall(ev) -> "object":
    """The core: a neutral post-tool-failure event -> a verdict carrying the memories as context."""
    import hook_contract as hc
    v = hc.Verdict()
    if ev.kind == "post-tool-failure":
        err = ev.error
        if not err.strip():
            return v
        import memory_search as ms
        types, bl = blocks()
        hits = ms.recall_error(bl, types, err, max(len(bl), 1))
        if hits:
            more = len(hits) - RECALL_LIMIT
            v.context = ("Memories that may explain this failure (memory_search --error); follow or supersede them:\n"
                         + "\n".join(line(b) for _, b in hits[:RECALL_LIMIT])
                         + (f"\n+{more} more: .boa/tools/memory_search.py --error '<the error text>' --limit {len(hits)}"
                            if more > 0 else ""))
    return v


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception:  # noqa: BLE001  (a hook never fails)
        pass
    sys.exit(0)
