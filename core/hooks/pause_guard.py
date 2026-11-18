#!/usr/bin/env -S python3 -I
"""Pre-tool hook (every tool kind): the pause signal. While <REPO>/<BOA_LEAD_DIR>/PAUSE exists (written by
pause-project), a SUB-AGENT's tool calls are denied except, exactly, what it needs to stop cleanly:
- writing its own resume file <own worktree>/.lane-resume/<role>.md and its memories file .lane-resume/memories.md
  (file-write events);
- handing back its final report (the neutral tool kind `report`: the call some runtimes deliver a sub-agent's report
  through; refusing it would lose the report);
- shell commands made only of these commands, joined by `&&`, `;`, `||` or newlines (no pipe, no background, no subshell):
  - read-only git, exactly as `git -c core.fsmonitor=false -c diff.external= status|rev-parse …` and
    `… diff|log|show --no-textconv --no-ext-diff …`, and `git add` / `git commit` (no -c), in its own worktree (its
    cwd, `cd <own worktree>[/…]` earlier in the command, or `git -C <own worktree>`); a substitution only as a
    commit message `$(cat <<'EOF' … EOF)`;
  - appending an id-less memory block to its own `.lane-resume/memories.md`: `cat >> <own worktree>/.lane-resume/
    memories.md <<'EOF' … EOF` (the block's content is the memory lint's to judge);
  - `rm` of its own scratch entry <scratch root>/<…>/<own task>-<role>[/…] (literal paths), its place under the
    root given by the layout BOA_SCRATCH_GLOB (the entry at its last level, every level above it matching the glob);
  - `kill [-SIGNAL]` of its own PIDs: a process whose working directory is in its own worktree or scratch subdir
    (read from /proc: on a system without it, macOS and Windows, no PID can be proven own and every kill is refused
    while paused, a declared limit that fails closed).
  Refused inside that set: a here-document with an unquoted delimiter (its body expands), git's output options
  (`-o`, `--output…`) and `--ext-diff` / `--textconv`, kill options after the first PID.
Residual limit: `git add` / `git commit` still run what the repository's own configuration sets up (clean filters,
fsmonitor, the hooks); that configuration is the lead's (sub-agents cannot write it: the guard refuses their writes
into .git and their `git config` / `-c` of command-running keys), so the pause trusts it.
Everything else — file-read events included — is denied with the instruction: write the resume file, commit
wip, clean up, end the turn. The integrator gets its own instruction: an already-running merge may
finish, the next one (`gh pr merge`, `glab mr merge`, `git merge`, a rebase) is not started, and it reports the
stack state. The lead (an event without agent_id) is never blocked by the pause.

Purpose:  while the project is paused, let a sub-agent do only what it needs to stop cleanly.
When:     on every tool call of every sub-agent (the lead is never blocked by the pause).
Wire:     the agent registers it on its runtime's pre-tool event for every tool and pipes it the NEUTRAL event
          (references/hook-contract.md: {"event": "pre-tool", "tool": <kind>, "tool_input", "agent_id",
          "agent_type", "cwd"}): `<BOA_PYTHON> -I .boa/hooks/pause_guard.py`, timeout 5 s; a "deny" verdict, a
          non-zero exit or a timeout of the hook refuses the call (the wiring fails closed too).
Verify:   with the pause flag set, a sub-agent's read is denied with the stop instruction; `lead-status.sh --guards`
          prints no GUARD DOWN line for it.
Outputs:  a neutral deny verdict with the stop instruction, or nothing.
Limits:   `git add` / `git commit` still run the repository's own configured filters and hooks (see above). It FAILS
          CLOSED: an unreadable event, an internal error or no verdict within 3.5 s refuses the call, naming the
          lead's logged escape.

The own lane is the task the agent binding bound the agent to (agent_binding.py, recorded when the lead spawned it)
and its worktree. Unbound, it is the lane worktree the agent's cwd is in or, when the cwd is in none (a runtime may
start sub-agents in the main checkout), the first lane worktree the call names (its file path, or a path in its
command); its task is then that worktree's name when it is a task id (a lane worktree is <BOA_WT_DIR>/<task>,
lane-worktree.sh); without one, no task: no scratch, container or PID cleanup, which needs the task to prove
ownership. Known limit of the unbound fallback: a sub-agent running from the main checkout is given the lane its
call names, so it is an accident net, not a proof of identity. Known limit on Windows: paths are compared in the
guards' slash form (C:/x, a Git Bash /c/x read the same); a Git Bash mount path (/tmp, /usr) is compared as
written, never resolved to the Windows directory it names, so it matches only a root configured in that same spelling
(BOA_SCRATCH_ROOT='/tmp/x') and any other spelling of the place is refused; a drive-relative path (`C:x`, `C:..`) is not resolved
against that drive's current directory, so it never matches an own path and is refused (fail closed; no
agent writes that form by accident). Any internal error refuses the call (fail closed,
hook_config.run_guard). Python standard library only; invoked as `<BOA_PYTHON> -I <hook>`.
"""
import importlib.util
import json
import os
import posixpath
import re
import sys

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
    LEX, CONFIG, BROKEN = _load_sibling("shell_lexer"), _load_sibling("hook_config"), None
