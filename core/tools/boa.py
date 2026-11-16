"""boa — BOA's one command-line entry point: `boa <subcommand> [args]`.

Called by the launchers `.boa/bin/boa` (POSIX sh) and `.boa/bin/boa.cmd` (Windows), which first check BOA's
prerequisites without Python (git, Python 3.11+) and then run `python -I -B .boa/tools/boa.py`.
Subcommands, resolved in this order:
  install | uninstall                                 BOA's install surface (uninstall = install --uninstall)
  help | --help | -h                                  this text and the tools found
  status, lane, language                              short names of lead-status, lane-worktree, markers
  <word> <word2> ...                                  the tool `<word>_<word2>` when it exists (boa memory write ->
                                                      tools/memory_write.py)
  <word> ...                                          the tool `<word>` (`-` and `_` alike): tools/<word>.py, then
                                                      bin/<word>.py, bin/<word>.sh, hooks/<word>.py
Python tools run with this interpreter (`-I -B`), a `bin/<word>.sh` launcher (it calls its Python tool) with `bash`. On
POSIX the tool replaces this process (exec): signals, Ctrl-C cleanup and the exit status are the tool's own. On
Windows it runs as a child (Ctrl-C reaches it; this process waits) and its exit code is returned.
Interpreter: the config's BOA_PYTHON, read with the one config reader (boa_config.py; the environment's BOA_PYTHON
wins, as for every key): when it names a working Python 3.11+ other than this one, boa.py first runs itself again with
it (the launchers only guess a first Python); otherwise (unset, not working, or an unreadable config) it goes on
with this one.
Arguments pass through unchanged. Unknown subcommand: exit 2. Exit 3 belongs to the launchers alone (a missing
prerequisite): no BOA tool uses it.
Python 3 standard library only; this file parses on old interpreters so the version message can be printed.
"""

import os
import signal
import subprocess
import sys

sys.dont_write_bytecode = True
HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the core directory (.boa/ once installed)
BUILTIN = {"install": ("boa_install", []), "uninstall": ("boa_install", ["--uninstall"])}
ALIASES = {"status": "lead-status", "lane": "lane-worktree", "language": "markers"}
PLACES = (("tools", ".py"), ("bin", ".py"), ("bin", ".sh"), ("hooks", ".py"))


def find(word):
    """The file of tool WORD, or None."""
    if not word or word.startswith((".", "-")) or any(c in word for c in "/\\:"):
        return None
    for d, ext in PLACES:
        for name in {word, word.replace("-", "_"), word.replace("_", "-")}:
            p = os.path.join(HOME, d, name + ext)
            if os.path.isfile(p):
                return p
    return None


def tools():
    seen = []
    for d, ext in PLACES:
        base = os.path.join(HOME, d)
        if os.path.isdir(base):
            seen += sorted(f[:-len(ext)] for f in os.listdir(base) if f.endswith(ext) and not f.startswith("_"))
    return seen


def find_bash(environ=None, windows=None):
    """The bash that runs a shell tool. On POSIX "bash" (exec searches PATH). On Windows a bare "bash" makes
    CreateProcess search the system directory first, where System32\\bash.exe is the WSL launcher, not the Git Bash the
    agent works in: the first bash.exe in an absolute PATH entry (never the current directory, never a .cmd or .bat),
    skipping the system directory and the WindowsApps aliases; "bash" when there is none."""
    environ = os.environ if environ is None else environ
    if not (os.name == "nt" if windows is None else windows):
        return "bash"
    system = os.path.normcase(environ.get("SystemRoot", "C:\\Windows")).lower().rstrip("\\/")
    for d in environ.get("PATH", "").split(";"):
        nd = os.path.normcase(d.strip().strip('"')).lower().rstrip("\\/")
        if not nd or not os.path.isabs(nd):
            continue   # empty or relative (on Windows also a rooted \\x without its drive): never the current directory
        if nd == system or nd.startswith(system + os.sep) or "windowsapps" in nd:   # normcase: os.sep separators
            continue
        exe = os.path.join(d.strip().strip('"'), "bash.exe")
        if os.path.isfile(exe):
            return exe
    return "bash"


def run(path, args, interpreter=False):
    """Run the tool PATH with ARGS (or, with interpreter=True, the Python PATH itself with `-I -B` ARGS)."""
    if interpreter:
        cmd = [path, "-I", "-B"] + list(args)
    else:
        cmd = ([sys.executable, "-I", "-B", path] if path.endswith(".py") else [find_bash(), path]) + list(args)
    try:
        if os.name != "nt":
            sys.stdout.flush()
            # Python ignores SIGPIPE and SIGXFSZ and an exec'd program would inherit that (a shell tool in a pipe
            # would print "Broken pipe" instead of ending quietly): the tool starts with the defaults
            for name in ("SIGPIPE", "SIGXFSZ"):
                if hasattr(signal, name):
                    signal.signal(getattr(signal, name), signal.SIG_DFL)
            os.execvp(cmd[0], cmd)   # the tool becomes this process; returns only on failure
        signal.signal(signal.SIGINT, signal.SIG_IGN)   # Ctrl-C is the child's to handle; wait for its exit
        return subprocess.call(cmd)
    except OSError as exc:
        print("boa: cannot run %s: %s" % (path, exc), file=sys.stderr)
        return 1


def configured_python():
    """The config's BOA_PYTHON when it is a working Python 3.11+ other than this interpreter, else None."""
    if os.environ.get("_BOA_SWITCHED"):
        return None   # already switched once: never loop
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import boa_config
        py = boa_config.load(HOME).get("BOA_PYTHON", "")
    except Exception:   # noqa: BLE001  (no reader beside this file, an unreadable config: go on with this Python)
        return None
    if not py or not os.path.isabs(py) or not os.path.isfile(py) \
            or os.path.realpath(py) == os.path.realpath(sys.executable or ""):
        return None
    try:
        ok = subprocess.run([py, "-I", "-c", "import json, sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    return py if ok else None


def main(argv):
    if sys.version_info < (3, 11):
        print("boa: Python 3.11 or newer is needed (this is %d.%d): install it and run again"
              % sys.version_info[:2], file=sys.stderr)
        return 3
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import boa_config  # noqa: F401  (its import makes stdin, stdout and stderr UTF-8: boa_config.utf8_stdio)
    except Exception:   # noqa: BLE001  (no reader beside this file: go on, configured_python finds none either)
        pass
    py = configured_python()
    if py:
        os.environ["_BOA_SWITCHED"] = "1"
        return run(py, [os.path.abspath(__file__)] + list(argv), interpreter=True)
    if not argv or argv[0] in ("help", "--help", "-h"):
        print(__doc__.split("\n\n", 1)[0].strip())
        print("\nusage: boa <subcommand> [args]\n\nbuilt in: " + " ".join(sorted(BUILTIN)))
        print("tools: " + " ".join(tools()))
        return 0 if argv else 2
    word, rest = argv[0], argv[1:]
    if word in BUILTIN:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        module, pre = BUILTIN[word]
        return __import__(module).main(pre + rest)
    word = ALIASES.get(word, word)
    if rest:
        two = find(word + "_" + rest[0])
        if two:
            return run(two, rest[1:])
    path = find(word)
    if path:
        return run(path, rest)
    print("boa: unknown subcommand '%s' (boa help lists them)" % word, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
