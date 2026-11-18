#!/usr/bin/env python3
"""Metalearning: the lead's own notes into the inbox, and the lessons that repeat.

Every sub-agent report ends with a metacognitive trace (mistakes, surprises, what slowed it, lessons on the way of
working), written as id-less memory blocks in its lane's .lane-resume/memories.md: they reach the metalearning file
(BOA_METALEARNING_FILE, default memory-bank/10-METALEARNING.md) through the train's fold, never as copies in the
inbox. The lead keeps its own notes and curations in an inbox (<BOA_LEAD_DIR>/metalearning-inbox.md), folded the
same way; a lesson seen twice becomes a rule proposal, a brief line or a tooling task.

Usage:
  python3 -I .boa/tools/metalearning.py append --task lead --role lead [--report FILE]
      For the lead's own notes (a sub-agent's trace goes through its lane's memories, never here). Reads the
      report (FILE, else stdin), takes its trace — the lines under a heading or a bold/label line that
      says "metacognitive trace" (e.g. "## Metacognitive trace", "**Metacognitive trace:**", "Metacognitive
      trace: ..."), up to the next heading or label line — and appends one draft per lesson (an id-less memory block
      rendered by memory_write.py --format-only rules; datetime = now, UTC, `YYYY-MM-DDTHH:MM:SSZ`; env BOA_MEMORY_NOW
      overrides it for tests); the integrator's train fold gives the inbox its ids (memory_write.py --ingest):
          @@@memory brief="<the lesson's first 100 characters>" datetime="<UTC>" keywords="<task> <role> metalearning" type="lesson"
          <the lesson>
          Source: the metacognitive trace of the <role> report of <task>.
          @endmemory
      (bullets and numbering stripped, control characters removed; a lesson over 600 characters keeps its first 600
      and ends with " [cut at 600 characters: the full lesson is in <where>]", never a silent cut: <where> is "the
      report file <absolute FILE>" with --report, else "the <role> report of <task> in the lane journal
      (<BOA_LEAD_DIR>/lanes/<task>.md of the main checkout)", and for --task lead (no lane journal) "the lead's
      session transcript"). The inbox
      is created with a header when missing; the append holds the inbox's lock (boa_lock: the same lock
      memory_write --mark takes when it marks the fold). Exit 1 when the report has
      no trace (the lead asks the agent for one).
  python3 -I .boa/tools/metalearning.py curate [--threshold 0.5]
      Reads the inbox and the curated file (memory blocks; hand-written "- " lines too, outside fenced code), groups the lessons that say the same thing (word-set
      similarity >= threshold, after dropping case, punctuation and common words) and prints every group seen at
      least twice (from different reports) with a proposal kind:
          SEEN <n>x: <the first wording>
            - <each wording, with its source>
            PROPOSE <tooling|rule|brief>: <why>
      tooling when the lesson names a check a tool could make (script, tool, hook, guard, check, lint, test,
      suite, automate), rule when it states an always/never/must, else a brief line. Last line:
      "METALEARNING: <lessons> lesson(s), <groups> repeated, <n> proposal(s)". Exit 0.
Options: --inbox FILE and --curated FILE override the paths (relative to --root, default the project of this file;
the default inbox is in the MAIN checkout's lead dir, also when --root is a worktree, and so is its lock).
Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

sys.dont_write_bytecode = True  # importing the sibling module must leave no __pycache__ behind (zero residue)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_config  # noqa: E402  (sibling module; `python3 -I` leaves the script directory off sys.path)
import boa_lock  # noqa: E402
import memory_lint  # noqa: E402
import memory_write  # noqa: E402

TRACE_HEAD = re.compile(r"metacognitive\s+trace", re.I)
# A heading, or a line that is only a bold/label ("**Label:**", "Label:" with at most five words before the colon).
HEADING = re.compile(r"^\s*(#{1,6}\s|\*\*[^*]+\*\*\s*:?\s*$|[A-Z][\w /-]{0,40}:\s*$)")
LABEL_INLINE = re.compile(r"^\s*(?:#{1,6}\s*)?\**\s*metacognitive\s+trace\s*\**\s*:?\s*\**\s*(.*)$", re.I)
BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
SOURCE = re.compile(r"^Source: the metacognitive trace of the (\S+) report of (\S+)\.$", re.M)
STOP = set("""a an and are as at be been but by can do does for from had has have how i if in into is it its
its' me my no not of on or our so than that the their them then there these they this to too was we were what
when which while who will with would you your one ones only also more most very just about after before each
every any all""".split())
TOOLING = re.compile(r"\b(script|tool|tooling|hook|guard|check|lint|linter|test|suite|automat\w*|grep)\b", re.I)
RULE = re.compile(r"\b(always|never|must|rule|forbid\w*|only)\b", re.I)
LESSON_CAP = 600   # characters of a lesson kept in the inbox; a longer one says it is cut and where the whole is


def capped(lesson: str, where: str) -> str:
    """The lesson as stored: whole, or its first LESSON_CAP characters and a marker naming where the full text is (the
    report's entry in the lane journal), never a silent cut."""
    if len(lesson) <= LESSON_CAP:
        return lesson
    return lesson[:LESSON_CAP] + f" [cut at {LESSON_CAP} characters: the full lesson is in {where}]"


def extract_trace(text: str) -> list[str]:
    """The lessons of the report's metacognitive trace (empty list: none)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not TRACE_HEAD.search(line) or not (HEADING.match(line) or LABEL_INLINE.match(line)):
            continue
        out: list[str] = []
        first = LABEL_INLINE.match(line)
        if first and first.group(1).strip():
            out.append(first.group(1))
        for nxt in lines[i + 1:]:
            if HEADING.match(nxt) and not BULLET.match(nxt):
                break
            out.append(nxt)
        lessons = []
        for raw in out:
            s = BULLET.sub("", raw).strip()
            s = re.sub(r"[\x00-\x1f\x7f]+", " ", s).strip()
            if s:
                lessons.append(s)
        if lessons:
            return lessons
    return []


def words(text: str) -> frozenset[str]:
    return frozenset(w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in STOP)


def similar(a: frozenset[str], b: frozenset[str], threshold: float) -> bool:
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= threshold


def read_lessons(path: str, source: str) -> list[tuple[str, str]]:
    """(lesson, source) of every memory block of a file (a block written by append names its report as the source),
    and of every hand-written '- ' line outside the blocks and outside fenced code blocks (a format example)."""
    bad = memory_lint.special(path)   # one stat before the open: a FIFO never hangs curate
    if bad:
        print(f"metalearning: skipped {bad}", file=sys.stderr)
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        return []
    out = []
    names = memory_lint.memory_types.load().names
    blocks = [b for b in memory_lint.parse_blocks(path, text, names)[0] if b.id is not None] + [
        b for b in memory_lint.parse_blocks(path, text, names, drafts=True)[0] if b.id is None]
    blocks.sort(key=lambda b: b.line)
    inside = {n for b in blocks for n in range(b.line, b.end + 1)}
    for b in blocks:
        m = SOURCE.search(b.text)
        lesson = SOURCE.sub("", b.text).strip()
        out.append((lesson, f"{m.group(2)} {m.group(1)} {b.fields.get('datetime', '')}" if m else source))
    fenced = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced   # a fenced code block (a format example) holds no lesson
        elif n not in inside and not fenced and line.startswith("- "):
            out.append((line[2:].strip(), source))
    return out


def proposal(text: str) -> tuple[str, str]:
    if TOOLING.search(text):
        return "tooling", "a check a tool can make: plan a tooling task so it cannot happen again"
    if RULE.search(text):
        return "rule", "an always/never: propose it for the owner rules"
    return "brief", "a habit: add a line to the common brief"


def curate(lessons: list[tuple[str, str]], threshold: float) -> tuple[list[list[tuple[str, str]]], str]:
    groups: list[list[tuple[str, str]]] = []
    keys: list[frozenset[str]] = []
    for lesson, src in lessons:
        w = words(lesson)
        for n, k in enumerate(keys):
            if similar(w, k, threshold):
                groups[n].append((lesson, src))
                break
        else:
            groups.append([(lesson, src)])
            keys.append(w)
    repeated = [g for g in groups if len({src for _, src in g}) >= 2]
    out = []
    for g in repeated:
        kind, why = proposal(" ".join(lesson for lesson, _ in g))
        out.append(f"SEEN {len(g)}x: {g[0][0]}")
        out += [f"  - {lesson} ({src})" for lesson, src in g]
        out.append(f"  PROPOSE {kind}: {why}")
    out.append(f"METALEARNING: {len(lessons)} lesson(s), {len(repeated)} repeated, {len(repeated)} proposal(s)")
    return repeated, "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    try:
        cfg = boa_config.load()
    except (boa_config.ConfigError, OSError, UnicodeDecodeError) as exc:   # one line naming the bad line, no traceback
        print(f"metalearning: config: {exc}", file=sys.stderr)
        return 2
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ap.add_argument("--inbox")
    ap.add_argument("--curated", default=cfg["BOA_METALEARNING_FILE"])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ap_a = sub.add_parser("append")
    ap_a.add_argument("--task", required=True)
    ap_a.add_argument("--role", required=True)
    ap_a.add_argument("--report")
    ap_c = sub.add_parser("curate")
    ap_c.add_argument("--threshold", type=float, default=0.5)
    a = ap.parse_args(argv)
    try:
        main = boa_config.main_of(a.root)   # the lead dir and the locks are the main checkout's, also from a worktree
    except boa_config.ConfigError as exc:
        print(f"metalearning: {exc}", file=sys.stderr)
        return 2
    inbox = (os.path.join(main, cfg["BOA_LEAD_DIR"], "metalearning-inbox.md") if not a.inbox
             else a.inbox if os.path.isabs(a.inbox) else os.path.join(a.root, a.inbox))
    curated = a.curated if os.path.isabs(a.curated) else os.path.join(a.root, a.curated)
    if a.cmd == "curate":
        if not 0 < a.threshold <= 1:
            print("metalearning: --threshold must be in (0, 1]", file=sys.stderr)
            return 2
        lessons = read_lessons(curated, "curated") + read_lessons(inbox, "inbox")
        sys.stdout.write(curate(lessons, a.threshold)[1])
        return 0
    task_re = boa_config.task_re(cfg)
    if not re.fullmatch(rf"(?:{task_re}|TRAIN-\d+|lead)", a.task) or not re.fullmatch(r"[a-z][a-z-]{0,31}", a.role):
        print(f"metalearning: invalid --task '{a.task}' or --role '{a.role}'", file=sys.stderr)
        return 2
    try:
        now = memory_lint.now_stamp()
    except ValueError as exc:
        print(f"metalearning: {exc}", file=sys.stderr)
        return 2
    try:
        if a.report:
            with open(a.report, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        else:
            text = sys.stdin.read()
    except OSError as exc:
        print(f"metalearning: {exc}", file=sys.stderr)
        return 2
    lessons = extract_trace(text)
    if not lessons:
        print(f"metalearning: no metacognitive trace in the report of {a.task} {a.role}: ask the agent for one",
              file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(inbox) or ".", exist_ok=True)
    bad = memory_lint.special(inbox)   # the inbox is read before the append: a FIFO would hang it
    if bad:
        print(f"metalearning: refused: {bad}", file=sys.stderr)
        return 1
    state = os.path.join(main, cfg.get("BOA_STATE_DIR", ".boa/state"))
    try:
        lock = boa_lock.FileLock(boa_lock.lock_path(state, inbox)).__enter__()
    except boa_lock.LockError as exc:
        print(f"metalearning: {exc}", file=sys.stderr)
        return 1
    with lock, open(inbox, "a+", encoding="utf-8", newline="\n") as fh:
        fh.seek(0)
        if not fh.read(1):
            fh.write("# Metalearning inbox (lead; curated into the metalearning file, see metalearning.py curate; append only through metalearning.py, never edit by hand while memory_write.py --mark runs)\n")
        fh.seek(0, os.SEEK_END)
        if a.report:
            where = f"the report file {os.path.abspath(a.report).replace(os.sep, '/')}"   # `/` on every OS, as the text
        elif a.task == "lead":   # the lead's own notes have no lane journal
            where = "the lead's session transcript"
        else:
            where = (f"the {a.role} report of {a.task} in the lane journal "
                     f"({cfg['BOA_LEAD_DIR'].rstrip('/')}/lanes/{a.task}.md of the main checkout)")
        for lesson in (capped(x, where) for x in lessons):
            fields = {"brief": memory_write.clean(lesson[:100]), "datetime": now,
                      "keywords": f"{a.task} {a.role} metalearning", "type": "lesson"}
            fh.write(memory_write.render(fields, f"{lesson}\nSource: the metacognitive trace of the {a.role} report of {a.task}."))
    os.chmod(inbox, 0o600)
    print(f"metalearning: {len(lessons)} lesson(s) of {a.task} {a.role} appended to {inbox}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