except Exception as _exc:   # noqa: BLE001 - a broken companion: every call is refused in main(), never a traceback
    LEX = CONFIG = None
    BROKEN = f"{type(_exc).__name__}: {_exc}"[:300]
TAG = "[boa-pause]"
GIT_READ = {"status", "diff", "log", "show", "rev-parse"}
GIT_OK = GIT_READ | {"add", "commit"}
READ_CONFIG = ("core.fsmonitor=false", "diff.external=")   # the -c pair every read command carries while paused
RESUME = re.compile(r"[A-Za-z0-9_-]+\.md")
PROC = "/proc"   # a module value so the suite can point it at a fixture


def joined(op):
    """An operator between two allowed segments: none (the first), &&, ;, || or newlines (no pipe, no background)."""
    return op is None or op.replace("\n", "") in ("", "&&", ";", "||")


def under(path, root):
    """path is root or inside it, on every OS (hook_config.inside: `/` and, on Windows, `\\` both separate)."""
    return CONFIG.inside(path, root)


def sl(p):
    """p normalised in the guards' one path form (hook_config.slash: as written on POSIX; on Windows `/` separators and
    an MSYS drive path `/c/x` read as `C:/x`, the form Git Bash commands use), "" for none: every path this guard
    compares, slices or prints is in this form, so a cwd, a config path and a command's path match on every OS."""
    return posixpath.normpath(CONFIG.slash(p)) if p else ""


def bound_lane(cfg, agent_id):
    """(task, its worktree) from the agent binding (agent_binding.task_of), or (None, None) when unbound."""
    try:   # loaded on use: without the binding module the agent is unbound, never a crash
        task = _load_sibling("agent_binding").task_of(cfg, agent_id)
    except Exception:
        task = None
    if not task:
        return None, None
    wt = next((d for d in CONFIG.checkouts(cfg)[1:] if os.path.basename(d) == task
               or os.path.basename(d).startswith(task + "-")), None)
    return (task, sl(wt)) if wt else (None, None)


def own_lane(cfg, cwd):
    """(own task or None, own worktree or None): the worktree holding the cwd, its name as the task when it is one."""
    cwd, wt = sl(cwd), sl(cfg["wt"])
    if cwd and under(cwd, wt) and cwd != wt:
        name = CONFIG.parts(cwd[len(wt) + 1:])[0]
        return (name if re.fullmatch(cfg["task_re"], name) else None), wt + "/" + name
    return None, None


def resolve(path, base):
    """path made absolute against base (the cwd), in the guards' path form (an MSYS drive path is absolute)."""
    path = CONFIG.slash(CONFIG.expanduser(path))
    return sl(path if CONFIG.is_abs(path) else (CONFIG.slash(base) or "/").rstrip("/") + "/" + path)


class Lane:
    """What a paused sub-agent owns: its task, worktree, scratch subdirs and processes."""

    def __init__(self, cfg, task, wt):
        self.cfg, self.task, self.wt = cfg, task, wt

    def scratch(self, p):
        """p is (inside) an own task entry <scratch>/<…>/<task>-<role> of the layout (cfg scratch_glob): literal, no
        glob, no '..'."""
        if not self.task or "$" in p or "`" in p or re.search(r"[*?\[]", p) or ".." in CONFIG.parts(p):
            return False
        p, root = sl(p), sl(self.cfg["scratch"])
        if not under(p, root) or p == root:
            return False
        entry = CONFIG.scratch_entry(CONFIG.parts(p[len(root) + 1:]), self.cfg["scratch_glob"])
        return bool(entry and entry.startswith(self.task + "-"))

    def pid(self, word):
        """A PID whose process works in the own worktree or an own scratch subdir."""
        if not re.fullmatch(r"[1-9][0-9]*", word) or word == "1":
            return False
        try:
            cwd = sl(os.readlink(os.path.join(PROC, word, "cwd")))
        except OSError:
            return False
        return bool((self.wt and under(cwd, self.wt)) or self.scratch(cwd))


