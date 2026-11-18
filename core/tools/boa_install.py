"""boa install / boa uninstall — install BOA into a project, re-install idempotently, or uninstall exactly.

Needs `<target>/.boa/config.env`. When it is missing, install writes the package's commented template
(`assets/config.env`) there, installs nothing else and exits 1: the agent fills it in (a project-wiring step,
references/project-wiring.md "Config") and runs install again. BOA provides the tools and hooks; the project's agent
wires them into its runtime: this installer writes no runtime directory and no runtime setting. Install, from the
package:
  1. renders every file of `assets/templates/` with render.py and maps it to its project path (`target_of`): agents
     and commands to `.boa/agents/` and `.boa/commands/` (the agent wires them, with BOA's hooks and its runtime's
     instructions and options, in its own runtime's format: references/runtimes.md; no runtime file ships); the
     project's documents (AGENTS.md, the memory bank, the handbook, the lead dir, parity) to their paths, the notice
     (the attribution of BOA's texts, CC BY 4.0, and MIT files; the AGPL tool copies named; the project's own
     config and content are not BOA's) to docs/boa-notice.md, a versioned path (an ignore rule hiding it is warned); the forge's PR/MR template only for
     BOA_FORGE. CI workflow templates are neither
     rendered nor installed (with the user's consent the agent writes the project's CI itself).
     Render-time keys besides the config: BOA_INSTALL_DATE (UTC ISO-8601 time of the first install: the config's
     BOA_INSTALL_DATE when set, else the manifest's, else the date the project's rendered files already carry, else
     now), BOA_SCRATCH_ABS (BOA_SCRATCH_ROOT without a trailing slash, asserted absolute and >= 2 deep),
     BOA_WT_ABS / BOA_PROJECTS_DIR / BOA_BRANCH_GLOB (checked). Every rendered `*.json` must parse;
  2. copies `core/` to `.boa/` and `stacks/<BOA_STACK>/` to `.boa/stack/` (no `__pycache__`), modes kept;
  3. writes marked blocks: `.gitignore` (`/.boa/*`: tools, hooks, templates, logs and state, all put back by
     `boa install`; except the files the agent writes for the project, which stay versioned: `.boa/config.env`,
     `.boa/protected-commands.conf`, `.boa/memory-types.json`, `.boa/markers.json` (the marker words: `boa language
     set`, plan column aliases) and the stack plug-in `.boa/stack/` the agent adapts),
     `.gitattributes` (BOA's files checked out with
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
(`<!-- boa:start -->` … `<!-- boa:end -->`; the whole file when it is created, appended to an existing one): with
BOA_AGENTS_BLOCK=full (the default) the block holds BOA's rules; with pointer it holds the short pointer of
`AGENTS-pointer.md`, and BOA's rules are the file docs/boa-rules.md (their relative links moved one level up);
switching the key on a reinstall replaces the block in place and installs or removes docs/boa-rules.md (a changed
one is kept). AGENTS.md's block is rewritten only while it is as BOA last wrote it (its sha256 is the manifest's
`agents_block` meta): a block changed since, or one with no such record (an older release's manifest, a clone), is
kept, reported `kept`, the new block parked in `.boa/pending/AGENTS.md`; the uninstall keeps it too, unless --force.
A versioned file of the stack plug-in (`.boa/stack/`), a `.boa/memory-types.json` or a `.boa/markers.json` that BOA
did not install is the project's adapted copy: kept, the package's version parked, never overwritten. A kept
memory-types.json or markers.json (adapted, or changed since install) gets the entries the package has and its
merge base had not (merge_json: a type by its name, a recall moment by its id, a keyword route by its keyword and
type, a marker by its key; one `merge` line each), the project's entries never changed or removed, so one it deleted,
renamed or narrowed never comes back. The merge base is the package version last installed or merged, kept as an
installed file in `.boa/merge-base/`; with none recorded (an older release's install, a fresh clone) nothing is
merged, the package's version is parked and becomes the base; a file that does not parse, has another
schema or would no longer validate is left as it is, said. A project's own lead file a hook writes later
(RESUME-LEAD.md, open-items.md) is a conflict with a second warning naming the hook. A
project's own 04 gets the residue register as a marked block (the rows agents wrote into its table carried into the
new block, in order; its text outside the rows hashed as the `residue_block` meta and kept like AGENTS.md's block
when changed or unrecorded; the uninstall keeps a block holding agent rows unless --force: the template's own
rows, recorded as the `residue_rows` meta, do not count; on a clone, whose 04 holds
BOA's block and no manifest, the same), a file that equals BOA's own rendering is left alone (not
owned) except on a clone of an installed project (BOA's `.gitignore` block present, no manifest:
`.boa/installed.list` is not versioned), where it is adopted; any other existing file is a conflict: it is kept, the rendered version goes to `.boa/pending/<path>` and the conflict is reported. A
file BOA installed and someone changed since is kept the same way. Re-install updates unchanged installed files,
replaces the blocks and removes installed files the new config no longer produces (unless changed). Nothing is
written through a symlink (no path component of a write may be a symlink).
Uninstall removes exactly what the manifest lists, plus BOA's machine-local directories (machine_dirs: the memory
search environment, the state and log dirs — locks and logs, never project knowledge): unchanged files, the blocks
(restoring the files byte for byte),
the directories it created when empty; changed files are kept and reported unless --force, and so is what BOA's tools
wrote beside the installed files (tool_written: the memory id ledger, the lane journals, the pause flag). The notice
docs/boa-notice.md (the attribution of BOA's texts and MIT files) is kept, and said with what it covers, while any of
them stays: an installed file kept (BOA's AGPL tool copies aside), AGENTS.md's or the 04's block kept, or a
project-adapted copy of a plug-in file BOA shipped, of markers.json or of memory-types.json. The install
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
import markers as boa_markers  # noqa: E402  (the validator and layout of the markers file)
import boa_tool  # noqa: E402
import memory_embed  # noqa: E402
import memory_lint  # noqa: E402
import memory_types  # noqa: E402
from boa_lock import FileLock, LockError  # noqa: E402

USAGE = __doc__.split("Usage: ", 1)[1].split("\nExit:", 1)[0]
HERE_PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PENDING_DIR = ".boa/pending"
RESIDUE_TMPL = "residue-register.md"           # embedded in the 04 template; a marked block in a project's own 04
ARCH_REL = "memory-bank/04-ARCHITECTURE.md"
CONFIG_TMPL = "assets/config.env"              # the commented config template, copied (not rendered) when none exists
POINTER_TMPL = "AGENTS-pointer.md"             # BOA_AGENTS_BLOCK=pointer: AGENTS.md's short block pointing to RULES_REL
RULES_REL = "docs/boa-rules.md"                # BOA_AGENTS_BLOCK=pointer: BOA's rendered AGENTS.md, a file of its own
NOTICE_TMPL = "boa-notice.md"                  # the attribution of BOA's files in the project (credit, licences, MIT text)
NOTICE_REL = "docs/boa-notice.md"
AGPL_COPIES = (".boa/bin/", ".boa/tools/", ".boa/hooks/", ".boa/embed.json")   # BOA's own tools: not under the notice
AGENTS_BLOCK_MODES = ("full", "pointer")
STACK_DIR = ".boa/stack"                       # the stack plug-in: the project adapts it, so it is versioned
MARKERS_REL = ".boa/markers.json"              # the project's marker words (`boa language set`, plan column aliases)
TYPES_REL = ".boa/memory-types.json"           # the project's memory types (memory_types.py)
# the files under .boa/ the project keeps versioned (exceptions of the .gitignore block), besides the stack plug-in
PROJECT_FILES = (".boa/config.env", ".boa/protected-commands.conf", TYPES_REL, MARKERS_REL)
# the project's JSON files an install adds the package's new entries to (merge_json): never a project value changed
MERGED_JSON = (TYPES_REL, MARKERS_REL)
# the merge base of each: a copy of the package version last merged into (or installed as) the project's file, an
# installed file of its own (its sha256 in the manifest is the record; a copy that no longer has it counts as none)
MERGE_BASE_DIR = ".boa/merge-base"
# manifest meta per block a project writes in: the sha256 of the block as BOA last wrote it (the residue register's
# without the rows agents add to its table: owned_text)
BLOCK_META = {"AGENTS.md": "agents_block", ARCH_REL: "residue_block"}
# manifest meta: the sha256 of the rows the release's register template ships itself (block_lines of them), so the
# uninstall tells them from the rows agents wrote (agent_rows)
ROWS_META = "residue_rows"
# what to do with what an uninstall keeps: this run removes the manifest, so a later --force finds nothing to act on
FORCE_ADVICE = (" (kept: remove it by hand; to have the uninstall remove such files, run `boa uninstall --dry-run` "
                "first and decide on --force before the real run)")
TABLE_RULE = re.compile(rb"^\|\s*:?-{3,}")   # a Markdown table's separator line (`|----|...`)
# the lead files a hook writes after the install: a project's own file kept there will be written by that hook
LEAD_HOOK_FILES = {"RESUME-LEAD.md": "the lead stop hook writes its marked status block into it at every pause "
                                     "(the rest of the file is kept)",
                   "open-items.md": "the sub-agent stop hook appends the reports' Leftovers lines to it"}
# the variables that point git at another repository, work tree or object store: removed for the throwaway repository
THROWAWAY_UNSET = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
                   "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_CEILING_DIRECTORIES",
                   "GIT_DISCOVERY_ACROSS_FILESYSTEM", "GIT_PREFIX", "GIT_SHALLOW_FILE", "GIT_REPLACE_REF_BASE",
                   "GIT_GRAFT_FILE")
LINK = re.compile(rb"\]\((?![A-Za-z][A-Za-z0-9+.-]*:|#|/)")   # a Markdown link to a path relative to its file
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


def replaceable(path: str) -> None:
    """Fail when `path` exists and is not a regular file: a rename onto it would replace it (boa_tool's check)."""
    try:
        boa_tool.check_replaceable(path)
    except boa_tool.NotRegularFile as exc:
        raise Fail(str(exc)) from exc


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


BOM = b"\xef\xbb\xbf"


def bare(line: bytes) -> bytes:
    """A line as a marker is compared: without a leading byte order mark and a trailing carriage return (a file
    saved with CRLF line ends, or by an editor that writes a BOM)."""
    return (line[len(BOM):] if line.startswith(BOM) else line).rstrip(b"\r")


def find_marker(lines: list[bytes], marker: bytes, frm: int = 0) -> int | None:
    """The index of the first line from `frm` on that is `marker` (compared bare); None when there is none."""
    return next((i for i in range(frm, len(lines)) if bare(lines[i]) == marker), None)


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
        self.planned_blocks: dict[str, str] = {}   # BLOCK_META blocks this run writes: their sha256 (recorded once on disk)
        self.armed = self.finished = False
        self.writes = 0
        self.live_tmp = ""
        self.warnings = 0
        self.kinds: set[str] = set()   # the words of the warnings given (the closing line's advice follows them)
        self.types_merged = False      # the memory types got new entries: their generated tables are stale
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
        self.kinds.add(word)
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
        """dst replaced by data through a temporary file beside it and a rename (mode: dst's, else the umask's); a dst
        that exists and is not a regular file (a device, a FIFO, a socket, a directory) is refused, never replaced."""
        replaceable(dst)
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
        return os.path.isfile(path) and find_marker(lines_of(read_bytes(path)), start) is not None

    def current_block(self, rel: str) -> bytes | None:
        """The body of rel's block (the lines between the markers) as it is now; None when there is no such file or
        block."""
        path = self.path_of(rel)
        if not os.path.isfile(path) or os.path.islink(path):
            return None
        return block_body(read_bytes(path), rel)

    def block_sha(self, rel: str) -> str | None:
        """The sha256 of what BOA owns of rel's block as it is now (owned_text); None when there is no block."""
        body = self.current_block(rel)
        return None if body is None else sha_bytes(owned_text(rel, body))

    def block_flags(self, path: str, start: bytes) -> str:
        """The flags a new block will need (c = file created, n = trailing newline added). A file that holds nothing but
        BOA's block counts as created (a clone's reinstall: the uninstall then removes the file, as on the original)."""
        if self.has_block(path, start):
            lines = lines_of(read_bytes(path))
            end = start.replace(b"start", b"end")
            return "c" if lines and bare(lines[0]) == start and bare(lines[-1]) == end \
                and sum(bare(x) == end for x in lines) == 1 else ""
        if not os.path.lexists(path):
            return "c"
        data = read_bytes(path)
        return "n" if data and not data.endswith(b"\n") else ""

    def block_upsert(self, path: str, rel: str, content: bytes) -> None:
        if os.path.lexists(path):
            old = read_bytes(path)
            new = with_block(old, rel, content, path)
            if new != old:   # an unchanged block is not rewritten (a reinstall writes nothing)
                self.atomic_write(path, new, stat.S_IMODE(os.stat(path).st_mode))
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.atomic_write(path, with_block(None, rel, content, path), None)

    def block_remove(self, path: str, rel: str, flags: str) -> None:
        """Remove the block (and the blank line before it), undo the recorded flags; the file's own line ends (CRLF
        too) and a byte order mark that stood before the block's start marker are kept."""
        start, end = markers(rel)
        lines = lines_of(read_bytes(path)) if os.path.isfile(path) else []
        st = find_marker(lines, start)
        en = find_marker(lines, end, st) if st is not None else None
        if st is None or en is None:
            return
        frm = st - 1 if st > 0 and bare(lines[st - 1]) == b"" else st
        out = lines[:frm] + lines[en + 1:]
        if frm == 0 and out and lines[0].startswith(BOM) and not out[0].startswith(BOM):
            out[0] = BOM + out[0]
        data = b"\n".join(out) + (b"" if "n" in flags or not out else b"\n")
        if "n" in flags and data.endswith(b"\r"):   # the CRLF file had no line end after its last line
            data = data[:-1]
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
                elif b in ("seeded_ledger", ROWS_META, *BLOCK_META.values()):
                    if not re.fullmatch(r"[0-9a-f]{64}", a) or c:
                        why = f"bad {b}"
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
            for rel, new in self.planned_blocks.items():
                if self.block_sha(rel) == new:
                    self.n_meta[BLOCK_META[rel]] = new
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
        derived: list[str] = []   # what stays of BOA's texts and MIT files: the notice is their attribution
        adapted = self.adapted_copies()   # read before the blocks go: the plug-in's names are in .gitignore's block
        for rel in sorted(self.o_file):
            if rel == NOTICE_REL:
                continue   # decided after the rest: it goes only when nothing derived from BOA stays
            f = self.path_of(rel)
            stays = True
            if not self.no_link(rel):
                self.warn("kept", f"{rel}: behind a symlink; not touched")
            elif not os.path.lexists(f):
                continue
            elif not os.path.isfile(f):
                self.warn("kept", f"{rel}: not a file any more (a directory or another node stands there); not touched")
            elif (changed := sha_file(f) != self.o_file[rel]) and not force:
                self.warn("kept", f"{rel}: changed since install{FORCE_ADVICE}")
            else:
                if not self.dry:
                    self.remove(f)
                self.say("removed", f"{rel} (changed; --force)" if changed else rel)
                stays = False
            kept = kept or stays
            if stays and not rel.startswith(AGPL_COPIES):
                derived.append(rel)
        for rel in sorted(self.o_block):
            if rel != ":exclude" and not self.no_link(rel):
                self.warn("kept", f"{rel}: a symlink; block left in place")
                kept = True
                if rel in ("AGENTS.md", ARCH_REL):   # BOA's text; the ignore and attribute blocks are not
                    derived.append(rel)
                continue
            body = self.current_block(rel) if rel in BLOCK_META else None
            rows = agent_rows(body, self.o_meta.get(ROWS_META)) if body is not None and rel == ARCH_REL else []
            if body is not None and (rows or sha_bytes(owned_text(rel, body)) != self.o_meta.get(BLOCK_META[rel])):
                why = "its residue register holds rows" if rows else \
                    "BOA's block was changed since install, or its install is not recorded"
                if not force:
                    self.warn("kept", f"{rel}: {why}{FORCE_ADVICE}")
                    kept = True
                    if rel in ("AGENTS.md", ARCH_REL):   # BOA's text stays: the notice is its attribution
                        derived.append(rel)
                    continue
                self.say("unblock", f"{rel} ({'rows' if rows else 'changed'}; --force)")
            else:
                self.say("unblock", rel)
            if not self.dry:
                self.block_remove(self.path_of(rel), rel, self.o_block[rel])
        kept = self.uninstall_notice(force, derived + adapted) or kept
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
                self.warn("kept", f"{rel}: {what}{FORCE_ADVICE}")
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

    def adapted_copies(self) -> list[str]:
        """The project's adapted copies of BOA's MIT files that the uninstall leaves (BOA did not install them, so they
        are not in the manifest): `.boa/markers.json`, `.boa/memory-types.json`, and the stack plug-in files by the
        names BOA shipped, as its `.gitignore` block re-includes them (`!/.boa/stack/<name>`). A file the project added
        to `.boa/stack/` under another name is its own, not BOA's."""
        names = [MARKERS_REL, TYPES_REL]
        gi = self.path_of(".gitignore")
        if os.path.isfile(gi) and not os.path.islink(gi):
            start, end = markers(".gitignore")
            inside = False
            for line in lines_of(read_bytes(gi)):
                if line == start or line == end:
                    inside = line == start
                elif inside and line.startswith(f"!/{STACK_DIR}/".encode()) and not line.endswith(b"/"):
                    names.append(re.sub(r"\\(.)", r"\1", line[2:].decode("utf-8", "replace")))
        return [r for r in names if r not in self.o_file and self.safe_rel(r) and self.no_link(r)
                and os.path.isfile(self.path_of(r))]

    def uninstall_notice(self, force: bool, derived: list[str]) -> bool:
        """The notice (NOTICE_REL) is the attribution of BOA's texts and MIT files: removed like any installed file
        only when none of them stays; `derived` names those that stay (an installed file kept, but not one of BOA's
        AGPL tool copies; AGENTS.md's or the 04's block kept; a project-adapted copy, adapted_copies). Otherwise the
        notice is kept and the report names what it covers. A changed notice is kept unless --force, like any file.
        True when the notice was kept."""
        rel = NOTICE_REL
        if rel not in self.o_file:
            return False
        f = self.path_of(rel)
        if not self.no_link(rel):
            self.warn("kept", f"{rel}: behind a symlink; not touched")
        elif not os.path.lexists(f):
            return False
        elif not os.path.isfile(f):
            self.warn("kept", f"{rel}: not a file any more (a directory or another node stands there); not touched")
        elif (changed := sha_file(f) != self.o_file[rel]) and not force:
            self.warn("kept", f"{rel}: changed since install{FORCE_ADVICE}")
        elif derived:
            more = f" and {len(derived) - 1} more" if len(derived) > 1 else ""
            self.warn("kept", f"{rel}: the attribution of what stays of BOA ({derived[0]}{more}); remove it with them")
        else:
            if not self.dry:
                self.remove(f)
            self.say("removed", f"{rel} (changed; --force)" if changed else rel)
            return False
        return True

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
        fd = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_BINARY", 0), 0o644)   # O_BINARY: no CRLF from the Windows C runtime
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
        agents = cfg.get("BOA_AGENTS_BLOCK", "").strip() or "full"
        if agents not in AGENTS_BLOCK_MODES:
            raise Fail(f"BOA_AGENTS_BLOCK='{agents}' is not one of {', '.join(AGENTS_BLOCK_MODES)}: fix it in "
                       ".boa/config.env")
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
        date = date or self.o_meta.get("install_date") or self.rendered_date(render, cfg, pkg, ltarget, forge, lead,
                                                                              agents)
        self.n_meta["install_date"] = date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        keys = self.render_keys(cfg, ltarget)
        rendered = self.render_templates(render, cfg, pkg, keys)

        # the stage: every project path with its bytes and mode, decided before anything is written
        stage: dict[str, tuple[bytes, int]] = {}
        unmapped, source = [], {}
        for rel, item in sorted(rendered.items()):
            dsts = target_of(rel, forge, lead, agents)
            if dsts is None:
                unmapped.append(rel)
            for dst in dsts or []:
                if dst in source:   # never decided by the order the templates are read in
                    raise Fail(f"templates {source[dst]} and {rel} both map to {dst} (fix target_of): nothing installed")
                source[dst] = rel
                stage[dst] = (for_path(dst, item[0]), item[1])
        if unmapped:
            raise Fail(f"templates without a project path (add them to target_of): {' '.join(unmapped)}")
        stage.update(tree(os.path.join(pkg, "core"), ".boa"))
        stage.update(tree(os.path.join(pkg, "stacks", stack), STACK_DIR))
        staged_boa = {posix_parts(rel)[1] for rel in stage if rel.startswith(".boa/")}
        log_dir, state_dir = cfg.get("BOA_LOG_DIR", ".boa/logs"), cfg.get("BOA_STATE_DIR", ".boa/state")
        staged_boa.add(posix_parts(MERGE_BASE_DIR)[1])   # the merge bases are BOA's too
        reserved = {boa_paths.fold(n) for n in staged_boa} | set(boa_paths.FIXED_RESERVED)
        for d in (log_dir, state_dir):
            m = re.fullmatch(r"\.boa/([A-Za-z0-9_][A-Za-z0-9._-]{0,63})", d)
            if not m or boa_paths.fold(m.group(1)) in reserved:
                raise Fail(f"BOA_LOG_DIR / BOA_STATE_DIR must be a new subdirectory of .boa/ (got '{d}'): "
                           "fix it in .boa/config.env")
        # BOA's own files are put back by `boa install`; the files the agent writes for the project stay versioned
        # (the stack plug-in too: the project adapts it). Each shipped plug-in file is re-included by name, so a project
        # rule such as `*.env` cannot hide it, while a file the project adds there follows the project's own rules.
        stack_files = sorted(rel for rel in stage if in_stack(rel))
        # the notice too: it is the attribution of BOA's files, so an ignore rule of the project that hides it is warned
        versioned = [*PROJECT_FILES, *stack_files, *([NOTICE_REL] if NOTICE_REL in stage else [])]
        blocks = {".gitignore": "".join(f"{x}\n" for x in ("/.boa/*", *(f"!/{r}" for r in PROJECT_FILES), f"!/{STACK_DIR}/",
                                                          *(f"!/{gitignore_literal(r)}" for r in stack_files))),
                  ".gitattributes": "/.boa/** text eol=lf\n",
                  ":exclude": f"/{lead}/\n/.lane-resume/\n"}

        plan, residue, residue_why = [], b"", ""
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
                # always a marked block (also when created): a clone's reinstall replaces it in place; a block changed
                # since BOA wrote it, or one with no record of how BOA wrote it, is kept and the new one parked
                act = "block-kept" if self.block_edited(rel, data) else "block"
            elif not os.path.lexists(dst):
                act = "create"
            elif same:
                act = "identical"
            elif (in_stack(rel) or rel in MERGED_JSON) and os.path.isfile(dst):
                act = "adapted"   # the project's versioned copy (a clone, or a lost manifest): never overwritten
            elif rel == ARCH_REL and os.path.isfile(dst) and RESIDUE_TMPL in rendered \
                    and (rel in self.o_block or b"<!-- residue-register:begin -->" not in read_bytes(dst)
                         or self.has_block(dst, markers(rel)[0])):   # a clone: BOA's block there, no manifest
                # the project's own 04: BOA's residue register as a marked block (+ the rendering parked), the rows
                # agents wrote into it carried into the new block; text changed outside the rows keeps the block
                residue, residue_why = self.residue_block(rendered[RESIDUE_TMPL][0])
                if residue is not None and self.block_edited(rel, residue):
                    residue_why = ("a block between BOA's markers that is not BOA's residue register"
                                   if b"<!-- residue-register:begin -->" not in (self.current_block(rel) or b"") else
                                   "BOA's residue register block was changed since install outside its rows"
                                   if BLOCK_META[rel] in self.o_meta else
                                   "BOA's residue register block differs from this release's and BOA has no record "
                                   "of writing it (an older release's install, or a clone)")
                act = "residue-kept" if residue_why else "residue"
            else:
                act = "conflict"
            plan.append((rel, act))
        # the project's own JSON files kept: the entries new in the package since the merge base added (decided now,
        # written in order below); no base recorded (an older release, a fresh clone): nothing merged (None)
        bases = {rel: self.merge_base(rel) for rel in MERGED_JSON}
        merges: dict[str, tuple[bytes | None, list[str], str] | None] = {
            rel: None if bases[rel] is None else (None, [], "") if bases[rel] == stage[rel][0]
            else merge_json(rel, read_bytes(self.path_of(rel)), stage[rel][0], bases[rel])
            for rel, act in plan if rel in MERGED_JSON and act in ("kept", "adapted")}
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
            if act in ("block", "block-kept", "residue", "residue-kept"):
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
                self.n_file[rel] = self.o_file[rel]   # still the sha256 as installed: never "unchanged" after a merge
                self.park(data, mode, rel)
                if rel in merges:
                    self.merge_in(rel, merges[rel])
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
                hook = LEAD_HOOK_FILES.get(rel[len(lead) + 1:]) if rel.startswith(f"{lead}/") else None   # target_of's form
                if hook:
                    self.warn("hook", f"{rel}: {hook}: merge BOA's rendering into it before the first pause")
            elif act == "adapted":
                what = {MARKERS_REL: "marker words file", TYPES_REL: "memory types file"}.get(rel, "stack plug-in file")
                self.warn("kept", f"{rel}: the project's adapted {what} is kept; the package's version in "
                                  f"{PENDING_DIR}/{rel}")
                self.park(data, mode, rel)
                if rel in merges:
                    self.merge_in(rel, merges[rel])
            elif act == "unsafe":
                self.warn("conflict", f"{rel}: a symlink or a file is in the way; rendered version in {PENDING_DIR}/{rel}")
                self.park(data, mode, rel)
            elif act == "block":
                self.write_block(rel, data)
                self.say("block", rel)
            elif act == "block-kept":
                self.keep_block(rel)
                self.warn("kept", f"{rel}: BOA's block was changed since install, or its install is not recorded; the "
                                  f"block is kept, the new one in {PENDING_DIR}/{rel}")
                self.park(data, mode, rel)
            elif act == "residue":
                rows = len(table_rows(residue))
                self.write_block(rel, residue)
                self.n_meta[ROWS_META] = sha_bytes(block_lines(table_rows(block_lines(rendered[RESIDUE_TMPL][0]))))
                self.warn("block", f"{rel}: the project's own file; BOA's residue register added as a marked block"
                                   f"{f' ({rows} row(s) carried over)' if rows else ''}, the full rendering in "
                                   f"{PENDING_DIR}/{rel}")
                self.park(data, mode, rel)
            elif act == "residue-kept":
                self.keep_block(rel)
                self.warn("kept", f"{rel}: {residue_why}; the block is kept, the full rendering in {PENDING_DIR}/{rel}")
                self.park(data, mode, rel)
            if rel in MERGED_JSON:   # only once the project's file is written: an interruption before never advances it
                self.record_base(rel, act, clone, merges.get(rel), data)
        for rel, content in blocks.items():
            if not block_ok[rel]:
                self.warn("conflict", f"{rel} is a symlink or not a file: add these lines by hand: "
                                      f"{' '.join(content.split())}")
                continue
            self.add_block(rel, content.encode())
            self.say("block", "info/exclude" if rel == ":exclude" else rel)
        # the versioned paths git still ignores: on the tree as written, or (a dry run) as it would be written
        gi = blocks[".gitignore"].encode() if block_ok[".gitignore"] else None
        self.check_versioned(versioned, simulate=self.dry, gitignore_block=gi)

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
        advice = []
        if self.kinds & {"conflict", "kept", "block"}:   # each parks a rendering in pending
            advice.append(f"resolve conflicts from {PENDING_DIR}, then re-run")
        if "ignored" in self.kinds:
            advice.append("change the ignore rules named above so the versioned paths are not ignored")
        if self.types_merged:
            advice.append("regenerate the memory tables: python3 -I .boa/tools/memory_types.py --write")
        tail = "".join(f"; {a}" for a in advice)
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
        """A Markdown file of the bank holds a memory with an id (a line starting `@@@memory-<N>`) among the lines the
        memory lint judges (memory_lint.judged_lines: after the `<!-- boa:memory-cutoff -->` line, outside code
        fences): legacy memories before the cutoff are never registered, so they ask for no ledger."""
        for cur, dirs, names in os.walk(bank):
            dirs.sort()
            for n in sorted(names):
                if n.endswith(".md"):
                    try:
                        text = read_bytes(os.path.join(cur, n)).decode("utf-8", "replace")
                    except OSError:
                        continue
                    if any(MEMORY_ID.match(line.encode("utf-8")) for _, line in memory_lint.judged_lines(text)):
                        return True
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
            if boa_config.special_kind(env["stamp"]) is not None:   # one stat first: a FIFO is no stamp, never opened
                raise ValueError("not a regular file")
            with open(env["stamp"], encoding="utf-8") as fh:
                stamp = json.load(fh)
        except (OSError, ValueError):
            stamp = {}   # no usable stamp: the environment is built again
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
        st = find_marker(lines, start)
        if st is not None and find_marker(lines, end, st) is None:
            raise Fail(f"{path}: {start.decode()} without {end.decode()} after it (fix the file by hand): nothing installed")

    def check_versioned(self, rels: list[str], simulate: bool = False, gitignore_block: bytes | None = None) -> None:
        """Warn for every path the project must version that git still ignores once BOA's block is in place: a rule
        of the project's own that BOA's re-include lines cannot undo (an ignored parent such as `/.boa/` or `.*`).
        A dry run writes nothing, so it asks git in a throwaway repository holding the ignore files as the run would
        leave them (the top-level .gitignore with BOA's block, info/exclude, the .gitignore files on the way to each
        path, the project's core.excludesFile resolved against the project): the preview warns exactly as the run
        does. The throwaway git runs with every variable that relocates a repository removed (THROWAWAY_UNSET), so an
        exported GIT_DIR never points it at the project; a symlinked .gitignore is left out, as git leaves it out."""
        if not simulate:
            self.ask_ignored(self.target, rels, [])
            return
        env = {k: v for k, v in os.environ.items() if k not in THROWAWAY_UNSET}
        with tempfile.TemporaryDirectory(prefix="boa-install-ignore.") as tmp:
            if git(tmp, "init", "-q", env=env) is None:
                self.warn("ignored", "could not ask git which versioned paths it ignores (no throwaway repository)")
                return
            top = self.path_of(".gitignore")
            cur = read_bytes(top) if os.path.isfile(top) and not os.path.islink(top) else None
            data = with_block(cur, ".gitignore", gitignore_block, top) if gitignore_block is not None else cur
            if data is not None:
                with open(os.path.join(tmp, ".gitignore"), "wb") as fh:
                    fh.write(data)
            if os.path.isfile(self.exclude):
                with open(os.path.join(tmp, ".git", "info", "exclude"), "wb") as fh:
                    fh.write(read_bytes(self.exclude))
            for rel in rels:
                parts = posix_parts(rel)
                for k in range(1, len(parts)):
                    os.makedirs(os.path.join(tmp, *parts[:k]), exist_ok=True)
                    own = os.path.join(self.target, *parts[:k], ".gitignore")
                    copy = os.path.join(tmp, *parts[:k], ".gitignore")
                    if os.path.isfile(own) and not os.path.islink(own) and not os.path.lexists(copy):
                        shutil.copyfile(own, copy)
            # `~` expanded by --path; a relative path is the project's (git names it as configured in its output)
            excludes = git(self.target, "config", "--get", "--path", "core.excludesFile")
            opts, sources = [], {}
            if excludes:
                resolved = excludes if os.path.isabs(excludes) else os.path.join(self.target, excludes)
                resolved = resolved.replace(os.sep, "/")   # git names the file as given: one spelling on Windows too
                opts, sources = ["-c", f"core.excludesFile={resolved}"], {resolved: excludes}
            self.ask_ignored(tmp, rels, opts, env, sources)

    def ask_ignored(self, repo: str, rels: list[str], opts: list[str], env: dict[str, str] | None = None,
                    sources: dict[str, str] | None = None) -> None:
        """Warn for each of `rels` git ignores in `repo`; `sources` renames an ignore file's path in the warning."""
        try:
            r = self.check_ignore(repo, rels, opts, env)
        except (OSError, subprocess.SubprocessError) as exc:
            self.warn("ignored", f"could not ask git which versioned paths it ignores ({exc})")
            return
        if r.returncode not in (0, 1):
            self.warn("ignored", f"could not ask git which versioned paths it ignores: {r.stderr.strip()[:200]}")
            return
        hits = self.ignore_hits(r.stdout)
        parents = {d for _, _, _, path in hits for d in posix_parent_dirs(path)}
        ignored_dirs = None   # which of those directories git ignores; None when it could not be asked
        if parents:
            try:
                q = self.check_ignore(repo, sorted(parents), opts, env)
                if q.returncode in (0, 1):
                    ignored_dirs = {path for _, _, _, path in self.ignore_hits(q.stdout)}
            except (OSError, subprocess.SubprocessError):
                pass
        for src, num, pat, path in hits:
            src = (sources or {}).get(src, src)
            if ignored_dirs is None:
                how = "change that rule"
            elif any(d in ignored_dirs for d in posix_parent_dirs(path)):
                how = "change that rule (no later line can re-include a path whose parent directory is ignored)"
            else:
                how = f"add a `!{path}` re-include line after it, or remove the rule"
            self.warn("ignored", f"{path}: still git-ignored by `{pat}` ({src}:{num}), but it must be versioned: {how}")

    @staticmethod
    def check_ignore(repo: str, rels: list[str], opts: list[str],
                     env: dict[str, str] | None) -> subprocess.CompletedProcess:
        """`git check-ignore -v --no-index --stdin` on `rels`, one per line. The paths go in as UTF-8 bytes: a text-mode
        pipe would write each newline as CRLF on Windows, and git would read the CR as part of the path."""
        r = subprocess.run(["git", *opts, "-C", repo, "check-ignore", "-v", "--no-index", "--stdin"], env=env,
                           input="".join(f"{x}\n" for x in rels).encode("utf-8"), capture_output=True, timeout=30)
        return subprocess.CompletedProcess(r.args, r.returncode, r.stdout.decode("utf-8", "replace"),
                                           r.stderr.decode("utf-8", "replace"))

    @staticmethod
    def ignore_hits(out: str) -> list[tuple[str, str, str, str]]:
        """(source, line, pattern, path) of each `git check-ignore -v` line; a `!` pattern re-includes the path."""
        hits = []
        for line in out.splitlines():   # <source>:<line>:<pattern> TAB <path>
            where, _, path = line.partition("\t")
            m = re.fullmatch(r"(.*?):([0-9]+):(.*)", where)
            if m and not m.group(3).startswith("!"):
                hits.append((m.group(1), m.group(2), m.group(3), path))
        return hits

    def add_block(self, rel: str, content: bytes) -> None:
        start, _ = markers(rel)
        path = self.path_of(rel)
        self.n_block[rel] = self.o_block[rel] if rel in self.o_block else self.block_flags(path, start)
        if not self.dry:
            self.touched()
            self.block_upsert(path, rel, content)

    def block_edited(self, rel: str, content: bytes) -> bool:
        """What BOA owns of rel's block (owned_text) differs from the new block (`content`) and from the sha256
        recorded when BOA last wrote it: changed by someone since, or written before BOA recorded it (an older
        release's manifest, a clone with no manifest), so BOA cannot vouch it is its own. A file with no block yet
        gets one."""
        now = self.block_sha(rel)
        return now is not None and now != sha_bytes(owned_text(rel, block_lines(content))) \
            and now != self.o_meta.get(BLOCK_META[rel])

    def residue_block(self, content: bytes) -> tuple[bytes | None, str]:
        """The residue register block to write into the project's own 04: the new one (`content`) with the rows agents
        wrote into the current block's table carried over, in their order, but for a row the new block already holds
        (an exact match: a row the release's template ships), and "" (no reason to keep the block); None
        and the reason when there are rows and the new block has no table to take them, or a table whose header or
        separator line differs from the current one (a column added, renamed or moved: the rows would no longer
        fit)."""
        body = self.current_block(ARCH_REL)
        rows = table_rows(body) if body is not None else []
        new = block_lines(content)
        if not rows:
            return new, ""
        if table_head(new) is None:
            return None, "this release's residue register has no table to take the rows agents wrote into it"
        if table_head(body) != table_head(new):
            return None, ("this release changes the residue register's table header or separator (its columns): the "
                          "rows agents wrote into it would no longer fit")
        ships = set(table_rows(new))   # a row the release's template carries itself is never carried twice
        return carry_rows(new, [r for r in rows if r not in ships]), ""

    def write_block(self, rel: str, content: bytes) -> None:
        """A BLOCK_META block written, its sha256 recorded (also by an interrupted run once the block is on disk)."""
        self.planned_blocks[rel] = sha_bytes(owned_text(rel, block_lines(content)))
        self.add_block(rel, content)
        self.n_meta[BLOCK_META[rel]] = self.planned_blocks[rel]

    def keep_block(self, rel: str) -> None:
        """A BLOCK_META block left as it is: still BOA's block in the manifest, its recorded sha256 (if any) kept."""
        self.n_block[rel] = self.o_block[rel] if rel in self.o_block else self.block_flags(self.path_of(rel),
                                                                                          markers(rel)[0])
        for key in (BLOCK_META[rel], ROWS_META) if rel == ARCH_REL else (BLOCK_META[rel],):
            if key in self.o_meta:
                self.n_meta[key] = self.o_meta[key]

    def merge_base(self, rel: str) -> bytes | None:
        """The merge base of a MERGED_JSON file: its recorded copy under MERGE_BASE_DIR, read before anything is
        written; None when none is recorded or the copy no longer has the recorded sha256."""
        b = f"{MERGE_BASE_DIR}/{posix_parts(rel)[-1]}"
        p = self.path_of(b)
        if b in self.o_file and self.no_link(b) and os.path.isfile(p) and sha_file(p) == self.o_file[b]:
            return read_bytes(p)
        return None

    def record_base(self, rel: str, act: str, clone: bool, result, data: bytes) -> None:
        """Advance (or keep) the merge base of a MERGED_JSON file: the package version `data` once the project's file
        is BOA's (installed, updated, adopted), or kept with this version's new entries merged, nothing new, or no
        base so far (the next release merges what is new since this one); the old base kept when the merge was
        refused (its entries are offered again); nothing for a file that is not BOA's (a conflict)."""
        b = f"{MERGE_BASE_DIR}/{posix_parts(rel)[-1]}"
        if act in ("kept", "adapted") and result is not None and result[2]:
            if b in self.o_file:
                self.n_file[b] = self.o_file[b]
        elif (act in ("same", "update", "create", "kept", "adapted") or (act == "identical" and clone)) \
                and self.writable(b):
            self.put_recorded(data, 0o644, b)

    def merge_in(self, rel: str, result: tuple[bytes | None, list[str], str] | None) -> None:
        """Write a kept JSON file with the entries new in the package since its merge base added (merge_json), one
        `merge` line per entry; a refused merge leaves the file as it is and says why; with no merge base (None)
        nothing is added and that is said."""
        if result is None:
            self.say("kept", f"{rel}: no merge base recorded (installed by an older release, or a fresh clone): "
                             "nothing added; the package's new entries are merged from its next version on")
            return
        new, added, why = result
        if why:
            self.warn("kept", f"{rel}: the package's new entries are not added ({why}): add them by hand from "
                              f"{PENDING_DIR}/{rel}")
            return
        if new is None:
            return
        for entry in added:
            self.say("merge", f"{rel}: {entry} (added from the package; the project's own entries unchanged)")
        self.types_merged |= rel == TYPES_REL
        self.put(new, os.stat(self.path_of(rel)).st_mode, rel)

    def park(self, data: bytes, mode: int, rel: str) -> None:
        """The rendered version of a file BOA may not write goes to .boa/pending/<rel>."""
        if not self.writable(f"{PENDING_DIR}/{rel}"):
            self.warn("skipped", f"{PENDING_DIR}/{rel}: unsafe path; rendered version not parked")
            return
        self.put_recorded(data, mode, f"{PENDING_DIR}/{rel}")

    def rendered_date(self, render, cfg, pkg, ltarget, forge, lead, agents) -> str | None:
        """The install date the project's files already carry: each template that holds the date is rendered with a
        sentinel, and a target file that equals the rendering up to the sentinel gives the date found there."""
        self.n_meta["install_date"] = SENTINEL_DATE
        for rel, (data, _mode) in sorted(self.render_templates(render, cfg, pkg, self.render_keys(cfg, ltarget)).items()):
            for dst in (target_of(rel, forge, lead, agents) or []) if SENTINEL_DATE.encode() in data else []:
                text = for_path(dst, data).decode("utf-8", "replace")
                i = text.find(SENTINEL_DATE)
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


def target_of(rel: str, forge: str, lead: str, agents: str) -> list[str] | None:
    """The project paths of a template ([] = not for this config); None = unmapped. Agents and commands stay under
    `.boa/`: the agent wires them in its runtime's format. BOA_AGENTS_BLOCK (`agents`, required): full = BOA's rules
    are AGENTS.md's marked block and the pointer template goes nowhere; pointer = BOA's rules are RULES_REL and
    AGENTS.md's block is the pointer template; each template has exactly one target per mode."""
    if rel in ("AGENTS.md", POINTER_TMPL):
        return {("AGENTS.md", "full"): ["AGENTS.md"], (POINTER_TMPL, "full"): [],
                ("AGENTS.md", "pointer"): [RULES_REL], (POINTER_TMPL, "pointer"): ["AGENTS.md"]}[(rel, agents)]
    if rel.startswith("memory-bank/"):
        return [rel]
    if rel == "agent-handbook.md":
        return ["docs/agent-handbook.md"]
    if rel == NOTICE_TMPL:
        return [NOTICE_REL]
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


def in_stack(rel: str) -> bool:
    """A manifest path (always written with `/`) below the stack plug-in's directory."""
    return pathlib.PurePosixPath(STACK_DIR) in pathlib.PurePosixPath(rel).parents


def gitignore_literal(rel: str) -> str:
    """`rel` as a .gitignore pattern that matches only itself: glob characters and a backslash escaped, and every
    trailing space as `\\ ` (git drops unescaped trailing spaces of a pattern)."""
    lit = re.sub(r"([\\*?\[])", r"\\\1", rel)
    stem = lit.rstrip(" ")
    return stem + "\\ " * (len(lit) - len(stem))


def with_block(old: bytes | None, rel: str, content: bytes, path: str = "") -> bytes:
    """A file's bytes with BOA's marked block holding `content`: the block replaced in place, else appended (after a
    line end the file lacked, and a blank line), else the whole file when there is none (`old` None or empty). The
    markers are found bare (a CRLF line end, a byte order mark); the lines written take the file's own line ends: the
    start marker's in place, CRLF appended to a file that uses CRLF."""
    start, end = markers(rel)
    if content and not content.endswith(b"\n"):
        content += b"\n"
    lines = lines_of(old or b"")
    st = find_marker(lines, start)
    if st is not None:
        en = find_marker(lines, end, st)
        if en is None:
            raise Fail(f"{path or rel}: {start.decode()} without {end.decode()} after it (fix the file by hand)")
        cr = b"\r" if lines[st].endswith(b"\r") else b""
        out = lines[:st + 1] + [x + cr for x in lines_of(content)] + lines[en:]
        return b"".join(x + b"\n" for x in out)
    if not old:
        return start + b"\n" + content + end + b"\n"
    eol = b"\r\n" if b"\r\n" in old else b"\n"
    data = old if old.endswith(b"\n") else old + eol
    return data + eol + start + eol + b"".join(x + eol for x in lines_of(content)) + end + eol


def block_body(data: bytes, rel: str) -> bytes | None:
    """The lines between BOA's markers in a file's bytes, each ending in a newline (a CRLF's carriage return dropped),
    as with_block writes `content` (block_body(with_block(x, rel, c), rel) == block_lines(c)); None when the file
    holds no complete block."""
    start, end = markers(rel)
    lines = lines_of(data)
    st = find_marker(lines, start)
    en = find_marker(lines, end, st) if st is not None else None
    if st is None or en is None:
        return None
    return block_lines([x[:-1] if x.endswith(b"\r") else x for x in lines[st + 1:en]])


def table_rows(body: bytes) -> list[bytes]:
    """The rows of the first Markdown table in a block's body: the lines starting with `|` right after its separator
    line (none when the body holds no table)."""
    lines = lines_of(body)
    sep = next((i for i, x in enumerate(lines) if TABLE_RULE.match(x)), None)
    rows = []
    for x in lines[sep + 1:] if sep is not None else []:
        if not x.lstrip().startswith(b"|"):
            break
        rows.append(x)
    return rows


def table_head(body: bytes) -> tuple[bytes, bytes] | None:
    """The header and separator lines of the first Markdown table in a block's body; None when it has none."""
    lines = lines_of(body)
    sep = next((i for i, x in enumerate(lines) if TABLE_RULE.match(x)), None)
    return None if sep is None else (lines[sep - 1] if sep else b"", lines[sep])


def agent_rows(body: bytes, shipped: str | None) -> list[bytes]:
    """The rows of a register block's table that agents wrote: the rows after the leading ones whose sha256 (block_lines)
    is `shipped`, the recorded rows of the template (carry_rows puts the agents' rows after them); every row when none
    is recorded or no leading run matches (a shipped row edited: all count, so the block is kept)."""
    rows = table_rows(body)
    for k in range(len(rows), -1, -1):
        if shipped is not None and sha_bytes(block_lines(rows[:k])) == shipped:
            return rows[k:]
    return rows


def owned_text(rel: str, body: bytes) -> bytes:
    """What BOA owns of a block's body: all of it, but for the residue register, whose table rows the agents write."""
    if rel != ARCH_REL:
        return body
    rows = table_rows(body)
    lines = lines_of(body)
    sep = next((i for i, x in enumerate(lines) if TABLE_RULE.match(x)), 0)
    return block_lines(lines[:sep + 1] + lines[sep + 1 + len(rows):]) if rows else body


def carry_rows(body: bytes, rows: list[bytes]) -> bytes | None:
    """`body` (a block's lines) with `rows` added after the rows its first table already has; None when it has no
    table."""
    lines = lines_of(body)
    sep = next((i for i, x in enumerate(lines) if TABLE_RULE.match(x)), None)
    if sep is None:
        return None
    end = sep + 1 + len(table_rows(body))
    return block_lines(lines[:end] + rows + lines[end:])


def block_lines(content: bytes | list[bytes]) -> bytes:
    """A block's body as with_block writes it: every line ending in a newline."""
    return b"".join(x + b"\n" for x in (lines_of(content) if isinstance(content, bytes) else content))


def merge_json(rel: str, ours: bytes, theirs: bytes, base: bytes) -> tuple[bytes | None, list[str], str]:
    """The project's JSON file `ours` with the entries the package version `theirs` has and its version last merged
    (`base`, the merge base) had not: only what is new since the base, and only when the project's file lacks it;
    nothing of the project's is changed, moved or removed, so an entry the project deleted, renamed or narrowed is
    never brought back. Entries: a top-level key; in the markers file a marker entry by its key; in the memory types a
    type by its name, a recall moment by its id, a keyword route by its keyword and type. Returns (the merged bytes,
    written in the file's shipped layout; None when nothing is to be written, the entries added, why the merge was
    refused: a file that does not parse, another schema, or a result its own validator refuses, e.g. a new marker
    without a text in the project's language)."""
    try:
        mine, pkg, was = (json.loads(b.decode("utf-8")) for b in (ours, theirs, base))
    except (UnicodeDecodeError, ValueError) as exc:   # json.JSONDecodeError is a ValueError
        return None, [], f"it does not parse as JSON ({exc})"
    if not all(isinstance(x, dict) for x in (mine, pkg, was)):
        return None, [], "it is not a JSON object"
    if mine.get("schema") != pkg.get("schema"):
        return None, [], f"its schema {mine.get('schema')!r} is not the package's {pkg.get('schema')!r}"
    ident = {"types": lambda e: e.get("name"), "recall_moments": lambda e: e.get("id"),
             "keyword_routes": lambda e: (e.get("keyword"), e.get("type"))}

    def ids(entries: object, key: str) -> set[str]:
        return {repr(ident[key](e)) for e in entries if isinstance(e, dict)} if isinstance(entries, list) else set()

    out, added = dict(mine), []
    for key, new in pkg.items():
        old, before = mine.get(key), was.get(key)
        if key not in mine:
            if key not in was:
                out[key] = new
                added.append(key)
        elif isinstance(old, dict) and isinstance(new, dict):   # the markers: one entry per key
            gone = before if isinstance(before, dict) else {}
            more = {k: v for k, v in new.items() if k not in old and k not in gone}
            out[key] = {**old, **more}
            added += [f"{key} {k}" for k in more]
        elif isinstance(old, list) and isinstance(new, list) and key in ident:
            have = ids(old, key) | ids(before, key)
            more = [e for e in new if isinstance(e, dict) and repr(ident[key](e)) not in have]
            out[key] = old + more
            added += [f"{key} {' '.join(str(x) for x in label if x is not None)}"
                      for label in (ident[key](e) if key == "keyword_routes" else (ident[key](e),) for e in more)]
    if not added:
        return None, [], ""
    bad = boa_markers.problems(out) if rel == MARKERS_REL else memory_types.validate(out)
    if bad:
        return None, added, "; ".join(bad[:3])
    if rel == MARKERS_REL:
        return boa_markers.dumps(out).encode("utf-8"), added, ""
    return json_lines(out).encode("utf-8"), added, ""


# the shipped layout of a memory type: these keys in this order, over four lines
TYPE_LINES = (("name", "records"), ("use_when",), ("must_contain",), ("route", "recall"))


def json_lines(data: dict) -> str:
    """A JSON object in the memory types' shipped layout: two-space indentation, one line per element of a list, a
    memory type over the four lines of TYPE_LINES (json_lines(json.loads(shipped file)) is the shipped file)."""
    def dump(v: object) -> str:
        return json.dumps(v, ensure_ascii=False)

    def element(e: object) -> str:
        if isinstance(e, dict) and list(e) == [k for group in TYPE_LINES for k in group]:
            return "{" + ",\n     ".join(", ".join(f"{dump(k)}: {dump(e[k])}" for k in group) for group in TYPE_LINES) + "}"
        return dump(e)

    out, items = ["{"], list(data.items())
    for i, (k, v) in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        if isinstance(v, list) and v:
            out.append(f"  {dump(k)}: [")
            out += [f"    {element(e)}" + ("," if j < len(v) - 1 else "") for j, e in enumerate(v)]
            out.append("  ]" + comma)
        else:
            out.append(f"  {dump(k)}: {dump(v)}{comma}")
    return "\n".join(out + ["}"]) + "\n"


def for_path(dst: str, data: bytes) -> bytes:
    """A rendering as it lands at `dst`: BOA's rules moved to RULES_REL get their relative links one level up (the
    template's links are written from the project's top)."""
    return LINK.sub(b"](../", data) if dst == RULES_REL else data


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


def posix_parent_dirs(rel: str) -> list[str]:
    """The directories above a path written with `/`, outermost first (`a/b/c` gives `a`, `a/b`)."""
    parts = posix_parts(rel)
    return ["/".join(parts[:k]) for k in range(1, len(parts))]


def git(cwd: str, *args: str, env: dict[str, str] | None = None) -> str | None:
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=30,
                           stdin=subprocess.DEVNULL, env=env)
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
