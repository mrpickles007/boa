"""BOA lead status: "where is everything" in one screen, for the lead and for any agent that resumes the work.

Purpose:  one read-only screen of the whole project: dead guards first, every open lane with its last agent's verdict
          and the suggested next step, whether a new lane may start now, every warning (pause, pending owner rules,
          stale journals, stages over budget, open items, unfolded plan lines), resume files, HITL, guard denials and
          DONE/total.
When:     at every session start (the session hook injects it), after every hand-off, before starting a lane (the
          admission line), before every train, after a pause; any agent resuming the work runs it first.
Wire:     nothing to wire for the CLI; the session-start hook (`hooks/session_status.py`) calls it in --hook form.
Verify:   `.boa/bin/lead-status.sh --no-gh` prints "<project> lead status, <time>" and ends with the DONE line.
Outputs:  stdout only; the one file it writes is its bookmark <lead dir>/lead-status.seen (guard denials seen).
          Thresholds: BOA_LANE_CAP, BOA_ADMIT_MAX_LOAD, BOA_ADMIT_MIN_MEM_MB, BOA_LANE_MEM_MB, BOA_PENDING_MAX_H (24),
          BOA_OPEN_ITEMS_MAX (10), BOA_OPEN_ITEMS_MAX_DAYS (7), BOA_PLAN_PENDING_MAX_H (24).
Limits:   the admission needs MemAvailable and a load average (/proc on Linux): elsewhere it says "unknown"; the NEXT
          column is a hint from the last agent's report, not a decision; the forge list needs its CLI (gh, glab).

Usage: .boa/bin/lead-status.sh [--no-gh] [--no-mark]
       .boa/bin/lead-status.sh --hook        session-start hook form: the resume protocol plus the top of the status
                                             (<= 60 lines) as the runtime's additional context; no forge call, no
                                             bookmark; always exit 0
       .boa/bin/lead-status.sh --guards      only the guard health check (GUARD DOWN lines, if any)
  --no-gh    skip the forge's open-PR/MR list (offline)        --no-mark  leave the bookmark alone

Output, in this order:
  0. GUARD DOWN lines, first: every hook in <home>/hooks/*.py except the libraries the hooks load (MODULES:
     hook_config.py, shell_lexer.py) is run once, all at once, with a harmless neutral pre-tool event (shell `true`)
     through the configured interpreter (BOA_PYTHON, default python3; `-I`, at most 1 s each); a missing interpreter,
     a non-zero exit or a timeout gives "GUARD DOWN: <hook> (<why>)". A hook that does not act on pre-tool events
     ignores the probe; a deny (a guard refusing it, e.g. while paused) is an answer, not a dead guard, except the
     fail-closed refusal of a guard that could not judge it (a config line outside the grammar, no project, an
     internal error): "GUARD DOWN: <hook> (refuses every call: <its reason>)";
  1. one row per open lane (every linked worktree): task, head, commits ahead of <remote>/<main branch>, open PR/MR
     (BOA_FORGE github: gh; gitlab: glab; none: skipped), the newest lane-journal entry (<lead dir>/lanes/<task>.md:
     time, agent type, verdict line) and a suggested NEXT step derived from it, then the lane's newest
     <lead dir>/lanes.md registry line;
  2. lane admission: OPEN with how many lanes may start now, or CLOSED with the reasons. Open when the linked
     worktrees are under BOA_LANE_CAP, the 1-minute load is under BOA_ADMIT_MAX_LOAD (default: the CPU count),
     MemAvailable is at least BOA_ADMIT_MIN_MEM_MB and no pause flag; how many = the smallest of
     the free cap, the CPUs left under the load limit (one per lane) and the lanes the memory holds (BOA_LANE_MEM_MB
     each above the minimum, the first one at the minimum);
  3. warnings: the pause flag (<lead dir>/PAUSE), owner rules waiting in <lead dir>/owner-rules-pending.md (below its last
     fold marker) for more than BOA_PENDING_MAX_H hours (age from the oldest date written on a rule line, else mtime), a lane whose newest
     journal entry is older than its last commit (or that has commits but no journal), a lane whose newest registry
     line carries the token OVER-BUDGET (the lead records it there when a stage passes its budget), the open items of
     <lead dir>/open-items.md ("- [ ]" lines) above BOA_OPEN_ITEMS_MAX or the oldest at least BOA_OPEN_ITEMS_MAX_DAYS
     old, plan entries of <lead dir>/plan-additions-pending.md not folded (the memory blocks and "- " lines after the
     last "# ... Folded by ..." marker line, except "do not fold" ones) the oldest at least BOA_PLAN_PENDING_MAX_H hours old
     (an entry's age is the oldest date on its line that is not in the future, else the file's mtime);
  4. pause/resume files: <lead dir>/RESUME-LEAD.md and every <worktree>/.lane-resume/<role>.md; context: open PRs (or
     "unavailable"), Open HITL items of the active context (BOA_ACTIVE_CONTEXT), the open items (count, the oldest's
     age, the three oldest) and the plan lines not folded (count, the oldest's age), guard denials since the last
     check (<log dir>/guard-denials.jsonl);
  5. last line: DONE/total from tools/plan_lanes.py on BOA_PLAN_FILE.
Child processes (the forge CLI, the plan count, the probes) are bounded in time; their output goes through a temp file
in BOA_LEAD_TMPDIR (default the system temp dir), removed on every exit.
Environment (tests): BOA_MEMINFO, BOA_LOADAVG (files read instead of /proc/meminfo, /proc/loadavg), BOA_NPROC.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True   # no __pycache__ next to the installed tools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_tool as bt  # noqa: E402
import markers  # noqa: E402

TOOL = "lead-status"


PROTOCOL = ("Resume protocol: read AGENTS.md -> docs/agent-handbook.md -> memory-bank/RESUME.md -> "
            "memory-bank/08-OWNER-RULES.md and memory-bank/09-OPERATING-PROCEDURES.md (binding) -> run "
            ".boa/bin/lead-status.sh; live lane state is in the lead dir (lanes.md registry, lanes/<task>.md journal).")
# the registry's over-budget token (lead/lanes.md template): exactly this word, standing alone
OVER_BUDGET = r"(?<![A-Za-z0-9_-])OVER-BUDGET(?![A-Za-z0-9_-])"
STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[0-9]{2}:[0-9]{2}(?::[0-9]{2})?Z?)?")


def cut_to(n: int, s: str, src: str = "") -> str:
    """S cut to N characters with "…"; with SRC the cut also names the file holding the whole text."""
    s = s.replace("\t", " ")
    if len(s) <= n:
        return s
    return s[:n - 1] + "…" + (f" [cut: full text in {src}]" if src else "")


def more(shown: int, total: int, src: str) -> list[str]:
    """The line that says a list was cut and where the rest is ("" when nothing was left out)."""
    return [f"  … {total - shown} more, cut: see {src}"] if total > shown else []


def tdiv(a: int, b: int) -> int:
    """Integer division truncating toward zero (the shell's arithmetic)."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def stamp_epoch(s: str) -> int | None:
    """Epoch of a date stamp read as UTC (YYYY-MM-DD[THH:MM[:SS][Z]]); None when it is no date."""
    s = s.rstrip("Z")
    if "T" not in s:
        s += "T00:00"
    if re.fullmatch(r".*T[0-9]{2}:[0-9]{2}", s):
        s += ":00"
    return bt.from_utc(s + "Z")


# --- guard health ------------------------------------------------------------------------------------------------

def unfolded(lines: list[str] | None) -> list[str] | None:
    """The lines of a staging file below its last fold marker (a single-`#` line saying "Folded by"): what the
    train fold has not taken yet."""
    if lines is None:
        return None
    try:   # the fold marker's every accepted text (markers.json); English when the file cannot be read
        fold = markers.fold_regex()
    except markers.MarkersError:
        fold = re.compile(r"^# [^#].*Folded by")
    last = max((n for n, x in enumerate(lines) if fold.match(x)), default=-1)
    return lines[last + 1:]


def pending_entries(lines: list[str]) -> list[str]:
    """The entries of a staging file not yet folded: each memory block (its header line, which carries its datetime)
    and each hand-written "- " line; an entry whose text says "do not fold" is skipped."""
    out: list[str] = []
    block: list[str] | None = None
    for x in lines:
        if block is not None:
            block.append(x)
            if x.strip() == "@endmemory":
                if "do not fold" not in "\n".join(block):
                    out.append(block[0])
                block = None
        elif x.startswith("@@@memory"):
            block = [x]
        elif x.startswith("- ") and "do not fold" not in x:
            out.append(x)
    if block is not None and "do not fold" not in "\n".join(block):   # an unclosed block still waits for its fold
        out.append(block[0])
    return out


MODULES = ("hook_config.py", "shell_lexer.py")   # libraries the hooks load, not hooks


FAIL_CLOSED = "the guard could not judge this call"   # the guards' fail-closed refusal (hooks/hook_config.py)


def guard_hooks(env: bt.Env) -> list[str]:
    """The hooks to probe: every hooks/*.py except the libraries of MODULES."""
    d = os.path.join(env.home, "hooks")
    try:
        names = sorted(n for n in os.listdir(d) if n.endswith(".py") and os.path.isfile(os.path.join(d, n)))
    except OSError:
        return []
    return [n for n in names if n not in MODULES]


def grace() -> float:
    """How long a stopped child gets to clean up: HOOK_GRACE inside the session-start hook (BOA_LS_HOOK), else 1 s."""
    return bt.HOOK_GRACE if os.environ.get("BOA_LS_HOOK") else 1.0


def guard_check(env: bt.Env) -> list[str]:
    py = env["BOA_PYTHON"]
    probe = '{"event":"pre-tool","session_id":"boa-health","tool":"shell","tool_input":{"command":"true"}}'
    down: list[str] = []
    running: list = []
    try:
        for g in guard_hooks(env):
            gf = os.path.join(env.home, "hooks", g)
            if not shutil.which(py):
                down.append(f"{g} (interpreter '{py}' not found)")
            else:
                try:
                    with bt.held_stop_signals() as release:   # recorded before a stop can land (the finally below)
                        running.append((g, subprocess.Popen(
                            [py, "-I", gf], cwd=env.root, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, start_new_session=os.name != "nt", preexec_fn=release)))
                except OSError as exc:
                    down.append(f"{g} (exit 126 with '{py}': {exc.strerror})")
                    continue
                try:
                    running[-1][1].stdin.write(probe.encode())
                    running[-1][1].stdin.close()
                except OSError:
                    pass   # a probe that died before reading: its exit status says so
        deadline = time.monotonic() + 1.0
        for g, p in running:
            try:
                rc = p.wait(timeout=max(deadline - time.monotonic(), 0.01))
            except subprocess.TimeoutExpired:
                bt._kill_tree(p, bt.HOOK_GRACE)
                down.append(f"{g} (no answer in 1 s)")
                continue
            if rc != 0:
                down.append(f"{g} (exit {rc} with '{py}')")
            elif FAIL_CLOSED in (said := p.stdout.read(65536).decode("utf-8", "replace")):
                # the guard runs, but refuses even a harmless call: every call is refused until it is fixed
                m = re.search(re.escape(FAIL_CLOSED) + r" \((.*?)\)(?: and refuses|, and the lead)", said)
                down.append(f"{g} (refuses every call: {m.group(1)[:160] if m else 'it fails closed'})")
    finally:   # a stop mid-check ends every probe still running
        for _, p in running:
            if p.poll() is None:
                bt._kill_tree(p, bt.HOOK_GRACE)
    return [f"GUARD DOWN: {g} — every pre-tool check of this hook is off; fix it before any agent runs" for g in down]


# --- pieces of the screen ----------------------------------------------------------------------------------------

def last_entry(path: str) -> tuple[str, str] | None:
    """(header, verdict) of the newest journal entry, or None."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().split("\n")
    except OSError:
        return None
    hdr = v = weak = first = ""
    for raw in lines:
        if re.match(r"## [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]{8}Z \| ", raw):
            hdr, v, weak, first = raw, "", "", ""
            continue
        if hdr:
            line = re.sub(r"^[ \t#>*-]+", "", raw)
            low = line.lower()
            if not first and line:
                first = line
            if not v and re.search(r"review clean|findings?|green|fail|bounce|blocked|merged|escalat", low):
                v = line
            if not weak and re.search(r"done|tested|verdict|pass(ed)?[ =:]", low):
                weak = line
    if not hdr:
        return None
    return hdr, (v or weak or first)


def verdict_word(*keys: str, data: dict | None = None) -> str:
    """An alternation of the verdict words (markers.json `verdict.*`, every accepted language, lower case); the
    English words when the markers file cannot be read."""
    try:
        return "(?:" + "|".join(markers.regex(k, data)[3:-1] for k in keys) + ")"
    except markers.MarkersError:
        return "(?:" + "|".join(re.escape(k.split(".", 1)[1]) for k in keys) + ")"


def hint_for(role: str, verdict: str, data: dict | None = None) -> str:
    """The NEXT hint from the last agent's verdict line; its words are markers (verdict.*), so a report written in the
    product language is read as well as an English one."""
    v = verdict.lower()
    w = lambda *k: re.compile(verdict_word(*(f"verdict.{x}" for x in k), data=data), re.IGNORECASE)  # noqa: E731
    if role in ("builder", "builder-mid"):
        return "reviewer (code) / tester (docs-only)"
    if role == "reviewer":
        return "tester" if w("clean").search(v) and not re.search(verdict_word("verdict.finding", data=data) + r".*[1-9]", v, re.I) \
            else "builder delta (findings)"
    if role == "tester":
        return "integrator (train)" if w("green", "pass").search(v) and not w("fail", "bounce").search(v) \
            else "builder (failures)"
    if role == "integrator":
        return "residue check, remove worktree" if w("merged", "done").search(v) else "check the train"
    if role == "":
        return "no journal: resume from the registry"
    return "read the journal"


def ledger_stats(lines: list[str], path: str, now: int) -> list[tuple[str, str]]:
    """[(count, oldest epoch)] then up to three (YYYY-MM-DD or -, line) of the oldest entries."""
    try:
        mtime = int(os.stat(path).st_mtime)
    except OSError:
        mtime = now
    rows = []
    for i, t in enumerate(lines):
        es = [e for e in (stamp_epoch(m) for m in STAMP.findall(t)) if e is not None and e <= now]
        rows.append((min(es) if es else None, i, t))
    known = [e for e, _, _ in rows if e is not None]
    out = [(str(len(rows)), str(min(known) if known else mtime))]
    for e, _, t in sorted(rows, key=lambda r: (r[0] is None, r[0] or 0, r[1]))[:3]:
        out.append(("-" if e is None else time.strftime("%Y-%m-%d", time.gmtime(e)), t))
    return out


def read_lines(path: str) -> list[str] | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()
    except OSError:
        return None


def admission(env: bt.Env, lanes: int, lead: str) -> str:
    cpus_s = os.environ.get("BOA_NPROC") or str(os.cpu_count() or 1)
    cpus = int(cpus_s) if re.fullmatch(r"[1-9][0-9]*", cpus_s) else 1
    mem_kb = ""
    for line in read_lines(os.environ.get("BOA_MEMINFO") or "/proc/meminfo") or []:
        if line.startswith("MemAvailable:"):
            parts = line.split()
            mem_kb = parts[1] if len(parts) > 1 else ""
            break
    load = ((read_lines(os.environ.get("BOA_LOADAVG") or "/proc/loadavg") or [""])[0].split() or [""])[0]
    mx = env["BOA_ADMIT_MAX_LOAD"] or str(cpus)
    for n in ("BOA_LANE_CAP", "BOA_LANE_MEM_MB", "BOA_ADMIT_MIN_MEM_MB"):
        if not re.fullmatch(r"[0-9]+", env[n]):
            return f"Lane admission: unknown ({n} is not a number)"
    cap, lane_mb, min_mb = int(env["BOA_LANE_CAP"]), int(env["BOA_LANE_MEM_MB"]), int(env["BOA_ADMIT_MIN_MEM_MB"])
    num = r"[0-9]+(\.[0-9]+)?"
    if not re.fullmatch(r"[0-9]+", mem_kb) or not re.fullmatch(num, load) or not re.fullmatch(num, mx):
        return f"Lane admission: unknown (no MemAvailable/load average on this host); cap {cap}, {lanes} active"
    avail = int(mem_kb) // 1024
    l100, m100 = int(float(load) * 100 + 0.5), int(float(mx) * 100 + 0.5)
    by_cap = cap - lanes
    by_cpu = tdiv(m100 - l100 + 99, 100)
    by_mem = tdiv(avail - min_mb, lane_mb if lane_mb > 0 else 1) + 1 if avail >= min_mb else 0
    reasons = []
    if by_cap <= 0:
        reasons.append(f"{lanes} active of cap {cap}")
    if l100 >= m100:
        reasons.append(f"load {load} >= {mx}")
    if by_mem <= 0:
        reasons.append(f"MemAvailable {avail} MiB < {min_mb} MiB")
    if os.path.exists(os.path.join(lead, "PAUSE")):
        reasons.append("project paused")
    facts = (f"active {lanes} of cap {cap}; load {load} of max {mx} on {cpus} CPU(s); MemAvailable {avail} MiB "
             f"(min {min_mb} + {lane_mb} per lane)")
    if reasons:
        return f"Lane admission: CLOSED ({'; '.join(reasons)}) — {facts}"
    return f"Lane admission: OPEN, up to {min(by_cap, by_cpu, by_mem)} more lane(s) — {facts}"


def worktrees(root: str) -> list[tuple[str, str, str]]:
    out, path, head, branch = [], "", "", ""
    for line in (bt.git("-C", root, "worktree", "list", "--porcelain") or "").split("\n") + [""]:
        if line.startswith("worktree "):
            path, head, branch = line[9:], "", ""
        elif line.startswith("HEAD "):
            head = line.split()[1] if len(line.split()) > 1 else ""
        elif line.startswith("branch "):
            branch = re.sub(r"^refs/heads/", "", line[7:])
        elif line == "" and path:
            out.append((path, head, branch))
            path = ""
    return out


def forge_prs(env: bt.Env) -> tuple[dict[str, str], str]:
    forge = env["BOA_FORGE"]
    if forge == "github":
        argv, key = ["gh", "pr", "list", "--state", "open", "--limit", "100", "--json", "number,headRefName"], "gh"
    elif forge == "gitlab":
        argv, key = ["glab", "mr", "list", "--output", "json"], "gl"
    else:
        return {}, f"no forge configured (BOA_FORGE={forge})"
    rc, out = bt.run_bounded(argv, 8, cwd=env.root)
    prs: dict[str, str] = {}
    try:
        if rc != 0:
            raise ValueError
        for pr in json.loads(out):
            if key == "gh":
                prs[str(pr["headRefName"])] = f"#{pr['number']}"
            else:
                prs[str(pr["source_branch"])] = f"!{pr['iid']}"
    except (ValueError, KeyError, TypeError):
        return {}, f"unavailable ({forge} CLI failed or no network)"
    return prs, (", ".join(f"{n} {b}" for b, n in prs.items()) or "none")


# --- the screen --------------------------------------------------------------------------------------------------

def status(env: bt.Env, gh: bool, mark: bool) -> list[str]:
    out: list[str] = []
    if not os.environ.get("BOA_LS_NO_GUARDS"):
        out += guard_check(env)
    root = env.root
    lead, lead_rel = env.path(env["BOA_LEAD_DIR"]), env["BOA_LEAD_DIR"]
    logs = env.path(env["BOA_LOG_DIR"])
    now = int(time.time())
    base = f"{env['BOA_REMOTE']}/{env['BOA_MAIN_BRANCH']}"
    if bt.git("-C", root, "rev-parse", "-q", "--verify", f"{base}^{{commit}}") is None:
        base = env["BOA_MAIN_BRANCH"]
    prs, prs_note = forge_prs(env) if gh else ({}, "skipped (--no-gh)")

    warn: list[str] = []
    rows: list[str] = []
    verdicts: list[str] = []
    resumes: list[str] = []
    lanes = 0
    same = os.path.normcase(os.path.normpath(root))
    for path, head, branch in worktrees(root):
        if os.path.normcase(os.path.normpath(path)) == same:   # git prints C:/x where the root may be C:\x
            continue
        lanes += 1
        base_name = os.path.basename(path)
        m = re.search(r"(?:^|/)(" + bt.TASK_RE + r")(?:-|$)", branch)
        task = m.group(1) if m else (base_name if re.fullmatch(bt.TASK_RE, base_name) else "")
        ahead = (bt.git("-C", path, "rev-list", "--count", f"{base}..HEAD") or "?").strip() or "?"
        ctime_s = (bt.git("-C", path, "log", "-1", "--format=%ct", "HEAD") or "0").strip()
        ctime = int(ctime_s) if ctime_s.isdigit() else 0
        role = verdict = ""
        when = "-"
        entry = last_entry(os.path.join(lead, "lanes", f"{task}.md")) if task else None
        if entry:
            hdr, verdict = entry[0], entry[1].rstrip("\t")
            parts = hdr[3:].split("|")
            jts = parts[0].replace(" ", "")
            role = parts[1].replace(" ", "") if len(parts) > 1 else ""
            when = f"{role} {jts[5:16]}"
            je = bt.from_utc(jts) or 0
            if ctime > je:
                warn.append(f"{task}: newest journal entry ({jts}) is older than the lane's last commit "
                            f"({bt.utc(ctime)}): record the stage in {lead_rel}/lanes.md and check the agent")
        elif re.match(r"[1-9]", ahead):
            warn.append(f"{task or base_name}: {ahead} commit(s) ahead but no lane-journal entry: record the stage in "
                        f"{lead_rel}/lanes.md")
        rdir = os.path.join(path, ".lane-resume")
        try:
            resumes += [os.path.join(rdir, n) for n in sorted(os.listdir(rdir))
                        if n.endswith(".md") and os.path.isfile(os.path.join(rdir, n))]
        except OSError:
            pass
        reg = ""
        reg_lines = read_lines(os.path.join(lead, "lanes.md")) if task else None
        if reg_lines:
            hits = [x for x in reg_lines
                    if re.match(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]{8}Z " + re.escape(task) + r"(?:[^0-9a-z]|$)", x)]
            if not hits:
                hits = [x for x in reg_lines if re.search(r"(?:^|[^0-9A-Za-z-])" + re.escape(task) + r"(?:[^0-9a-z]|$)", x)]
            reg = hits[-1] if hits else ""
        rows.append(f"{task or base_name:<7} {head[:7]:<8} {ahead:>5} {prs.get(branch, '-'):<5} {cut_to(20, when):<20} "
                    f"{cut_to(34, verdict or '-'):<34} -> {hint_for(role, verdict)}")
        verdicts.append(verdict)
        if reg:
            rows.append("        registry: " + cut_to(110, reg, f"{lead_rel}/lanes.md"))
        if reg and re.search(OVER_BUDGET, reg):
            warn.append(f"{task}: OVER BUDGET in the registry: the agent stops and reports its state; accept, bounce "
                        "or extend once with a reason (a new registry line)")

    short = (bt.git("-C", root, "rev-parse", "--short", "HEAD") or "?").strip() or "?"
    out.append(f"{env['BOA_PROJECT_NAME']} lead status, {bt.utc(now)} ({env['BOA_MAIN_BRANCH']} {short})")
    if rows:
        out.append(f"{'LANE':<7} {'HEAD':<8} {'AHEAD':>5} {'PR':<5} {'LAST AGENT (UTC)':<20} {'VERDICT':<34} NEXT")
        out += rows
        if any(len((x or "")) > 34 for x in verdicts):
            out.append(f"  (a VERDICT cut with … is whole in {lead_rel}/lanes/<lane>.md)")
    else:
        out.append("No open lanes (no linked worktrees).")
    out.append(admission(env, lanes, lead))

    # --- warnings
    flag = os.path.join(lead, "PAUSE")
    if os.path.isfile(flag):
        fl = read_lines(flag) or []
        at = next((x[len("paused_at="):] for x in fl if x.startswith("paused_at=")), "")
        why = next((x[len("reason="):] for x in fl if x.startswith("reason=")), "")
        warn.insert(0, f"PROJECT PAUSED since {at}: {why} — resume with /resume-project (pause-flag.sh clear)")
    pend = os.path.join(lead, "owner-rules-pending.md")
    pl = unfolded(read_lines(pend))
    if pl is not None and any(not re.fullmatch(r"\s*(#.*)?", x) for x in pl):
        stamps = [e for x in pl if not re.match(r"\s*#", x) for e in (stamp_epoch(s) for s in STAMP.findall(x))
                  if e is not None]
        oldest = min(stamps) if stamps else int(os.stat(pend).st_mtime)
        age_h = tdiv(now - oldest, 3600)
        max_h = int(os.environ.get("BOA_PENDING_MAX_H") or 24)
        if age_h >= max_h:
            warn.append(f"owner rules pending in {lead_rel}/owner-rules-pending.md for {age_h} h (limit {max_h} h): fold "
                        "them into memory-bank/08-OWNER-RULES.md in the next train's docs(memory) commit")
        else:
            warn.append(f"owner rules pending in {lead_rel}/owner-rules-pending.md ({age_h} h): the next train's "
                        "docs(memory) commit folds them into 08")
    open_items: list[tuple[str, str]] = []
    oi = os.path.join(lead, "open-items.md")
    oil = read_lines(oi)
    if oil is not None:
        items = [re.sub(r"^\s*[-*] \[ \]\s*", "", x) for x in oil if re.match(r"\s*[-*] \[ \]", x)]
        open_items = ledger_stats(items, oi, now)
        n, oldest = int(open_items[0][0]), int(open_items[0][1])
        age_d = tdiv(now - oldest, 86400)
        max_n = int(os.environ.get("BOA_OPEN_ITEMS_MAX") or 10)
        max_d = int(os.environ.get("BOA_OPEN_ITEMS_MAX_DAYS") or 7)
        if n > max_n or (n > 0 and age_d >= max_d):
            warn.append(f"open items: {n} in {lead_rel}/open-items.md (limit {max_n}), the oldest {age_d} d old "
                        f"(limit {max_d} d): walk the ledger, close what is done, give the rest an owner task")
    plan_pending = None
    pp = os.path.join(lead, "plan-additions-pending.md")
    ppl = unfolded(read_lines(pp))
    if ppl is not None:
        sel = pending_entries(ppl)
        plan_pending = ledger_stats(sel, pp, now)[0]
        n, oldest = int(plan_pending[0]), int(plan_pending[1])
        age_h = tdiv(now - oldest, 3600)
        max_h = int(os.environ.get("BOA_PLAN_PENDING_MAX_H") or 24)
        if n > 0 and age_h >= max_h:
            warn.append(f"{n} plan line(s) in {lead_rel}/plan-additions-pending.md not folded, the oldest for {age_h} h "
                        f"(limit {max_h} h): fold them into the plan in the next train's docs(memory) commit, then mark "
                        "the fold")
    out.append("")
    out += (["Warnings:"] + [f"  ! {w}" for w in warn]) if warn else ["Warnings: none"]

    # --- pause/resume files
    if os.path.isfile(os.path.join(lead, "RESUME-LEAD.md")):
        out.append(f"Lead resume file: {os.path.join(lead, 'RESUME-LEAD.md').replace(os.sep, '/')} (read it first)")
    if resumes:   # paths with `/` on every OS, as the rest of the status
        out.append("Lane resume files (give each to the agent that resumes the lane):")
        out += [f"  {r.replace(os.sep, '/')}" for r in resumes]

    # --- context
    out.append(f"Open PRs: {prs_note}")
    acl = read_lines(env.path(env["BOA_ACTIVE_CONTEXT"]))
    if acl is not None:
        hitl, inside = [], False
        for x in acl:
            if x.startswith("## Open HITL"):
                inside = True
                continue
            if x.startswith("## "):
                inside = False
            if inside and x.startswith("- ") and not re.search(r"RESOLVED|CLOSED|^- Resolved", x) \
                    and x[2:].strip().rstrip(".").lower() != "none":   # the template's placeholder `- none`
                hitl.append(x)
        out.append(f"Open HITL ({len(hitl)}):")
        ac = env["BOA_ACTIVE_CONTEXT"]
        out += [f"  {cut_to(140, h, ac)}" for h in hitl[:6]] + more(min(6, len(hitl)), len(hitl), ac)
    if open_items:
        n, oldest = int(open_items[0][0]), int(open_items[0][1])
        out.append(f"Open items ({lead_rel}/open-items.md): {n} open, the oldest {tdiv(now - oldest, 86400)} d "
                   f"({time.strftime('%Y-%m-%d', time.gmtime(oldest))})")
        out += [f"  {day} {cut_to(120, text, f'{lead_rel}/open-items.md')}" for day, text in open_items[1:]]
        out += more(len(open_items) - 1, n, f"{lead_rel}/open-items.md")
        caught = [x for x in oil if re.match(r"\s*[-*] \[ \]", x)]
        left = sum(1 for x in caught if ": leftover: " in x)
        flagged = sum(1 for x in caught if "report without a '" in x)
        if left or flagged:
            out.append(f"  leftovers captured from agent reports: {left}; reports flagged without a Leftovers "
                       f"section: {flagged} (resume that agent)")
    if plan_pending:
        n, oldest = int(plan_pending[0]), int(plan_pending[1])
        out.append(f"Plan additions pending ({lead_rel}/plan-additions-pending.md): {n} not folded"
                   + (f", the oldest {tdiv(now - oldest, 3600)} h" if n else ""))
    try:
        md = markers.load()
        out.append(f"Product language (.boa/markers.json): {md['language']} — reports use its markers "
                   f"(Leftovers = '{markers.texts('section.leftovers', md)[0]}'); change it with boa language set")
    except markers.MarkersError as exc:
        out.append(f"Product language: markers file unreadable ({exc}): fix it — the report capture says so at every stop, lead-status reads the fold marker in English")
    gl = os.path.join(logs, "guard-denials.jsonl")
    total, newest = 0, ""
    try:
        with open(gl, "rb") as fh:
            data = fh.read()
        total = data.count(b"\n")
        last = data.decode("utf-8", "replace").split("\n")
        last = [x for x in last if x != ""]
        if total > 0 and last:
            o = json.loads(last[-1])
            newest = f"{o.get('ts') or 'no-ts'} {o.get('agent') or '?'}: " + cut_to(90, str(o.get('reason') or ''),
                                                                                 f"{env['BOA_LOG_DIR']}/guard-denials.jsonl")
    except (OSError, ValueError, AttributeError):
        pass
    seen_f = os.path.join(lead, "lead-status.seen")
    seen_l = read_lines(seen_f)
    seen_s = re.sub(r"[^0-9]", "", seen_l[0]) if seen_l else ""
    seen = int(seen_s) if seen_s else 0
    if seen > total:
        seen = 0
    out.append(f"Guard denials: {total - seen} new since the last check ({total} total)" + (f"; newest: {newest}" if newest else ""))
    if mark and os.path.isdir(lead):
        try:
            with open(seen_f, "w", encoding="utf-8") as fh:
                fh.write(f"{total}\n")
        except OSError:
            pass

    # --- progress (last line)
    report = ""
    if shutil.which(env["BOA_PYTHON"]):
        _, report = bt.run_bounded([env["BOA_PYTHON"], "-I", os.path.join(env.home, "tools", "plan_lanes.py"), "--plan",
                                    env.path(env["BOA_PLAN_FILE"])], 30, grace=grace())
    prog = ""
    for x in report.split("\n"):
        f = x.split("|")
        if len(f) > 5 and f[1] == " all ":
            prog = f"DONE {f[2].strip(' ')}, work-weighted {f[4].strip(' ')}"
            break
    out.append(prog or "DONE: unavailable (tools/plan_lanes.py failed)")
    return out


def hook_text() -> str:
    """The session-start text: the protocol, the guard check and the top 60 lines of the status, each bounded in
    time and run side by side (a status that runs out of time must not hide a dead guard)."""
    me = [sys.executable, "-I", "-B", os.path.abspath(__file__)]
    e = dict(os.environ, BOA_LS_NO_GUARDS="1", BOA_LS_HOOK="1")
    g = st = None
    try:
        with bt.held_stop_signals():   # both recorded before a stop can land: the finally below always sees them
            g = bt.Bounded(me + ["--guards"], 1.5, tag="lead-status", grace=bt.HOOK_GRACE)
            # the status child ends its own children with HOOK_GRACE (BOA_LS_HOOK): it gets a little more
            st = bt.Bounded(me + ["--no-gh", "--no-mark"], 1.8, env=e, tag="lead-status", grace=3 * bt.HOOK_GRACE)
        rc, guards = g.result()
        _, status_text = st.result()
    finally:
        for b in (g, st):
            if b is not None:
                b.close()
    guards = guards.rstrip("\n")
    if rc is None:
        guards = ("GUARD DOWN: the guard health check did not finish in 1.5 s (run .boa/bin/lead-status.sh "
                  "--guards)")
    lines = status_text.rstrip("\n").split("\n")
    if len(lines) > 60:   # 59 lines and the line that says the rest was cut and where it is: still 60
        lines = lines[:59] + [f"… {len(lines) - 59} more status lines cut: run .boa/bin/lead-status.sh for the whole status"]
    status_text = "\n".join(lines)
    return PROTOCOL + "\n\n" + (guards + "\n" if guards else "") + status_text


def main(argv: list[str]) -> int:
    bt.on_term_exit()   # a stop mid-check still removes the temp files and the children
    hook = guards = False
    gh = mark = True
    for a in argv:
        if a == "--hook":
            hook, gh, mark = True, False, False
        elif a == "--guards":
            guards = True
        elif a == "--no-gh":
            gh = False
        elif a == "--no-mark":
            mark = False
        elif a in ("-h", "--help"):
            sys.stdout.write(bt.help_text(__doc__))
            return 0
        else:
            print(f"{TOOL}: unknown option {a}", file=sys.stderr)
            return 2
    if hook:
        try:
            sys.stdin.buffer.read(1048576)
        except OSError:
            pass
        try:
            text = hook_text()
        except Exception:  # noqa: BLE001 - the hook never fails; the protocol line always goes out
            text = PROTOCOL
        import hook_contract as hc
        print(hc.Verdict(context=text).neutral())
        return 0
    env = bt.init(os.path.abspath(__file__), TOOL)
    if guards:
        for line in guard_check(env):
            print(line)
        return 0
    try:
        print("\n".join(status(env, gh, mark)))
    except BrokenPipeError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