def segment_allowed(words, cwd, lane):
    """One simple command of the allowed set; returns (allowed, the cwd after it)."""
    words, docs = LEX.heredoc_words(words)
    has_doc = len(docs) == 1
    if not words:
        return True, cwd
    if words[0] in ("cd", "pushd") and len(words) == 2:
        cwd = resolve(words[1], cwd)
        return bool(lane.wt and under(cwd, lane.wt)) or lane.scratch(cwd), cwd
    prog = os.path.basename(words[0])
    if prog in ("bash", "sh") and len(words) > 1:
        words, prog = words[1:], os.path.basename(words[1])
    if prog == "cat" and len(words) == 3 and words[1] == ">>" and has_doc:   # an id-less memory block, appended
        return bool(lane.wt and resolve(words[2], cwd) == lane.wt + "/.lane-resume/memories.md"), cwd
    if prog == "git":
        rest, where, cfgs = words[1:], cwd, []
        while rest and rest[0] in ("-C", "-c") and len(rest) > 1:
            if rest[0] == "-C":
                where = resolve(rest[1], where)
            else:
                cfgs.append(rest[1])
            rest = rest[2:]
        if not rest or not (lane.wt and under(where, lane.wt)):
            return False, cwd
        verb, opts = rest[0], rest[1:]
        writes = any(w in ("-o", "--output", "--ext-diff", "--textconv") or w.startswith(("--output=", "--output-"))
                     or (w.startswith("-o") and not w.startswith("--")) for w in opts)
        if verb in GIT_READ:   # exactly: git -c core.fsmonitor=false -c diff.external= <verb> (no drivers)
            ok = sorted(cfgs) == sorted(READ_CONFIG) and (
                verb not in ("diff", "log", "show") or ("--no-textconv" in opts and "--no-ext-diff" in opts))
        else:
            ok = verb in GIT_OK and not cfgs
        return bool(ok and not writes), cwd
    if prog == "rm":
        paths = [w for w in words[1:] if not w.startswith("-")]
        flags_ok = all(re.fullmatch(r"-[rRfv]+|--recursive|--force|--", w) for w in words[1:] if w.startswith("-"))
        return bool(paths and flags_ok and all(".." not in CONFIG.parts(p) and lane.scratch(resolve(p, cwd))
                                              for p in paths)), cwd
    if prog == "kill":
        first = next((k for k, w in enumerate(words[1:], 1) if not w.startswith("-")), len(words))
        opts, pids = words[1:first], words[first:]
        flags_ok = all(re.fullmatch(r"-(?:[0-9]+|[A-Z]+|SIG[A-Z]+)", w) for w in opts)   # options only before the pids
        return bool(pids and flags_ok and all(lane.pid(p) for p in pids)), cwd
    return False, cwd


def bash_allowed(cmd, cwd, lane):
    """Every segment is of the allowed set; a substitution only as a commit message."""
    LEX.DEADLINE[0] = float("inf")
    stripped, docs = LEX.split_heredocs(cmd)
    if any(not quoted for _, quoted in docs):
        return False   # an unquoted here-document expands $(...) and backquotes in its body
    # a substitution: only the commit-message idiom (cat of a here-document)
    out, i = [], 0
    while True:
        j = stripped.find("$(", i)
        if j < 0:
            out.append(stripped[i:])
            break
        k = LEX.close_paren(stripped, j + 2)
        body = stripped[j + 2:k]
        inner, inner_docs = LEX.split_heredocs(body)
        if any(not quoted for _, quoted in inner_docs):
            return False
        segs = LEX.op_segments(inner)
        if segs and all(LEX.heredoc_words(w)[0] == ["cat"] and joined(op) for w, op in segs):
            out.append(stripped[i:k + 1])
        else:
            return False
        i = k + 1
    stripped = "".join(out)
    if "`" in stripped or "<(" in stripped or ">(" in stripped:
        return False
    for words, op in LEX.op_segments(stripped):
        if not joined(op):
            return False
        ok, cwd = segment_allowed(words, cwd, lane)
        if not ok:
            return False
    return True


def named_lane(wt):
    """The pattern of a lane directory named in a call: the worktrees dir wt (guards' form), then `/` and the lane's
    name; on Windows also spelt with `\\` or as an MSYS drive path (`/c/...`), each followed by `/` or `\\`."""
    if not CONFIG.on_windows():
        return re.escape(wt.rstrip("/")) + r"/([^/\s'\";&|()<>`$]+)"
    spell = {wt, wt.replace("/", "\\")}
    d = re.match(r"([A-Za-z]):(/.*)", wt)
    if d:
        spell |= {"/" + d.group(1).lower() + d.group(2), "/" + d.group(1).upper() + d.group(2)}
    alt = "|".join(re.escape(x.rstrip("/\\")) for x in sorted(spell, key=len, reverse=True))
    return r"(?:" + alt + r")[/\\]([^/\\\s'\";&|()<>`$]+)"


