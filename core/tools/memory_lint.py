#!/usr/bin/env python3
"""Memory record lint: every recorded memory is one block, every block is well formed and correctly linked.

A memory block (memory bank entries, decisions, progress, metalearning, lead notes):

    @@@memory-<N> brief="<one-line summary>" datetime="<YYYY-MM-DDTHH:MM:SSZ>" keywords="<words, T-NNN ids>" type="<type>"
    <the full text of the memory>
    @endmemory

with, optionally, `supersedes="memory-12,memory-31"` (it replaces those) and `superseded-by="memory-<N>"` (stamped by
memory_write on a memory that a newer one replaced: the only edit ever made to an existing block). Ids are one global,
progressive sequence over the memory bank, assigned only by memory_write and recorded in the id ledger
`<memory bank>/.memory-ids.jsonl`. A draft (an id-less block: `@@@memory brief=…`, as `memory_write.py
--format-only` renders it for a report or a lane file) is checked with `--drafts`; it may carry `supersedes` (final
ids) and `supersedes-brief` (the brief of another draft of the same batch, several separated by ` | `).

Checks, each reported as `<file>:<line>: <finding>`:
  * the header: exactly the fields brief, datetime, keywords, type (+ supersedes, superseded-by; drafts: supersedes,
    supersedes-brief), each once, `key="value"`, nothing else on the line; an id (`@@@memory-<N>`, N >= 1) on every
    block of the bank, none on a draft;
  * brief: not empty, at most 200 characters; keywords: not empty, a task id among them is T-NNN; datetime: exactly
    `YYYY-MM-DDTHH:MM:SSZ`, a real UTC time, not in the future (later than the real now + 5 min); type: one of `.boa/memory-types.json` (memory_types.py);
  * the block has a text and is closed by `@endmemory` before the next block (no nesting) and the end of the file;
  * links (over all the files linted together): ids unique; in each file in increasing order; every `supersedes` id
    exists, is lower than the block's own and its datetime is strictly earlier (supersession runs forward in time); `supersedes` and `superseded-by` agree both ways; one successor at most;
    no cycle;
  * the id ledger (when the files linted are the memory bank, or `--ledger FILE`): every block's id is in it (an id
    not in it was written by hand) and, when the whole bank is linted, every ledger id has its block (no orphan; an id voided by
    `memory_write.py --repair-ledger` after a crash stays reserved, never reused, and needs no block).
Lines in fenced code blocks (```), and every line up to a `<!-- boa:memory-cutoff -->` line (legacy, exempt), are not
judged; prose and headings between blocks are allowed.

Usage:  python3 -I .boa/tools/memory_lint.py [--drafts] [--ledger FILE | --no-ledger] [path...]
        python3 -I .boa/tools/memory_lint.py --staged     the staged memory bank (pre-commit)
  path: files or directories (every *.md under them); default: the project's memory bank (BOA_MEMORY_DIR, default
  memory-bank). Last line: "memory-lint: <n> block(s) in <m> file(s), <k> finding(s)".
A file to lint or the id ledger that is a FIFO, a device, a socket or a directory is never opened (one stat first: a
FIFO would hang the lint): it is a finding naming it.
Exit: 0 no finding, 1 findings, 2 usage (a path that does not exist, an unreadable memory-types file).
Also the shared parser of memory_search.py, memory_write.py, metalearning.py and the memory hooks.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

sys.dont_write_bytecode = True  # importing the sibling modules must leave no __pycache__ behind (zero residue)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_config  # noqa: E402  (sibling module; `python3 -I` leaves the script directory off sys.path)
import boa_lock  # noqa: E402
import memory_types  # noqa: E402

SKEW_S = 300  # a datetime later than the real now + 5 minutes is in the future

BASE = ("brief", "datetime", "keywords", "type")
BANK_EXTRA = ("supersedes", "superseded-by")
DRAFT_EXTRA = ("supersedes", "supersedes-brief")
START, END, CUTOFF = "@@@memory", "@endmemory", "<!-- boa:memory-cutoff -->"
HEADER = re.compile(r"^@@@memory(?:-(\d+))?(?=\s|$)(.*)$")
ATTR = re.compile(r'\s+([a-z-]+)="([^"]*)"')
TASKISH = re.compile(r"(?<![A-Za-z0-9])[Tt]-?\d+[a-z]?(?![A-Za-z0-9])")
TASK = re.compile(r"T-\d{3,}[a-z]?")
MID = re.compile(r"memory-([1-9]\d*)")
LEDGER = ".memory-ids.jsonl"
HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.environ.get("BOA_ROOT") or os.path.dirname(HOME)  # the project (env BOA_ROOT overrides it)


@dataclass
class Block:
    path: str
    line: int
    id: int | None
    fields: dict[str, str]
    text: str
    end: int
    header: str = ""
    links: list[int] = field(default_factory=list)

    def when(self) -> datetime.datetime | None:
        return parse_datetime(self.fields.get("datetime", ""))

    @property
    def mid(self) -> str:
        return f"memory-{self.id}" if self.id else "(draft)"

    @property
    def current(self) -> bool:
        return not self.fields.get("superseded-by")


DATETIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")   # ASCII digits only


def parse_datetime(value: str) -> datetime.datetime | None:
    """A UTC datetime from exactly YYYY-MM-DDTHH:MM:SSZ in ASCII digits, or None (any other digit is refused; a
    real date and time: no leap second, no hour 24, no year 0). The fields go straight to datetime, the same result as
    strptime with that format for ASCII digits, without its cost: every search reads every block's datetime."""
    if not DATETIME.fullmatch(value):
        return None
    try:
        return datetime.datetime(int(value[0:4]), int(value[5:7]), int(value[8:10]), int(value[11:13]),
                                 int(value[14:16]), int(value[17:19]), tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def test_env(name: str) -> str | None:
    """A test-only variable: honoured ONLY when BOA_TEST_MODE=1 is set too, and every use is announced on stderr."""
    value = os.environ.get(name)
    if not value:
        return None
    if os.environ.get("BOA_TEST_MODE") != "1":
        print(f"memory: {name} ignored (test-only: it needs BOA_TEST_MODE=1)", file=sys.stderr)
        return None
    print(f"memory: WARNING test mode: {name}={value}", file=sys.stderr)
    return value


def real_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def now_stamp() -> str:
    """The datetime of a new block: the real now (UTC, seconds). BOA_MEMORY_NOW replaces it in test mode only."""
    env = test_env("BOA_MEMORY_NOW")
    if env:
        if not parse_datetime(env):
            raise ValueError("BOA_MEMORY_NOW must be YYYY-MM-DDTHH:MM:SSZ")
        return env
    return real_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def id_list(value: str) -> list[int] | None:
    """The ids of a `supersedes` value, or None when it is not a comma list of memory-N."""
    out = []
    for part in value.split(","):
        m = MID.fullmatch(part.strip())
        if not m:
            return None
        out.append(int(m.group(1)))
    return out


def parse_header(rest: str, drafts: bool) -> tuple[dict[str, str], list[str]]:
    fields: dict[str, str] = {}
    problems: list[str] = []
    pos = 0
    for m in ATTR.finditer(rest):
        if m.start() != pos:
            problems.append(f"unreadable header text '{rest[pos:m.start()].strip()[:40]}' (fields are key=\"value\")")
        key = m.group(1)
        if key in fields:
            problems.append(f"field '{key}' given twice")
        fields[key] = m.group(2)
        pos = m.end()
    if rest[pos:].strip():
        problems.append(f"unreadable header text '{rest[pos:].strip()[:40]}' (a value with a quote inside, or no quotes?)")
    allowed = BASE + (DRAFT_EXTRA if drafts else BANK_EXTRA)
    for k in fields:
        if k not in allowed:
            problems.append(f"unknown field '{k}' (fields: {', '.join(allowed)})")
    for k in BASE:
        if k not in fields:
            problems.append(f"missing field '{k}'")
    return fields, problems


def check_fields(fields: dict[str, str], names: list[str]) -> list[str]:
    out: list[str] = []
    brief = fields.get("brief")
    if brief is not None:
        if not brief.strip():
            out.append("brief is empty")
        elif len(brief) > 200:
            out.append(f"brief is {len(brief)} characters (one line, at most 200)")
    kw = fields.get("keywords")
    if kw is not None:
        if not kw.strip():
            out.append("keywords are empty (task ids, components, tools, error words)")
        for t in TASKISH.findall(kw):
            if not TASK.fullmatch(t):
                out.append(f"task id '{t}' in keywords: task ids are T-NNN (T- and at least three digits)")
    dt = fields.get("datetime")
    if dt is not None and parse_datetime(dt) is None:
        out.append(f"datetime '{dt}' is not exactly YYYY-MM-DDTHH:MM:SSZ (UTC, seconds; e.g. date -u +%Y-%m-%dT%H:%M:%SZ)")
    elif dt is not None and (parse_datetime(dt) - real_now()).total_seconds() > SKEW_S:
        out.append(f"datetime '{dt}' is in the future (later than now + {SKEW_S // 60} min): a datetime is never set by hand")
    typ = fields.get("type")
    if typ is not None and typ not in names:
        out.append(f"type '{typ}' is not one of {', '.join(names)} (.boa/memory-types.json)")
    for k in ("supersedes", "superseded-by"):
        if k in fields and (id_list(fields[k]) is None or (k == "superseded-by" and len(id_list(fields[k]) or []) != 1)):
            out.append(f"{k} '{fields[k]}' is not " + ("one memory id (memory-N)" if k == "superseded-by"
                                                         else "a comma list of memory ids (memory-12,memory-31)"))
    return out


def judged_lines(text: str) -> list[tuple[int, str]]:
    """(line number, line) of the lines the lint judges: after the cutoff marker (if any), outside fenced code."""
    lines = text.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if line.strip() == CUTOFF:
            start = i + 1
    out = []
    fence = False
    for i in range(start, len(lines)):
        if lines[i].lstrip().startswith("```"):
            fence = not fence
            continue
        if not fence:
            out.append((i + 1, lines[i]))
    return out


def legacy_ids(text: str) -> list[int]:
    """The ids of the `@@@memory-<N>` header lines before the file's last cutoff marker: legacy blocks the lint never
    judges and the ledger never adopts, whose ids are still taken (the next id is above them: no id twice)."""
    lines = text.splitlines()
    cut = max((i for i, line in enumerate(lines) if line.strip() == CUTOFF), default=0)   # no marker: none
    return [int(m.group(1)) for line in lines[:cut] for m in [HEADER.match(line.strip())] if m and m.group(1)]


def parse_blocks(path: str, text: str, names: list[str] | None = None, drafts: bool = False,
                 check: bool = True) -> tuple[list[Block], list[str]]:
    """(blocks, findings) of one file's text (the per-block checks; links are checked by check_links). check=False:
    the same blocks, no findings (the field checks skipped: what a search or a write that only reads the blocks
    needs)."""
    if names is None and check:
        names = memory_types.load().names
    blocks: list[Block] = []
    findings: list[str] = []
    cur: Block | None = None
    body: list[str] = []
    for n, line in judged_lines(text):
        stripped = line.strip()
        m = HEADER.match(stripped)
        if m:
            mid = int(m.group(1)) if m.group(1) else None
            if not check:
                cur, body = Block(path, n, mid, dict(ATTR.findall(m.group(2))), "", 0, stripped), []   # last wins
                continue
            if cur:
                findings.append(f"{path}:{n}: a block starts inside the block opened at line {cur.line} (no nesting; "
                                f"close it with {END})")
            fields, problems = parse_header(m.group(2), drafts)
            problems += check_fields(fields, names)
            if drafts and mid is not None:
                problems.append("a draft has no id (ids are assigned by memory_write.py --ingest)")
            if not drafts and mid is None:
                problems.append("the block has no id (@@@memory-<N>): write memories only through memory_write.py")
            if mid == 0:
                problems.append("ids start at memory-1")
            findings += [f"{path}:{n}: {p}" for p in problems]
            cur, body = Block(path, n, mid, fields, "", 0, stripped), []
        elif stripped == END:
            if not cur:
                if check:
                    findings.append(f"{path}:{n}: {END} with no open block")
                continue
            if check and not "\n".join(body).strip():
                findings.append(f"{path}:{cur.line}: the block has no text")
            cur.text, cur.end = "\n".join(body), n
            blocks.append(cur)
            cur = None
        elif cur:
            body.append(line)
    if cur and check:
        findings.append(f"{path}:{cur.line}: the block is not closed ({END} missing before the end of the file)")
    return blocks, findings


def sup(b: Block) -> list[int]:
    """The ids a block supersedes (empty when none or malformed)."""
    v = b.fields.get("supersedes")
    return (id_list(v) or []) if v else []


def succ_of(b: Block) -> int | None:
    v = b.fields.get("superseded-by")
    ids = id_list(v) if v else None
    return ids[0] if ids and len(ids) == 1 else None


def check_links(blocks: list[Block]) -> list[str]:
    out: list[str] = []
    by_id: dict[int, Block] = {}
    for b in blocks:
        if b.id is None:
            continue
        if b.id in by_id:
            first = by_id[b.id]
            out.append(f"{b.path}:{b.line}: id memory-{b.id} is used twice (also {first.path}:{first.line}); ids are never reused")
        else:
            by_id[b.id] = b
    last: dict[str, int] = {}
    for b in blocks:
        if b.id is None:
            continue
        if b.path in last and b.id < last[b.path]:
            out.append(f"{b.path}:{b.line}: memory-{b.id} comes after memory-{last[b.path]} in the file (ids are progressive)")
        last[b.path] = max(last.get(b.path, 0), b.id)
    succ: dict[int, int] = {}
    for b in by_id.values():
        for s in sup(b):
            if s not in by_id:
                out.append(f"{b.path}:{b.line}: memory-{b.id} supersedes memory-{s}, which does not exist")
                continue
            if s >= b.id:
                out.append(f"{b.path}:{b.line}: memory-{b.id} supersedes memory-{s}, which is not older (a memory replaces earlier ones)")
            target = by_id[s]
            tb, tt = b.when(), target.when()
            if tb and tt and tb <= tt:
                out.append(f"{b.path}:{b.line}: memory-{b.id} supersedes memory-{s} but is not newer (datetime "
                           f"{b.fields['datetime']} is not after {target.fields['datetime']}): supersession runs forward in time")
            if succ_of(target) != b.id:
                out.append(f"{target.path}:{target.line}: memory-{s} is superseded by memory-{b.id} but its tag says "
                           f"superseded-by=\"{target.fields.get('superseded-by', '')}\" (one-way supersession)")
            if s in succ and succ[s] != b.id:
                out.append(f"{b.path}:{b.line}: fork: memory-{s} is superseded twice (by memory-{succ[s]} and memory-{b.id}); a memory is superseded once")
            succ[s] = b.id
    for b in by_id.values():
        s = succ_of(b)
        if s is None:
            continue
        if s not in by_id:
            out.append(f"{b.path}:{b.line}: memory-{b.id} is superseded-by memory-{s}, which does not exist")
        elif b.id not in sup(by_id[s]):
            out.append(f"{b.path}:{b.line}: memory-{b.id} says superseded-by memory-{s}, but memory-{s} does not supersede it "
                       "(one-way supersession)")
    # cycles in the supersedes graph
    graph = {i: sup(b) for i, b in by_id.items()}
    state: dict[int, int] = {}

    def visit(i: int, path: list[int]) -> None:
        state[i] = 1
        for j in graph.get(i, []):
            if j not in graph:
                continue
            if state.get(j) == 1:
                cyc = path[path.index(j):] + [j] if j in path else [i, j]
                out.append(f"{by_id[i].path}:{by_id[i].line}: supersession cycle: {' -> '.join(f'memory-{x}' for x in cyc)}")
            elif j not in state:
                visit(j, path + [j])
        state[i] = 2

    for i in sorted(graph):
        if i not in state:
            visit(i, [i])
    return out


def special(path: str) -> str | None:
    """The finding for a path that exists and is not a regular file (a FIFO, a device, a socket, a directory; a link
    judged by its target) or cannot be checked, else None: one stat, never an open (a FIFO would hang the reader)."""
    import boa_tool
    try:
        kind = boa_tool.special_kind(path)
    except OSError as exc:
        return f"{path}: cannot be checked ({exc.strerror or exc}): not read"
    return f"{path}: {kind}, not a regular file: not read" if kind else None


def read_files(files: list[str]) -> tuple[dict[str, str], list[str], list[str]]:
    """(texts, findings, read errors) of the files to lint: a special file is a finding and is not read; a file that
    fails to read is an error line and lints as empty."""
    texts: dict[str, str] = {}
    findings: list[str] = []
    errors: list[str] = []
    for f in files:
        bad = special(f)
        if bad:
            findings.append(bad)
            continue
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                texts[f] = fh.read()
        except OSError as exc:
            texts[f] = ""
            errors.append(f"{f}: {exc.strerror or exc}")
    return texts, findings, errors


def read_ledger(path: str, text: str | None = None) -> tuple[dict[int, dict], list[str]]:
    """The ledger's entries by id (from `text` when given, else the file; a missing file: none; a special file: none
    and its finding, never opened)."""
    entries: dict[int, dict] = {}
    errs: list[str] = []
    if text is None:
        bad = special(path)
        if bad:
            return entries, [bad]
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except FileNotFoundError:
            return entries, errs
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            i = int(e["id"])
        except (ValueError, KeyError, TypeError):
            errs.append(f"{path}:{n}: not a ledger record")
            continue
        if i in entries:
            errs.append(f"{path}:{n}: memory-{i} is in the ledger twice")
        entries[i] = e
    return entries, errs


def check_ledger(blocks: list[Block], ledger_path: str, whole: bool, text: str | None = None,
                 present: bool | None = None) -> list[str]:
    if present is None:
        present = text is not None or os.path.exists(ledger_path)
    if not present:
        if any(b.id for b in blocks):
            return [f"{ledger_path}: no id ledger: run `memory_write.py --seed` once to adopt the existing ids"]
        return []
    if text is None and special(ledger_path):
        return [str(special(ledger_path))]   # never opened; its blocks are not judged against a ledger not read
    entries, out = read_ledger(ledger_path, text)
    ids = {b.id for b in blocks if b.id}
    for b in blocks:
        if b.id and b.id not in entries:
            out.append(f"{b.path}:{b.line}: memory-{b.id} is not in the id ledger (a hand-written id): write memories "
                       "only through memory_write.py")
    if whole:
        bank = os.path.normcase(os.path.realpath(os.path.dirname(ledger_path)))
        for i in sorted(entries):
            stored = os.path.normcase(os.path.realpath(boa_lock.from_posix(ROOT, str(entries[i].get("file", "")))))
            in_bank = stored.startswith(bank + os.sep)
            if i not in ids and in_bank and not entries[i].get("void"):
                out.append(f"{ledger_path}: memory-{i} ({entries[i].get('file', '?')}) is in the id ledger but its block "
                           "is missing (orphan)")
    return out


def files_of(paths: list[str]) -> list[str]:
    out: list[str] = []
    for p in paths:
        if os.path.isdir(p):
            for cur, dirs, names in os.walk(p):
                dirs.sort()
                out += [os.path.join(cur, n) for n in sorted(names) if n.endswith(".md")]
        else:
            out.append(p)
    return out


def memory_dir(root: str = ROOT) -> str:
    return os.path.join(root, boa_config.load().get("BOA_MEMORY_DIR", "memory-bank"))


def lint_texts(texts: dict[str, str], names: list[str], drafts: bool, ledger: str | None,
               whole: bool, ledger_text: str | None = None, ledger_present: bool | None = None) -> tuple[list[Block], list[str]]:
    blocks: list[Block] = []
    findings: list[str] = []
    for path, text in texts.items():
        b, f = parse_blocks(path, text, names, drafts)
        blocks += b
        findings += f
    if not drafts:
        findings += check_links(blocks)
        if ledger:
            findings += check_ledger(blocks, ledger, whole, ledger_text, ledger_present)
    return blocks, findings


def staged_key(root: str, gitpath: str, pathmod=os.path) -> str:
    """The key of a staged file: git's `/` path joined to the root with the platform's separators, normalised, so it
    compares equal to `pathmod.join(mdir, LEDGER)` normalised the same way on every platform."""
    return boa_lock.from_posix(root, gitpath, pathmod)


def staged_texts(root: str, mdir: str) -> dict[str, str]:
    rel = boa_lock.posix_rel(mdir, root)
    out = subprocess.run(["git", "-C", root, "ls-files", "-z", "--", rel], capture_output=True, check=True).stdout
    texts: dict[str, str] = {}
    for p in out.decode().split("\0"):
        if p.endswith(".md") or p.endswith(LEDGER):
            shown = subprocess.run(["git", "-C", root, "show", f":{p}"], capture_output=True)
            if shown.returncode == 0:
                texts[staged_key(root, p)] = shown.stdout.decode("utf-8", "replace")
    return texts


def main(argv: list[str]) -> int:
    drafts = staged = no_ledger = False
    ledger: str | None = None
    paths: list[str] = []
    it = iter(argv)
    for a in it:
        if a == "--drafts":
            drafts = True
        elif a == "--staged":
            staged = True
        elif a == "--no-ledger":
            no_ledger = True
        elif a == "--ledger":
            ledger = next(it, None)
            if not ledger:
                print("memory-lint: --ledger needs a file", file=sys.stderr)
                return 2
        elif a.startswith("-"):
            print("usage: memory_lint.py [--drafts] [--ledger FILE | --no-ledger] [--staged] [path...]", file=sys.stderr)
            return 2
        else:
            paths.append(a)
    try:
        names = memory_types.load().names
    except memory_types.TypesError as exc:
        print(f"memory-lint: {exc}", file=sys.stderr)
        return 2
    try:
        mdir = memory_dir()
    except (boa_config.ConfigError, OSError, UnicodeDecodeError) as exc:   # one line naming the bad line, no traceback
        print(f"memory-lint: config: {exc}", file=sys.stderr)
        return 2
    whole = False
    if staged:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if top.returncode != 0:
            print("memory-lint: --staged needs a git checkout", file=sys.stderr)
            return 2
        root = top.stdout.strip()
        mdir = os.path.normpath(os.path.join(root, os.path.relpath(memory_dir(), ROOT)))
        texts = staged_texts(root, mdir)
        ledger_text = texts.pop(os.path.normpath(os.path.join(mdir, LEDGER)), None)
        blocks, findings = lint_texts(texts, names, drafts, None if no_ledger else os.path.join(mdir, LEDGER), True,
                                      ledger_text, ledger_text is not None)
        files = list(texts)
    else:
        if not paths:
            paths, whole = [mdir], True
        missing = [p for p in paths if not os.path.exists(p)]
        if missing:
            print(f"memory-lint: not found: {', '.join(missing)}", file=sys.stderr)
            return 2
        real_mdir = os.path.realpath(mdir)
        if len(paths) == 1 and os.path.realpath(paths[0]) == real_mdir:
            whole = True
        if ledger is None and not no_ledger and not drafts and all(
                os.path.realpath(p) == real_mdir or os.path.realpath(p).startswith(real_mdir + os.sep) for p in paths):
            ledger = os.path.join(mdir, LEDGER)
        if no_ledger:
            ledger = None
        files = files_of(paths)
        texts, unread, errors = read_files(files)
        for e in errors:
            print(e)
        blocks, findings = lint_texts(texts, names, drafts, ledger, whole)
        findings = unread + findings
    for e in findings:
        print(e)
    print(f"memory-lint: {len(blocks)} block(s) in {len(files)} file(s), {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
