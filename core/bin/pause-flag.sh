#!/bin/sh
# BOA pause flag launcher (POSIX sh): runs `boa pause-flag` (tools/pause_flag.py) with BOA's interpreter rules; the tool card and
# usage: pause-flag.sh --help. Windows: `boa.cmd pause-flag`.
exec "$(dirname -- "$0")/boa" pause-flag "$@"
