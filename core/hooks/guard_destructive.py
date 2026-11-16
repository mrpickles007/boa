#!/usr/bin/env -S python3 -I
"""Pre-tool guard: deny destructive commands that could touch things that are not provably this project's (other
projects on this shared host, the deployed instance, the repository's protected areas), and keep sub-agents inside
their own lane. Role-aware: the lead (an event without agent_id) and sub-agents (agent_id set) get different rules.

Purpose:  refuse destructive commands on what is not provably this project's, and keep each sub-agent in its lane.
When:     on every shell, file-writing and file-reading tool call of every agent (the lead and the sub-agents).
Wire:     the agent registers it on its runtime's pre-tool event for those tools and pipes it the NEUTRAL event
          (references/hook-contract.md: {"event": "pre-tool", "tool": "shell" | "file-write" | "file-read",
          "tool_input": {"command"} | {"file_path"} | {"file_path", "path", "glob"}, "agent_id", "agent_type",
          "cwd"}): `<BOA_PYTHON> -I .boa/hooks/guard_destructive.py`, timeout 10 s; a verdict with decision "deny"
          refuses the call, and so does a non-zero exit or a timeout of the hook (the wiring must fail closed too).
Verify:   `.boa/bin/lead-status.sh --guards` prints no GUARD DOWN line for it.
Outputs:  a neutral deny verdict with its reason, or nothing; a log line in <BOA_LOG_DIR>/guard-denials.jsonl.
Limits:   a best-effort net against accidents, not a sandbox: the declared limits below are real. It FAILS CLOSED:
          an unreadable event, an internal error or no verdict within 8.5 s refuses the call, naming the lead's
          logged escape (<BOA_ENV_PREFIX>GUARD_LEAD_VERIFIED=<reason> <command>).

BEST-EFFORT SAFETY NET, NOT A SANDBOX: it lowers the odds of an accident and of a lane wandering off; it does not
contain a determined agent, and its declared limits are real. It parses the command line it is given with a small
shell lexer (quotes, $( ), backticks, heredocs, redirections, subshells, wrappers, keywords) and models git's options
and configuration; a shell grammar and git's parsers have more corners than any such model, so it will never be
complete (that is why sub-agents get an allowlist of git overrides). It cannot see inside script files,
`python -c`, `node -e`, Makefiles or anything a command runs later. It FAILS CLOSED on a crash, an unreadable
event or its watchdog (hook_config.run_guard). Declared limits: names or paths computed at run time, a cd that fails, writers it does not
model, symlinks created after the check; a repository the agent made itself and points git at (--git-dir, GIT_DIR, a
cd into it), whose own configuration and hooks git then runs — the same limit as a script file; an alias the lead
stored with `git config` and calls later; a sub-agent command that cannot be parsed is denied when it names a checked
program; git's options that run an inline command line of their own (rebase -x/--exec, bisect run, submodule
foreach, difftool -x/--extcmd, grep -O/--open-files-in-pager, filter-branch filters, --exec-path) are judged only as
far as the git model above goes (a known limit, not a check to add); the file writes of a protected command's own
options (e.g. a copy out of a container) are not modelled. Agents still follow the project's owner rules and
operating procedures.

What it checks:
- deletions (rm, rmdir, unlink, truncate, find -delete/-exec rm, chmod/chown -R) only of provably ours paths;
  '..', the scratch root, protected dirs and symlinks resolving elsewhere are refused; a recursive deleter's start
  (find -delete/-exec rm, rsync --delete) that holds a protected path is judged like rm -rf of that start; a find
  that deletes while following symlinks (-L, -H, -follow) is refused;
- sub-agent writes (Bash redirections, mv, cp, tee, ln, install, rsync, sed -i, dd of=; and the Write/Edit tools)
  only in their own lane worktree, the scratch root, /tmp/<BOA_NAME_PREFIX>*, and the main checkout's
  BOA_SUBAGENT_MAIN_WRITES prefixes (logs/); everyone's Bash writes to <main>/.boa/, <main>/.env* and the agent
  runtime's own configuration in <main> (BOA_RUNTIME_CONFIG) are refused (the lead uses its file tools or the
  override);
- own lane: a sub-agent is bound to the first <BOA_TASK_PREFIX><n> id of its spawn description (the agent binding,
  agent_binding.py, recorded when the lead spawned it); another lane's worktree is refused ("that is lane X, yours
  is Y"), the integrator may touch any lane, an unbound agent stays confined to the lane worktrees and its
  destructive commands there are noted in the log (the binding's known limits are in agent_binding.py);
- other projects on this host: a sub-agent may not name a path under the projects dir (the main checkout's
  parent) other than the project's own (reads included, also relative to its cwd, and with Read/Grep/Glob, which
  may not search the projects dir or anything above it either) nor cd into one; nobody runs git write verbs on
  another project's repository;
- ln/mv/install/rsync/cp --remove-destination onto /dev, chmod/chown/chgrp/setfacl/chattr on /dev, mount/umount
  of /dev, dd to a device (not /dev/null);
- the project's PROTECTED COMMANDS (<main checkout>/.boa/protected-commands.conf, written by the project's agent:
  `<all|lanes> <program>[,<program>...] <pattern> <reason>`, see parse_protected): a command of a listed program
  whose text matches the pattern is refused for everyone (all) or for sub-agents (lanes) with the reason; this is
  how a project protects its own resources (databases, containers, services, deployed instances) — the guard knows
  no database, container engine or service itself; git clean/reset --hard/checkout of paths outside the project or
  (sub-agents) outside their lane, pushes to BOA_MAIN_BRANCH, force pushes and remote deletions outside the lane
  branch grammar (BOA_BRANCH_GRAMMAR); git's own file writers (--output, archive -o, bundle create, config -f,
  checkout-index --prefix); git settings that start a program, read another configuration or run their own command
  line (EXEC_SETTINGS: aliases, pagers, editors, diff/merge/filter/credential/ssh/askpass/proxy/gpg programs,
  fsmonitor, hooksPath, include paths, the ext:: transport, --upload-pack/--receive-pack/--exec, abbreviated long
  options read as git reads them): for sub-agents an ALLOWLIST of harmless overrides (SUBAGENT_CONFIG; anything else
  is refused), for the lead the program judged and its aliases expanded as git expands them; pkill/killall, kill of
  every process or a process group, reboot/shutdown, filesystem and partition tools, writes to devices; a sub-agent
  piping into a shell; a command nested past MAX_NESTING levels (everyone). Service, package-manager, firewall,
  crontab and forge-CLI protections are the project's protected commands (references/safety.md, "Host protections"),
  written by its agent for its OS and forge: the guard names no such tool.

Denies are non-blocking: the agent gets the reason and adapts; nobody waits for a human. Anything not recognised
as destructive is left alone (exit 0, no output). Denials are appended (agent, tool and the reason, capped; the reason can quote arguments of the command, the
command line itself is not stored) to
<main checkout>/<BOA_LOG_DIR>/guard-denials.jsonl (default .boa/logs; ${BOA_ENV_PREFIX}GUARD_NOLOG=1 turns that off, for tests). The lead may
prefix a command it has proven safe with ${BOA_ENV_PREFIX}GUARD_LEAD_VERIFIED=<single-token-reason> (at least 3
characters of [A-Za-z0-9_.-], then a blank): that is logged as an override with its reason; for a sub-agent the
prefix is only an environment assignment and the command is judged normally. The same prefix is the lead's escape
when the guard fails (fail closed, see Limits). Python standard library only.

Paths and names come from hook_config.py (the project's .boa/config.env; `--print-paths` shows the
paths): REPO the main checkout, WT the lane worktrees dir, SCRATCH the agents' scratch root (BOA_SCRATCH_ROOT), the
projects dir = REPO's parent, RUNTIME_CONFIG the runtime's own configuration names in REPO (BOA_RUNTIME_CONFIG).
"""
import importlib.util
import json
import os
import posixpath
import re
import shlex
import subprocess
import sys
import time

sys.dont_write_bytecode = True


