"""Paths, reserved names and the interpreter check used by `boa install`.

  fold(s)                       ASCII-only lower case (no locale, no Unicode folding: a non-ASCII letter stays as
                                it is, so `B` + dotted capital I (U+0130) + `N` folds to `b` + that same letter + `n`)
  FIXED_RESERVED                the names the installer owns directly under .boa/ besides the core's own entries
  is_abs(p, windows)            an absolute path of plain segments ([A-Za-z0-9._+-], and `~` after the first character:
                                an 8.3 short name) separated by `/`, without empty,
                                `.` or `..` segments; on Windows with a drive (`C:/x`); min_depth segments at least
  phys(p)                       p with every symlink in its existing part resolved (the rest appended as is); a root
                                (`/`, a drive's `C:/`) is "" or `C:`, so a joined path never starts with `//`
  inside(p, top)                p is top or below it, without regard to case where the file system ignores it (Windows,
                                macOS)
  wt_problem(wt, top)           why the worktrees dir WT (absolute, logical) is not acceptable for the project TOP (its
                                physical top level), "" when it is: absolute and two levels deep, never the project,
                                inside it or holding it, also once symlinks are resolved
  python_ok(p)                  an absolute executable Python 3.11+ that runs `-I -c "import json"`
Paths in BOA's config are written with `/` on every platform (Windows accepts it); `to_slash` converts.
Python 3 standard library only.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

FIXED_RESERVED = ("pending", "config.env", "installed.list", "stack", "agents", "commands",
                  "embed", "embed.partial", "embed.old")
_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
SEG = r"[A-Za-z0-9._+-][A-Za-z0-9._+~-]*"   # a `~` inside a segment (a Windows 8.3 name: RUNNER~1), never first
WINDOWS = os.name == "nt"
CASE_INSENSITIVE = WINDOWS or sys.platform == "darwin"   # the default file systems of Windows and macOS (APFS)


def fold(s: str) -> str:
    return s.translate(_LOWER)


def to_slash(p: str, windows: bool = WINDOWS) -> str:
    return p.replace("\\", "/") if windows else p


def is_abs(p: str, min_depth: int = 1, windows: bool = WINDOWS) -> bool:
    """A plain absolute path (see the module docstring); a trailing `/` is not accepted here."""
    if windows:
        m = re.fullmatch(r"([A-Za-z]:)?((?:/" + SEG + r")+)", p)
        rest = m.group(2) if m and m.group(1) else None
    else:
        rest = p if re.fullmatch(r"(?:/" + SEG + r")+", p) else None
    if rest is None:
        return False
    segs = rest.split("/")[1:]
    return len(segs) >= min_depth and not any(s in (".", "..") for s in segs)


def phys(p: str) -> str:
    """The physical form of an absolute path: symlinks of its existing part resolved; "" for the root."""
    p = p.rstrip("/") or "/"
    if re.fullmatch(r"[A-Za-z]:", p):
        p += "/"   # a drive root, never the drive-relative `C:` (that drive's current directory)
    rest = ""
    while not os.path.lexists(p) and os.path.dirname(p) != p:
        rest = "/" + os.path.basename(p) + rest
        p = os.path.dirname(p)
    # a root (`/`, `C:/`) loses its slash, so the joined rest never starts with `//`
    return to_slash(os.path.realpath(p)).rstrip("/") + rest


def inside(p: str, top: str, ci: bool = CASE_INSENSITIVE) -> bool:
    """p is top or below it; ci = compared without regard to (ASCII) case, as the file system does."""
    a, b = (fold(p), fold(top)) if ci else (p, top)
    b = b.rstrip("/")
    return a == b or a.startswith(b + "/")


def wt_problem(wt: str, top: str, windows: bool = WINDOWS, ci: bool = CASE_INSENSITIVE) -> str:
    wt, top = wt.rstrip("/"), top.rstrip("/")
    if not is_abs(wt, 2, windows):
        return "not an absolute path at least two levels deep without . or .. segments"
    for p in (wt, phys(wt)):
        if inside(p, top, ci):
            return f"the project itself or inside it ({p})"
        if inside(top, p, ci):
            return f"it holds the project ({p})"
    return ""


def python_ok(p: str) -> bool:
    if not p or not os.path.isabs(p) or os.path.isdir(p) or not os.access(p, os.X_OK):
        return False
    try:
        r = subprocess.run([p, "-I", "-c", "import json, sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def load_render(core: str):
    """The renderer module of a core directory (core/bin/render.py), loaded by path (it is a script, not a package)."""
    import importlib.util
    path = os.path.join(core, "bin", "render.py")
    spec = importlib.util.spec_from_file_location("boa_render_" + str(abs(hash(path))), path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
