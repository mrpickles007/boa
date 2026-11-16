# 10 — Metalearning (lessons about the way of working)

> Filled by the train fold (OR-35): lane lessons arrive from each lane's `.lane-resume/memories.md` (the agents'
> metacognitive traces), the lead's own notes and curations from its `metalearning-inbox.md`; a lead curation that
> improves a lane lesson supersedes it, never copies it.
> Every entry is one memory block (OR-50) of type `lesson`, `gotcha`, `trap` or `heuristic`, deduplicated: a lesson
> seen again gets a new block that supersedes the old one with the added sighting. Every entry says the change it
> caused, or "watch" until it causes one. A lesson seen twice becomes a rule proposal to the owner (08), a line in the
> lead brief, an agent-contract line or a tooling task. `python3 -I .boa/tools/metalearning.py` lists repeats;
> `.boa/tools/memory_lint.py` validates the blocks.

Block format:
```
@@@memory-<N> brief="ML-NNN — <one-line lesson>" datetime="<YYYY-MM-DDTHH:MM:SSZ from date -u +%Y-%m-%dT%H:%M:%SZ>" keywords="ML-NNN, <task ids T-NNN>, <tools, error words>" type="lesson"
ML-NNN — <one-line lesson>
- Seen: <datetime> <task or TRAIN-NNN> (<role>)[; <datetime> …]
- What happened: <the mistake, surprise or slowdown, concretely>
- Lesson: <what to do differently, as a check someone can apply>
- Change: <OR-NN | brief-common line | contract <role> | task <id> | watch>
@endmemory
```

## Memories — lessons

@@@memory-4 brief="ML-001 — Edits to the agent runtime's own configuration directory prompt the user, whatever the allowlist" datetime="{{BOA_INSTALL_DATE}}" keywords="ML-001, permissions, prompts, configuration directory, briefs" type="lesson"
ML-001 — Edits to the agent runtime's own configuration directory prompt the user, whatever the allowlist
- Seen: {{BOA_INSTALL_DATE}} install (a lesson BOA ships from its proven practice)
- What happened: a builder that edited hook files in the runtime's configuration directory, and cleaned its scratch
  in the same compound commands, made the user approve prompts by hand for ten minutes: some runtimes protect their
  own configuration directory even when every other prompt is allowlisted (the runtime profile in
  `references/runtimes.md` names the directory and the behaviour).
- Lesson: before a lane edits the runtime's configuration directory (guards, hooks, settings), tell the user that
  prompts will come; the brief asks for one file per edit command and the scratch cleanup as its own allowlisted
  removal, so the prompts stay few and readable; the permission log shows them at the next train (OR-22).
- Change: a brief line for lanes that edit the runtime's configuration directory
@endmemory