def _load_sibling(name):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name + ".py")
    spec = importlib.util.spec_from_file_location("boa_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def refuse_broken(tag, error):
    """A companion module (hook_config.py, shell_lexer.py) could not be loaded: the shared fail-closed path is what
    broke, so this guard refuses on its own (a deny verdict for the wiring, then a non-zero exit)."""
    print(json.dumps({"decision": "deny", "reason": f"{tag} the guard's companion module is broken ({error}): every "
                      "call is refused until .boa/hooks is fixed or reinstalled", "context": "", "message": ""}))
    return 1


try:
    CONFIG, BROKEN = _load_sibling("hook_config"), None
except Exception as _exc:   # noqa: BLE001 - a broken companion: every call is refused in main(), never a traceback
    CONFIG, BROKEN = None, f"{type(_exc).__name__}: {_exc}"[:300]
HOME = os.path.expanduser("~")
# set by configure() from the loaded configuration (run_guard refuses every call when there is none: fail closed)
CFG = REPO = WT = SCRATCH = OTHER_PROJECT = None
RUNTIME_CONFIG = LANE_TMP_PREFIXES = PROTECTED_ANY = PROTECTED_MAIN = MAIN_REFS = PROJECT_DIRS = SUB_MAIN_WRITES = ()
BRANCH_OK = PROTECTED_ERROR = None
PROTECTED = []
NAME_PREFIX = DEMO_PREFIX = SLUG = ENV_PREFIX = TASK_RE = ""
TAG = "[boa-guard]"


def other_projects_pattern(repo, wt):
    """Any path under the projects dir (the main checkout's parent) that is not ours."""
    projects = os.path.dirname(repo)
    ours = {os.path.basename(repo)} | ({os.path.basename(wt)} if os.path.dirname(wt) == projects else set())
    names = "|".join(re.escape(n) for n in sorted(ours))
    alts = ["/+".join(re.escape(c) for c in projects.split("/"))]
    if HOME and HOME != "/" and projects.startswith(HOME + "/"):
        alts.append("~/+" + "/+".join(re.escape(c) for c in projects[len(HOME) + 1:].split("/")))
    root = "(?:" + "|".join(alts) + ")"
    other = root + r"/+(?!(?:" + names + r")(?![A-Za-z0-9._-]))[A-Za-z0-9._-]+"
    up = root + r"/+(?:" + names + r")/+\.\.(?![A-Za-z0-9._-])"  # <ours>/.. climbs into the projects dir
    return re.compile(other + "|" + up, re.I if CONFIG.on_windows() else 0)   # Windows: names in any case


def configure(cfg):
    """Derive every path and name from the project's configuration (hook_config.load)."""
    global CFG, REPO, WT, SCRATCH, RUNTIME_CONFIG, OTHER_PROJECT, LANE_TMP_PREFIXES, PROTECTED_ANY, PROTECTED_MAIN
    global MAIN_REFS, PROJECT_DIRS, SUB_MAIN_WRITES, BRANCH_OK, NAME_PREFIX, DEMO_PREFIX
    global SLUG, ENV_PREFIX, TASK_RE, PROTECTED, PROTECTED_ERROR, HOME
    CFG = cfg
    HOME = CONFIG.slash(CONFIG.expanduser("~"))
    REPO, WT, SCRATCH = (CONFIG.slash(CFG[k]) for k in ("repo", "wt", "scratch"))
    RUNTIME_CONFIG = CFG["runtime_config"]
    OTHER_PROJECT = other_projects_pattern(REPO, WT)
    NAME_PREFIX, SLUG = CFG["name_prefix"], CFG["slug"]
    DEMO_PREFIX = SLUG + "-"
    LANE_TMP_PREFIXES = ("/tmp/" + NAME_PREFIX, "/tmp/" + DEMO_PREFIX)
    PROTECTED_ANY, PROTECTED_MAIN = CFG["protected_any"], CFG["protected_main"]
    SUB_MAIN_WRITES = CFG["sub_main_writes"]
    BRANCH_OK = CFG["branch_re"]
    MAIN_REFS = tuple(sorted({b for m in (CFG["main_branch"], "main", "master") for b in (m, "refs/heads/" + m)}))
    PROJECT_DIRS = [CONFIG.slash(CFG["projects"])]
    ENV_PREFIX = CFG["env_prefix"]
    TASK_RE = CFG["task_re"]
    PROTECTED, PROTECTED_ERROR = parse_protected(os.path.join(REPO, ".boa", "protected-commands.conf"))



GLOB = re.compile(r"[*?\[]")
SHELLS = ("sh", "bash", "dash", "zsh", "ksh")  # su -c, watch and coproc are handled as shells/wrappers too
DELETERS = ("rm", "rmdir", "unlink", "shred", "truncate", "srm")
DEVICE_OK = ("/dev/null", "/dev/stdout", "/dev/stderr", "/dev/stdin", "/dev/tty")
KEYWORDS = {"!", "{", "}", "if", "then", "else", "elif", "fi", "while", "until", "do", "done", "esac"}
# wrappers that run their arguments as a command: options that take a separate value
WRAPPERS = {
    "sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U", "-T", "--user", "--group", "--host", "--prompt",
             "--chdir", "--role", "--type", "--other-user", "--command-timeout", "--close-from"},
    "doas": {"-u", "-C"},
    "env": {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"},
    "nice": {"-n", "--adjustment"},
    "ionice": {"-c", "-n", "-p", "-P", "-u", "--class", "--classdata", "--pid", "--pgid", "--uid"},
    "stdbuf": {"-i", "-o", "-e", "--input", "--output", "--error"},
    "timeout": {"-k", "-s", "--kill-after", "--signal"},
    "time": {"-f", "--format", "-o", "--output"},
    "exec": {"-a"},
    "flock": {"-w", "-E", "--timeout", "--conflict-exit-code"},
    "nohup": set(), "setsid": set(), "builtin": set(), "command": set(),
}
CHECKED_PROGS = re.compile(r"\b(git|mv|cp|tee|sed|rm|rmdir|unlink|find|rsync|chmod|chown|ln|install|dd|truncate|"
                           r"shred|perl|tar|curl|wget|pkill|killall|prune|mkfs|wipefs)\b|-delete\b|>")
LOOKS_DESTRUCTIVE = re.compile(r"\b(rm|rmdir|shred|unlink|truncate|pkill|killall|prune|mkfs|wipefs|clean)\b|-delete\b|>")
XARGS_OPTS = {"-a", "-d", "-E", "-e", "-I", "-L", "-l", "-n", "-P", "-s", "--arg-file", "--delimiter", "--eof",
              "--replace", "--max-lines", "--max-args", "--max-procs", "--max-chars", "--process-slot-var"}
XARGS_DANGER = DELETERS + SHELLS + ("git", "mv", "chmod", "chown", "find", "dd", "tee", "cp")


class Deny(Exception):
    pass


def names_checked(cmd):
    """The text names a program the guard checks (built in, or a protected command of the project)."""
    if CHECKED_PROGS.search(cmd):
        return True
    progs = protected_programs()
    return bool(progs) and any(os.path.basename(w) in progs for w in re.findall(r"[A-Za-z0-9_./+-]+", cmd))


def norm(p):
    """p normalised in the guard's one path form (hook_config.slash: as written on POSIX; on Windows `/` separators and
    MSYS drive paths mapped), so the `/` of the path rules below holds on every OS."""
    return posixpath.normpath(CONFIG.slash(p))


def is_abs(p):
    return CONFIG.is_abs(p)


def pjoin(base, p):
    """base/p in the guard's path form; p itself when it is absolute."""
    return CONFIG.slash(p) if is_abs(p) else posixpath.join(CONFIG.slash(base), CONFIG.slash(p))


def expand(p):
    """~ expanded (from HOME, as the shell does), in the guard's path form."""
    return CONFIG.slash(CONFIG.expanduser(p))


def named(name, names):
    """name is one of names, compared as the file system does (hook_config.fold_name: case-insensitive on Windows and
    macOS, so `.GIT` or `Memory-Bank` is the protected name there)."""
    n = CONFIG.fold_name(name)
    return any(n == CONFIG.fold_name(x) for x in names)


def env_name(name):
    return CONFIG.fold_name(name).startswith(".env")


def realp(p):
    """Where p really leads (symlinks resolved), in the guard's path form."""
    return CONFIG.slash(os.path.realpath(p))


def under(path, root):
    """path strictly inside root (not root itself)."""
    return path.startswith(root.rstrip("/") + "/")


def checkout_of(path):
    """(root, is_main) of the checkout containing path, else (None, None)."""
    if path == REPO or under(path, REPO):
        return REPO, True
    if under(path, WT):
        rest = path[len(WT) + 1:]
        return WT + "/" + rest.split("/", 1)[0], False
    return None, None


# ----------------------------------------------------------------------------- lexer
OPS = ("&&", "||", ";;", "|&", ";", "|", "&", "(", ")")
REDIR = re.compile(r"(\d*)(<<<|<<-|<<|&>>|&>|>>|>\||>&|<&|<>|>|<)")
META = set(" \t\n;&|()<>")


HEREDOC_START = re.compile(r"<<(-?)[ \t]*(['\"]?)([^\s'\";&|()<>]+)\2")


def skip_heredoc_bodies(s, i, pending):
    """From just after a newline at s[i], skip the bodies of the pending heredocs; index after the last tag line."""
    n = len(s)
    for tag, strip in pending:
        while i < n:
            j = s.find("\n", i)
            line = s[i:] if j < 0 else s[i:j]
            i = n if j < 0 else j + 1
            if (line.lstrip("\t") if strip else line) == tag:
                break
    return i


def find_close(s, i):
    """Index just past the ')' that closes a '$(' or '(' opened before s[i] (quotes, nesting and heredoc bodies
    respected: `$(cat <<'EOF' … don't … EOF)` is one substitution)."""
    depth, n, pending = 1, len(s), []
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "<" and s.startswith("<<", i) and not s.startswith("<<<", i):
            m = HEREDOC_START.match(s, i)
            if m:
                pending.append((m.group(3), m.group(1) == "-"))
                i = m.end()
                continue
        if c == "\n" and pending:
            i = skip_heredoc_bodies(s, i + 1, pending)
            pending = []
            continue
        if c == "'":
            j = s.find("'", i + 1)
            i = n if j < 0 else j + 1
            continue
        if c == '"':
            i = skip_dquote(s, i + 1)
            continue
        if c == "`":
            j = s.find("`", i + 1)
            i = n if j < 0 else j + 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced $(")


def skip_dquote(s, i):
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == '"':
            return i + 1
        if c == "$" and s[i + 1:i + 2] == "(":
            i = find_close(s, i + 2)
            continue
        if c == "`":
            j = s.find("`", i + 1)
            i = n if j < 0 else j + 1
            continue
        i += 1
    raise ValueError("unbalanced double quote")


def read_word(s, i):
    """A shell word from s[i]: (text with quotes removed and $()/`` kept, inner command strings, end, quoted)."""
    out, subs, n, quoted = [], [], len(s), False
    while i < n and s[i] not in META:
        c = s[i]
        if c == "\\":
            if i + 1 < n and s[i + 1] == "\n":
                i += 2
                continue
            out.append(s[i + 1:i + 2])
            i += 2
            quoted = True
        elif c == "'":
            j = s.find("'", i + 1)
            if j < 0:
                raise ValueError("unbalanced single quote")
            out.append(s[i + 1:j])
            i, quoted = j + 1, True
        elif c == "$" and s[i + 1:i + 2] == "'":
            j = i + 2
            while j < n and s[j] != "'":
                j += 2 if s[j] == "\\" else 1
            if j >= n:
                raise ValueError("unbalanced $'")
            out.append(ansi_c(s[i + 2:j]))
            i, quoted = j + 1, True
        elif c == '"':
            quoted = True
            i += 1
            while True:
                if i >= n:
                    raise ValueError("unbalanced double quote")
                c = s[i]
                if c == '"':
                    i += 1
                    break
                if c == "\\" and s[i + 1:i + 2] in ('"', "\\", "$", "`", "\n"):
                    out.append(s[i + 1] if s[i + 1] != "\n" else "")
                    i += 2
                elif c == "$" and s[i + 1:i + 2] == "(":
                    j = find_close(s, i + 2)
                    subs.append(s[i + 2:j - 1])
                    out.append(s[i:j])
                    i = j
                elif c == "`":
                    j = s.find("`", i + 1)
                    if j < 0:
                        raise ValueError("unbalanced backtick")
                    subs.append(s[i + 1:j])
                    out.append(s[i:j + 1])
                    i = j + 1
                else:
                    out.append(c)
                    i += 1
        elif c == "$" and s[i + 1:i + 2] == "(":
            j = find_close(s, i + 2)
            subs.append(s[i + 2:j - 1])
            out.append(s[i:j])
            i = j
        elif c == "$" and s[i + 1:i + 2] == "{":
            j, inner = read_param(s, i + 2)
            subs += inner
            out.append(s[i:j])
            i = j
        elif c == "`":
            j = s.find("`", i + 1)
            if j < 0:
                raise ValueError("unbalanced backtick")
            subs.append(s[i + 1:j])
            out.append(s[i:j + 1])
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out), subs, i, quoted


def read_param(s, i):
    """A ${…} expansion from just after '${': (index after its '}', command substitutions inside, nested too)."""
    subs, n, depth = [], len(s), 1
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
        elif c == "'":
            j = s.find("'", i + 1)
            i = n if j < 0 else j + 1
        elif c == '"':
            j = skip_dquote(s, i + 1)
            subs += dquote_subs(s[i + 1:j - 1])
            i = j
        elif c == "$" and s[i + 1:i + 2] == "(":
            j = find_close(s, i + 2)
            subs.append(s[i + 2:j - 1])
            i = j
        elif c == "$" and s[i + 1:i + 2] == "{":
            depth, i = depth + 1, i + 2
        elif c == "`":
            j = s.find("`", i + 1)
            if j < 0:
                raise ValueError("unbalanced backtick")
            subs.append(s[i + 1:j])
            i = j + 1
        elif c == "}":
            depth, i = depth - 1, i + 1
            if depth == 0:
                return i, subs
        else:
            i += 1
    raise ValueError("unbalanced ${")


ANSI_ESC = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b", "f": "\f", "v": "\v",
            "\\": "\\", "'": "'", '"': '"', "?": "?"}


def ansi_c(body):
    """Decode a $'…' body the way bash does (\\xHH, \\NNN octal, \\uHHHH, \\UHHHHHHHH, \\n …), so `$'\\x72m'` reads as rm."""
    def one(m):
        e = m.group(1)
        if e[0] in "xuU":
            return chr(int(e[1:], 16))
        if e[0] in "01234567":
            return chr(int(e, 8) & 0xFF)
        if e[0] == "c":
            return chr(ord(e[1]) & 0x1F)
        return ANSI_ESC.get(e, "\\" + e)
    return re.sub(r"\\(x[0-9A-Fa-f]{1,2}|u[0-9A-Fa-f]{1,4}|U[0-9A-Fa-f]{1,8}|[0-7]{1,3}|c.|.)", one, body)


def dquote_subs(text):
    """Command substitutions in an unquoted heredoc body (it is expanded like a double-quoted string)."""
    subs, i, n = [], 0, len(text)
    while i < n:
        if text[i] == "\\":
            i += 2
        elif text[i] == "$" and text[i + 1:i + 2] == "(":
            j = find_close(text, i + 2)
            subs.append(text[i + 2:j - 1])
            i = j
        elif text[i] == "`":
            j = text.find("`", i + 1)
            if j < 0:
                break
            subs.append(text[i + 1:j])
            i = j + 1
        else:
            i += 1
    return subs


def lex(s):
    """Items: ("op", x) | ("word", text, subs) | ("redir", op, text, subs) | ("heredoc", body, quoted)."""
    items, i, n, pending = [], 0, len(s), []  # pending: [(index of the placeholder item, tag, strip tabs)]
    while i < n:
        c = s[i]
        if c == "\\" and s[i + 1:i + 2] == "\n":
            i += 2
            continue
        if c == "\n":
            items.append(("op", ";"))
            i += 1
            for at, tag, strip in pending:
                body = []
                while i < n:
                    j = s.find("\n", i)
                    line = s[i:] if j < 0 else s[i:j]
                    i = n if j < 0 else j + 1
                    if (line.lstrip("\t") if strip else line) == tag:
                        break
                    body.append(line)
                items[at] = ("heredoc", "\n".join(body), items[at][2])
            pending = []
            continue
        if c in " \t":
            i += 1
            continue
        if c == "#" and (i == 0 or s[i - 1] in " \t\n;&|()"):
            j = s.find("\n", i)
            i = n if j < 0 else j
            continue
        if c in "<>" and s[i + 1:i + 2] == "(":  # process substitution: a word whose command is checked
            j = find_close(s, i + 2)
            items.append(("word", s[i:j], [s[i + 2:j - 1]]))
            i = j
            continue
        m = REDIR.match(s, i)
        if m:
            op = m.group(2)
            i = m.end()
            while i < n and s[i] in " \t":
                i += 1
            text, subs, i, quoted = read_word(s, i)
            if op in ("<<", "<<-"):
                pending.append((len(items), text, op == "<<-"))
                items.append(("heredoc", "", quoted))  # the body is filled in at the next newline
                continue
            items.append(("redir", op, text, subs))
            continue
        for op in OPS:
            if s.startswith(op, i):
                items.append(("op", op))
                i += len(op)
                break
        else:
            text, subs, i, _ = read_word(s, i)
            items.append(("word", text, subs))
    return items


def commands(items):
    """Group lexer items into simple commands: [("cmd", words, redirs, heredocs) | ("op", x)]."""
    out, words, redirs, docs = [], [], [], []

    def flush():
        if words or redirs or docs:
            out.append(("cmd", list(words), list(redirs), list(docs)))
        words.clear(), redirs.clear(), docs.clear()

    for it in items:
        if it[0] == "op":
            flush()
            out.append(it)
        elif it[0] == "word":
            words.append((it[1], it[2]))
        elif it[0] == "redir":
            redirs.append((it[1], it[2], it[3]))
        else:
            docs.append((it[1], it[2]))
    flush()
    return out


