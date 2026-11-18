# Pause and resume — the mechanics

> Installed procedure: 09 §13, `/pause-project`, `/resume-project`. This reference explains how the signal reaches
> every agent and how the state is captured, for the skill, the documentation and per-runtime wiring.

## Why a signal and not a message
A message to an agent arrives only at its next turn; an agent inside a long tool call, or one the lead forgot, keeps
working and its state is lost when the session ends. The pause flag is checked by a hook **at every tool call**, so
every agent learns of the pause at its next action, and the hooks capture what each one leaves behind.

## The pieces
| Piece | Event | What it does |
|---|---|---|
| `.boa/bin/pause-flag.sh set "<reason>"` | the lead runs it | writes `<lead>/PAUSE` (time, reason); `clear` removes it; `status` |
| `.boa/hooks/pause_guard.py` | `pre-tool`, every tool kind | while the flag exists, a **sub-agent** may only: write its own `.lane-resume/<role>.md`; append (only) to its lane's `.lane-resume/memories.md`; run read-only git; `git add` / `git commit` in its own worktree; `rm` its own scratch subdir; `kill` its own PIDs; hand back its final report (neutral kind `report`); everything else is denied with the reason "project paused: write your resume file (template in the reason), commit wip, clean up, stop your clock, end your turn". The lead is not blocked (it must flush state) |
| `.boa/hooks/subagent_stop.py` | sub-agent stop (neutral `subagent-stop`) | journals the agent's final report as always (through the lane journal writer, `.boa/bin/lane-journal.sh`); under the flag also copies the agent's resume file to `<lead>/lanes/<task>-<role>.md`, journals the stop as "paused", warns when there is no resume file |
| `.boa/hooks/lead_stop.py` | `stop` of the lead (its turn ends) | under the flag: renders the status screen (lanes, stages, resume files, next steps, Open HITL) as the marked block of `<lead>/RESUME-LEAD.md` (`<!-- boa:lead-stop:begin -->` … `<!-- boa:lead-stop:end -->`); every byte outside the block is kept, a file without the markers keeps its whole content under a new block, broken markers or a symlink are left untouched and said |
| `.boa/hooks/session_status.py` | `session-start` | injects the status, which shows the flag and lists `RESUME-LEAD.md` and every resume file |

## The pause set (exact; the pause guard implements it)
While the flag is set, a sub-agent may only: write its own `.lane-resume/<role>.md`; append (only) to its lane's
`.lane-resume/memories.md`; run read-only git; `git add` /
`git commit` in its own
worktree; `rm` its own scratch subdir; `kill` its own PIDs (the cleanup needs the task: the agent binding, else the
lane worktree's name); hand back its final report (the report tool call, neutral kind `report`, where the runtime
delivers it so).
Everything else is denied. Any other resource a lane started (containers, services) is named in its resume file and
removed by the lead with the project's own commands (the pause guard knows no container engine or service). The integrator stops BEFORE starting the next merge; a merge command already running
completes; it never
leaves a half-merged train unreported (its resume file states the stack state: which lanes merged and at which SHAs,
which are stacked and gated, which are not).

## The resume file (`<wt>/.lane-resume/<role>.md`, git-excluded, never committed)
Task and goal; branch and head SHA; uncommitted work; every deliverable done / partial / not started with its paths;
what remains, in order; every lead message and addendum received; open questions; commands to verify. The test: a
fresh agent with no memory can continue from it alone.

## Pause, step by step
`/pause-project` → flag → the lead messages every running agent → each agent finishes its atomic step, commits
`wip(<task>): …` (or declares uncommitted work), writes its resume file, cleans its scratch, ends its
turn (the guard leaves it nothing else; a read-only role, reviewer or analyzer, writes no file: it puts the same
content in its final message, the hook's "no resume file" warning is expected, and the lead writes its resume file
and the lead-dir copy from that message) → the hooks copy and journal → the lead appends the pause to the registry,
pushes the lane branches as a backup (no PRs), updates active-context and stages the pause outcome for the fold, stops the daemons → the lead's stop hook writes
its status block into `RESUME-LEAD.md` → the lead checks it and completes it by hand (outside the block: the hook keeps
every byte there). Integrator: the integrator stops BEFORE starting the
next merge; a merge command already running completes; it never leaves a half-merged train unreported (its resume
file states the stack state: which lanes merged and at which SHAs, which are stacked and gated, which are not).

## Resume, step by step
**In another runtime, first.** A pause in one runtime may be resumed by a different runtime that never worked on the
project, on the same repository. Everything the pause left (the flag, `RESUME-LEAD.md`, the resume files, the
journals, the memory bank, the `AGENTS.md` block) is plain files and reaches the new agent through `AGENTS.md`'s read
order; the first runtime's wiring (its hooks, agents, commands) is not read by the second. So when the runtime you
resume in is not one the capabilities record (04 "Environment") names, or its wiring is absent, you first redo the
capability self-assessment for this runtime (its latest official documentation and the installed version, SKILL step
1) and wire it (SKILL step 7) before you clear the flag or resume any lane. Do only what this runtime needs and leave
the other runtime's wiring untouched: never modify, move, regenerate or remove it unless the user explicitly asks,
even when it looks stale or duplicated (report what you found); the two coexist. Add this runtime to the capabilities
record and tell the user what this runtime cannot enforce. A declared limit: until the wiring exists, no hook reminds
you (no event exists before the wiring), and `AGENTS.md`'s read order is the only path to this step. Never a
bootstrap: an installed project is resumed, whatever door the agent came in by. Runtimes take turns: two runtimes
working on the same project at the same time is not supported (one lead, one scratch root); resuming in one after
the other has paused is.

Then: `/resume-project` → the session-start set → `pause-flag.sh clear` → daemons restarted → the status screen → a per-lane
plan: the same agents if the session survived (a fresh agent where the size trigger or the wait trigger of 09 §5.3 holds at the resume, else the SAME agent; a resumed
paused round is the same round continuing and never counts toward the third-round trigger), otherwise new agents of the same
role, each briefed with its resume-file path, the newest journal entry and the lead's notes since the stop. The code
and git win over a resume file that disagrees with them.

## Runtimes without hooks
Without a pre-tool hook the flag is not enforced: the lead messages every agent and checks each resume file by
hand; without a stop hook the lead writes `RESUME-LEAD.md` itself. `references/runtimes.md` lists what each runtime
supports; what it cannot do is declared in 04 "Environment".

## Edge cases
- A sub-agent that never reaches another tool call (stuck in a very long command): the lead notes it in
  `<lead>/lanes/<task>-lead.md` ("interrupted at <step>") and the next agent restarts that step.
- A pause during a train gate: the gate is interrupted (its cleanup runs on the signal), the train is re-run after the
  resume; nothing merges unless the gate finished green before the flag.
- The flag left behind after a crash: `/run-project` refuses to start while it exists and points to
  `/resume-project`.
