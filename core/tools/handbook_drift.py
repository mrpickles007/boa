#!/usr/bin/env python3
"""handbook_drift.py — the agent-handbook drift check of a BOA project (rule OR-26).

Usage: python3 -I .boa/tools/handbook_drift.py [--root DIR]

Checks, in the project at DIR (default: the current directory), that docs/agent-handbook.md is the complete and
correct map of the installed tooling:
  undocumented     a file under .boa/{bin,hooks,tools,stack,agents,commands}/ (any depth) is not named
  missing-path     the handbook names a .boa/ path that does not exist
  no-card          a file under .boa/bin/, .boa/hooks/ or .boa/tools/ (a kept tool, or a library) is named on no tool
                   card's "Files:" line
  card-incomplete  a tool card lacks one of its fields (Files, Purpose, When, Wire, Verify, Limits) or leaves it empty
  stack-rows       the handbook's stack block (<!-- boa:stack-rows:begin/end -->) is missing or differs from
                   .boa/stack/handbook-rows.md, or the stack plug-in ships no handbook-rows.md
  no-link          AGENTS.md does not link docs/agent-handbook.md
  no-pointer       memory-bank/RESUME.md does not point to AGENTS.md
  no-section       a role contract (.boa/agents/*.md) has no "## Agent handbook" section
  section-without-handbook   that section never names docs/agent-handbook.md
  broken-link      a relative link in AGENTS.md or the handbook does not resolve
A tool card is a "#### Tool card: <name>" heading followed, up to the next heading, by the field lines
"- Files:" (the backticked paths the card covers), "- Purpose:", "- When:", "- Wire:", "- Verify:" and "- Limits:".
The check knows no agent runtime: the agent's runtime files (its renderings of the agents and commands, its settings,
its instruction file) are the agent's own wiring and are checked by the project (BOA's references/runtimes.md); a
path outside .boa/ named in the handbook is not checked.
A path counts as named when it appears whole: letters, digits and _ . / - only, bounded by any other character.
Machine-local files (__pycache__, *.pyc, .DS_Store) are ignored.

Output: one "drift: <kind>: <detail>" line per finding, then "SUMMARY: <n> drift finding(s)".
Exit status: 0 no drift, 1 drift found, 2 usage or unreadable project.
Read-only; Python 3 standard library only.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

sys.dont_write_bytecode = True

HANDBOOK = "docs/agent-handbook.md"
TOOL_DIRS = (".boa/bin", ".boa/hooks", ".boa/tools", ".boa/stack", ".boa/agents", ".boa/commands")
CARD_DIRS = (".boa/bin", ".boa/hooks", ".boa/tools")
CARD_FIELDS = ("Files", "Purpose", "When", "Wire", "Verify", "Limits")
CARD = re.compile(r"^#### Tool card: *(.*?) *\n(.*?)(?=^#|\Z)", re.M | re.S)
STACK_BLOCK = re.compile(r"<!-- boa:stack-rows:begin -->\n(.*?)<!-- boa:stack-rows:end -->", re.S)
IGNORED_NAMES = {"__pycache__", ".DS_Store"}
NAME_CHARS = r"A-Za-z0-9_./-"
PATH_TOKEN = re.compile(r"(?<![" + NAME_CHARS + r"])(\.boa/[" + NAME_CHARS + r"]*)")
LINK = re.compile(r"\]\(([^)\s]+)\)")


def read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return None


def named(text: str, path: str) -> bool:
    pattern = r"(?<![" + NAME_CHARS + r"])" + re.escape(path) + r"(?![" + NAME_CHARS + r"])"
    return re.search(pattern, text) is not None


def tool_files(root: str, dirs: tuple[str, ...]) -> list[str]:
    """The files under dirs (any depth), as handbook paths: relative to root, written with '/' on every OS."""
    found: list[str] = []
    for rel_dir in dirs:
        base = os.path.join(root, rel_dir)   # a "/"-written relative path: every OS accepts it
        for current, subdirs, files in os.walk(base):
            subdirs[:] = sorted(d for d in subdirs if d not in IGNORED_NAMES)
            for name in sorted(files):
                if name in IGNORED_NAMES or name.endswith(".pyc"):
                    continue
                found.append(pathlib.Path(os.path.relpath(os.path.join(current, name), root)).as_posix())
    return found


def cards(handbook: str) -> tuple[set[str], list[str]]:
    """(every path a tool card's Files line names, the card-incomplete findings)."""
    covered: set[str] = set()
    findings: list[str] = []
    for match in CARD.finditer(handbook):
        name, body = match.group(1) or "(no name)", match.group(2)
        fields = {m.group(1): m.group(2).strip() for m in re.finditer(r"^- (\w+):(.*)$", body, re.M)}
        missing = [f for f in CARD_FIELDS if not fields.get(f)]
        if missing:
            findings.append(f"card-incomplete: {name}: no {', '.join(missing)}")
        covered |= set(re.findall(r"`([^`]+)`", fields.get("Files", "")))
    return covered, findings


def check(root: str) -> list[str]:
    findings: list[str] = []
    handbook = read(os.path.join(root, HANDBOOK))
    if handbook is None:
        return [f"missing-path: {HANDBOOK} (the handbook itself)"]

    for rel in tool_files(root, TOOL_DIRS):
        if not named(handbook, rel):
            findings.append(f"undocumented: {rel}")
    covered, incomplete = cards(handbook)
    findings += incomplete
    for rel in tool_files(root, CARD_DIRS):
        if rel not in covered:
            findings.append(f"no-card: {rel}")

    for token in sorted(set(PATH_TOKEN.findall(handbook))):
        path = token.rstrip("/.")
        if path == ".boa":
            continue
        if not os.path.exists(os.path.join(root, path)):
            findings.append(f"missing-path: {path}")

    agents_md = read(os.path.join(root, "AGENTS.md")) or ""
    if HANDBOOK not in agents_md:
        findings.append("no-link: AGENTS.md does not link docs/agent-handbook.md")
    text = read(os.path.join(root, "memory-bank", "RESUME.md"))
    if text is None or "AGENTS.md" not in text:
        findings.append("no-pointer: memory-bank/RESUME.md does not point to AGENTS.md")

    agents_dir = os.path.join(root, ".boa", "agents")
    names = sorted(n for n in os.listdir(agents_dir) if n.endswith(".md")) if os.path.isdir(agents_dir) else []
    for name in names:
        text = read(os.path.join(agents_dir, name)) or ""
        match = re.search(r"^## Agent handbook[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        if match is None:
            findings.append(f"no-section: .boa/agents/{name}")
        elif HANDBOOK not in match.group(1):
            findings.append(f"section-without-handbook: .boa/agents/{name}")

    if os.path.isdir(os.path.join(root, ".boa", "stack")):
        rows = read(os.path.join(root, ".boa", "stack", "handbook-rows.md"))
        block = STACK_BLOCK.search(handbook)
        if rows is None:
            findings.append("stack-rows: the stack plug-in ships no .boa/stack/handbook-rows.md")
        elif block is None:
            findings.append("stack-rows: the handbook has no stack block")
        elif block.group(1).strip() != rows.strip():
            findings.append("stack-rows: the handbook's stack block differs from .boa/stack/handbook-rows.md")

    for rel, text in (("AGENTS.md", agents_md), (HANDBOOK, handbook)):
        base = os.path.dirname(os.path.join(root, rel))
        for target in LINK.findall(text):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            path = target.split("#", 1)[0]
            if path and not os.path.exists(os.path.normpath(os.path.join(base, path))):
                findings.append(f"broken-link: {rel} -> {target}")
    return findings


def main(argv: list[str]) -> int:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import boa_config  # noqa: F401,E402  (its import makes stdin, stdout and stderr UTF-8: boa_config.utf8_stdio)
    root = "."
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg == "--root" and args:
            root = args.pop(0)
        elif arg in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            print(f"usage: handbook_drift.py [--root DIR] (unknown argument: {arg})", file=sys.stderr)
            return 2
    if not os.path.isdir(root):
        print(f"handbook_drift.py: not a directory: {root}", file=sys.stderr)
        return 2
    findings = check(root)
    for finding in findings:
        print(f"drift: {finding}")
    print(f"SUMMARY: {len(findings)} drift finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