# ----------------------------------------------------------------------------- path rules
def expand_braces(word, limit=256):
    """Bash brace expansion of a path word ({a,b}, nested; ${…} left alone): every result, so each one is checked.
    A sequence ({x..y}), an unbalanced brace or more than `limit` results can't be checked: Deny."""
    results = []

    def match(w, j):
        depth, k = 0, j
        while k < len(w):
            if w[k] == "{":
                depth += 1
            elif w[k] == "}":
                depth -= 1
                if depth == 0:
                    return k
            k += 1
        return None

    def rec(w):
        i = 0
        while True:
            j = w.find("{", i)
            if j < 0:
                results.append(w)
                break
            k = match(w, j)
            if k is None:
                raise Deny(f"'{word}': an unbalanced brace can't be checked; write the paths out")
            if j > 0 and w[j - 1] == "$":  # ${…}: a parameter, not a brace list
                i = k + 1
                continue
            inner, parts, depth, start = w[j + 1:k], [], 0, 0
            for m, ch in enumerate(inner):
                depth += ch == "{"
                depth -= ch == "}"
                if ch == "," and depth == 0:
                    parts.append(inner[start:m])
                    start = m + 1
            parts.append(inner[start:])
            if len(parts) == 1:
                if re.fullmatch(r"[^{},]*\.\.[^{},]*", inner):
                    raise Deny(f"'{word}': a {{x..y}} sequence can't be checked; write the paths out")
                i = k + 1  # {} or {x}: literal braces
                continue
            for part in parts:
                rec(w[:j] + part + w[k + 1:])
                if len(results) > limit:
                    raise Deny(f"'{word}': brace expansion gives too many paths to check")
            break

    rec(word)
    return results


def resolve_var(raw, ctx):
    """Resolve a leading $NAME / ${NAME}: (path, 'mktemp'|None), or raise Deny when it can't be verified."""
    m = re.match(r'^\$\{?(\w+)\}?(/.*)?$', raw)
    rest = (m.group(2) or "") if m else ""
    if m and "$" not in rest and "`" not in rest:
        if m.group(1) in ctx["mktemp_vars"]:
            return None, "mktemp"
        if m.group(1) in ctx["vars"]:
            return ctx["vars"][m.group(1)] + rest, None
    return None, None


def variants(p, g, follow_last=False):
    """The path as written plus, when a symlink may sit in it, where it really leads (follow_last: a write
    through a symlink in the last component lands where the link points)."""
    out = [p]
    try:
        if follow_last and os.path.islink(p.rstrip("/")):
            out.append(realp(p))
        parent = os.path.dirname(p.rstrip("/")) or "/"
        if os.path.isdir(parent):
            real = pjoin(realp(parent), os.path.basename(p.rstrip("/")))
            if real != p.rstrip("/"):
                out.append(real)
        if (g or p.endswith("/")) and os.path.exists(p.rstrip("/") or "/"):
            real = realp(p)
            if real not in out:
                out.append(real)
    except OSError:
        pass
    return out


# ----------------------------------------------------------------------------- own lane (the agent binding)
def own_task(ctx):
    """The subagent's own task id from the agent binding (agent_binding.task_of: recorded when the lead spawned it,
    the first task id of its spawn description), or None."""
    if "own_task" not in ctx:
        ctx["own_task"] = None
        if ctx["subagent"]:
            try:   # loaded on use: without the binding module every sub-agent is unbound, never a crash
                ctx["own_task"] = _load_sibling("agent_binding").task_of(CFG, ctx.get("agent_id") or "")
            except Exception:
                pass
    return ctx["own_task"]


def check_lane(root, ctx, what):
    """A bound subagent touches only its own lane; an unbound one any lane worktree (noted in the log); integrators
    clean any lane."""
    if not ctx["subagent"] or ctx.get("agent_type") == "integrator":
        return
    lane = root[len(WT) + 1:]
    task = own_task(ctx)
    if task is None:
        if what in DELETERS + ("find-delete", "git clean", "git reset", "git checkout", "git restore", "git stash", "git switch"):
            ctx["notes"].append(f"{what} in lane {lane}: own lane unknown (no agent binding), allowed")
    elif not (lane == task or lane.startswith(task + "-")):
        raise Deny(f"{what} in {root}: that is lane {lane}, yours is {task}; touch only your own worktree")


def check_delete_path(raw, cwd, ctx, what="delete", expanded=False, start=False):
    """Raise Deny unless raw (a path argument) is provably ours. start: raw is where a recursive deleter (find
    -delete, rsync --delete) starts; it is judged like `rm -rf <start>` only when it holds a protected path."""
    if raw.startswith("-"):
        return
    if not expanded and "{" in raw:
        for v in expand_braces(raw):
            check_delete_path(v, cwd, ctx, what, True, start)
        return
    if "$" in raw or "`" in raw:
        path, kind = resolve_var(raw, ctx)
        if kind == "mktemp":
            return
        if path is None:
            raise Deny(f"{what} of '{raw}': variable paths can't be verified; use a literal absolute path "
                       f"under {SCRATCH}/ or {WT}/<task>/ (or a var assigned from mktemp or a literal path in the same command)")
        return check_delete_path(path, cwd, ctx, what, start=start)
    p = expand(raw)
    if not is_abs(p):
        if cwd is None:
            raise Deny(f"{what} of relative '{raw}' after an unresolvable cd; use an absolute path")
        p = pjoin(cwd, p)
    if ".." in p.split("/"):
        raise Deny(f"{what} of '{raw}': '..' in a delete path is not allowed")
    g = GLOB.search(p)
    for v in variants(p, g):
        delete_rules(v, raw, ctx, what, start)


def holds_protected(base):
    """base is a checkout root (it holds .git and the protected dirs) or an ancestor of the main checkout, the
    worktrees dir or the scratch root."""
    return base == checkout_of(base)[0] or any(r and (base == r or under(r, base)) for r in (REPO, WT, SCRATCH))


def delete_rules(p, raw, ctx, what, start=False):
    g = GLOB.search(p)
    if g:
        base = p[:g.start()]
        base = norm(base[:base.rfind("/") + 1] or "/")
    else:
        base = norm(p)
    if start and (g or not holds_protected(base)):
        return  # a start that holds nothing protected: its contents are judged on their own (<start>/x)
    hint = "; it deletes inside its start whatever its tests: start at the directories you mean" if start else ""
    if base == SCRATCH:
        raise Deny(f"{what} of the whole project scratch root ({SCRATCH}) is not allowed; name a subpath")
    if under(base, SCRATCH):
        # <SCRATCH>/<session>/scratchpad is shared by every lane of a session: never the session dir, its
        # scratchpad or tasks dir, nor a glob directly inside the scratchpad; only a named <TASK>-<role> subfolder
        rel = base[len(SCRATCH) + 1:].split("/")
        if len(rel) < 2 or (len(rel) == 2 and rel[1] in ("scratchpad", "tasks")):
            raise Deny(f"{what} of '{raw}': the shared session scratchpad belongs to every lane; delete only your "
                       "own <TASK>-<role> subfolder")
        return
    if any(base.startswith(pref) for pref in LANE_TMP_PREFIXES) and base.count("/") >= 2 and not (g and base == "/tmp"):
        return
    root, is_main = checkout_of(base)
    if root is None:
        raise Deny(f"{what} of '{raw}' ({base}) is outside the project's paths "
                   f"({SCRATCH}/, {WT}/<task>/, /tmp/{NAME_PREFIX}*); other projects share this host")
    if base == root:
        if is_main:
            raise Deny(f"{what} of the main checkout {REPO} itself is never allowed{hint}")
        if g:
            raise Deny(f"{what} with a glob at the worktree root {root}: name the paths explicitly")
        if ctx["subagent"]:
            if start:
                raise Deny(f"{what} from the worktree root {root} reaches .git and the protected dirs{hint}")
            raise Deny(f"remove worktree {root} with 'git worktree remove {root}' (integrator), not rm")
        return
    rel = base[len(root) + 1:]
    top = rel.split("/", 1)[0]
    if named(top, PROTECTED_ANY):
        raise Deny(f"{what} of '{raw}': {top}/ is protected (git metadata / an immutable reference tree)")
    if is_main:
        if ctx["subagent"]:
            raise Deny(f"subagents must not {what} inside the main checkout {REPO}; work in {WT}/<task>/")
        if named(top, PROTECTED_MAIN) or env_name(top):
            raise Deny(f"{what} of '{raw}': {top} in the main checkout is protected (deployed instance/memory/state)")
    else:
        check_lane(root, ctx, what)


def check_write_path(raw, cwd, ctx, what="write", expanded=False):
    """Bash writes: everyone keeps off <REPO>/.boa, <REPO>/.env* and the runtime's configuration names (RUNTIME_CONFIG)
    in <REPO>; subagents write only in their lane,
    the scratch root, /tmp/<name prefix>*, and the main checkout's SUB_MAIN_WRITES prefixes. Also used for the
    Write/Edit tools."""
    if raw in DEVICE_OK or raw.startswith(("/dev/fd/", "/dev/tcp/", "/dev/udp/")) or raw == "-" or raw.startswith(("<(", ">(")):
        return
    if not expanded and "{" in raw:
        for v in expand_braces(raw):
            check_write_path(v, cwd, ctx, what, True)
        return
    if "$" in raw or "`" in raw:
        path, kind = resolve_var(raw, ctx)
        if kind == "mktemp":
            return
        if path is None:
            if ctx["subagent"]:
                raise Deny(f"{what} to '{raw}': variable paths can't be verified; write under your worktree or "
                           f"{SCRATCH}/ with a literal path (or a var assigned from mktemp or a literal path)")
            return
        return check_write_path(path, cwd, ctx, what)
    p = expand(raw)
    if not is_abs(p):
        if cwd is None:
            if ctx["subagent"]:
                raise Deny(f"{what} to relative '{raw}' after an unresolvable cd; use an absolute path")
            return
        p = pjoin(cwd, p)
    for v in variants(norm(p), GLOB.search(p), follow_last=True):
        write_rules(norm(v), raw, ctx, what)


def write_rules(p, raw, ctx, what):
    kept = (".boa",) + tuple(RUNTIME_CONFIG)
    if (under(p, REPO) and named(CONFIG.parts(p[len(REPO) + 1:])[0], kept)) or \
            (os.path.dirname(p) == REPO and env_name(os.path.basename(p))):
        names = ", ".join(f"{REPO}/{d}" for d in kept)
        raise Deny(f"{what} to '{raw}': {names} (the hooks, their config and the agent runtime's own configuration) "
                   f"and {REPO}/.env* are not written from Bash "
                   f"(the lead uses the Edit tool or {ENV_PREFIX}GUARD_LEAD_VERIFIED=<reason>)")
    if not ctx["subagent"]:
        return
    if under(p, SCRATCH) or any(p.startswith(x) for x in LANE_TMP_PREFIXES):
        return
    for w in SUB_MAIN_WRITES:  # "logs/" = anything under <REPO>/logs; "storage/x-" = a name with that prefix
        if p.startswith(REPO + "/" + w) and len(p) > len(REPO) + 1 + len(w):
            return
    root, is_main = checkout_of(p)
    if root is None:
        raise Deny(f"subagents may write only under {WT}/<task>/ or {SCRATCH}/ (not {p})")
    if is_main:
        raise Deny(f"subagents must not write in the main checkout {REPO} ({p}); work in {WT}/<task>/")
    if p == root:
        raise Deny(f"{what} to the worktree root {root} itself is not allowed")
    top = p[len(root) + 1:].split("/", 1)[0]
    if named(top, PROTECTED_ANY):
        raise Deny(f"{top}/ is protected (git metadata / an immutable reference tree)")
    check_lane(root, ctx, what)


