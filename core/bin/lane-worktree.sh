#!/bin/sh
# BOA lean lane worktrees launcher (POSIX sh): runs `boa lane-worktree` (tools/lane_worktree.py) with BOA's interpreter rules; the tool card and
# usage: lane-worktree.sh --help. Windows: `boa.cmd lane-worktree`.
exec "$(dirname -- "$0")/boa" lane-worktree "$@"
