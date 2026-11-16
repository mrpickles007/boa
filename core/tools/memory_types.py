#!/usr/bin/env python3
"""Memory types: the ONE definition of the memory types, their routes and recall moments (`.boa/memory-types.json`,
shipped default `core/memory-types.json`; env BOA_MEMORY_TYPES names another file).

Purpose:  the one definition of the memory types, their routes and recall moments, and the doc tables generated
          from it.
When:     whenever a memory type is added or changed (validate, then `--write` the docs); `--stale` in the pre-commit
          and the gate; `--list` when choosing a type.
Wire:     the memory check hook regenerates the tables after a write of the types file; the pre-commit and the gate
          run `--stale`.
Verify:   `python3 -I .boa/tools/memory_types.py --check` says ok with the counts.
Outputs:  the check line, the tables, the list; exit 0 ok, 1 invalid file or stale sections, 2 usage.
Limits:   regenerates only the sections between its marker lines in files git tracks.

Schema `boa/memory-types/1`:
  types[]           {name, records, use_when, must_contain[], route, recall[]}: name `[a-z][a-z0-9-]*`, unique; route =
                    a file of the memory bank (`NN-NAME.md`, no directory); recall = ids of recall_moments
  keyword_routes[]  {keyword, route, priority[, type]}: a memory whose keywords hold `keyword` (and, when given, of
                    that type) goes to `route` instead of its type's route; when several match, the highest integer
                    `priority` wins; two routes with the same priority are a config error (refused), so the winner
                    never depends on the order of the list
  recall_moments[]  {id, when, search_for}: the moments an agent searches the memory; a moment's types are the types
                    whose `recall` names it
Every memory tool (memory_write, memory_lint, memory_search, the memory hooks, the session status) reads types,
routes and recall moments only from this file: a type a project adds here is validated, then allowed everywhere.

Usage:  python3 -I .boa/tools/memory_types.py --check [FILE]          validate (exit 0 ok, 1 invalid)
        python3 -I .boa/tools/memory_types.py --render-tables [FILE]  the Markdown tables for the docs (types, routes,
                                                                     recall moments), generated, never hand-written
        python3 -I .boa/tools/memory_types.py --list [FILE]           one line per type: name, file, what it records
        python3 -I .boa/tools/memory_types.py --write [--types FILE] [DOC...]
                                      rewrite the generated sections of the docs (all three tables between the
                                      BEGIN/END marker lines; one between `<!-- memory-<kind>:begin/end -->`, kind types,
                                      routes or recall)
                                      (default: every tracked file holding one) from the types file
        python3 -I .boa/tools/memory_types.py --stale [--types FILE] [DOC...]
                                      exit 1 naming each doc whose generated section differs (the pre-commit and gate
                                      check); an invalid types file is refused (exit 1) and nothing is rewritten
Python 3 standard library only.
"""

from __future__ import annotations

import json
import os
import re
import sys

HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = "boa/memory-types/1"
NAME = re.compile(r"[a-z][a-z0-9-]*")
ROUTE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.md")

sys.dont_write_bytecode = True   # importing boa_tool must leave no __pycache__ behind (zero residue)


class TypesError(Exception):
    pass


def default_path() -> str:
    return os.environ.get("BOA_MEMORY_TYPES") or os.path.join(HOME, "memory-types.json")