# ----------------------------------------------------------------------------- protected commands
def parse_protected(path):
    """The project's protected commands (<REPO>/.boa/protected-commands.conf, written by the project's agent):
    ([(line, who, programs, regex, reason)], error). One rule per line, `#` comments and blank lines ignored:
        <who> <program>[,<program>...] <pattern> <reason ...>
    who: `all` (everyone, the lead included) or `lanes` (sub-agents only); programs: basenames; pattern: a Python
    regular expression without blanks (\\s for whitespace) searched in the command's text (the program's basename
    and its arguments joined by single blanks, quotes removed, after wrappers such as sudo or env); reason: shown in
    the refusal. A missing file means no rules; a file that cannot be read, is over 64 KiB, or holds an invalid line
    is an error: every shell command is refused until it is fixed (fail closed)."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read(64 * 1024 + 1)
    except FileNotFoundError:
        return [], None
    except OSError as exc:
        return [], f"{path} cannot be read ({exc.__class__.__name__})"
    if len(raw) > 64 * 1024:
        return [], f"{path} is over 64 KiB"
    rules = []
    for n, line in enumerate(raw.decode("utf-8", "replace").splitlines(), 1):
        w = line.strip().split(None, 3)
        if not w or w[0].startswith("#"):
            continue
        if len(w) < 4 or w[0] not in ("all", "lanes"):
            return [], f"{path} line {n}: expected `<all|lanes> <program>[,...] <pattern> <reason>`"
        progs = tuple(x for x in w[1].split(",") if x)
        if not progs or not all(re.fullmatch(r"[A-Za-z0-9_.+-]+", x) for x in progs):
            return [], f"{path} line {n}: the programs must be basenames separated by commas"
        never = sorted(set(progs) & (KEYWORDS | {"coproc"}))
        if never:
            return [], (f"{path} line {n}: {', '.join(never)} is a shell keyword, never a program the guard sees, so "
                        "the rule could never fire; protect the command it runs instead")
        try:
            regex = re.compile(w[2])
        except re.error as exc:
            return [], f"{path} line {n}: invalid pattern ({exc})"
        rules.append((n, w[0], frozenset(progs), regex, w[3].strip()))
    return rules, None


PROTECTED_TEXT_MAX = 8192   # the text a rule searches (a cutoff refuses, never truncates)


def protected_programs():
    return frozenset(x for rule in PROTECTED for x in rule[2])


def check_protected(prog, args, ctx):
    """Refuse a protected command of the project's configuration (parse_protected)."""
    if PROTECTED_ERROR:
        raise Deny(f"the protected-commands file is invalid ({PROTECTED_ERROR}): every shell command is refused "
                   "until it is fixed (the lead edits it with its file tool)")
    text = " ".join([prog] + list(args))
    if len(text) > PROTECTED_TEXT_MAX and any(prog in rule[2] for rule in PROTECTED):
        raise Deny(f"{prog}: a command of a protected program over {PROTECTED_TEXT_MAX} characters can't be matched "
                   "against the project's rules; shorten it (put long data in a file)")
    for n, who, progs, regex, why in PROTECTED:
        if prog in progs and (who == "all" or ctx["subagent"]) and regex.search(text):
            raise Deny(f"{prog}: a protected command of this project ({why}) [protected-commands.conf line {n}]")


# ----------------------------------------------------------------------------- git
def rel(x, base):
    """x as a normalised absolute path (relative to base), or None when it holds a substitution or base is unknown."""
    if "$" in x or "`" in x:
        return None
    x = expand(x)
    if is_abs(x):
        return norm(x)
    return None if base is None else norm(pjoin(base, x))


def check_git(args, cwd, ctx, assigns=()):
    a = list(args)
    gcwd = cwd

    # GIT_DIR / GIT_WORK_TREE from an earlier export or assignment, a prefix assignment or `env NAME=value`
    genv = dict(ctx["git_env"])
    for name, value in assigns:
        if git_tracked(name):
            genv[name] = value
    aliases = {}   # alias name (lower case) -> value (None: from --config-env, not known); only the lead keeps them

    def note_alias(key, value):
        if key.strip().lower().startswith("alias."):
            aliases[key.strip().lower()[len("alias."):]] = value

    for name, row in EXEC_ENV.items():   # GIT_PAGER, GIT_EDITOR, GIT_ASKPASS, GIT_CONFIG_GLOBAL … set in this command
        if genv.get(name) is not None:
            git_exec_value(row, "environment " + name, None if genv[name] == "$?" else genv[name], gcwd, ctx)
    for name, value in genv.items():
        if re.fullmatch(r"GIT_CONFIG_KEY_\d+", name) and value not in (None, "$?"):
            v = genv.get("GIT_CONFIG_VALUE_" + name.rsplit("_", 1)[1])
            git_exec_config(value, None if v in (None, "$?") else v, gcwd, ctx, "environment " + name + " =")
            note_alias(value, None if v in (None, "$?") else v)
        elif name == "GIT_CONFIG_PARAMETERS" and value is not None:
            try:
                pairs = config_parameters(value)
            except ValueError:
                raise Deny("GIT_CONFIG_PARAMETERS can't be read the way git reads it; set the configuration with -c")
            for k, v in pairs:
                git_exec_config(k, v if v else None, gcwd, ctx, "environment GIT_CONFIG_PARAMETERS")
                note_alias(k, v if v else None)
    git_dir = (rel(genv["GIT_DIR"], gcwd) or "?") if genv.get("GIT_DIR") is not None else None
    work_tree = (rel(genv["GIT_WORK_TREE"], gcwd) or "?") if genv.get("GIT_WORK_TREE") is not None else None

    while a and a[0].startswith("-"):
        t = a[0]
        if t == "-C" and len(a) > 1:
            gcwd, a = rel(a[1], gcwd), a[2:]
        elif t in ("--work-tree", "--git-dir") and len(a) > 1:
            if t == "--work-tree":
                work_tree = rel(a[1], gcwd) or "?"
            else:
                git_dir = rel(a[1], gcwd) or "?"
            a = a[2:]
        elif t.startswith("--work-tree="):
            work_tree, a = rel(t.split("=", 1)[1], gcwd) or "?", a[1:]
        elif t.startswith("--git-dir="):
            git_dir, a = rel(t.split("=", 1)[1], gcwd) or "?", a[1:]
        elif t == "-c" and len(a) > 1:
            key, _, value = a[1].partition("=")
            if key.lower() == "core.worktree":
                work_tree = rel(value, gcwd) or "?"
            git_exec_config(key, value, gcwd, ctx, "-c")
            note_alias(key, value)
            a = a[2:]
        elif t.startswith("--config-env=") or (t == "--config-env" and len(a) > 1):
            spec = t.split("=", 1)[1] if "=" in t else a[1]
            if spec.lower().startswith("core.worktree="):
                work_tree = "?"
            git_exec_config(spec.split("=", 1)[0], None, gcwd, ctx, "--config-env")
            note_alias(spec.split("=", 1)[0], None)
            a = a[1:] if "=" in t else a[2:]
        elif t in ("--namespace", "--exec-path", "--super-prefix") and len(a) > 1:
            a = a[2:]
        else:
            a = a[1:]
    if not a:
        return
    git_sub(a[0], [canonical_option(t) for t in a[1:]], dict(aliases), 0, args, gcwd, work_tree, git_dir, ctx)


def git_sub(sub, rest, aliases, depth, args, gcwd, work_tree, git_dir, ctx):
    """One git subcommand with its arguments, after git's own options. An alias of it is expanded as git does
    (case-insensitive, from every source, at most 5 levels deep) and judged; an alias with a builtin's name is judged
    AND the plain builtin too (whether git runs the alias depends on its version and on what is installed: gui,
    citool, send-email), and the command is refused when either form is."""
    name = sub.lower()
    if name in aliases:
        if depth >= 5:
            raise Deny(f"git alias chain deeper than 5 at '{sub}': spell the git command out")
        value = aliases[name]
        others = {k: v for k, v in aliases.items() if k != name}
        if value is None:
            raise Deny(f"git alias '{sub}' comes from the environment (--config-env): its command can't be judged")
        if value.lstrip().startswith("!"):   # a program, with the arguments git appends
            git_exec_value(EXEC_ROWS[0], f"alias {sub}", value.lstrip(), gcwd, ctx, " " + " ".join(rest))
        else:
            try:
                expanded = shlex.split(value)
            except ValueError:
                raise Deny(f"git alias '{sub}' can't be read; spell the git command out")
            if expanded:
                git_sub(expanded[0], [canonical_option(t) for t in expanded[1:]] + rest, others, depth + 1, args, gcwd,
                        work_tree, git_dir, ctx)
        if name not in GIT_BUILTINS:
            return
    for k, t in enumerate(rest):   # transport options that name the program run on the other side; ext:: URLs
        val = None
        if t in TRANSPORT_OPTS or (t == "-u" and sub in ("clone", "ls-remote")):
            val = rest[k + 1] if k + 1 < len(rest) else ""
        elif t.startswith(tuple(o + "=" for o in TRANSPORT_OPTS)):
            val = t.split("=", 1)[1]
        elif t.startswith("ext::"):
            git_exec_value((None, (), (), "cmd"), f"{sub} {t[:30]}", t[5:].replace("%S", "").replace("%s", ""),
                           gcwd, ctx)
        if val is not None:
            git_exec_value((None, (), (), "cmd"), f"{sub} {t}", val, gcwd, ctx)
    if sub in ("clean", "reset", "checkout", "restore", "stash", "push", "rebase", "branch", "worktree", "switch",
               "rm", "mv", "commit", "merge", "pull", "am", "apply", "cherry-pick", "revert", "add", "gc", "tag",
               "config", "fetch", "init", "update-ref"):
        places = [p for p in (gcwd, work_tree, git_dir) if p not in (None, "?")]
        if OTHER_PROJECT.search(" ".join(args)) or any(OTHER_PROJECT.search(p + "/") for p in places):
            raise Deny(f"'git {sub}' on another project's repository; this project's agents never change other projects")
    if sub in ("diff", "log", "show", "format-patch", "whatchanged"):
        for target in git_output_targets(sub, rest):  # git writes its output to a file of the caller's choice
            check_write_path(target, gcwd, ctx, f"git {sub} --output")
    for target in git_file_targets(sub, rest):        # archive -o, bundle create, config -f, checkout-index --prefix
        check_write_path(target, gcwd, ctx, f"git {sub}")
    if sub == "config":
        key, value = git_config_write(rest)
        if ctx["subagent"] and not git_config_read(rest):
            raise Deny("git config writes are the lead's: the local configuration is the main checkout's .git/config, "
                       "shared by every lane, and the global/system ones are the host's; sub-agents only read it "
                       "(--get, --list, get) or override a harmless setting for one command (-c)")
        if key is not None:
            git_exec_config(key, value, gcwd, ctx, "config")
    if sub == "push":
        force = any(t in ("-f", "--force", "--mirror") or t.startswith("--force-with-lease")
                    or t.startswith("--force-if-includes") for t in rest)
        delete = any(t in ("-d", "--delete") for t in rest)
        positional, k, repo_opt = [], 0, False
        while k < len(rest):
            t = rest[k]
            if t == "--repo":
                repo_opt, k = True, k + 2
                continue
            if t.startswith("--repo="):
                repo_opt = True
            elif not t.startswith("-"):
                positional.append(t)
            k += 1
        refs = positional if repo_opt else positional[1:]  # the remote is --repo or the first positional
        plus = [r for r in refs if r.startswith("+")]
        colon_del = [r for r in refs if r.startswith(":")]
        if "--mirror" in rest or "--all" in rest and force:
            raise Deny("git push --mirror/--all --force is not allowed")
        if ctx["subagent"] and any(r.lstrip("+").split(":")[-1] in MAIN_REFS for r in refs):
            raise Deny("subagents never push to main (the integrator merges through PRs)")
        if force or plus:
            if not refs:
                raise Deny("force push without an explicit lane-branch refspec is not allowed")
            for r in refs:
                dst = r.lstrip("+").split(":")[-1]
                if not BRANCH_OK.match(dst):
                    raise Deny(f"force push to '{dst}' is not allowed (only lane branches {CFG['branch_glob']})")
        if delete or colon_del:
            for r in (refs if delete else colon_del):
                dst = r.lstrip(":")
                if not BRANCH_OK.match(dst):
                    raise Deny(f"deleting remote branch '{dst}' is not allowed (only lane branches {CFG['branch_glob']})")
        return
    if sub == "branch" and any(t in ("-D", "-d", "--delete") or (t.startswith("-") and "D" in t) for t in rest):
        for t in rest:
            if not t.startswith("-") and t in MAIN_REFS:
                raise Deny(f"deleting the main branch ({t}) is not allowed")
        return
    if sub == "worktree" and rest and rest[0] == "remove":
        for t in rest[1:]:
            if t.startswith("-"):
                continue
            p = rel(t, gcwd)
            if p is None or not under(p, WT) or "/" in p[len(WT) + 1:]:
                raise Deny(f"git worktree remove '{t}': only {WT}/<task> worktrees")
        return
    discard = (sub == "clean" or (sub == "reset" and "--hard" in rest)
               or (sub == "stash" and rest[:1] in (["drop"], ["clear"]))
               or (sub == "restore")
               or (sub == "switch" and any(t in ("-f", "--force", "--discard-changes") for t in rest))
               or (sub == "checkout" and any(t in (".", "--", "-f", "--force", "-p", "--patch") for t in rest)))
    if not discard:
        return
    tree = work_tree or gcwd
    if tree in (None, "?") or git_dir == "?":
        raise Deny(f"'git {sub}' in a work tree that can't be resolved; use git -C <absolute path>")

    def inside_project(p):
        return p == REPO or under(p, REPO) or under(p, WT) or under(p, SCRATCH)

    for p in [tree] + ([git_dir] if git_dir else []):
        if not inside_project(p):
            raise Deny(f"'git {sub}' on {p}: outside the project's repositories (other projects share this host)")
    in_main = tree == REPO or under(tree, REPO)
    if ctx["subagent"]:
        if in_main or (git_dir and (git_dir == REPO or under(git_dir, REPO)) and not under(git_dir, REPO + "/.git/worktrees")):
            raise Deny(f"'git {sub}' in the main checkout would discard the lead's state; work in {WT}/<task>/")
        if under(tree, WT):
            check_lane(WT + "/" + tree[len(WT) + 1:].split("/", 1)[0], ctx, f"git {sub}")
    if sub == "clean" and in_main:
        raise Deny("git clean in the main checkout would delete .env, logs, the lead's state and ignored data")


