#!/usr/bin/env python3
"""Traceability check: the ONE check that must reach 0 at close (requirement/feature → task → test, and the rest).

It walks every relation that must hold between the project's records and reports each mismatch on one line:

  task-contract  every live leaf task of the plan names, in its `Contract / spec` cell (a plan table whose header
                 has that column: its text in any language of .boa/markers.json or one of its aliases, the same for
                 the other columns below), the contract clauses (`C-<NAME>.<n>`), whole contracts (`C-<NAME>`: a
                 spec-side task that writes or amends all of it) and `SPEC-` specs it writes, characterises or
                 implements, or
                 `none: <category>` (a category of CATEGORIES) for a task with no external surface; every contract it
                 names is in the contracts index and lists the task, every clause it names is defined, and every
                 task a contract lists names the contract (or one of its clauses) back;
  task-spec      every `SPEC-` id a task names is defined — by a heading or the ID cell of a table row — in the
                 specifications (BOA_SPEC_FILE) or docs/specs/;
  task-row       in the same plan table: a `none:` task (no external surface) has checkable `Acceptance criteria`
                 (they are its contract); every live leaf lists its `Edge cases` (or `none, because …`); every live
                 task has a `Managed by` owner (the lead, or the sub-lead that runs it); an empty cell, a dash or a
                 `<placeholder>` is missing;
  contract       every row of the contracts index (02, between `<!-- contracts:begin -->` and `<!-- contracts:end
                 -->`; columns ID | Version | Where | Consumers | Compatibility | Tasks | Tests | Features | Status):
                 a well-formed id `C-<NAME>`, its contract file (Where) present and defining at least one clause,
                 live tasks, at least one test, every listed test present and carrying `@covers-contract <C-ID or
                 clause> <task>` in its header, known features, status open|closed, and closed only when every task is
                 DONE; a version (1, 2, 1.2.0, …) after the first (0.x, 1, 1.0, 1.0.0) is named by an ADR in the
                 decisions file (BOA_DECISIONS_FILE) as the whole token `<C-ID> v<version>` (`v2-beta` is not v2);
                 with --close every contract is closed;
  clause         a clause is defined by a line of its contract file that starts — after an optional `#`…`######`,
                 `//`, `--`, `-`, `*`, `>`, `|` or `1.`/`1)` marker, the word `Clause`, backticks or bold — with its
                 id, optionally followed by `.`, `:` or `)` (`C-API.1 …`, `# C-API.1: …`, `### Clause C-API.1 — …`,
                 `1. C-API.1 …`, `**C-API.1.** …`, `| C-API.1 | …`), once; fenced code blocks and the Changelog
                 section are not read (the section ends at a clause line, and at the next heading of its level in
                 Markdown or a non-comment line elsewhere), a fence closes only on a fence of its character at
                 least as long (CommonMark), a fence left open is a mismatch; an id of the contract among the first three words after
                 the marker of any other line is a mismatch (a definition the check cannot read; a later mention is
                 prose); every clause has a test that runs carrying
                 `@covers-contract <clause> <task>` (a task of its contract);
  contract-test  every `@covers-contract <C-ID or clause> <task>` header line of a test that runs names a known
                 contract (and a defined clause) and one of its tasks; a contract's listed test must be such a test;
  feature        every feature (of the baseline a rewrite reproduces, and every new one) → task(s) → test(s): the
                 inventory (BOA_FEATURES_FILE) rules below, one line per error;
  residue        every residue register row (BOA_REGISTER_FILE, "### Residue register") has an owner task and a
                 removal step; with --close every row is a mismatch (the register must be empty);
  open-item      <lead dir>/open-items.md is a transit queue, never a source of work (the plan is the only one): its
                 open lines (`- [ ]`) wait to be resolved into the plan; with --close every line still open is a
                 mismatch (the queue must be empty);
  bug            every current memory of type `bug` whose text says `Status: open` names its owner task (T-NNN in its
                 keywords or text); with --close no bug is open;
  pending-fold   every line of <lead dir>/plan-additions-pending.md and owner-rules-pending.md after their last fold
                 marker (a `# … Folded by …` line, one `#` only; `- ` and `## ` lines, except "do not fold" ones) is
                 not folded yet;
  unread         every record the check reads (the plan aside: that one is fatal, exit 2) that exists and is not a
                 regular file (a FIFO, a device, a socket, a directory) is named, never opened: a stat comes first, so
                 a FIFO never hangs the check.

Tests that run: the files matching BOA_TEST_GLOBS (space-separated globs relative to the root, `**` for any depth;
set per stack) minus those matching BOA_TEST_EXCLUDES, tracked by git when the root is a git checkout; only their
header counts (shell `.sh`/`.bash`: the leading comment block after the shebang; any other file: the lines before its
first declaration — class, def, function, func, fn, describe, test, it, suite, module), so heredocs, strings and
commented-out code never trace anything.

The feature relation. The inventory lists every feature, each mapped to the plan task(s) that build it; a test
declares what it exercises with a header line `@covers-feature F-ID T-NNN[ T-NNN…][, F-ID T-NNN…]`: the feature and
the task(s) whose work the test proves.
  * inventory shape: known keys, unique well-formed IDs, origin baseline|new, at least one task, a ref or a source;
  * every task ID of a feature or of [not_features] is a live task of the plan's plan-lanes block; a not_features
    reason starts with a category (`tooling: …`, see CATEGORIES); a not_features task has no feature task in its
    split lineage (itself, its split parents or its children);
  * every live leaf task registers a feature (directly or through its split parent) or is a not_features entry;
  * every feature of every DONE leaf task has an annotation naming that very task (per task, not per feature: another
    task's tests, a sibling's or the split parent's, never stand in for it);
  * every annotation names a known feature and a leaf task of that feature's split lineage (never a split parent); a
    malformed annotation, or one on an abstract class (never run), fails;
  * cross-reference against the spec inventories the inventory declares (`[[source]]` tables, optional): every item is
    claimed by exactly one feature, every ref a feature claims exists, and where the source names owner tasks the
    claiming feature's task lineage includes one of them. A Markdown source checks its rows against the count the
    spec states (`count`, a regex with one group) or else their numbering, and refuses rows it cannot read, so a new
    sub-heading or a "12a" row never drops an item silently;
  * every live task cited in the plan's coverage checklist (BOA_PLAN_CHECKLIST_HEAD; ranges expanded, superseded
    paragraphs skipped; set it empty to have no checklist) is accounted for by a feature or a not_features entry.
A `[[source]]` table: `path` (relative to the root), `prefix` (the items are `<prefix>/<key>`), `kind` "table"
(default: the Markdown table rows of the one section whose heading starts with `heading`, `key` and `owners` = 1-based
column numbers, `count` = the stated-count regex, `numbered` = first column 1..N, default true) or "tsv" (a
tab-separated file with a header row; `key` and `owners` = column names; lines starting with # skipped).

Output: one `MISMATCH <relation>: <detail>` line per mismatch, then `MISMATCHES: <n>`. Exit 0 only at 0 mismatches,
1 otherwise, 2 on a usage error or when the plan cannot be read (a plan header naming one column twice included).
`--report` first prints the feature report (counts
per milestone — a feature's milestone is the latest milestone of its tasks —, status DONE / in progress / TODO, the
tests each feature is traced to) when the feature relation has no mismatch. `--close` is the train mode plus the
close-out relations: every contract closed, an empty transit queue, every pending fold folded (as always), the residue
register empty, no open bug, every live leaf task DONE (relation `task`), every feature DONE and traced by a test.

Usage:  python3 -I .boa/tools/trace_check.py [--root DIR] [--close] [--report]
Python 3.11+ standard library only (tomllib); reuses the plan parser of plan_lanes.py.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field

sys.dont_write_bytecode = True  # importing the sibling modules must leave no __pycache__ behind (zero residue)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_config  # noqa: E402  (sibling module; `python3 -I` leaves the script directory off sys.path)
import markers  # noqa: E402

try:   # read here first, so a bad config line is named under this tool's own prefix (plan_lanes reads it on import)
    boa_config.load()
except (boa_config.ConfigError, OSError, UnicodeDecodeError) as _exc:
    sys.exit(f"trace-check: config: {_exc}")
import plan_lanes  # noqa: E402

CONFIG = plan_lanes.CONFIG
INVENTORY = CONFIG["BOA_FEATURES_FILE"]
PLAN = CONFIG["BOA_PLAN_FILE"]
TEST_GLOBS = CONFIG["BOA_TEST_GLOBS"].split()
TEST_EXCLUDES = CONFIG.get("BOA_TEST_EXCLUDES", "").split()
CHECKLIST_HEAD = CONFIG["BOA_PLAN_CHECKLIST_HEAD"]
TID = plan_lanes.ID_RE
TASK_ID = re.compile(TID + r"(?![0-9a-z])")
FID = r"F-[A-Z0-9]+(?:-[A-Z0-9]+)*"
ENTRY = FID + r"(?:\s+" + TID + r")+"
ANNOTATION = re.compile(r"^\s*(?://|#|/?\*+)\s*@covers-feature\b(.*)$")
ANNOTATION_BODY = re.compile(r"^\s*(" + ENTRY + r"(?:\s*,\s*" + ENTRY + r")*)\s*(?:\*/)?\s*$")
# The first declaration ends a non-shell test file's header; group 1 = its modifiers, group 2 = its keyword.
DECL = re.compile(r"^\s*((?:(?:final|abstract|readonly|public|private|export|default|async|static|sealed|open|data)\s+)*)"
                  r"(class|def|function|func|fn|describe|test|it|suite|module)\b")
SHELL_EXT = (".sh", ".bash")
LEAD_COMMENT = re.compile(r"^\s*(?://|#|/\*|\*)")   # a comment line of a test script with no declaration
FEATURE_KEYS = {"id", "title", "origin", "tasks", "refs", "source", "note"}
ORIGINS = {"baseline": "baseline", "new": "new"}
CATEGORIES = ("process", "tooling", "spec", "characterization", "review", "sign-off", "verification", "maintenance",
              "decision", "compliance", "environment", "documentation", "bug-fix")
REASON = re.compile(r"^(?:" + "|".join(CATEGORIES) + r"):\s*\S")
TASK_OR_RANGE = re.compile(r"(" + TID + r")(?:\s*(?:…|\.\.\.)\s*(" + TID + r"))?")

CID = r"C-[A-Z0-9]+(?:-[A-Z0-9]+)*"
CLAUSE = CID + r"\.[A-Z0-9]+(?:-[A-Z0-9]+)*"
SID = r"SPEC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*"
# A clause definition line: an optional marker (heading, comment, list item, quote, table cell, ordered-list number),
# an optional word "Clause", then the id (backticks or bold allowed), optionally followed by `.`, `:` or `)`.
CLAUSE_DEF = re.compile(r"^\s*(?:#{1,6}|//|--|[-*>|]|\d+[.)])?\s*(?:[Cc]lause\s+)?[`*]*(" + CLAUSE
                        + r")(?![A-Za-z0-9-]|\.[A-Za-z0-9])")
CLAUSE_ANY = re.compile(r"(?<![A-Za-z0-9-])(" + CLAUSE + r")(?![A-Za-z0-9-]|\.[A-Za-z0-9])")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
MARKER = re.compile(r"^\s*(?:#{1,6}|//|--|[-*>|]|\d+[.)])?\s*(?:[Cc]lause\s+)?")   # the line marker of CLAUSE_DEF
CHANGELOG = re.compile(r"^(#{1,6})\s+[`*]*changelog\b", re.I)
C_BEGIN, C_END = "<!-- contracts:begin -->", "<!-- contracts:end -->"
C_COLUMNS = ["ID", "Version", "Where", "Consumers", "Compatibility", "Tasks", "Tests", "Features", "Status"]
CONTRACT_ANN = re.compile(r"^\s*(?://|#|/?\*+)\s*@covers-contract\b(.*)$")
CONTRACT_BODY = re.compile(r"^\s*(" + CID + r"(?:\.[A-Z0-9]+(?:-[A-Z0-9]+)*)?)\s+(" + TID + r")\s*(?:\*/)?\s*$")
VERSION = re.compile(r"\d+(?:\.\d+)*")
FIRST_VERSION = re.compile(r"0(?:\.\d+)*|1(?:\.0)*")   # 0.x (pre-release) or 1, 1.0, 1.0.0: no ADR needed
# The plan table columns trace_check reads (short name -> markers.json entry), and the fold marker: machine-recognised
# words of .boa/markers.json; a header row is resolved by markers.plan_header only (every language, the aliases).
COLUMN_KEYS = {"contract": "plan.contract_column", "acceptance": "plan.acceptance_column", "edge": "plan.edge_column",
               "managed": "plan.managed_column"}

MARKERS_ERROR = ""   # an unreadable markers file is fatal (exit 2), reported by check()
_MARKERS: dict = {}
try:
    _MARKERS = markers.load()
    FOLD = markers.fold_regex(_MARKERS)
except markers.MarkersError as _exc:
    MARKERS_ERROR, FOLD = str(_exc), re.compile(r"(?!)")
NONE = ("", "—", "-")
# A fold marker: a level-1 comment/heading line ("# [<time>] Folded by TRAIN-n …"); a "## " pending entry that only
# mentions folding is an entry, not a marker.
OPEN_BUG = re.compile(r"^\s*[-*]?\s*status\s*:\s*open\b", re.I | re.M)
HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class InventoryError(Exception):
    pass


# --- spec sources ---------------------------------------------------------------------------------------------------
# Each parser returns {ref: owner tasks the spec names} (empty set: the spec names no owner for that kind of item).
# A missing file, section, stated count or readable row is an error: a restructured spec never passes silently.

Items = dict[str, frozenset[str]]
SEPARATOR = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+\s*$")


def heading_level(line: str) -> int:
    return len(line) - len(line.lstrip("#"))


def section(path: str, text: str, heading: str) -> list[str]:
    """The lines of the one section whose heading starts with `heading`, up to the next heading of the same or a
    higher level (deeper sub-headings stay inside)."""
    lines = text.splitlines()
    starts = [i for i, x in enumerate(lines) if x.startswith(heading)]
    if len(starts) != 1:
        raise InventoryError(f"{path}: need exactly one section '{heading}' (found {len(starts)})")
    level, out = heading_level(heading), []
    for line in lines[starts[0] + 1:]:
        if line.startswith("#") and heading_level(line) <= level:
            break
        out.append(line)
    return out


def table_rows(lines: list[str]) -> list[tuple[list[str], list[str]]]:
    """(header cells, cells) of every data row of the Markdown tables in `lines`; an escaped pipe stays in its cell."""
    def cells(x: str) -> list[str]:
        return [c.strip() for c in re.split(r"(?<!\\)\|", x.strip().strip("|"))]
    out: list[tuple[list[str], list[str]]] = []
    header: list[str] = []
    for i, x in enumerate(lines):
        if not x.startswith("|") or SEPARATOR.match(x):
            continue
        if i + 1 < len(lines) and SEPARATOR.match(lines[i + 1]):
            header = cells(x)
            continue
        out.append((header, cells(x)))
    return out


def row_number(path: str, what: str, cell: str) -> int:
    if re.fullmatch(r"\d+", cell):
        return int(cell)
    raise InventoryError(f"{path}: {what}: unreadable row '{cell}' (rows are numbered 1, 2, …)")


def check_count(path: str, what: str, numbers: list[int], stated: int | None) -> None:
    if numbers != list(range(1, len(numbers) + 1)):
        raise InventoryError(f"{path}: {what}: rows are not numbered 1..N in order (a new sub-heading or row?)")
    if stated is not None and len(numbers) != stated:
        raise InventoryError(f"{path}: {what}: {len(numbers)} rows, but the spec states {stated}")


def stated(path: str, what: str, pattern: str, text: str) -> int:
    m = re.search(pattern, text, re.M)
    if not m:
        raise InventoryError(f"{path}: {what}: the stated count ('{pattern}') is missing")
    return int(m.group(1))


def put(path: str, items: Items, ref: str, owners: frozenset[str] = frozenset()) -> None:
    if ref in items:
        raise InventoryError(f"{path}: item '{ref}' appears twice")
    items[ref] = owners


def owners_of(cell: str) -> frozenset[str]:
    return frozenset(TASK_ID.findall(cell))


SOURCE_KEYS = {"path", "kind", "prefix", "heading", "key", "owners", "count", "numbered"}


def table_source(path: str, text: str, src: dict) -> Items:
    """A Markdown table source: the rows of the one section whose heading starts with `heading`."""
    heading, key, owners = src["heading"], src["key"], src.get("owners")
    lines = section(path, text, heading)
    width = max(key, owners or 0)
    numbered = src.get("numbered", True)
    count = stated(path, heading, src["count"], "\n".join(lines)) if src.get("count") else None
    rs = [c for _, c in table_rows(lines)]
    for c in rs:
        if len(c) < width:
            raise InventoryError(f"{path}: {heading}: row '{c[0]}' has {len(c)} cells, expected {width}")
    if numbered:
        check_count(path, heading, [row_number(path, heading, c[0]) for c in rs], count)
    elif count is not None and len(rs) != count:
        raise InventoryError(f"{path}: {heading}: {len(rs)} rows, but the spec states {count}")
    items: Items = {}
    for c in rs:
        put(path, items, f"{src['prefix']}/{c[key - 1].strip('`')}", owners_of(c[owners - 1]) if owners else frozenset())
    return items


def tsv_source(path: str, text: str, src: dict) -> Items:
    """A tab-separated source with a header row: `key` and `owners` are column names."""
    rs = [x.split("\t") for x in text.splitlines() if x and not x.startswith("#")]
    if not rs or src["key"] not in rs[0] or (src.get("owners") and src["owners"] not in rs[0]):
        cols = [src["key"]] + ([src["owners"]] if src.get("owners") else [])
        raise InventoryError(f"{path}: expected a header row with the column(s) {', '.join(cols)}")
    head = rs[0]
    k = head.index(src["key"])
    o = head.index(src["owners"]) if src.get("owners") else None
    if len(rs) < 2:
        raise InventoryError(f"{path}: no rows")
    items: Items = {}
    for c in rs[1:]:
        if len(c) < len(head) or not c[k]:
            raise InventoryError(f"{path}: unreadable row '{c[0]}' (expected {len(head)} tab-separated cells)")
        put(path, items, f"{src['prefix']}/{c[k]}", owners_of(c[o]) if o is not None else frozenset())
    return items


def load_sources(raw: object) -> tuple[list[dict], list[str]]:
    """The `[[source]]` tables of the inventory, validated (errors name the source by its number)."""
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        return [], ["source must be an array of tables ([[source]])"]
    out: list[dict] = []
    errors: list[str] = []
    for n, src in enumerate(raw, 1):
        where = f"source #{n}"
        if not isinstance(src, dict):
            errors.append(f"{where}: not a table")
            continue
        bad = sorted(set(src) - SOURCE_KEYS)
        kind = src.get("kind", "table")
        problems = [f"unknown key(s) {', '.join(bad)}"] if bad else []
        if not isinstance(src.get("path"), str) or not src.get("path"):
            problems.append("path is required")
        if not isinstance(src.get("prefix"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", src.get("prefix") or ""):
            problems.append("prefix is required (lower-case letters, digits, -)")
        if kind == "table":
            if not isinstance(src.get("heading"), str) or not src.get("heading", "").startswith("#"):
                problems.append("heading is required (a Markdown heading, e.g. '## 2. Screens')")
            for col in ("key", "owners"):
                v = src.get(col)
                if (col == "key" or v is not None) and not (isinstance(v, int) and not isinstance(v, bool) and v >= 1):
                    problems.append(f"{col} must be a column number (1 = first)")
            if src.get("count") is not None:
                try:
                    if re.compile(src["count"]).groups != 1:
                        problems.append("count must be a regex with exactly one group")
                except (re.error, TypeError):
                    problems.append("count must be a regex with exactly one group")
            if not isinstance(src.get("numbered", True), bool):
                problems.append("numbered must be true or false")
        elif kind == "tsv":
            for col in ("key", "owners"):
                v = src.get(col)
                if (col == "key" or v is not None) and not (isinstance(v, str) and v):
                    problems.append(f"{col} must be a column name")
            extra = sorted(set(src) & {"heading", "count", "numbered"})
            if extra:
                problems.append(f"{', '.join(extra)} only apply to kind \"table\"")
        else:
            problems.append(f"kind must be table or tsv (got {kind!r})")
        if problems:
            errors += [f"{where}: {p}" for p in problems]
        else:
            out.append(dict(src, kind=kind))
    return out, errors


# --- inventory -------------------------------------------------------------------------------------------------


@dataclass
class Trace:
    fid: str
    tid: str
    path: str
    line: int


@dataclass
class Feature:
    fid: str
    title: str
    origin: str
    tasks: list[str]
    refs: list[str]
    traces: list[Trace] = field(default_factory=list)
    ms: str = ""
    status: str = ""


def load_inventory(text: str) -> tuple[list[Feature], dict[str, str], list[dict], list[str]]:
    """Return (features, not_features {task: reason}, spec sources, errors)."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise InventoryError(f"{INVENTORY}: not valid TOML: {exc}") from exc
    errors: list[str] = []
    extra = sorted(set(data) - {"schema", "feature", "not_features", "source"})
    if extra:
        errors.append(f"unknown top-level key(s): {', '.join(extra)}")
    if data.get("schema") != 1:
        errors.append("schema must be 1")
    features: list[Feature] = []
    seen: set[str] = set()
    raw = data.get("feature", [])
    if not isinstance(raw, list) or not raw:
        errors.append("no [[feature]] entries")
        raw = []
    for n, f in enumerate(raw, 1):
        if not isinstance(f, dict):
            errors.append(f"feature #{n}: not a table (write each feature as a [[feature]] table)")
            continue
        fid = f.get("id")
        where = f"feature #{n} ({fid})" if isinstance(fid, str) else f"feature #{n}"
        unknown = sorted(set(f) - FEATURE_KEYS)
        if unknown:
            errors.append(f"{where}: unknown key(s) {', '.join(unknown)}")
        if not isinstance(fid, str) or not re.fullmatch(FID, fid):
            errors.append(f"{where}: bad id (F-UPPER-CASE-WORDS, e.g. F-LINES)")
            continue
        if fid in seen:
            errors.append(f"{fid}: duplicate feature id")
            continue
        seen.add(fid)
        title, origin = f.get("title"), f.get("origin")
        tasks, refs, source = f.get("tasks", []), f.get("refs", []), f.get("source", "")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"{fid}: empty title")
        if origin not in ORIGINS:
            errors.append(f"{fid}: origin must be one of {', '.join(ORIGINS)} (got {origin!r})")
        if not isinstance(tasks, list) or not all(isinstance(t, str) for t in tasks):
            errors.append(f"{fid}: tasks must be a list of task IDs")
            tasks = []
        if not tasks:
            errors.append(f"{fid}: no task (every feature maps to at least one plan task)")
        for t in tasks:
            if not re.fullmatch(TID, t):
                errors.append(f"{fid}: bad task ID '{t}'")
        if len(set(tasks)) != len(tasks):
            errors.append(f"{fid}: a task is listed twice")
        if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):
            errors.append(f"{fid}: refs must be a list of strings")
            refs = []
        if not isinstance(source, str) or ("note" in f and not isinstance(f["note"], str)):
            errors.append(f"{fid}: source and note must be strings")
        elif not refs and not source.strip():
            errors.append(f"{fid}: needs refs (spec items it claims) or a source (where the feature is specified)")
        features.append(Feature(fid, title if isinstance(title, str) else "", origin if isinstance(origin, str) else "",
                                [t for t in tasks if re.fullmatch(TID, t)], refs))
    nf = data.get("not_features", {})
    if not isinstance(nf, dict):
        errors.append("[not_features] must be a table of task = reason")
        nf = {}
    for tid, why in nf.items():
        if not re.fullmatch(TID, tid):
            errors.append(f"not_features: bad task ID '{tid}'")
        if not isinstance(why, str) or not REASON.match(why):
            errors.append(f"not_features: {tid} needs a reason that starts with a category ("
                          f"{'|'.join(CATEGORIES)}), e.g. \"tooling: disk monitor\"")
    sources, serr = load_sources(data.get("source"))
    return features, {k: v for k, v in nf.items() if isinstance(v, str)}, sources, errors + serr


