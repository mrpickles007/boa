#!/usr/bin/env -S python3 -I
"""The project's configuration and paths, and the shared entry point, for the safety hooks (guard_destructive,
pause_guard). Python standard library only; the hooks load this file by path (they run under `python3 -I`, which
keeps their own directory off sys.path).

The guards' entry point (run_guard): read ONE neutral pre-tool event (references/hook-contract.md) from stdin, judge
it under a watchdog, print ONE neutral verdict ({"decision": "deny", "reason", "context", "message"}) when it
refuses. Every guard FAILS CLOSED: an event that is not a well-formed neutral event (not one JSON object, an unknown
event name or tool kind, a missing command/file_path), a hook not installed in a checkout, an internal error or no
verdict within the watchdog refuses the call, and the reason names the lead's escape: a shell command of the lead
that starts with <BOA_ENV_PREFIX>GUARD_LEAD_VERIFIED=<reason> (3+ of [A-Za-z0-9_.-]) and a blank is then allowed and
logged (ESCAPE) in <BOA_LOG_DIR>/guard-denials.jsonl. A neutral event other than pre-tool is not judged (no output).

Where the project is (derived at run time, never hard-coded):
  REPO     the main checkout of the repository that holds the hook file (<repo>/.boa/hooks/<hook>.py), read from
           .git, never by running git; never taken from the payload (a forged or nested checkout cannot re-root it)
  CONFIG   <REPO>/.boa/config.env, read through the one reader every BOA tool uses (<REPO>/.boa/tools/boa_config.py,
           parse: the strict grammar; never sourced, never expanded); a missing file or key takes the default in
           DEFAULTS; a line outside the grammar, or a missing reader, fails load() and the guards refuse (fail closed)
  WT       the lane worktrees: BOA_WT_DIR, relative to REPO unless absolute (default ../<slug>-wt)
  SCRATCH  BOA_SCRATCH_ROOT (the agent runtime's own temp dir for this project, set when the agent wires its
           runtime) when it is strictly inside /tmp/, /var/tmp/ or the home dir and not an ancestor of the home dir,
           REPO, the projects dir or WT, else BOA's own fallback <temp>/.boa-<uid>/<REPO's path, every non-alphanumeric
           -> '-'> (<temp>: /tmp, the system temp dir on Windows), a directory no runtime uses, so nothing there is
           taken for an agent's scratch until the root is configured
  PROJECTS the projects dir: REPO's parent (every other directory in it is another project)
  RUNTIME  BOA_RUNTIME_CONFIG: the top-level names in REPO that hold the agent runtime's own configuration (its
           settings directory, its instruction file); nobody writes them from a shell, sub-agents never touch them
Every name derives from REPO itself, never from the payload (a payload's cwd such as <main>/x would name the scratch
root after a sibling directory). Path keys are validated (relative, no '..'); an invalid value falls back to its
default. $TMPDIR is deliberately NOT used: its parent could be /tmp itself, which would make all of /tmp deletable.

`<BOA_PYTHON> -I .boa/hooks/hook_config.py` prints the derived values as JSON (an install self-check).
"""
import faulthandler
import io
import json
import os
import posixpath
import pathlib
import re
import sys
import tempfile
import threading
import time

DEFAULTS = {
    "BOA_PROJECT_SLUG": "",                  # derived from REPO's name when empty
    "BOA_TASK_PREFIX": "T-",
    "BOA_BRANCH_GRAMMAR": "m<ms>/<task>-<slug>",
    "BOA_MAIN_BRANCH": "main",
    "BOA_WT_DIR": "../<slug>-wt",
    "BOA_LEAD_DIR": ".lead",
    "BOA_SCRATCH_ROOT": "",
    "BOA_NAME_PREFIX": "boa-",
    "BOA_LABEL_KEY": "",                     # com.<slug>.lane when empty
    "BOA_ENV_PREFIX": "BOA_",
    "BOA_FORGE": "github",
    # safety keys (each with this default)
    "BOA_PROTECTED_DIRS": ".git",            # top-level dirs of any checkout nobody deletes or writes into
    "BOA_PROTECTED_MAIN": "memory-bank .env AGENTS.md logs .boa",  # + BOA_LEAD_DIR and BOA_RUNTIME_CONFIG
    "BOA_RUNTIME_CONFIG": "",                # the runtime's own config names in the main checkout (set at wiring)
    "BOA_SUBAGENT_MAIN_WRITES": "logs/",     # main-checkout prefixes a sub-agent may write (dir/ or name prefix)
    "BOA_LOG_DIR": ".boa/logs",             # the logs (guard denials)
    "BOA_STATE_DIR": ".boa/state",
}
CONFIG_REL = os.path.join(".boa", "config.env")
_READER = []   # boa_config, loaded once on first use


