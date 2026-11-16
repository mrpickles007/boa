# context-gate: integration note for the agent that wires it

For the agent wiring BOA into its runtime (the BOA skill's wiring step). The standalone skill instructions are in
`SKILL.md`; this file is the exact copy map and wiring entry so the agent does not have to interpret prose.
The copy map below is executable: the package's own development suite performs a simulated install from it (one row
per shipped file, sources and targets in backticks) and fails when a shipped file has no row.

## Copy map (source in this package -> targets in the project)

The skill copy (`.claude/skills/context-gate/`) is self-contained: SKILL.md refers only to files inside it. The
runtime copy (`.context-gate/`) can be installed from the skill copy alone.

| Source | Targets | Rule |
|---|---|---|
| `context-gate/SKILL.md` | `.claude/skills/context-gate/SKILL.md` | Claude Code; another runtime: wherever its skills live |
| `context-gate/scripts/gate_core.py` | `.claude/skills/context-gate/scripts/gate_core.py`, `.context-gate/scripts/gate_core.py` | byte-identical (`cmp`) |
| `context-gate/hooks/precompact.sh` | `.claude/skills/context-gate/hooks/precompact.sh`, `.context-gate/hooks/precompact.sh` | keep the executable bit |
| `context-gate/assets/precedence-block.txt` | `.claude/skills/context-gate/assets/precedence-block.txt`, `.context-gate/prompts/precedence-block.txt` | byte-identical; never rendered or reflowed |
| `context-gate/assets/config.json` | `.claude/skills/context-gate/assets/config.json`, `.context-gate/config.json` | profile `light`: chosen by profile (see below); fill `agent.name`, `agent.version`, `probe.*` from the probe (`jq`) |
| `context-gate/assets/config.l0-only.json` | `.claude/skills/context-gate/assets/config.l0-only.json`, `.context-gate/config.json` | profile `l0-only`: replaces the row above; same fill |
| `context-gate/assets/custom-instructions.md` | `.claude/skills/context-gate/assets/custom-instructions.md`, `.context-gate/prompts/custom-instructions.md` | light profile only; render `{{BOA_PROJECT_NAME}}`, `{{BOA_LEAD_DIR}}` with `render.py` |
| `context-gate/assets/gitignore.txt` | `.claude/skills/context-gate/assets/gitignore.txt`, `.context-gate/.gitignore` | copy |
| `context-gate/assets/after-compaction-lead.md` | `.claude/skills/context-gate/assets/after-compaction-lead.md` | not a file in the project: rendered into the lead's project instructions (see "Rules for the agents") |
| `context-gate/assets/after-compaction-subagent.md` | `.claude/skills/context-gate/assets/after-compaction-subagent.md` | not a file in the project: rendered into every sub-agent definition (see "Rules for the agents") |

Create `.context-gate/conversations/` lazily (the core does it); never commit it.

## Profile choice

`light` where the runtime fires a pre-compaction event with the transcript path AND appends the hook's stdout to its
compaction prompt (Claude Code: verified in 2.1.322, re-verify in the installed version); `l0-only` where only the
event exists; neither otherwise (tell the user, install nothing). The probe procedure, including measuring the cap
(`probe.extension_cap_chars`, which the core reads), is in `SKILL.md`. A config that is missing, unreadable or names
an unknown profile runs as `l0-only`: the extension is printed only when the config says `light`.

## Hook entry

One hook, the pre-compaction event, **no matcher** (every trigger), timeout 60 s. Claude Code, rendered into
`.claude/settings.json` (merge into an existing file, never overwrite other hooks):

```json
{"hooks": {"PreCompact": [{"hooks": [{"type": "command",
  "command": "\"$CLAUDE_PROJECT_DIR\"/.context-gate/hooks/precompact.sh", "timeout": 60}]}]}}
```

Do not wire a post-compaction injection or a turn-end hook. Other runtimes: the same command in the runtime's own hook
format; the text that tells the agent how to wire it for its runtime (no claim without a probe) belongs to the
project's `AGENTS.md`, not to this directory.

## Rules for the agents ("After a compaction")

Two parts, two destinations; both are mandatory under `l0-only` (the compaction prompt cannot carry the instruction),
and recommended under `light` (the extension is dropped in sub-agent contexts).

| Asset | Goes into | Placeholders to fill when wiring |
|---|---|---|
| `assets/after-compaction-lead.md` | the lead's project instructions (`CLAUDE.md`/`AGENTS.md`, the block the template defines) | `{{BOA_LEAD_DIR}}` |
| `assets/after-compaction-subagent.md` | every sub-agent definition (the agent contracts), as its "After a compaction" section | `{{BOA_CLAUDE_PROJECT_DIR_NAME}}`, `{{BOA_SUBAGENT_TRANSCRIPT_LOOKUP}}` |

- `{{BOA_CLAUDE_PROJECT_DIR_NAME}}`: the directory name Claude Code uses under `~/.claude/projects/` for the project
  root. Read it, never derive it (the runtime shortens long names): it is the entry of `ls ~/.claude/projects/` that
  holds this session's transcript (the newest one that names the project path with
  every character that is not a letter or digit as `-`). Render that exact name, never a guess.
- `{{BOA_SUBAGENT_TRANSCRIPT_LOOKUP}}`: for another runtime, the one-line lookup of a sub-agent's own transcript, from
  the probe (where it is, how to tell which file is yours). With no other runtime installed, render
  `not applicable (no other runtime is configured)`.
- `{{BOA_LEAD_DIR}}` and every other `BOA_` key come from `.boa/config.env`.

## Verify

`python3 .context-gate/scripts/gate_core.py selftest` must print `"passed": true`; `cmp` the two copies of the core
and of the precedence block; the package's own development suite checks the same.
