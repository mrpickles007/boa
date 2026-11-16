---
description: (Optional manual shortcut) Flush durable state into the memory bank. The lead does this on its own (AGENTS.md §3); use for a manual flush, e.g. before a likely compaction.
---
<!-- BOA neutral command metadata: the header above (description, optional argument-hint) is converted by the agent to its runtime's format at bootstrap; the body is the runtime-neutral contract. -->

Reconcile the memory bank with reality:

1. Diff reality against the bank: `git log`, `git status`, the code, open worktrees, branches and PRs, the lead
   registry — against `03-IMPLEMENTATION-PLAN.md` (statuses), `05-PROGRESS.md` and `active-context.md`.
2. **Code is truth:** wherever the bank disagrees with the code, fix the bank.
3. Update: `active-context.md` (milestone, lanes, next action, Open HITL, blockers); `01`/`02`/`04` (scope or design
   changes). Everything that lands in 05, 06, 07 or 10 (completed or advanced work, decisions not yet logged, new
   security facts, the lessons of the inbox) goes as id-less `--format-only` blocks into the pending files of
   `{{BOA_LEAD_DIR}}/` (with new owner rules and plan rows), so the next train folds them: never a direct write.
4. The project's disk measurement (project-wiring "measure commands"): record the footprint and trend in `active-context.md`; clean the project's own
   caches and stale worktrees if it grew abnormally (never another project's files).
5. Confirm `active-context.md` plus `RESUME.md` are enough for a cold session to know exactly what to do next.
6. Report what you updated in one short list.

Rule: no orphan knowledge — anything a future session needs lives in a file, not only in this conversation.
