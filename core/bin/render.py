#!/usr/bin/env python3
"""Render BOA templates from the project's config (`.boa/config.env`).

A template holds placeholders `{{BOA_KEY}}`; each is replaced by the value of `BOA_KEY` in the config.
There is no other template syntax and no code execution: no expressions, no conditionals, no includes.

Rules:
- The config is bash-sourceable `KEY=value` and is parsed by `tools/boa_config.py` (the one reader of config.env)
  without executing anything. Accepted
  line shapes: blank, `# comment`, `KEY=value` (unquoted: no spaces, quotes, `$`, backtick, `\\`, `;`,
  `&`, `|`, `<`, `>`, `(`, `)`, `~`), `KEY='value'` (single quotes; a literal quote is written `'\\''`), and
  `KEY="value"` (double quotes, no `$`, backtick, `\\` or `"` inside). Anything else is an error naming
  the line, so a value bash would expand can never be read differently here.
- Only `BOA_[A-Z0-9_]+` keys are accepted; a key defined twice is an error.
- A placeholder naming a key the config does not define is an error naming the file and the key; so is
  a malformed placeholder that looks like one (`{{ boa_key }}`, `{{BOA_key}}`, `{{ BOA_KEY }}`). Other
  double-brace text (e.g. `${{ github.ref }}` in CI files) is left alone.
- `--set KEY=VALUE` (repeatable, before the command) adds a render-time key that is not in the config
  (the installer's `BOA_INSTALL_DATE`, `BOA_SCRATCH_ABS`, …); it may not redefine a config key.
- Idempotent: a destination whose content is already the rendering is not rewritten. Files are written
  through a temporary file and a rename, with the template's permission bits.

Usage (OPTS = [--config FILE] [--set KEY=VALUE]...):
  render.py OPTS SRC [DST]            render one file (to stdout without DST)
  render.py OPTS --tree SRCDIR DSTDIR render every file under SRCDIR into DSTDIR
  render.py OPTS --check FILE...      only verify the placeholders (exit 1 on any error)
  render.py OPTS --get KEY            print one value
  render.py OPTS --dump0              print every KEY\0VALUE\0 pair (for bash readers)
The default config is `.boa/config.env` under the current directory.
Exit: 0 ok, 1 template or config error, 2 usage error.
Library: `load_config(path) -> dict`, `render_text(text, config, name) -> str`, `read_template(path) -> str` and
`render_files(srcdir, config, skip) -> [(src, rel, text)]` (every file rendered in memory, all errors at once; `skip`
filters relative paths written with `/`), which `--tree` and the installer share.
"""
from __future__ import annotations

import os
import pathlib
import re
import stat
import sys
import tempfile

sys.dont_write_bytecode = True
# the one config reader lives with the tools (`<home>/tools/boa_config.py`, beside this `<home>/bin/`)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import boa_config  # noqa: E402

DEFAULT_CONFIG = os.path.join(".boa", "config.env")

# Anything shaped like a placeholder: {{ word }} with optional inner spaces.
LOOSE_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
STRICT_RE = re.compile(r"\{\{(BOA_[A-Z0-9_]+)\}\}")


class RenderError(Exception):
    """A config or template error, with a message naming the file (and line or key)."""


def load_config(path: str) -> dict[str, str]:
    """The config through boa_config.parse, the one reader of config.env (the grammar above)."""
    try:
        with open(path, encoding="utf-8", newline="") as fh:  # keep \r: bash would keep it too
            text = fh.read()
    except OSError as exc:
        raise RenderError(f"{path}: cannot read config: {exc.strerror}") from None
    except UnicodeDecodeError:
        raise RenderError(f"{path}: config is not UTF-8") from None
    try:
        return boa_config.parse(text, path)
    except boa_config.ConfigError as exc:
        raise RenderError(str(exc)) from None


def render_text(text: str, config: dict[str, str], name: str) -> str:
    errors = []
    for m in LOOSE_RE.finditer(text):
        token = m.group(1)
        if not token.upper().startswith("BOA_"):
            continue
        if not STRICT_RE.fullmatch(m.group(0)):
            errors.append(f"{name}: malformed placeholder {m.group(0)} (write {{{{{token.upper()}}}}})")
        elif token not in config:
            errors.append(f"{name}: unknown placeholder {{{{{token}}}}} (key {token} not in config)")
    if errors:
        raise RenderError("\n".join(dict.fromkeys(errors)))
    return STRICT_RE.sub(lambda m: config[m.group(1)], text)


