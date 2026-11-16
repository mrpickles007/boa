#!/usr/bin/env -S python3 -I
"""The shell lexer of pause_guard.py: it reads a command line the way bash reads it, far enough to tell its segments
and here-documents apart. Python standard library only; the hooks load this file by path (`python3 -I` keeps their
directory off sys.path). It never runs anything.

split_heredocs() (backslash-newline continuations joined outside single quotes and here-document bodies; each
here-document operator replaced by a placeholder word whose body is in DOCS; a `<<` inside $((...)) or ((...)) is a
shift; comments cut with their newline kept), substitutions() (the bodies of $(...), `...`, <(...), >(...), inside
double quotes too, never inside single quotes; a backquoted span is one piece of a word, replaced by a placeholder
whose body is in SUBS), close_paren() (the end of a `$(`), op_segments() (segments with the operator before each),
heredoc_words() (the words without here-document placeholders, and their bodies).

Bounded: check_deadline() raises TooLong past DEADLINE[0]; every scan is one forward pass.
"""
import re
import shlex
import time

OPERATORS = {";", "&&", "||", "|", "&", "|&", ";;", "(", ")", "\n"}
SEPARATORS = set(";&|()\n")
HEREDOC_OP = re.compile(r"(?<!<)<<(?!<)(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
QUOTES = "'\"`"


class TooLong(Exception):
    """A command or script that cannot be judged within the hook's time: the hook refuses it with this reason."""


DEADLINE = [time.monotonic() + 2.0]   # set by the hook per command
DOCS = {}   # placeholder word -> here-document body (one hook process judges one command)
DOC_WORD = re.compile(r"__boadoc[0-9]+__")
SUBS = {}   # placeholder word -> the body of the backquoted span it stands for


def check_deadline():
    if time.monotonic() > DEADLINE[0]:
        raise TooLong("could not judge this command in time: split it, or put it in a script file")


# --- here-documents, substitutions, segments with operators -----------------------------------------------
def ctx_step(text, i, stack):
    """One step of bash's quoting over text[i]; returns the index after it. stack holds the open contexts, innermost
    last, and is changed in place: ' and " (quotes), ` (a backquoted command, to its closing unescaped backquote),
    ( (the inside of $(, <( or >(, or of a parenthesis within one). A `$(` or a backquote opens a new context inside
    double quotes too, as in bash: in `"$(echo " #")"` the inner quotes are the command's own."""
    c, top = text[i], (stack[-1] if stack else None)
    if top == "'":
        if c == "'":
            stack.pop()
    elif c == "\\":
        return i + 2
    elif top == "`":
        if c == "`":
            stack.pop()
    elif c == "`":
        stack.append(c)
    elif c == "$" and text.startswith("(", i + 1):
        stack.append("(")
        return i + 2
    elif top == '"':
        if c == '"':
            stack.pop()
    elif c in "'\"":
        stack.append(c)
    elif c in "<>" and text.startswith("(", i + 1):
        stack.append("(")
        return i + 2
    elif top == "(" and c == "(":
        stack.append(c)
    elif top == "(" and c == ")":
        stack.pop()
    return i + 1


def is_comment(text, i):
    """A `#` at the start of a word, in command context."""
    return text[i] == "#" and (i == 0 or text[i - 1] in " \t\n;&|(")


def scan(s, stack):
    """One forward pass over a line from the quoting contexts `stack` (ctx_step; left as they are at the line's end):
    (the positions of `<<` in command context (outside quotes, backquotes, comments and arithmetic; inside $(...)
    too), whether it ends in a backslash that continues it, where a comment starts or None). A backquoted span is
    skipped to its closing unescaped backquote, as bash reads it: a `#` or a `<<` in it belongs to its own text
    (substitutions() judges it), not to this line."""
    ops, i, n, cont = [], 0, len(s), False
    while i < n:
        top = stack[-1] if stack else None
        if top in (None, "(") and is_comment(s, i):
            return ops, False, i
        if top not in ("'", "`") and (s.startswith("$((", i) or (
                top in (None, "(") and s.startswith("((", i) and (i == 0 or s[i - 1] in " \t;&|("))):
            end = s.find("))", i + 2)   # arithmetic: a `<<` in it is a shift, not a here-document
            i = n if end < 0 else end + 2
            continue
        if top in (None, "(") and s.startswith("<<", i):
            if not s.startswith("<<<", i):
                ops.append(i)
            i += 3 if s.startswith("<<<", i) else 2
            continue
        if s[i] == "\\" and top != "'":
            cont = i == n - 1
        i = ctx_step(s, i, stack)
    return ops, cont, None


def split_heredocs(text):
    """The text with backslash-newline continuations joined (outside single quotes and here-document bodies,
    as bash does) and each here-document operator replaced by a placeholder word whose body is in DOCS;
    and [(body, delimiter quoted)]."""
    lines, out, docs, i, ctx = text.split("\n"), [], [], 0, []   # ctx: the open quoting contexts (scan)
    while i < len(lines):
        check_deadline()
        pieces, start_top = [lines[i]], ctx[-1:]
        i += 1
        ops, cont, comment = scan(pieces[-1], ctx)
        offset, all_ops = 0, list(ops)
        while cont and ctx[-1:] != ["'"] and i < len(lines):
            offset += len(pieces[-1]) - 1
            pieces[-1] = pieces[-1][:-1]
            pieces.append(lines[i])
            i += 1
            ops, cont, comment = scan(pieces[-1], ctx)
            all_ops.extend(offset + p for p in ops)
        line = "".join(pieces)
        if comment is not None:   # cut here; the newline stays, so the next line is a command of its own
            line = line[:offset + comment]
        if start_top and start_top[0] in QUOTES:   # a line that starts inside a quoted string: no operator is recognised
            all_ops = []
        parts, last, found = [], 0, []
        for p in all_ops:
            m = HEREDOC_OP.match(line, p)
            if not m or p < last:
                continue
            word = "__boadoc%d__" % len(DOCS)
            DOCS[word] = None
            parts.append(line[last:m.start()] + " " + word + " ")
            last = m.end()
            found.append((m, word))
        parts.append(line[last:])
        out.append("".join(parts))
        for m, word in found:
            body = []
            while i < len(lines):
                cur = lines[i]
                i += 1
                if (cur.lstrip("\t") if m.group(1) else cur).strip() == m.group(3):
                    break
                body.append(cur)
            DOCS[word] = "\n".join(body)
            docs.append((DOCS[word], bool(m.group(2))))
    return "\n".join(out), docs


def close_paren(text, j):
    """The index of the `)` that closes the $(, <( or >( whose body starts at j (len(text) if none), the body read
    as bash reads it (ctx_step): its quotes, the substitutions nested in them, its comments."""
    stack, n = ["("], len(text)
    while j < n:
        if stack[-1] == "(" and is_comment(text, j):
            nl = text.find("\n", j)
            j = n if nl < 0 else nl
            continue
        if stack == ["("] and text[j] == ")":
            return j
        j = ctx_step(text, j, stack)
    return n


def substitutions(text, heredoc=False):
    """(the bodies of $(...), `...`, <(...), >(...): unquoted or in double quotes (in a here-document body: quotes
    are literal there), never in single quotes or a comment; the text with each backquoted span replaced by a
    placeholder word whose body is in SUBS). bash reads a backquoted span as one piece of a word, to its closing
    backquote, lines and here-documents in it included: its body is judged by the caller, never as lines of the
    text around it; where its output is a list (xargs, a for list, find roots) listed_words() reads its words."""
    bodies, parts, last, i, q, n = [], [], 0, 0, None, len(text)
    while i < n:
        c = text[i]
        if q == "'":
            q = None if c == "'" else q
        elif c == "\\":
            i += 1
        elif not heredoc and c == "'" and q is None:
            q = "'"
        elif not heredoc and c == '"':
            q = None if q == '"' else '"'
        elif c == "`":
            j = i + 1
            while j < n and text[j] != "`":
                j += 2 if text[j] == "\\" else 1
            word = "__boasub%d__" % len(SUBS)
            SUBS[word] = text[i + 1:j]
            bodies.append(SUBS[word])
            parts.append(text[last:i] + word)
            last, i = j + 1, j
        elif text.startswith("(", i + 1) and (c == "$" or (c in "<>" and q is None and not heredoc)) \
                and not text.startswith("((", i + 1):
            j = close_paren(text, i + 2)
            bodies.append(text[i + 2:j])
            i = j
        elif q is None and not heredoc and is_comment(text, i):
            nl = text.find("\n", i)
            i = n if nl < 0 else nl
        i += 1
    parts.append(text[last:])
    return bodies, "".join(parts)


def op_segments(text):
    """[(words, the operator before it)]: quote-aware words, comments already cut by split_heredocs()."""
    lex = shlex.shlex(text, posix=True, punctuation_chars="();<>|&\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    out, seg, op = [], [], None
    for tok in lex:
        if tok in OPERATORS or set(tok) <= SEPARATORS:
            if seg:
                out.append((seg, op))
            seg, op = [], tok
        else:
            seg.append(tok)
    if seg:
        out.append((seg, op))
    return out


def heredoc_words(words):
    """(the words without here-document placeholders, the bodies they stand for)."""
    return [w for w in words if not DOC_WORD.fullmatch(w)], [DOCS.get(w) or "" for w in words if DOC_WORD.fullmatch(w)]