def validate(data: object) -> list[str]:
    errs: list[str] = []
    if not isinstance(data, dict):
        return ["the file must hold one JSON object"]
    extra = sorted(set(data) - {"schema", "types", "keyword_routes", "recall_moments", "_comment"})
    if extra:
        errs.append(f"unknown key(s): {', '.join(extra)}")
    if data.get("schema") != SCHEMA:
        errs.append(f"schema must be '{SCHEMA}'")
    moments = data.get("recall_moments")
    ids: set[str] = set()
    if not isinstance(moments, list) or not moments:
        errs.append("recall_moments must be a non-empty list")
        moments = []
    for n, m in enumerate(moments, 1):
        if not isinstance(m, dict) or set(m) != {"id", "when", "search_for"}:
            errs.append(f"recall_moments #{n}: needs exactly id, when, search_for")
            continue
        if not isinstance(m["id"], str) or not NAME.fullmatch(m["id"]):
            errs.append(f"recall_moments #{n}: bad id {m['id']!r}")
        elif m["id"] in ids:
            errs.append(f"recall moment '{m['id']}' defined twice")
        else:
            ids.add(m["id"])
        for k in ("when", "search_for"):
            if not isinstance(m[k], str) or not m[k].strip():
                errs.append(f"recall moment {m['id']!r}: {k} must be a non-empty string")
    types = data.get("types")
    names: set[str] = set()
    if not isinstance(types, list) or not types:
        errs.append("types must be a non-empty list")
        types = []
    keys = {"name", "records", "use_when", "must_contain", "route", "recall"}
    for n, t in enumerate(types, 1):
        if not isinstance(t, dict):
            errs.append(f"types #{n}: not an object")
            continue
        where = f"type {t.get('name')!r}" if isinstance(t.get("name"), str) else f"types #{n}"
        if set(t) != keys:
            errs.append(f"{where}: needs exactly {', '.join(sorted(keys))}")
            continue
        if not isinstance(t["name"], str) or not NAME.fullmatch(t["name"]):
            errs.append(f"{where}: bad name (lower-case letters, digits, -)")
        elif t["name"] in names:
            errs.append(f"type '{t['name']}' defined twice (names are unique)")
        else:
            names.add(t["name"])
        for k in ("records", "use_when"):
            if not isinstance(t[k], str) or not t[k].strip():
                errs.append(f"{where}: {k} must be a non-empty string")
        if not isinstance(t["must_contain"], list) or not t["must_contain"] or not all(
                isinstance(x, str) and x.strip() for x in t["must_contain"]):
            errs.append(f"{where}: must_contain must be a non-empty list of strings")
        if not isinstance(t["route"], str) or not ROUTE.fullmatch(t["route"]):
            errs.append(f"{where}: route {t['route']!r} must be a file of the memory bank (NN-NAME.md, no directory)")
        if not isinstance(t["recall"], list) or not all(isinstance(x, str) for x in t["recall"]):
            errs.append(f"{where}: recall must be a list of recall moment ids")
        else:
            for x in t["recall"]:
                if x not in ids:
                    errs.append(f"{where}: unknown recall moment '{x}'")
    rules = data.get("keyword_routes", [])
    if not isinstance(rules, list):
        errs.append("keyword_routes must be a list")
        rules = []
    for n, r in enumerate(rules, 1):
        if not isinstance(r, dict) or not {"keyword", "route", "priority"} <= set(r) \
                or not set(r) <= {"keyword", "route", "priority", "type"}:
            errs.append(f"keyword_routes #{n}: needs keyword, route and priority (and optionally type)")
            continue
        if not isinstance(r["priority"], int) or isinstance(r["priority"], bool):
            errs.append(f"keyword_routes #{n}: priority {r['priority']!r} must be an integer")
        if not isinstance(r["keyword"], str) or not r["keyword"].strip():
            errs.append(f"keyword_routes #{n}: empty keyword")
        if not isinstance(r["route"], str) or not ROUTE.fullmatch(r["route"]):
            errs.append(f"keyword_routes #{n}: route {r['route']!r} must be a file of the memory bank")
        if "type" in r and r["type"] not in names:
            errs.append(f"keyword_routes #{n}: unknown type '{r['type']}'")
    # the highest priority wins: equal priorities would leave the winner to the order of the list
    seen: dict[int, str] = {}
    for r in rules:
        if isinstance(r, dict) and isinstance(r.get("priority"), int) and not isinstance(r.get("priority"), bool):
            if r["priority"] in seen:
                errs.append(f"keyword_routes: '{seen[r['priority']]}' and '{r.get('keyword')}' have the same priority "
                            f"{r['priority']} (a memory holding both keywords has no single route)")
            seen.setdefault(r["priority"], str(r.get("keyword")))
    # routes are files: two spellings that differ only in case are one file on a case-insensitive file system
    spelled: dict[str, str] = {}
    for r in [t.get("route") for t in types if isinstance(t, dict)] + [r.get("route") for r in rules if isinstance(r, dict)]:
        if not isinstance(r, str):
            continue
        k = r.lower()
        if k in spelled and spelled[k] != r:
            errs.append(f"routes {spelled[k]!r} and {r!r} differ only in case (one file on a case-insensitive file system)")
        spelled.setdefault(k, r)
    return errs