# --- tests --------------------------------------------------------------------------------------------------------


def slash_rel(p: str) -> str:
    """A path relative to the root in the one form this tool keeps, compares and prints: normalised, `/` on every OS."""
    return os.path.normpath(p).replace(os.sep, "/")


def test_files(root: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Return ([(path relative to root with `/` on every OS, 'sh'|'code')], errors): the tests that run (see the module
    docstring); a report names them the same way on every OS."""
    def matches(patterns: list[str]) -> set[str]:
        return {slash_rel(os.path.relpath(f, root)) for p in patterns
                for f in glob.glob(os.path.join(root, p), recursive=True) if os.path.isfile(f)}

    if not TEST_GLOBS:
        return [], ["BOA_TEST_GLOBS is empty: no test can trace a feature"]
    picked = matches(TEST_GLOBS) - matches(TEST_EXCLUDES)
    files = [(rel, "sh" if rel.endswith(SHELL_EXT) else "code") for rel in picked]
    if os.path.exists(os.path.join(root, ".git")):
        try:
            out = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            return [], [f"git ls-files failed in {root}: {exc}"]
        tracked = {slash_rel(p) for p in out.decode("utf-8", "replace").split("\0") if p}
        files = [f for f in files if f[0] in tracked]
    return sorted(set(files)), []


def header(text: str, kind: str) -> list[tuple[int, str]]:
    """Numbered header lines: shell the leading comment block (gate rule), any other file the lines before its first
    declaration, or, with no declaration (a test script: a Perl .t, an awk test), its leading comment block (`#`,
    `//`, `/*`, `*` lines). The header of an abstract class is returned too; scan_tests refuses an annotation there."""
    lines = text.splitlines()
    end = None if kind == "sh" else next((n for n, line in enumerate(lines) if DECL.match(line)), None)
    if end is not None:
        return list(enumerate(lines[:end], 1))
    comment = (lambda x: x.startswith("#")) if kind == "sh" else LEAD_COMMENT.match
    out = []
    for n, line in enumerate(lines, 1):
        if n == 1 and line.startswith("#!"):
            continue
        if not comment(line):
            break
        out.append((n, line))
    return out


def abstract_class(text: str) -> bool:
    """The first class declaration of the file is abstract (a test runner never runs it as a test)."""
    m = next((m for m in map(DECL.match, text.splitlines()) if m and m.group(2) == "class"), None)
    return bool(m and "abstract" in m.group(1).split())


def scan_tests(root: str) -> tuple[list[Trace], list[str]]:
    traces: list[Trace] = []
    files, errors = test_files(root)
    for rel, kind in files:
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            errors.append(f"{rel}: {exc.strerror or exc}")
            continue
        abstract = kind == "code" and abstract_class(text)
        for n, line in header(text, kind):
            m = ANNOTATION.match(line)
            if not m:
                continue
            if abstract:
                errors.append(f"{rel}:{n}: annotation on an abstract class (never run: annotate the concrete test "
                              "classes)")
                continue
            body = ANNOTATION_BODY.match(m.group(1))
            if not body:
                errors.append(f"{rel}:{n}: malformed annotation (write: @covers-feature F-ID T-NNN[ T-NNN…][, F-ID T-NNN…])")
                continue
            for entry in body.group(1).split(","):
                fid, *tids = entry.split()
                traces += [Trace(fid, t, rel, n) for t in tids]
    return traces, errors


def checklist_tasks(plan_text: str, live: set[str]) -> tuple[set[str], list[str]]:
    """Live task IDs cited by the plan's coverage checklist (ranges expanded; each superseded paragraph, from
    '*(Superseded' up to its closing ')*', skipped). No checklist configured (empty head): none."""
    if not CHECKLIST_HEAD:
        return set(), []
    lines = plan_text.splitlines()
    starts = [i for i, x in enumerate(lines) if x.startswith(CHECKLIST_HEAD)]
    if len(starts) != 1:
        return set(), [f"{PLAN}: need exactly one '{CHECKLIST_HEAD}' section (found {len(starts)})"]
    cited: set[str] = set()
    superseded = False
    for line in lines[starts[0] + 1:]:
        if line.startswith("### ") or line.startswith("## "):
            break
        if line.lstrip().startswith("*(Superseded"):
            superseded = True
        if superseded:
            superseded = ")*" not in line
            continue
        for a, b in TASK_OR_RANGE.findall(line):
            cited.add(a)
            if b:
                cited.add(b)
                lo, hi = re.search(r"\d+", a), re.search(r"\d+", b)
                if lo and hi:
                    prefix, width = a[:lo.start()], len(lo.group())
                    cited |= {f"{prefix}{k:0{width}d}" for k in range(int(lo.group()), int(hi.group()) + 1)}
    if superseded:
        return set(), [f"{PLAN}: the checklist ends inside a '*(Superseded' paragraph (no closing ')*'): the rest would be skipped"]
    return cited & live, []



# --- the feature relation ----------------------------------------------------------------------------------------


@dataclass
class Result:
    features: list[Feature]
    checklist: int
    refs: int


def features_check(root: str, plan_text: str, tasks: dict, superseded: set[str]) -> tuple[Result | None, list[str]]:
    """The feature relation on an already parsed and valid plan: (result, errors)."""
    def read(rel: str) -> str:
        with open(os.path.join(root, rel), encoding="utf-8") as fh:
            return fh.read()

    plan = plan_lanes.Plan(tasks)
    try:
        features, not_features, sources, errors = load_inventory(read(INVENTORY))
    except OSError as exc:
        return None, [f"{INVENTORY}: {exc.strerror or exc}"]
    except UnicodeDecodeError as exc:
        return None, [f"{INVENTORY}: not UTF-8 text (byte {exc.start})"]
    except InventoryError as exc:
        return None, [str(exc)]
    by_id = {f.fid: f for f in features}

    def live(tid: str, who: str) -> bool:
        if tid in tasks:
            return True
        errors.append(f"{who}: {tid} is " + ("superseded" if tid in superseded else "not a task of the plan") +
                      " (use a live task ID of the plan-lanes block)")
        return False

    for f in features:
        f.tasks = [t for t in f.tasks if live(t, f.fid)]
    not_features = {t: why for t, why in not_features.items() if live(t, "not_features")}

    # Split lineage: a task, its split parents (up) and its children (down).
    parent = {c: t.tid for t in tasks.values() if t.split for c in t.deps}

    def up(tid: str) -> list[str]:
        out = [tid]
        while out[-1] in parent:
            out.append(parent[out[-1]])
        return out

    def down(tid: str) -> list[str]:
        t = tasks[tid]
        return [tid] + ([x for c in t.deps for x in down(c)] if t.split else [])

    def related(f: Feature) -> set[str]:
        return {x for t in f.tasks for x in up(t) + down(t)}

    owners_of_task: dict[str, list[str]] = {}
    for f in features:
        for t in f.tasks:
            owners_of_task.setdefault(t, []).append(f.fid)

    def features_of(tid: str) -> list[Feature]:
        lineage = set(up(tid))
        return [f for f in features if lineage & set(f.tasks)]

    def accounted(tid: str) -> bool:
        if any(x in not_features or x in owners_of_task for x in up(tid)):
            return True
        t = tasks[tid]
        return t.split and all(accounted(c) for c in t.deps)

    for tid in sorted(not_features, key=plan_lanes.TID):
        for x in up(tid)[::-1][:-1] + down(tid):
            if x in owners_of_task:
                which = "and is" if x == tid else f"but {x} of its split lineage is"
                errors.append(f"{tid} is in not_features {which} a task of {', '.join(owners_of_task[x])} (pick one)")

    # Every live leaf task is registered.
    for t in sorted(tasks.values(), key=lambda t: plan_lanes.TID(t.tid)):
        if not t.split and not accounted(t.tid):
            errors.append(f"{t.tid} is a live task that registers no feature (add it to a [[feature]] tasks list, "
                          "or to [not_features] with a reason)")

    # Tests: annotations name a feature and a task of its split lineage.
    traces, terr = scan_tests(root)
    errors += terr
    for tr in traces:
        f = by_id.get(tr.fid)
        if f is None:
            errors.append(f"{tr.path}:{tr.line}: @covers-feature names unknown feature {tr.fid}")
        elif tr.tid not in tasks:
            errors.append(f"{tr.path}:{tr.line}: @covers-feature {tr.fid} names {tr.tid}, which is not a live task")
        elif tasks[tr.tid].split:
            errors.append(f"{tr.path}:{tr.line}: {tr.tid} is split: name the child task whose work the test proves "
                          f"({', '.join(tasks[tr.tid].deps)})")
        elif tr.tid not in related(f):
            errors.append(f"{tr.path}:{tr.line}: @covers-feature {tr.fid} names {tr.tid}, which is not a task of "
                          f"{tr.fid} ({', '.join(f.tasks)}) or of their split lineage")
        else:
            f.traces.append(tr)

    # Every feature of every DONE leaf is traced to that very leaf (a split parent is never named, see above).
    untested: dict[str, list[str]] = {}
    for t in sorted(tasks.values(), key=lambda t: plan_lanes.TID(t.tid)):
        if t.split or not t.done:
            continue
        for f in features_of(t.tid):
            if not any(tr.tid == t.tid for tr in f.traces):
                untested.setdefault(f.fid, []).append(t.tid)
    for fid, done in untested.items():
        hint = " ".join(done)
        errors.append(f"{fid}: no test traces DONE task(s) {', '.join(done)} (annotate a test that exercises that "
                      f"task's part: '@covers-feature {fid} {hint}')")

    # Spec cross-reference.
    items: Items = {}
    for src in sources:
        rel = src["path"]
        try:
            items |= (table_source if src["kind"] == "table" else tsv_source)(rel, read(rel), src)
        except OSError as exc:
            errors.append(f"{rel}: {exc.strerror or exc}")
        except UnicodeDecodeError as exc:
            errors.append(f"{rel}: not UTF-8 text (byte {exc.start})")
        except InventoryError as exc:
            errors.append(str(exc))
    claims: dict[str, list[str]] = {}
    for f in features:
        for r in f.refs:
            claims.setdefault(r, []).append(f.fid)
            if not items:
                continue  # every source failed; those errors are reported already
            if r not in items:
                errors.append(f"{f.fid}: unknown ref '{r}' (not an item of the spec inventories)")
            elif items[r] and not items[r] & related(f):
                errors.append(f"{f.fid} claims '{r}', but none of its tasks ({', '.join(f.tasks)}) or their split "
                              f"lineage is among the spec's owners ({', '.join(sorted(items[r], key=plan_lanes.TID))})")
    for r, owners in sorted(claims.items()):
        if len(owners) > 1:
            errors.append(f"ref '{r}' is claimed by {len(owners)} features: {', '.join(owners)} (one feature per item)")
    for r in sorted(items):
        if r not in claims:
            errors.append(f"{r} is claimed by no feature (add it to the refs of the feature that delivers it)")

    # Coverage checklist.
    cited, cerr = checklist_tasks(plan_text, set(tasks))
    errors += cerr
    for tid in sorted(cited, key=plan_lanes.TID):
        if not accounted(tid):
            errors.append(f"the coverage checklist cites {tid}, but no feature or not_features entry accounts for it")

    # Milestone and status of each feature.
    for f in features:
        if not f.tasks:
            continue
        f.ms = max((tasks[t].ms for t in f.tasks), key=lambda ms: int(ms[1:]))
        leaves = [x for t in f.tasks for x in down(t) if not tasks[x].split]
        f.status = ("DONE" if all(plan.complete(t) for t in f.tasks)
                    else "in progress" if any(tasks[x].done for x in leaves) else "TODO")
    return Result(features, len(cited), len(items)), errors


# --- feature report ----------------------------------------------------------------------------------------------------


def counts(fs: list[Feature]) -> tuple[int, int, int, int, int, int, int]:
    return (len(fs), sum(f.origin == "baseline" for f in fs), sum(f.origin == "new" for f in fs),
            sum(f.status == "DONE" for f in fs), sum(f.status == "in progress" for f in fs),
            sum(f.status == "TODO" for f in fs), sum(bool(f.traces) for f in fs))


def scopes(r: Result) -> list[tuple[str, list[Feature]]]:
    mss = sorted({f.ms for f in r.features}, key=lambda m: int(m[1:]))
    return [("all", r.features)] + [(m, [f for f in r.features if f.ms == m]) for m in mss]


def report(r: Result) -> str:
    out = ["#### Feature parity per milestone (a feature's milestone = the latest of its tasks)", "",
           "| Scope | Features | Baseline | New | DONE | In progress | TODO | Traced (≥ 1 test) |", "|---|---|---|---|---|---|---|---|"]
    for scope, fs in scopes(r):
        n, b, new, done, prog, todo, traced = counts(fs)
        out.append(f"| {scope} | {n} | {b} | {new} | {done} | {prog} | {todo} | {traced}/{n} ({plan_lanes.pct(traced, n)}) |")
    out += ["", f"Spec items cross-referenced: {r.refs}; checklist tasks accounted for: {r.checklist}; "
            "unregistered live tasks: 0", "",
            "#### Features", "", "| ID | MS | Origin | Status | Tasks | Tests (file:line task) |", "|---|---|---|---|---|---|"]
    for f in sorted(r.features, key=lambda f: (int(f.ms[1:]), f.fid)):
        tests = ", ".join(f"{t.path}:{t.line} {t.tid}" for t in sorted(f.traces, key=lambda t: (t.path, t.line, plan_lanes.TID(t.tid)))) or "—"
        out.append(f"| {f.fid} | {f.ms} | {ORIGINS[f.origin]} | {f.status} | {', '.join(f.tasks)} | {tests} |")
    return "\n".join(out) + "\n"


def summary(r: Result) -> str:
    n, b, new, done, prog, _todo, traced = counts(r.features)
    per = ", ".join(f"{scope} {c[0]} ({c[3]} DONE, {c[6]} traced)" for scope, fs in scopes(r)[1:] for c in [counts(fs)])
    return (f"features: {n} ({b} from the baseline, {new} new), {done} DONE, {prog} in progress, "
            f"{traced} traced; {r.refs} spec items, {r.checklist} checklist tasks, 0 unregistered live tasks; "
            f"per milestone: {per}")


# --- the other relations -------------------------------------------------------------------------------------------


def cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def bare(cell: str) -> str:
    return cell.strip().strip("`").strip("*").strip("`").strip()


def missing(cell: str | None) -> bool:
    """An absent, empty, dash or `<placeholder>` cell."""
    return cell is None or bare(cell) in NONE or bool(re.fullmatch(r"<[^>]*>", bare(cell)))


def id_list(cell: str) -> list[str]:
    return [] if bare(cell) in NONE else [bare(x) for x in cell.split(",") if bare(x)]


UNREAD: dict[str, str] = {}   # the files a run found special (FIFO, device, socket, directory): never opened


def read(root: str, rel: str) -> str | None:
    """A file's text, or None when it is missing or unreadable, or exists and is not a regular file: one stat first,
    so a FIFO never hangs the check (recorded in UNREAD, reported as a mismatch naming it)."""
    import boa_tool
    try:
        kind = boa_tool.special_kind(os.path.join(root, rel))
    except OSError:
        return None
    if kind is not None:
        UNREAD[slash_rel(os.path.relpath(os.path.join(root, rel), root))] = kind   # relative to the root, as printed
        return None
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def plan_rows(text: str, data: dict | None = None) -> dict[str, dict[str, str | None]]:
    """task id -> {short name of COLUMN_KEYS: its cell, None when the table has no such column}, from every plan table
    (outside the plan block) whose header row names the contract column; the header is resolved by
    markers.plan_header with the loaded markers file (or `data`, for the language self-check). A row whose first cell
    is a task id is a task row, never a header (a cell that happens to equal a column name or an alias). A plan header
    naming one column twice, or a second row of one task in the plan tables (a later table would silently mask the
    first row's gaps), raises markers.MarkersError, its lines named."""
    data = data or _MARKERS
    out: dict[str, dict[str, str | None]] = {}
    first: dict[str, int] = {}   # task id -> the line of its row
    col: dict[str, int] = {}
    head = 0                     # the line of the current plan table's header
    via = ""                     # the alias that made it a plan table ("" when the contract column has its own name)
    in_block = False
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s == plan_lanes.BEGIN:
            in_block = True
        if s == plan_lanes.END:
            in_block = False
            continue
        if in_block or not s.startswith("|"):
            col = {} if not s.startswith("|") else col
            continue
        c = cells(s)
        tid = bare(c[0])
        if not re.fullmatch(TID, tid):
            try:
                found = markers.plan_header(c, data)
            except markers.MarkersError as exc:
                raise markers.MarkersError(f"line {n}: {exc}") from None
            if found is not None:
                col, head = {k: found[key] for k, key in COLUMN_KEYS.items() if key in found}, n
                cell = c[found[COLUMN_KEYS["contract"]]]
                via = cell.strip() if markers.is_alias(COLUMN_KEYS["contract"], cell, data) else ""
            continue
        if col:
            if tid in first:
                fix = (f"rename that table's header, or drop the alias '{via}' (of the contract column) that "
                       "makes it one" if via else "rename that table's header (an archive need not be a plan table) or keep one row")
                raise markers.MarkersError(
                    f"line {n}: {tid} has a second row in a plan table (its first is at line {first[tid]}; the table "
                    f"of line {n} is a plan table because its header, line {head}, names the contract column): one row "
                    f"per task in the plan tables — {fix}")
            first[tid] = n
            out[tid] = {k: (c[col[k]] if k in col and len(c) > col[k] else None) for k in COLUMN_KEYS}
    return out


def contracts(text: str, where: str, mm: list[tuple[str, str]]) -> dict[str, dict[str, str]]:
    lines = text.splitlines()
    b = [i for i, x in enumerate(lines) if x.strip() == C_BEGIN]
    e = [i for i, x in enumerate(lines) if x.strip() == C_END]
    if len(b) != 1 or len(e) != 1 or e[0] < b[0]:
        mm.append(("contract", f"{where}: need exactly one '{C_BEGIN}' … '{C_END}' contracts index"))
        return {}
    out: dict[str, dict[str, str]] = {}
    header: list[str] = []
    for line in lines[b[0] + 1:e[0]]:
        if not line.strip().startswith("|"):
            continue
        c = cells(line)
        if not header:
            header = c
            if header != C_COLUMNS:
                mm.append(("contract", f"{where}: the contracts index columns must be {' | '.join(C_COLUMNS)}"))
                return {}
            continue
        if set(c[0]) <= set("-: "):
            continue
        row = dict(zip(header, c + [""] * (len(header) - len(c))))
        cid = bare(row["ID"])
        if not re.fullmatch(CID, cid):
            mm.append(("contract", f"bad contract id '{cid}' (C-<NAME>: capitals, digits, -)"))
            continue
        if cid in out:
            mm.append(("contract", f"{cid} is listed twice in the contracts index"))
            continue
        out[cid] = row
    return out


def clauses_of(cid: str, text: str, mm: list[tuple[str, str]], where: str) -> set[str]:
    """The clauses of `cid` its contract file defines (see the module docstring), outside fenced code blocks and the
    Changelog section; a clause defined twice is a mismatch, and so is an id of `cid` among the first three words
    after the marker of a line that is not a definition (a definition written in a form the check does not read), and
    a code fence left open (it would hide every line after it)."""
    out: set[str] = set()
    markdown = where.lower().endswith((".md", ".markdown"))
    fence, fence_line = "", 0   # the open fence run (3+ backticks or tildes) and its line, "" outside a fence
    changelog = 0   # the heading level of the Changelog section being skipped, 0 outside it
    for n, line in enumerate(text.splitlines(), 1):
        f = FENCE.match(line)
        if f and (fence or line.count(f.group(1)) < 2):   # a fence opened and closed on one line toggles nothing
            if not fence:
                fence, fence_line = f.group(1), n
            elif f.group(1)[0] == fence[0] and len(f.group(1)) >= len(fence):   # CommonMark: same char, as long
                fence = ""
            continue
        if fence:
            continue
        m = CLAUSE_DEF.match(line)
        if changelog:
            if markdown:   # it ends at the next heading of its level or a clause definition
                h = re.match(r"^(#{1,6})\s", line)
                ends = bool(h and len(h.group(1)) <= changelog) or bool(m)
            else:   # a comment-only file section (YAML, …): it ends at a non-comment line or a clause definition
                ends = not line.lstrip().startswith(("#", "//")) or bool(m)
            if ends:
                changelog = 0
        c = CHANGELOG.match(line)
        if c:
            changelog = len(c.group(1))
        if changelog:
            continue
        if m and m.group(1).split(".", 1)[0] == cid:
            if m.group(1) in out:
                mm.append(("clause", f"{m.group(1)} is defined twice in {where}"))
            out.add(m.group(1))
            continue
        if m:
            continue   # another contract's clause line
        for word in line[MARKER.match(line).end():].split()[:3]:
            w = CLAUSE_ANY.search(word)
            if w and w.group(1).split(".", 1)[0] == cid:
                mm.append(("clause", f"{where}:{n}: {w.group(1)} near the start of a line that does not define it "
                                     f"(start the line with the id: '{w.group(1)} …', '# {w.group(1)}: …', "
                                     f"'### {w.group(1)} — …', '1. {w.group(1)} …' or '| {w.group(1)} | …')"))
                break
    if fence:
        mm.append(("clause", f"{where}:{fence_line}: unclosed code fence — the lines after it are not read"))
    return out


def contract_annotations(root: str) -> tuple[list[tuple[str, str, str, int]], list[str], set[str]]:
    """(contract or clause, task, file, line) of every @covers-contract header line of the tests that run, the
    malformed ones, and the set of those test files."""
    files, _ = test_files(root)
    paths = {rel: kind for rel, kind in files}
    out: list[tuple[str, str, str, int]] = []
    bad: list[str] = []
    for rel, kind in sorted(paths.items()):
        text = read(root, rel) or ""
        for n, line in header(text, kind):
            m = CONTRACT_ANN.match(line)
            if not m:
                continue
            body = CONTRACT_BODY.match(m.group(1))
            if body:
                out.append((body.group(1), body.group(2), rel, n))
            else:
                bad.append(f"{rel}:{n}: malformed annotation (write: @covers-contract <C-ID or clause> <task>)")
    return out, bad, set(paths)


def register_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    lines = text.splitlines()
    start = next((i for i, x in enumerate(lines) if x.startswith("### Residue register")), None)
    if start is None:
        return rows
    header_: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith("#"):
            break
        if not line.startswith("|"):
            if header_ and rows:
                break
            continue
        c = cells(line)
        if not header_:
            header_ = c
            continue
        if set(c[0]) <= set("-: "):
            continue
        rows.append([dict(zip(header_, c)).get(k, "") for k in ("ID", "Owner task", "Removal step")])
    return rows


def spec_defined(ref: str, corpus: str) -> bool:
    """A spec is defined by a heading that STARTS with its id ("### SPEC-M1-1 — …") or by the ID cell (first cell) of a
    table row; a heading that only mentions it, prose, a list or another cell does not define it."""
    word = re.escape(ref) + r"(?![A-Za-z0-9-])"
    return bool(re.search(r"^#{1,6}\s+[`*]*" + word, corpus, re.M)
                or re.search(r"^\|\s*[`*]*" + word + r"[`*]*\s*\|", corpus, re.M))


def pending_lines(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        if FOLD.match(line):
            out = []
        elif (line.startswith("- ") or line.startswith("## ")) and "do not fold" not in line:
            out.append(line.strip())
    return out


def task_owner_and_edges(tasks: dict, leaves: list[str], rows: dict[str, dict[str, str | None]],
                         mm: list[tuple[str, str]]) -> None:
    """Every live leaf lists its edge cases; every live task (split parents included: every plan row) names who
    manages it."""
    for tid in leaves:
        if missing(rows.get(tid, {}).get("edge")):
            mm.append(("task-row", f"{tid}: no edge cases (its Edge cases cell: the cases, or 'none, because …')"))
    for tid in sorted(tasks, key=plan_lanes.TID):
        if missing(rows.get(tid, {}).get("managed")):
            mm.append(("task-row", f"{tid}: no 'Managed by' (the lead, or the sub-lead that runs the task)"))


def check(root: str, close: bool) -> tuple[list[tuple[str, str]], str | None, Result | None]:
    mm: list[tuple[str, str]] = []
    if MARKERS_ERROR:   # the plan columns and the fold marker are unknown: nothing can be judged
        return mm, f"markers: {MARKERS_ERROR}", None
    try:
        main = boa_config.main_of(root)   # the lead dir is the MAIN checkout's, also when --root is a worktree
    except boa_config.ConfigError as exc:
        return mm, str(exc), None
    UNREAD.clear()
    plan_text = read(root, PLAN)
    if plan_text is None:
        kind = UNREAD.get(slash_rel(PLAN))
        return mm, (f"the plan {PLAN} is {kind}, not a regular file: not read" if kind
                    else f"cannot read the plan {PLAN}"), None
    try:
        tasks, superseded, closing, outside, perr = plan_lanes.parse(plan_text)
    except plan_lanes.PlanError as exc:
        return mm, f"plan: {exc}", None
    perr += plan_lanes.validate(tasks, superseded, outside, closing) if not perr else []
    if perr:
        return mm, "plan: " + "; ".join(perr) + " (run plan_lanes.py --check)", None
    plan = plan_lanes.Plan(tasks)
    leaves = sorted((k for k, t in tasks.items() if not t.split), key=plan_lanes.TID)

    spec_text = read(root, CONFIG["BOA_SPEC_FILE"]) or ""
    if not spec_text:
        mm.append(("contract", f"{CONFIG['BOA_SPEC_FILE']}: not found (the specifications and the contracts index)"))
    index = contracts(spec_text, CONFIG["BOA_SPEC_FILE"], mm) if spec_text else {}
    spec_corpus = spec_text + "".join(read(root, os.path.relpath(p, root)) or ""
                                      for p in sorted(glob.glob(os.path.join(root, "docs/specs/**/*.md"), recursive=True)))
    clauses: dict[str, set[str]] = {}
    for cid, row in index.items():
        where = bare(row["Where"])
        text = None if where in NONE else read(root, where)
        clauses[cid] = clauses_of(cid, text, mm, where) if text is not None else set()

    # task -> contract / clause / spec, and the rest of its row
    try:
        rows = plan_rows(plan_text)
    except markers.MarkersError as exc:   # the plan's columns cannot be told apart: nothing of its rows can be judged
        return mm, f"plan {PLAN}: {exc}", None
    task_owner_and_edges(tasks, leaves, rows, mm)
    cites: dict[str, set[str]] = {}
    for tid in leaves:
        raw = rows.get(tid, {}).get("contract")
        if missing(raw):
            mm.append(("task-contract", f"{tid}: no contract or spec (its Contract / spec cell: C-… clauses or "
                                        "contracts, SPEC-… ids, or none: <category> for a task with no external "
                                        "surface)"))
            continue
        raw = raw or ""
        if re.match(r"^\s*none\s*:", bare(raw), re.I):
            cat = bare(raw).split(":", 1)[1].strip()
            if cat not in CATEGORIES:
                mm.append(("task-contract", f"{tid}: 'none: {cat}' is not a category ({', '.join(CATEGORIES)})"))
            if missing(rows[tid].get("acceptance")):
                mm.append(("task-row", f"{tid}: 'none: {cat}' without acceptance criteria (a task with no external "
                                       "surface states its contract as checkable criteria in its Acceptance criteria "
                                       "cell)"))
            continue
        for ref in id_list(raw):
            if re.fullmatch(CID, ref) or re.fullmatch(CLAUSE, ref):
                cid = ref.split(".", 1)[0]
                cites.setdefault(tid, set()).add(cid)
                if cid not in index:
                    mm.append(("task-contract", f"{tid} names {ref}, which is not in the contracts index"))
                elif ref != cid and ref not in clauses[cid]:
                    mm.append(("task-contract", f"{tid} names {ref}, which {cid}'s contract file does not define"))
            elif re.fullmatch(SID, ref):
                if not spec_defined(ref, spec_corpus):
                    mm.append(("task-spec", f"{tid} names {ref}, which no specification defines"))
            else:
                mm.append(("task-contract", f"{tid}: '{ref}' is neither a C- contract or clause nor a SPEC- id"))

    # contracts
    features_text = read(root, INVENTORY) or ""
    fids = set(re.findall(r'^id\s*=\s*"(F-[A-Z0-9-]+)"', features_text, re.M))
    decisions = read(root, CONFIG["BOA_DECISIONS_FILE"]) or ""
    tests_of: dict[str, list[str]] = {}
    for cid, row in index.items():
        ctasks = id_list(row["Tasks"])
        if not ctasks:
            mm.append(("contract", f"{cid}: lists no task"))
        for t in ctasks:
            if t not in tasks:
                mm.append(("contract", f"{cid}: task {t} is not a live task of the plan"))
            elif cid not in cites.get(t, set()) and not tasks[t].split:
                mm.append(("task-contract", f"{cid} lists {t}, but {t}'s Contract / spec cell does not name {cid} "
                                            "or one of its clauses"))
        for t, cs in cites.items():
            if cid in cs and t not in ctasks:
                mm.append(("task-contract", f"{t} names {cid}, but {cid} does not list {t} in its Tasks"))
        where = bare(row["Where"])
        if where in NONE or not os.path.exists(os.path.join(root, where)):
            mm.append(("contract", f"{cid}: its contract file '{where}' does not exist"))
        elif not clauses[cid]:
            mm.append(("contract", f"{cid} defines no clause in {where} (one line per clause, starting with its id: "
                                   f"'{cid}.1 …', '# {cid}.1: …', '### {cid}.1 — …' or '| {cid}.1 | …')"))
        version = bare(row["Version"])
        if not VERSION.fullmatch(version):
            mm.append(("contract", f"{cid}: version '{version}' (numbers: 1, 2, 1.2.0, …)"))
        elif not FIRST_VERSION.fullmatch(version) and not re.search(
                r"(?<![A-Za-z0-9-])" + re.escape(f"{cid} v{version}") + r"(?![A-Za-z0-9_-]|\.\d)", decisions):
            mm.append(("contract", f"{cid}: version {version} has no ADR (an entry of {CONFIG['BOA_DECISIONS_FILE']} "
                                   f"names '{cid} v{version}' with its compatibility impact)"))
        status = bare(row["Status"])
        if status not in ("open", "closed"):
            mm.append(("contract", f"{cid}: status '{status}' (open or closed)"))
        elif status == "closed":
            for t in ctasks:
                if t in tasks and not plan.complete(t):
                    mm.append(("contract", f"{cid} is closed but {t} is not DONE"))
        elif close:
            mm.append(("contract", f"{cid} is still open at close (every contract must be closed)"))
        for f in id_list(row["Features"]):
            if f not in fids:
                mm.append(("contract", f"{cid}: feature {f} is not in {INVENTORY}"))
        tests_of[cid] = id_list(row["Tests"])
        for path in tests_of[cid]:
            if not os.path.isfile(os.path.join(root, path)):
                mm.append(("contract", f"{cid}: test {path} does not exist"))
    anns, bad, running = contract_annotations(root)
    mm += [("contract-test", b) for b in bad]
    annotated: dict[str, set[str]] = {}
    clause_tested: set[str] = set()
    for ref, tid, rel, n in anns:
        cid = ref.split(".", 1)[0]
        if cid not in index:
            mm.append(("contract-test", f"{rel}:{n}: @covers-contract names unknown contract {cid}"))
        elif ref != cid and ref not in clauses[cid]:
            mm.append(("contract-test", f"{rel}:{n}: @covers-contract names {ref}, which {cid}'s contract file does "
                                        "not define"))
        elif tid not in id_list(index[cid]["Tasks"]):
            mm.append(("contract-test", f"{rel}:{n}: @covers-contract {ref} names {tid}, which is not a task of {cid}"))
        else:
            annotated.setdefault(cid, set()).add(slash_rel(rel))
            clause_tested.add(ref)
    for cid in index:
        if not annotated.get(cid):
            mm.append(("contract", f"{cid} has no test (list its contract tests and give each the header "
                                   f"'@covers-contract <{cid} clause> <task>')"))
        for clause in sorted(clauses[cid] - clause_tested):
            mm.append(("clause", f"{clause} has no test that runs (give one the header '@covers-contract {clause} "
                                 "<task>')"))
        for path in tests_of[cid]:
            if not os.path.isfile(os.path.join(root, path)):
                continue
            if slash_rel(path) not in running:
                mm.append(("contract", f"{cid}: test {path} is not a test that runs (outside BOA_TEST_GLOBS, excluded "
                                       "by BOA_TEST_EXCLUDES, or untracked)"))
            elif slash_rel(path) not in annotated.get(cid, set()):
                mm.append(("contract", f"{cid}: test {path} has no '@covers-contract {cid}… <task>' header line"))

    # features: every feature -> task(s) -> test(s)
    result, ferr = features_check(root, plan_text, tasks, superseded)
    mm += [("feature", e) for e in ferr]
    if close:   # close-out: all the work is done and every feature is DONE and traced
        mm += [("task", f"{tid} is still {tasks[tid].status} at close (every live task must be DONE)")
               for tid in leaves if not plan.complete(tid)]
        for f in result.features if result else []:
            if f.status != "DONE":
                mm.append(("feature", f"{f.fid} is {f.status or 'not built (no live task)'} at close (every feature must be "
                                      "DONE)"))
            if not f.traces:
                mm.append(("feature", f"{f.fid} has no test at close (a running test carries '@covers-feature "
                                      f"{f.fid} <task>')"))

    # residue register: owned rows during the work, empty at close
    reg = read(root, CONFIG["BOA_REGISTER_FILE"])
    for n, (rid, owner, removal) in enumerate(register_rows(reg or ""), 1):
        if bare(owner) in NONE:
            mm.append(("residue", f"register row {n} ({rid}): no owner task"))
        if bare(removal) in NONE:
            mm.append(("residue", f"register row {n} ({rid}): no removal step"))
        if close:
            mm.append(("residue", f"register row {n} ({rid}) is still registered at close (the register must be empty)"))

    # open bugs (memory blocks of type bug, current, "Status: open"): each names its owner task; none at close
    try:
        import memory_lint as ml
        import memory_types
        names = memory_types.load().names
        mdir = os.path.join(root, CONFIG.get("BOA_MEMORY_DIR", "memory-bank"))
        for f in ml.files_of([mdir]) if os.path.isdir(mdir) else []:
            for b in ml.parse_blocks(f, read(root, os.path.relpath(f, root)) or "", names)[0]:
                if b.fields.get("type") != "bug" or not b.current or not OPEN_BUG.search(b.text):
                    continue
                rel = slash_rel(os.path.relpath(f, root))
                if not re.search(TID, b.fields.get("keywords", "") + "\n" + b.text):
                    mm.append(("bug", f"{b.mid} ({rel}:{b.line}) is open without an owner task T-NNN: {b.fields.get('brief', '')}"))
                if close:
                    mm.append(("bug", f"{b.mid} ({rel}:{b.line}) is still open at close: {b.fields.get('brief', '')}"))
    except Exception as exc:  # noqa: BLE001  (an unreadable types file is reported, not a crash)
        mm.append(("bug", f"the memory bank could not be read for open bugs: {exc}"))

    # open items and pending folds: the lead dir is the MAIN checkout's, also when --root is a worktree
    lead = CONFIG["BOA_LEAD_DIR"]
    leaddir = os.path.join(main, lead)
    for line in (read(root, os.path.join(leaddir, "open-items.md")) or "").splitlines() if close else []:
        m = re.match(r"^\s*[-*] \[ \]\s*(.*)$", line)
        if m:
            mm.append(("open-item", f"still in the transit queue at close (resolve it into the plan): "
                                    f"{m.group(1)[:140]}"))
    for name in ("plan-additions-pending.md", "owner-rules-pending.md"):
        for line in pending_lines(read(root, os.path.join(leaddir, name)) or ""):
            mm.append(("pending-fold", f"{lead}/{name}: not folded: {line[:140]}"))
    mm += [("unread", f"{rel}: {kind}, not a regular file: not read") for rel, kind in sorted(UNREAD.items())]
    return mm, None, (result if not ferr else None)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    # installed as <project>/.boa/tools/trace_check.py: the project is two levels up
    ap.add_argument("--root", default=os.path.dirname(HOME))
    ap.add_argument("--close", action="store_true", help="close-out: every contract closed, empty register and "
                                                          "transit queue, no open bug")
    ap.add_argument("--report", action="store_true", help="print the feature report first (Markdown)")
    a = ap.parse_args(argv)
    mm, fatal, result = check(a.root, a.close)
    if fatal:
        print(f"trace-check: {fatal}", file=sys.stderr)
        return 2
    if a.report and result is not None:
        sys.stdout.write(summary(result) + "\n\n" + report(result) + "\n")
    for rel, detail in mm:
        print(f"MISMATCH {rel}: {detail}")
    print(f"MISMATCHES: {len(mm)}")
    return 0 if not mm else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
