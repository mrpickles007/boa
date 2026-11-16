"""BOA tool runtime: what every lead and lane tool needs, in one place (Python 3 standard library only).

Purpose:  the shared start-up of the lead and lane tools: the tool's home, its checkout, the project's main checkout,
          every BOA_* config key with its default, and the small helpers they share (task ids, dates, locked appends,
          bounded child processes, generated sections).
When:     imported by the tools under tools/ (never run on its own).
Wire:     nothing to wire: it lives next to the tools (`.boa/tools/`).
Verify:   every tool suite exercises it; `python3 -I .boa/tools/boa_tool.py --selftest` runs its own checks.
Outputs:  none.
Limits:   dates are the UTC `YYYY-MM-DDTHH:MM:SSZ` form only.

init(file) -> Env:
  home      the directory holding bin/ and tools/ (the installed `.boa/`, or `core/` in the package)
  checkout  the git checkout holding home (a lane worktree when the tool runs from one)
  root      the project's main checkout, also when the checkout is a linked worktree, so every lane and the lead share
            one set of logs and one lead dir (env BOA_ROOT overrides, mainly for tests)
  cfg       every BOA_* key, read by boa_config.load (the one config reader: the environment wins, then
            `<home>/config.env`, env BOA_CONFIG overrides the path), then the defaults (DEFAULTS and the derived ones of
            `_derive`) for every key unset or empty
Task ids are always T-NNN (T- and at least three digits, an optional lower-case letter); merge trains are TRAIN-<n>.
"""

from __future__ import annotations

import calendar
import contextlib
import os
import re
import subprocess
import sys
import time

sys.dont_write_bytecode = True   # no __pycache__ next to the installed tools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_config  # noqa: E402  (sibling module; `python3 -I` leaves the script directory off sys.path)

TASK_RE = r"T-[0-9]{3,}[a-z]?"
TRAIN_RE = r"TRAIN-[0-9]+"
DEFAULTS = dict(boa_config.DEFAULTS)
DEFAULTS.update({
    "BOA_BRANCH_GRAMMAR": "m<ms>/<task>-<slug>", "BOA_MAIN_BRANCH": "main", "BOA_REMOTE": "origin",
    "BOA_LEAD_DIR": ".lead", "BOA_LOG_DIR": ".boa/logs", "BOA_STATE_DIR": ".boa/state", "BOA_NAME_PREFIX": "boa-",
    "BOA_DEP_DIRS": "", "BOA_DEP_PRIVATE": "", "BOA_SPARSE_EXCLUDES": "",
    "BOA_ACTIVE_CONTEXT": "memory-bank/active-context.md", "BOA_LANE_CAP": "2", "BOA_LANE_MEM_MB": "2560",
    "BOA_ADMIT_MIN_MEM_MB": "2048", "BOA_ADMIT_MAX_LOAD": "", "BOA_FORGE": "none", "BOA_PYTHON": "python3",
})


class ToolError(Exception):
    """A usage or configuration error: the tool prints `<tool>: <message>` and exits 2."""


def die(tool: str, msg: str, code: int = 2) -> None:
    print(f"{tool}: {msg}", file=sys.stderr)
    raise SystemExit(code)


def git(*args: str, cwd: str | None = None, timeout: float = 30) -> str | None:
    """stdout of a git command, None when git is missing or the command fails."""
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "project"


