#!/usr/bin/env python3
"""BOA session-start hook: the resume protocol, the lead status and the memory block, injected into a new session.

Purpose:  every session (lead or resumed agent) starts knowing where everything is: the resume protocol and the top
          of the lead status (GUARD DOWN lines, lanes, admission, warnings, pause flag, resume files, open items,
          DONE/total), then the memory-writing reminder and the current memories of the active lanes' tasks.
When:     runs by itself at every session start (also after a compaction or a resume).
Wire:     the runtime's session start, mapped onto the neutral `session-start` event, piped to
          `<BOA_PYTHON> -I .boa/hooks/session_status.py`, `2>/dev/null || true`, timeout 8; the verdict's `context` is
          the text to add to the session.
Verify:   `printf '{"event":"session-start"}' | python3 -I .boa/hooks/session_status.py` prints the neutral verdict
          whose context starts with "Resume protocol:".
Outputs:  stdout only: the neutral verdict.
Limits:   bounded: the status in at most 1.8 s (60 lines), the guard check 1.5 s, the memory block 1.5 s (run with the
          configured interpreter BOA_PYTHON, left out when that interpreter is missing). Other events: nothing.
"""

from __future__ import annotations

import os
import shutil
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import boa_tool as bt  # noqa: E402
import hook_contract as hc  # noqa: E402


def session_context(env: "bt.Env | None") -> str:
    """The core: the text a new session gets. Without a usable configuration (env None) it is the resume protocol
    alone: the protocol always goes out."""
    import lead_status
    if env is None:
        return lead_status.PROTOCOL
    try:
        text = lead_status.hook_text()
    except Exception:  # noqa: BLE001 - the protocol line always goes out
        text = lead_status.PROTOCOL
    py = env["BOA_PYTHON"]
    memory = ""
    if shutil.which(py):
        _, memory = bt.run_bounded([py, "-I", "-B", os.path.join(HERE, "memory_recall.py"), "--session"], 1.5,
                                   tag="session-status", grace=bt.HOOK_GRACE)
        memory = memory.rstrip("\n")
    return text + ("\n\n" + memory if memory else "")


def main(argv: list[str]) -> int:
    bt.on_term_exit(0)   # a stop still removes its bounded children and their temp files; a hook exits 0, silent
    if "-h" in argv or "--help" in argv:
        sys.stdout.write(bt.help_text(__doc__))
        return 0
    try:
        ev = hc.read_event(sys.stdin.buffer.read(1048576).decode("utf-8", "replace"))
        if ev.kind != "session-start":
            return 0
        try:
            env: "bt.Env | None" = bt.Env(os.path.join(os.path.dirname(HERE), "tools", "boa_tool.py"))
        except Exception:  # noqa: BLE001 - a malformed config still gets the protocol
            env = None
        try:
            text = session_context(env)
        except Exception:  # noqa: BLE001 - the protocol line always goes out
            import lead_status
            text = lead_status.PROTOCOL
        out = hc.write_verdict(hc.Verdict(context=text))
        if out:
            print(out)
    except Exception:  # noqa: BLE001 - a hook never fails the runtime
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
