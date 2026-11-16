#!/usr/bin/env python3
"""BOA markers: the machine-recognised words, defined once (`.boa/markers.json`), and the safe language change.

Purpose:  every phrase a BOA hook or tool recognises in text people write — the report sections and the Leftovers
          section the report capture reads (and its "none"), the review classes, the fold marker of the staging
          files, the plan's column headers — lives in ONE file, English always kept (older reports still parse) plus
          the current product language; `boa language set` switches that language only after every hook recognised
          samples written in it.
When:     read by the report capture (sub-agent stop), lead-status, trace_check and memory_write; run by the lead
          when the product language changes (09 §31, OR-65): `boa language set <lang> --texts FILE` FIRST, reports
          stay English until it passes.
Wire:     nothing: the tools import it; `boa language …` runs it.
Verify:   `boa language check` prints `markers: ok (…)`; `boa language set <lang> --texts FILE` prints "self-check
          passed"; `boa language regen --check` exits 0.
Outputs:  `.boa/markers.json` (rewritten only by `set`); the marker-bearing sections of the installed Markdown files
          (`regen`, also run by `set`).
Limits:   the memory syntax and the standard block syntax (`@@@memory`, `@endmemory`, field and type names, any
          `@@@…`/`@end…` line) are never markers and never translated — the check refuses an entry that redefines
          them; regen writes no runtime directory (the agent copies .boa/agents and .boa/commands into its runtime
          again, as when it wired them).

  boa language show                 the product language and every entry (`<key> = <texts>`), current text first
  boa language check                validate the markers file (exit 1, one line per problem)
  boa language texts <key>          every accepted text of one entry, one per line
  boa language set <lang> --texts FILE
      FILE: a JSON object `{<key>: <text in that language>}` the agent wrote (translated; the user may correct it).
      Every key needs a text (a missing translation is refused), no unknown key, no block syntax. Then the
      self-check feeds every hook samples written in the new language: the report capture (a report with its
      Leftovers section and items, one with Leftovers "none", review classes), the fold marker on a sample staging
      file, the plan's column headers on a sample plan table. Only when all pass is the file rewritten (language =
      <lang>, English kept as aliases) and the marker-bearing sections regenerated; otherwise nothing changes.
      `en` restores English as the current language (the other texts stay aliases).
  boa language [--root DIR] regen [--check]
      Regenerate every section between `<!-- boa:markers:begin keys=<key>,... -->` and `<!-- boa:markers:end -->`
      in the root files of BOA_REGEN_FILES (default AGENTS.md; the agent adds its runtime's instruction file when it
      wires BOA) and every .md under docs/, memory-bank/ and .boa/, in the current language, keeping the file's line
      endings. An unpaired begin or end, or a begin inside an open section, is an error for that file: nothing in
      it is rewritten (exit 1). `--check` rewrites nothing and exits 1 naming each stale file.
The markers file is `<home>/markers.json` (home = the directory holding tools/, `.boa/` in a project); env
BOA_MARKERS names another one (tests). Exit: 0 ok, 1 refused, 2 usage. Python 3.11+ standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.dont_write_bytecode = True  # importing the sibling modules must leave no __pycache__ behind (zero residue)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_config  # noqa: E402  (sibling module; `python3 -I` leaves the script directory off sys.path)

LANG = re.compile(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?")
BLOCK_SYNTAX = re.compile(r"@@@|@end|\b(?:finding|leftover|requirement|memory)\b\s*=")
# The fixed words of the standard blocks; a marker text equal to one of them would redefine a block.
RESERVED = {"@@@memory", "@endmemory", "@@@finding", "@endfinding", "@@@leftover", "@endleftover",
            "@@@requirement", "@endrequirement"}


class MarkersError(Exception):
    pass


def path() -> str:
    return os.environ.get("BOA_MARKERS") or os.path.join(boa_config.HOME, "markers.json")


def problems(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["the markers file is not a JSON object"]
    out = []
    lang = data.get("language")
    if not isinstance(lang, str) or not LANG.fullmatch(lang):
        out.append(f"language: '{lang}' is not a language code (e.g. en, it, pt-BR)")
    marks = data.get("markers")
    if not isinstance(marks, dict) or not marks:
        return out + ["markers: missing or empty"]
    for key, texts in marks.items():
        if not isinstance(texts, dict) or not isinstance(texts.get("en"), str) or not texts["en"].strip():
            out.append(f"{key}: no English text (English is always kept)")
            continue
        for lg, text in texts.items():
            if not LANG.fullmatch(str(lg)) or not isinstance(text, str) or not text.strip():
                out.append(f"{key}.{lg}: not a language code with a non-empty text")
            elif text.strip().lower() in RESERVED or BLOCK_SYNTAX.search(text):
                out.append(f"{key}.{lg}: '{text}' redefines the standard block syntax (always English, never a marker)")
        if isinstance(lang, str) and lang != "en" and lang not in texts:
            out.append(f"{key}: no text for the current language '{lang}'")
    seen: dict[str, str] = {}   # two entries with one text: the hooks could not tell them apart
    for key, texts in marks.items():
        for text in (texts.values() if isinstance(texts, dict) else []):
            if not isinstance(text, str):
                continue
            other = seen.setdefault(text.strip().lower(), key)
            if other != key:
                out.append(f"{key}: '{text}' is also the text of {other} (the hooks could not tell them apart)")
    return out


def load() -> dict:
    p = path()
    try:
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise MarkersError(f"{p}: missing (install it from the package)") from None
    except (OSError, json.JSONDecodeError) as exc:
        raise MarkersError(f"{p}: unreadable ({exc})") from None
    bad = problems(data)
    if bad:
        raise MarkersError(f"{p}: " + "; ".join(bad))
    return data


def texts(key: str, data: dict | None = None) -> list[str]:
    """Every accepted text of an entry: the current language first, then the others, English always among them."""
    data = data or load()
    entry = data["markers"].get(key)
    if entry is None:
        raise MarkersError(f"unknown marker '{key}'")
    first = entry.get(data["language"]) or entry["en"]
    return [first] + [t for t in dict.fromkeys(entry.values()) if t != first]


def regex(key: str, data: dict | None = None) -> str:
    """An alternation of every accepted text (escaped, longest first)."""
    return "(?:" + "|".join(re.escape(t) for t in sorted(texts(key, data), key=len, reverse=True)) + ")"


def fold_regex(data: dict | None = None) -> re.Pattern:
    """THE fold-marker line of a staging file (one `#`, then any accepted text of `fold` as a whole word): the one
    definition every tool uses (memory_write, trace_check, the self-check)."""
    return re.compile(r"^# [^#].*(?<!\w)" + regex("fold", data) + r"(?!\w)")


def self_check(data: dict) -> list[str]:
    """Feeds every hook its own samples written in the data's language (the hooks' own parsers); returns the failures."""
    import lead_status  # noqa: PLC0415  (they import this module)
    import report_capture as rc  # noqa: PLC0415
    import trace_check  # noqa: PLC0415
    fails = []
    lang, t = data["language"], (lambda k: texts(k, data)[0])
    sample = (f"## {t('section.verdict')}\n{lang}\n- [{t('review.blocking')}] a ({t('review.fixed')})\n"
              f"- [{t('review.non_blocking')}] b\n\n## {t('section.leftovers')}\n\n- {lang} one\n\n1. {lang} two\n\n"
              f"## {t('section.memories_used')}\n-\n")
    found, items, _ = rc.leftovers(sample, data)
    if not found or items != [f"{lang} one", f"{lang} two"]:
        fails.append(f"report capture: the Leftovers section '{t('section.leftovers')}' and its loose-list items not "
                     "recognised")
    found, items, none = rc.leftovers(f"{t('section.leftovers')}: {t('leftovers.none')}\n", data)
    if not found or items or not none:
        fails.append(f"report capture: '{t('section.leftovers')}: {t('leftovers.none')}' not read as no leftovers")
    if rc.review_classes(sample, data) != (0, 1):
        fails.append(f"report capture: the review classes '{t('review.blocking')}' / '{t('review.non_blocking')}' "
                     f"(and '{t('review.fixed')}') not read")
    hints = {("reviewer", f"REVIEW {t('verdict.clean')}"): "tester",
             ("tester", f"{t('verdict.green')}"): "integrator (train)",
             ("integrator", f"{t('verdict.merged')}"): "residue check, remove worktree"}
    for (role, verdict), want in hints.items():
        if lead_status.hint_for(role, verdict, data) != want:
            fails.append(f"lead-status: the verdict '{verdict}' of a {role} is not read")
    staging = f"- a line\n# [2000-01-01T00:00:00Z] {t('fold')} TRAIN-001: everything above. Pending below.\n- pending\n"
    if not any(fold_regex(data).match(x) for x in staging.splitlines()):
        fails.append(f"the fold marker '{t('fold')}' is not found in a sample staging file")
    keys = ("plan.contract_column", "plan.acceptance_column", "plan.edge_column", "plan.managed_column")
    plan = ("| ID | Title | MS | " + " | ".join(t(k) for k in keys) + " | Deps |\n|---|---|---|---|---|---|---|---|\n"
            "| T-001 | x | M1 | C-A | ac | edge | lead | — |\n")
    row = trace_check.plan_rows(plan, trace_check.columns_of(data)).get("T-001") or {}
    if row != {"contract": "C-A", "acceptance": "ac", "edge": "edge", "managed": "lead"}:
        fails.append("trace_check: the plan columns " + ", ".join(f"'{t(k)}'" for k in keys) + " not read")
    return fails


# One marker line: a begin (with its keys) or an end, alone on its line, LF or CRLF.
MARK = re.compile(r"^<!-- boa:markers:(?:begin keys=([A-Za-z0-9_.,-]+)|(end)) -->(\r?\n|$)", re.M)
REGEN_DIRS = ("docs", "memory-bank", ".boa")


def regen_files(root: str) -> list[str]:
    """The root files of BOA_REGEN_FILES (default AGENTS.md) and every .md under docs/, memory-bank/ and .boa/."""
    names = boa_config.load().get("BOA_REGEN_FILES", "AGENTS.md").split()
    paths = [os.path.join(root, n) for n in names if os.path.isfile(os.path.join(root, n))]
    for rel in REGEN_DIRS:
        top = os.path.join(root, rel)
        for d, dirs, fs in os.walk(top) if os.path.isdir(top) else []:
            dirs[:] = sorted(x for x in dirs if x not in (".git", "state", "logs", "__pycache__"))
            paths += [os.path.join(d, f) for f in sorted(fs) if f.endswith(".md")]
    return paths


def render_section(keys: str, data: dict) -> str:
    """The body of one marker-bearing section in the data's current language."""
    words = "; ".join(f"{k} = `{texts(k, data)[0]}`" for k in keys.split(",") if k)
    return (f"  Machine-recognised words (`.boa/markers.json`, product language `{data['language']}`; the English "
            f"texts are always accepted too): {words}.\n")