class Types:
    def __init__(self, data: dict):
        self.data = data
        self.by_name = {t["name"]: t for t in data["types"]}
        self.rules = data.get("keyword_routes", [])
        self.moments = {m["id"]: m for m in data["recall_moments"]}

    @property
    def names(self) -> list[str]:
        return [t["name"] for t in self.data["types"]]

    def route(self, typ: str, keywords: str) -> str:
        words = {w.lower() for w in re.split(r"[,\s]+", keywords) if w}
        hits = [r for r in self.rules if r["keyword"].lower() in words and r.get("type", typ) == typ]
        return max(hits, key=lambda r: r["priority"])["route"] if hits else self.by_name[typ]["route"]

    def moment_types(self, moment: str) -> list[str]:
        return [t["name"] for t in self.data["types"] if moment in t["recall"]]


def load(path: str | None = None) -> Types:
    path = path or default_path()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        raise TypesError(f"{path}: {exc.strerror or exc}") from exc
    except ValueError as exc:
        raise TypesError(f"{path}: not valid JSON: {exc}") from exc
    errs = validate(data)
    if errs:
        raise TypesError(f"{path}: " + "; ".join(errs))
    return Types(data)


def render_parts(t: Types) -> dict[str, str]:
    """The three generated tables, by kind: types, (keyword) routes, recall (moments)."""
    def cell(s: str) -> str:
        return s.replace("|", "\\|")
    ty = ["| type | What it records | Use it when | Must contain | File | Recall moments |", "|---|---|---|---|---|---|"]
    for x in t.data["types"]:
        ty.append(f"| `{x['name']}` | {cell(x['records'])} | {cell(x['use_when'])} | {cell(', '.join(x['must_contain']))} "
                  f"| `{x['route']}` | {', '.join(x['recall']) or '—'} |")
    ro = ["| Keyword | Type | Priority | File |", "|---|---|---|---|"]
    for r in sorted(t.rules, key=lambda r: -r["priority"]):
        ro.append(f"| `{r['keyword']}` | {('`' + r['type'] + '`') if 'type' in r else 'any'} | {r['priority']} "
                  f"| `{r['route']}` |")
    rc = ["| Moment | When | Search for | Types to look at first |", "|---|---|---|---|"]
    for m in t.data["recall_moments"]:
        rc.append(f"| `{m['id']}` | {cell(m['when'])} | {cell(m['search_for'])} | "
                  f"{', '.join('`' + n + '`' for n in t.moment_types(m['id'])) or '—'} |")
    return {"types": "\n".join(ty) + "\n", "routes": "\n".join(ro) + "\n", "recall": "\n".join(rc) + "\n"}


def render_tables(t: Types) -> str:
    """The three tables, separated by a blank line (what --render-tables prints)."""
    p = render_parts(t)
    return p["types"] + "\n" + p["routes"] + "\n" + p["recall"]


