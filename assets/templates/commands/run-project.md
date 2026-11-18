---
description: Run the whole BOA discipline on this project — mode bootstrap on the first run, then the autonomous loop (lanes → pipeline → merge trains) until the project is complete or a HITL blocks everything.
---
<!-- BOA neutral command metadata: the header above (description, optional arguments) is converted by the agent to its runtime's format at bootstrap and at every re-wire, after checking the runtime's latest documentation and installed version (OR-63); the body is the runtime-neutral contract. -->

You are the **lead** of {{BOA_PROJECT_NAME}}. Run the project end to end, autonomously, and forget nothing.

## 0. Load
1. Read `AGENTS.md` (its Modus operandi first: the mood behind every rule), `docs/agent-handbook.md`, the runtime's own instruction file if any,
   `memory-bank/RESUME.md`, every `memory-bank/*.md` (08 and
   09 are binding), then `{{BOA_LEAD_DIR}}/` (README, open-items, pending files, `lanes.md`).
2. If `{{BOA_LEAD_DIR}}/PAUSE` exists, the project is paused: run `/resume-project` instead (it wires this runtime
   first when needed) and stop here.
2b. **This runtime wired?** If the capabilities record does not name the runtime you run in, or BOA's agents,
   commands or hooks are not wired in it, redo the capability self-assessment for it and wire it now (§1's first
   bullet), doing only what this runtime needs and leaving the other runtime's wiring untouched, then go on with the
   loop. A project whose plan has tasks is never bootstrapped again (§1 runs only on an empty plan).
3. `.boa/bin/lead-status.sh`; the project's disk measurement (project-wiring "measure commands"; start it if not running); state in one line the
   milestone, the lanes and the next action.

## 1. Mode bootstrap (only when the plan has no tasks yet; 09 §23)
- **Self-wire first, in every mode (09 §23):** check the capabilities record shows the agents, the commands and the
  hooks wired in your runtime's own format, report capture included (the sub-agent-stop hook saving each agent's
  report to the lane journal, the lead-stop and session-status hooks). Not wired, or the runtime changed: do it now
  from the BOA package's `references/runtimes.md`, declare a substitute where the runtime lacks a feature, ask the
  user what you cannot tell, and record it.
- **greenfield:** turn `IDEA.md` into `00-PROJECT-BRIEF.md`, `01-BLUEPRINT.md`, specs and contracts (`02`,
  `docs/specs/`, `docs/api/`), the milestones of `AGENTS.md` §2, the plan with lanes (`03`, machine block,
  `python3 -I .boa/tools/plan_lanes.py --check` green). Stack not given → choose it from the goals (latest stable,
  verified online), ADR.
- **brownfield:** fan out `analyzer` agents (as many as the code base needs, one area each, every file read) →
  consolidate into `04-ARCHITECTURE.md`, `01` (`exists`), contracts in `02`/`docs/api/`, known issues in `07` → ask
  the owner the goals (options + recommendation) → plan.
- **refactor:** as brownfield, then characterise current behaviour (tests or goldens) as the first tasks, then plan
  the refactor from `IDEA.md`; adopt the optional clean-room rule when the IP situation needs it.
- Adopt the optional rules of the rules pool that apply (08 "Optional rules adopted"); register every task in
  `docs/parity/features.toml`; record the environment in 04; tooling tasks the project needs are planned like
  product tasks.
- Commit the bootstrap through the pipeline like any task (a docs lane: builder → tester → integrator).

## 2. The loop (AGENTS.md §6bis; 09 §3–§16)
Repeat until every milestone is DONE or a HITL blocks all remaining work:
1. **Sync reality:** git, worktrees, open PRs, the registry, the newest journal entries (OR-17: harvest finished
   agents first).
2. **Fill the lanes** (09 §3): eligible tasks from `plan_lanes.py`, hotspots serialised, product first, admission
   from `lead-status.sh` (lane cap {{BOA_LANE_CAP}}) and, before every fill, the project's disk alert (project-wiring
   "measure commands", 09 §10): while it is set no new lane starts; `.boa/bin/lane-worktree.sh add <task> <branch>`; a registry
   line; choose `builder` or `builder-mid` (OR-34; when in doubt `builder`); a full brief (09 §4, paste
   `{{BOA_LEAD_DIR}}/brief-common.md`); the sub-agent spawn's description starts with the task id.
3. **Run each lane's pipeline** (09 §5): builder → reviewer ⇄ builder delta → tester; same agent per role within the
   task (OR-16; resume or fresh agent: 09 §5.3); docs-only lanes skip review; loop guard after 3 failed attempts (09 §6).
4. **Merge trains** (09 §7): 3–4 green lanes (or the 60-minute / critical-path exceptions) → brief the integrator
   with the order, the `docs(memory)` lines and the folds.
5. **At every train:** the correspondence check (`trace_check.py`, 09 §26; new mismatches → tasks or ledger items), the duration review (09 §15: gate total, per step, critical-path suite of each parallel step,
   dominance; open speed-up tasks at once; throughput proposals), guard and permission logs (09 §11), disk
   (09 §10), open items (OR-25), owner-rules and plan folds (09 §16), the metalearning inbox → `10-METALEARNING.md`,
   deployment update if the train needs it (09 §12), the handbook current.
6. **New owner rules or requests** said in chat → pending files at once (09 §16); new features → spec + plan rows.
   In an existing project (brownfield or refactor) this holds as much as in a new one: every new feature and change goes
   through the full flow, none is edited outside a lane (OR-69).
7. **Owner decisions only** go to the owner (OR-12: options + recommendation, "Open HITL"); everything else you
   decide and record.
8. Flush memory when the context grows (AGENTS.md §3).

## 3. When everything is DONE
Check that the whole plan is DONE and the transit queue `{{BOA_LEAD_DIR}}/open-items.md` is empty, then tell the owner the project is ready for `/close-project`.
