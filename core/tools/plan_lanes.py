#!/usr/bin/env python3
"""Recompute the task DAG, waves, lanes, critical path and progress from the plan.

Reads the machine-readable block of the implementation plan (BOA_PLAN_FILE, default
memory-bank/03-IMPLEMENTATION-PLAN.md), between the lines
`<!-- plan-lanes:begin -->` and `<!-- plan-lanes:end -->`:

    | ID | Size | MS | Deps | Del | Heavy | Lane | Hot | Status |
    | `T-123` | M | M1 | T-001 | Y | Y | L5 | H-CI | TODO |
    Superseded: T-003, T-004, ...
    Closing: M1=T-005, M2=T-006, M3=T-007, M4=T-008, final=T-009.

* Task IDs are always T-NNN (T- and at least three digits, an optional lower-case letter); milestones are M<n>.

* ID in backticks: the block never matches the `| T-123 |` row patterns that other suites pin task rows with.

* Size: S=1, M=2, L=3 (a leaf task is at most L), XL=5 (only on a SPLIT parent: its pre-split estimate).
* Deps: `—` or a comma list of task IDs (no ranges). A SPLIT parent's Deps are its children; it is
  complete when all of them are. Depending on a split parent means depending on all its children.
* Status: TODO, IN-FLIGHT, BLOCKED, SPLIT or DONE, optionally followed by "; note" segments. A task is DONE only
  when the cell is exactly `DONE` or carries the appended segment `; DONE — PR #<n>`; any other mention of DONE is
  refused, and a SPLIT parent never carries DONE (it is complete when its children are). "TODO; row pending T-002": the task row is added by that IN-FLIGHT lane (allowed until it lands).
* Hot: `—` or a comma list of hotspots; tasks of the same wave that share one are serialised in one lane.

Checks (any failure exits 1): unique IDs (in the block, one `| T-123 | M1 |` definition row and one ledger row per ID
in the plan), valid cells, every dep known (not superseded), no cycle,
every child under one parent only, every task row of the plan present in the block (or superseded),
every block task has a plan row (unless in flight or its row is pending an in-flight lane), DONE in the
plan ⇔ DONE in the block, a DONE task depends on no open task, a SPLIT parent's plan row says "SPLIT into" and vice versa, a child keeps its parent's
milestone and its plan row says "child N of <parent>" (new tasks only, so a split never changes progress (b)); with a
`Closing:` line, every open task comes before the final task and every open task of a milestone before that
milestone's closing task (or is part of the closing sequence after it).

Usage:  python3 -I .boa/tools/plan_lanes.py [--plan FILE] [--check]
        (no --check: print the report — progress, critical path, waves with lanes — as Markdown)
Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from fractions import Fraction

sys.dont_write_bytecode = True  # importing the sibling module must leave no __pycache__ behind (zero residue)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_config  # noqa: E402  (sibling module; `python3 -I` leaves the script directory off sys.path)

try:
    CONFIG = boa_config.load()
    ID_RE = boa_config.task_re(CONFIG)
except (boa_config.ConfigError, OSError, UnicodeDecodeError) as _exc:   # one line naming it, no traceback
    sys.exit(f"plan-lanes: config: {_exc}")
TID = boa_config.task_key   # task ids sort by number (a four-digit id after every three-digit one), wherever listed
BEGIN, END = "<!-- plan-lanes:begin -->", "<!-- plan-lanes:end -->"
SIZES = {"S": 1, "M": 2, "L": 3, "XL": 5}
STATUSES = ("TODO", "IN-FLIGHT", "BLOCKED", "SPLIT")
NONE = ("—", "-", "")
# A task definition row (a table with an MS column): `| T-123 | M1 | scope | ...`.
DEF_ROW = re.compile(r"^\| (?:\*\*|`)?(" + ID_RE + r")(?:\*\*|`)? \| M\d \|")
LEDGER_HEAD = "### Status ledger"
# A row of any task table outside the block: `| T-123 |`, `| **T-123** |` or `` | `T-123` | ``.
PLAN_ROW = re.compile(r"^\| (?:\*\*|`)?(" + ID_RE + r")(?:\*\*|`)? \|")
# A plan row that records the task as done: second or last cell starts with DONE, or an appended marker.
# Its own DONE marker only (not one quoted from another task): last cell ending in `DONE — PR #<n>` (alone or after `;`).
DONE_TAIL = re.compile(r"(^|;\s*)DONE — PR #\d+$")
# The only DONE forms a block Status cell may carry: exactly `DONE`, or an appended `; DONE — PR #<n>` segment.
DONE_SEGMENT = re.compile(r"DONE — PR #\d+")
# A child's definition row names its parent ("child 2 of T-123"): a split may only list new tasks as children.
CHILD_OF = r"child \d+ of {}(?![0-9a-z])"
SPLIT_MARK = re.compile(r"SPLIT into " + ID_RE)
# A block row whose task row is added by another, in-flight lane: Status "TODO; row pending T-002".
PENDING = re.compile(r"row pending (" + ID_RE + r")")


@dataclass
class Task:
    tid: str
    size: str
    ms: str
    deps: list[str]
    dele: str
    heavy: bool
    lane: str
    hot: list[str]
    status: str
    line: int
    note: str = ""
    children: list[str] = field(default_factory=list)

    @property
    def done(self) -> bool:
        return self.status == "DONE"

    @property
    def split(self) -> bool:
        return self.status == "SPLIT"


class PlanError(Exception):
    pass


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def id_list(text: str, where: str, errors: list[str]) -> list[str]:
    if text in NONE:
        return []
    out = []
    for part in text.split(","):
        part = part.strip()
        if not re.fullmatch(ID_RE, part):
            errors.append(f"{where}: bad task ID '{part}' (comma list of IDs, no ranges)")
        else:
            out.append(part)
    return out


def parse(text: str) -> tuple[dict[str, Task], set[str], dict[str, str], list[str], list[str]]:
    """Return (tasks, superseded, closing tasks, plan lines outside the block, errors)."""
    lines = text.splitlines()
    begins = [i for i, x in enumerate(lines) if x.strip() == BEGIN]
    ends = [i for i, x in enumerate(lines) if x.strip() == END]
    if len(begins) != 1 or len(ends) != 1 or ends[0] < begins[0]:
        raise PlanError(f"need exactly one '{BEGIN}' … '{END}' block (found {len(begins)}/{len(ends)})")
    b, e = begins[0], ends[0]
    outside = lines[:b] + lines[e + 1:]
    stray = [n + 1 for n, x in enumerate(lines) if x.strip().startswith("Closing:") and not b < n < e]
    tasks: dict[str, Task] = {}
    superseded: set[str] = set()
    closing: dict[str, str] = {}
    errors: list[str] = []
    for n in range(b + 1, e):
        line = lines[n].strip()
        where = f"line {n + 1}"
        if line.startswith("Superseded:"):
            superseded |= set(id_list(line.split(":", 1)[1].strip().rstrip("."), where, errors))
            continue
        if line.startswith("Closing:"):
            for pair in line.split(":", 1)[1].strip().rstrip(".").split(","):
                m = re.fullmatch(r"\s*(M\d|final)=(" + ID_RE + r")\s*", pair)
                if not m or m.group(1) in closing:
                    errors.append(f"{where}: bad or repeated Closing entry '{pair.strip()}' (M<n>=T-123 or final=T-123)")
                else:
                    closing[m.group(1)] = m.group(2)
            continue
        if not line.startswith("|"):
            continue
        c = cells(line)
        if c[0] == "ID" or (c[0] and set(c[0]) <= set("-: ")):
            continue
        if len(c) != 9:
            errors.append(f"{where}: expected 9 cells, got {len(c)}")
            continue
        tid, size, ms, deps, dele, heavy, lane, hot, status = c
        if tid == "":
            errors.append(f"{where}: empty ID cell")
            continue
        if not re.fullmatch("`" + ID_RE + "`", tid):
            errors.append(f"{where}: bad task ID '{tid}' (write it in backticks, e.g. `T-123`)")
            continue
        tid = tid.strip("`")
        if tid in tasks:
            errors.append(f"{where}: duplicate task {tid}")
            continue
        state, problem = parse_status(status)
        if problem:
            errors.append(f"{where}: {tid} {problem}")
        if size not in SIZES:
            errors.append(f"{where}: {tid} has unknown size '{size}'")
        elif size == "XL" and state != "SPLIT":
            errors.append(f"{where}: {tid} is XL but not SPLIT (a leaf task is at most L — split it)")
        if not re.fullmatch(r"M\d", ms):
            errors.append(f"{where}: {tid} has bad milestone '{ms}'")
        if heavy not in ("Y", "N", "—"):
            errors.append(f"{where}: {tid} has bad Heavy '{heavy}'")
        if dele not in ("Y", "N", "—"):
            errors.append(f"{where}: {tid} has bad Del '{dele}'")
        hots = [] if hot in NONE else [h.strip() for h in hot.split(",")]
        tasks[tid] = Task(tid, size, ms, id_list(deps, f"{where} ({tid} deps)", errors), dele,
                          heavy == "Y", lane, hots, state, n + 1, status)
    if not tasks and not errors:
        errors.append("the block has no task rows")
    errors += [f"line {n}: a Closing: line outside the plan-lanes block is not read — move it into the block" for n in stray]
    return tasks, superseded, closing, outside, errors


def parse_status(cell: str) -> tuple[str, str]:
    """Return (state, problem). Grammar: STATE[; note]... with STATE in STATUSES or exactly DONE; a task becomes DONE
    only through a bare `DONE` cell or an appended `; DONE — PR #<n>` segment. Any other mention of DONE is refused
    (e.g. "BLOCKED; until T-002 is DONE" must not count as done), and a SPLIT parent never carries DONE."""
    parts = [x.strip() for x in cell.split(";")]
    head, rest = parts[0], parts[1:]
    if head == "SPLIT":
        if re.search(r"\bDONE\b", cell):
            return "SPLIT", f"is SPLIT but its Status mentions DONE ('{cell}'): a split parent is complete when its children are"
        return "SPLIT", ""
    if head == "DONE":
        return "DONE", "" if not rest else f"has text after DONE ('{cell}'); write the state first, then '; DONE — PR #NN'"
    if head not in STATUSES:
        return head, f"has unknown status '{cell}'"
    done = [x for x in rest if DONE_SEGMENT.fullmatch(x)]
    stray = [x for x in rest if re.search(r"\bDONE\b", x) and not DONE_SEGMENT.fullmatch(x)]
    if stray:
        return head, f"mentions DONE outside the '; DONE — PR #NN' marker ('{cell}')"
    return ("DONE" if done else head), ""


def validate(tasks: dict[str, Task], superseded: set[str], outside: list[str],
             closing: dict[str, str] | None = None) -> list[str]:
    errors: list[str] = []
    for tid in sorted(set(tasks) & superseded, key=TID):
        errors.append(f"{tid} is both a block row and superseded")
    if not tasks:
        return errors
    for t in tasks.values():
        for d in t.deps:
            if d == t.tid:
                errors.append(f"{t.tid} depends on itself")
            elif d in superseded:
                errors.append(f"{t.tid} depends on superseded {d}")
            elif d not in tasks:
                errors.append(f"{t.tid} depends on {d}, which is missing from the block")
    parent_of: dict[str, str] = {}
    for t in tasks.values():
        if t.split:
            if not t.deps:
                errors.append(f"{t.tid} is SPLIT but lists no children")
            t.children = list(t.deps)
            for ch in t.children:
                if ch in parent_of:
                    errors.append(f"{ch} is a child of both {parent_of[ch]} and {t.tid}")
                parent_of[ch] = t.tid
                if ch in tasks and tasks[ch].ms != t.ms:
                    errors.append(f"{ch} is in {tasks[ch].ms} but its split parent {t.tid} is in {t.ms} (a split keeps the milestone)")
    cycles = find_cycles(tasks)
    errors += [f"dependency cycle: {' -> '.join(c)}" for c in cycles]
    if not cycles and not errors:
        p = Plan(tasks)
        for t in tasks.values():
            if t.done:
                errors += [f"{t.tid} is DONE but depends on open {d}" for d in t.deps if d in tasks and not p.complete(d)]
        errors += closing_errors(p, closing or {})
    # Coverage against the plan's own task rows (outside the block).
    rows: dict[str, list[str]] = {}
    for line in outside:
        m = PLAN_ROW.match(line)
        if m:
            rows.setdefault(m.group(1), []).append(line)
    errors += duplicate_ids(outside)
    for tid in sorted(rows, key=TID):
        if tid not in tasks and tid not in superseded:
            errors.append(f"{tid} has a plan row but is missing from the block (add it, or list it as superseded)")
    for t in tasks.values():
        if t.tid not in rows:
            m = PENDING.search(t.note)
            owner = tasks.get(m.group(1)) if m else None
            if t.status == "IN-FLIGHT" or (owner is not None and owner.status == "IN-FLIGHT"):
                continue
            why = f" ('row pending {m.group(1)}' but that task is not IN-FLIGHT)" if m else ""
            errors.append(f"{t.tid} is in the block but has no plan row (scope/acceptance){why}")
            continue
        marked_done = any(plan_row_done(r) for r in rows[t.tid])
        if marked_done and not t.done and not t.split:
            errors.append(f"{t.tid} is DONE in the plan but {t.status} in the block (append '; DONE — PR #NN' there too)")
        if t.done and not marked_done:
            errors.append(f"{t.tid} is DONE in the block but no plan row of it is marked DONE")
        says_split = any(SPLIT_MARK.search(r) for r in rows[t.tid])
        if t.split and not says_split:
            errors.append(f"{t.tid} is SPLIT in the block but no plan row of it says 'SPLIT into'")
        if says_split and not t.split:
            errors.append(f"{t.tid} has a plan row saying 'SPLIT into' but its block row is {t.status}, not SPLIT")
        if t.tid in parent_of and not any(re.search(CHILD_OF.format(parent_of[t.tid]), r) for r in rows[t.tid]):
            errors.append(f"{t.tid} is a child of {parent_of[t.tid]} but no plan row of it says 'child N of {parent_of[t.tid]}'"
                          " (a split lists new tasks only)")
    return errors


def closing_errors(p: "Plan", closing: dict[str, str]) -> list[str]:
    """Closing tasks (block line `Closing: M1=T-005, …, final=T-009`): (a) every open leaf comes before the final
    task; (b) every open leaf of milestone N comes before N's closing task, unless it is that task or comes after it
    (the closing sequence, e.g. review and sign-off, which (a) still covers), and that closing sequence ends in exactly
    one task (the milestone sign-off). Checked only when the line is present."""
    if not closing:
        return []
    unknown = [f"{k}={v}" for k, v in sorted(closing.items()) if v not in p.t]
    if unknown:
        return [f"closing task {x} is not in the block" for x in unknown]
    errors: list[str] = []
    leaves = p.open_leaves()
    if "final" not in closing:
        errors.append("the Closing line declares no final task (final=T-…)")
    else:
        fin = closing["final"]
        orphans = [k for k in leaves if k != fin and k not in p.ancestors(fin)]
        if orphans:
            errors.append(f"open tasks not before the final task {fin}: {', '.join(orphans)}")
    for ms in sorted({p.t[k].ms for k in leaves}):
        if ms not in closing:
            errors.append(f"{ms} has open tasks but no closing task (add {ms}=T-… to the Closing line)")
            continue
        c = closing[ms]
        before, after = p.ancestors(c), p.descendants(c)
        orphans = [k for k in leaves if p.t[k].ms == ms and k != c and k not in before and k not in after]
        if orphans:
            errors.append(f"{ms} open tasks not before its closing task {c}: {', '.join(orphans)}")
        # The closing sequence (the milestone's open tasks after its closing task) must end in exactly one task, the
        # sign-off: otherwise a task hanging off the closing task could stay open when the milestone is tagged.
        ends = sequence_ends(p, ms, c)
        if len(ends) > 1:
            errors.append(f"{ms} closing sequence after {c} ends in more than one task: {', '.join(ends)}")
    return errors


def sequence_ends(p: "Plan", ms: str, closer: str) -> list[str]:
    """End tasks of milestone `ms`'s closing sequence: its open tasks after `closer` that come before none of the
    others. Exactly one (the sign-off) in a valid plan; empty when nothing of `ms` follows the closer."""
    after = p.descendants(closer)
    seq = [k for k in p.open_leaves() if p.t[k].ms == ms and k in after]
    return [k for k in seq if not any(x in p.descendants(k) for x in seq if x != k)]


def closing_summary(p: "Plan", closing: dict[str, str]) -> str:
    """`M1=T-005→T-006, …, final=T-009`: each milestone's closing task → the end of its closing sequence (the
    sign-off; the closing task itself when nothing follows it). Printed by --check and pinned by the suite, so a task
    appended after a sign-off changes the line."""
    ms = sorted((k for k in closing if k != "final"), key=lambda k: int(k[1:]))
    parts = [f"{k}={closing[k]}→{(sequence_ends(p, k, closing[k]) or [closing[k]])[0]}" for k in ms]
    return ", ".join(parts + ([f"final={closing['final']}"] if "final" in closing else []))


def duplicate_ids(outside: list[str]) -> list[str]:
    """One definition row per task ID (`| T-123 | M1 | …`), one row per ID in the status ledger.

    Two lanes that pick the same new ID both add a definition row (and a ledger row); after the second merge the ID is
    defined twice. Older seed tables without an MS column and the §1 disposition table stay out: they are history.
    """
    errors: list[str] = []
    defs: dict[str, list[str]] = {}
    ledger: dict[str, int] = {}
    in_ledger = False
    for line in outside:
        if line.startswith("#"):
            in_ledger = line.startswith(LEDGER_HEAD)
        m = DEF_ROW.match(line)
        if m:
            defs.setdefault(m.group(1), []).append(cells(line)[2])
        m = PLAN_ROW.match(line)
        if in_ledger and m:
            ledger[m.group(1)] = ledger.get(m.group(1), 0) + 1
    for tid, scopes in sorted(defs.items(), key=lambda kv: TID(kv[0])):
        if len(scopes) > 1:
            kind = "with different scopes" if len(set(scopes)) > 1 else "with the same scope"
            errors.append(f"{tid} is defined {len(scopes)} times {kind} (duplicate task ID: give the new task a free ID)")
    for tid, n in sorted(ledger.items(), key=lambda kv: TID(kv[0])):
        if n > 1:
            errors.append(f"{tid} has {n} rows in the status ledger (duplicate task ID, or append to the existing row)")
    return errors


def plan_row_done(row: str) -> bool:
    """The row marks its own task DONE: the status cell (second or last) starts with DONE, the last cell ends with the
    appended `DONE — PR #<n>` marker, or the scope cell opens with `**DONE (`. A marker quoted elsewhere does not count."""
    c = cells(row)
    if len(c) < 2:
        return False
    return (c[1].startswith("DONE") or c[-1].startswith("DONE") or bool(DONE_TAIL.search(c[-1]))
            or (len(c) > 2 and c[2].startswith("**DONE (")))


def find_cycles(tasks: dict[str, Task]) -> list[list[str]]:
    """Iterative DFS; one cycle reported per back edge found."""
    state: dict[str, int] = {}
    cycles: list[list[str]] = []
    for root in sorted(tasks, key=TID):
        if root in state:
            continue
        stack = [(root, iter(tasks[root].deps))]
        path = [root]
        state[root] = 1
        while stack:
            node, it = stack[-1]
            nxt = next((d for d in it if d in tasks), None)
            if nxt is None:
                state[node] = 2
                stack.pop()
                path.pop()
            elif state.get(nxt) == 1:
                cycles.append(path[path.index(nxt):] + [nxt])
            elif nxt not in state:
                state[nxt] = 1
                stack.append((nxt, iter(tasks[nxt].deps)))
                path.append(nxt)
    return cycles


class Plan:
    def __init__(self, tasks: dict[str, Task]):
        self.t = tasks
        self._complete: dict[str, bool] = {}
        self._finish: dict[str, int] = {}
        self._ef: dict[str, int] = {}
        self._tail: dict[str, int] = {}
        self.dependants: dict[str, list[str]] = {k: [] for k in tasks}
        for t in tasks.values():
            for d in t.deps:
                self.dependants[d].append(t.tid)

    def complete(self, tid: str) -> bool:
        if tid not in self._complete:
            t = self.t[tid]
            self._complete[tid] = all(self.complete(c) for c in t.children) if t.split else t.done
        return self._complete[tid]

    def weight(self, tid: str) -> int:
        t = self.t[tid]
        return 0 if t.split or self.complete(tid) else SIZES[t.size]

    def finish(self, tid: str) -> int:
        """Wave in which the task finishes (0 = already complete)."""
        if tid not in self._finish:
            t = self.t[tid]
            if self.complete(tid):
                v = 0
            elif t.split:
                v = max(self.finish(c) for c in t.children)
            else:
                v = 1 + max((self.finish(d) for d in t.deps), default=0)
            self._finish[tid] = v
        return self._finish[tid]

    def ef(self, tid: str) -> int:
        """Earliest finish in size units (longest weighted chain ending here)."""
        if tid not in self._ef:
            self._ef[tid] = self.weight(tid) + max((self.ef(d) for d in self.t[tid].deps), default=0)
        return self._ef[tid]

    def tail(self, tid: str) -> int:
        """Remaining weighted chain from this task to the end (priority inside a lane)."""
        if tid not in self._tail:
            self._tail[tid] = self.weight(tid) + max((self.tail(d) for d in self.dependants[tid]), default=0)
        return self._tail[tid]

    def ancestors(self, tid: str) -> set[str]:
        """Every task that `tid` depends on, directly or through others (a split parent through its children)."""
        seen: set[str] = set()
        stack = list(self.t[tid].deps)
        while stack:
            d = stack.pop()
            if d not in seen and d in self.t:
                seen.add(d)
                stack += self.t[d].deps
        return seen

    def descendants(self, tid: str) -> set[str]:
        """Every task that depends on `tid`, directly or through others."""
        seen: set[str] = set()
        stack = list(self.dependants[tid])
        while stack:
            d = stack.pop()
            if d not in seen:
                seen.add(d)
                stack += self.dependants[d]
        return seen

    def open_leaves(self) -> list[str]:
        return sorted((k for k, t in self.t.items() if not t.split and not t.done), key=TID)

    def critical_path(self) -> list[str]:
        leaves = self.open_leaves()
        if not leaves:
            return []
        node = max(leaves, key=lambda k: (self.ef(k), TID(k)))
        chain = []
        while True:
            if not self.t[node].split:
                chain.append(node)
            deps = [d for d in self.t[node].deps if not self.complete(d)]
            if not deps:
                break
            node = max(deps, key=lambda k: (self.ef(k), TID(k)))
        return list(reversed(chain))

    def waves(self) -> dict[int, list[str]]:
        out: dict[int, list[str]] = {}
        for k in self.open_leaves():
            out.setdefault(self.finish(k), []).append(k)
        return dict(sorted(out.items()))

    def lanes(self, wave: list[str]) -> list[list[str]]:
        """Tasks of one wave sharing a hotspot (transitively) form one serial lane; others run alone."""
        parent = {k: k for k in wave}

        def find(k: str) -> str:
            while parent[k] != k:
                parent[k] = parent[parent[k]]
                k = parent[k]
            return k

        first: dict[str, str] = {}
        for k in wave:
            for h in self.t[k].hot:
                if h in first:
                    parent[find(k)] = find(first[h])
                else:
                    first[h] = k
        groups: dict[str, list[str]] = {}
        for k in wave:
            groups.setdefault(find(k), []).append(k)
        lanes = [sorted(g, key=lambda k: (-self.tail(k), TID(k))) for g in groups.values()]
        return sorted(lanes, key=lambda g: (-self.tail(g[0]), TID(g[0])))

    def progress_weights(self) -> dict[str, Fraction]:
        """Leaf weights anchored on the pre-split estimate: a split never changes the total."""
        children = {c for t in self.t.values() for c in t.children}
        w: dict[str, Fraction] = {}

        def spread(tid: str, weight: Fraction) -> None:
            t = self.t[tid]
            if not t.split:
                w[tid] = weight
                return
            total = sum(SIZES[self.t[c].size] for c in t.children)
            for c in t.children:
                spread(c, weight * SIZES[self.t[c].size] / total)

        for k in sorted(self.t, key=TID):
            if k not in children:
                spread(k, Fraction(SIZES[self.t[k].size]))
        return w

    def progress(self) -> list[tuple[str, int, int, int, Fraction, Fraction]]:
        """Rows (scope, done leaves, in-flight leaves, total leaves, done weight, total weight)."""
        w = self.progress_weights()
        rows = []
        for scope in ["all"] + sorted({self.t[k].ms for k in w}):
            ks = [k for k in w if scope == "all" or self.t[k].ms == scope]
            rows.append((scope, sum(self.t[k].done for k in ks), sum(self.t[k].status == "IN-FLIGHT" for k in ks),
                         len(ks), sum((w[k] for k in ks if self.t[k].done), Fraction(0)), sum((w[k] for k in ks), Fraction(0))))
        return rows


def pct(a: Fraction | int, b: Fraction | int) -> str:
    return f"{float(100 * Fraction(a) / Fraction(b)) if b else 0.0:.1f}%"


def report(p: Plan) -> str:
    out = ["#### Progress (lead reports (a) and (b) together)", "",
           "| Scope | (a) DONE / leaf tasks | in flight | (b) work-weighted DONE |", "|---|---|---|---|"]
    for scope, done, fly, total, dw, tw in p.progress():
        out.append(f"| {scope} | {done}/{total} ({pct(done, total)}) | {fly} | {float(dw):.1f}/{float(tw):.1f} ({pct(dw, tw)}) |")
    cp = p.critical_path()
    out += ["", f"#### Critical path ({len(cp)} tasks, {p.ef(cp[-1]) if cp else 0} size units; S=1 M=2 L=3)", "",
            " → ".join(f"{k} ({p.t[k].size})" for k in cp) or "(nothing open)", ""]
    out += ["#### Waves (wave 1 = eligible now; `*` heavy, `~` in flight, `!` blocked; a lane runs its tasks in order)", "",
            "| Wave | Tasks | Heavy | Lanes |", "|---|---|---|---|"]
    for n, wave in p.waves().items():
        lanes = []
        for lane in p.lanes(wave):
            hot = sorted({h for k in lane for h in p.t[k].hot if sum(h in p.t[x].hot for x in lane) > 1})
            label = f"[{', '.join(hot)}] " if hot else ""
            lanes.append(label + " → ".join(k + ("*" if p.t[k].heavy else "") + ("~" if p.t[k].status == "IN-FLIGHT" else "")
                                            + ("!" if p.t[k].status == "BLOCKED" else "") for k in lane))
        heavy = sum(p.t[k].heavy for k in wave)
        out.append(f"| {n} | {len(wave)} | {heavy} | {' · '.join(lanes)} |")
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", default=CONFIG["BOA_PLAN_FILE"])
    ap.add_argument("--check", action="store_true", help="validate only")
    a = ap.parse_args(argv)
    try:
        with open(a.plan, encoding="utf-8") as fh:
            tasks, superseded, closing, outside, errors = parse(fh.read())
    except (OSError, PlanError) as exc:
        print(f"plan-lanes: {exc}", file=sys.stderr)
        return 1
    errors += validate(tasks, superseded, outside, closing) if not errors else []
    if errors:
        for e in errors:
            print(f"plan-lanes: ERROR {e}", file=sys.stderr)
        return 1
    p = Plan(tasks)
    if a.check:
        print(f"plan-lanes: ok — {len(tasks)} tasks, {len(p.open_leaves())} open leaves, "
              f"{len(p.waves())} waves, critical path {len(p.critical_path())} tasks"
              + (f" — closing {closing_summary(p, closing)}" if closing else ""))
        return 0
    sys.stdout.write(report(p))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