def read_template(src: str) -> str:
    try:
        with open(src, encoding="utf-8", newline="") as fh:
            return fh.read()
    except OSError as exc:
        raise RenderError(f"{src}: cannot read template: {exc.strerror}") from None
    except UnicodeDecodeError:
        raise RenderError(f"{src}: template is not UTF-8 text") from None


def write_if_changed(dst: str, content: str, mode: int) -> bool:
    """Write `content` to `dst` unless it already holds it. Returns True when written."""
    data = content.encode("utf-8")
    try:
        with open(dst, "rb") as fh:
            if fh.read() == data:
                if stat.S_IMODE(os.stat(dst).st_mode) != mode:
                    os.chmod(dst, mode)
                return False
    except FileNotFoundError:
        pass
    parent = os.path.dirname(dst) or "."
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".render-", dir=parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, dst)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return True


def render_file(src: str, dst: str | None, config: dict[str, str]) -> None:
    out = render_text(read_template(src), config, src)
    if dst is None:
        sys.stdout.write(out)
        return
    write_if_changed(dst, out, stat.S_IMODE(os.stat(src).st_mode))


def render_files(srcdir: str, config: dict[str, str], skip=lambda rel: False) -> list[tuple[str, str, str]]:
    """Every file under srcdir rendered in memory: [(src, rel with `/`, text)], sorted; all errors in one RenderError."""
    if not os.path.isdir(srcdir):
        raise RenderError(f"{srcdir}: not a directory")
    out = []
    errors = []
    for root, dirs, files in os.walk(srcdir):
        dirs.sort()
        for name in sorted(files):
            src = os.path.join(root, name)
            rel = os.path.relpath(src, srcdir).replace(os.sep, "/")
            if skip(rel):
                continue
            if os.path.islink(src):
                errors.append(f"{src}: symlinks are not rendered")
                continue
            try:
                out.append((src, rel, render_text(read_template(src), config, src)))
            except RenderError as exc:
                errors.append(str(exc))
    if errors:
        raise RenderError("\n".join(errors))
    return out


def render_tree(srcdir: str, dstdir: str, config: dict[str, str]) -> None:
    for src, rel, out in render_files(srcdir, config):
        write_if_changed(os.path.join(dstdir, *pathlib.PurePosixPath(rel).parts), out, stat.S_IMODE(os.stat(src).st_mode))


def main(argv: list[str]) -> int:
    args = list(argv)
    config_path = DEFAULT_CONFIG
    extra: dict[str, str] = {}
    usage = ("usage: render.py [--config FILE] [--set KEY=VALUE]... "
             "(SRC [DST] | --tree SRCDIR DSTDIR | --check FILE... | --get KEY | --dump0)")
    while len(args) >= 2 and args[0] in ("--config", "--set"):
        if args[0] == "--config":
            config_path = args[1]
        else:
            key, sep, value = args[1].partition("=")
            if not sep or not boa_config.KEY.fullmatch(key) or key in extra:
                print(f"render: --set needs a new BOA_ KEY=VALUE, got {args[1]!r}", file=sys.stderr)
                return 2
            extra[key] = value
        args = args[2:]
    if not args or args[0] in ("-h", "--help"):
        print(usage, file=sys.stderr)
        return 2
    try:
        config = load_config(config_path)
        clash = sorted(set(extra) & set(config))
        if clash:
            raise RenderError(f"--set may not redefine config keys: {', '.join(clash)}")
        config.update(extra)
        if args[0] == "--tree":
            if len(args) != 3:
                print(usage, file=sys.stderr)
                return 2
            render_tree(args[1], args[2], config)
        elif args[0] == "--check":
            if len(args) < 2:
                print(usage, file=sys.stderr)
                return 2
            errors = []
            for path in args[1:]:
                try:
                    render_text(read_template(path), config, path)
                except RenderError as exc:
                    errors.append(str(exc))
            if errors:
                raise RenderError("\n".join(errors))
        elif args[0] == "--get":
            if len(args) != 2:
                print(usage, file=sys.stderr)
                return 2
            if args[1] not in config:
                raise RenderError(f"{config_path}: key {args[1]} not in config")
            print(config[args[1]])
        elif args[0] == "--dump0":
            if len(args) != 1:
                print(usage, file=sys.stderr)
                return 2
            sys.stdout.write("".join(f"{k}\0{v}\0" for k, v in config.items()))
        elif args[0].startswith("-") or len(args) > 2:
            print(usage, file=sys.stderr)
            return 2
        else:
            render_file(args[0], args[1] if len(args) == 2 else None, config)
    except RenderError as exc:
        print(f"render: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