def reader():
    """The ONE config.env reader (boa_config.parse): <hooks dir>/../tools/boa_config.py, loaded by path (the hooks
    run under `python3 -I`). Raises when it is missing or broken: the guards then refuse (fail closed)."""
    if not _READER:
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "boa_config.py")
        spec = importlib.util.spec_from_file_location("boa_hook_boa_config", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"the config reader {path} cannot be loaded")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _READER.append(module)
    return _READER[0]


def parse_env(path):
    """The KEY=value pairs of config.env read through boa_config.parse (the strict grammar every BOA tool reads; never
    sourced, never expanded). {} when the file does not exist; a line outside the grammar, an unreadable file or a
    missing reader raises (load() fails, so a guard refuses every call naming the line: fail closed)."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        return {}
    return reader().parse(text, path)


def main_checkout(start):
    """Main worktree of the git repository that holds start, or None.

    A directory with a .git directory is a main checkout. A .git file ("gitdir: <main>/.git/worktrees/<name>")
    marks a linked worktree, whose main checkout is <main>. Anything else (a submodule, garbage) is None.
    """
    if not start or not os.path.isabs(start):
        return None
    d = os.path.normpath(start)
    while True:
        g = os.path.join(d, ".git")
        if os.path.isdir(g):
            return d
        if os.path.isfile(g):
            try:
                with open(g, encoding="utf-8") as fh:
                    m = re.match(r"gitdir:\s*(\S.*?)\s*$", fh.read(4096))
            except (OSError, UnicodeDecodeError):
                return None
            if not m:
                return None
            gitdir = os.path.normpath(os.path.join(d, m.group(1)))
            parent = os.path.dirname(gitdir)
            if os.path.basename(parent) == "worktrees" and os.path.basename(os.path.dirname(parent)) == ".git":
                return os.path.dirname(os.path.dirname(parent))
            return None
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up


def mangle(path):
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.normpath(path))


def words(value):
    return [w for w in (value or "").split() if w]


def task_regex(prefix):
    """The task id grammar: <prefix><digits>[one lower-case letter]."""
    return re.escape(prefix) + r"\d+[a-z]?"


def branch_lane_regex(grammar, prefix):
    """A compiled regex matching a lane branch name (refs/heads/ optional): the branch grammar up to and including
    its <task> placeholder (m<ms>/<task>-<slug> -> m\\d+/T-\\d+[a-z]?), followed by the end, '-' or '/'. A grammar
    without <task> is used whole, its other placeholders as one path-free word each."""
    g = grammar.split("<task>", 1)
    head = g[0] + ("<task>" if len(g) > 1 else "")
    out, i = [], 0
    for m in re.finditer(r"<([a-z]+)>", head):
        out.append(re.escape(head[i:m.start()]))
        out.append({"ms": r"\d+", "task": task_regex(prefix)}.get(m.group(1), r"[A-Za-z0-9._-]+"))
        i = m.end()
    out.append(re.escape(head[i:]))
    return re.compile(r"^(?:refs/heads/)?" + "".join(out) + r"(?:$|[-/])")


def branch_glob(grammar):
    """The branch grammar as a shell glob (every placeholder -> *): the shape the permission allowlist uses."""
    return re.sub(r"<[a-z]+>", "*", grammar)


def _safe_name(value, default, pattern=r"[A-Za-z0-9][A-Za-z0-9._-]+"):
    return value if value and re.fullmatch(pattern, value) else default


SAFE_REL = re.compile(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*/?")


def rel_paths(value, default, refuse=()):
    """Relative paths of a config value: each must be a plain relative path (no '..', not absolute, safe characters)
    whose first component is not in refuse; the invalid ones are dropped, and none left means the default."""
    out = []
    for w in words(value):
        top = w.split("/", 1)[0]
        if SAFE_REL.fullmatch(w) and ".." not in w.split("/") and top not in ("", ".") and top not in refuse \
                and not top.startswith(".env"):
            out.append(w)
    return tuple(out) or tuple(words(default))


def path_depth(path):
    """The number of components of an absolute path below its root, on any OS: `/` and `\\` both separate, a drive
    (`C:`) or a UNC share (`//server/share`) is the root. `/srv/x` and `C:\\Users\\x` are 2 deep; `/`, `C:\\`, `/srv`
    are not 2 deep. A path that is not absolute is 0 deep."""
    p = (path or "").replace("\\", "/")
    m = re.match(r"^(?://[^/]+/[^/]+|[A-Za-z]:)(?=/|$)", p)
    if m:
        p = p[m.end():]
    if not p.startswith("/"):
        return 0
    return len([c for c in p.split("/") if c and c != "."])


WINDOWS = os.name == "nt"
CASE_INSENSITIVE = WINDOWS or sys.platform == "darwin"   # the default file systems of Windows and macOS


def on_windows(windows=None):
    """True on Windows; `windows` overrides it (tests simulate the other OS)."""
    return WINDOWS if windows is None else windows


def fold_name(name, ci=None):
    """A top-level name as the file system compares it: case-folded where it ignores case (Windows, macOS; `ci`
    overrides it for tests), as is elsewhere. The guards compare their protected names (.git, .boa, .env*, the main
    checkout's protected names, the runtime's configuration names) through it."""
    return name.casefold() if (CASE_INSENSITIVE if ci is None else ci) else name


def expanduser(p, env=None):
    """`~` and `~/x` from HOME, as the shell expands them (on Windows os.path.expanduser reads USERPROFILE, while the
    agent's Git Bash expands HOME, the home the guards must see); `~user` and the rest as os.path.expanduser."""
    if p == "~" or p.startswith("~/") or (on_windows() and p.startswith("~\\")):   # `\\` separates on Windows only
        home = (os.environ if env is None else env).get("HOME")
        if home:
            return home.rstrip("/\\") + p[1:]
    return os.path.expanduser(p)


def slash(p, windows=None):
    """A path in the guards' one form: as written on POSIX; on Windows `\\` becomes `/`, an MSYS drive path `/c/x`
    becomes `C:/x` and a drive letter is upper case (the form a POSIX shell's words and os.path both map to, so the
    guards' path rules hold on every OS). The rest of the letter case is kept: the guards compare whole paths as
    written (a path spelt in another case reads as another path: a known limit, on the refusing side of the rules that
    need a known root) and only the protected top-level names case-insensitively where the file system is (fold_name)."""
    if not p or not on_windows(windows):
        return p
    p = p.replace("\\", "/")
    m = re.match(r"^(?:/([A-Za-z])(?=/|$)|([A-Za-z]):)", p)
    return (m.group(1) or m.group(2)).upper() + ":" + p[m.end():] if m else p


def is_abs(p, windows=None):
    """p is absolute in the guards' form: it starts at the root (`/`), or on Windows at a drive (`C:`)."""
    p = slash(p, windows)
    return p.startswith("/") or bool(on_windows(windows) and re.match(r"[A-Za-z]:(?:/|$)", p))


def parts(p, windows=None):
    """The components of p: split on `/` (and on Windows on `\\` too)."""
    return slash(p, windows).split("/")


def inside(path, root, windows=None):
    """path is root or below it, compared component-wise in the guards' form (both normalised, no '..')."""
    p, r = slash(path, windows), slash(root, windows)
    return p == r or p.startswith(r.rstrip("/") + "/")


def strictly_inside(path, root, windows=None):
    """path is below root, not root itself (see inside)."""
    return slash(path, windows) != slash(root, windows) and inside(path, root, windows)


def uid_name():
    """The user's id for the fallback scratch root (.boa-<uid>); the user name where the OS has no uid."""
    getuid = getattr(os, "getuid", None)
    if getuid is not None:
        return str(getuid())
    try:
        import getpass
        user = getpass.getuser()
    except Exception:   # noqa: BLE001 - no user name: a fixed fallback still names one root
        user = "user"
    return re.sub(r"[^A-Za-z0-9]", "-", user) or "user"


def scratch_root(value, name, guarded, home, ci=None):
    """BOA_SCRATCH_ROOT when it is an absolute path strictly inside /tmp/, /var/tmp/ or the home dir, and not an
    ancestor of (or equal to) one of the guarded paths (the home dir, the repository, the projects dir, the worktrees
    dir), else BOA's fallback <temp>/.boa-<uid>/<name> (<temp>: /tmp, the system temp dir on Windows). A system dir
    (/var/lib, /opt, /etc) is never a scratch root. Compared without regard to case where the file system ignores it
    (Windows, macOS; `ci` overrides it for tests): C:/Users/dev/PROJECTS is the projects dir C:/Users/dev/projects."""
    # in the guards' slash form (Windows: a Git Bash /c/x is C:/x, which os.path.isabs of Python 3.13+ no longer takes
    # for absolute once normpath has made it \c\x; HOME may reach Python spelt either way)
    scratch = posixpath.normpath(slash(expanduser(value, {"HOME": home} if home else None))) if value else ""
    roots = ["/tmp", "/var/tmp"] + ([posixpath.normpath(slash(home))] if home and is_abs(home) and path_depth(home) >= 2
                                    else [])
    fold = str.casefold if (CASE_INSENSITIVE if ci is None else ci) else str
    if is_abs(scratch) and any(strictly_inside(fold(scratch), fold(r)) for r in roots) \
            and not any(inside(fold(slash(g)), fold(scratch)) for g in guarded if g):
        return scratch
    temp = tempfile.gettempdir() if on_windows() else "/tmp"
    return os.path.join(temp, ".boa-" + uid_name(), name)   # not under a /tmp/<name prefix> lane path


def load(here=None, env=None, ci=None):
    """The configuration as a dict of derived values; None when the hook is not installed in a checkout (the guards
    then refuse). The repository is the one holding the hook file (<repo>/.boa/hooks/<hook>.py), never one named by
    the payload (a nested or forged checkout cannot re-root it). A worktrees dir that is the repository or inside it is
    refused in any letter case where the file system ignores case (`ci` overrides CASE_INSENSITIVE for tests)."""
    env = os.environ if env is None else env
    here = here or os.path.abspath(__file__)
    repo = main_checkout(os.path.dirname(os.path.dirname(os.path.dirname(here))))
    # a checkout at / or one level below would put the whole host "inside the project"
    if not repo or path_depth(repo) < 2:
        return None
    conf = dict(DEFAULTS)
    conf.update({k: v for k, v in parse_env(os.path.join(repo, CONFIG_REL)).items() if k.startswith("BOA_")})
    slug = _safe_name(conf["BOA_PROJECT_SLUG"], re.sub(r"[^a-z0-9-]+", "-", os.path.basename(repo).lower()).strip("-")
                      or "project")
    home = env.get("HOME") or os.path.expanduser("~")
    wt = expanduser(conf["BOA_WT_DIR"].replace("<slug>", slug) or "../%s-wt" % slug, env)
    # a Git Bash drive path (/c/x) is absolute; os.path.isabs of Python 3.13+ on Windows would join it under the repo
    wt = slash(wt)
    wt = os.path.normpath(wt if is_abs(wt) else os.path.join(repo, wt))
    fold = str.casefold if (CASE_INSENSITIVE if ci is None else ci) else str
    if path_depth(wt) < 2 or inside(fold(slash(repo)), fold(slash(wt))):
        wt = os.path.join(os.path.dirname(repo), slug + "-wt")
    name = mangle(repo)
    scratch = scratch_root(conf["BOA_SCRATCH_ROOT"], name,
                           (os.path.normpath(home) if home else "", repo, os.path.dirname(repo), wt), home, ci)
    prefix = _safe_name(conf["BOA_TASK_PREFIX"], "T-", r"[A-Za-z][A-Za-z0-9_-]{0,15}")
    name_prefix = _safe_name(conf["BOA_NAME_PREFIX"], "boa-")
    label = _safe_name(conf["BOA_LABEL_KEY"], "com.%s.lane" % slug)
    lead_dir = (pathlib.PurePath(os.path.normpath(conf["BOA_LEAD_DIR"] or ".lead")).parts or ("",))[0]
    if lead_dir in ("", ".", "..") or not re.fullmatch(r"[A-Za-z0-9._-]+", lead_dir):
        lead_dir = ".lead"
    runtime = tuple(w.rstrip("/") for w in rel_paths(conf["BOA_RUNTIME_CONFIG"], "") if "/" not in w.rstrip("/"))
    never = (".git", ".boa", lead_dir) + runtime   # never a place sub-agents write into
    return {
        "repo": repo, "wt": wt, "scratch": scratch, "runtime_config": runtime,
        "projects": os.path.dirname(repo), "config": os.path.join(repo, CONFIG_REL), "slug": slug,
        "task_prefix": prefix, "task_re": task_regex(prefix),
        "branch_re": branch_lane_regex(conf["BOA_BRANCH_GRAMMAR"] or DEFAULTS["BOA_BRANCH_GRAMMAR"], prefix),
        "branch_glob": branch_glob(conf["BOA_BRANCH_GRAMMAR"] or DEFAULTS["BOA_BRANCH_GRAMMAR"]),
        "main_branch": _safe_name(conf["BOA_MAIN_BRANCH"], "main", r"[A-Za-z0-9][A-Za-z0-9._/-]*"),
        "lead_dir": lead_dir, "name_prefix": name_prefix, "label_key": label,
        "label_ns": label.rsplit(".", 1)[0] + "." if "." in label else label,
        "env_prefix": _safe_name(conf["BOA_ENV_PREFIX"], "BOA_", r"[A-Z][A-Z0-9_]*"),
        "forge": conf["BOA_FORGE"],
        "protected_any": tuple(sorted(set(rel_paths(conf["BOA_PROTECTED_DIRS"], ".git")) | {".git"})),
        "protected_main": tuple(sorted(set(rel_paths(conf["BOA_PROTECTED_MAIN"], DEFAULTS["BOA_PROTECTED_MAIN"]))
                                       | {lead_dir, ".boa", ".git"} | set(runtime))),
        "sub_main_writes": rel_paths(conf["BOA_SUBAGENT_MAIN_WRITES"], DEFAULTS["BOA_SUBAGENT_MAIN_WRITES"], never),
        "log_dir": os.path.join(repo, rel_paths(conf["BOA_LOG_DIR"], DEFAULTS["BOA_LOG_DIR"])[0].rstrip("/")),
        "state_dir": os.path.join(repo, rel_paths(conf["BOA_STATE_DIR"], DEFAULTS["BOA_STATE_DIR"])[0].rstrip("/")),
    }


def checkouts(cfg):
    """The project's checkouts: the main checkout and every directory in the worktrees dir."""
    out = [cfg["repo"]]
    try:
        out += sorted(os.path.join(cfg["wt"], d) for d in os.listdir(cfg["wt"])
                      if os.path.isdir(os.path.join(cfg["wt"], d)))
    except OSError:
        pass
    return out


# ----------------------------------------------------------------------------- the guards' event, verdict, failure
# The neutral hook contract (references/hook-contract.md): a guard reads ONE neutral event (a JSON object on stdin)
# and prints ONE neutral verdict, only when it refuses. The agent's wiring builds the event from its runtime and maps
# the verdict back; no guard reads a runtime's own payload.
EVENTS = ("session-start", "session-end", "subagent-start", "subagent-stop", "stop", "pre-tool", "post-tool",
          "post-tool-failure", "permission-denied", "permission-request", "prompt")
TOOL_KINDS = ("shell", "file-write", "file-read", "sub-agent", "other")
MAX_EVENT = 4 * 1024 * 1024   # bytes of stdin read; a longer event is unreadable (refused)


class Unreadable(Exception):
    """The input is not a well-formed neutral pre-tool event: the guard refuses (fails closed)."""


class NoProject(Exception):
    """The hook file is not installed in a checkout, so it has no project to protect: it refuses (fails closed)."""


class TimedOut(Exception):
    """The guard found no verdict within its watchdog budget: it refuses (fails closed)."""


class GuardEvent:
    """A neutral pre-tool event, validated: tool kind, tool_input, the agent (empty agent_id: the lead), cwd."""

    def __init__(self, tool, tool_input, agent_id="", agent_type="", cwd=""):
        self.tool, self.input, self.agent_id, self.agent_type, self.cwd = tool, tool_input, agent_id, agent_type, cwd

    @property
    def command(self):
        return self.input.get("command", "") if self.tool == "shell" else ""


def _opt_str(data, key, where="event"):
    v = data.get(key)
    if v is None:
        return ""
    if not isinstance(v, str):
        raise Unreadable(f"{where} field '{key}' is not a string")
    return v


def parse_event(text):
    """The guard's GuardEvent; None for a neutral event that is not pre-tool (nothing to judge). Unreadable for
    anything else: not one JSON object, an unknown event name, an unknown tool kind, a missing or ill-typed field.
    Fail closed: a wiring mistake refuses calls, it never switches a guard off."""
    try:
        data = json.loads(text)
    except ValueError:
        raise Unreadable("stdin is not one JSON object") from None
    if not isinstance(data, dict):
        raise Unreadable("stdin is not one JSON object")
    ev = data.get("event")
    if not isinstance(ev, str) or ev not in EVENTS:
        raise Unreadable(f"unknown event {ev!r} (expected one of the neutral events, e.g. 'pre-tool')")
    if ev != "pre-tool":
        return None
    tool = data.get("tool")
    if tool not in TOOL_KINDS:
        raise Unreadable(f"unknown tool kind {tool!r} (expected one of {', '.join(TOOL_KINDS)})")
    ti = data.get("tool_input", {})
    if not isinstance(ti, dict):
        raise Unreadable("tool_input is not an object")
    if tool == "shell" and not isinstance(ti.get("command"), str):
        raise Unreadable("a shell event without a string tool_input.command")
    if tool == "file-write" and not (isinstance(ti.get("file_path"), str) and ti["file_path"]):
        raise Unreadable("a file-write event without tool_input.file_path")
    for key in ("file_path", "path", "glob"):
        if tool == "file-read":
            _opt_str(ti, key, "tool_input")
    return GuardEvent(tool, ti, _opt_str(data, "agent_id"), _opt_str(data, "agent_type"), _opt_str(data, "cwd"))


def deny_verdict(reason):
    """The neutral verdict that refuses the call (the same four fields every BOA hook prints)."""
    # ASCII JSON (non-ASCII as \u escapes): the verdict reads the same whatever the console's code page (Windows)
    return json.dumps({"decision": "deny", "reason": reason, "context": "", "message": ""})


def hook_repo(here):
    """The main checkout that holds the hook file, or None (the guard's project; never taken from the event)."""
    repo = main_checkout(os.path.dirname(os.path.dirname(os.path.dirname(here))))
    return repo if repo and path_depth(repo) >= 2 else None


def env_prefix_of(cfg, here):
    """The configured BOA_ENV_PREFIX, read without load() when cfg is missing (load may be what failed)."""
    if cfg:
        return cfg["env_prefix"]
    repo = hook_repo(here)
    try:
        value = parse_env(os.path.join(repo, CONFIG_REL)).get("BOA_ENV_PREFIX", "") if repo else ""
    except Exception:   # noqa: BLE001 - an unreadable config: the default prefix still names the lead's escape
        value = ""
    return _safe_name(value, "BOA_", r"[A-Z][A-Z0-9_]*")


def escape_token(event, prefix):
    """The lead's escape: a shell command of the lead (no agent_id) that starts with
    <prefix>GUARD_LEAD_VERIFIED=<reason> (3+ characters of [A-Za-z0-9_.-]) and a blank. The reason token, or None."""
    if event is None or event.agent_id or event.tool != "shell":
        return None
    m = re.match(r"^\s*" + re.escape(prefix) + r"GUARD_LEAD_VERIFIED=([\w.-]{3,})\s", event.command, re.ASCII)
    return m.group(1) if m else None


def guard_log(cfg, here, agent, tool, reason, override=None):
    """Append one record {ts, agent, tool, reason capped at 500 characters[, override]} to <log dir>/guard-denials.jsonl
    (0600; the reason can quote arguments, the command line itself is not stored): the configured log dir, else
    <repo>/.boa/logs when the configuration could not be loaded (created when missing). True when the record landed.
    A denial or a note that cannot be written goes to stderr; <env prefix>GUARD_NOLOG=1 (tests) skips them (True). An
    escape (override) is always written, NOLOG or not: when it cannot be, False, and the caller refuses the escape (an
    escape is always audited). Never raises."""
    prefix = env_prefix_of(cfg, here)
    if os.environ.get(prefix + "GUARD_NOLOG") == "1" and not override:
        return True
    rec = "{}"
    try:
        repo = cfg["repo"] if cfg else hook_repo(here)
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "agent": agent or "lead", "tool": tool,
               "reason": (reason or "")[:500]}
        if override:
            rec["override"] = override
        rec = json.dumps(rec)
        log_dir = cfg["log_dir"] if cfg else os.path.join(repo, ".boa", "logs")
        os.makedirs(log_dir, 0o700, exist_ok=True)   # a missing log dir never refuses an escape
        with open(os.path.join(log_dir, "guard-denials.jsonl"), "a", encoding="utf-8") as fh:
            os.chmod(fh.name, 0o600)
            fh.write(rec + "\n")
        return True
    except Exception:
        if override:
            return False
        try:
            sys.stderr.write("guard log unavailable: " + str(rec)[:2000] + "\n")
        except Exception:
            pass
        return False


