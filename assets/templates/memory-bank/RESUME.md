# RESUME.md — how to pick up {{BOA_PROJECT_NAME}} at any moment

> A **living pointer file**: it holds no state, so it never goes stale. If this file and the code disagree, **the
> code wins** — fix this file.

## Read order (a new lead session, or any agent that has to resume)
0. `AGENTS.md` (its Modus operandi first: the mood behind every rule) and the agent handbook `docs/agent-handbook.md`: where every piece of information lives and every
   tool, when and how.
1. The runtime's own instruction file, when it has one — the runtime wiring (the rules are in `AGENTS.md`, step 0).
2. This file.
3. Every file in `memory-bank/`, above all `08-OWNER-RULES.md` (every binding owner rule) and
   `09-OPERATING-PROCEDURES.md` (how the lead and the agents actually work).
4. The lead's live state in the main checkout's `{{BOA_LEAD_DIR}}/` (machine-local, never committed): `README.md`,
   `PAUSE` and `RESUME-LEAD.md` (only after a pause), `lanes.md` (registry: the newest line per lane wins) and
   `lanes/<task>.md` (lane journal: every agent's final report, written by the sub-agent stop hook).
5. Run `.boa/bin/lead-status.sh`: every open lane with its head, last agent's verdict and suggested next step,
   resume files, warnings, open PRs, Open HITL, new guard denials, DONE/total (the disk alert and the suite timings come
   from the project's own measuring). (The session-start
   hook already put its top lines into the session context.)

## Where things are
- Plan and status of every task: `memory-bank/03-IMPLEMENTATION-PLAN.md` (`python3 -I .boa/tools/plan_lanes.py`
  computes eligible tasks and progress); what happened: `05-PROGRESS.md`; why: `06-DECISIONS.md`; now:
  `active-context.md`; lessons: `10-METALEARNING.md`.
- Lane worktrees: `{{BOA_WT_DIR}}/<task>`; after a pause each holds `.lane-resume/<role>.md`.
- Pause and resume: `09-OPERATING-PROCEDURES.md` §13 (`/pause-project`, `/resume-project`); close-out: §14
  (`/close-project`).
- Duration control (gate total, per-step times, critical-path suites, speed-up tasks): `09-OPERATING-PROCEDURES.md`
  §15.
