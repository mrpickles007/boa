"""BOA pause flag: the signal behind pausing and resuming the project.

Purpose:  one flag file that says "the project is paused, since when and why"; the pause guard, the pause capture,
          the lead's stop hook and the status screen all read it.
When:     the pause command sets it (with the owner's reason), the resume command clears it; anyone checks it with
          `status` before starting work.
Wire:     nothing to wire: the pause/resume commands call it; the hooks read the flag file.
Verify:   `pause-flag.sh status` says "not paused" (exit 4) or "PAUSED since <time>: <reason>".
Outputs:  <main checkout>/<BOA_LEAD_DIR>/PAUSE (0600): `paused_at=<UTC ISO time>` and `reason=<one line>`.
Limits:   setting it again keeps the first time and records the new reason; control characters in the reason become
          spaces.

Usage: .boa/bin/pause-flag.sh set <reason...>   write <lead dir>/PAUSE (time, reason); refuses an empty reason
       .boa/bin/pause-flag.sh clear             remove the flag (resume); says so when it was not set
       .boa/bin/pause-flag.sh status            "PAUSED since <time>: <reason>" (exit 0) or "not paused" (exit 4)
The flag lives in the git-excluded lead dir of the main checkout, also when run from a lane worktree. Readers: the
pause guard (sub-agents may then only write their resume file and commit wip in their own worktree), the pause
capture (copies each stopping agent's resume file), the lead stop hook (renders RESUME-LEAD.md). Exit: 0 ok, 2 usage,
4 status: not paused (3 is reserved for the `boa` launchers: a missing prerequisite).
Environment (tests): BOA_LEAD_DIR (absolute: the lead dir), BOA_PAUSE_NOW (epoch seconds used as "now").
"""

from __future__ import annotations

import os
import re
import sys
import time

sys.dont_write_bytecode = True   # no __pycache__ next to the installed tools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_tool as bt  # noqa: E402

TOOL = "pause-flag"


def field(flag: str, name: str) -> str:
    try:
        with open(flag, encoding="utf-8", errors="replace") as fh:
            for line in fh.read().splitlines():
                if line.startswith(name + "="):
                    return line[len(name) + 1:]
    except OSError:
        pass
    return ""


def usage() -> int:
    sys.stdout.write(bt.help_text(__doc__))
    return 2


def main(argv: list[str]) -> int:
    bt.on_term_exit()   # a stop mid-write still removes the temp file
    if argv[:1] in (["-h"], ["--help"]):
        sys.stdout.write(bt.help_text(__doc__))
        return 0
    env = bt.init(os.path.abspath(__file__), TOOL)
    os.umask(0o077)
    flag = os.path.join(env.path(env["BOA_LEAD_DIR"]), "PAUSE")
    cmd, args = (argv[0], argv[1:]) if argv else ("", [])
    if cmd == "set":
        reason = re.sub(r"[\x00-\x1f\x7f]", " ", " ".join(args)).strip(" ")
        if not reason:
            bt.die(TOOL, "set needs a reason (e.g. 'owner: stop for today')")
        os.makedirs(os.path.dirname(flag), exist_ok=True)
        at = field(flag, "paused_at") if os.path.isfile(flag) else ""
        at = at or bt.utc(int(os.environ.get("BOA_PAUSE_NOW") or time.time()))
        tmp = flag + ".tmp"
        try:   # the name is known before the file exists: any way out removes a leftover temp file
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(f"paused_at={at}\nreason={reason}\n")
            os.chmod(tmp, 0o600)
            os.replace(tmp, flag)
        finally:
            if os.path.lexists(tmp):
                os.remove(tmp)
        print(f"pause-flag: PAUSED since {at}: {reason} ({flag})")
    elif cmd == "clear":
        if args:
            return usage()
        if os.path.lexists(flag):
            os.remove(flag)
            print(f"pause-flag: cleared ({flag})")
        else:
            print("pause-flag: was not set")
    elif cmd == "status":
        if args:
            return usage()
        if os.path.isfile(flag):
            print(f"PAUSED since {field(flag, 'paused_at')}: {field(flag, 'reason')}")
        else:
            print("not paused")
            return 4
    else:
        return usage()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
