---
name: context-gate
description: "Install or check the context-gate (mode A): at every compaction, a byte-exact L0 snapshot of the raw transcript on disk, plus, where the runtime lets a hook extend its compaction prompt (light profile), an extension of that prompt (precedence block, next_action -> goal -> constraints, the project's custom instructions, the L0 path). Where the runtime cannot extend the prompt, the L0-only profile takes the snapshot and nothing else. No digest, no injection, no turn-end hook, no model call. Invoke explicitly as a user command."
disable-model-invocation: true
---
# context-gate (light profile, with an L0-only fallback)

Only **mode A** is shipped. Two profiles, one core, chosen by `config.json` `profile`:

| Profile | Use when the runtime | Hook does |
|---|---|---|
| `light` | fires a pre-compaction event with the transcript path AND appends the hook's output to the compaction prompt | L0 snapshot, then prints the extension on stdout |
| `l0-only` | fires a pre-compaction event with the transcript path but cannot extend the compaction prompt | L0 snapshot only; stdout stays empty |

The snapshot is the guarantee; the extension is printed only when `config.json` positively says `light`. A missing or
unreadable `config.json`, or an unknown `profile`, runs as `l0-only`.

If the runtime has no pre-compaction event at all (or none that carries or lets you find the transcript path),
neither profile applies: say so and stop; do not improvise another mode. The full skill's modes B/C/D, structured
digest, post-compaction injection, turn-end checkpoint and `recover` are deliberately absent.

## What it guarantees, and what it does not

| Tier | Here | Property |
|---|---|---|
| **L0** | byte-exact copy of the raw transcript, taken at the pre-compaction hook | lossless: the source of truth for what was said |
| native summary | the runtime's own compaction summary; under `light`, steered by the prompt extension | lossy, prose; under `light` it opens with the precedence block |

Declared losses: no cumulative digest across compactions, no `src` pointers, no `recover`. The resume is the native
summary (a summary of summaries) plus L0 on disk, read at the lines you need.

- **`light`, sub-agent context:** Claude Code drops the prompt extension there (verified in 2.1.322); the snapshot
  is still taken. Sub-agents get the "read L0 when in doubt" rule from their agent definition instead
  (`assets/after-compaction-subagent.md`), and their own transcript (append-only) is their L0.
- **`l0-only`, every context:** the summary is the runtime's unsteered own. The "After a compaction" rules in every
  agent definition (sub-agents) and in the lead's project instructions carry the instruction to verify against the
  working tree and git first and to read L0 whenever in doubt (`assets/after-compaction-lead.md`, `assets/after-compaction-subagent.md`); under this profile
  both are mandatory.

## Invariants

1. **Probe, never recall.** Verify every capability against the runtime's latest official documentation and the
   installed version (`--version`, `--help`, the settings schema, the running binary, a harmless trial), at install
   and at every re-wire or update, never from memory, and record the evidence (what was checked, where, when) in
   `.context-gate/config.json` -> `probe`. Nothing in the runtime table below is a claim about a version you have not
   checked: a date or version written there is a past check, never a reason to skip one. When the installed version
   is older than the documentation, follow the installed version's behaviour and tell the user an update exists.
2. **Snapshot before the compaction, never async.** L0 is written with tmp -> fsync -> rename, appended per
   session, never written over; a rewritten or rotated source opens a new L0 file.
3. **stdout of the hook = the extension text only** (light) or nothing (l0-only). No JSON, no logs (diagnostics go
   to `hook.log`).
4. **Never block the compaction.** The hook always exits 0; a failed snapshot is said in the light extension (the
   live transcript path is named instead) and only logged under l0-only.
5. **The precedence block is copied verbatim** from `assets/precedence-block.txt`, never rewritten from memory.
   `gate_core.py` holds a byte-identical fallback; the install's `prompts/precedence-block.txt` is a copy.
6. **Zero calls beyond the native compaction.** No headless self-invocation, no model.
7. **Transcripts never enter git.** `.context-gate/conversations/` and `hook.log` are ignored.
8. **Ask before writing outside the project** (user-level settings). Project settings need no confirmation.

## Runtime notes

| Runtime | Pre-compaction event | Prompt extension | Profile |
|---|---|---|---|
| Claude Code | `PreCompact`, every trigger (manual, auto), no matcher; stdin JSON `transcript_path`, `session_id`, `trigger`, `custom_instructions` | a successful hook's trimmed stdout is appended to the compaction's custom instructions; cap 10,000 characters (measured in 2.1.322; the core stays 500 under the probed cap); dropped in sub-agent contexts | `light` |
| any other | whatever its docs and `--version` say: not verified by this skill | not claimed: probe it | `light` only if both capabilities are proven in the installed version, else `l0-only`, else none |

**Probe, for a runtime not in the table:** (a) does it fire a hook before EVERY compaction trigger it has, with the
transcript path in the event (or a stable transcript location you can set as `transcript.glob`)? (b) does it append
the hook's stdout to the compaction prompt? Test (b) with a marker string in the hook's stdout and read the
resulting summary or the runtime's own docs/binary; record both answers and the version in `probe`. (c) measure the
cap on the hook's output: print a long stdout ending in a distinct marker, compact, and see where the summary prompt
(or the runtime's docs/binary) cuts it; record it as `probe.extension_cap_chars` (the core reads it and stays 500
characters under it; the mandatory text, precedence block plus instructions plus L0 line, is about 2,000 characters,
so under a cap below that the core logs it and prints nothing, like `l0-only`: choose `l0-only`). If the cap cannot be proven, record the smallest value you can
prove or choose `l0-only`. (a) yes and (b) no -> `l0-only`. (a) no -> not applicable.

