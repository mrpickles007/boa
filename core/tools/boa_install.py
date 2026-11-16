"""boa install / boa uninstall — install BOA into a project, re-install idempotently, or uninstall exactly.

Needs `<target>/.boa/config.env`. When it is missing, install writes the package's commented template
(`assets/config.env`) there, installs nothing else and exits 1: the agent fills it in (a project-wiring step,
references/project-wiring.md "Config") and runs install again. BOA provides the tools and hooks; the project's agent
wires them into its runtime: this installer writes no runtime directory and no runtime setting. Install, from the
package:
  1. renders every file of `assets/templates/` with render.py and maps it to its project path (`target_of`): agents
     and commands to `.boa/agents/` and `.boa/commands/` (the agent wires them, with BOA's hooks and its runtime's
     instructions and options, in its own runtime's format: references/runtimes.md; no runtime file ships); the
     project's documents (AGENTS.md, the memory bank, the handbook, the lead dir, parity) to their paths; the forge's
     PR/MR template only for BOA_FORGE. CI workflow templates are neither
     rendered nor installed (with the user's consent the agent writes the project's CI itself).
     Render-time keys besides the config: BOA_INSTALL_DATE (UTC ISO-8601 time of the first install: the config's
     BOA_INSTALL_DATE when set, else the manifest's, else the date the project's rendered files already carry, else
     now), BOA_SCRATCH_ABS (BOA_SCRATCH_ROOT without a trailing slash, asserted absolute and >= 2 deep),
     BOA_WT_ABS / BOA_PROJECTS_DIR / BOA_BRANCH_GLOB (checked). Every rendered `*.json` must parse;
  2. copies `core/` to `.boa/` and `stacks/<BOA_STACK>/` to `.boa/stack/` (no `__pycache__`), modes kept;
  3. writes marked blocks: `.gitignore` (`/.boa/*`: tools, hooks, templates, logs and state, all put back by
     `boa install`; except the files the agent writes for the project, which stay versioned: `.boa/config.env`,
     `.boa/protected-commands.conf`, `.boa/memory-types.json`), `.gitattributes` (BOA's files checked out with
     LF on every platform: the launchers and hooks break with CRLF) and `<git-common-dir>/info/exclude` (the lead
     dir, `.lane-resume/`);
  4. records everything in `.boa/installed.list` (the manifest).
Everything that can fail is checked before the first write (rendering, mapping, JSON, markers, path safety, a file
standing where a directory is needed); during the writes each entry is recorded once its write landed, and an
interrupted or failed run still leaves a manifest of everything it touched, so the uninstall removes it. One install
at a time per repository: a lock in the git directory (`boa-install.lock`, there only while BOA is installed: removed
whenever a run ends with no manifest). Known limit: a run that removes the lock while a second waits and a third
starts lets those two overlap (three concurrent runs on a project with nothing installed).
Rules: a project file BOA did not install is never overwritten: AGENTS.md is always BOA's marked block
(`<!-- boa:start -->` … `<!-- boa:end -->`; the whole file when it is created, appended to an existing one), a
project's own 04 gets the residue register as one, a file that equals BOA's own rendering is left alone (not
owned) except on a clone of an installed project (BOA's `.gitignore` block present, no manifest:
`.boa/installed.list` is not versioned), where it is adopted; any other existing file is a conflict: it is kept, the rendered version goes to `.boa/pending/<path>` and the conflict is reported. A
file BOA installed and someone changed since is kept the same way. Re-install updates unchanged installed files,
replaces the blocks and removes installed files the new config no longer produces (unless changed). Nothing is
written through a symlink (no path component of a write may be a symlink).
Uninstall removes exactly what the manifest lists, plus BOA's machine-local directories (machine_dirs: the memory
search environment, the state and log dirs — locks and logs, never project knowledge): unchanged files, the blocks
(restoring the files byte for byte),
the directories it created when empty; changed files are kept and reported unless --force, and so is what BOA's tools
wrote beside the installed files (tool_written: the memory id ledger, the lane journals, the pause flag). The install
seeds the id ledger of a bank that has none (the installed memories' ids, so the memory lint passes at once); the
uninstall removes it while it is still as seeded (its hash is in the manifest). Wiring the
agent added to its runtime is undone by the agent (references/runtimes.md). A manifest with an entry outside the project (absolute,
`..`, `.git/`, a symlinked path) or of a kind not allowed for its path is rejected whole. A manifest written by a
pre-release version (settings-merge or CI entries) is refused the same way: nothing is changed, and its leftovers are
removed by hand. `.boa/config.env` (the project's, filled in by its agent) is kept and reported.

Usage: boa install [--target DIR] [--package DIR] [--dry-run]
       boa uninstall [--target DIR] [--force] [--dry-run]   (= boa install --uninstall ...)
  --target   the project (default: git top level of the current directory)
  --package  the BOA package (default: the package this command runs from; required when run from .boa/)
Exit: 0 done (conflicts are reported, not fatal), 1 error, 2 usage, 130/143 interrupted (manifest written).
Test hooks (honoured only with BOA_TEST_MODE=1; else ignored, said on stderr): BOA_TEST_FAULT_AFTER=N simulates an interruption by a signal (BOA_TEST_FAULT_SIGNAL=TERM|INT, default TERM)
when write N+1 starts (BOA_TEST_FAULT_POINT=start, the default), once its temporary file is written (staged) or right
after it landed (landed).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_config  # noqa: E402  (sibling module; `python -I` leaves the script directory off sys.path)
import boa_paths  # noqa: E402
import memory_embed  # noqa: E402
from boa_lock import FileLock, LockError  # noqa: E402

USAGE = __doc__.split("Usage: ", 1)[1].split("\nExit:", 1)[0]
HERE_PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PENDING_DIR = ".boa/pending"
RESIDUE_TMPL = "residue-register.md"           # embedded in the 04 template; a marked block in a project's own 04
ARCH_REL = "memory-bank/04-ARCHITECTURE.md"
CONFIG_TMPL = "assets/config.env"              # the commented config template, copied (not rendered) when none exists
REQUIRED_KEYS = ("BOA_PROJECT_NAME", "BOA_PROJECT_SLUG", "BOA_MODEL_FRONTIER", "BOA_MODEL_MID", "BOA_PYTHON",
                 "BOA_WT_DIR", "BOA_SCRATCH_ROOT", "BOA_LABEL_KEY")   # the template leaves them empty: the agent decides
BLOCK_FILES = (".gitignore", ".gitattributes", ":exclude", "AGENTS.md", ARCH_REL)
ISO = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
SENTINEL_DATE = "1111-11-11T11:11:11Z"   # rendered in place of the date to find where a template carries it
LEDGER = ".memory-ids.jsonl"             # the memory id ledger in the memory bank (memory_lint.LEDGER)
MEMORY_ID = re.compile(rb"^[ \t]*@@@memory-[0-9]+(?=\s|$)", re.M)   # a memory with an id (memory_lint.HEADER)


def test_hook(name: str, quiet: bool = False) -> str:
    """A test hook's value: honoured only with BOA_TEST_MODE=1 (a stray variable never swaps the pinned spec or
    fakes a signal); otherwise "" and, unless quiet (a second read of the same variable), said on stderr."""
    value = os.environ.get(name, "")
    if value and os.environ.get("BOA_TEST_MODE") != "1":
        if not quiet:
            print(f"install: {name} ignored (test-only: it needs BOA_TEST_MODE=1)", file=sys.stderr)
        return ""
    return value


class Fail(Exception):
    """A refusal: the message is printed as `install: <message>`, exit 1."""


class Interrupted(BaseException):
    def __init__(self, code: int):
        super().__init__(code)
        self.code = code


# the signals that end a run with its manifest written: SIGINT 130, SIGTERM 143, SIGHUP 129 (a closed terminal)
SIGNALS = {s: 128 + int(s) for s in (getattr(signal, n, None) for n in ("SIGINT", "SIGTERM", "SIGHUP")) if s}


def _on_signal(signum, _frame):
    raise Interrupted(128 + signum)


class held:
    """Signals held for a few statements that must happen together (a temporary file created and recorded, a rename
    and its bookkeeping); a signal that lands meanwhile is delivered right after. A no-op where the platform cannot
    hold signals (Windows)."""

    def __enter__(self):
        if hasattr(signal, "pthread_sigmask"):
            signal.pthread_sigmask(signal.SIG_BLOCK, set(SIGNALS))
        return self

    def __exit__(self, *exc):
        if hasattr(signal, "pthread_sigmask"):
            signal.pthread_sigmask(signal.SIG_UNBLOCK, set(SIGNALS))


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: str) -> str:
    with open(p, "rb") as fh:
        return sha_bytes(fh.read())


def lines_of(data: bytes) -> list[bytes]:
    """awk's records: split on \\n, a last line without a newline still a record."""
    if not data:
        return []
    parts = data.split(b"\n")
    return parts[:-1] if data.endswith(b"\n") else parts


