---
description: Pause the project — a stop signal for the lead and every sub-agent; each leaves a resume file (captured by hooks), state is flushed so the work resumes losslessly.
arguments: <reason, e.g. "usage limit until tomorrow">
---
<!-- BOA neutral command metadata: the header above (description, optional arguments) is converted by the agent to its runtime's format at bootstrap and at every re-wire, after checking the runtime's latest documentation and installed version (OR-63); the body is the runtime-neutral contract. -->

Pause {{BOA_PROJECT_NAME}} now (09 §13). Reason: "<arguments>".

1. **Raise the flag:** `.boa/bin/pause-flag.sh set "<reason>"` (writes `{{BOA_LEAD_DIR}}/PAUSE`). From its next tool
   call each sub-agent may only: write its own `.lane-resume/<role>.md`; append (only) to its lane's
   `.lane-resume/memories.md`; run read-only git; `git add` / `git commit`
   in its own
   worktree; `rm` its own scratch subdir; `kill` its own PIDs (the cleanup needs the task: the agent binding, else the
   lane worktree's name); hand back its final report (the report tool call, neutral kind `report`, where the runtime
   delivers it so); the pause guard denies everything else (09 §13). Any other resource a lane started
   (containers, services) is named in its resume file and removed by the lead with the project's own commands.
2. **Tell every running agent** (message each one): "Project paused: finish only your current atomic step, commit
   coherent work as `wip(<task>): …` (or say what is uncommitted), write `<worktree>/.lane-resume/<role>.md` (task and
   goal, branch, head SHA, uncommitted work, deliverables done/partial/not started with paths, remaining steps in
   order, every lead message you received, open questions, verify commands), clean your scratch, leave no processes,
   name in it any other resource your lane started, end your turn." A read-only role (reviewer, analyzer) gets "put
   that content in your final message instead: you write no file". Integrator: the integrator stops BEFORE starting the next merge;
   a merge command already running completes; it never
   leaves a half-merged train unreported (its resume file states the stack state: which lanes merged and at which SHAs,
   which are stacked and gated, which are not).
3. **Wait** for every agent to stop (bounded: check the journal `{{BOA_LEAD_DIR}}/lanes/<task>.md`; an agent that
   does not stop within a reasonable time is noted in the resume file as "interrupted at <step>").
4. **Check the capture:** the sub-agent stop hook copied each resume file to `{{BOA_LEAD_DIR}}/lanes/<task>-<role>.md`
   and journaled "paused"; for a read-only role (reviewer, analyzer) its "no resume file" warning is expected: write
   its `.lane-resume/<role>.md` and `{{BOA_LEAD_DIR}}/lanes/<task>-<role>.md` from its final message; for any other
   lane without one, write what you know into `{{BOA_LEAD_DIR}}/lanes/<task>-lead.md`.
5. **Flush:** append the pause to `{{BOA_LEAD_DIR}}/lanes.md`; push every lane branch as a backup (no PRs); update
   `active-context.md` ("paused since …") and record the pause as an id-less `--format-only` block in the lead's staging file `{{BOA_LEAD_DIR}}/plan-additions-pending.md` (the next fold routes it by type); fold nothing new.
6. **Stop the daemons:** the project's own (e.g. its disk measurement, project-wiring "measure commands"). When you end your turn the stop hook
   (`.boa/hooks/lead_stop.py`) renders the status screen as the marked block of `{{BOA_LEAD_DIR}}/RESUME-LEAD.md`
   (every byte outside the block is kept); check it reads right
   (lanes, stages, lanes "merged, fold pending", next step per lane, decisions in flight, open HITL, what to do
   first) and complete it by hand where
   it lacks something.
7. Report to the owner in {{BOA_REPLY_LANGUAGE}}: DONE/total, the lanes paused and at which stage, how to resume
   (`/resume-project`).