def rewrite_sections(text: str, data: dict) -> str:
    """Every begin/end pair re-rendered (the body keeps the begin line's line ending). Raises MarkersError on a begin
    without its end, an end without its begin, or a begin inside an open section — the file is then left untouched."""
    out, pos, open_m = [], 0, None
    for m in MARK.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        if m.group(2):                        # an end
            if open_m is None:
                raise MarkersError(f"line {line}: an end marker without its begin")
            body = render_section(open_m.group(1), data).replace("\n", open_m.group(3) or "\n")
            out += [text[pos:open_m.end()], body]
            pos, open_m = m.start(), None
        else:
            if open_m is not None:
                raise MarkersError(f"line {line}: a begin marker inside the section opened at line "
                                   f"{text.count(chr(10), 0, open_m.start()) + 1} (no end marker)")
            open_m = m
    if open_m is not None:
        raise MarkersError(f"line {text.count(chr(10), 0, open_m.start()) + 1}: a begin marker without its end")
    return "".join(out) + text[pos:]


def regen(root: str, data: dict, check: bool) -> tuple[list[str], list[str]]:
    """Rewrites (or with check, only lists) the stale marker-bearing sections; returns (changed files, problems)."""
    changed: list[str] = []
    errs: list[str] = []
    for f in regen_files(root):
        try:
            with open(f, encoding="utf-8", newline="") as fh:
                old = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        if "<!-- boa:markers:" not in old:
            continue
        try:
            new = rewrite_sections(old, data)
        except MarkersError as exc:
            errs.append(f"{os.path.relpath(f, root)}: {exc}")
            continue
        if new != old:
            if not check:
                tmp = f"{f}.tmp.{os.getpid()}"
                try:
                    with open(tmp, "w", encoding="utf-8", newline="") as fh:
                        fh.write(new)
                    os.replace(tmp, f)
                except OSError as exc:      # this file stays stale; said, and no temp file left behind
                    errs.append(f"{os.path.relpath(f, root)}: not rewritten ({exc})")
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                    continue
            changed.append(os.path.relpath(f, root))
    return changed, errs


