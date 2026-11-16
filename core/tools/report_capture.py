"""BOA report capture: a sub-agent's Leftovers go to the transit queue, a missing Leftovers section is flagged.

Purpose:  forget nothing (OR-25): every line an agent leaves under its report's Leftovers section reaches the lead's
          transit queue `<lead dir>/open-items.md` the moment the agent stops, so the next fold places it in the plan;
          a task agent's report without a Leftovers section is flagged (queued for the lead, and the hook's warning),
          and a reviewer's non-blocking findings with no blocking one left are queued to be fixed or relocated.
When:     called by the sub-agent stop hook (subagent_stop.py) after the report is journaled; never run on its own.
Wire:     nothing beyond the stop hook: it reads only the neutral event's `last_message` (references/hook-contract.md),
          whatever the runtime.
Verify:   a neutral `subagent-stop` event whose `last_message` ends with "Leftovers:\n- x" adds
          `- [ ] <time> (owner: <task>) <type> <id>: leftover: x` to `<lead dir>/open-items.md`.
Outputs:  `- [ ]` lines appended (under the file's lock) to `<lead dir>/open-items.md`; the warning text for the hook.
Limits:   it recognises sections by the labels of `.boa/markers.json` (every accepted language, English always): a
          label line alone (a heading, optionally numbered, optionally bold, optionally with a colon) or `Label: text`;
          the Leftovers items are the bullet or text lines under it, up to the next heading, section label or blank
          line after an item; an item in an older block form, `@@@leftover none` (or `@@@leftover` + a "none" word),
          is an explicit none and a bare `@endleftover` line is no item; a queued item longer than 300 characters is
          cut and says so, naming the journal file
          that holds the whole report. An agent with no task (a runtime helper) is never flagged; its Leftovers are
          still queued.
"""

from __future__ import annotations

import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_tool as bt  # noqa: E402
import markers  # noqa: E402

ITEM_CAP = 300
BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")


def _label_re(labels: list[str]) -> re.Pattern:
    alt = "|".join(re.escape(x) for x in sorted(labels, key=len, reverse=True))
    return re.compile(r"^\s*(?:#{1,6}\s*)?(?:\d+[.)]\s*)?(?:\*\*)?(?:" + alt + r")(?:\*\*)?\s*"
                      r"(?::\s*(?:\*\*)?\s*(.*?))?\s*$", re.IGNORECASE)


def _all_labels(data: dict) -> list[str]:
    return [t for k in data["markers"] if k.startswith("section.") for t in markers.texts(k, data)]


OLD_BLOCK = re.compile(r"^@@@leftover\b\s*", re.IGNORECASE)   # an older block form: `@@@leftover none` … `@endleftover`


def _is_none(text: str, data: dict) -> bool:
    text = OLD_BLOCK.sub("", text.strip())
    return text.strip(".").strip().lower() in {t.lower() for t in markers.texts("leftovers.none", data)}


def _is_end(text: str) -> bool:
    return text.strip().lower() == "@endleftover"


HEADING = re.compile(r"^\s*(#{1,6})\s")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
RULE = re.compile(r"^\s*(?:(?:-\s*){3,}|(?:\*\s*){3,}|(?:_\s*){3,})$")


def fences(lines: list[str]) -> list[bool]:
    """For each line: True when it is a code-fence line or inside a fenced block (``` or ~~~; a backtick fence's info string
    holds no backtick (``` x ``` is inline code); a fence closes only on
    a fence of the same character, at least as long, with nothing after it; an unclosed fence runs to the end)."""
    out, open_f = [], None
    for x in lines:
        m = FENCE.match(x)
        if open_f is None:
            if m and m.group(1)[0] == "`" and "`" in m.group(2):
                m = None                 # a backtick in a backtick fence's info string: inline code, not a fence
            if m:
                open_f = (m.group(1)[0], len(m.group(1)))
            out.append(bool(m))
        else:
            out.append(True)
            if m and m.group(1)[0] == open_f[0] and len(m.group(1)) >= open_f[1] and not m.group(2).strip():
                open_f = None
    return out