class Env:
    def __init__(self, script: str):
        self.script = os.path.realpath(script)
        self.home = os.path.dirname(os.path.dirname(self.script))
        top = (git("-C", self.home, "rev-parse", "--show-toplevel") or "").strip()
        self.checkout = top or os.path.dirname(self.home)
        if os.environ.get("BOA_ROOT"):
            self.root = os.path.realpath(os.environ["BOA_ROOT"])
        else:
            try:
                self.root = boa_config.main_of(self.checkout)
            except boa_config.ConfigError as exc:
                raise ToolError(f"cannot resolve the main checkout of {self.checkout}: {exc}") from exc
        try:
            cfg = boa_config.load(self.home)
        except boa_config.ConfigError as exc:
            raise ToolError(str(exc)) from exc
        except (OSError, UnicodeDecodeError) as exc:
            raise ToolError(f"cannot read the config: {exc}") from exc
        self.cfg = cfg
        self._derive()

    def _derive(self) -> None:
        c = self.cfg   # every default applies when the key is unset or empty (the shell's ${KEY:=default})
        for k, v in DEFAULTS.items():
            if not c.get(k):
                c[k] = v
        if not c.get("BOA_PROJECT_NAME"):
            c["BOA_PROJECT_NAME"] = os.path.basename(self.root.rstrip("/\\")) or self.root
        if not c.get("BOA_PROJECT_SLUG"):
            c["BOA_PROJECT_SLUG"] = _slug(c["BOA_PROJECT_NAME"])
        if not c.get("BOA_WT_DIR"):
            c["BOA_WT_DIR"] = f"../{c['BOA_PROJECT_SLUG']}-wt"
        if not c.get("BOA_LABEL_KEY"):
            c["BOA_LABEL_KEY"] = f"com.{c['BOA_PROJECT_SLUG']}.lane"

    def __getitem__(self, key: str) -> str:
        return self.cfg.get(key, "")

    def path(self, p: str) -> str:
        """Absolute and lexically normalized (symlinks not resolved); relative paths lie under the root. On Windows a
        Git Bash drive path written in the config (`/c/x`) is that drive's path (`C:/x`), not `<root>\\c\\x`."""
        if os.name == "nt":
            p = re.sub(r"^/([A-Za-z])(?=/|$)", lambda m: m.group(1).upper() + ":", p)
        return os.path.normpath(p if os.path.isabs(p) else os.path.join(self.root, p))


def init(script: str, tool: str) -> Env:
    try:
        return Env(script)
    except ToolError as exc:
        die(tool, str(exc))
        raise  # unreachable


# --- names and ids -----------------------------------------------------------------------------------------------

def branch_re(grammar: str, task: str) -> str:
    """The branch grammar as an anchored regex: <ms> digits, <task> the given text, <slug> a lower-case slug."""
    out, g = "", grammar
    while g:
        if g.startswith("<ms>"):
            out, g = out + "[0-9]+", g[4:]
        elif g.startswith("<task>"):
            out, g = out + f"({task})", g[6:]
        elif g.startswith("<slug>"):
            out, g = out + "[a-z0-9][a-z0-9-]*", g[6:]
        else:
            c, g = g[0], g[1:]
            out += c if re.fullmatch(r"[A-Za-z0-9/_-]", c) else f"[{re.escape(c)}]"
    return f"^{out}$"


# --- time --------------------------------------------------------------------------------------------------------

def utc(epoch: float) -> str:
    """YYYY-MM-DDTHH:MM:SSZ (the datetime of memory blocks and of every ledger)."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(epoch)))


def from_utc(ts: object) -> int | None:
    """Epoch seconds of a YYYY-MM-DDTHH:MM:SSZ string; None for anything else."""
    if not isinstance(ts, str):
        return None
    try:
        return calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
    except (ValueError, OverflowError):
        return None


# --- files -------------------------------------------------------------------------------------------------------

def append_locked(path: str, text: str, wait: float = 3.0, dir_mode: int | None = None, file_mode: int = 0o600) -> None:
    """Append `text` to `path` under the file's lock (bounded wait; a sidecar `<path>.lock` where locks are mandatory,
    i.e. Windows, removed after the append when no other writer holds it open), setting the modes on every append (also
    when the file or its directory already existed)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import boa_lock
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="") as fh:
        try:
            if dir_mode is not None:
                os.chmod(d, dir_mode)
            os.chmod(path, file_mode)
        except OSError:
            pass
        sidecar = None if boa_lock._impl() == "fcntl" else path + ".lock"
        with boa_lock.FileLock(sidecar or path, timeout=wait):
            fh.write(text)
            fh.flush()
    if sidecar:
        # no sidecar left behind (it would outlive an uninstall): Windows refuses to delete a file another process has
        # open, so it goes only when no waiter holds it, and a later writer simply creates a new one
        try:
            os.remove(sidecar)
        except OSError:
            pass


_STOP_SIGNALS = ("SIGTERM", "SIGINT", "SIGHUP")


