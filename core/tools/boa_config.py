"""BOA config for the Python tools: the one config.env reader and the main-checkout finder.

`parse(text)` is the ONE reader of config.env for the tools: every Python tool, the lead and lane hooks, boa.py (the
interpreter switch) and the renderer (which `boa install` runs, so an installed config is always in this grammar) read
the file through it, so a value is never read two ways; the safety hooks' config module (hooks/hook_config.py) loads
this file by path and reads through it too (a line outside the grammar makes the guards refuse every call). The file
is bash-sourceable and read, never executed. Accepted line shapes:
blank, `# comment`, `KEY=value` (unquoted: no spaces, quotes, `$`, backtick, `\\`, `;`, `&`, `|`, `<`, `>`, `(`, `)`,
`~`), `KEY='value'` (single quotes; a literal quote is written `'\\''`) and `KEY="value"` (double quotes, no `$`,
backtick, `\\` or `"` inside); only `BOA_[A-Z0-9_]+` keys; a key defined twice, any other line (leading blanks,
`export`, a trailing comment, a CR of a CRLF file, a value bash would expand) raises ConfigError naming the line. A
leading byte-order mark is ignored.
`load()` returns every BOA_* key: the environment wins, then `<home>/config.env` (env BOA_CONFIG overrides the path;
home = the directory holding tools/), then the defaults below.
`main_of(dir)`: the main checkout of the repository `dir` belongs to absolute.
`dir` itself unless it is the top of a LINKED worktree (`--git-dir` differs from `--git-common-dir`; a plain checkout,
a submodule checkout and a directory that is not the top of a checkout — a fixture inside a repository — are their
own main). For a linked worktree: the common dir's `core.worktree` when set (relative to the common dir or absolute;
a worktree of a submodule: git names the module's git dir as its main worktree), else the first entry of `git worktree
list --porcelain`; a `bare` first entry (a bare repository with worktrees), and a first entry that is the git dir
itself (a --separate-git-dir checkout, whose main work tree git does not record), raise ConfigError "unsupported
repository layout". The lead dir and the state dir (locks) live in the main checkout, also from a lane or train worktree.
`utf8_stdio()`: this process reads stdin and writes stdout and stderr as UTF-8 (an unencodable or undecodable character
replaced), whatever the locale, and writes `\n` line ends on every OS; it runs once when this module is imported, so
every tool and hook that reads its config through it speaks UTF-8 on Windows too, where a console or a pipe defaults to
the ANSI code page (cp1252) and Python writes `\r\n` (a POSIX shell's `$(...)` would keep the `\r` of each line).
Python 3 standard library only.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys


def utf8_stdio() -> None:
    """stdin, stdout and stderr as UTF-8 with errors replaced, stdout and stderr with `\n` line ends (stdin keeps
    universal newlines); a stream without reconfigure, such as a test's StringIO or a missing console's None, is left
    alone."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace", **({} if stream is sys.stdin else {"newline": "\n"}))


utf8_stdio()   # at import: every BOA tool and hook reads its config through this module

HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULTS = {
    "BOA_PLAN_FILE": "memory-bank/03-IMPLEMENTATION-PLAN.md",
    "BOA_SPEC_FILE": "memory-bank/02-SPECIFICATIONS.md",
    "BOA_REGISTER_FILE": "memory-bank/04-ARCHITECTURE.md",
    "BOA_FEATURES_FILE": "docs/parity/features.toml",
    "BOA_TEST_GLOBS": "tests/scripts/*.test.sh",
    "BOA_PLAN_CHECKLIST_HEAD": "## Coverage checklist",
    "BOA_DECISIONS_FILE": "memory-bank/06-DECISIONS.md",
    "BOA_LEAD_DIR": ".lead",
    "BOA_METALEARNING_FILE": "memory-bank/10-METALEARNING.md",
}
LINE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<raw>.*)")
KEY = re.compile(r"BOA_[A-Z0-9_]+")
UNQUOTED = re.compile(r"[^\s'\"$`\\;&|<>()~]*")
DOUBLE = re.compile(r'"([^"$`\\]*)"')


class ConfigError(Exception):
    pass


