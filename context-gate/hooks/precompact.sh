#!/usr/bin/env bash
# context-gate pre-compaction wrapper (skill: .claude/skills/context-gate/SKILL.md). The profile is read from
# ../config.json by gate_core.py `precompact`:
#   light   (1) an L0 snapshot, byte-exact, of the transcript named in the event; (2) on stdout, the extension of
#           the native compaction prompt (Claude Code appends a successful PreCompact hook's stdout to the
#           compaction's custom instructions);
#   l0-only the snapshot only; stdout stays empty.
# stdout = only that text; diagnostics go to hook.log. The core always exits 0: the gate never blocks a compaction
# (no python3 = a non-blocking hook failure). The root is derived from this file's own path: <root>/hooks/.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/scripts/gate_core.py" precompact --root "$ROOT" --event - 2>>"$ROOT/hook.log"