def cmd_set(lang: str, texts_file: str, root: str) -> int:
    if not LANG.fullmatch(lang):
        print(f"markers: '{lang}' is not a language code", file=sys.stderr)
        return 2
    data = load()
    if lang != "en":
        try:
            with open(texts_file, encoding="utf-8") as fh:
                given = json.load(fh)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            print(f"markers: --texts {texts_file}: unreadable ({exc})", file=sys.stderr)
            return 1
        if not isinstance(given, dict):
            print("markers: --texts must be a JSON object {key: text}", file=sys.stderr)
            return 1
        missing = sorted(k for k in data["markers"] if not str(given.get(k) or "").strip())
        unknown = sorted(k for k in given if k not in data["markers"])
        if missing or unknown:
            for k in missing:
                print(f"markers: missing translation for '{k}' (English: {data['markers'][k]['en']})", file=sys.stderr)
            for k in unknown:
                print(f"markers: unknown key '{k}'", file=sys.stderr)
            return 1
        for k, t in given.items():
            data["markers"][k][lang] = str(t).strip()
    data["language"] = lang
    bad = problems(data) or self_check(data)
    if not bad:   # every marker section of the installed files must be rewritable BEFORE anything is written
        for f in regen_files(root):
            try:
                with open(f, encoding="utf-8", newline="") as fh:
                    rewrite_sections(fh.read(), data)
            except MarkersError as exc:
                bad.append(f"{os.path.relpath(f, root)}: {exc} (fix the file, then run set again)")
            except (OSError, UnicodeDecodeError):
                continue
    if bad:
        for b in bad:
            print(f"markers: {b}", file=sys.stderr)
        print("markers: language NOT changed; keep writing reports in the previous language", file=sys.stderr)
        return 1
    p = path()
    tmp = f"{p}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, p)
    print(f"markers: product language = {lang}; self-check passed; English kept as aliases")
    changed, errs = regen(root, data, False)
    for c in changed:
        print(f"markers: regenerated {c}")
    for b in errs:
        print(f"markers: {b}", file=sys.stderr)
    if errs:
        print("markers: language switched; run `boa language regen` to finish (the files above are still stale)",
              file=sys.stderr)
    if changed:
        print("markers: copy .boa/agents and .boa/commands into your runtime's directories again (the wiring step)")
    return 1 if errs else 0