def watchdog_s(prefix, default):
    """The guard's budget for one verdict, under the wiring's timeout: <prefix>GUARD_WATCHDOG seconds when set (only
    ever shorter, at least 0.2), else default."""
    try:
        return min(default, max(0.2, float(os.environ.get(prefix + "GUARD_WATCHDOG", default))))
    except ValueError:
        return default


BACKSTOP_S = 1.0     # after the watchdog: the process-level backstop, when the guard cannot even refuse in time


def backstop(seconds):
    """Arm (seconds) or cancel (None) the process-level backstop: faulthandler kills the process (exit 1, no verdict,
    which the wiring refuses) BACKSTOP_S after the watchdog. It runs in C, so it fires even when a regular expression
    or another C call holds the interpreter lock and the watchdog thread cannot run. Best effort: a process without a
    real stderr (an in-process test) keeps only the watchdog."""
    try:
        if seconds is None:
            faulthandler.cancel_dump_traceback_later()
        else:
            faulthandler.dump_traceback_later(seconds + BACKSTOP_S, exit=True, file=sys.__stderr__)
    except (AttributeError, ValueError, OSError, RuntimeError, io.UnsupportedOperation):
        pass


def with_watchdog(fn, seconds):
    """fn() run in a worker thread; its result, its exception re-raised, or TimedOut after seconds. The worker gets a
    large stack (deep command nesting must reach the guard's own limits, not the platform's thread stack)."""
    box = {}

    def work():
        try:
            box["value"] = fn()
        except BaseException as exc:   # noqa: BLE001 - re-raised in the caller
            box["error"] = exc

    try:
        threading.stack_size(64 * 1024 * 1024)
    except (ValueError, RuntimeError):
        pass
    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    worker.join(seconds)
    if worker.is_alive():
        raise TimedOut(f"no verdict within {seconds:g} s")
    if "error" in box:
        raise box["error"]
    return box.get("value")


