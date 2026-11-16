#!/bin/sh
# BOA lane journal launcher (POSIX sh): runs `boa lane-journal` (tools/lane_journal.py) with BOA's interpreter rules; the tool card and
# usage: lane-journal.sh --help. Windows: `boa.cmd lane-journal`.
exec "$(dirname -- "$0")/boa" lane-journal "$@"