@contextlib.contextmanager
def held_stop_signals():
    """TERM, INT and HUP held (POSIX, main thread) while a resource is created and recorded: a stop that lands then
    is delivered right after the block, when the caller's cleanup can see the resource. The pattern is
    `x = None; try: with held_stop_signals(): x = create(); ... finally: cleanup(x)`; hold only the creation and
    the recording, never a call that may block (a pipe write, a wait). Yields the `preexec_fn` a process started
    inside must use, so the child does not inherit the held signals (None where nothing is held).
    It holds only while no other thread of the process has these signals unblocked: a process-directed signal goes
    to any thread that does not block it, so every worker thread blocks them as its first action
    (signal.pthread_sigmask(SIG_BLOCK, ...))."""
    import signal
    import threading
    sigs = {getattr(signal, n) for n in _STOP_SIGNALS if hasattr(signal, n)}
    if not sigs or not hasattr(signal, "pthread_sigmask") or threading.current_thread() is not threading.main_thread():
        yield None
        return
    old = signal.pthread_sigmask(signal.SIG_BLOCK, sigs)
    try:
        yield lambda: signal.pthread_sigmask(signal.SIG_UNBLOCK, sigs)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old)


class Bounded:
    """A command bounded in time, started at once (several can run side by side): its stdout goes to a named temp
    file `boa-<tag>.*` in BOA_LEAD_TMPDIR (default the system temp dir), not a pipe, so a child left running past the
    limit can't hold the caller; on POSIX it runs in a session of its own, so a timeout ends it with everything it
    started. `result()` waits up to the limit and returns (exit status or None on a timeout, stdout); the temp file is
    removed then (and by `close()`, which the callers run on every exit path). The file and the process are created
    with the stop signals held, and anything that goes wrong in the constructor (a stop, an error) closes what it
    made before it is raised again: nothing is left behind by a half-built object. A caller keeps the object in a
    variable assigned inside `held_stop_signals()` (see run_bounded)."""

    def __init__(self, argv: list[str], timeout: float, cwd: str | None = None, env: dict | None = None,
                 stdin_text: str | None = None, tag: str = "run", errors: str = "replace",
                 stderr_through: bool = False, grace: float = 1.0):
        import tempfile
        self.grace = grace   # how long a stopped child gets to clean up before KILL (see _kill_tree)
        self.p: "subprocess.Popen | None" = None
        self.out = None
        self.stdin_text = stdin_text   # written by result(), outside any held signals (a full pipe may block)
        self.errors = errors
        self.deadline = time.monotonic() + timeout
        try:
            with held_stop_signals() as release:
                self.out = tempfile.NamedTemporaryFile(mode="w+b", prefix=f"boa-{tag}.", delete=False,
                                                       dir=os.environ.get("BOA_LEAD_TMPDIR") or None)
                try:
                    self.p = subprocess.Popen(argv, cwd=cwd, env=env, stdout=self.out,
                                              stderr=None if stderr_through else subprocess.DEVNULL,
                                              stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
                                              start_new_session=os.name != "nt", preexec_fn=release)
                except OSError:
                    self.p = None
        except BaseException:   # a stop or an error mid-construction: end what was started, remove the file
            self.close()
            raise

    def result(self) -> tuple[int | None, str]:
        rc: int | None = 127
        try:
            if self.p is not None and self.stdin_text is not None:
                text, self.stdin_text = self.stdin_text, None
                try:
                    self.p.stdin.write(text.encode())
                    self.p.stdin.close()
                except OSError:
                    pass
            if self.p is not None:
                try:
                    rc = self.p.wait(timeout=max(self.deadline - time.monotonic(), 0.01))
                except subprocess.TimeoutExpired:
                    _kill_tree(self.p, self.grace)
                    rc = None
            self.out.seek(0)
            text = self.out.read().decode("utf-8", self.errors)
        finally:
            self.close()
        return rc, text

    def close(self) -> None:
        if self.p is not None and self.p.poll() is None:
            _kill_tree(self.p, self.grace)
        if self.out is not None:
            try:
                self.out.close()
                os.unlink(self.out.name)
            except OSError:
                pass


def run_bounded(argv: list[str], timeout: float, cwd: str | None = None, env: dict | None = None,
                stdin_text: str | None = None, tag: str = "run", errors: str = "replace",
                stderr_through: bool = False, grace: float = 1.0) -> tuple[int | None, str]:
    """(exit status or None on a timeout, stdout decoded with `errors`) of a command bounded in time (see Bounded);
    its stderr is discarded, or with stderr_through goes to ours (a command's own error message for the user);
    `grace`: how long a stopped child gets to clean up (the hook paths pass HOOK_GRACE)."""
    b = None
    try:
        with held_stop_signals():
            b = Bounded(argv, timeout, cwd, env, stdin_text, tag, errors, stderr_through, grace)
        return b.result()
    finally:
        if b is not None:
            b.close()