BEGIN = "<!-- BEGIN generated: memory types (memory_types.py --write; edit the memory-types file, never this table) -->"
END = "<!-- END generated: memory types -->"
# One table each, where a doc places them apart (the shipped templates and references): the marker lines name the kind.
KIND_MARKERS = {k: (f"<!-- memory-{k}:begin -->", f"<!-- memory-{k}:end -->") for k in ("types", "routes", "recall")}


def _bt():
    """boa_tool, imported on first use (the types file alone needs nothing more)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import boa_tool
    return boa_tool


def regenerate(text: str, t: Types) -> str:
    """`text` with every generated section holding its tables: all three between BEGIN and END, one between the
    marker lines of its kind (memory-types, memory-routes, memory-recall)."""
    parts = render_parts(t)
    try:
        text = _bt().replace_generated(text, BEGIN, END, render_tables(t))
        for kind, (b, e) in KIND_MARKERS.items():
            text = _bt().replace_generated(text, b, e, parts[kind])
        return text
    except ValueError as exc:
        raise TypesError(str(exc)) from exc


def docs_with_sections(root: str) -> list[str]:
    """The files git tracks under `root` that hold a generated section (of any kind)."""
    found: set[str] = set()
    for marker in [BEGIN] + [b for b, _ in KIND_MARKERS.values()]:
        found.update(_bt().tracked_files_with(root, marker))
    return sorted(found)


def checkout_docs(path: str) -> list[str]:
    """The docs with a generated section in the checkout that holds `path` (a lane's own files, never its main's)."""
    return docs_with_sections(_bt().toplevel(path))


def sync_docs(t: Types, docs: list[str], write: bool) -> list[str]:
    """The docs whose generated sections differ from the types file (rewritten when `write`)."""
    stale = []
    for d in docs:
        with open(d, encoding="utf-8", newline="") as fh:
            text = fh.read()
        new = regenerate(text, t)
        if new != text:
            stale.append(d)
            if write:
                _bt().write_atomic(d, new)
    return stale


def main(argv: list[str]) -> int:
    _bt().on_term_exit()   # --write goes through a temp file: a stop still removes it
    usage = ("usage: memory_types.py --check|--render-tables|--list [FILE]\n"
             "       memory_types.py --write|--stale [--types FILE] [DOC...]   (DOC default: the tracked files with a "
             "generated section)")
    if not argv or argv[0] not in ("--check", "--render-tables", "--list", "--write", "--stale"):
        print(usage, file=sys.stderr)
        return 2
    mode, rest = argv[0], argv[1:]
    types_file = None
    if mode in ("--write", "--stale"):
        if rest[:1] == ["--types"]:
            if len(rest) < 2:
                print(usage, file=sys.stderr)
                return 2
            types_file, rest = rest[1], rest[2:]
    elif len(rest) > 1:
        print(usage, file=sys.stderr)
        return 2
    else:
        types_file = rest[0] if rest else None
    try:
        t = load(types_file)
    except TypesError as exc:   # an invalid file is refused: nothing is rewritten, the docs keep the last valid tables
        print(f"memory-types: {exc}", file=sys.stderr)
        return 1
    if mode == "--check":
        print(f"memory-types: ok — {len(t.names)} types, {len(t.moments)} recall moments, {len(t.rules)} keyword routes")
    elif mode == "--render-tables":
        sys.stdout.write(render_tables(t))
    elif mode == "--list":
        for x in t.data["types"]:
            print(f"{x['name']}\t{x['route']}\t{x['records']}")
    else:
        docs = rest or checkout_docs(os.getcwd())
        try:
            stale = sync_docs(t, docs, mode == "--write")
        except (OSError, TypesError) as exc:
            print(f"memory-types: {exc}", file=sys.stderr)
            return 1
        for d in stale:
            print(f"memory-types: {'rewrote' if mode == '--write' else 'stale'} {d.replace(os.sep, '/')}")   # `/` on every OS
        if mode == "--stale" and stale:
            print("memory-types: the generated sections above are stale: run memory_types.py --write", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
