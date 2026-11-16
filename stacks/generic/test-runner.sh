#!/bin/sh
# BOA stack plug-in "generic": the targeted test runner. Installed as .boa/stack/test-runner.sh.
#
# What it is for: running the tests a change touches, and the project gate's contract tests, by explicit file: never a
# directory, a glob or a whole suite. When to use it: builder and tester on the tests of their change; the project gate's
# contract-tests step runs it on every test carrying @covers-contract (at most TEST_RUNNER_MAX_FILES files per call).
# How to wire it: by configuration only, in plugin.env: TEST_COMMANDS maps a test-file glob to the command that runs
# one such file (`{}` = the file, `{dir}` = its directory), one `<glob>=<command>` per line, the first match wins;
# shell suites (*.sh, *.bash) always run with bash. Shape:
#   TEST_COMMANDS='
#   <glob>=<command that runs one such file> {}
#   <another glob>=<command> {dir}
#   '
# How to check it: `.boa/stack/test-runner.sh <one test>` runs it and exits with its status;
# `.boa/stack/test-runner.sh tests/` is refused (exit 64), and so is a file no glob maps.
#
# The contract a project's runner fulfils (this template implements the first part; the agent adds the rest when
# the project needs it, and the project's gate and the roles then rely on it):
#   - explicit files only; refuse a directory, a glob, a symlink, an absolute path, a `..`, an unknown option (64);
#   - a case filter, `--filter=<pattern>`: narrows a run to the cases whose name matches, for the one test tool that
#     has cases; the pattern is restricted (letters, digits and `_ : . @ + -`, 1 to 200 characters, one line) and
#     passed to the tool as one word, never through a shell; refused when no file of that tool is named;
#   - heavy tests, `--heavy`: runs the tests that need an external service, in a container started from the image
#     named by TEST_HEAVY_IMAGE (plugin.env). There is no default image: `--heavy` is refused (64) while the setting
#     is empty, spans several lines or is not an image reference. With `--heavy`, BOA_TEST_HEAVY=1 and
#     BOA_TEST_HEAVY_IMAGE=<image> reach the test tool, whose test base class starts the service; without it
#     BOA_TEST_HEAVY=0 and the image variable is unset;
#   - a per-call cap (TEST_RUNNER_MAX_FILES): the project's gate calls the runner in chunks of that size.
# Usage: .boa/stack/test-runner.sh <test file>...   (from the project root; each command runs there)
# The path is never part of the command text: the command runs as `sh -c <command> sh <file> <dir>` with `{}` and
# `{dir}` standing for "$1" and "$2", so any file name works (app/[id]/page.test.tsx, src/routes/+page.test.ts, spaces,
# quotes).
# Exit: 0 every file passed · 1 a file failed · 64 a refused argument (no file, an option, a directory, a missing
# file, a symlink (the file or a directory on its path), an absolute path or a `..`, a file no command is mapped to).
# POSIX sh.
set -u
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck source=plugin.env disable=SC1091  # the plug-in settings, next to this file
. "$here/plugin.env"
refuse() { echo "test-runner: $*" >&2; exit 64; }
# command_for <file> — the command template mapped to the file (shell suites: bash), or nothing.
command_for() {
    case $1 in *.sh|*.bash) echo 'bash {}'; return ;; esac
    printf '%s\n' "${TEST_COMMANDS-}" | while IFS= read -r line; do
        line=$(printf '%s' "$line" | sed 's/^[[:space:]]*//')
        case $line in ''|'#'*) continue ;; esac
        pattern=${line%%=*}
        # shellcheck disable=SC2254  # the configured glob is a pattern on purpose
        case $1 in $pattern) printf '%s\n' "${line#*=}"; break ;; esac
    done
}
[ "$#" -gt 0 ] || refuse "name the test files (explicit files only)"
for f in "$@"; do
    case $f in -*) refuse "unknown option: $f" ;; esac
    case $f in /*) refuse "a test path is relative to the project root: $f" ;; esac
    case /$f/ in */../*) refuse "no .. in a test path: $f" ;; esac
    p=$f   # the file and every directory on its path: a symlink may lead out of the tree
    while :; do
        [ ! -L "$p" ] || refuse "a symlink is not a test file of this tree: $p (name the real file)"
        case $p in */*) p=${p%/*} ;; *) break ;; esac
    done
    { [ -f "$f" ] && [ ! -d "$f" ]; } || refuse "not a test file of this tree: $f (explicit files only, never a directory)"
    [ -n "$(command_for "$f")" ] || refuse "no command for $f: map its kind in TEST_COMMANDS (.boa/stack/plugin.env), e.g. '<glob>=<command> {}'"
done
failed=0
for f in "$@"; do
    dir=$(dirname -- "$f")
    # The configured command gets the path as data, never as text: {dir} -> "$2", {} -> "$1".
    # shellcheck disable=SC2016  # "$1" and "$2" are for the inner sh, literal here
    cmd=$(command_for "$f" | sed 's|{dir}|"$2"|g; s|{}|"$1"|g')
    rc=0
    sh -c "$cmd" sh "$f" "$dir" || rc=$?
    echo "--- $f (exit $rc)"
    [ "$rc" -eq 0 ] || failed=1
done
exit "$failed"
