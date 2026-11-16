# active-context.md — where we are RIGHT NOW

> Lead-owned and SHORT: only the present. History goes to `05-PROGRESS.md`, decisions to `06-DECISIONS.md`, live
> lane detail to the lead registry. The integrator edits only the lines the lead's brief names, in its
> `docs(memory)` commit. Lanes never edit this file. Rewrite the header line at every update with the date.

## Now (updated YYYY-MM-DD HH:MM UTC)
- Milestone: <M1 — name>; progress: <DONE>/<total> tasks (<%>), work-weighted <%>; tested and waiting: <n>.
- Mode: {{BOA_MODE}}; stack: {{BOA_STACK}}; running: <yes | paused since … (see the lead dir's RESUME-LEAD.md)>.

## In-flight lanes
| Task | Stage | Agent tier | Next |
|---|---|---|---|

## Next eligible
- <from `python3 -I .boa/tools/plan_lanes.py`>

## Open HITL (decisions waiting on the owner)
<!-- State lines, not memories: `- <question> — options, recommendation (memory-<N>)`. The question itself is a memory
     block written with `.boa/tools/memory_write.py` (type requirement, routed to 02); the answer becomes an ADR or
     EDR block in 06 that supersedes it, and the line here is removed. -->
- none

## Blockers
<!-- State lines: `- <blocker> — owner task T-NNN, what unblocks it (memory-<N>)`; the blocker's memory block (type
     constraint or deferred) lives where `memory_write.py` routes it. -->
- none

## Deployment
- <URL of the project's own instance; where its credentials live (never the credentials); last deploy and health>

## Disk and durations
- Footprint: <MB> (warning {{BOA_DISK_WARN_MB}} MB); trend: <…>. Gate: <last total s> (budget {{BOA_GATE_BUDGET_S}} s);
  open speed-up tasks: <ids>.