def leftovers(text: str, data: dict) -> tuple[bool, list[str], bool]:
    """(a Leftovers section was found, the items of every Leftovers section, an explicit "none" was given).

    A section runs from its label to the next heading of the same or a higher level (any heading when the label is
    not a heading itself), the next known section label, a horizontal rule, or a blank line followed by something that is not a list
    item or an indented continuation: a loose list (blank lines between items), a numbered list and sub-headings
    inside the section are read whole; code-fenced lines (``` or ~~~) are skipped, never a boundary or an item. An inline text after the label ("Leftovers: x") is an item only when no
    Leftovers section of the report lists items (so "Leftovers: see below" never hides the list below)."""
    head, other = _label_re(markers.texts("section.leftovers", data)), _label_re(_all_labels(data))
    lines = text.splitlines()
    code = fences(lines)               # code-block lines are never labels, boundaries or items
    nxt_sig = [len(lines)] * (len(lines) + 1)   # the next line that is neither blank nor code, in one pass
    for k in range(len(lines) - 1, -1, -1):
        nxt_sig[k] = nxt_sig[k + 1] if (not lines[k + 1:k + 2] or code[k + 1] or not lines[k + 1].strip()) else k + 1
    found = explicit_none = False
    items: list[str] = []
    inline: list[str] = []
    i = 0
    while i < len(lines):
        m = None if code[i] else head.match(lines[i])
        if not m:
            i += 1
            continue
        found = True
        h = HEADING.match(lines[i])
        level = len(h.group(1)) if h else 0
        text_inline = (m.group(1) or "").strip()
        if text_inline:
            if _is_none(text_inline, data):
                explicit_none = True
            else:
                inline.append(text_inline)
        sec: list[str] = []
        j = i + 1
        while j < len(lines):
            line, s = lines[j], lines[j].strip()
            if code[j]:
                j += 1
                continue
            if RULE.match(line):            # a horizontal rule ends the section
                break
            hm = HEADING.match(line)
            if hm and (level == 0 or len(hm.group(1)) <= level):
                break
            if head.match(line) or other.match(line):
                break
            if hm:                         # a sub-heading inside the section: context, not an item
                j += 1
                continue
            if not s:
                nxt = lines[nxt_sig[j]] if nxt_sig[j] < len(lines) else ""
                if sec and not (BULLET.match(nxt) or nxt[:1].isspace() or HEADING.match(nxt)):
                    break
                j += 1
                continue
            b = BULLET.match(line)
            if b:
                sec.append(b.group(1).strip())
            elif sec and line[:1].isspace():
                sec[-1] += " " + s          # a continuation line of the item above
            elif _is_none(s, data) and not sec:
                explicit_none = True
            else:
                sec.append(s)
            j += 1
        explicit_none = explicit_none or any(_is_none(x, data) for x in sec)
        items += [x for x in sec if x and not _is_none(x, data) and not _is_end(x)]
        i = j
    return found, (items or inline), explicit_none


def review_classes(text: str, data: dict) -> tuple[int, int]:
    """(blocking, non-blocking) open findings: the `[<class>` tags of the reviewer's findings list (any case); lines
    marked resolved or fixed (markers review.resolved / review.fixed) are left out."""
    done = re.compile(r"(?<!\w)(?:" + markers.regex("review.resolved", data) + "|" + markers.regex("review.fixed", data)
                      + r")(?!\w)", re.IGNORECASE)
    live = "\n".join(x for x in text.splitlines() if not done.search(x))

    def count(key: str) -> int:
        return len(re.findall(r"\[\s*" + markers.regex(key, data) + r"(?![\w-])", live, re.IGNORECASE))
    return count("review.blocking"), count("review.non_blocking")


def capture(report: str, task: str, atype: str, aid: str, env: bt.Env, now: int) -> str:
    """Queues the report's Leftovers (and what is flagged) in <lead dir>/open-items.md; returns the warning or ""."""
    data = markers.load()
    lead = env.path(env["BOA_LEAD_DIR"])
    journal = f"{env['BOA_LEAD_DIR']}/lanes/{task}.md"
    is_task = bool(re.fullmatch(r"(?:" + bt.TASK_RE + r"|" + bt.TRAIN_RE + r")", task))
    found, items, explicit_none = leftovers(report, data)
    head = f"- [ ] {bt.utc(now)} (owner: {task if is_task else 'lead'}) {task} {atype} {aid or 'unknown'}:"

    def line(text: str) -> str:
        text = " / ".join(x.strip() for x in text.splitlines() if x.strip())
        if len(text) > ITEM_CAP:
            text = text[:ITEM_CAP] + f"… [cut at {ITEM_CAP} characters: the whole report is in {journal}]"
        return f"{head} {text}\n"

    out, warn = [], ""
    label = markers.texts("section.leftovers", data)[0]
    if is_task and not found:
        warn = (f"BOA report capture: the report of {atype} ({task}) has no '{label}' section: resume the same agent to "
                f"add it (its report is in {journal})")
        out.append(line(f"report without a '{label}' section: resume the same agent to add it"))
    elif is_task and not items and not explicit_none:
        warn = (f"BOA report capture: the '{label}' section of {atype} ({task}) is empty (no item, no "
                f"'{markers.texts('leftovers.none', data)[0]}'): resume the same agent to fill it (its report is in {journal})")
        out.append(line(f"report with an empty '{label}' section: resume the same agent to fill it"))
    out += [line(f"leftover: {x}") for x in items]
    if atype == "reviewer":
        blocking, non_blocking = review_classes(report, data)
        if non_blocking and not blocking:
            out.append(line(f"{non_blocking} non-blocking finding(s) with no blocking one left: fix each in the lane "
                            f"or relocate it to a named task (see {journal})"))
    if out:
        os.makedirs(lead, exist_ok=True)
        bt.append_locked(os.path.join(lead, "open-items.md"), "".join(out), wait=3)
    return warn
