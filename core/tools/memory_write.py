#!/usr/bin/env python3
"""Memory writer: the ONLY way a memory gets an id, a place and its supersession links.

  python3 -I .boa/tools/memory_write.py --type T --brief B --keywords K [--text TEXT] [--supersedes memory-12,...]
                                        [--file PATH]
      Writes one memory: the next id of the global sequence, `datetime` = now (UTC, seconds), the file chosen by the
      type and its keywords through `.boa/memory-types.json` (keyword routes first, the highest priority wins:
      `owner-rule` -> 08 (100), `plan-row` -> 03 (90), `security` -> 07 (50); else the type's route), under the file's
      `## Memories — …` section (created at the end of the file when missing); `--file` overrides the route
      (documented exceptions only). The text comes from --text, else stdin. Every superseded id must exist and be
      current; each one gets `superseded-by="memory-N"` (the only edit ever made to an existing block). Prints
      `memory-N <file>`.
  After a write or an ingest it starts a detached child that caches the memory search vector of each memory written
  (memory_search.py --warm-ids, through the environment `boa install` builds; its output in
  <BOA_LOG_DIR>/memory-vectors.log) and returns without waiting; `--no-vectors` skips it. Best effort: with no
  environment it prints one `memory-write: memory search vectors not computed …` line on stderr and the write stands
  (the search computes missing vectors itself).
  python3 -I .boa/tools/memory_write.py --format-only --type T --brief B --keywords K [--text TEXT]
                                        [--supersedes memory-12,...] [--supersedes-brief "<brief> | <brief>"]
      Prints a draft (an id-less block) without touching the bank or the sequence: for an agent's report trace or a
      lane's `.lane-resume/memories.md`; `--ingest` gives it its id later.
  python3 -I .boa/tools/memory_write.py --ingest FILE...
      Reads the drafts of the files (in the order given; a lead staging file — a file in the main checkout's
      <BOA_LEAD_DIR>, also when the fold runs from a train worktree: metalearning inbox, owner rules, plan additions
      — under its lock, only the lines BELOW its last `# … Folded by …` marker, the part not folded yet). Idempotent: the ledger records each ingested draft's content hash (`draft_sha256`, of
      its canonical form: header fields in a fixed order, body lines without trailing whitespace, line endings
      normalised); a draft already ingested (a live id) is skipped and reported (`skipped "<brief>" (<file>:
      <line>): already ingested as memory-N`), as is a second identical draft of the batch, so a lane or a staging file
      read again never duplicates a memory; a `supersedes-brief` naming a skipped draft names its final id. Validates
      every one (memory_lint --drafts rules, a datetime in the future refused), resolves their supersession —
      `supersedes` = final ids (current ones), `supersedes-brief` = the brief of another draft of the same batch (a
      referenced brief must name exactly one draft; two identical unreferenced drafts are fine) —, assigns ids so that
      they ascend with time wherever the dependencies allow (among the drafts ready, the oldest first: datetime, then
      file order, then line), routes each by type, stamps superseded-by on every target (in any file), appends the
      ids to the ledger, and prints one `memory-N <- "<brief>" (<file>)` line per draft. All or nothing: an unknown
      id or brief, an ambiguous referenced brief, a fork, a cycle, a superseding draft not newer than its target, or
      superseding a memory that is already superseded (the message names the current head) refuses the whole batch
      and writes nothing. It NEVER modifies or deletes the draft files: lane drafts go with the lane's worktree once
      its fold has landed; the lead marks a staging file folded after the merge.
      Only the integrator's train fold runs it, inside ONE docs(memory) commit: the lead's staging files first, then
      the lanes' files in train order, in one call; the fork and chain checks span the whole batch. Ids assigned in a
      fold that is discarded never existed: a rebuilt fold starts again from main's ledger.
      With `--receipt PATH` (outside the memory bank; there is no default) it also writes an ingest receipt (also when
      every draft was skipped): per file read, `staging` (true for a lead staging file), `lines` = N, the 1-based
      number of the last draft line it read, and `sha256` = the hash of the WHOLE prefix, lines 1..N (each line's text
      without its line ending, `\n`-terminated): a later edit anywhere in that prefix is detected. A receipt path
      that exists and is not a regular file (a device, a FIFO, a socket, a directory; a symbolic link judged by its
      target) is refused before anything is read or written: the receipt is renamed into place, which would replace
      it with a regular file; so is a receipt that is one of the files to ingest or whose directory does not exist,
      and a path that cannot be checked (a parent that is a file, a symbolic link loop). An input file of --ingest,
      or the receipt of --mark, that exists and is not a regular file (a device, a FIFO, a socket, a directory) or
      cannot be checked is refused before it is read: nothing waits or reads forever. So is every file of the
      memory bank a write reads (the memory files, the id ledger, the --file target).
  python3 -I .boa/tools/memory_write.py --mark RECEIPT --train TRAIN-NNN
      After the fold has landed: inserts `# [<UTC now>] Folded by TRAIN-NNN: everything above. Pending below.` right
      AFTER line N (the receipt's last line read) in each STAGING file, under that file's lock, with the file's own
      line endings (CRLF stays CRLF), so drafts appended after the fold stay below the marker (the next fold reads
      them). Lane files are never marked: one still there is reported "not a staging file", one gone (its worktree
      removed) "gone, nothing to mark". All or nothing, refused only when a staging file is missing or its lines 1..N
      no longer match the recorded prefix hash. Running it again is a no-op ("already marked") for a file whose line
      N is already followed by this train's marker. The lead never edits a staging file by hand while --mark runs
      (an editor's save is not under the lock; tools that append, like metalearning.py, take it).
  python3 -I .boa/tools/memory_write.py --seed
      Adopts the ids of an existing memory bank (blocks after the cutoff) into a new ledger; refused when ids
      collide, the ledger exists, or no valid id is found (no ledger written; the message names the blocks it
      could not read: lint findings, a header before the cutoff or in a fenced code block). Every write seeds a
      missing ledger first, so the sequence starts right.
  python3 -I .boa/tools/memory_write.py --repair-ledger [--adopt memory-N[,memory-M] --reason "…"]
      Recovery after an interrupted write (see "Crash safety"): voids every ledger id whose block is missing (`void`:
      the id stays reserved, never reused), stamps a superseded memory whose stamp the interruption left out (only
      when both ids were in the ledger before the repair), and drops a stamp whose superseding block was never
      written; prints one line per change and a summary. A bank id missing from the ledger is never crash damage
      (the ledger is renamed first): the repair is refused, naming each one, unless every such block is adopted
      explicitly with --adopt and a --reason (recorded as `assigned_by: "adopted: <reason>"`; the block must pass the
      field checks and may not declare supersedes). Refused when bank ids collide.

The id ledger `<memory bank>/.memory-ids.jsonl` (one JSON line per assigned id: id, file, brief, datetime,
assigned_by, and draft_sha256 for an ingested draft) travels with git; only this tool writes it, under an exclusive
lock (`<BOA_STATE_DIR>/memory.lock`).
memory_lint refuses a block whose id is not in it and an id whose block is missing. Ids: the next is the highest of the
ledger and the bank plus one; never reused. `--file` must name a file inside the memory bank (relative to the
project root). The ledger stores `file` with `/` separators on every platform.
Crash safety: every check runs first; then every file is written to a temp file; then the LEDGER is renamed into
place first and the bank files after it. An interruption after the ledger leaves ids without blocks — harmless (the
ids are only reserved; memory_lint reports them as orphans); a later one leaves a new block whose target in another
file lacks its stamp (memory_lint: one-way supersession). Recovery: run `memory_lint.py`; for orphans or a missing
stamp run `memory_write.py --repair-ledger`, then lint again, then redo the write (or the fold) that was interrupted —
new ids follow the voided ones, and a fold run again skips the drafts already ingested. Ids missing from the ledger
are hand-written blocks, not crash damage: --repair-ledger refuses them (see --adopt). Leftover `*.tmp.<pid>` files
of the interrupted write may be deleted. The lock is portable (boa_lock.FileLock: fcntl or msvcrt; a platform with
neither is refused). The lead dir and the state dir (locks) are the MAIN checkout's, also when --root is a worktree.
Supersession runs forward in time: a superseding memory's datetime must be strictly later than every memory it
supersedes (and it gets a higher id); otherwise the write is refused (a clock problem — a datetime is never set by
hand); a datetime later than the real now + 5 minutes is refused too. Exit: 0 written, 1 refused, 2 usage.
Environment (tests only, honoured only with BOA_TEST_MODE=1 and announced on stderr at every use): BOA_MEMORY_NOW
(the datetime of new blocks), BOA_MEMORY_FAIL_AFTER=<n> (stop after n renames: crash tests).
Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True  # importing the sibling modules must leave no __pycache__ behind (zero residue)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_config  # noqa: E402  (sibling module; `python3 -I` leaves the script directory off sys.path)
import boa_lock  # noqa: E402
import markers  # noqa: E402
import memory_lint as ml  # noqa: E402
import memory_types  # noqa: E402


class Refused(Exception):
    pass


def replaceable(path: str) -> None:
    """Refused when `path` exists and is not a regular file: every write here renames a temp file onto its target,
    which would replace a device, a FIFO, a socket or a directory with a regular file (boa_tool.check_replaceable).
    A path that cannot be checked (a parent that is a file, a symbolic link loop, no permission) is refused too."""
    import boa_tool
    try:
        boa_tool.check_replaceable(path)
    except boa_tool.NotRegularFile as exc:
        raise Refused(str(exc)) from exc
    except OSError as exc:
        raise Refused(f"{path}: cannot be checked ({exc.strerror or exc}): not written") from exc


def readable(path: str, what: str) -> None:
    """Refused when the input `path` exists and is not a regular file: checked before any read, so a FIFO or an endless
    device never makes the tool wait or read forever (a missing file is left to the read's own message; a path that
    cannot be checked — a parent that is a file, a symbolic link loop, no permission — is refused)."""
    import boa_tool
    try:
        kind = boa_tool.special_kind(path)
    except OSError as exc:
        raise Refused(f"{what} {path}: cannot be checked ({exc.strerror or exc}): not read") from exc
    if kind is not None:
        raise Refused(f"{what} {path} is {kind}, not a regular file: not read")


def same_file(a: str, b: str) -> bool:
    """`a` and `b` are one file: by device and inode when both exist (a hard link included), else by real path."""
    if os.path.exists(a) and os.path.exists(b):
        try:
            return os.path.samefile(a, b)
        except OSError:
            return False
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def clean(v: str) -> str:
    return re.sub(r"\s+", " ", v.replace('"', "'")).strip()


def render(fields: dict[str, str], text: str, mid: int | None = None) -> str:
    head = ml.START + (f"-{mid}" if mid else "")
    order = ["brief", "datetime", "keywords", "type", "supersedes", "supersedes-brief", "superseded-by"]
    attrs = " ".join(f'{k}="{fields[k]}"' for k in order if fields.get(k))
    return f"{head} {attrs}\n{text.rstrip()}\n{ml.END}\n"


class Bank:
    """The memory bank (files and parsed blocks), the ledger and the pending writes."""

    def __init__(self, root: str):
        cfg = boa_config.load()
        self.root = root
        self.dir = os.path.join(root, cfg.get("BOA_MEMORY_DIR", "memory-bank"))
        self.ledger = os.path.join(self.dir, ml.LEDGER)
        main = boa_config.main_of(root)   # a fold may run from a train worktree: lead and state dirs are the main's
        self.state = os.path.join(main, cfg.get("BOA_STATE_DIR", ".boa/state"))
        self.lead = os.path.join(main, cfg.get("BOA_LEAD_DIR", ".lead"))
        self.types = memory_types.load()
        self.texts: dict[str, str] = {}
        self.blocks: list[ml.Block] = []
        self.new_ledger: list[dict] = []
        self.held: boa_lock.FileLock | None = None
        self.new_files: set[str] = set()   # files that receive a new block: renamed before the ones only stamped

    def lock(self) -> None:
        """The bank's exclusive lock, held until unlock() (portable: boa_lock.FileLock)."""
        self.held = boa_lock.FileLock(os.path.join(self.state, "memory.lock")).__enter__()

    def unlock(self) -> None:
        """Release the lock (process exit releases it too)."""
        if self.held:
            self.held.__exit__(None, None, None)
            self.held = None

    def load(self, extra: list[str] = ()) -> None:
        files = ml.files_of([self.dir]) if os.path.isdir(self.dir) else []
        for f in list(files) + [x for x in extra if x not in files and os.path.exists(x)]:
            readable(f, "the memory file")   # one stat before the open: a FIFO never hangs the write
            with open(f, encoding="utf-8") as fh:
                self.texts[f] = fh.read()
            self.blocks += ml.parse_blocks(f, self.texts[f], check=False)[0]
        readable(self.ledger, "the id ledger")
        self.entries, errs = ml.read_ledger(self.ledger)
        if errs:
            raise Refused("; ".join(errs))

    def seed_if_missing(self, explicit: bool = False) -> int:
        if os.path.exists(self.ledger):
            if explicit:
                raise Refused(f"{self.ledger} exists already: nothing to seed")
            return 0
        seen: dict[int, ml.Block] = {}
        for b in self.blocks:
            if not b.id:   # no id, or memory-0 (ids start at memory-1: the lint refuses it)
                continue
            if b.id in seen:
                raise Refused(f"cannot seed the ledger: memory-{b.id} is used twice ({seen[b.id].path}:{seen[b.id].line} "
                              f"and {b.path}:{b.line}); fix the ids first")
            seen[b.id] = b
        for i in sorted(seen):
            b = seen[i]
            self.new_ledger.append({"id": i, "file": boa_lock.posix_rel(b.path, self.root), "brief": b.fields.get("brief", ""),
                                    "datetime": b.fields.get("datetime", ""), "assigned_by": "seed"})
            self.entries[i] = self.new_ledger[-1]
        return len(seen)

    def next_id(self) -> int:
        """Above every id of the ledger and the bank, the legacy ids before a cutoff marker included (never reused)."""
        legacy = [i for text in self.texts.values() for i in ml.legacy_ids(text)]
        return max([0] + list(self.entries) + [b.id for b in self.blocks if b.id] + legacy) + 1

    def by_id(self) -> dict[int, ml.Block]:
        return {b.id: b for b in self.blocks if b.id}

    def is_staging(self, path: str) -> bool:
        """A lead staging file (metalearning inbox, owner rules, plan additions): a file in the lead directory."""
        lead = os.path.normcase(os.path.realpath(self.lead))
        return os.path.normcase(os.path.realpath(path)).startswith(lead + os.sep)

    def target(self, typ: str, keywords: str, override: str | None) -> str:
        if override:
            if os.path.isabs(override) or override.startswith(("/", "\\")):
                raise Refused(f"--file {override}: a path relative to the project root, inside the memory bank")
            path = os.path.normpath(os.path.join(self.root, override))
            bank = os.path.normcase(os.path.realpath(self.dir))
            if not os.path.normcase(os.path.realpath(path)).startswith(bank + os.sep) or not path.endswith(".md"):
                raise Refused(f"--file {override}: must be a .md file inside the memory bank ({boa_lock.posix_rel(self.dir, self.root)}/)")
            return path
        return os.path.join(self.dir, self.types.route(typ, keywords))

    def insert(self, path: str, blocks: list[str]) -> None:
        """Append the blocks, in their order, at the end of the file's `## Memories` section (after the legacy cutoff,
        created when missing), and never before a block already in the file (ids stay progressive in each file).
        Several blocks for one file go in one pass — the place is found once, with one parse of the file, not one per
        block (a bulk ingest stays linear) — giving the same bytes as one block at a time, which it falls back to
        where the two could differ: the place inside a fenced code block, or a block holding the cutoff line."""
        text = self.texts.get(path)
        if text is None:
            text = f"# {os.path.splitext(os.path.basename(path))[0]}\n\n## Memories\n"
        lines = text.splitlines(keepends=True)
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        cut = max((i for i, x in enumerate(lines) if x.strip() == ml.CUTOFF), default=-1)
        start = next((i for i, x in enumerate(lines) if i > cut and x.startswith("## Memories")), None)
        if start is None:
            lines += ["\n", "## Memories\n"]
            start = len(lines) - 1
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        last = max((b.end for b in ml.parse_blocks(path, "".join(lines), check=False)[0]), default=0)
        if last > end:
            end = last
        while end > start + 1 and not lines[end - 1].strip():
            end -= 1
        # one block at a time, the next one lands right after the previous one: unless the place is inside a fenced
        # code block (the parse would not see the block just added) or a block moves the cutoff (and the section)
        fenced = sum(1 for x in lines[cut + 1:end] if x.lstrip().startswith("```")) % 2 == 1
        if len(blocks) > 1 and (fenced or any(x.strip() == ml.CUTOFF for b in blocks[:-1] for x in b.splitlines())):
            for b in blocks:
                self.insert(path, [b])
            return
        lines[end:end] = [x for b in blocks for x in ("\n", b)]
        self.texts[path] = "".join(lines)
        self.new_files.add(path)

    def stamp(self, pairs: list[tuple[ml.Block, int]]) -> None:
        """Stamp `superseded-by="memory-<succ>"` on each (target, succ), one rewrite per file."""
        by_path: dict[str, list[tuple[ml.Block, int]]] = {}
        for target, succ in pairs:
            by_path.setdefault(target.path, []).append((target, succ))
        for path, todo in by_path.items():
            lines = self.texts[path].splitlines(keepends=True)
            for target, succ in todo:
                i = target.line - 1
                nl = "\n" if lines[i].endswith("\n") else ""
                lines[i] = lines[i].rstrip("\n") + f' superseded-by="memory-{succ}"' + nl
                target.fields["superseded-by"] = f"memory-{succ}"
            self.texts[path] = "".join(lines)

    def commit(self, touched: set[str], ledger_text: str | None = None) -> None:
        """Lint the result, write every file to a temp file, then rename the LEDGER first and the bank files after it
        (an interruption in between leaves reserved ids without blocks: harmless, see the docstring's recovery). The
        files that receive a new block go before the files that are only stamped, so a later interruption leaves a
        new block whose target lacks its stamp — which --repair-ledger completes."""
        findings = ml.check_links(self.reparse(touched))
        if findings:
            raise Refused("the result would not lint: " + "; ".join(findings[:5]))
        for path in ([self.ledger] if self.new_ledger or ledger_text is not None else []) + sorted(touched):
            replaceable(path)   # before any temp file: a refusal writes nothing
        tmp: list[tuple[str, str]] = []
        try:
            if self.new_ledger or ledger_text is not None:
                t = f"{self.ledger}.tmp.{os.getpid()}"
                if ledger_text is None:
                    ledger_text = ""
                    if os.path.exists(self.ledger):
                        with open(self.ledger, encoding="utf-8") as fh:
                            ledger_text = fh.read()
                    ledger_text += "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in self.new_ledger)
                os.makedirs(os.path.dirname(self.ledger), exist_ok=True)
                with open(t, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(ledger_text)
                tmp.append((t, self.ledger))
            for path in sorted(touched, key=lambda p: (p not in self.new_files, p)):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                t = f"{path}.tmp.{os.getpid()}"
                with open(t, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(self.texts[path])
                tmp.append((t, path))
        except OSError:
            for t, _ in tmp:
                if os.path.exists(t):
                    os.unlink(t)
            raise
        fail_after = ml.test_env("BOA_MEMORY_FAIL_AFTER")
        for n, (t, path) in enumerate(tmp):
            if fail_after is not None and n >= int(fail_after):
                print(f"memory-write: test mode: stopping after {n} rename(s) (BOA_MEMORY_FAIL_AFTER)", file=sys.stderr)
                raise SystemExit(70)
            os.replace(t, path)

    def reparse(self, touched: set[str]) -> list[ml.Block]:
        blocks: list[ml.Block] = []
        for path, text in self.texts.items():
            blocks += ml.parse_blocks(path, text, check=False)[0]
        return blocks


def nothing_to_seed(bank: Bank) -> str:
    """Why --seed found no id to adopt, naming the blocks it did not read: to fix — the lint's findings, and every
    `@@@memory` line in a fenced code block or with a malformed header — and the legacy ones, before the cutoff
    marker, which are never adopted (by design: the cutoff exempts them)."""
    fix: list[str] = []
    legacy: list[str] = []
    for path, text in bank.texts.items():
        rel = boa_lock.posix_rel(path, bank.root)
        blocks, findings = ml.parse_blocks(path, text, bank.types.names)
        fix += [f.replace(path, rel, 1) for f in findings]
        read = {b.line for b in blocks if b.id}
        named = {f[len(path) + 1:].split(":")[0] for f in findings if f.startswith(path + ":")}   # their lines
        lines = text.splitlines()
        cut = max((n for n, x in enumerate(lines, 1) if x.strip() == ml.CUTOFF), default=0)
        for n, x in enumerate(lines, 1):
            if x.strip().startswith(ml.START) and n not in read and str(n) not in named:
                if n < cut:
                    legacy.append(f"{rel}:{n}")
                else:
                    fix.append(f"{rel}:{n}: not read as a memory block (in a fenced code block, or a malformed header)")
    out = f"no valid memory id in {boa_lock.posix_rel(bank.dir, bank.root)}/: nothing to seed, no ledger written"
    if not fix and not legacy:
        return out + " (the memory bank holds no @@@memory-<N> block)"
    if fix:
        more = f" (+{len(fix) - 5} more)" if len(fix) > 5 else ""
        out += ("; the blocks to fix: " + "; ".join(fix[:5]) + more
                + ". Fix them (memory_lint.py lists every finding), then run --seed again")
    if legacy:
        more = f" (+{len(legacy) - 5} more)" if len(legacy) > 5 else ""
        out += (f"; {len(legacy)} legacy block(s) before the cutoff marker ({', '.join(legacy[:5])}{more}) are never "
                "adopted: that is what the cutoff is for — new memories go through memory_write.py")
    return out


def check_draft(fields: dict[str, str], text: str, names: list[str]) -> None:
    problems = ml.check_fields(fields, names)
    for k in ml.BASE:
        if not fields.get(k):
            problems.append(f"{k} is required")
    if not text.strip():
        problems.append("the memory has no text")
    if problems:
        raise Refused("; ".join(problems))


def chain_head(by_id: dict[int, ml.Block], b: ml.Block) -> str:
    """The current memory reached by following superseded-by from b (or where the chain breaks)."""
    seen = set()
    while not b.current:
        s = ml.succ_of(b)
        if s is None or s not in by_id or s in seen:
            return f"memory-{s} (a broken chain: run memory_lint.py)"
        seen.add(s)
        b = by_id[s]
    return f"memory-{b.id}"


def resolve_targets(bank: Bank, ids: list[int], by_id: dict[int, ml.Block] | None = None) -> list[ml.Block]:
    by_id = bank.by_id() if by_id is None else by_id
    out = []
    for i in ids:
        b = by_id.get(i)
        if b is None or i not in bank.entries:
            raise Refused(f"memory-{i} does not exist (not in the bank and the ledger)")
        if not b.current:
            head = chain_head(by_id, b)
            raise Refused(f"memory-{i} is already superseded (by {b.fields['superseded-by']}); the current head of its "
                          f"chain is {head}: supersede {head} instead (a memory is superseded once)")
        out.append(b)
    return out


def write_one(bank: Bank, a: argparse.Namespace, text: str) -> str:
    fields = {"brief": clean(a.brief), "datetime": ml.now_stamp(), "keywords": clean(a.keywords), "type": a.type}
    check_draft(fields, text, bank.types.names)
    ids = ml.id_list(a.supersedes) if a.supersedes else []
    if ids is None:
        raise Refused(f"--supersedes '{a.supersedes}' is not a comma list of memory ids")
    ids = sorted(set(ids))
    targets = resolve_targets(bank, ids)
    for t in targets:
        if fields["datetime"] <= t.fields.get("datetime", ""):
            raise Refused(f"the new memory's datetime {fields['datetime']} is not after {t.mid}'s "
                          f"{t.fields.get('datetime')}: supersession runs forward in time (a clock problem: check "
                          "the host clock; a datetime is never set by hand)")
    mid = bank.next_id()
    if ids:
        fields["supersedes"] = ",".join(f"memory-{i}" for i in ids)
    path = bank.target(a.type, fields["keywords"], a.file)
    if path not in bank.texts and os.path.exists(path):
        readable(path, "the memory file")
        with open(path, encoding="utf-8") as fh:
            bank.texts[path] = fh.read()
    bank.insert(path, [render(fields, text, mid)])
    touched = {path}
    bank.stamp([(t, mid) for t in targets])
    touched.update(t.path for t in targets)
    bank.new_ledger.append({"id": mid, "file": boa_lock.posix_rel(path, bank.root), "brief": fields["brief"],
                            "datetime": fields["datetime"], "assigned_by": "memory_write"})
    bank.commit(touched)
    return f"memory-{mid} {boa_lock.posix_rel(path, bank.root)}"




def unfolded(text: str) -> str:
    """The text below the last `# … Folded by …` marker (lines above it blanked, so line numbers stay true)."""
    lines = text.splitlines(keepends=True)
    # the fold marker: every accepted text of markers.json (--mark writes it in English), loaded only here, so a bad
    # markers file never stops --format-only or a plain write
    try:
        fold = markers.fold_regex()
    except markers.MarkersError as exc:
        raise Refused(f"markers: {exc}") from None
    last = max((i for i, x in enumerate(lines) if fold.match(x)), default=-1)
    return "".join("\n" if i <= last else x for i, x in enumerate(lines))


FIELD_ORDER = ["brief", "datetime", "keywords", "type", "supersedes", "supersedes-brief", "superseded-by"]


def draft_hash(b: ml.Block) -> str:
    """sha256 of a draft's canonical form, so the same draft is recognised however it was spaced or saved: its parsed
    header fields as `key=value` lines in a fixed order (datetime included; whitespace in a value collapsed), a blank
    line, then its body lines with trailing whitespace stripped (line endings normalised, outer blank lines dropped)."""
    keys = [k for k in FIELD_ORDER if k in b.fields] + sorted(k for k in b.fields if k not in FIELD_ORDER)
    head = [f"{k}={' '.join(b.fields[k].split())}" for k in keys]
    body = "\n".join(x.rstrip() for x in b.text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip("\n")
    return hashlib.sha256(("\n".join(head) + "\n\n" + body + "\n").encode("utf-8")).hexdigest()


def prefix_hash(lines: list[str]) -> str:
    """sha256 of lines (each without its line ending, `\n`-terminated): one ingested prefix, ending-agnostic."""
    return hashlib.sha256("".join(x.rstrip("\r\n") + "\n" for x in lines).encode("utf-8")).hexdigest()


def read_draft_file(bank: Bank, f: str) -> str:
    """A draft file's text; a staging file is read under its lock (an append in progress is never half-read)."""
    readable(f, "the input")
    try:
        if bank.is_staging(f):
            with boa_lock.FileLock(boa_lock.lock_path(bank.state, f)), open(f, encoding="utf-8") as fh:
                return fh.read()
        with open(f, encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        raise Refused(f"{f}: {exc.strerror or exc}") from exc


def ingest(bank: Bank, files: list[str], receipt: str | None = None) -> list[str]:
    drafts: list[tuple[str, ml.Block]] = []
    raw: dict[str, list[str]] = {}
    found: list[tuple[str, ml.Block]] = []
    for f in files:
        full = read_draft_file(bank, f)
        raw[f] = full.splitlines()
        blocks, findings = ml.parse_blocks(f, unfolded(full), bank.types.names, drafts=True)
        if findings:
            raise Refused("; ".join(findings[:5]))
        found += [(f, b) for b in blocks]
    # idempotency: a draft whose content the ledger already records (a live id) is skipped, never ingested twice
    by_id = bank.by_id()
    known = {e["draft_sha256"]: i for i, e in sorted(bank.entries.items())
             if e.get("draft_sha256") and not e.get("void") and i in by_id}
    skips: list[str] = []
    skipped: dict[str, list[int]] = {}   # brief -> the final ids of the skipped drafts with that brief
    first: dict[str, tuple[str, ml.Block]] = {}
    digest: dict[int, str] = {}
    for f, b in found:
        h = draft_hash(b)
        if h in known:
            skipped.setdefault(b.fields["brief"], []).append(known[h])
            skips.append(f"skipped \"{b.fields['brief']}\" ({f}:{b.line}): already ingested as memory-{known[h]}")
        elif h in first:
            skips.append(f"skipped \"{b.fields['brief']}\" ({f}:{b.line}): the same draft as {first[h][0]}:{first[h][1].line}")
        else:
            first[h] = (f, b)
            digest[len(drafts)] = h
            drafts.append((f, b))
    if not drafts:
        return skips + ["memory-write: no new draft to ingest"] + (
            [write_receipt(bank, receipt, files, found, raw, [])] if receipt else [])
    briefs: dict[str, list[int]] = {}
    for n, (_, b) in enumerate(drafts):
        briefs.setdefault(b.fields["brief"], []).append(n)
    deps: dict[int, list[int]] = {}
    finals: dict[int, list[int]] = {}
    for n, (f, b) in enumerate(drafts):
        sb = [x.strip() for x in b.fields.get("supersedes-brief", "").split(" | ") if x.strip()]
        ids = ml.id_list(b.fields["supersedes"]) if b.fields.get("supersedes") else []
        if ids is None:
            raise Refused(f"{f}:{b.line}: supersedes '{b.fields['supersedes']}' is not a comma list of final ids")
        for x in [x for x in sb if x in skipped]:
            # a brief of an already-ingested draft (a re-read lane) names its final id
            if x in briefs or len(skipped[x]) > 1:
                raise Refused(f"{f}:{b.line}: supersedes-brief \"{x}\" is ambiguous: it names a draft of this batch "
                              f"or an already-ingested one ({', '.join(f'memory-{i}' for i in skipped[x])})")
            ids.append(skipped[x][0])
        sb = [x for x in sb if x not in skipped]
        for x in sb:
            if x not in briefs:
                raise Refused(f"{f}:{b.line}: supersedes-brief \"{x}\" names no draft of this batch")
            if len(briefs[x]) > 1:
                where = ", ".join(f"{drafts[k][0]}:{drafts[k][1].line}" for k in briefs[x])
                raise Refused(f"{f}:{b.line}: supersedes-brief \"{x}\" is ambiguous: {len(briefs[x])} drafts of the batch "
                              f"have that brief ({where})")
            if briefs[x][0] == n:
                raise Refused(f"{f}:{b.line}: a draft cannot supersede itself")
        deps[n] = [briefs[x][0] for x in sb]
        finals[n] = sorted(set(ids))
    # every target superseded once
    claimed: dict[object, int] = {}
    for n in range(len(drafts)):
        for t in [("d", d) for d in deps[n]] + [("f", i) for i in finals[n]]:
            if t in claimed:
                what = f"memory-{t[1]}" if t[0] == "f" else repr(drafts[t[1]][1].fields["brief"])
                a, b = drafts[claimed[t]], drafts[n]
                raise Refused(f"fork: {what} is superseded by two drafts — \"{a[1].fields['brief']}\" ({a[0]}:{a[1].line}) "
                              f"and \"{b[1].fields['brief']}\" ({b[0]}:{b[1].line}); a memory is superseded once")
            claimed[t] = n
    for n in range(len(drafts)):
        resolve_targets(bank, finals[n], by_id)
    # dependency order: a superseded draft first (Kahn); among the drafts ready, the oldest first (datetime, then the
    # file's place in the batch, then the line), so ids ascend with time wherever the dependencies allow
    # (a heap of the drafts ready: each pick costs log n, not a scan of every draft)
    fidx = {f: k for k, f in enumerate(files)}
    order: list[int] = []
    waiting = {n: len(deps[n]) for n in range(len(drafts))}   # the deps not placed yet (a repeated one counts twice)
    users: dict[int, list[int]] = {}
    for n in range(len(drafts)):
        for d in deps[n]:
            users.setdefault(d, []).append(n)

    def key(n: int) -> tuple[str, int, int, int]:
        return drafts[n][1].fields["datetime"], fidx[drafts[n][0]], drafts[n][1].line, n

    ready = [key(n) for n in range(len(drafts)) if not waiting[n]]
    heapq.heapify(ready)
    while ready:
        pick = heapq.heappop(ready)[-1]
        order.append(pick)
        for u in users.get(pick, []):
            waiting[u] -= 1
            if not waiting[u]:
                heapq.heappush(ready, key(u))
    if len(order) < len(drafts):
        done = set(order)
        left = [drafts[n][1].fields["brief"] for n in range(len(drafts)) if n not in done]
        raise Refused(f"supersession cycle among the drafts: {', '.join(left)}")
    # supersession runs forward in time: every superseding draft is strictly newer than what it supersedes
    for n in order:
        f, b = drafts[n]
        mine = b.fields["datetime"]
        for d in deps[n]:
            if mine <= drafts[d][1].fields["datetime"]:
                raise Refused(f"{f}:{b.line}: \"{b.fields['brief']}\" ({mine}) is not newer than the draft it supersedes "
                              f"\"{drafts[d][1].fields['brief']}\" ({drafts[d][1].fields['datetime']}): supersession runs "
                              "forward in time")
        for i in finals[n]:
            if mine <= by_id[i].fields.get("datetime", ""):
                raise Refused(f"{f}:{b.line}: \"{b.fields['brief']}\" ({mine}) is not newer than memory-{i} "
                              f"({by_id[i].fields.get('datetime')}): supersession runs forward in time")
    mid = bank.next_id()
    assigned: dict[int, int] = {}
    touched: set[str] = set()
    report: list[str] = []
    stamp = ml.now_stamp()
    pending: dict[str, list[str]] = {}   # per file, its new blocks in id order: inserted in one pass per file
    for n in order:
        f, b = drafts[n]
        fields = {k: v for k, v in b.fields.items() if k in ml.BASE}
        fields["datetime"] = b.fields["datetime"] or stamp
        sup = sorted(finals[n] + [assigned[d] for d in deps[n]])
        if sup:
            fields["supersedes"] = ",".join(f"memory-{i}" for i in sup)
        path = bank.target(fields["type"], fields["keywords"], None)
        if path not in bank.texts and os.path.exists(path):
            readable(path, "the memory file")
            with open(path, encoding="utf-8") as fh:
                bank.texts[path] = fh.read()
        pending.setdefault(path, []).append(render(fields, b.text, mid))
        touched.add(path)
        assigned[n] = mid
        report.append(f"memory-{mid} <- \"{fields['brief']}\" ({boa_lock.posix_rel(path, bank.root)})")
        bank.new_ledger.append({"id": mid, "file": boa_lock.posix_rel(path, bank.root), "brief": fields["brief"],
                                "datetime": fields["datetime"], "assigned_by": "ingest", "draft_sha256": digest[n]})
        bank.entries[mid] = bank.new_ledger[-1]
        mid += 1
    for path, new in pending.items():
        bank.insert(path, new)
    # stamps: reparse the written texts so each target's header line is current
    blocks = {b.id: b for b in bank.reparse(touched) if b.id}
    pairs = [(blocks[i], assigned[n]) for n in order for i in finals[n] + [assigned[d] for d in deps[n]]]
    bank.stamp(pairs)
    touched.update(t.path for t, _ in pairs)
    bank.commit(touched)
    report += skips
    if receipt:
        report.append(write_receipt(bank, receipt, files, found, raw, sorted(assigned.values())))
    return report


def write_receipt(bank: Bank, receipt: str, files: list[str], found: list[tuple[str, ml.Block]],
                  raw: dict[str, list[str]], ids: list[int]) -> str:
    """Per file read: `lines` = N (its last draft line read), `sha256` = the hash of lines 1..N, `staging`."""
    entries = []
    for f in files:
        last = max((b.end for g, b in found if g == f), default=None)
        entries.append({"path": os.path.abspath(f).replace(os.sep, "/"), "staging": bank.is_staging(f), "lines": last,
                        "sha256": prefix_hash(raw[f][:last]) if last else None})
    doc = {"schema": "boa/ingest-receipt/1", "datetime": ml.real_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "ids": ids, "files": entries}
    replaceable(receipt)   # checked up front too (run): here for a path that changed since
    t = f"{receipt}.tmp.{os.getpid()}"
    with open(t, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    os.replace(t, receipt)
    return f"memory-write: receipt {receipt}"


def mark(bank: Bank, receipt: str, train: str) -> list[str]:
    """Insert the fold marker after each staging file's ingested prefix (all or nothing, under each file's lock).
    Lane files are not marked (they go with their worktree): one that is gone is reported, never refused."""
    if not re.fullmatch(r"TRAIN-\d+", train):
        raise Refused(f"--train {train!r}: a merge train id TRAIN-<n>")
    readable(receipt, "the receipt")
    try:
        with open(receipt, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise Refused(f"{receipt}: not a readable receipt ({exc})") from exc
    if not isinstance(doc, dict) or doc.get("schema") != "boa/ingest-receipt/1":
        raise Refused(f"{receipt}: not an ingest receipt (schema boa/ingest-receipt/1)")
    marker_rx = re.compile(r"^# \[[^]]*\] Folded by " + re.escape(train) + r"\b")
    stamp = ml.now_stamp()
    plans: list[tuple[str, list[str], int]] = []
    out: list[str] = []
    locks = []
    try:
        for e in doc.get("files", []):
            path, last, digest = e.get("path"), e.get("lines"), e.get("sha256")
            if e.get("staging") is not True:
                out.append(f"{path}: " + ("not a staging file: nothing to mark" if os.path.exists(str(path))
                                          else "gone, nothing to mark (a lane file: it went with its worktree)"))
                continue
            if not last:
                out.append(f"{path}: nothing was ingested from it: no marker")
                continue
            replaceable(str(path))   # the marker is renamed into place: never onto a device, FIFO or directory
            lk = boa_lock.FileLock(boa_lock.lock_path(bank.state, path)).__enter__()
            locks.append(lk)
            try:
                with open(path, encoding="utf-8", newline="") as fh:   # newline="": the file's own line endings
                    lines = fh.read().splitlines(keepends=True)
            except OSError as exc:
                raise Refused(f"{path}: the staging file is missing or unreadable ({exc.strerror or exc}); nothing "
                              "marked") from exc
            if not isinstance(last, int) or last > len(lines) or prefix_hash(lines[:last]) != digest:
                raise Refused(f"{path}: lines 1..{last}, the prefix the fold ingested, changed since the ingest (hash "
                              "mismatch); nothing marked — check the file, then mark by hand or re-run the fold")
            if last < len(lines) and marker_rx.match(lines[last]):
                out.append(f"{path}: already marked for {train} after line {last}: no-op")
                continue
            plans.append((path, lines, last))
        for path, lines, last in plans:
            ends = [x[len(x.rstrip("\r\n")):] for x in lines if x.endswith("\n")]
            eol = "\r\n" if ends and ends[0] == "\r\n" else "\n"   # the file's own (CRLF stays CRLF)
            if not lines[last - 1].endswith("\n"):
                lines[last - 1] += eol
            lines[last:last] = [f"# [{stamp}] Folded by {train}: everything above. Pending below.{eol}"]
            t = f"{path}.tmp.{os.getpid()}"
            with open(t, "w", encoding="utf-8", newline="") as fh:
                fh.write("".join(lines))
            os.replace(t, path)
            out.append(f"{path}: marked after line {last} (Folded by {train})")
    finally:
        for lk in locks:
            lk.__exit__(None, None, None)
    return out


def repair_ledger(bank: Bank, adopt: list[int], reason: str) -> list[str]:
    """Recovery after an interrupted write: void ledger ids whose block is missing (the id stays reserved), complete a
    supersession whose stamp is missing (both ids in the ledger before the repair), drop a stamp whose superseding
    block is missing. A bank id missing from the ledger is NOT crash damage (the ledger is written first): refused and
    named, unless adopted explicitly (`--adopt memory-N --reason "…"`, the block must pass the field checks)."""
    out: list[str] = []
    touched: set[str] = set()
    by_id = bank.by_id()
    before = set(bank.entries)
    seen: dict[int, ml.Block] = {}
    for b in bank.blocks:
        if b.id is None:
            continue
        if b.id in seen:
            raise Refused(f"memory-{b.id} is used twice ({seen[b.id].path}:{seen[b.id].line} and {b.path}:{b.line}): "
                          "fix the ids first")
        seen[b.id] = b
    missing = sorted(i for i in seen if i not in before)
    for i in adopt:
        if i in before:
            raise Refused(f"--adopt memory-{i}: it is in the ledger already")
        if i not in seen:
            raise Refused(f"--adopt memory-{i}: no block with that id in the memory bank")
        if seen[i].fields.get("supersedes"):
            raise Refused(f"--adopt memory-{i} ({seen[i].path}:{seen[i].line}): an adopted block may not declare "
                          "supersedes: rewrite it through memory_write.py --supersedes")
        problems = ml.check_fields(seen[i].fields, bank.types.names) + [
            f"{k} is required" for k in ml.BASE if not seen[i].fields.get(k)]
        if problems:
            raise Refused(f"--adopt memory-{i} ({seen[i].path}:{seen[i].line}): " + "; ".join(problems))
    if adopt and not reason.strip():
        raise Refused("--adopt needs --reason \"why this hand-written block is adopted\"")
    rest = [i for i in missing if i not in adopt]
    if rest:
        raise Refused("not in the ledger (hand-written, not crash damage: the ledger is written first): "
                      + ", ".join(f"memory-{i} ({seen[i].path}:{seen[i].line})" for i in rest)
                      + "; rewrite them through memory_write.py, or adopt each explicitly with "
                      "--adopt memory-N --reason \"…\"")
    for b in sorted(by_id.values(), key=lambda x: x.id):
        for t in ml.sup(b):
            if b.id in before and t in before and t in by_id and ml.succ_of(by_id[t]) is None \
                    and not by_id[t].fields.get("superseded-by"):
                bank.stamp([(by_id[t], b.id)])
                touched.add(by_id[t].path)
                out.append(f"stamped memory-{t} superseded-by memory-{b.id} (the interrupted write's stamp)")
    for b in sorted(by_id.values(), key=lambda x: x.id):
        succ = ml.succ_of(b)
        if succ is not None and succ not in by_id:
            lines = bank.texts[b.path].splitlines(keepends=True)
            lines[b.line - 1] = lines[b.line - 1].replace(f' superseded-by="memory-{succ}"', "")
            bank.texts[b.path] = "".join(lines)
            b.fields.pop("superseded-by", None)
            touched.add(b.path)
            out.append(f"dropped memory-{b.id}'s stamp superseded-by memory-{succ} (that block was never written)")
    entries = dict(bank.entries)
    stamp = ml.real_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    for i in sorted(adopt):
        b = seen[i]
        entries[i] = {"id": i, "file": boa_lock.posix_rel(b.path, bank.root), "brief": b.fields.get("brief", ""),
                      "datetime": b.fields.get("datetime", ""), "assigned_by": f"adopted: {clean(reason)}"}
        out.append(f"adopted memory-{i} ({entries[i]['file']}): {clean(reason)}")
    bankdir = os.path.normcase(os.path.realpath(bank.dir))
    for i in sorted(entries):
        e = entries[i]
        stored = os.path.normcase(os.path.realpath(boa_lock.from_posix(bank.root, str(e.get("file", "")))))
        if i not in seen and not e.get("void") and stored.startswith(bankdir + os.sep):
            entries[i] = dict(e, void=f"{stamp} repair: block missing (interrupted write)")
            out.append(f"voided memory-{i} ({e.get('file')}): no block; the id stays reserved, never reused")
    if not out:
        return ["memory-write: ledger and bank agree; nothing to repair"]
    text = "".join(json.dumps(entries[i], ensure_ascii=False) + "\n" for i in sorted(entries))
    bank.commit(touched, ledger_text=text)
    return out + [f"memory-write: ledger repaired ({len(out)} change(s)); run memory_lint.py to confirm"]


def main(argv: list[str]) -> int:
    import boa_tool
    boa_tool.on_term_exit()   # a stop mid-write still runs the finally blocks (temp files, locks)
    done: dict = {"lines": [], "vectors": True}
    code = run(argv, done)
    ids = sorted({int(m.group(1)) for x in done["lines"] for m in [re.match(r"memory-(\d+) ", x)] if m})
    if code == 0 and ids and done["vectors"]:
        note = start_vectors(done["root"], ids)
        if note:
            print(note, file=sys.stderr)
    return code


def start_vectors(root: str, ids: list[int]) -> str:
    """Cache the memory search vectors of the memories just written WITHOUT waiting for them: a detached child
    (memory_search.py --warm-ids) whose output goes to <BOA_LOG_DIR>/memory-vectors.log of the main checkout. Best
    effort: returns the one line to print when it is not started (no search environment, or a failed start), else ''.
    """
    note = "memory-write: memory search vectors not computed (the search computes them later): "
    try:
        import memory_search
        main = boa_config.main_of(root)
        cmd, why = memory_search.embedder(main)
        if cmd is None:
            return note + why
        logs = os.path.join(main, boa_config.load().get("BOA_LOG_DIR", ".boa/logs"))
        os.makedirs(logs, exist_ok=True)
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(logs, "memory-vectors.log"), "ab") as log:
            # Windows: no console window (its own children inherit the hidden console); POSIX: its own session
            detach = {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} \
                if os.name == "nt" else {"start_new_session": True}
            subprocess.Popen([sys.executable, "-I", os.path.join(here, "memory_search.py"), "--warm-ids",
                              ",".join(map(str, ids))], cwd=root, env={**os.environ, "BOA_ROOT": root},
                             stdin=subprocess.DEVNULL, stdout=log, stderr=log, **detach)
        return ""
    except Exception as exc:  # noqa: BLE001  (a write never fails because of its vectors)
        return note + str(exc)


def run(argv: list[str], done: dict) -> int:
    """The command; `done` gets the bank's root and dir and the lines of the memories written (for main's vectors)."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=ml.ROOT)
    ap.add_argument("--type")
    ap.add_argument("--brief")
    ap.add_argument("--keywords")
    ap.add_argument("--text")
    ap.add_argument("--supersedes", default="")
    ap.add_argument("--supersedes-brief", default="")
    ap.add_argument("--file")
    ap.add_argument("--format-only", action="store_true")
    ap.add_argument("--ingest", nargs="+")
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--repair-ledger", action="store_true")
    ap.add_argument("--adopt", default="")
    ap.add_argument("--reason", default="")
    ap.add_argument("--receipt")
    ap.add_argument("--mark")
    ap.add_argument("--train")
    ap.add_argument("--no-vectors", action="store_true")
    a = ap.parse_args(argv)
    done["vectors"] = not a.no_vectors
    bank: Bank | None = None
    try:
        if a.format_only:
            names = memory_types.load().names
            text = a.text if a.text is not None else sys.stdin.read()
            if not (a.type and a.brief and a.keywords):
                print("memory-write: --format-only needs --type, --brief and --keywords", file=sys.stderr)
                return 2
            fields = {"brief": clean(a.brief), "datetime": ml.now_stamp(), "keywords": clean(a.keywords), "type": a.type}
            check_draft(fields, text, names)
            if a.supersedes:
                if ml.id_list(a.supersedes) is None:
                    raise Refused(f"--supersedes '{a.supersedes}' is not a comma list of memory ids")
                fields["supersedes"] = a.supersedes.replace(" ", "")
            if a.supersedes_brief:
                fields["supersedes-brief"] = clean(a.supersedes_brief)
            sys.stdout.write(render(fields, text))
            return 0
        bank = Bank(os.path.abspath(a.root))
        done.update(root=bank.root, dir=bank.dir)
        bank.lock()
        if a.seed:
            bank.load()
            n = bank.seed_if_missing(explicit=True)
            if not n:
                raise Refused(nothing_to_seed(bank))
            bank.commit(set())
            print(f"memory-write: ledger seeded with {n} id(s) ({boa_lock.posix_rel(bank.ledger, bank.root)})")
            return 0
        if a.adopt and not a.repair_ledger:
            print("memory-write: --adopt only with --repair-ledger", file=sys.stderr)
            return 2
        if a.repair_ledger:
            adopt = ml.id_list(a.adopt) if a.adopt else []
            if adopt is None:
                raise Refused(f"--adopt '{a.adopt}' is not a comma list of memory ids")
            bank.load()
            if not os.path.exists(bank.ledger):
                raise Refused("no ledger to repair: run --seed")
            for line in repair_ledger(bank, sorted(set(adopt)), a.reason):
                print(line)
            return 0
        if a.mark:
            if not a.train:
                print("memory-write: --mark needs --train TRAIN-NNN", file=sys.stderr)
                return 2
            for line in mark(bank, a.mark, a.train):
                print(line)
            return 0
        if a.ingest:
            if a.receipt:
                r = os.path.normcase(os.path.realpath(a.receipt))
                if r.startswith(os.path.normcase(os.path.realpath(bank.dir)) + os.sep):
                    raise Refused(f"--receipt {a.receipt}: keep receipts outside the memory bank")
                if any(same_file(a.receipt, f) for f in a.ingest):
                    raise Refused(f"--receipt {a.receipt}: it is one of the files to ingest; name another file")
                if not os.path.isdir(os.path.dirname(os.path.abspath(a.receipt))):
                    raise Refused(f"--receipt {a.receipt}: its directory does not exist")
                replaceable(a.receipt)   # before the ingest: a refused receipt leaves the bank untouched
            bank.load()
            bank.seed_if_missing()
            for line in ingest(bank, a.ingest, a.receipt):
                print(line)
                done["lines"].append(line)
            return 0
        if not (a.type and a.brief and a.keywords):
            print("memory-write: --type, --brief and --keywords are required (or --format-only, --ingest, --seed)",
                  file=sys.stderr)
            return 2
        if a.supersedes_brief:
            print("memory-write: --supersedes-brief only in drafts (--format-only) and --ingest", file=sys.stderr)
            return 2
        text = a.text if a.text is not None else sys.stdin.read()
        target = bank.target(a.type, a.keywords, a.file) if a.type in bank.types.names else None
        bank.load([target] if target else [])
        bank.seed_if_missing()
        line = write_one(bank, a, text)
        print(line)
        done["lines"].append(line)
        return 0
    except Refused as exc:
        print(f"memory-write: refused: {exc}", file=sys.stderr)
        return 1
    except boa_lock.LockError as exc:
        print(f"memory-write: {exc}", file=sys.stderr)
        return 1
    except (memory_types.TypesError, boa_config.ConfigError, ValueError) as exc:
        print(f"memory-write: {exc}", file=sys.stderr)
        return 2
    finally:
        if bank:
            bank.unlock()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
