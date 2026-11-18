"""BOA pause flag: the signal behind pausing and resuming the project.

Purpose:  one flag file that says "the project is paused, since when and why"; the pause guard, the pause capture,
          the lead's stop hook and the status screen all read it.
When:     the pause command sets it (with the owner's reason), the resume command clears it; anyone checks it with
          `status` before starting work.
Wire:     nothing to wire: the pause/resume commands call it; the hooks read the flag file.
Verify:   `pause-flag.sh status` says "not paused" (exit 4) or "PAUSED since <time>: <reason>".
Outputs:  <main checkout>/<BOA_LEAD_DIR>/PAUSE (0600): `paused_at=<UTC ISO time>` and `reason=<one line>`.
Limits:   setting it again keeps the first time and records the new reason; control characters in the reason become
          spaces. `set` also removes the temp files other set runs left behind (<flag>.tmp.<other pid>, or the older
          <flag>.tmp) last changed over a minute before it started, unopened; a directory there is left alone.

Usage: .boa/bin/pause-flag.sh set <reason...>   write <lead dir>/PAUSE (time, reason); refuses an empty reason
       .boa/bin/pause-flag.sh clear             remove the flag (resume); says so when it was not set
       .boa/bin/pause-flag.sh status            "PAUSED since <time>: <reason>" (exit 0) or "not paused" (exit 4); a
                                                FIFO, device, socket or directory at the flag's path is a pause too,
                                                named and never opened (as the pause guard sees it)
The flag lives in the git-excluded lead dir of the main checkout, also when run from a lane worktree. Readers: the
pause guard (sub-agents may then only write their resume file and commit wip in their own worktree), the pause
capture (copies each stopping agent's resume file), the lead stop hook (renders RESUME-LEAD.md). Exit: 0 ok, 1 refused
(`set` when the flag's path is a device, a FIFO, a socket or a directory: it is never replaced, or when its temp path
<flag>.tmp.<pid> (one per process) is a directory; any other leftover there is removed, never opened; `clear` when the flag's path is a
directory or cannot be removed), 2 usage, 4 status: not
paused (3 is reserved for the `boa` launchers: a missing prerequisite).
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


STALE_S = 60   # a temp file of a set still running lives for milliseconds: older than this, its set is gone


def remove_stale_temps(flag: str, own: str, started: float) -> None:
    """Remove the temp files other `set` runs left behind (killed before their own clean-up): `<flag>.tmp.<pid>` of
    another pid, and the older single `<flag>.tmp`, last changed more than STALE_S seconds before this run started
    (a set running at the same time keeps its own). Each is judged by lstat and unlinked, never opened or followed (a
    FIFO there never hangs, a link's target is never touched); a directory is left alone. Best effort: one that
    cannot be removed stays."""
    base = os.path.basename(flag)
    name = re.compile(re.escape(base) + r"\.tmp(\.[0-9]+)?")
    try:
        entries = list(os.scandir(os.path.dirname(flag)))
    except OSError:
        return
    for e in entries:
        if e.path == own or not name.fullmatch(e.name):
            continue
        try:
            if not e.is_dir(follow_symlinks=False) and e.stat(follow_symlinks=False).st_mtime < started - STALE_S:
                os.remove(e.path)
        except OSError:
            pass


def main(argv: list[str]) -> int:
    started = time.time()
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
        paused, kind = bt.pause_state(flag)   # the flag is renamed into place: never onto a special file
        if kind:
            bt.die(TOOL, f"not set: {flag} is {kind}, not a regular file (it already counts as a pause; remove it "
                         f"({bt.pause_removal(kind)}), then set again)", 1)
        at = field(flag, "paused_at") if os.path.isfile(flag) else ""
        at = at or bt.utc(int(os.environ.get("BOA_PAUSE_NOW") or time.time()))
        tmp = f"{flag}.tmp.{os.getpid()}"   # per process: two sets at once never share (and remove) one temp file
        remove_stale_temps(flag, tmp, started)
        if os.path.isdir(tmp) and not os.path.islink(tmp):
            bt.die(TOOL, f"not set: {tmp} (the flag's temp path) is a directory: remove it by hand, then set again", 1)
        if os.path.lexists(tmp):   # a leftover (a FIFO, a link, a file): removed, never opened or written through
            try:
                os.remove(tmp)
            except OSError as exc:
                bt.die(TOOL, f"not set: the leftover temp file {tmp} could not be removed ({exc.strerror or exc})", 1)
        try:   # the name is known before the file exists: any way out removes a leftover temp file
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
                         | getattr(os, "O_BINARY", 0), 0o600)   # O_BINARY: no CRLF from the Windows C runtime
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
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
            if os.path.isdir(flag) and not os.path.islink(flag):
                bt.die(TOOL, f"not cleared: {flag} is a directory, not the flag file (remove it by hand)", 1)
            try:
                os.remove(flag)
            except OSError as exc:
                bt.die(TOOL, f"not cleared: {flag} could not be removed ({exc.strerror or exc})", 1)
            print(f"pause-flag: cleared ({flag})")
        else:
            print("pause-flag: was not set")
    elif cmd == "status":
        if args:
            return usage()
        paused, kind = bt.pause_state(flag)   # as the pause guard sees it: anything there is a pause
        if paused and kind:
            print(f"PAUSED: the flag {flag} is {kind}, not a regular file (not read): remove it "
                  f"({bt.pause_removal(kind)}) to resume")
        elif paused:
            print(f"PAUSED since {field(flag, 'paused_at')}: {field(flag, 'reason')}")
        else:
            print("not paused")
            return 4
    else:
        return usage()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