def git_output_targets(sub, rest):
    """Files git diff/log/show/format-patch write: --output[=]FILE, -o FILE / -oFILE, and format-patch's
    --output-directory / -o DIR (as DIR/x)."""
    out, k = [], 0
    while k < len(rest):
        t = rest[k]
        if t == "--":
            break
        val, is_dir = None, sub == "format-patch" and (t in ("-o", "--output-directory")
                                                        or t.startswith(("--output-directory=", "-o")))
        if t in ("--output", "-o", "--output-directory") and k + 1 < len(rest):
            val, k = rest[k + 1], k + 1
        elif t.startswith(("--output=", "--output-directory=")):
            val = t.split("=", 1)[1]
        elif t.startswith("-o") and len(t) > 2 and not t.startswith("--"):
            val = t[2:]
        if val is not None:
            out.append(val.rstrip("/") + "/x" if is_dir else val)
        k += 1
    return out


def git_file_targets(sub, rest):
    """Files other git commands write: archive -o/--output, bundle create <file>, config -f/--file <file>,
    checkout-index --prefix=<p> (as <p>x: the prefix is glued to every path it writes)."""
    out, k = [], 0
    if sub == "bundle":
        if rest[:1] == ["create"]:
            out += [w for w in rest[1:] if not w.startswith("-")][:1]
        return out
    while k < len(rest):
        t = rest[k]
        if t == "--":
            break
        if sub == "archive" and t in ("-o", "--output") and k + 1 < len(rest):
            out.append(rest[k + 1])
            k += 1
        elif sub == "archive" and (t.startswith("--output=") or (t.startswith("-o") and len(t) > 2 and not t.startswith("--"))):
            out.append(t.split("=", 1)[1] if t.startswith("--output=") else t[2:])
        elif sub == "config" and t in ("-f", "--file") and k + 1 < len(rest):
            out.append(rest[k + 1])
            k += 1
        elif sub == "config" and t.startswith("--file="):
            out.append(t.split("=", 1)[1])
        elif sub == "checkout-index" and t.startswith("--prefix="):
            out.append(t.split("=", 1)[1] + "x")
        k += 1
    return out


GIT_CONFIG_READ = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--get-color", "--get-colorbool", "--list",
                   "-l"}
GIT_CONFIG_DISPLAY = {"--name-only", "--show-origin", "--show-scope", "--null", "-z", "--bool", "--int", "--path",
                      "--includes", "--no-includes"}
GIT_CONFIG_VALUED = {"--type", "--default"}   # these take a value (--type=x or --type x)
GIT_CONFIG_LOCATION = {"--global", "--system", "--local", "--worktree"}
GIT_CONFIG_SUBCOMMANDS = {"get", "list", "set", "unset", "edit", "rename-section", "remove-section"}   # git >= 2.46


def git_config_read(rest):
    """`git config` in an allowlisted READ shape (fail closed): every option word a known read, display, type or
    location option (a location only together with a read), or the get/list subcommands, or one key with no option
    word at all (an implicit get). Any other word starting with '-' (an abbreviated --unset-a, --remove-s, …) or any
    other subcommand is a write."""
    pos, k, has_read, has_opt = [], 0, False, False
    while k < len(rest):
        t = rest[k]
        k += 1
        if not t.startswith("-"):
            pos.append(t)
            continue
        has_opt = True
        word = t.split("=", 1)[0]
        if word in GIT_CONFIG_READ:
            has_read = True
        elif word in GIT_CONFIG_VALUED:
            if "=" not in t:
                k += 1   # its value
        elif word not in GIT_CONFIG_DISPLAY and word not in GIT_CONFIG_LOCATION:
            return False   # an option outside the read shape: a write, or one the guard does not know
    if pos[:1] in (["get"], ["list"]):
        return True
    if has_read:
        return True
    return not has_opt and len(pos) == 1 and pos[0] not in GIT_CONFIG_SUBCOMMANDS   # `git config edit` is no key


def git_config_write(rest):
    """(key, value) when `git config` sets a key (`<key> <value>`, `--add`, `set <key> <value>`), else (None, None)."""
    reads = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--list", "-l", "--unset", "--unset-all",
             "--remove-section", "--rename-section", "--edit", "-e", "--show-origin", "--show-scope"}
    if any(t in reads for t in rest) or rest[:1] in (["get"], ["list"], ["unset"], ["remove-section"],
                                                     ["rename-section"], ["edit"]):
        return None, None
    pos, k = [], 0
    while k < len(rest):
        t = rest[k]
        if t in ("-f", "--file", "--blob", "--type", "--default", "--comment", "--value") and k + 1 < len(rest):
            k += 2
            continue
        if not t.startswith("-"):
            pos.append(t)
        k += 1
    if pos[:1] == ["set"]:
        pos = pos[1:]
    return (pos[0], pos[1]) if len(pos) >= 2 else (None, None)


def kill_targets_ok(args):
    """False when kill would signal a process group or every process: a value <= 0 where a pid stands (after the
    first pid, or after --), blanks and tabs stripped first (kill reads " -1" as -1)."""
    pid_seen = after_dd = skip = False
    for raw in args:
        a = raw.strip(" \t\n")
        if skip:
            skip = False
            continue
        if raw == "--" and not after_dd:
            after_dd = True
            continue
        if not after_dd and not pid_seen and raw in ("-s", "-n"):
            skip = True   # the signal name or number
            continue
        # an option is exactly "-…" (a signal); a word kill reads as a pid ("-1 " included) is judged as one
        if after_dd or pid_seen or not raw.startswith("-") or raw != a:
            if re.fullmatch(r"[-+]?\d+", a) and int(a) <= 0:
                return False
            pid_seen = True
    return True


# ----------------------------------------------------------------------------- writes by programs
def dev_path(raw, cwd):
    """The normalised absolute path when raw names /dev or something under it (//dev/x, ../../dev/x after a cd), else None."""
    if not raw or "$" in raw or "`" in raw:
        return None
    p = expand(raw)
    if not is_abs(p):
        if cwd is None:
            return None
        p = pjoin(cwd, p)
    p = norm(re.sub(r"^/+", "/", p))
    p = re.sub(r"^/+", "/", p)
    return p if p == "/dev" or p.startswith("/dev/") else None


def write_targets(prog, args):
    """Paths a program writes (or removes, for mv sources), as written on its command line."""
    opts_val = {"cp": {"-t", "--target-directory", "-S", "--suffix"}, "mv": {"-t", "--target-directory", "-S", "--suffix"},
                "ln": {"-t", "--target-directory", "-S", "--suffix"},
                "install": {"-t", "--target-directory", "-m", "--mode", "-o", "--owner", "-g", "--group", "-S", "--suffix"},
                "tee": set(), "rsync": {"-e", "--rsh", "--exclude", "--include", "--filter", "-f", "--chmod", "--rsync-path",
                                        "--exclude-from", "--include-from", "--files-from", "--log-file", "--backup-dir",
                                        "--partial-dir", "--temp-dir", "-T"}}
    vals, pos, target, i = opts_val.get(prog, set()), [], None, 0
    while i < len(args):
        t = args[i]
        if t == "--":
            pos += args[i + 1:]
            break
        if t in ("-t", "--target-directory") and i + 1 < len(args):
            target, i = args[i + 1], i + 2
            continue
        if t.startswith("--target-directory="):
            target, i = t.split("=", 1)[1], i + 1
            continue
        if prog in ("cp", "mv", "ln", "install") and re.fullmatch(r"-[A-Za-z]+", t) and "t" in t:
            k = t.index("t")  # a cluster such as -sft DIR or -ftDIR: t takes the rest, or the next word
            if k + 1 < len(t):
                target, i = t[k + 1:], i + 1
            elif i + 1 < len(args):
                target, i = args[i + 1], i + 2
            else:
                i += 1
            continue
        if t in vals:
            i += 2
            continue
        if t.startswith("-") and t != "-":
            i += 1
            continue
        pos.append(t)
        i += 1
    if prog == "tee":
        return pos
    if prog == "rsync":
        return [p for p in pos[-1:] if not re.match(r"^[\w.@-]+:", p)]
    if prog == "install" and any(t in ("-d", "--directory") for t in args):
        return pos
    if prog == "mv":
        return pos + ([target] if target else [])  # sources disappear, the destination is written
    if target:
        return [target]
    return pos[-1:] if len(pos) >= 2 else []


def tool_writes(prog, args):
    """Paths written by downloaders, tar and perl -i (directories as <dir>/x, so the dir itself is not 'the root')."""
    out, i = [], 0
    if prog in ("curl", "wget"):
        long_file = {"curl": ("--output",), "wget": ("--output-document", "--output-file", "--append-output")}[prog]
        long_dir = {"curl": ("--output-dir",), "wget": ("--directory-prefix",)}[prog]
        # short options that take a value; in a cluster (-fsSLo FILE, -qO FILE, -qOFILE) the first of them takes
        # the rest of the cluster, or the next word
        takes = {"curl": "AbcCdDeEFHKmoPQrtTuUwxXyYz", "wget": "aABDeiIloOPQRtTUwX"}[prog]
        file_short = {"curl": "o", "wget": "Ooa"}[prog]
        dir_short = {"curl": "", "wget": "P"}[prog]
        while i < len(args):
            t = args[i]
            if t in long_file + long_dir and i + 1 < len(args):
                out.append(args[i + 1] if t in long_file else args[i + 1].rstrip("/") + "/x")
                i += 2
                continue
            if t.startswith("--"):
                for o in long_file + long_dir:
                    if t.startswith(o + "="):
                        v = t.split("=", 1)[1]
                        out.append(v if o in long_file else v.rstrip("/") + "/x")
                i += 1
                continue
            if t.startswith("-") and len(t) > 1:
                for k in range(1, len(t)):
                    letter = t[k]
                    if letter in takes:
                        if k + 1 < len(t):
                            value = t[k + 1:]
                        elif i + 1 < len(args):
                            value, i = args[i + 1], i + 1
                        else:
                            value = None
                        if value is not None and letter in file_short:
                            out.append(value)
                        elif value is not None and letter in dir_short:
                            out.append(value.rstrip("/") + "/x")
                        break
            i += 1
        return [p for p in out if p != "-"]
    if prog == "tar":
        first = args[0] if args else ""
        flags = "".join(t[1:] for t in args if re.match(r"^-[A-Za-z]+$", t)) + (first if re.fullmatch(r"[A-Za-z]+", first) else "")
        extract = "x" in flags or "--extract" in args or "--get" in args
        create = "c" in flags or "r" in flags or "u" in flags or any(t in ("--create", "--append", "--update") for t in args)
        target, archive = None, None
        while i < len(args):
            t = args[i]
            if t in ("-C", "--directory") and i + 1 < len(args):
                target, i = args[i + 1], i + 2
                continue
            if t.startswith("--directory="):
                target = t.split("=", 1)[1]
            elif t in ("-f", "--file") and i + 1 < len(args):
                archive, i = args[i + 1], i + 2
                continue
            elif t.startswith("--file="):
                archive = t.split("=", 1)[1]
            elif re.match(r"^-[A-Za-z]*f$", t) and i + 1 < len(args):
                archive, i = args[i + 1], i + 2
                continue
            i += 1
        if extract:
            out.append((target or ".").rstrip("/") + "/x")
        if create and archive and archive != "-":
            out.append(archive)
        return out
    if prog == "perl":
        if not any(re.match(r"^-[a-zA-Z]*i", t) for t in args):
            return []
        files, script_given = [], False
        while i < len(args):
            t = args[i]
            if t in ("-e", "-E"):
                script_given, i = True, i + 2
                continue
            if re.match(r"^-[a-zA-Z]*[eE]$", t):  # -pie 'script'
                script_given, i = True, i + 2
                continue
            if t.startswith("-"):
                i += 1
                continue
            files.append(t)
            i += 1
        return files if script_given else files[1:]
    return []


def sed_files(args):
    if not any(re.match(r"^-[a-zA-Z]*i", t) or t.startswith("--in-place") for t in args):
        return []
    files, script_given, i = [], False, 0
    while i < len(args):
        t = args[i]
        if t in ("-e", "--expression", "-f", "--file"):
            script_given, i = True, i + 2
            continue
        if t.startswith(("--expression=", "--file=")):
            script_given, i = True, i + 1
            continue
        if t.startswith("-") and t != "-":
            i += 1
            continue
        files.append(t)
        i += 1
    return files if script_given else files[1:]


