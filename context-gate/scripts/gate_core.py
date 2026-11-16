#!/usr/bin/env python3
"""context-gate core, two profiles chosen by config.json "profile" (mode A).

  light    two effects at the agent's pre-compaction hook, and nothing else:
             1. an L0 snapshot: a byte-exact copy of the raw transcript on disk (append-only per session);
             2. the EXTENSION of the native compaction prompt: printed on stdout, the harness appends it
                to the compaction's custom instructions (precedence block verbatim, then next_action ->
                goal -> constraints, then the project's custom instructions, then the path of the L0
                just taken).
  l0-only  (default, and the fallback for an unknown profile or an unreadable config.json) for a
             runtime that cannot extend the compaction prompt: effect 1 only; stdout stays empty.
             The "After a compaction" rules of the lead and of the agent definitions carry the
             "read L0 when in doubt" instruction instead. The extension is printed only when the
             config positively says light: the snapshot is the guarantee, the extension a bonus
             the runtime must be proven to accept.

No digest, no injection, no turn-end checkpoint, no model call: zero calls beyond the native
compaction. Pure standard library, Python >= 3.8. Diagnostics go to stderr (the hook wrapper sends
them to hook.log); stdout carries only the documented payload of each subcommand.

Subcommands:
  precompact  snapshot, then (light) print the extension text or (l0-only) print nothing; ALWAYS
              exits 0 (the gate never blocks a compaction: if the snapshot fails the live transcript
              is still on disk, and the light extension says so; l0-only only logs it)
  snapshot    snapshot only; stdout one JSON line; exit 0 ok / 2 transcript missing or unreadable /
              3 lock contention
  selftest    synthetic round-trip in a temp dir; stdout {"passed":bool,"checks":[...]}; exit 0 / 1
  gc          --older-than <N>d: delete conversations whose chain.json is older; stdout {"removed":[]}
"""
import argparse
import contextlib
import datetime as _dt
import glob
import hashlib
import io
import json
import os
import random
import shutil
import sys
import tempfile
import time

SCHEMA_CHAIN = "context-gate/chain/1"
EXIT_OK, EXIT_FAIL, EXIT_INTEGRITY, EXIT_LOCK = 0, 1, 2, 3
PROFILES = ("light", "l0-only")
# Claude Code 2.1.322 cuts a PreCompact hook's stdout at 10,000 characters (read in the running binary).
# The cap comes from config.json probe.extension_cap_chars (what the install measured for the runtime in
# use); the extension stays EXTENSION_HEADROOM under it, so the L0 line at the end is never the part cut.
DEFAULT_EXTENSION_CAP = 10000
EXTENSION_HEADROOM = 500
# Byte-identical to assets/precedence-block.txt; used only when prompts/precedence-block.txt is absent.
PRECEDENCE_FALLBACK = """GROUND TRUTH PRECEDENCE
This digest is a reconstruction of a compacted conversation, not a source of truth.
It may be stale, incomplete, or wrong. Where any statement below conflicts with
observable reality, observable reality is correct. Precedence, highest first:
1. The working tree as it exists on disk right now.
2. Git state: committed history, diffs, branch, staged and unstaged changes.
3. Remote state: GitHub/GitLab issues, pull requests, CI results, review comments.
4. Project instruction files and configuration checked into the repository.
5. The persistent memory layer, if one is configured for this agent.
6. This digest.
7. Any compaction summary produced by the agent runtime itself.
Verification is cheap and staleness is likely: a file is read before anything this
digest says about it is acted on. A record's `src`, if any, names the raw transcript
snapshot and the line ranges it cites; the raw transcript is the authoritative
record of what was said, and this digest is not.
"""
LIGHT_INSTRUCTIONS = """
Instructions for this summary (context-gate, light profile):
- Begin the summary with the GROUND TRUTH PRECEDENCE block above, copied verbatim.
- Then, in this order: (1) next_action: the exact next step to take; (2) the active goal;
  (3) the constraints, decisions and user directives still in force, quoted short and verbatim.
- Mark anything that was superseded as superseded, naming what replaced it.
"""
DEFAULT_CONFIG = {
    "schema": "context-gate/config/1",
    "profile": "l0-only",
    "agent": {"name": "unknown", "version": "unknown"},
    "probe": {"extension_cap_chars": DEFAULT_EXTENSION_CAP},
    "transcript": {
        "event_field": "transcript_path", "glob": None,
        "fields": {"session_id": "sessionId", "record_id": "uuid", "timestamp": "timestamp"},
        "boundary": {"field": "subtype", "value": "compact_boundary"},
        "write_lag": True, "settle_ms": 1500,
    },
}


