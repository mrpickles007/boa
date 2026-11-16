#!/bin/sh
# BOA lead status launcher (POSIX sh): runs `boa lead-status` (tools/lead_status.py) with BOA's interpreter rules; the tool card and
# usage: lead-status.sh --help. Windows: `boa.cmd lead-status`.
exec "$(dirname -- "$0")/boa" lead-status "$@"