# ----------------------------------------------------------------------------- commands
def chdir(cwd, tgt):
    """The directory after `cd tgt` from cwd; None when it can't be known."""
    if "$" in tgt or "`" in tgt or tgt == "-" or re.fullmatch(r"[+-]\d+", tgt):
        return None
    tgt = expand(tgt)
    if not is_abs(tgt) and cwd is None:
        return None
    return norm(pjoin(cwd or "/", tgt))


def unwrap(words, cwd, ctx, depth):
    """Strip keywords, prefix assignments and wrappers: (words, cwd, keyword_seen, assignments).
    assignments: the NAME=value words stripped (prefix assignments and `env NAME=value`): the command's own
    environment when a command follows, plain statements (under a keyword) when none does."""
    kw, assigns = False, []
    while True:
        while words and words[0][0] in KEYWORDS:
            words, kw = words[1:], True
        while words and re.match(r"^\w+\+?=", words[0][0]):
            name, _, value = words[0][0].partition("=")
            assigns.append((name, value))
            words = words[1:]
        if not words:
            return words, cwd, kw, assigns
        prog = os.path.basename(words[0][0])
        if prog == "coproc":
            words = words[1:]
            if len(words) > 1 and re.fullmatch(r"\w+", words[0][0]) and words[1][0] == "{":
                words = words[1:]  # coproc NAME { …; }
            continue
        if prog not in WRAPPERS:
            return words, cwd, kw, assigns
        check_protected(prog, [w for w, _ in words[1:]], ctx)   # a rule on the wrapper itself (sudo, nohup, ...)
        if prog == "command" and any(w in ("-v", "-V") for w, _ in words[1:2]):
            return [], cwd, kw, []
        vals, rest, positional = WRAPPERS[prog], words[1:], 0
        if prog in ("timeout", "flock"):
            positional = 1  # the duration / the lock file
        while rest:
            t = rest[0][0]
            if t == "--":
                rest = rest[1:]
                break
            if t in vals and len(rest) > 1:
                if prog in ("env", "sudo", "doas") and t in ("-C", "--chdir", "-D"):
                    cwd = chdir(cwd, rest[1][0])
                if prog == "env" and t in ("-S", "--split-string"):
                    check_command(rest[1][0], cwd, ctx, depth + 1)
                rest = rest[2:]
                continue
            if t.startswith("-") and t != "-":
                if prog == "flock" and t in ("-c", "--command") and len(rest) > 1:
                    check_command(rest[1][0], cwd, ctx, depth + 1)
                    return [], cwd, kw, []
                if t.startswith("--chdir=") and prog in ("env", "sudo"):
                    cwd = chdir(cwd, t.split("=", 1)[1])
                rest = rest[1:]
                continue
            if prog in ("env",) and re.match(r"^\w+=", t):
                name, _, value = t.partition("=")
                assigns.append((name, value))
                rest = rest[1:]
                continue
            if positional:
                positional -= 1
                rest = rest[1:]
                if prog == "flock" and rest and rest[0][0] in ("-c", "--command") and len(rest) > 1:
                    check_command(rest[1][0], cwd, ctx, depth + 1)
                    return [], cwd, kw, []
                continue
            break
        words = rest


def shell_command_string(args):
    """For sh/bash -c (any short-option cluster holding c, e.g. -xc, -ec): the command string, else None."""
    i, has_c = 0, False
    while i < len(args):
        t = args[i]
        if t in ("-o", "+o", "-O", "+O", "--rcfile", "--init-file"):
            i += 2
            continue
        if t == "--":
            i += 1
            break
        if t.startswith("-") and not t.startswith("--") and "c" in t[1:]:
            has_c = True
            i += 1
            continue
        if t.startswith(("-", "+")) and t not in ("-", "+"):
            i += 1
            continue
        break
    return (args[i] if i < len(args) else "") if has_c else None


