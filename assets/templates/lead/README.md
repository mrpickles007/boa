# {{BOA_LEAD_DIR}}/ — the lead's live state (machine-local, git-excluded, never committed)

Only the lead writes here (the guard refuses sub-agent writes); agents may read it. Durable rules and decisions are
never here: they live in `AGENTS.md` and `memory-bank/` (08, 09, 06…). Full description:
`docs/agent-handbook.md` §6 and `memory-bank/09-OPERATING-PROCEDURES.md` §2.

| File | Purpose |
|---|---|
| `README.md` | this file |
| `lanes.md` | the registry: append-only, one timestamped UTC line per stage change (`<time> <task> <stage> (<sha>) — <role>, …`); the newest line per lane wins; trains are `TRAIN-<n> (<a>+<b>) …`; override evidence goes here; agent ids are not here (the agents registry, project-wiring "usage clock and throughput") |
| `lanes/<task>.md` | the lane journal: every agent's final report, written by the SubagentStop hook; never edited by hand |
| `lanes/<task>-<role>.md` | resume or closure copies of a role's `.lane-resume/<role>.md` (written by the hook at a pause, or by the lead) |
| `lanes/<task>.full/` | the whole text of a report longer than the journal's 20 KiB cap (one file per report; the journal's cut marker names it); removed with the lane's other lead-dir files when the lane closes, and at close-out |
| `brief-common.md` | the rules pasted into every agent brief (generic part + the project lessons the lead grows) |
| `open-items.md` | the transit queue (OR-25): captured to-dos not yet placed in the plan — the stop hook's Leftovers lines and the lead's and owner's notes; the next train's fold places each one in the plan, which stays the only source of work; empty at close-out |
| `owner-rules-pending.md` | owner rules said in chat, folded into 08 at the next train |
| `plan-additions-pending.md` | plan rows and notes, folded into 03 at the next train; the lead's own outcome and decision blocks, routed by type to 05 and 06 |
| `metalearning-inbox.md` | lessons from the agents' metacognitive traces, curated into 10-METALEARNING.md at each train |
| `PAUSE` | present only while the project is paused (time, reason); written by `.boa/bin/pause-flag.sh` |
| `RESUME-LEAD.md` | written at a pause by the Stop hook (and completed by the lead): what to do first on resume |
| `lead-status.seen` | the status screen's bookmark (guard denials already seen) |

If this directory is missing (a fresh clone elsewhere): there is no live lane state; rely on the memory bank, `git
worktree list` and the forge's open PRs, and start lanes fresh.