def markers(rel: str) -> tuple[bytes, bytes]:
    if rel in (".gitignore", ".gitattributes", ":exclude"):
        return b"# boa:start", b"# boa:end"
    return b"<!-- boa:start -->", b"<!-- boa:end -->"


class Installer:
    def __init__(self, target: str, dry: bool):
        self.target = target
        self.dry = dry
        common = git(target, "rev-parse", "--path-format=absolute", "--git-common-dir")
        if common is None:
            raise Fail(f"cannot read the git directory of {target}")
        self.git_common = common
        self.exclude = os.path.join(common, "info", "exclude")
        self.manifest = os.path.join(target, ".boa", "installed.list")
        self.o_file: dict[str, str] = {}
        self.o_block: dict[str, str] = {}
        self.o_dir: set[str] = set()
        self.o_meta: dict[str, str] = {}
        self.n_file: dict[str, str] = {}
        self.n_block: dict[str, str] = {}
        self.n_dir: set[str] = set()
        self.n_meta: dict[str, str] = {}
        self.planned: dict[str, str] = {}
        self.armed = self.finished = False
        self.writes = 0
        self.live_tmp = ""
        self.warnings = 0
        self.fault_at: int | None = None
        self.fault_point = test_hook("BOA_TEST_FAULT_POINT") or "start"
        self.fault_sig = getattr(signal, "SIG" + (test_hook("BOA_TEST_FAULT_SIGNAL") or "TERM"), None)
        if self.fault_sig not in SIGNALS:
            self.fault_sig = signal.SIGTERM
        raw = test_hook("BOA_TEST_FAULT_AFTER")
        if raw:
            # test hook: simulate an interruption after N writes; only a plain number is honoured
            if re.fullmatch(r"[0-9]{1,6}", raw):
                self.fault_at = int(raw)
            else:
                print("install: BOA_TEST_FAULT_AFTER is not a number: ignored", file=sys.stderr)

    # --- output -----------------------------------------------------------------------------------------------
    @staticmethod
    def say(word: str, text: str) -> None:
        print(f"  {word:<9} {text}", flush=True)

    def warn(self, word: str, text: str) -> None:
        self.warnings += 1
        self.say(word, text)

    # --- paths ------------------------------------------------------------------------------------------------
    def path_of(self, rel: str) -> str:
        return self.exclude if rel == ":exclude" else os.path.join(self.target, *posix_parts(rel))

    @staticmethod
    def safe_rel(r: str) -> bool:
        """A plain relative path inside the work tree (no absolute, empty/./.. segment, .git, control char)."""
        if not r or r.startswith("/") or "\\" in r or re.match(r"[A-Za-z]:", r) \
                or any(ord(c) < 32 or ord(c) == 127 for c in r):
            return False
        segs = r.split("/")
        if any(s in ("", ".", "..") for s in segs):
            return False
        return boa_paths.fold(segs[0]) != ".git"

    def no_link(self, rel: str) -> bool:
        """No existing component of <target>/rel is a symlink (so a write cannot leave the project)."""
        p = self.target
        if os.path.islink(p):
            return False
        for seg in posix_parts(rel):
            p = os.path.join(p, seg)
            if os.path.islink(p):
                return False
            if not os.path.lexists(p):
                return True
        return True

    def blocked(self, rel: str) -> bool:
        """A non-directory stands where a parent directory is needed, or rel itself is a directory."""
        p = self.target
        for seg in posix_parts(rel)[:-1]:
            p = os.path.join(p, seg)
            if os.path.lexists(p) and not os.path.isdir(p):
                return True
        return os.path.isdir(self.path_of(rel))

    def writable(self, rel: str) -> bool:
        return self.safe_rel(rel) and self.no_link(rel) and not self.blocked(rel)

    # --- writes -----------------------------------------------------------------------------------------------
    def fault(self, point: str) -> None:
        if self.fault_at is not None and self.writes > self.fault_at and self.fault_point == point:
            self.fault_at = None
            if os.name != "nt":   # the real signal path (handler -> Interrupted); Windows would end the process
                os.kill(os.getpid(), self.fault_sig)
            raise Interrupted(SIGNALS[self.fault_sig])

    def touched(self) -> None:
        self.armed = True
        self.writes += 1
        self.fault("start")

    def atomic_write(self, dst: str, data: bytes, mode: int | None) -> None:
        """dst replaced by data through a temporary file beside it and a rename (mode: dst's, else the umask's)."""
        with held():
            fd, tmp = tempfile.mkstemp(prefix=".boa-install.", dir=os.path.dirname(dst))
            self.live_tmp = tmp
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        if mode is not None:
            os.chmod(tmp, mode)
        else:
            umask = os.umask(0)
            os.umask(umask)
            os.chmod(tmp, 0o666 & ~umask)
        self.fault("staged")
        with held():
            os.replace(tmp, dst)
            self.live_tmp = ""
        self.fault("landed")

    def mkdirs(self, rel_dir: str) -> None:
        """Create missing directories, recording each before it is created."""
        if rel_dir in ("", "."):
            return
        p = ""
        for seg in rel_dir.split("/"):
            p = f"{p}/{seg}" if p else seg
            if not os.path.isdir(self.path_of(p)):
                self.n_dir.add(p)
                if not self.dry:
                    self.touched()
                    os.mkdir(self.path_of(p))

    def put(self, data: bytes, mode: int, rel: str) -> None:
        if not self.writable(rel):
            raise Fail(f"{rel}: unsafe path (internal error: should have been caught before writing)")
        self.mkdirs(os.path.dirname(rel))
        if self.dry:
            return
        dst = self.path_of(rel)
        if os.path.isfile(dst) and read_bytes(dst) == data and same_x(mode, os.stat(dst).st_mode):
            return
        self.touched()
        self.atomic_write(dst, data, stat.S_IMODE(mode))

    def put_recorded(self, data: bytes, mode: int, rel: str) -> None:
        """put, then record the new checksum once the write landed (an interruption in between is reconciled from
        `planned`: what is on disk decides)."""
        new = sha_bytes(data)
        self.planned[rel] = new
        self.put(data, mode, rel)
        self.n_file[rel] = new

    def remove(self, path: str) -> None:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass

    # --- marked blocks ----------------------------------------------------------------------------------------
    def has_block(self, path: str, start: bytes) -> bool:
        return os.path.isfile(path) and start in lines_of(read_bytes(path))

    def block_flags(self, path: str, start: bytes) -> str:
        """The flags a new block will need (c = file created, n = trailing newline added). A file that holds nothing but
        BOA's block counts as created (a clone's reinstall: the uninstall then removes the file, as on the original)."""
        if self.has_block(path, start):
            lines = lines_of(read_bytes(path))
            end = start.replace(b"start", b"end")
            return "c" if lines and lines[0] == start and lines[-1] == end and lines.count(end) == 1 else ""
        if not os.path.lexists(path):
            return "c"
        data = read_bytes(path)
        return "n" if data and not data.endswith(b"\n") else ""

    def block_upsert(self, path: str, rel: str, content: bytes) -> None:
        start, end = markers(rel)
        if content and not content.endswith(b"\n"):
            content += b"\n"
        body = lines_of(content)
        if self.has_block(path, start):
            lines = lines_of(read_bytes(path))
            if end not in lines[lines.index(start):]:
                raise Fail(f"{path}: {start.decode()} without {end.decode()} after it (fix the file by hand)")
            out, skip = [], False
            for line in lines:
                if line == start:
                    out.append(line)
                    out.extend(body)
                    skip = True
                    continue
                if line == end:
                    skip = False
                if not skip:
                    out.append(line)
            new = b"".join(x + b"\n" for x in out)
            if new != read_bytes(path):   # an unchanged block is not rewritten (a reinstall writes nothing)
                self.atomic_write(path, new, stat.S_IMODE(os.stat(path).st_mode))
        elif not os.path.lexists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.atomic_write(path, start + b"\n" + content + end + b"\n", None)
        else:
            data = read_bytes(path)
            if data and not data.endswith(b"\n"):
                data += b"\n"
            sep = b"\n" if data else b""
            self.atomic_write(path, data + sep + start + b"\n" + content + end + b"\n",
                              stat.S_IMODE(os.stat(path).st_mode))

    def block_remove(self, path: str, rel: str, flags: str) -> None:
        """Remove the block (and the blank line before it), undo the recorded flags."""
        start, end = markers(rel)
        if not self.has_block(path, start):
            return
        lines = lines_of(read_bytes(path))
        st = lines.index(start)
        try:
            en = lines.index(end, st)
        except ValueError:
            return
        frm = st - 1 if st > 0 and lines[st - 1] == b"" else st
        out = lines[:frm] + lines[en + 1:]
        data = b"\n".join(out) + (b"" if "n" in flags or not out else b"\n")
        if "c" in flags and not data:
            self.live_tmp = ""
            os.unlink(path)
        else:
            self.atomic_write(path, data, stat.S_IMODE(os.stat(path).st_mode))

    # --- manifest ---------------------------------------------------------------------------------------------
    def read_manifest(self) -> None:
        """The whole manifest is rejected on the first entry that is not allowed."""
        m = self.manifest
        if not os.path.lexists(m):
            return
        if os.path.islink(m):
            raise Fail(f"{m} is a symlink: manifest rejected")
        text = read_bytes(m).decode("utf-8", "surrogateescape")
        for n, line in enumerate(text.split("\n"), 1):
            if not line:
                continue
            parts = line.split("\t")
            kind, a, b, c = parts[0], *(parts[1:3] + ["", ""])[:2], "\t".join(parts[3:])
            why = ""
            if kind == "file":
                if not re.fullmatch(r"[0-9a-f]{64}", a) or c:
                    why = "bad file entry"
                if not (self.safe_rel(b) and self.no_link(b)):
                    why = "path outside the work tree"
            elif kind == "block":
                if not re.fullmatch(r"[-cn]{1,2}", a) or c:
                    why = "bad block flags"
                if b not in BLOCK_FILES:
                    why = f"no block allowed in {b}"
                elif b != ":exclude" and not self.no_link(b):
                    why = "symlinked block file"
            elif kind == "dir":
                if a != "-" or c:
                    why = "bad dir entry"
                if not (self.safe_rel(b) and self.no_link(b)):
                    why = "path outside the work tree"
            elif kind == "meta":
                if b == "install_date":
                    if not ISO.fullmatch(a) or c:
                        why = "bad install_date"
                elif b == "seeded_ledger":
                    if not re.fullmatch(r"[0-9a-f]{64}", a) or c:
                        why = "bad seeded_ledger"
                else:
                    why = f"unknown meta {b}"
            else:
                why = "unknown entry kind"
            if why:
                raise Fail(f"{m}:{n}: {why}: manifest rejected (nothing changed; fix or remove it by hand)")
            if kind == "file":
                self.o_file[b] = a
            elif kind == "block":
                self.o_block[b] = a.lstrip("-")
            elif kind == "dir":
                self.o_dir.add(b)
            else:
                self.o_meta[b] = a

    def write_manifest(self, union: bool = False) -> None:
        """union = the old entries too, overlaid by the new (an interrupted run)."""
        if union:
            self.n_file = {**self.o_file, **self.n_file}
            self.n_block = {**self.o_block, **self.n_block}
            self.n_dir |= self.o_dir
            self.n_meta = {**self.o_meta, **self.n_meta}
        rows = [("file", v, k) for k, v in self.n_file.items()] + \
               [("block", v or "-", k) for k, v in self.n_block.items()] + \
               [("dir", "-", k) for k in self.n_dir] + [("meta", v, k) for k, v in self.n_meta.items()]
        rows.sort(key=lambda r: (r[0].encode(), r[2].encode("utf-8", "surrogateescape")))
        data = "".join(f"{k}\t{a}\t{p}\n" for k, a, p in rows).encode("utf-8", "surrogateescape")
        os.makedirs(os.path.dirname(self.manifest), exist_ok=True)
        with held():   # never a half-written manifest or a temporary file left by a signal
            fd, tmp = tempfile.mkstemp(prefix="installed.list.", dir=os.path.dirname(self.manifest))
            try:
                with os.fdopen(fd, "wb") as fh:
                    fh.write(data)
                os.chmod(tmp, 0o644)
                os.replace(tmp, self.manifest)
            except BaseException:
                self.remove(tmp)
                raise

    def rmdirs(self) -> None:
        """Remove recorded directories that are empty, deepest first; keep the rest recorded."""
        for d in sorted(self.n_dir, key=lambda x: -x.count("/")):
            p = self.path_of(d)
            if os.path.isdir(p) and not os.path.islink(p):
                if not os.listdir(p):
                    if not self.dry:
                        os.rmdir(p)
                    self.n_dir.discard(d)
            elif not os.path.isdir(p):
                self.n_dir.discard(d)

    def on_exit(self, code: int) -> None:
        if self.live_tmp:
            self.remove(self.live_tmp)
            self.live_tmp = ""
        if self.armed and not self.finished and not self.dry:
            # files planned this run: record each by what is on disk now (the new checksum only if the write landed)
            for rel, new in self.planned.items():
                p = self.path_of(rel)
                if os.path.isfile(p) and sha_file(p) == new:
                    self.n_file[rel] = new
            try:
                self.write_manifest(union=True)
                print(f"install: stopped before the end (exit {code}); {self.manifest} lists everything touched: "
                      "re-run, or run the package's `boa uninstall`", file=sys.stderr)
            except OSError:
                pass

    # --- uninstall --------------------------------------------------------------------------------------------
    def uninstall(self, force: bool) -> int:
        if os.path.islink(os.path.join(self.target, ".boa")):
            raise Fail(f"{self.target}/.boa is a symlink: refusing to work through it")
        if not os.path.isfile(self.manifest):
            raise Fail(f"no manifest ({self.manifest}): nothing installed here, or installed by hand")
        self.read_manifest()
        print(f"install: uninstalling BOA from {self.target}{' (dry run)' if self.dry else ''}")
        kept = False
        for rel in sorted(self.o_file):
            f = self.path_of(rel)
            if not self.no_link(rel):
                self.warn("kept", f"{rel}: behind a symlink; not touched")
                kept = True
            elif not os.path.lexists(f):
                continue
            elif not os.path.isfile(f):
                self.warn("kept", f"{rel}: not a file any more (a directory or another node stands there); not touched")
                kept = True
            elif sha_file(f) != self.o_file[rel]:
                if force:
                    if not self.dry:
                        self.remove(f)
                    self.say("removed", f"{rel} (changed; --force)")
                else:
                    self.warn("kept", f"{rel}: changed since install (remove by hand or use --force)")
                    kept = True
            else:
                if not self.dry:
                    self.remove(f)
                self.say("removed", rel)
        for rel in sorted(self.o_block):
            if rel != ":exclude" and not self.no_link(rel):
                self.warn("kept", f"{rel}: a symlink; block left in place")
                kept = True
                continue
            if not self.dry:
                self.block_remove(self.path_of(rel), rel, self.o_block[rel])
            self.say("unblock", rel)
        for d, what in self.machine_dirs():
            rel = boa_paths.to_slash(os.path.relpath(d, self.target))
            if os.path.islink(d):
                self.warn("kept", f"{rel}: a symlink; not touched")
                kept = True
            elif os.path.isdir(d):
                if not self.dry:
                    shutil.rmtree(d)
                self.say("removed", f"{rel}/ ({what})")
        for rel, what in self.tool_written():
            p = self.path_of(rel)
            if not os.path.lexists(p):
                continue
            if not self.no_link(rel):
                self.warn("kept", f"{rel}: behind a symlink; not touched")
                kept = True
            elif posix_parts(rel)[-1] == LEDGER and os.path.isfile(p) and sha_file(p) == self.o_meta.get("seeded_ledger"):
                if not self.dry:
                    self.remove(p)
                self.say("removed", f"{rel} ({what}, as the install seeded it)")
            elif force:
                if not self.dry and os.path.isdir(p):
                    shutil.rmtree(p)
                elif not self.dry:
                    self.remove(p)
                self.say("removed", f"{rel} ({what}; --force)")
            else:
                self.warn("kept", f"{rel}: {what} (remove by hand or use --force)")
                kept = True
        self.n_dir = set(self.o_dir)
        self.rmdirs()
        if not self.dry:
            self.remove(self.manifest)
        for d in sorted(self.n_dir):
            self.warn("kept", f"{d}/ (not empty)")
        boa = os.path.join(self.target, ".boa")
        # every entry still under .boa/ is the project's own (config.env, protected-commands.conf, ...): named, so
        # "delete by hand" is the whole remaining trace (a dry run names the project-written files it would leave)
        if self.dry:
            left = [n for n in ("config.env", "protected-commands.conf") if os.path.lexists(os.path.join(boa, n))]
        else:
            left = sorted(boa_paths.to_slash(os.path.relpath(os.path.join(d, n), boa))
                          for d, dirs, files in os.walk(boa)
                          for n in files + [x for x in dirs if os.path.islink(os.path.join(d, x))
                                            or not os.listdir(os.path.join(d, x))])   # files, links, empty dirs
        for rel in left:
            if f".boa/{rel}" not in self.o_file:   # an installed file kept (changed, behind a link) was named above
                self.say("kept", f".boa/{rel} (not installed by `boa install`; delete by hand to remove every trace)")
        if not self.dry and os.path.isdir(boa) and not os.listdir(boa):
            os.rmdir(boa)
        print(f"install: uninstall done{', some files kept (see above)' if kept else ''}")
        return 0

    def project_config(self) -> dict:
        """The project's config.env as a dict ({} when it is missing or unreadable: the callers use the defaults)."""
        config = os.path.join(self.target, ".boa", "config.env")
        try:
            return boa_config.parse(read_bytes(config).decode("utf-8"), config)
        except (OSError, UnicodeDecodeError, boa_config.ConfigError):
            return {}

    def tool_written(self) -> list[tuple[str, str]]:
        """What BOA's tools write after the install beside the manifest's files: the memory id ledger next to the
        memory bank, the lead dir's lane journals (the whole lanes/ directory), pause flag and lead-status bookmark.
        Project knowledge: the uninstall keeps them unless --force, like a changed file. A configured dir that is not a
        plain relative path inside the work tree (safe_rel) is left alone."""
        cfg, out = self.project_config(), []
        for key, default, names in (("BOA_MEMORY_DIR", "memory-bank", ((LEDGER, "the memory id ledger"),)),
                                    ("BOA_LEAD_DIR", ".lead", (("lanes", "the lane journals, everything under lanes/"),
                                                               ("PAUSE", "the pause flag"),
                                                               ("lead-status.seen", "the lead-status bookmark")))):
            base = cfg.get(key, default).strip("/")
            if self.safe_rel(base):
                out += [(f"{base}/{name}", what) for name, what in names]
        return out

    def machine_dirs(self) -> list[tuple[str, str]]:
        """BOA's machine-local directories under .boa/, git-ignored and never project knowledge, that the uninstall
        removes whole: the memory search environment (and a stopped build's leftovers), the state dir (locks such as
        memory_write's) and the log dir of the config (defaults when unreadable); a configured dir that is not a plain
        `.boa/<name>`, names what BOA installs, or is or holds the memory bank or the lead dir is left alone."""
        out = [(memory_embed.paths(self.target)["dir"] + x, "the memory search environment")
               for x in ("", ".partial", ".old")]
        cfg = self.project_config()
        installed = {boa_paths.fold(posix_parts(rel)[1]) for rel in self.o_file if rel.startswith(".boa/")}
        # paths folded on both sides: a case-insensitive file system sees .boa/KB and .boa/kb as one directory
        knowledge = [boa_paths.fold(os.path.realpath(os.path.join(self.target, cfg.get(k, d))))
                     for k, d in (("BOA_MEMORY_DIR", "memory-bank"), ("BOA_LEAD_DIR", ".lead"))]
        for key, default in (("BOA_STATE_DIR", ".boa/state"), ("BOA_LOG_DIR", ".boa/logs")):
            m = re.fullmatch(r"\.boa/([A-Za-z0-9_][A-Za-z0-9._-]{0,63})/?", cfg.get(key, default))
            d = os.path.join(self.target, ".boa", m.group(1)) if m else ""
            real = boa_paths.fold(os.path.realpath(d)) if d else ""
            if m and boa_paths.fold(m.group(1)) not in installed | set(boa_paths.FIXED_RESERVED) \
                    and not any(k == real or k.startswith(real + os.sep) for k in knowledge):
                out.append((d, "BOA's machine-local state: locks, logs"))
        return out

    # --- install ----------------------------------------------------------------------------------------------
    def config_template(self, pkg: str, config: str) -> int:
        """No config yet: write the package's commented template there (never through a symlink, never over a
        file), install nothing else, exit 1: the agent fills it in and runs install again."""
        src = os.path.join(pkg, CONFIG_TMPL)
        if not os.path.isfile(src):
            raise Fail(f"no {config} and no template in the package ({src})")
        if self.dry:
            print(f"install: no .boa/config.env: would write it from {CONFIG_TMPL} and stop (dry run)")
            return 1
        boa = os.path.join(self.target, ".boa")
        if not os.path.isdir(boa):
            os.mkdir(boa)
        fd = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
        with os.fdopen(fd, "wb") as fh:
            fh.write(read_bytes(src))
        print("install: wrote .boa/config.env from the package's template and installed nothing else: fill it in "
              "(references/project-wiring.md, \"Config\"), then run `boa install` again", file=sys.stderr)
        return 1

    def install(self, pkg: str, ltarget: str) -> int:
        t = self.target
        if not os.path.isfile(os.path.join(pkg, "core", "bin", "render.py")):
            raise Fail(f"{pkg} is not a BOA package (no core/bin/render.py); pass --package")
        if os.path.islink(os.path.join(t, ".boa")):
            raise Fail(f"{t}/.boa is a symlink: refusing to install through it")
        config = os.path.join(t, ".boa", "config.env")
        if os.path.islink(config) or (os.path.lexists(config) and not os.path.isfile(config)):
            raise Fail(f"{config} is a symlink or not a file: refusing to read it")
        if not os.path.lexists(config):
            return self.config_template(pkg, config)
        render = boa_paths.load_render(os.path.join(pkg, "core"))
        try:
            cfg = render.load_config(config)
        except render.RenderError as exc:
            raise Fail(f"config does not parse: {exc}") from None
        for k in ("BOA_STACK", "BOA_FORGE", "BOA_LEAD_DIR"):
            if k not in cfg:
                raise Fail(f"{config} lacks {k}: add it to .boa/config.env")
        for k in REQUIRED_KEYS:
            if not cfg.get(k, "").strip():
                raise Fail(f"{k} is empty: fill it in .boa/config.env (the comments there say how), then run again")
        stack, forge, lead = cfg["BOA_STACK"], cfg["BOA_FORGE"], cfg["BOA_LEAD_DIR"]
        if not os.path.isdir(os.path.join(pkg, "stacks", stack)):
            raise Fail(f"unknown stack '{stack}': no {pkg}/stacks/{stack}")
        self.read_manifest()
        py = cfg.get("BOA_PYTHON", "")
        if py and not boa_paths.python_ok(py):
            # the hooks call BOA_PYTHON directly: with an interpreter that does not run, no guard runs
            print(f"install: BOA_PYTHON={py} does not run (3.11+, -I -c \"import json\"): the hooks call it, so no guard "
                  "runs until it does; fix it in .boa/config.env", file=sys.stderr)

        date = cfg.pop("BOA_INSTALL_DATE", "").strip()   # empty = unset: the date is then found or computed below
        if date:
            try:
                when = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                when = None
            if when is None or not ISO.fullmatch(date):
                raise Fail(f"BOA_INSTALL_DATE='{date}' is not a real YYYY-MM-DDTHH:MM:SSZ date: fix it in .boa/config.env")
            if when > datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5):
                raise Fail(f"BOA_INSTALL_DATE='{date}' is in the future: fix it in .boa/config.env")
        # the first install's date, never a new one on a reinstall: the config, the manifest, else the date the files
        # already rendered for this project carry (a clone has no manifest: .boa/installed.list is not versioned)
        date = date or self.o_meta.get("install_date") or self.rendered_date(render, cfg, pkg, ltarget, forge, lead)
        self.n_meta["install_date"] = date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        keys = self.render_keys(cfg, ltarget)
        rendered = self.render_templates(render, cfg, pkg, keys)

        # the stage: every project path with its bytes and mode, decided before anything is written
        stage: dict[str, tuple[bytes, int]] = {}
        unmapped = []
        for rel, item in sorted(rendered.items()):
            dsts = target_of(rel, forge, lead)
            if dsts is None:
                unmapped.append(rel)
            for dst in dsts or []:
                stage[dst] = item
        if unmapped:
            raise Fail(f"templates without a project path (add them to target_of): {' '.join(unmapped)}")
        stage.update(tree(os.path.join(pkg, "core"), ".boa"))
        stage.update(tree(os.path.join(pkg, "stacks", stack), ".boa/stack"))
        staged_boa = {posix_parts(rel)[1] for rel in stage if rel.startswith(".boa/")}
        log_dir, state_dir = cfg.get("BOA_LOG_DIR", ".boa/logs"), cfg.get("BOA_STATE_DIR", ".boa/state")
        reserved = {boa_paths.fold(n) for n in staged_boa} | set(boa_paths.FIXED_RESERVED)
        for d in (log_dir, state_dir):
            m = re.fullmatch(r"\.boa/([A-Za-z0-9_][A-Za-z0-9._-]{0,63})", d)
            if not m or boa_paths.fold(m.group(1)) in reserved:
                raise Fail(f"BOA_LOG_DIR / BOA_STATE_DIR must be a new subdirectory of .boa/ (got '{d}'): "
                           "fix it in .boa/config.env")
        # BOA's own files are put back by `boa install`; the files the agent writes for the project stay versioned
        blocks = {".gitignore": "".join(f"{x}\n" for x in ("/.boa/*", "!/.boa/config.env", "!/.boa/protected-commands.conf",
                                                          "!/.boa/memory-types.json")),
                  ".gitattributes": "/.boa/** text eol=lf\n",
                  ":exclude": f"/{lead}/\n/.lane-resume/\n"}

        plan = []
        for rel in sorted(stage):
            data, _mode = stage[rel]
            dst = self.path_of(rel)
            same = os.path.isfile(dst) and read_bytes(dst) == data
            if not self.writable(rel):
                act = "unsafe"
            elif rel in self.o_file:
                if not os.path.lexists(dst) or same or sha_file(dst) == self.o_file[rel]:
                    act = "same" if same else "update"
                else:
                    act = "kept"
            elif rel == "AGENTS.md" and (os.path.isfile(dst) or not os.path.lexists(dst)):
                act = "block"   # always a marked block (also when created): a clone's reinstall replaces it in place
            elif not os.path.lexists(dst):
                act = "create"
            elif same:
                act = "identical"
            elif rel == ARCH_REL and os.path.isfile(dst) and RESIDUE_TMPL in rendered \
                    and (rel in self.o_block or b"<!-- residue-register:begin -->" not in read_bytes(dst)):
                act = "residue"   # the project's own 04: BOA's residue register as a marked block (+ the rendering parked)
            else:
                act = "conflict"
            plan.append((rel, act))
        block_ok = {}
        for rel in blocks:
            f = self.path_of(rel)
            if rel == ":exclude":
                info = os.path.dirname(self.exclude)
                block_ok[rel] = not (os.path.islink(f) or os.path.islink(info)
                                     or (os.path.lexists(f) and not os.path.isfile(f)))
            else:
                block_ok[rel] = self.writable(rel) and not (os.path.lexists(f) and not os.path.isfile(f))
            self.check_markers(rel, f)
        for rel, act in plan:
            if act in ("block", "residue"):
                self.check_markers(rel, self.path_of(rel))

        clone = not self.o_file and self.has_block(self.path_of(".gitignore"), markers(".gitignore")[0])
        # --- apply ---
        print(f"install: BOA into {t}{' (dry run)' if self.dry else ''}", flush=True)
        seen = set()
        for rel, act in plan:
            data, mode = stage[rel]
            seen.add(rel)
            if act in ("same", "update", "create"):
                self.say(act, rel)
                self.put_recorded(data, mode, rel)
            elif act == "kept":
                self.warn("kept", f"{rel}: changed since install; new version in {PENDING_DIR}/{rel}")
                self.n_file[rel] = self.o_file[rel]
                self.park(data, mode, rel)
            elif act == "identical" and clone:
                # a clone of an installed project (BOA's .gitignore block, no manifest: it is not versioned): a file
                # that equals BOA's own rendering is BOA's
                self.n_file[rel] = sha_bytes(data)
                self.say("adopt", f"{rel} (equals BOA's rendering)")
            elif act == "identical":
                self.say("same", f"{rel} (the project's own identical file; not owned)")
            elif act == "conflict":
                self.warn("conflict", f"{rel}: the project's own file is kept; rendered version in {PENDING_DIR}/{rel}")
                self.park(data, mode, rel)
            elif act == "unsafe":
                self.warn("conflict", f"{rel}: a symlink or a file is in the way; rendered version in {PENDING_DIR}/{rel}")
                self.park(data, mode, rel)
            elif act == "block":
                self.add_block(rel, data)
                self.say("block", rel)
            elif act == "residue":
                self.add_block(rel, rendered[RESIDUE_TMPL][0])
                self.warn("block", f"{rel}: the project's own file; BOA's residue register added as a marked block, "
                                   f"the full rendering in {PENDING_DIR}/{rel}")
                self.park(data, mode, rel)
        for rel, content in blocks.items():
            if not block_ok[rel]:
                self.warn("conflict", f"{rel} is a symlink or not a file: add these lines by hand: "
                                      f"{' '.join(content.split())}")
                continue
            self.add_block(rel, content.encode())
            self.say("block", "info/exclude" if rel == ":exclude" else rel)

        # what an earlier install put there and this config no longer produces
        for rel in sorted(self.o_file):
            if rel in self.n_file or rel in seen:
                continue
            f = self.path_of(rel)
            if not self.no_link(rel):
                self.warn("kept", f"{rel}: behind a symlink; not touched")
            elif not os.path.isfile(f):
                continue
            elif sha_file(f) == self.o_file[rel]:
                if not self.dry:
                    self.touched()
                    self.remove(f)
                self.say("remove", f"{rel} (no longer installed)")
            else:
                self.warn("kept", f"{rel}: no longer installed but changed: it is now the project's own file")
        for rel in sorted(self.o_block):
            if rel in self.n_block:
                continue
            if rel != ":exclude" and not self.no_link(rel):
                self.warn("kept", f"{rel}: a symlink; block left in place")
                continue
            if not self.dry:
                self.touched()
                self.block_remove(self.path_of(rel), rel, self.o_block[rel])
            self.say("unblock", rel)
        self.n_dir |= self.o_dir
        self.rmdirs()
        self.seed_ledger()
        if not self.dry:
            self.write_manifest()
        self.finished = True
        embed_ok = self.embed_env(pkg)
        if embed_ok and not self.dry and test_hook("BOA_TEST_EMBED_SPEC", quiet=True) != "off":
            self.warm_vectors()
        tail = f"; resolve conflicts from {PENDING_DIR}, then re-run" if self.warnings else ""
        if not embed_ok:
            print(f"install: incomplete — embedding library not installed (the files are installed, {self.warnings} "
                  "warning(s); see the error above)")
            return 1
        print(f"install: done ({self.warnings} warning(s)){tail}")
        return 0

    def seed_ledger(self) -> None:
        """A bank with no id ledger gets one seeded with the ids of its memories (the installed memory_write.py
        --seed), so the memory lint passes right after the install; its hash is recorded, so an uninstall removes the
        ledger while it is still as seeded. An existing ledger is left alone; a refused seed is a warning."""
        base = self.project_config().get("BOA_MEMORY_DIR", "memory-bank").strip("/")
        rel = f"{base}/{LEDGER}"
        if not self.safe_rel(base) or not self.no_link(rel):
            return
        ledger = self.path_of(rel)
        if os.path.lexists(ledger):
            if os.path.isfile(ledger) and self.o_meta.get("seeded_ledger") == sha_file(ledger):
                self.n_meta["seeded_ledger"] = self.o_meta["seeded_ledger"]
            return
        if not self.bank_has_ids(self.path_of(base)):
            return   # nothing to register (the memory lint asks for a ledger only once a memory carries an id)
        if self.dry:
            self.say("seed", f"{rel} (would seed the memory id ledger)")
            return
        tool = os.path.join(self.target, ".boa", "tools", "memory_write.py")
        # the project's own config only: a BOA_CONFIG or BOA_MEMORY_DIR of the shell would seed another bank
        env = {k: v for k, v in os.environ.items() if k not in ("BOA_CONFIG", "BOA_MEMORY_DIR")}
        ok = self.run([sys.executable, "-I", tool, "--seed", "--root", self.target], env={**env, "BOA_ROOT": self.target})
        if ok is True and not os.path.isfile(ledger):
            ok = "it wrote no ledger"
        if ok is not True:
            self.warn("seed", f"{rel}: not seeded ({ok}); run `python3 -I .boa/tools/memory_write.py --seed`")
        else:
            self.n_meta["seeded_ledger"] = sha_file(ledger)
            self.say("seed", f"{rel} (the memory id ledger, with the ids of the installed memories)")

    @staticmethod
    def bank_has_ids(bank: str) -> bool:
        """A Markdown file of the bank holds a memory with an id (a line starting `@@@memory-<N>`)."""
        for cur, dirs, names in os.walk(bank):
            dirs.sort()
            for n in sorted(names):
                if n.endswith(".md"):
                    try:
                        if MEMORY_ID.search(read_bytes(os.path.join(cur, n))):
                            return True
                    except OSError:
                        continue
        return False

    # --- the memory search environment (memory_embed.py) ------------------------------------------------------
    def embed_env(self, pkg: str) -> bool:
        """Install the embedding library and model of `core/embed.json` into .boa/embed/ (an isolated venv of the
        newest Python in the spec's range, pick_python; never the system Python's packages): built in
        .boa/embed.partial/, checked, then swapped in; a failure removes the partial build, says what is missing and how to fix it, and returns False (exit 1).
        pip installs the pinned library under the spec's constraints; every model file is checked against its sha256
        before the model is loaded. Up to date (same spec, same Python, stamp and files present) = nothing done. Test hooks: BOA_TEST_EMBED_SPEC=off skips
        the step, =FILE uses another spec; BOA_TEST_PIP_FIND_LINKS=DIR installs from DIR only (no package index)."""
        hook = test_hook("BOA_TEST_EMBED_SPEC")
        if hook == "off":
            self.say("skipped", f"{memory_embed.EMBED_DIR}/ (test hook BOA_TEST_EMBED_SPEC=off)")
            return True
        spec_path = hook or os.path.join(pkg, "core", "embed.json")
        env = memory_embed.paths(self.target)
        stage, old = env["dir"] + ".partial", env["dir"] + ".old"
        try:
            raw = read_bytes(spec_path)
            spec = json.loads(raw)
            errs = memory_embed.check_spec(spec)
        except (OSError, ValueError) as exc:
            errs = [str(exc)]
        if errs:
            return self.embed_failed(f"{spec_path}: " + "; ".join(errs), "fix the package (re-download it)", stage)
        what = f"{', '.join(spec['requirements'])} + model {spec['model']['name']} ({spec['model']['repo']}@" \
               f"{spec['model']['revision'][:12]})"
        for d in (env["dir"], stage, old):
            if os.path.islink(d):
                return self.embed_failed(f"{d} is a symlink", "remove it by hand", "")
        if not os.path.lexists(env["dir"]) and os.path.isdir(old):
            # a run stopped between its two renames: the working environment goes back first
            if not self.dry:
                os.replace(old, env["dir"])
            self.say("recovered", f"{memory_embed.EMBED_DIR}/ (from {memory_embed.EMBED_DIR}.old/)")
        lo, hi = memory_embed.python_range(spec)
        picked, seen = pick_python(lo, hi)
        if picked is None:
            return self.embed_failed(
                f"no Python {lo[0]}.{lo[1]} to {hi[0]}.{hi[1]} found (the versions the embedding library ships for; "
                f"found: {', '.join(seen) or 'none'})",
                f"install a Python between {lo[0]}.{lo[1]} and {hi[0]}.{hi[1]} (python.org, or the system's packages), "
                "then re-run `boa install`", "")
        base, version = picked
        key = {"spec_sha": sha_bytes(raw), "python": version, "base": " ".join(base)}
        try:
            with open(env["stamp"], encoding="utf-8") as fh:
                stamp = json.load(fh)
        except (OSError, ValueError):
            stamp = {}
        if isinstance(stamp, dict) and all(stamp.get(k) == v for k, v in key.items()) \
                and os.path.isfile(env["python"]) and model_mismatch(env["model"], spec["model"]["files"]) is None \
                and self.run([env["python"], "-I", os.path.join(pkg, "core", "tools", "memory_embed.py"), "check",
                              env["model"]]) is True:   # the library still imports
            self.say("same", f"{memory_embed.EMBED_DIR}/ (memory search environment: {what})")
            return True
        if self.dry:
            self.say("embed", f"{memory_embed.EMBED_DIR}/ (would install {what})")
            return True
        print(f"install: memory search environment: installing {what} into {memory_embed.EMBED_DIR}/", flush=True)
        part = memory_embed.layout(stage)
        swapped = False
        try:
            for d in (stage, old):   # leftovers of an earlier run that stopped half-way
                shutil.rmtree(d, ignore_errors=True)
                if os.path.lexists(d):
                    return self.embed_failed(f"{d} is left from an earlier run and cannot be removed",
                                             f"remove {d} by hand, then re-run `boa install`", "")
            os.makedirs(stage)
            fix = "re-run `boa install`"
            r = self.run(base + ["-m", "venv", part["venv"]])
            if r is not True:
                return self.embed_failed(f"`{' '.join(base)} -m venv` failed: {r}",
                                         "install the venv module (with ensurepip) for this Python — it ships with "
                                         "the python.org builds, some systems package it separately — then " + fix, stage)
            constraints = os.path.join(stage, "constraints.txt")
            with open(constraints, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("".join(f"{c}\n" for c in spec["constraints"]))
            pip = [part["python"], "-I", "-m", "pip", "install", "--no-cache-dir", "--disable-pip-version-check",
                   "--no-input", "--only-binary=:all:", "-c", constraints]
            links = test_hook("BOA_TEST_PIP_FIND_LINKS")
            if links:
                pip += ["--no-index", "--find-links", links]
            r = self.run(pip + list(spec["requirements"]))
            if r is not True:
                return self.embed_failed(f"pip could not install {', '.join(spec['requirements'])}: {r}",
                                         "check the network access to the package index (or set PIP_INDEX_URL to a "
                                         "reachable mirror), then " + fix, stage)
            tool = os.path.join(pkg, "core", "tools", "memory_embed.py")
            hub = {**os.environ, "HF_HOME": os.path.join(stage, "hf-home"), "HF_HUB_DISABLE_TELEMETRY": "1"}
            r = self.run([part["python"], "-I", tool, "fetch", spec_path, part["model"]], hub)
            if r is not True:
                return self.embed_failed(f"the model {spec['model']['repo']}@{spec['model']['revision'][:12]} could "
                                         f"not be downloaded: {r}",
                                         "check the network access to the model hub, then " + fix, stage)
            bad = model_mismatch(part["model"], spec["model"]["files"])
            if bad:
                return self.embed_failed(f"the model file {bad[0]} does not match its pinned sha256 (got {bad[1]})",
                                             "check what serves the model hub on this network (a proxy or mirror "
                                             "rewriting files), then " + fix, stage)
            r = self.run([part["python"], "-I", tool, "probe", spec["model"]["name"], part["model"]], hub)
            if r is not True:
                return self.embed_failed(f"the model {spec['model']['name']} does not load: {r}", fix, stage)
            for junk in (os.path.join(stage, "hf-home"), os.path.join(part["model"], ".cache"), constraints):
                if os.path.isdir(junk):
                    shutil.rmtree(junk, ignore_errors=True)
                elif os.path.isfile(junk):
                    os.unlink(junk)
            frozen = subprocess.run([part["python"], "-I", "-m", "pip", "freeze", "--disable-pip-version-check"],
                                    capture_output=True, text=True, errors="replace", timeout=120).stdout.split()
            with open(part["stamp"], "w", encoding="utf-8", newline="\n") as fh:
                json.dump({**key, "requirements": spec["requirements"], "model": spec["model"], "installed": frozen},
                          fh, indent=1)
                fh.write("\n")
            with held():
                if os.path.lexists(env["dir"]):
                    os.replace(env["dir"], old)
                try:
                    os.replace(stage, env["dir"])
                except OSError:
                    if os.path.lexists(old):
                        os.replace(old, env["dir"])   # the working environment back in place
                    raise
                swapped = True
            shutil.rmtree(old, ignore_errors=True)
        except (OSError, subprocess.SubprocessError) as exc:
            return self.embed_failed(str(exc), "re-run `boa install`", "" if swapped else stage)
        finally:
            if not swapped:
                shutil.rmtree(stage, ignore_errors=True)
        self.say("embed", f"{memory_embed.EMBED_DIR}/ (memory search environment: {what}; checked)")
        return True

    def warm_vectors(self) -> None:
        """Cache the memory search vector of every memory of the bank once (the installed memory_search.py --warm, in
        chunks, no time budget), so queries never pay the cold start; best effort: a failure is a warning only."""
        tool = os.path.join(self.target, ".boa", "tools", "memory_search.py")
        try:
            r = subprocess.run([sys.executable, "-I", tool, "--warm"], cwd=self.target, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, errors="replace", timeout=3600,
                               env={**os.environ, "BOA_ROOT": self.target})
            line = ([x for x in r.stdout.splitlines() if x.startswith("memory-search: ")] or [""])[-1]
            why = line[len("memory-search: "):] or (r.stderr.strip().splitlines() or [f"exit {r.returncode}"])[-1]
        except (OSError, subprocess.SubprocessError) as exc:
            why = str(exc)
        done = why.startswith("memory search vectors: ") and why.endswith(", 0 still missing")
        self.say("warm", why if done else f"{why[:300]} (best effort: memory search fills the rest at query time)")

    @staticmethod
    def run(cmd: list[str], env: dict[str, str] | None = None) -> bool | str:
        """True when `cmd` exits 0, else its last error line (or why it did not start)."""
        try:
            r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace",
                               timeout=900, env=env)
        except subprocess.TimeoutExpired:
            return "timed out after 900s"
        except OSError as exc:
            return f"did not start ({exc})"
        if r.returncode == 0:
            return True
        lines = [x.strip() for x in (r.stderr + "\n" + r.stdout).splitlines() if x.strip()]
        return f"exit {r.returncode}: {(lines or ['no message'])[-1][:300]}"

    @staticmethod
    def embed_failed(why: str, fix: str, stage: str) -> bool:
        if stage:
            shutil.rmtree(stage, ignore_errors=True)
        print(f"install: the memory search environment is NOT installed: {why}", file=sys.stderr)
        print(f"install: to fix: {fix}. Until then memory search ranks by BM25 alone and warns. Nothing half-installed "
              "was left; ask the user before changing anything on this machine.", file=sys.stderr)
        return False

    def check_markers(self, rel: str, path: str) -> None:
        """A block start must have its end AFTER it (an end before the start would let a rewrite drop the rest)."""
        start, end = markers(rel)
        lines = lines_of(read_bytes(path)) if os.path.isfile(path) else []
        if start in lines and end not in lines[lines.index(start):]:
            raise Fail(f"{path}: {start.decode()} without {end.decode()} after it (fix the file by hand): nothing installed")

    def add_block(self, rel: str, content: bytes) -> None:
        start, _ = markers(rel)
        path = self.path_of(rel)
        self.n_block[rel] = self.o_block[rel] if rel in self.o_block else self.block_flags(path, start)
        if not self.dry:
            self.touched()
            self.block_upsert(path, rel, content)

    def park(self, data: bytes, mode: int, rel: str) -> None:
        """The rendered version of a file BOA may not write goes to .boa/pending/<rel>."""
        if not self.writable(f"{PENDING_DIR}/{rel}"):
            self.warn("skipped", f"{PENDING_DIR}/{rel}: unsafe path; rendered version not parked")
            return
        self.put_recorded(data, mode, f"{PENDING_DIR}/{rel}")

    def rendered_date(self, render, cfg, pkg, ltarget, forge, lead) -> str | None:
        """The install date the project's files already carry: each template that holds the date is rendered with a
        sentinel, and a target file that equals the rendering up to the sentinel gives the date found there."""
        self.n_meta["install_date"] = SENTINEL_DATE
        for rel, (data, _mode) in sorted(self.render_templates(render, cfg, pkg, self.render_keys(cfg, ltarget)).items()):
            text = data.decode("utf-8", "replace")
            i = text.find(SENTINEL_DATE)
            for dst in (target_of(rel, forge, lead) or []) if i >= 0 else []:
                p = self.path_of(dst)
                if os.path.isfile(p) and not os.path.islink(p):
                    cur = read_bytes(p).decode("utf-8", "replace")
                    if cur.startswith(text[:i]) and ISO.fullmatch(cur[i:i + 20]):
                        return cur[i:i + 20]
        return None

    def render_keys(self, cfg: dict[str, str], ltarget: str) -> dict[str, str]:
        """The render-time keys (logical paths), each checked."""
        scratch = cfg.get("BOA_SCRATCH_ROOT", "").rstrip("/")
        if not boa_paths.is_abs(scratch, 2):
            raise Fail(f"BOA_SCRATCH_ROOT='{cfg.get('BOA_SCRATCH_ROOT', '')}' is not an absolute path at least two "
                       "levels deep: fix it in .boa/config.env")
        wt = cfg.get("BOA_WT_DIR", "")
        if wt.startswith("/") or (boa_paths.WINDOWS and re.match(r"[A-Za-z]:/", wt)):
            wt_abs = wt.rstrip("/")
        else:
            wt_abs = (posix_dirname(ltarget) + "/" + (wt[3:] if wt.startswith("../") else wt)).rstrip("/")
        why = boa_paths.wt_problem(wt_abs, self.target)
        if why:
            raise Fail(f"BOA_WT_DIR='{wt}' gives '{wt_abs}': {why}: fix it in .boa/config.env")
        projects = posix_dirname(ltarget)
        if not (projects.startswith("/") or re.match(r"[A-Za-z]:/", projects)):
            raise Fail(f"cannot derive the projects directory of {self.target}")
        glob = cfg.get("BOA_BRANCH_GRAMMAR", "")
        for tok in ("<ms>", "<task>", "<slug>"):
            glob = glob.replace(tok, "*")
        import fnmatch
        if not glob.replace("*", "") or "<" in glob or ">" in glob \
                or fnmatch.fnmatchcase(cfg.get("BOA_MAIN_BRANCH", "main"), glob):
            raise Fail(f"BOA_BRANCH_GRAMMAR gives the branch glob '{glob}', which is empty or matches the main "
                       "branch: fix it in .boa/config.env")
        date = self.n_meta["install_date"]
        keys = {"BOA_INSTALL_DATE": date, "BOA_SCRATCH_ABS": scratch, "BOA_WT_ABS": wt_abs,
                "BOA_PROJECTS_DIR": projects, "BOA_BRANCH_GLOB": glob}
        return keys

    def render_templates(self, render, cfg, pkg, keys) -> dict[str, tuple[bytes, int]]:
        """Every template, rendered by render.py: rel -> (bytes, mode); every rendered `*.json` must parse. No CI file
        ships, so one planted in the templates is unmapped and refused."""
        base = os.path.join(pkg, "assets", "templates")
        clash = sorted(set(keys) & set(cfg))
        if clash:
            raise Fail("template rendering failed: nothing installed\nrender: --set may not redefine config keys: "
                       + ", ".join(clash))
        if not os.path.isdir(base):
            return {}
        try:
            files = render.render_files(base, {**cfg, **keys})
        except render.RenderError as exc:
            raise Fail("template rendering failed: nothing installed\nrender: "
                       + str(exc).replace("\n", "\nrender: ")) from None
        out, bad_json = {}, []
        for src, rel, text in files:
            if rel.endswith(".json"):
                try:
                    json.loads(text)
                except ValueError as exc:
                    bad_json.append(f"{rel}: {exc}")
            out[rel] = (text.encode("utf-8"), os.stat(src).st_mode)
        if bad_json:
            raise Fail(f"rendered JSON templates do not parse (nothing installed): {'; '.join(bad_json)}")
        return out