def _git(*args: str) -> str | None:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def main_of(d: str) -> str:
    d = os.path.abspath(d)
    out = _git("-C", d, "rev-parse", "--path-format=absolute", "--show-toplevel", "--git-dir", "--git-common-dir")
    dirs = out.splitlines() if out else []
    if len(dirs) != 3 or os.path.realpath(dirs[0]) != os.path.realpath(d) \
            or os.path.realpath(dirs[1]) == os.path.realpath(dirs[2]):
        return d    # not the top of a checkout, a plain checkout or a submodule checkout: its own main
    common = dirs[2]
    first = (_git("-C", d, "worktree", "list", "--porcelain") or "").split("\n\n")[0].splitlines()
    if "bare" in first:
        raise ConfigError(f"unsupported repository layout: {d} is a worktree of the bare repository {common}")
    wt = (_git("--git-dir", common, "config", "--get", "core.worktree") or "").strip()
    if wt:
        return os.path.normpath(os.path.join(common, wt))
    main = next((x[len("worktree "):] for x in first if x.startswith("worktree ")), "")
    if not main:
        raise ConfigError(f"unsupported repository layout: no main worktree for {d} (git dir {common})")
    if os.path.realpath(main) == os.path.realpath(common):
        # git lists the git dir itself when the main work tree is not recorded (a --separate-git-dir checkout):
        # never take a git dir for the main checkout (the lead and state dirs would land inside it)
        raise ConfigError(f"unsupported repository layout: the main work tree of {common} is not recorded (a "
                          f"--separate-git-dir checkout); set it with: git --git-dir {common} config core.worktree "
                          "<main checkout>")
    return main


def _single_quoted(raw: str) -> str:
    """A value made of single-quoted segments joined by `\\'` (bash's '\\'' idiom)."""
    out, i = [], 0
    while i < len(raw):
        if raw[i] == "'":
            end = raw.find("'", i + 1)
            if end < 0:
                raise ValueError("unterminated single quote")
            out.append(raw[i + 1:end])
            i = end + 1
        elif raw.startswith("\\'", i):
            out.append("'")
            i += 2
        else:
            raise ValueError(f"unexpected character {raw[i]!r} after a quoted value")
    return "".join(out)


def value(raw: str) -> str:
    """The value of one `KEY=<raw>` line (the grammar above); ValueError when bash could read it differently."""
    if raw.startswith("'"):
        return _single_quoted(raw)
    if raw.startswith('"'):
        m = DOUBLE.fullmatch(raw)
        if not m:
            raise ValueError("double-quoted value with $, backtick, backslash or a quote (use single quotes)")
        return m.group(1)
    if UNQUOTED.fullmatch(raw):
        return raw
    raise ValueError("unquoted value with a space or shell metacharacter (use single quotes)")


def parse(text: str, where: str = "config.env") -> dict[str, str]:
    out: dict[str, str] = {}
    for n, line in enumerate(text.removeprefix("\ufeff").split("\n"), 1):
        if not line.strip() or line.strip().startswith("#"):
            continue
        try:
            m = LINE.fullmatch(line)
            if not m:
                raise ValueError("not a KEY=value line")
            if not KEY.fullmatch(m.group("key")):
                raise ValueError(f"key {m.group('key')} is not a BOA_ key")
            if m.group("key") in out:
                raise ValueError(f"key {m.group('key')} defined twice")
            out[m.group("key")] = value(m.group("raw"))
        except ValueError as exc:
            raise ConfigError(f"{where}:{n}: {exc}") from None
    return out


def load(home: str = HOME) -> dict[str, str]:
    path = os.environ.get("BOA_CONFIG") or os.path.join(home, "config.env")
    cfg = dict(DEFAULTS)
    try:
        with open(path, encoding="utf-8") as fh:
            cfg.update(parse(fh.read(), path))
    except FileNotFoundError:
        pass
    cfg.update({k: v for k, v in os.environ.items() if k.startswith("BOA_")})
    return cfg


TASK_RE = r"T-\d{3,}[a-z]?"


def task_re(cfg: dict[str, str] | None = None) -> str:
    """The task-id grammar: always T-NNN[a-z] (T- and at least three digits)."""
    return TASK_RE


def task_key(tid: str) -> tuple[int, str]:
    """A task id's sort key: by number (no upper limit: a four-digit id comes after every three-digit one), then the
    suffix."""
    m = re.search(r"\d+", tid)
    return (int(m.group()) if m else -1, tid)