# ----------------------------------------------------------------------------- utilities
def log(msg):
    sys.stderr.write("[context-gate] %s %s\n" % (utc_iso(), msg))


def utc_compact():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def describe_error(e):
    """One line naming the reason and the file, never the content being read."""
    if isinstance(e, UnicodeDecodeError):
        return "not valid UTF-8 (%s at byte %d)" % (e.reason, e.start)
    if isinstance(e, OSError):
        return "%s: %s" % (e.strerror or e.__class__.__name__, e.filename) if e.filename else str(e.strerror)
    text = str(e)
    return "%s: %s" % (e.__class__.__name__, text[:300])


def _fsync_dir(d):
    if os.name == "posix":
        try:
            fd = os.open(d, os.O_RDONLY)
            os.fsync(fd)
            os.close(fd)
        except OSError:
            pass


def atomic_write_bytes(path, data):
    """write tmp -> fsync -> replace -> fsync dir: a half-written file is never visible."""
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    tmp = "%s.tmp-%d-%04x" % (path, os.getpid(), random.randint(0, 0xFFFF))
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _fsync_dir(d)


def read_json_object(path):
    """(obj, None) when readable as a JSON object; (None, None) when absent; (None, reason) when
    present but unusable -- never taken for absent, so it is never silently written over."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None, None
    except (OSError, ValueError) as e:
        return None, describe_error(e)
    return (data, None) if isinstance(data, dict) else (None, "not a JSON object")


def deep_merge(base, override):
    out = dict(base)
    for k, v in (override or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def get_path(obj, dotted):
    cur = obj
    for part in (dotted or "").split(".") if dotted else []:
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur if dotted else None


def parse(line):
    try:
        return json.loads(line)
    except ValueError:
        return None


def integrity_trim(lines):
    """Drop trailing empty lines and a trailing tail that does not parse (a write in progress)."""
    dropped = 0
    while lines and lines[-1] == b"":
        lines.pop()
    while lines and parse(lines[-1]) is None:
        lines.pop()
        dropped += 1
    return lines, dropped


# ----------------------------------------------------------------------------- root / config
class Root:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        config, reason = read_json_object(os.path.join(self.path, "config.json"))
        if reason is not None:
            log("config.json cannot be read (%s): running on the DEFAULTS" % reason)
        self.config = deep_merge(DEFAULT_CONFIG, config or {})
        self.profile = self.config.get("profile")
        if self.profile not in PROFILES:
            log("config.json profile is %r (known: %s): running as l0-only"
                % (self.profile, ", ".join(PROFILES)))
            self.profile = "l0-only"
        cap = (self.config.get("probe") or {}).get("extension_cap_chars")
        if isinstance(cap, bool) or not isinstance(cap, int):
            if cap is not None:
                log("probe.extension_cap_chars %r is not an integer: using %d" % (cap, DEFAULT_EXTENSION_CAP))
            cap = DEFAULT_EXTENSION_CAP
        self.extension_cap = cap - EXTENSION_HEADROOM
        if self.extension_cap <= 0:  # no room for any extension: print nothing, as l0-only does
            log("probe.extension_cap_chars is %d, not above the %d headroom: no extension will be printed"
                % (cap, EXTENSION_HEADROOM))
        self.conversations = os.path.join(self.path, "conversations")
        os.makedirs(self.conversations, exist_ok=True)

    def read_prompt(self, name, fallback=""):
        p = os.path.join(self.path, "prompts", name)
        try:
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return fallback


def find_root(explicit):
    if explicit:
        return Root(explicit)
    cur = os.getcwd()
    while True:
        cand = os.path.join(cur, ".context-gate")
        if os.path.isdir(cand):
            return Root(cand)
        parent = os.path.dirname(cur)
        if parent == cur:
            raise SystemExit("[context-gate] no .context-gate root found (use --root)")
        cur = parent


def read_event(spec):
    if not spec:
        return {}
    if spec == "-":
        raw = "" if sys.stdin.isatty() else sys.stdin.read()
    else:
        with open(spec, "r", encoding="utf-8") as f:
            raw = f.read()
    raw = raw.strip()
    if not raw:
        return {}
    try:
        event = json.loads(raw)
    except ValueError:
        log("event payload is not JSON; ignoring it")
        return {}
    return event if isinstance(event, dict) else {}


# ----------------------------------------------------------------------------- lock
class Lock:
    """One exclusive lock per conversation on work/lock, the same mechanism as the package's tools: fcntl.flock on
    Linux/macOS, msvcrt.locking on Windows, taken without waiting (contention = EXIT_LOCK) and released by the
    operating system when its holder ends, so a lock is never left stale and nothing ever takes one over. A platform
    with neither is refused (logged, reported as contention): no weaker fallback. The lock file stays on disk (removing
    it would let two holders lock two different files). This core stays standalone: it imports nothing of the package."""

    def __init__(self, conv_dir):
        self.path = os.path.join(conv_dir, "work", "lock")
        self.fh = None
        self.kind = None

    def acquire(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        try:
            import fcntl
            kind = "fcntl"
        except ImportError:
            try:
                import msvcrt  # noqa: F401
                kind = "msvcrt"
            except ImportError:
                log("no file locking on this platform (needs fcntl or msvcrt): snapshot refused")
                return False
        try:
            fh = open(self.path, "a+")
        except OSError as e:
            log("lock file not usable (%s)" % describe_error(e))
            return False
        try:
            if kind == "fcntl":
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                import msvcrt
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            fh.close()
            return False
        self.fh, self.kind = fh, kind
        return True

    def release(self):
        if self.fh is None:
            return
        if self.kind == "msvcrt":
            import msvcrt
            try:
                self.fh.seek(0)
                msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        self.fh.close()  # closing releases an fcntl lock
        self.fh = None


# ----------------------------------------------------------------------------- chain
def new_chain(conversation_id, agent):
    return {"schema": SCHEMA_CHAIN, "conversation_id": conversation_id, "agent": agent,
            "sessions": [], "last": {}, "seq": 0, "linkage": "unknown"}


def chain_problem(chain):
    """Why a chain read as an object is not the shape the snapshot indexes, or None."""
    if not isinstance(chain.get("conversation_id"), str) or not isinstance(chain.get("seq"), int):
        return "no conversation_id or no integer seq"
    sessions = chain.get("sessions")
    ok = isinstance(sessions, list) and all(
        isinstance(s, dict) and "session_id" in s and isinstance(s.get("snapshot_file"), str)
        and isinstance(s.get("last_line"), int) and isinstance(s.get("boundaries"), list)
        for s in sessions)
    return None if ok else "sessions is not a list of sessions"


def load_chain(conv_dir):
    """(chain, reason): reason is set when chain.json is present but unusable."""
    chain, reason = read_json_object(os.path.join(conv_dir, "chain.json"))
    if chain is not None:
        reason = chain_problem(chain)
        if reason:
            chain = None
    return chain, reason


def find_conversation(root, session_id):
    for path in glob.glob(os.path.join(root.conversations, "*", "chain.json")):
        chain, _ = load_chain(os.path.dirname(path))
        if chain and any(s["session_id"] == session_id for s in chain["sessions"]):
            return chain["conversation_id"]
    return None


def resolve_transcript(root, event):
    tcfg = root.config["transcript"]
    p = event.get(tcfg.get("event_field") or "transcript_path")
    if not p and tcfg.get("glob"):
        cands = [c for c in glob.glob(os.path.expanduser(tcfg["glob"])) if os.path.isfile(c)]
        p = max(cands, key=os.path.getmtime) if cands else None
    if not p or not isinstance(p, str):
        return None
    p = os.path.expanduser(p)
    return p if os.path.isfile(p) else None


def settle(path, tcfg):
    """The transcript is written asynchronously: wait until its size stops changing (bounded)."""
    if not tcfg.get("write_lag"):
        return
    last = -1
    for _ in range(3):
        try:
            size = os.path.getsize(path)
        except OSError:
            return
        if size == last:
            return
        last = size
        time.sleep(int(tcfg.get("settle_ms", 1500)) / 1000.0)


# ----------------------------------------------------------------------------- snapshot
def cmd_snapshot(root, event, quiet=False):
    """L0: byte-exact, append-only copy of the transcript. Returns (exit code, result or None)."""
    tcfg = root.config["transcript"]
    fields = tcfg["fields"]
    path = resolve_transcript(root, event)
    if not path:
        log("transcript not found (event keys: %s)" % sorted(event.keys()))
        return EXIT_INTEGRITY, None
    settle(path, tcfg)
    try:
        with open(path, "rb") as f:
            lines = f.read().split(b"\n")
    except OSError as e:
        log("transcript cannot be read: %s -- no L0 snapshot was taken" % describe_error(e))
        return EXIT_INTEGRITY, None
    lines, dropped = integrity_trim(lines)
    if not lines:
        log("transcript is empty: %s" % path)
        return EXIT_INTEGRITY, None

    session_id = event.get("session_id") or os.path.splitext(os.path.basename(path))[0]
    first_sid = get_path(parse(lines[0]) or {}, fields.get("session_id"))
    parent_sid = first_sid if first_sid and first_sid != session_id else None
    linkage = "parent_id" if parent_sid else ("filename" if first_sid else "unknown")
    conv_id = find_conversation(root, session_id) or (parent_sid and find_conversation(root, parent_sid)) \
        or session_id
    conv_dir = os.path.join(root.conversations, conv_id)
    os.makedirs(conv_dir, exist_ok=True)

    lock = Lock(conv_dir)
    if not lock.acquire():
        log("lock contention on %s" % conv_dir)
        return EXIT_LOCK, None
    try:
        chain, reason = load_chain(conv_dir)  # re-read under the lock: the live chain is the one updated
        if reason is not None:
            kept = "chain.json.unreadable-%s" % utc_compact()
            n = 1
            while os.path.exists(os.path.join(conv_dir, kept)):
                n += 1
                kept = "chain.json.unreadable-%s-%d" % (utc_compact(), n)
            try:
                os.replace(os.path.join(conv_dir, "chain.json"), os.path.join(conv_dir, kept))
            except OSError as e:
                unlinked = "session_transcript_%s_unlinked.jsonl" % utc_compact()
                atomic_write_bytes(os.path.join(conv_dir, unlinked), b"\n".join(lines) + b"\n")
                log("chain.json unusable (%s) and not movable (%s): transcript saved UNLINKED as %s"
                    % (reason, describe_error(e), unlinked))
                return EXIT_INTEGRITY, None
            log("chain.json unusable (%s): kept aside as %s, a new chain starts" % (reason, kept))
        if chain is None:
            chain = new_chain(conv_id, root.config.get("agent"))
        if linkage != "unknown" or chain.get("linkage") == "unknown":
            chain["linkage"] = linkage

        gens = [s for s in chain["sessions"] if s["session_id"] == session_id]
        sess = gens[-1] if gens else None
        fingerprint = hashlib.sha1(lines[0]).hexdigest()[:16]
        effect = "rotate_new_file" if parent_sid else "append_in_place"
        if sess is not None and (len(lines) < sess["last_line"] or sess.get("first_record_fingerprint") != fingerprint):
            log("source rewritten (lines %d->%d): opening generation %d"
                % (sess["last_line"], len(lines), sess.get("generation", 1) + 1))
            effect, sess = "rewrite_in_place", None
        if sess is None:
            snap = None
            while snap is None or os.path.exists(snap):  # an L0 file is never written over
                chain["seq"] += 1
                fname = "session_transcript_%s_%03d.jsonl" % (utc_compact(), chain["seq"])
                snap = os.path.join(conv_dir, fname)
            atomic_write_bytes(snap, b"\n".join(lines) + b"\n")
            sess = {"session_id": session_id, "generation": (gens[-1].get("generation", 1) + 1) if gens else 1,
                    "source_path": path, "snapshot_file": fname, "first_record_fingerprint": fingerprint,
                    "last_line": len(lines), "parent_session_id": parent_sid, "boundaries": [],
                    "seq": chain["seq"], "effect": effect}
            chain["sessions"].append(sess)
            appended = len(lines)
        else:
            snap = os.path.join(conv_dir, sess["snapshot_file"])
            delta = lines[sess["last_line"]:]
            if delta:
                with open(snap, "ab") as f:
                    f.write(b"\n".join(delta) + b"\n")
                    f.flush()
                    os.fsync(f.fileno())
                with open(snap, "rb") as f:
                    check, _ = integrity_trim(f.read().split(b"\n"))
                if len(check) != len(lines):
                    log("append verification mismatch; rewriting the snapshot whole")
                    atomic_write_bytes(snap, b"\n".join(lines) + b"\n")
            sess["last_line"] = len(lines)
            appended = len(delta)
        known = {b["line"] for b in sess["boundaries"]}
        bfield, bvalue = (tcfg.get("boundary") or {}).get("field"), (tcfg.get("boundary") or {}).get("value")
        for i, ln in enumerate(lines, start=1):
            if i in known or bvalue is None or bvalue.encode() not in ln:
                continue
            rec = parse(ln)
            if rec and get_path(rec, bfield) == bvalue:
                meta = rec.get("compactMetadata") or {}
                sess["boundaries"].append({"line": i, "trigger": meta.get("trigger") or event.get("trigger"),
                                           "pre_tokens": meta.get("preTokens"),
                                           "at": get_path(rec, fields.get("timestamp"))})
        last_rec = parse(lines[-1]) or {}
        chain["last"] = {"session_id": session_id, "line": len(lines),
                         "record_id": get_path(last_rec, fields.get("record_id")), "at": utc_iso()}
        atomic_write_bytes(os.path.join(conv_dir, "chain.json"),
                           json.dumps(chain, indent=2, ensure_ascii=False).encode("utf-8"))
    finally:
        lock.release()
    result = {"ok": True, "conversation_id": conv_id, "session_id": session_id, "seq": chain["seq"],
              "snapshot_file": sess["snapshot_file"], "snapshot_path": snap, "generation": sess["generation"],
              "effect": effect, "lines": len(lines), "appended": appended, "dropped_unparsable_tail": dropped,
              "linkage": chain["linkage"]}
    if not quiet:
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    return EXIT_OK, result


# ----------------------------------------------------------------------------- precompact
def build_extension(root, result, event):
    """The text the harness appends to the native compaction prompt. Order (SKILL, mode A light):
    precedence block verbatim -> light instructions -> project custom instructions -> L0 line.
    "" (print nothing, as l0-only) when the mandatory part, the precedence block and the L0 line, cannot
    fit under the cap: a text the harness would cut loses its L0 line, and a cut precedence block is worse
    than none."""
    head = root.read_prompt("precedence-block.txt", PRECEDENCE_FALLBACK).rstrip("\n") + "\n" + LIGHT_INSTRUCTIONS
    if result:
        tail = '- End the summary with this line: "Raw transcript (L0, byte-exact): %s"\n' % result["snapshot_path"]
    else:
        tail = ('- End the summary with this line: "L0 snapshot FAILED; live transcript: %s"\n'
                % (event.get(root.config["transcript"].get("event_field") or "transcript_path") or "unknown"))
    if root.extension_cap <= 0 or len(head) + 1 + len(tail) > root.extension_cap:
        log("the mandatory extension (%d chars) does not fit under the %d cap: printing nothing"
            % (len(head) + 1 + len(tail), max(root.extension_cap, 0)))
        return ""
    custom = root.read_prompt("custom-instructions.md").strip()
    room = root.extension_cap - len(head) - len(tail) - 2
    if custom and len(custom) > room:
        log("custom-instructions.md is %d chars, over the %d left under the %d cap: cut"
            % (len(custom), max(room, 0), root.extension_cap))
        custom = custom[:max(room - 40, 0)].rstrip() + "\n[custom instructions cut at the cap]"
    return head + ("\n" + custom + "\n\n" if custom else "\n") + tail


def cmd_precompact(root, event):
    try:
        code, result = cmd_snapshot(root, event, quiet=True)
    except Exception as e:  # the extension is still printed: the compaction is never held
        log("snapshot fatal: %s" % describe_error(e))
        code, result = EXIT_INTEGRITY, None
    log("precompact snapshot exit=%d %s" % (code, json.dumps(result, ensure_ascii=False) if result else "{}"))
    if root.profile == "l0-only":
        return EXIT_OK  # the runtime cannot take an extension: stdout stays empty
    sys.stdout.write(build_extension(root, result, event))
    sys.stdout.flush()
    return EXIT_OK


# ----------------------------------------------------------------------------- gc
def cmd_gc(root, older_than):
    if not older_than or not older_than.endswith("d") or not older_than[:-1].isdigit():
        raise SystemExit("--older-than must look like 30d")
    cutoff = time.time() - int(older_than[:-1]) * 86400
    removed = []
    for d in sorted(glob.glob(os.path.join(root.conversations, "*"))):
        cp = os.path.join(d, "chain.json")
        if os.path.isfile(cp) and os.path.getmtime(cp) < cutoff:
            shutil.rmtree(d)
            removed.append(os.path.basename(d))
    sys.stdout.write(json.dumps({"removed": removed}) + "\n")
    return EXIT_OK


# ----------------------------------------------------------------------------- selftest
def _rec(sid, n, **extra):
    r = {"type": "user" if n % 2 else "assistant", "sessionId": sid, "uuid": "%s-%d" % (sid, n),
         "timestamp": "2026-01-01T00:00:%02dZ" % (n % 60), "message": {"content": "turn %d → ✓" % n}}
    r.update(extra)
    return json.dumps(r, ensure_ascii=False).encode("utf-8")


def _write(path, recs, tail=b"\n"):
    with open(path, "wb") as f:
        f.write(b"\n".join(recs) + tail)


def cmd_selftest(scratch):
    checks = []

    def check(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    base = tempfile.mkdtemp(prefix="ctxgate-selftest-", dir=scratch)
    try:
        gate = os.path.join(base, "gate")
        os.makedirs(os.path.join(gate, "prompts"))
        with open(os.path.join(gate, "config.json"), "w", encoding="utf-8") as f:
            json.dump({"profile": "light", "agent": {"name": "selftest", "version": "0"},
                       "transcript": {"write_lag": False}}, f)
        with open(os.path.join(gate, "prompts", "custom-instructions.md"), "w", encoding="utf-8") as f:
            f.write("CUSTOM-MARKER keep the lane registry.\n")
        root = Root(gate)
        src = os.path.join(base, "sessA.jsonl")
        recs = [_rec("sessA", i) for i in range(1, 9)]
        _write(src, recs)
        ev = {"session_id": "sessA", "transcript_path": src, "trigger": "manual"}

        code, r = cmd_snapshot(root, ev, quiet=True)
        snap = r and r["snapshot_path"]
        check("fresh snapshot is byte-exact", code == 0 and open(snap, "rb").read() == open(src, "rb").read())

        partial = b"\n".join(recs + [_rec("sessA", 9)]) + b"\n" + b'{"type":"user","sess'
        with open(src, "wb") as f:
            f.write(partial)
        code, r = cmd_snapshot(root, ev, quiet=True)
        check("unparsable tail dropped, delta appended", code == 0 and r["appended"] == 1
              and r["dropped_unparsable_tail"] == 1 and r["snapshot_path"] == snap, json.dumps(r))

        recs = recs + [_rec("sessA", 9), _rec("sessA", 10, subtype="compact_boundary",
                                                compactMetadata={"trigger": "auto", "preTokens": 1234})]
        _write(src, recs)
        code, r = cmd_snapshot(root, ev, quiet=True)
        chain, _ = load_chain(os.path.join(root.conversations, "sessA"))
        b = chain["sessions"][0]["boundaries"]
        check("append keeps one L0 file, byte-exact", code == 0 and r["effect"] == "append_in_place"
              and open(snap, "rb").read() == open(src, "rb").read())
        check("compaction boundary recorded", len(b) == 1 and b[0]["line"] == 10 and b[0]["trigger"] == "auto", str(b))

        old = open(snap, "rb").read()
        _write(src, [_rec("sessA", 100), _rec("sessA", 101)])
        code, r = cmd_snapshot(root, ev, quiet=True)
        check("rewrite opens a new generation, old L0 untouched", code == 0 and r["effect"] == "rewrite_in_place"
              and r["generation"] == 2 and r["snapshot_path"] != snap and open(snap, "rb").read() == old)

        src_b = os.path.join(base, "sessB.jsonl")
        _write(src_b, [_rec("sessA", 101), _rec("sessB", 1), _rec("sessB", 2)])
        code, r = cmd_snapshot(root, {"session_id": "sessB", "transcript_path": src_b}, quiet=True)
        check("rotation joins the parent conversation", code == 0 and r["conversation_id"] == "sessA"
              and r["effect"] == "rotate_new_file" and r["linkage"] == "parent_id", json.dumps(r))

        conv = os.path.join(root.conversations, "sessA")
        lk = Lock(conv)
        lk.acquire()
        code, _ = cmd_snapshot(root, ev, quiet=True)
        lk.release()
        check("lock contention exits 3", code == EXIT_LOCK)
        with open(os.path.join(conv, "work", "lock"), "w") as f:
            f.write('{"pid": 999999, "host": "elsewhere"}')  # a lock file an ended holder left behind
        code, _ = cmd_snapshot(root, ev, quiet=True)
        check("a lock file left by an ended holder never blocks (the OS released its lock)", code == 0)

        code, _ = cmd_snapshot(root, {"session_id": "x", "transcript_path": os.path.join(base, "nope")}, quiet=True)
        check("missing transcript exits 2", code == EXIT_INTEGRITY)

        with open(os.path.join(conv, "chain.json"), "w") as f:
            f.write("[1, 2")
        code, r = cmd_snapshot(root, ev, quiet=True)
        kept = glob.glob(os.path.join(conv, "chain.json.unreadable-*"))
        check("unusable chain kept aside, snapshot still taken", code == 0 and len(kept) == 1 and r["seq"] >= 1)

        block = PRECEDENCE_FALLBACK
        text = build_extension(root, r, ev)
        check("extension opens with the precedence block verbatim", text.startswith(block))
        check("extension order: instructions, custom, L0 line last",
              text.index("next_action") < text.index("CUSTOM-MARKER") < text.index(r["snapshot_path"])
              and text.rstrip("\n").endswith('%s"' % r["snapshot_path"]) and not text.lstrip().startswith("{"))
        text_f = build_extension(root, None, ev)
        check("failed snapshot is said, live path named", "L0 snapshot FAILED; live transcript: %s" % src in text_f)
        with open(os.path.join(gate, "prompts", "custom-instructions.md"), "w", encoding="utf-8") as f:
            f.write("x" * 50000)
        text_c = build_extension(root, r, ev)
        check("extension stays under the harness cap, L0 line kept", len(text_c) <= root.extension_cap
              and text_c.rstrip("\n").endswith('%s"' % r["snapshot_path"]), str(len(text_c)))

        # the cap is read from probe.extension_cap_chars, minus the headroom; the L0 line stays last
        gate3 = os.path.join(base, "gate3")
        os.makedirs(os.path.join(gate3, "prompts"))
        with open(os.path.join(gate3, "config.json"), "w", encoding="utf-8") as f:
            json.dump({"profile": "light", "probe": {"extension_cap_chars": 4000}}, f)
        with open(os.path.join(gate3, "prompts", "custom-instructions.md"), "w", encoding="utf-8") as f:
            f.write("y" * 20000)
        root3 = Root(gate3)
        text_low = build_extension(root3, r, ev)
        check("a low probed cap is honoured, L0 line kept last", root3.extension_cap == 3500
              and len(text_low) <= 3500 and text_low.rstrip("\n").endswith('%s"' % r["snapshot_path"]),
              "%d chars" % len(text_low))
        with open(os.path.join(gate3, "config.json"), "w", encoding="utf-8") as f:
            json.dump({"profile": "light", "probe": {"extension_cap_chars": "many"}}, f)
        check("an unusable cap falls back to the default", Root(gate3).extension_cap
              == DEFAULT_EXTENSION_CAP - EXTENSION_HEADROOM)
        for low in (1500, 400):  # below the mandatory text / at or under the headroom: print nothing, L0 still taken
            with open(os.path.join(gate3, "config.json"), "w", encoding="utf-8") as f:
                json.dump({"profile": "light", "probe": {"extension_cap_chars": low},
                           "transcript": {"write_lag": False}}, f)
            out4 = io.StringIO()
            with contextlib.redirect_stdout(out4):
                code4 = cmd_precompact(Root(gate3), {"session_id": "sessC", "transcript_path": src})
            snaps4 = glob.glob(os.path.join(root3.conversations, "sessC", "session_transcript_*.jsonl"))
            check("cap %d: nothing printed, exit 0, L0 written" % low, code4 == 0 and out4.getvalue() == ""
                  and len(snaps4) == 1 and open(snaps4[0], "rb").read() == open(src, "rb").read(),
                  "%d chars" % len(out4.getvalue()))
            shutil.rmtree(os.path.join(root3.conversations, "sessC"), ignore_errors=True)

        # l0-only profile: the same snapshot, nothing on stdout, always exit 0 (also when the snapshot fails)
        gate2 = os.path.join(base, "gate2")
        os.makedirs(gate2)
        with open(os.path.join(gate2, "config.json"), "w", encoding="utf-8") as f:
            json.dump({"profile": "l0-only", "transcript": {"write_lag": False}}, f)
        root2 = Root(gate2)
        out2 = io.StringIO()
        with contextlib.redirect_stdout(out2):
            code2 = cmd_precompact(root2, {"session_id": "sessA", "transcript_path": src})
        snaps2 = glob.glob(os.path.join(root2.conversations, "sessA", "session_transcript_*.jsonl"))
        check("l0-only: precompact snapshots byte-exact and prints nothing", code2 == 0 and out2.getvalue() == ""
              and len(snaps2) == 1 and open(snaps2[0], "rb").read() == open(src, "rb").read(), out2.getvalue()[:80])
        out3 = io.StringIO()
        with contextlib.redirect_stdout(out3):
            code3 = cmd_precompact(root2, {"session_id": "x", "transcript_path": os.path.join(base, "nope")})
        check("l0-only: failed snapshot still exits 0 and prints nothing", code3 == 0 and out3.getvalue() == "")
        with open(os.path.join(gate2, "config.json"), "w", encoding="utf-8") as f:
            json.dump({"profile": "bogus"}, f)
        check("unknown profile runs as l0-only", Root(gate2).profile == "l0-only")
        os.remove(os.path.join(gate2, "config.json"))
        check("absent config runs as l0-only", Root(gate2).profile == "l0-only")
    except Exception as e:
        check("selftest ran without an exception", False, describe_error(e))
    finally:
        shutil.rmtree(base, ignore_errors=True)
    passed = all(c["ok"] for c in checks) and len(checks) >= 21
    sys.stdout.write(json.dumps({"passed": passed, "checks": checks}, ensure_ascii=False) + "\n")
    return EXIT_OK if passed else EXIT_FAIL


# ----------------------------------------------------------------------------- main
def main(argv=None):
    # stdin, stdout and stderr as UTF-8 whatever the locale (on Windows a console or a pipe defaults to the ANSI code
    # page), stdout and stderr with \n line ends (Windows would write \r\n: the extension would outgrow its probed cap
    # and a POSIX shell would keep each \r); this skill ships apart from BOA's tools, so it cannot share their helper
    # (boa_config.utf8_stdio)
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace", **({} if stream is sys.stdin else {"newline": "\n"}))
    ap = argparse.ArgumentParser(prog="gate_core", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("subcommand", choices=["precompact", "snapshot", "selftest", "gc"])
    ap.add_argument("--root")
    ap.add_argument("--event", help="'-' for stdin or a file with the agent's event JSON")
    ap.add_argument("--older-than")
    ap.add_argument("--scratch", help="selftest: parent dir for its temp dir (default: system temp)")
    a = ap.parse_args(argv)
    if a.subcommand == "selftest":
        return cmd_selftest(a.scratch)
    root = find_root(a.root)
    if a.subcommand == "gc":
        return cmd_gc(root, a.older_than)
    event = read_event(a.event)
    if a.subcommand == "precompact":
        return cmd_precompact(root, event)
    return cmd_snapshot(root, event)[0]


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:  # never a traceback on stdout
        log("fatal: %s" % describe_error(e))
        sys.exit(EXIT_FAIL)