def main(argv: list[str]) -> int:
    if "-h" in argv or "--help" in argv:
        sys.stdout.write(__doc__)
        return 0
    ap = argparse.ArgumentParser(prog="boa language", description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=os.path.dirname(boa_config.HOME), help="the project root (default: the parent of .boa/)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    sub.add_parser("check")
    p = sub.add_parser("texts")
    p.add_argument("key")
    p = sub.add_parser("set")
    p.add_argument("lang")
    p.add_argument("--texts", default="")
    p = sub.add_parser("regen")
    p.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "set":
            if a.lang != "en" and not a.texts:
                print("markers: set <lang> needs --texts FILE (the translated texts)", file=sys.stderr)
                return 2
            return cmd_set(a.lang, a.texts, a.root)
        data = load()
        if a.cmd == "regen":
            changed, errs = regen(a.root, data, a.check)
            for c in changed:
                print(f"markers: {'stale' if a.check else 'regenerated'} {c}")
            for b in errs:
                print(f"markers: {b}", file=sys.stderr)
            return 1 if errs or (a.check and changed) else 0
    except MarkersError as exc:
        print(f"markers: {exc}", file=sys.stderr)
        return 1
    if a.cmd == "texts":
        try:
            print("\n".join(texts(a.key, data)))
        except MarkersError as exc:
            print(f"markers: {exc}", file=sys.stderr)
            return 1
        return 0
    if a.cmd == "check":
        print(f"markers: ok ({len(data['markers'])} entries, language {data['language']})")
        return 0
    print(f"product language: {data['language']}")
    for key in data["markers"]:
        print(f"  {key} = {' | '.join(texts(key, data))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