def pick_python(lo: tuple[int, int], hi: tuple[int, int]) -> tuple[tuple[list[str], str] | None, list[str]]:
    """The newest Python from `lo` to `hi` (inclusive) on this machine — the one running the install, then
    python3.<minor> on PATH, then `py -3.<minor>` on Windows — as (command, "3.N"), and what was found."""
    cands = [[sys.executable]]
    for minor in range(hi[1], lo[1] - 1, -1):
        found = shutil.which(f"python{hi[0]}.{minor}")
        if found:
            cands.append([found])
        if os.name == "nt" and shutil.which("py"):
            cands.append(["py", f"-{hi[0]}.{minor}"])
    best: tuple[list[str], str] | None = None
    best_v = (0, 0)
    seen: list[str] = []
    for c in cands:
        try:
            r = subprocess.run(c + ["-I", "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                               stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace", timeout=15)
        except (OSError, subprocess.SubprocessError):
            continue
        m = re.fullmatch(r"(\d+)\.(\d+)", r.stdout.strip()) if r.returncode == 0 else None
        if not m:
            continue
        v = (int(m.group(1)), int(m.group(2)))
        seen.append(f"{v[0]}.{v[1]} ({' '.join(c)})")
        if lo <= v <= hi and v > best_v:
            best, best_v = (c, f"{v[0]}.{v[1]}"), v
    return best, seen


def model_mismatch(model_dir: str, files: dict[str, str]) -> tuple[str, str] | None:
    """The first model file whose sha256 (streamed: the model is large) is not the pinned one, with what it is."""
    for name, want in sorted(files.items()):
        f = os.path.join(model_dir, name)
        try:
            with open(f, "rb") as fh:
                got = hashlib.file_digest(fh, "sha256").hexdigest()
        except OSError:
            got = "missing"
        if got != want:
            return name, got
    return None


def target_of(rel: str, forge: str, lead: str) -> list[str] | None:
    """The project paths of a template ([] = not for this config); None = unmapped. Agents and commands stay under
    `.boa/`: the agent wires them in its runtime's format."""
    if rel == "AGENTS.md" or rel.startswith("memory-bank/"):
        return [rel]
    if rel == "agent-handbook.md":
        return ["docs/agent-handbook.md"]
    if rel.startswith(("agents/", "commands/")):
        return [f".boa/{rel}"]
    if rel.startswith("lead/"):
        return [f"{lead}/{rel[5:]}"]
    if rel == "forge/github/pull_request_template.md":
        return [".github/pull_request_template.md"] if forge == "github" else []
    if rel == "forge/gitlab/merge_request_template.md":
        return [".gitlab/merge_request_templates/Default.md"] if forge == "gitlab" else []
    if rel == RESIDUE_TMPL:
        return []   # consumed: the 04 residue register
    if rel.startswith("parity/"):
        return [f"docs/parity/{rel[7:]}"]
    return None


def tree(src: str, prefix: str) -> dict[str, tuple[bytes, int]]:
    """Every file under src (no __pycache__) as prefix/<rel> -> (bytes, mode)."""
    out = {}
    for root, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            p = os.path.join(root, name)
            out[prefix + "/" + boa_paths.to_slash(os.path.relpath(p, src))] = (read_bytes(p), os.stat(p).st_mode)
    return out


def read_bytes(p: str) -> bytes:
    with open(p, "rb") as fh:
        return fh.read()


def same_x(a: int, b: int) -> bool:
    return bool(a & stat.S_IXUSR) == bool(b & stat.S_IXUSR)


def posix_dirname(p: str) -> str:
    return p.rsplit("/", 1)[0] or "/"


def posix_parts(rel: str) -> tuple[str, ...]:
    """The components of a path written with `/` (the manifest, the package tree), on every OS."""
    return pathlib.PurePosixPath(rel).parts


def git(cwd: str, *args: str) -> str | None:
    import subprocess
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=30,
                           stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def resolve_target(given: str) -> tuple[str, str]:
    """(physical git top level, logical top level as the user sees it: symlinked parents kept)."""
    top = git(given, "rev-parse", "--show-toplevel")
    if not top:
        raise Fail(f"not inside a git work tree: {given}")
    target = boa_paths.to_slash(os.path.realpath(top))
    if os.path.isabs(given):
        given_l = os.path.normpath(given)
    else:   # relative to the directory as the user sees it ($PWD, symlinks kept), like `cd DIR && pwd -L`
        pwd, cwd = os.environ.get("PWD", ""), os.getcwd()
        try:
            base = pwd if pwd and os.path.isabs(pwd) and os.path.samefile(pwd, cwd) else cwd
        except OSError:
            base = cwd
        given_l = os.path.normpath(os.path.join(base, given))
    given_l = boa_paths.to_slash(given_l)
    given_p = boa_paths.to_slash(os.path.realpath(given))
    sub = given_p[len(target):] if given_p == target or given_p.startswith(target + "/") else None
    if sub is not None and given_l.endswith(sub):
        return target, given_l[:len(given_l) - len(sub)] if sub else given_l
    return target, target


def main(argv: list[str]) -> int:
    def usage() -> int:
        print("usage: " + USAGE, file=sys.stderr, end="")
        return 2
    target = pkg = ""
    dry = uninstall = force = False
    args = list(argv)
    while args:
        a = args.pop(0)
        if a in ("--target", "--package"):
            if not args:
                return usage()
            if a == "--target":
                target = args.pop(0)
            else:
                pkg = args.pop(0)
        elif a == "--dry-run":
            dry = True
        elif a == "--uninstall":
            uninstall = True
        elif a == "--force":
            force = True
        else:
            return usage()
    if force and not uninstall:
        return usage()
    old = {s: signal.signal(s, _on_signal) for s in SIGNALS}
    code = 1
    try:
        top, ltop = resolve_target(target or ".")
        inst = Installer(top, dry)
        lock = os.path.join(inst.git_common, "boa-install.lock")
        drop = False   # the lock file still to remove once released (Windows cannot delete an open file)
        with FileLock(lock, timeout=30):
            try:
                if uninstall:
                    code = inst.uninstall(force)
                else:
                    package = pkg or HERE_PKG
                    if not os.path.isdir(package):
                        raise Fail("package directory not found")
                    code = inst.install(boa_paths.to_slash(os.path.realpath(package)), ltop)
            except (Fail, OSError) as exc:
                print(f"install: {exc}", file=sys.stderr)
                code = 1
            except Interrupted as exc:
                code = exc.code
            finally:
                for s in old:
                    signal.signal(s, signal.SIG_IGN)   # a second signal must not cut the manifest write short
                inst.on_exit(code)
                if not os.path.lexists(inst.manifest):
                    # nothing installed (uninstalled, a dry or failed first run): no trace left in the git directory;
                    # removed while held, so a waiting run sees the lock file gone and opens a new one (boa_lock)
                    try:
                        os.unlink(lock)
                    except OSError:
                        drop = True   # Windows: still open; removed just below, once released
        if drop:
            try:
                os.unlink(lock)
            except OSError:
                pass   # another run opened it meanwhile: it is that run's lock now
    except (Fail, LockError, OSError) as exc:
        print(f"install: {exc}", file=sys.stderr)
        code = 1
    except Interrupted as exc:
        code = exc.code
    finally:
        for s, h in old.items():
            signal.signal(s, h)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
