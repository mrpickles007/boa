# 05 — Progress log

> Append-only, chronological. One memory block per stage of a task (build, review outcome, test, integration) and
> per meaningful lead action (bootstrap, re-plan, deployment, pause, resume, close-out), type `outcome` (OR-50,
> `memory-bank/README.md` "Memory blocks"). Never edit a block: a correction is a new block that says
> `supersedes="memory-<N>"`, written through `.boa/tools/memory_write.py`. In a clean-room project every block
> carries a `Provenance:` line.

Block format (`datetime` from `date -u +%Y-%m-%dT%H:%M:%SZ`; `keywords` with the task id `T-NNN`, the stage, the role):
```
@@@memory-<N> brief="<task id> <stage>: <one-line result>" datetime="<YYYY-MM-DDTHH:MM:SSZ from date -u +%Y-%m-%dT%H:%M:%SZ>" keywords="<task id>, <stage>, <role>, <components>" type="outcome"
<task id> <stage> (<role>, <model>)
- What: <what was done, per acceptance criterion>
- Files: <paths>
- Tests: <what ran, result>; review: <findings → resolved>; mutation: <paths, MSI, survivors and disposition>
- Decisions / assumptions: <…> (a lasting decision is also an ADR or EDR block in 06)
- Elapsed: <the clock's elapsed line>
@endmemory
```

## Memories — outcomes and bugs

@@@memory-1 brief="BOA installed (mode {{BOA_MODE}}, stack {{BOA_STACK}})" datetime="{{BOA_INSTALL_DATE}}" keywords="BOA, install, bootstrap, {{BOA_MODE}}, {{BOA_STACK}}" type="outcome"
BOA installed (mode {{BOA_MODE}}, stack {{BOA_STACK}}): memory bank, agent handbook, role contracts, commands, the
guard, the pause and the memory and lane hooks, the memory and lane tools and the lead dir installed.
@endmemory