def on_term_exit(code: int | None = None) -> None:
    """TERM, INT and HUP end the process through SystemExit, so `finally` blocks (temp files, children) run. Every
    entry point that creates a temp file or a child process calls it first. `code`: the exit status to end with (a
    hook passes 0: it never fails the runtime); default 128 + the signal."""
    import signal

    def _exit(signum, _frame):
        raise SystemExit(128 + signum if code is None else code)
    for name in ("SIGTERM", "SIGINT", "SIGHUP"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _exit)


HOOK_GRACE = 0.2   # seconds a hook path's child gets to clean up: a session start stays well inside its hook timeout


def _kill_tree(p: "subprocess.Popen", grace: float = 1.0) -> None:
    """End a process started in a session of its own with everything in that session: TERM first, so a tool that
    handles it (on_term_exit) still removes its own temp files and children, then, once it is gone or after `grace`
    seconds, KILL for whatever is left in the session."""
    import signal
    if os.name == "nt":
        try:
            p.kill()
        except OSError:
            pass
    else:
        try:
            os.killpg(p.pid, signal.SIGTERM)
        except OSError:
            pass
        try:
            p.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        p.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


# --- generated sections and files -------------------------------------------------------------------------------

def replace_generated(text: str, begin: str, end: str, body: str) -> str:
    """`text` with every generated section (a `begin` marker line ... an `end` marker line) holding `body`; ValueError
    on a begin marker without its end."""
    out, i = [], 0
    lines = text.split("\n")
    while i < len(lines):
        out.append(lines[i])
        if lines[i].strip() == begin:
            j = i + 1
            while j < len(lines) and lines[j].strip() != end:
                j += 1
            if j == len(lines):
                raise ValueError(f"a '{begin}' line without its '{end}' line")
            out += body.rstrip("\n").split("\n")
            out.append(lines[j])
            i = j
        i += 1
    return "\n".join(out)


def toplevel(path: str) -> str:
    """The checkout (the main one or a linked worktree) that holds `path`: its git top level; outside git, the directory
    itself. Never the main checkout of a worktree: a tool run in a lane changes the lane's files only."""
    d = path if os.path.isdir(path) else (os.path.dirname(path) or ".")
    top = (git("-C", d, "rev-parse", "--show-toplevel") or "").strip()
    return top or os.path.realpath(d)


def write_atomic(path: str, text: str) -> None:
    """Replace a file's content all at once: a temp file beside it (the file's own mode kept), then os.replace; an
    interruption leaves the old file whole and no temp file behind."""
    import tempfile
    tmp = None
    try:
        with held_stop_signals():   # the name is recorded before a stop can land (the finally below)
            fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".tmp.", dir=os.path.dirname(path) or ".")
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        try:
            os.chmod(tmp, os.stat(path).st_mode & 0o7777)
        except OSError:
            pass
        os.replace(tmp, path)
    finally:
        if tmp is not None and os.path.exists(tmp):
            os.remove(tmp)


def tracked_files_with(root: str, marker: str) -> list[str]:
    """The files git tracks under `root` that hold `marker` (absolute paths)."""
    out = git("-C", root, "grep", "-l", "-F", "-z", marker) or ""
    return [os.path.join(root, f) for f in out.split("\0") if f]


def help_text(doc: str | None) -> str:
    return (doc or "").strip("\n") + "\n"


def _selftest() -> int:
    assert re.match(branch_re("m<ms>/<task>-<slug>", "T-001"), "m1/T-001-ab-c")
    assert from_utc("2026-11-02T10:00:00Z") == 1793613600 and from_utc("x") is None and utc(1793613600) == "2026-11-02T10:00:00Z"
    assert replace_generated("a\n<b>\nold\n<e>\nz", "<b>", "<e>", "new\n") == "a\n<b>\nnew\n<e>\nz"
    print("boa_tool selftest: ok")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        raise SystemExit(_selftest())
    sys.stdout.write(help_text(__doc__))