def flag_kind(pause):
    """What stands at the PAUSE path when it is not a regular file, as boa_tool.pause_state (loaded by path) names it:
    a FIFO, a device, a socket, a directory (special_kind: one stat, never an open, a FIFO would hang the guard) or a
    dangling symbolic link. Called only when something is there (lexists) and it is not a regular file; toward the
    safe side it is a pause whatever it is: "not a regular file" when it cannot be told what it is (boa_tool missing
    or broken, the stat failing)."""
    try:
        tools = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
        spec = importlib.util.spec_from_file_location("boa_tool", os.path.join(tools, "boa_tool.py"))
        bt = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bt)
        return bt.pause_state(pause)[1] or "not a regular file"
    except Exception:  # noqa: BLE001 - cannot tell: still a pause
        return "not a regular file"


def decide(ev, cfg):
    """None to allow, or the reason to deny (ev: the neutral pre-tool event, hook_config.GuardEvent)."""
    pause = os.path.join(cfg["repo"], cfg["lead_dir"], "PAUSE")
    if not ev.agent_id or not os.path.lexists(pause):
        return None
    special = None if os.path.isfile(pause) else flag_kind(pause)
    tool, ti, cwd = ev.tool, ev.input, ev.cwd
    task, wt = bound_lane(cfg, ev.agent_id)
    if wt is None:
        task, wt = own_lane(cfg, cwd)
    if wt is None:   # the cwd binds no lane (a runtime may start sub-agents in the main checkout): the lane the call names
        target = ti.get("file_path") if tool == "file-write" else ti.get("command")
        m = re.search(named_lane(sl(cfg["wt"])), str(target or ""))
        if m:
            task, wt = own_lane(cfg, sl(cfg["wt"]) + "/" + m.group(1))
    lane = Lane(cfg, task, wt)
    if tool == "report":   # its final report, handed back: the pause wants it delivered
        return None
    if tool == "file-write":
        p = resolve(ti.get("file_path") or "", cwd)
        if wt and posixpath.dirname(p) == wt + "/.lane-resume" and RESUME.fullmatch(posixpath.basename(p)):
            return None
    elif tool == "shell":
        try:
            if bash_allowed(ti.get("command") or "", resolve(cwd, "/") if cwd else None, lane):
                return None
        except ValueError:
            pass
    if special:   # never opened: a FIFO would hang every call
        why = f"the pause flag {pause} is {special}, not a regular file: treated as paused, remove it to resume"
    else:
        try:
            with open(pause, encoding="utf-8", errors="replace") as fh:
                why = re.sub(r"[\x00-\x1f]+", " ", fh.read(400).split("\n", 1)[0]).strip()[:200]
        except OSError:
            why = ""
    role = re.sub(r"[^A-Za-z0-9_-]", "", ev.agent_type) or "<role>"
    w = wt or sl(cfg["wt"]) + "/<task>"
    t = task or "<task>"
    entry = "/".join(c if not re.search(r"[*?\[]", c) else "<dir>" for c in cfg["scratch_glob"][:-1]) + f"/{t}-{role}"
    head = f"{TAG} project paused{' (' + why + ')' if why else ''}: stop now. "
    if role == "integrator":
        head += ("Integrator: a merge command already running may finish, but do not start the next merge "
                 "(no gh pr merge / glab mr merge / git merge / rebase). Report the stack state: which lanes are "
                 "merged, which are stacked and at which commit, the last gate result. ")
    return (head + f"1) Write your resume file {w}/.lane-resume/{role}.md (task, goal, branch, head, uncommitted "
            "work, deliverables done/partial/todo with paths, remaining steps, every lead message, open questions, "
            f"verify commands); id-less memory blocks go to {w}/.lane-resume/memories.md. 2) Commit wip: "
            f"git -C {w} add -A && git -C {w} commit -m 'wip({t}): <what>' (or say "
            "what stays uncommitted); read git only as git -c core.fsmonitor=false -c diff.external= status, or "
            "diff/log/show with --no-textconv --no-ext-diff. 3) Clean up only your own: "
            f"rm -rf <scratch>/{entry.lstrip('/')}, kill <your PIDs>; name in your resume file any "
            f"other resource your lane started (labelled {cfg['label_key']}={t}): the lead removes it. "
            "4) End your turn with a short report (handing it back is allowed). Nothing else runs "
            "until the lead resumes the project.")


WATCHDOG_S = 3.5   # one verdict, under the wiring's 5 s timeout; past it the call is refused (fail closed)
HERE = os.path.abspath(__file__)


def main():
    if BROKEN:
        return refuse_broken(TAG, BROKEN)
    return CONFIG.run_guard(TAG, decide, HERE, WATCHDOG_S)


if __name__ == "__main__":
    sys.exit(main())
