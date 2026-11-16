---
description: (Optional manual shortcut) Run one plan task through the builder → reviewer → tester → integrator pipeline. The lead normally does this inside /run-project.
argument-hint: <task id> (omit to pick the next eligible task)
---
<!-- BOA neutral command metadata: the header above (description, optional argument-hint) is converted by the agent to its runtime's format at bootstrap; the body is the runtime-neutral contract. -->

> Optional: `/run-project` runs every task this way on its own. Use this only to nudge one task by hand.

Run task **$1** (none given: the first eligible task from `python3 -I .boa/tools/plan_lanes.py`) through
`AGENTS.md` §6, delegating every stage to its sub-agent:

1. **Load** the session-start set (09 §1); state the task's acceptance criteria; if its dependencies are not DONE,
   pick an eligible one instead.
2. **Lane:** `.boa/bin/lane-worktree.sh add <task> <branch>` (`{{BOA_BRANCH_GRAMMAR}}`), a registry line in
   `{{BOA_LEAD_DIR}}/lanes.md`, the disk snapshot.
3. **BUILD:** `builder` (or `builder-mid` for simple low-risk work, OR-34) with the full brief (09 §4).
4. **REVIEW:** `reviewer` (full) → findings → `builder` delta → `reviewer` delta, until the review exit rule (OR-52; loop guard at 3
   attempts: ask the owner, OR-06). Docs-only: no review (OR-01).
5. **TEST:** `tester` (acceptance map, touched suites, static analysis, the lane's only targeted mutation run).
   Failure → builder → reviewer delta → tester.
6. **INTEGRATE:** a train of one (09 §7) through `integrator`: `docs(memory)` first, one gate, merge pinned to the
   gated head, residue check, cleanup, durations.
7. **Report:** what shipped, pipeline stats (attempts, findings → 0, delicate paths and MSI, gate), merge commit,
   memory files updated, disk delta, newly unblocked tasks.