GIT_VARS = ("GIT_DIR", "GIT_WORK_TREE")
# Git settings that make git start a program, read a file of configuration, or run a git command line of their own.
# ONE table, source: git-config(1) "Variables" (alias.*, core.pager, pager.*, core.editor, sequence.editor,
# diff.external, diff.<driver>.command/textconv, core.sshCommand, core.fsmonitor, core.hooksPath, core.askPass,
# core.gitProxy, credential.helper, filter.<driver>.process/clean/smudge, merge.<driver>.driver,
# remote.<name>.uploadpack/receivepack, gpg.program, gpg.<format>.program, protocol.<name>.allow, include.path,
# includeIf.<condition>.path), git(1) "ENVIRONMENT VARIABLES" (GIT_PAGER, GIT_EDITOR, GIT_SEQUENCE_EDITOR,
# GIT_EXTERNAL_DIFF, GIT_SSH, GIT_SSH_COMMAND, GIT_ASKPASS, GIT_PROXY_COMMAND, GIT_ALLOW_PROTOCOL, GIT_CONFIG,
# GIT_CONFIG_GLOBAL, GIT_CONFIG_SYSTEM; PAGER, EDITOR, VISUAL, SSH_ASKPASS as git's fallbacks). Set through -c,
# --config-env, GIT_CONFIG_COUNT/KEY_n/VALUE_n, GIT_CONFIG_PARAMETERS, `git config` writes or the environment.
# Rows: (config key regex or None, environment variables, harmless values (lower case), kind). Kinds: "alias" (a
# git command line, or a program after "!"), "cmd" (a program: judged for the lead), "file" (a configuration file
# git reads: for the lead not judged), "protocol" (allows the ext:: transport, which runs a program). Sub-agents
# never set any of them to a value that is not harmless.
FALSE = ("", "false", "0", "no", "off")
EXEC_SETTINGS = (
    (r"alias\..+", (), (), "alias"),
    (r"core\.pager|pager\..+", ("GIT_PAGER", "PAGER"), FALSE + ("cat",), "cmd"),
    (r"core\.editor|sequence\.editor", ("GIT_EDITOR", "GIT_SEQUENCE_EDITOR", "EDITOR", "VISUAL"),
     FALSE + ("true", ":"), "cmd"),
    (r"diff\.external", ("GIT_EXTERNAL_DIFF",), FALSE, "cmd"),
    (r"diff\..+\.(?:command|textconv)", (), FALSE, "cmd"),
    (r"core\.sshcommand", ("GIT_SSH_COMMAND", "GIT_SSH"), FALSE, "cmd"),
    (r"core\.fsmonitor", (), FALSE, "cmd"),
    (r"core\.hookspath", (), FALSE, "file"),
    (r"core\.askpass", ("GIT_ASKPASS", "SSH_ASKPASS"), FALSE, "cmd"),
    (r"core\.gitproxy", ("GIT_PROXY_COMMAND",), FALSE, "cmd"),
    (r"credential\.(?:.+\.)?helper", (), FALSE, "cmd"),
    (r"filter\..+\.(?:process|clean|smudge)", (), FALSE, "cmd"),
    (r"merge\..+\.driver", (), FALSE, "cmd"),
    (r"remote\..+\.(?:uploadpack|receivepack)", (), FALSE, "cmd"),
    (r"gpg\.(?:.+\.)?program", (), FALSE, "cmd"),
    (r"protocol\.ext\.allow|protocol\.allow", ("GIT_ALLOW_PROTOCOL",), ("", "never"), "protocol"),
    (r"include\.path|includeif\..+\.path", (), ("",), "file"),
    (None, ("GIT_CONFIG", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM"), ("", "/dev/null"), "file"),
)
EXEC_ROWS = [(re.compile("^(?:%s)$" % k) if k else None, env, harmless, kind) for k, env, harmless, kind in EXEC_SETTINGS]
EXEC_ENV = {name: row for row in EXEC_ROWS for name in row[1]}
# Sub-agents get an ALLOWLIST instead (review r4: git's option and configuration parsing keeps leaking past any list
# of dangerous keys): a configuration override (-c, --config-env, GIT_CONFIG_COUNT/KEY_n/VALUE_n,
# GIT_CONFIG_PARAMETERS, `git config` writes) is refused unless its key is below with an allowed value (None: any).
BOOL = ("", "true", "false", "yes", "no", "on", "off", "1", "0")
SUBAGENT_CONFIG = (
    (r"core\.pager", ("cat",)),                          # plain output through cat, no other program
    (r"core\.editor", ("true", ":")),                    # never opens an editor (non-interactive commits)
    (r"core\.fsmonitor", ("false",)),                    # turns the monitor program off (the pause's read form)
    (r"diff\.external", ("",)),                          # turns an external diff program off (the pause's read form)
    (r"core\.quotepath", BOOL),                          # how paths are printed
    (r"color\..+", None),                                # colours of the output only
    (r"advice\..+", BOOL),                               # hint messages only
    (r"commit\.gpgsign|tag\.gpgsign", ("false", "no", "off", "0")),   # turns signing (a program) off
    (r"gc\.auto", ("0",)),                               # no automatic gc during the call
    (r"protocol\.allow", ("never",)),                    # narrows the transports, never widens them
    (r"init\.defaultbranch", None),                      # a branch name for git init
    (r"user\.name|user\.email", None),                  # identity in commits
    (r"safe\.directory", "lane-path"),                   # ownership check: only the own lane or scratch, no glob
)
SUBAGENT_ROWS = [(re.compile("^(?:%s)$" % k), allowed) for k, allowed in SUBAGENT_CONFIG]
# git's builtin commands (git(1) "GIT COMMANDS"): an alias with one of these names is ignored by git, never expanded
GIT_BUILTINS = frozenset("""add am annotate apply archive bisect blame branch bugreport bundle cat-file check-attr
check-ignore check-mailmap check-ref-format checkout checkout-index cherry cherry-pick citool clean clone column commit
commit-graph commit-tree config count-objects credential describe diagnose diff diff-files diff-index diff-tree
difftool fast-export fast-import fetch fetch-pack filter-branch fmt-merge-msg for-each-ref for-each-repo format-patch
fsck gc get-tar-commit-id grep gui hash-object help hook index-pack init instaweb interpret-trailers log ls-files
ls-remote ls-tree mailinfo mailsplit maintenance merge merge-base merge-file merge-index merge-tree mergetool mktag
mktree multi-pack-index mv name-rev notes pack-objects pack-redundant pack-refs patch-id prune prune-packed pull push
range-diff read-tree rebase receive-pack reflog refs remote repack replace replay rerere reset restore rev-list
rev-parse revert rm send-email send-pack shortlog show show-branch show-index show-ref sparse-checkout stash status
stripspace submodule switch symbolic-ref tag unpack-file unpack-objects update-index update-ref update-server-info
upload-archive upload-pack var verify-commit verify-pack verify-tag version whatchanged worktree write-tree
stage pickaxe init-db""".split())
# long options the guard reads (git parse-options also accepts any unambiguous prefix of them: --upload-p=, --pref=)
WATCHED_LONG = ("--upload-pack", "--receive-pack", "--exec", "--prefix", "--file", "--output", "--output-directory",
                "--global", "--system", "--worktree")


def canonical_option(t):
    """A `--word[=v]` that is a prefix of a watched long option, spelled out (an exact name wins; --outp is
    --output); anything else unchanged."""
    if not t.startswith("--") or len(t) < 4:
        return t
    word, eq, val = t.partition("=")
    if word in WATCHED_LONG:
        return t
    hits = [o for o in WATCHED_LONG if o.startswith(word)]
    if not hits:
        return t
    return min(hits, key=len) + eq + val


# transport options that name the program git runs on the other side (git-fetch(1), git-clone(1), git-push(1),
# git-ls-remote(1), git-archive(1)); -u means --upload-pack only for clone and ls-remote
TRANSPORT_OPTS = ("--upload-pack", "--receive-pack", "--exec")


def sq_word(text, i):
    """A word quoted the way git's sq_quote does ('…' pieces joined by \\' for a quote) from text[i]: (word, index
    after it). ValueError when it is not one."""
    out, n = [], len(text)
    if i >= n or text[i] != "'":
        raise ValueError("not a quoted word")
    while i < n and text[i] == "'":
        j = text.find("'", i + 1)
        if j < 0:
            raise ValueError("unterminated quote")
        out.append(text[i + 1:j])
        i = j + 1
        if text.startswith("\\'", i):
            out.append("'")
            i += 2
    return "".join(out), i


def config_parameters(text):
    """[(key, value or None)] of a GIT_CONFIG_PARAMETERS value, decoded as git decodes it ('\\'' is a quote);
    ValueError when it cannot be decoded."""
    out, i, n = [], 0, len(text)
    while i < n:
        if text[i] in " \t\n":
            i += 1
            continue
        key, i = sq_word(text, i)
        value = None
        if i < n and text[i] == "=":
            value, i = sq_word(text, i + 1)
        elif "=" in key:   # git's older form: one quoted 'key=value'
            key, value = key.split("=", 1)
        out.append((key, value))
    return out


def git_tracked(name):
    return name in GIT_VARS or name in EXEC_ENV or name.startswith("GIT_CONFIG_") or name == "GIT_CONFIG_PARAMETERS"


def git_exec_value(row, label, value, cwd, ctx, extra=""):
    """One command-running setting (a row of EXEC_SETTINGS) with its value (None: not known here): refused for
    sub-agents unless harmless; for the lead a program is judged (with extra, the words git appends)."""
    _, _, harmless, kind = row
    v = None if value is None else value.strip()
    if kind == "protocol":
        if v is not None and (v.lower() in harmless or (label.startswith("environment") and "ext" not in v.lower().split(":"))):
            return
    elif kind != "alias" and v is not None and v in harmless:   # case-sensitive: TRUE is a program, not true
        return
    if ctx["subagent"]:
        raise Deny(f"git {label}: that setting makes git start a program, read another configuration or run its own "
                   "command line; sub-agents never set it (run the command directly, where the guard can judge it)")
    if kind == "cmd" and v and "$" not in v and "`" not in v:
        check_command(v + extra, cwd, ctx, 1)
    elif kind == "alias" and v and v.startswith("!") and "$" not in v and "`" not in v:
        check_command(v[1:] + extra, cwd, ctx, 1)


def subagent_config_ok(key, value, cwd=None, ctx=None):
    """A configuration override a sub-agent may make: an allowlisted key with an allowed value (None: unknown).
    "lane-path": an absolute path, no glob, inside the agent's own lane worktree or the scratch root."""
    k = key.strip().lower()
    for rx, allowed in SUBAGENT_ROWS:
        if rx.match(k):
            if allowed == "lane-path":
                return lane_path_ok(value, cwd, ctx)
            return allowed is None or (value is not None and value.strip() in allowed)   # case-sensitive
    return False


def lane_path_ok(value, cwd, ctx):
    v = (value or "").strip()
    if not is_abs(v) or GLOB.search(v) or "$" in v or "`" in v or ".." in CONFIG.parts(v) or ctx is None:
        return False
    p = norm(v)
    if under(p, SCRATCH):
        return True
    root, is_main = checkout_of(p)
    if root is None or is_main:
        return False
    check_lane(root, ctx, "safe.directory")
    return True


def ext_command(key, value):
    """The program an ext:: transport in a configuration key or value names (remote.<n>.url=ext::…,
    url.ext::….insteadOf=…), else None."""
    for text in (value or "", key):
        if "ext::" in text:
            cmd = text.split("ext::", 1)[1]
            if text is key and "." in cmd:
                cmd = cmd.rsplit(".", 1)[0]   # url.<base>.insteadOf: the base ends before the last dot
            return cmd.replace("%S", "").replace("%s", "")
    return None


def git_exec_config(key, value, cwd, ctx, how):
    """A git configuration override (None value: not known here). Sub-agents: refused unless allowlisted
    (SUBAGENT_CONFIG). The lead: an ext:: transport anywhere in it is judged as a program, then its EXEC_SETTINGS row,
    if any, judges it."""
    k = key.strip().lower()
    if ctx["subagent"]:
        if not subagent_config_ok(key, value, cwd, ctx):
            raise Deny(f"git {how} {key}: sub-agents may override only harmless git settings (colour, advice, quoting, "
                       "identity, pager=cat, editor=true, fsmonitor=false, diff.external=, signing off); run the "
                       "command without it")
        return
    ext = ext_command(key, value)
    if ext is not None and "$" not in ext and "`" not in ext:
        check_command(ext, cwd, ctx, 1)
    for row in EXEC_ROWS:
        if row[0] is not None and row[0].match(k):
            git_exec_value(row, f"{how} {key}", value, cwd, ctx)
            return


def git_env(name, value, ctx):
    """Track GIT_DIR / GIT_WORK_TREE and the command-running git variables set earlier in the command (None: set to
    something unknown)."""
    if git_tracked(name):
        ctx["git_env"][name] = value if value is not None else "$?"


def literal_abs(value):
    """An absolute path with nothing the shell expands: `/x` and, on Windows, a drive path `C:/x` (or `/c/x`)."""
    return bool(re.fullmatch(r"[^$`*?\[\]]*", value)) and is_abs(value)


def set_var(name, value, ctx, eligible):
    """Record NAME=value when it is certain to hold for the next commands; forget NAME otherwise."""
    ctx["vars"].pop(name, None)
    ctx["mktemp_vars"].discard(name)
    if not eligible or value is None:
        return
    if re.fullmatch(r"\$\((\s*mktemp\b[^()]*)\)", value):
        ctx["mktemp_vars"].add(name)
        return
    if literal_abs(value):
        ctx["vars"][name] = norm(value)
        return
    path, kind = resolve_var(value, ctx) if value.startswith("$") else (None, None)
    if kind == "mktemp":
        ctx["mktemp_vars"].add(name)
    elif path is not None and literal_abs(path):
        ctx["vars"][name] = norm(path)


def forget_names(prog, args, ctx):
    """Builtins that set variables to values the guard can't know."""
    names = []
    if prog == "read":
        skip = {"-a", "-d", "-i", "-n", "-N", "-p", "-t", "-u"}
        i = 0
        while i < len(args):
            if args[i] in skip:
                if args[i] == "-a" and i + 1 < len(args):
                    names.append(args[i + 1])
                i += 2
                continue
            if not args[i].startswith("-"):
                names.append(args[i])
            i += 1
    elif prog == "printf" and "-v" in args:
        i = args.index("-v")
        names += args[i + 1:i + 2]
    elif prog in ("mapfile", "readarray"):
        names += [a for a in args if re.fullmatch(r"\w+", a)][-1:]
    elif prog == "unset":
        names += [a for a in args if not a.startswith("-")]
    for n in names:
        set_var(n, None, ctx, False)


MAX_NESTING = 6   # substitutions / shells / wrappers judged inside each other; one more is refused, never skipped


def check_command(cmd, cwd, ctx, depth=0):
    if depth > MAX_NESTING:
        # past the limit nothing inside can be checked: refused for everyone (a cutoff fails CLOSED)
        raise Deny(f"command nested more than {MAX_NESTING} levels deep (substitutions, shells, wrappers): it "
                   "can't be checked; simplify it")
    try:
        items = lex(cmd)
    except (ValueError, IndexError):
        # after a parse failure nothing of the rest can be checked: subagents get a deny whenever the text names
        # a program the guard checks; the lead only when it looks destructive (a RecursionError is a depth cutoff:
        # it reaches verdict(), which refuses it for everyone)
        if (ctx["subagent"] and names_checked(cmd)) or LOOKS_DESTRUCTIVE.search(cmd):
            raise Deny("command could not be parsed (unbalanced quotes or nesting) and names a checked program; "
                       "simplify it (e.g. write the message to a file and use -F/--body-file)")
        return
    seq = commands(items)
    stack, shaky = [], False  # shaky: the last cd may not have run (conditional), or may have failed (||)
    for k, entry in enumerate(seq):
        if entry[0] == "op":
            op = entry[1]
            if op != "&&" and ctx["chain"]:
                for name in ctx["chain"]:  # values set inside an && chain hold only until the chain ends
                    set_var(name, None, ctx, False)
                ctx["chain"] = []
            if op == "(":
                stack.append((cwd, dict(ctx["vars"]), set(ctx["mktemp_vars"])))
            elif op == ")" and stack:
                cwd, ctx["vars"], ctx["mktemp_vars"] = stack.pop()
            elif op == "||" and ctx.get("cd_seen"):
                nxt = seq[k + 1] if k + 1 < len(seq) else None
                if not (nxt and nxt[0] == "cmd" and nxt[1] and nxt[1][0][0] in ("exit", "return")):
                    cwd = None  # `cd X || exit` keeps X: nothing after it runs unless the cd worked
            elif op in (";", ";;", "&") and shaky:
                cwd, shaky = None, False
            continue
        prev_op = seq[k - 1][1] if k and seq[k - 1][0] == "op" else None
        next_op = seq[k + 1][1] if k + 1 < len(seq) and seq[k + 1][0] == "op" else None
        _, words, redirs, docs = entry
        ctx["cd_seen"] = False
        new = check_simple(words, redirs, docs, cwd, ctx, depth, prev_op, next_op)
        if ctx["cd_seen"]:
            shaky = shaky or prev_op in ("&&", "||")
        cwd = new
    if depth == 0:
        # trap bodies run later (at exit): check them against the command's final variables
        while ctx["traps"]:
            body, tcwd = ctx["traps"].pop(0)
            check_command(body, tcwd, ctx, 1)


def check_simple(words, redirs, docs, cwd, ctx, depth, prev_op, next_op):
    """Check one simple command; return the cwd for the commands after it."""
    sub_ctx = dict(ctx, vars=dict(ctx["vars"]), mktemp_vars=set(ctx["mktemp_vars"]))
    for _, subs in words:
        for s in subs:
            check_command(s, cwd, sub_ctx, depth + 1)
    for op, target, subs in redirs:
        for s in subs:
            check_command(s, cwd, sub_ctx, depth + 1)
    for body, quoted in docs:
        if not quoted:
            for s in dquote_subs(body):
                check_command(s, cwd, sub_ctx, depth + 1)
    for op, target, _ in redirs:
        if op in (">", ">>", ">|", "&>", "&>>", "<>") or (op == ">&" and not re.fullmatch(r"\d+-?|-", target)):
            check_write_path(target, cwd, ctx, "redirect")
    # a statement made only of assignments: remember literal values when certain
    plain = [w for w, _ in words]
    if plain and all(re.match(r"^\w+\+?=", w) for w in plain):
        piped = next_op in ("|", "|&", "&")
        eligible = prev_op in (None, ";", "(", ";;") and not piped
        in_chain = prev_op == "&&" and not piped  # holds for the rest of this && chain only
        for w in plain:
            name, _, value = w.partition("=")
            name, append = name.rstrip("+"), name.endswith("+")
            set_var(name, value, ctx, (eligible or in_chain) and not append)
            git_env(name, None if append else value, ctx)
            if in_chain and not eligible:
                ctx["chain"].append(name)
        return cwd
    if ctx["subagent"] and cwd is not None:
        # relative words resolved against the cwd (`cd /root && cat projects/<other>/.env`)
        texts = [w for w, _ in words]
        texts = texts[1:] if texts and "/" not in texts[0] else texts  # the program name is not a path
        for w in texts + [t for _, t, _ in redirs]:
            for part in (w, w.split("=", 1)[1] if "=" in w else ""):
                if part and not part.startswith(("/", "-", "$", "~")) and "`" not in part:
                    if OTHER_PROJECT.search(norm(pjoin(cwd, part)) + "/"):
                        raise Deny(f"'{part}' from {cwd} is another project's path; lanes never touch other projects")
    words, cmd_cwd, kw, assigns = unwrap(words, cwd, ctx, depth)
    if not words:
        for name, _ in assigns:  # NAME=value under a keyword or inside { }: conditional, so forget it
            set_var(name.rstrip("+"), None, ctx, False)
            git_env(name.rstrip("+"), None, ctx)
        return cwd
    prog = os.path.basename(words[0][0])
    args = [w for w, _ in words[1:]]
    check_protected(prog, args, ctx)   # every program, the shells, eval, xargs, su and watch included
    in_pipe = prev_op in ("|", "|&") or next_op in ("|", "|&", "&")
    conditional = kw or prev_op in ("&&", "||")
    if prog == "for" and args:
        set_var(args[0], None, ctx, False)
        return cwd
    if prog in ("case", "select", "function"):
        return cwd
    if prog in ("read", "printf", "mapfile", "readarray", "unset"):
        forget_names(prog, args, ctx)
        if prog == "unset":
            for a in args:
                ctx["git_env"].pop(a, None)
        return cwd
    if prog in ("local", "declare", "typeset", "export", "readonly"):
        for a in args:
            if a.startswith("-"):
                continue
            name, eq, value = a.partition("=")
            set_var(name.rstrip("+"), value if eq else None, ctx,
                    bool(eq) and not conditional and not in_pipe and not name.endswith("+"))
            if eq:
                git_env(name.rstrip("+"), None if (conditional or in_pipe or name.endswith("+")) else value, ctx)
        return cwd
    if prog in ("cd", "pushd", "popd"):
        if in_pipe:
            return cwd
        ctx["cd_seen"] = True
        if prog == "popd":
            return None
        targets = [a for a in args if a == "-" or not a.startswith("-") or a == "--"]
        targets = [a for a in targets if a != "--"]
        tgt = targets[0] if targets else (HOME if prog == "cd" else None)
        new = None if tgt is None else chdir(cmd_cwd, tgt)
        if new and ctx["subagent"] and (OTHER_PROJECT.search(new + "/") or new in PROJECT_DIRS):
            raise Deny(f"cd {tgt}: that is another project's directory (or the projects dir); lanes stay in the project's paths")
        return new
    if prog in SHELLS:
        inner = shell_command_string(args)
        for op, target, _ in redirs:
            if op == "<<<":  # a here-string fed to a shell is a script
                check_command(target, cmd_cwd, ctx, depth + 1)
        if inner is not None:
            check_command(inner, cmd_cwd, ctx, depth + 1)
        elif docs:
            for body, _ in docs:
                check_command(body, cmd_cwd, ctx, depth + 1)
        elif prev_op in ("|", "|&") and ctx["subagent"] and ("-s" in args or not [a for a in args if not a.startswith(("-", "+"))]):
            raise Deny(f"piping into {prog}: the commands it runs can't be checked; run them directly")
        return cwd
    if prog == "trap" and args:
        ctx["traps"].append((args[0], cmd_cwd))  # checked at the end, with the final variables
        return cwd
    if prog == "su":
        for i, a in enumerate(args):
            if a in ("-c", "--command") and i + 1 < len(args):
                check_command(args[i + 1], cmd_cwd, ctx, depth + 1)
            elif a.startswith("--command="):
                check_command(a.split("=", 1)[1], cmd_cwd, ctx, depth + 1)
        return cwd
    if prog == "watch":  # watch runs its arguments through sh -c
        rest = list(args)
        while rest and rest[0].startswith("-"):
            rest = rest[2:] if rest[0] in ("-n", "--interval", "-q", "--equexit") else rest[1:]
        if rest:
            check_command(" ".join(rest), cmd_cwd, ctx, depth + 1)
        return cwd
    if prog == "eval":
        check_command(" ".join(args), cmd_cwd, ctx, depth + 1)
        return cwd
    if prog == "xargs":
        rest, i = args, 0
        while i < len(rest) and rest[i].startswith("-"):
            i += 2 if rest[i] in XARGS_OPTS else 1
        inner = unwrap([(w, []) for w in rest[i:]], cmd_cwd, ctx, depth)[0]
        if inner and os.path.basename(inner[0][0]) in XARGS_DANGER + tuple(protected_programs()):
            raise Deny("xargs feeding a deleter, git, a shell or a protected command: targets can't be verified; "
                       "list literal paths/names")
        return cwd
    check_program(prog, args, cmd_cwd, ctx, " ".join(w for w, _ in words), assigns)
    return cwd


def check_program(prog, args, cwd, ctx, text, assigns=()):
    if prog in DELETERS:
        if prog == "shred":
            raise Deny("shred is not allowed")
        paths = [t for t in args if not t.startswith("-") or t == "-"]
        if prog == "truncate":
            vals = set()
            for i, t in enumerate(args):
                if t in ("-s", "--size", "-r", "--reference") and i + 1 < len(args):
                    vals.add(i + 1)
            paths = [t for i, t in enumerate(args) if not t.startswith("-") and i not in vals]
        if "--" in args:
            paths = args[args.index("--") + 1:]
        for p in paths:
            check_delete_path(p, cwd, ctx, prog)
        return
    if prog == "find":
        rest, follow = list(args), False
        while rest and (rest[0] in ("-H", "-L", "-P") or re.fullmatch(r"-O\d*", rest[0]) or rest[0] == "-D"):
            follow = follow or rest[0] in ("-H", "-L")
            rest = rest[2:] if rest[0] == "-D" else rest[1:]
        destructive, in_exec = "-delete" in rest, False
        for j, t in enumerate(rest):
            if in_exec:   # the words of an -exec command are its own (a grep -L there is no find option)
                in_exec = t not in (";", "+")
                continue
            follow = follow or t in ("-H", "-L", "-follow")   # GNU reads them as leading options, bfs anywhere
            if t in ("-exec", "-execdir", "-ok", "-okdir") and j + 1 < len(rest):
                in_exec = True
                inner = unwrap([(w, []) for w in rest[j + 1:]], cwd, ctx, 0)[0]   # env, nice, sudo, ... stripped
                if inner and os.path.basename(inner[0][0]) in DELETERS + SHELLS:
                    destructive = True
        if not destructive:
            return
        if follow:   # it deletes through symlinks under its start: where they lead is not in the command text
            raise Deny("find -L/-H/-follow that deletes follows symlinks to paths the guard cannot see; drop -L/-H "
                       "(find deletes a link itself, never its target) or list the paths to delete")
        starts = []
        for t in rest:
            if t.startswith("-") or t in ("(", ")", "!"):
                break
            starts.append(t)
        for s in (starts or ["."]):
            # find deletes inside its start: checked as <start>/x, but as <start>/* in the shared scratch (like a glob);
            # a start that holds a protected path (a checkout root, an ancestor of the project's roots) is judged like
            # rm -rf <start>, whatever tests narrow it (-name '*.md' still reaches the protected dirs' files)
            inner = "/*" if SCRATCH in pjoin(cwd or "/", s) else "/x"
            check_delete_path(s.rstrip("/") + inner if not GLOB.search(s) else s, cwd, ctx, "find-delete")
            check_delete_path(s, cwd, ctx, "find-delete", start=True)
        return
    if prog in ("chmod", "chown", "chgrp", "setfacl", "chattr", "mount", "umount"):
        if any(dev_path(t, cwd) for t in args if not t.startswith(("-", "+")) or t.startswith("/")):
            raise Deny(f"{prog} on /dev changes a device node of the shared host; never allowed")
        if prog in ("setfacl", "chattr", "mount", "umount"):
            return
    if prog in ("chmod", "chown", "chgrp") and any(t in ("-R", "--recursive") or (t.startswith("-") and "R" in t and not t.startswith("--")) for t in args):
        for p in [t for t in args if not t.startswith("-")][1:]:
            check_delete_path(p, cwd, ctx, f"{prog} -R")
        return
    if prog in ("mv", "cp", "tee", "ln", "install", "rsync"):
        targets = write_targets(prog, args)
        replaces = prog in ("mv", "ln", "install", "rsync") or (prog == "cp" and "--remove-destination" in args)
        if replaces and any(dev_path(t, cwd) for t in targets):
            # these replace the node itself (`ln -sf /etc /dev/null` turns /dev/null into a link for the whole host)
            raise Deny(f"{prog} onto or from /dev replaces a device node of the shared host; never allowed")
        for p in targets:
            check_write_path(p, cwd, ctx, prog)
            if prog == "rsync" and any(a == "--del" or a.startswith("--delete") for a in args):  # deletes inside its destination
                check_delete_path(p.rstrip("/") + "/x", cwd, ctx, "rsync --delete")
                check_delete_path(p, cwd, ctx, "rsync --delete", start=True)
        return
    if prog == "sed":
        for p in sed_files(args):
            check_write_path(p, cwd, ctx, "sed -i")
        return
    if prog in ("curl", "wget", "tar", "perl"):
        for p in tool_writes(prog, args):
            check_write_path(p, cwd, ctx, prog)
        return
    if prog in ("pkill", "killall"):
        raise Deny(f"{prog} matches processes of other projects; kill specific PIDs you started")
    if prog == "kill" and ((args and args[-1] in ("-1", "0")) or not kill_targets_ok(args)):
        raise Deny("kill of -1 (every process), 0 or a -<pgid> (a whole process group) is not allowed; kill the PIDs you started")
    if prog in ("reboot", "shutdown", "halt", "poweroff", "mkfs", "wipefs", "fdisk", "parted", "sfdisk") or prog.startswith("mkfs."):
        raise Deny(f"{prog} is never allowed")
    if prog == "dd":
        for t in args:
            if not t.startswith("of="):
                continue
            dev = dev_path(t[3:], cwd)
            if dev == "/dev/null":
                continue
            if dev:
                raise Deny("dd to a device is never allowed")
            check_write_path(t[3:], cwd, ctx, "dd")
        return
    if prog == "git":
        check_git(args, cwd, ctx, assigns)
        return


# ----------------------------------------------------------------------------- logging + entry point
def log_event(agent, tool, reason, override=None):
    """One record in <REPO>/<BOA_LOG_DIR>/guard-denials.jsonl (hook_config.guard_log: agent, tool, the reason capped at
    500 characters; the command line itself is not stored); True when it landed (an override always has to)."""
    return CONFIG.guard_log(CFG, HERE, agent, tool, reason, override)


def drive_rooted(p, base):
    """A file tool's own path (never a shell word): on Windows a rooted path without a drive (`/`, `/x`) is on the
    drive of base (the cwd), as the file system reads it; anything else is p as it is."""
    s = CONFIG.slash(p)
    if CONFIG.on_windows() and s.startswith("/") and not s.startswith("//"):
        d = re.match(r"[A-Za-z]:", CONFIG.slash(base or ""))
        if d:
            return d.group(0) + s
    return p


def check_read_paths(ti, cwd):
    """file-read events of sub-agents (file_path: a file read; path: a directory searched; glob: a path pattern
    searched, relative to path or the cwd): never another project, never the projects dir or anything above it."""
    for key in ("file_path", "path", "glob"):
        raw = ti.get(key)
        if not isinstance(raw, str) or not raw:
            continue
        base_dir = cwd
        if key == "glob" and not (is_abs(raw) or raw.startswith("~")):
            if ".." not in CONFIG.parts(raw):
                continue  # a relative pattern stays under `path`, which is checked as its own key
            # `../x/**` climbs out of `path` (or the cwd): resolve it there and check where it lands
            given = ti.get("path")
            if isinstance(given, str) and given:
                base_dir = norm(pjoin(cwd, expand(given)))
        p = drive_rooted(expand(raw), base_dir)
        p = norm(re.sub(r"^/+", "/", pjoin(base_dir, p)))
        if OTHER_PROJECT.search(raw) or OTHER_PROJECT.search(p + "/"):
            raise Deny(f"reading {raw}: another project on this host; lanes never touch other projects")
        if key in ("path", "glob"):
            base = norm(p[:GLOB.search(p).start()] or "/") if GLOB.search(p) else p
            if any(base == d or d.startswith(base.rstrip("/") + "/") for d in PROJECT_DIRS):
                raise Deny(f"searching {raw}: it spans other projects; search inside {WT}/<task>, {REPO} or {SCRATCH}")


def deadline_s():
    """Time budget for outside calls, under the guard's watchdog."""
    try:
        return min(7.0, max(0.5, float(os.environ.get(ENV_PREFIX + "GUARD_DEADLINE", "7"))))
    except ValueError:
        return 7.0


WATCHDOG_S = 8.5   # one verdict, under the wiring's 10 s timeout; past it the call is refused (fail closed)


def verdict(ev, cfg):
    """The verdict on one neutral pre-tool event: None (allow) or the reason to refuse."""
    configure(cfg)
    ti, tool = ev.input, ev.tool
    ctx = {"subagent": bool(ev.agent_id), "agent_id": ev.agent_id, "agent_type": ev.agent_type,
           "mktemp_vars": set(), "vars": {}, "notes": [], "chain": [], "traps": [], "git_env": {},
           "deadline": time.monotonic() + deadline_s()}
    cwd = ev.cwd or os.getcwd()
    agent = ev.agent_id or "lead"
    try:
        token = CONFIG.escape_token(ev, ENV_PREFIX)   # lead only (no agent_id), shell only, at the start
        if token:
            # lead-only, explicit, logged override after the lead has proven the target is ours; never unaudited
            if log_event("lead", tool, "OVERRIDE (lead-verified)", token):
                return None
            raise Deny(f"the lead's override could not be logged in {CFG['log_dir']}/guard-denials.jsonl: refused (an "
                       "override is always audited); fix the log dir")
        if tool == "shell":
            if ctx["subagent"] and OTHER_PROJECT.search(ev.command):
                raise Deny("this command names another project on this host (owner rule: lanes never touch other "
                           "projects, reads included); work only in the project's paths")
            try:
                check_command(ev.command, norm(cwd), ctx)
            except RecursionError:
                raise Deny("command nested too deeply to check; simplify it") from None
        elif tool == "file-write" and ctx["subagent"]:
            check_write_path(ti.get("file_path") or "", None, ctx, "file-write")
        elif tool == "file-read" and ctx["subagent"]:
            check_read_paths(ti, norm(cwd))
        for note in ctx["notes"]:
            log_event(agent, tool, "NOTE: " + note)
    except Deny as e:
        log_event(agent, tool, str(e))
        return f"{TAG} {e}"
    return None


HERE = os.path.abspath(__file__)


def main():
    if BROKEN:
        return refuse_broken(TAG, BROKEN)
    if sys.argv[1:] == ["--print-paths"]:
        try:
            cfg = CONFIG.load(here=HERE)
        except Exception as exc:   # noqa: BLE001 - a named message (a config line outside the grammar), no traceback
            print(f"guard_destructive: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        if cfg is None:
            print(json.dumps({"repo": None, "wt": None, "scratch": None}))
            return 0
        print(json.dumps({"repo": cfg["repo"], "wt": cfg["wt"], "scratch": cfg["scratch"]}))
        return 0
    return CONFIG.run_guard(TAG, verdict, HERE, WATCHDOG_S)


if __name__ == "__main__":
    sys.exit(main())