def fail_closed(tag, exc, event, cfg, here):
    """The guard could not judge the call (an internal error, a timeout, an unreadable event, no project): it refuses
    it, unless it is the lead's escape and the escape is logged. Returns the verdict text to print ('' to allow)."""
    prefix = env_prefix_of(cfg, here)
    agent = event.agent_id if event else ""
    tool = event.tool if event else ""
    kind = {Unreadable: "unreadable event", TimedOut: "timeout", NoProject: "no project"}.get(type(exc), "internal error")
    detail = re.sub(r"\s+", " ", f"{type(exc).__name__}: {exc}" if kind == "internal error" else str(exc))[:300]
    token = escape_token(event, prefix)
    repo = cfg["repo"] if cfg else hook_repo(here)
    log = os.path.join(cfg["log_dir"] if cfg else os.path.join(repo or "<repo>", ".boa", "logs"), "guard-denials.jsonl")
    if token:
        if guard_log(cfg, here, "lead", tool, f"ESCAPE (guard failed: {kind}: {detail})", token):
            return ""
        return deny_verdict(f"{tag} the guard could not judge this call ({kind}: {detail}), and the lead's escape "
                            f"could not be logged in {log}: refused (an escape is always audited). Fix the log dir.")
    guard_log(cfg, here, agent, tool, f"FAIL-CLOSED ({kind}: {detail})")
    return deny_verdict(
        f"{tag} the guard could not judge this call ({kind}: {detail}) and refuses it: it fails closed. "
        f"Lead only, for a command you have proven safe: run it as `{prefix}GUARD_LEAD_VERIFIED=<reason> <command>` "
        f"(logged in {log}). Then report the guard failure so it is fixed.")


