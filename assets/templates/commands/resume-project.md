---
description: Resume the project after a pause from the persisted state (flag, resume files, registry) and report.
---
<!-- BOA neutral command metadata: the header above (description, optional arguments) is converted by the agent to its runtime's format at bootstrap and at every re-wire, after checking the runtime's latest documentation and installed version (OR-63); the body is the runtime-neutral contract. -->

Resume {{BOA_PROJECT_NAME}} (09 §13).

1. Read the session-start set (09 §1), then `{{BOA_LEAD_DIR}}/RESUME-LEAD.md` and every
   `{{BOA_LEAD_DIR}}/lanes/<task>-<role>.md` written at the pause. Never a bootstrap: BOA is installed here.
1b. **This runtime first.** When the runtime you resume in is not one the capabilities record
   (`memory-bank/04-ARCHITECTURE.md` "Environment") names, or BOA's agents, commands or hooks are not wired in it,
   redo the capability self-assessment for this runtime (its latest official documentation and the installed
   version) and wire it (the BOA package's `SKILL.md`, steps 1 and 7) before you clear the flag or resume any lane.
   Do only what this runtime needs; leave the other runtime's wiring untouched (never modify, move, regenerate or
   remove it unless the user explicitly asks, even when it looks stale: report it), the two coexist. Add this
   runtime to the capabilities record and tell the user what this runtime cannot enforce. A runtime new to the
   project may not know where the BOA package is: find it (a copy installed as a skill on this machine, else ask the
   user); when `.boa/commands/` or `.boa/bin/` is missing (a fresh clone), run
   `sh <package>/core/bin/boa install --target . --package <package>` first. When the runtime that last worked on
   the project is not this one, set the per-runtime keys again (`BOA_SCRATCH_ROOT`, `BOA_SCRATCH_GLOB` in
   `.boa/config.env`, from this runtime's profile). Until that wiring exists no hook reminds you of this step:
   `AGENTS.md`'s read order is the only path to it (a declared limit).
2. Clear the flag: `.boa/bin/pause-flag.sh clear`. Restart the project's daemons (e.g. its disk measurement, project-wiring "measure commands").
3. `.boa/bin/lead-status.sh`: check every lane's worktree, head and resume file against RESUME-LEAD; the code and git
   win over the resume files when they disagree.
4. **Per-lane resume plan** (print it as a table: task, stage, agent tier, resume file, next step): if the session
   that paused is still alive, message the SAME agents (OR-16) "resume from your resume file", unless a trigger of 09 §5.3 holds at the resume (the size trigger or the wait past the cache lifetime: then a fresh agent; a resumed paused round never counts toward the third-round trigger); if the session that paused is gone, start NEW
   agents of the same role, each given its resume-file path, the newest journal entry and your notes since the
   stop. Registry line per lane.
5. Update `active-context.md` (running again), record the resume as an id-less `--format-only` block in
   `{{BOA_LEAD_DIR}}/plan-additions-pending.md` (the next fold routes it to `05-PROGRESS.md`), and continue with
   `/run-project` step 2.
6. Report to the owner in {{BOA_REPLY_LANGUAGE}}: DONE/total and the lanes resumed.
