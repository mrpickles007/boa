<!-- boa:lead-stop:begin -->
# RESUME-LEAD — PAUSED since <UTC time> (reason: <reason>)
<!-- boa:lead-stop:end -->

> Written at a pause by the lead's stop hook (`.boa/hooks/lead_stop.py`) from the status screen and completed by the lead;
> removed (or marked "RUNNING again since …") at resume. Machine-local. The hook writes only between the
> `boa:lead-stop` marker lines above; everything else in this file is the lead's and is kept byte for byte.

## Read order for a fresh lead session
AGENTS.md (its Modus operandi first) → docs/agent-handbook.md → the runtime's instruction file, if any → memory-bank/RESUME.md → 08 + 09 → every memory-bank file → THIS file
→ open-items.md → brief-common.md → the pending files → lanes.md (newest lines win) → lanes/<task>-<role>.md →
`git worktree list`, the forge's open PRs, `.boa/bin/lead-status.sh`.
Where the runtime cannot resume an agent across sessions (capabilities record), start NEW agents per lane with the
lane's resume file. Reply to the owner in
{{BOA_REPLY_LANGUAGE}}.

## State at the stop
- main = <sha> (<last train>); gate <green/red>; DONE <n>/<total>.
- Deployed instance: <state, last update, anything pending>.
- Running at the stop: <none | what was interrupted, where>.

## Lanes at the stop (worktrees {{BOA_WT_DIR}}/<task>)
| Task | Stage (incl. "merged, fold pending": worktree kept for the next train's fold) | Agent tier | Resume file | Next |
|---|---|---|---|---|

## Next eligible
- <from plan_lanes.py>

## Decisions in flight / Open HITL
- <…>

## Disk and processes
- the project's daemons stopped at the pause; containers of the lanes (when the project uses a container engine): the
  engine's list filtered by the label `{{BOA_LABEL_KEY}}` (none expected).

## Rules to repeat in every brief until they are in the contracts
- <rules folded since the last contract update, if any>