def run_guard(tag, judge, here, budget, stdin=None, stdout=None):
    """The entry point every guard shares. Reads the neutral event, loads the project configuration and runs
    judge(event, cfg) -> None (allow) or the reason to refuse, under a watchdog of budget seconds; prints the deny
    verdict when there is one. Every failure on the way (unreadable event, no project, an exception, the watchdog)
    refuses the call (fail_closed). Returns 0: the verdict, not the exit status, carries the decision. After a
    watchdog timeout it does not return: it prints the refusal and ends the process (os._exit(0)), since the worker may
    still run and hold the interpreter lock where a normal shutdown would wait on it (the backstop stays armed until
    then); callers that run a guard in-process must not let it time out."""
    stdout = stdout or sys.stdout
    event = cfg = None
    backstop(budget)
    try:
        # the event's bytes, read as UTF-8 whatever the locale (a Windows console or pipe defaults to the ANSI code
        # page), strictly: bytes that are not UTF-8 fail closed; a stdin without bytes underneath (a caller's
        # StringIO) is read as the text it is
        text = (stdin if stdin is not None else getattr(sys.stdin, "buffer", sys.stdin)).read(MAX_EVENT + 1)
        if len(text) > MAX_EVENT:
            raise Unreadable(f"event over {MAX_EVENT // (1024 * 1024)} MiB")
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        event = parse_event(text)
        if event is None:
            return 0
        cfg = load(here=here)
        if cfg is None:
            raise NoProject("the hook is not installed in a checkout (<repo>/.boa/hooks/)")
        seconds = watchdog_s(cfg["env_prefix"], budget)
        backstop(seconds)
        why = with_watchdog(lambda: judge(event, cfg), seconds)
    except BaseException as exc:   # noqa: BLE001 - every failure refuses (fail closed), SystemExit included
        if isinstance(exc, KeyboardInterrupt):
            raise
        out = fail_closed(tag, exc, event, cfg, here)
        if out:
            stdout.write(out + "\n")
            stdout.flush()
        if isinstance(exc, TimedOut):
            # the worker may still run, and may later hold the interpreter lock in C where shutdown would wait on
            # it: leave now (the verdict is out), with the backstop still armed until the very end
            sys.stderr.flush()
            os._exit(0)
        return 0
    finally:
        backstop(None)
    if why:
        stdout.write(deny_verdict(why) + "\n")
    return 0


def main(argv):
    try:
        cfg = load()
    except Exception as exc:   # noqa: BLE001 - the self-check names what the guards would refuse on
        print(f"hook_config: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if cfg is None:
        print(json.dumps(None))
        return 1
    print(json.dumps({k: (v.pattern if hasattr(v, "pattern") else sorted(v) if isinstance(v, frozenset) else v)
                      for k, v in cfg.items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