## Install

1. **Probe** as above. Pick the profile.
2. **Files** (under `<project>/.context-gate/`):
   - `scripts/gate_core.py` - copy of this skill's `scripts/gate_core.py` (byte-identical);
   - `prompts/precedence-block.txt` - copy of `assets/precedence-block.txt` (byte-identical; light only, harmless
     under l0-only);
   - `prompts/custom-instructions.md` - light only: the project's own instructions for the summary (start from
     `assets/custom-instructions.md`, fill its placeholders; inserted after the light instructions, cut to
     fit under the cap);
   - `hooks/precompact.sh` - copy of this skill's `hooks/precompact.sh` (root derived from its own path; executable);
   - `config.json` - copy of `assets/config.json` (light) or `assets/config.l0-only.json`, with `agent` and `probe`
     (including `extension_cap_chars`) filled from step 1;
   - `.gitignore` - copy of `assets/gitignore.txt`.
   - `LICENSE` - copy of this skill's `LICENSE` (byte-identical): the MIT notice travels with the copy; keep it beside
     the skill's own copy too.
3. **Wire ONE hook**: the pre-compaction event, with no trigger filter, timeout >= 60 s, command
   `<project>/.context-gate/hooks/precompact.sh`. Claude Code, project `.claude/settings.json`:
   `"PreCompact": [{"hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.context-gate/hooks/precompact.sh",
   "timeout": 60}]}]`. Merge, never overwrite other hooks. Do NOT wire a post-compaction injection or a turn-end
   hook. Other runtimes: wire the same command in the runtime's own format.
4. **Rules for agents**: `assets/after-compaction-subagent.md` into every sub-agent definition, with the transcript
   lookup of the runtime (Claude Code's is in the file; fill the slot for another runtime from the probe);
   `assets/after-compaction-lead.md` into the lead's project instructions (mandatory under `l0-only`).
5. **Self-test**: `python3 .context-gate/scripts/gate_core.py selftest` -> `{"passed": true, ...}` (fresh, append,
   partial tail, boundary, rewrite, rotation, lock, missing transcript, unusable chain, extension order, failure
   line, cap, a low probed cap, and the l0-only profile: silent stdout, exit 0 on failure, unknown profile and absent
   config = l0-only).
6. **Live check (at the first real compaction)**: `hook.log` has `precompact snapshot exit=0`; the L0 file exists
   under `.context-gate/conversations/<id>/`. Light only: the native summary opens with the `GROUND TRUTH
   PRECEDENCE` block verbatim, follows next_action -> goal -> constraints, and ends with `Raw transcript (L0,
   byte-exact): <path>`. No `CTXGATE-INJECT` marker is expected under either profile.
7. **Report**: profile and why, files written, the hook added, the cap (light), the self-test result, the live
   check (or that it completes at the first compaction), the limits above, and how to uninstall.

## Core (`scripts/gate_core.py`, pure stdlib, Python >= 3.8)

| subcommand | does | stdout | exit |
|---|---|---|---|
| `precompact --event -` | snapshot, then (light) prints the extension | the extension text (light) / nothing (l0-only) | always 0 |
| `snapshot --event -` | snapshot only | one JSON line (`conversation_id`, `snapshot_path`, `effect`, `lines`, `appended`...) | 0 ok / 2 transcript missing or unreadable / 3 lock |
| `selftest [--scratch <dir>]` | synthetic round-trip in a temp dir | `{"passed":bool,"checks":[...]}` | 0 / 1 |
| `gc --older-than 30d` | deletes conversations whose `chain.json` is older (only on request) | `{"removed":[...]}` | 0 |

Light extension order: precedence block -> light instructions (next_action, goal, constraints verbatim,
supersession) -> custom instructions -> `Raw transcript (L0, byte-exact): <path>` (or `L0 snapshot FAILED; live
transcript: <path>`). Layout: `conversations/<conversation_id>/chain.json` + `session_transcript_<UTC>_<seq>.jsonl`;
the conversation id is the root session of a rotation chain; `work/lock` guards the chain.

## After a compaction (runtime behaviour)

Light: the native summary opens with `GROUND TRUTH PRECEDENCE`: read next_action, goal and constraints from it,
verify against the working tree and git first (reality wins), and open the L0 file it names for any detail
(`grep`/`sed -n 'a,bp'`), never reconstruct from memory. A missing injected block is expected. L0-only: nothing is
injected; follow the "After a compaction" rule of your role: verify against the tree and git, then (lead) read the
newest file under `.context-gate/conversations/<id>/` or (sub-agent) your own transcript, at the lines you need.

## Uninstall

Remove the pre-compaction hook entry from the runtime's settings (Claude Code: the `PreCompact` entry of
`.claude/settings.json`) and delete `.context-gate/` (its `conversations/` holds the transcripts).
