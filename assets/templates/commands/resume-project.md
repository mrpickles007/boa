---
description: Resume the project after a pause from the persisted state (flag, resume files, registry) and report.
---
<!-- BOA neutral command metadata: the header above (description, optional argument-hint) is converted by the agent to its runtime's format at bootstrap; the body is the runtime-neutral contract. -->

Resume {{BOA_PROJECT_NAME}} (09 §13).

1. Read the session-start set (09 §1), then `{{BOA_LEAD_DIR}}/RESUME-LEAD.md` and every
   `{{BOA_LEAD_DIR}}/lanes/<task>-<role>.md` written at the pause.
2. Clear the flag: `.boa/bin/pause-flag.sh clear`. Restart the project's daemons (e.g. its disk measurement, project-wiring "measure commands").
3. `.boa/bin/lead-status.sh`: check every lane's worktree, head and resume file against RESUME-LEAD; the code and git
   win over the resume files when they disagree.
4. **Per-lane resume plan** (print it as a table: task, stage, agent tier, resume file, next step): if the session
   that paused is still alive, message the SAME agents (OR-16) "resume from your resume file"; otherwise start NEW
   agents of the same role, each given its resume-file path, the newest journal entry and your notes since the
   stop. Registry line per lane.
5. Update `active-context.md` (running again), record the resume as an id-less `--format-only` block in
   `{{BOA_LEAD_DIR}}/plan-additions-pending.md` (the next fold routes it to `05-PROGRESS.md`), and continue with
   `/run-project` step 2.
6. Report to the owner in {{BOA_REPLY_LANGUAGE}}: DONE/total and the lanes resumed.
