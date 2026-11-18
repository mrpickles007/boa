# 08 Measuring

The lead designs and measures. BOA ships the status screen, the plan check, the traceability check, the handbook drift
check and metalearning as code; the clock, the timing records, throughput, the disk measurement and the residue check
are the project's own, built by the agent from the project-wiring checklist
([references/project-wiring.md](../references/project-wiring.md)), and judged with the playbook of
[references/duration-control.md](../references/duration-control.md).

## The status screen

`boa status` (the `lead-status` tool) prints "where is everything" in one read-only screen: dead guards first (`GUARD
DOWN` lines), every open lane with its last agent's verdict and the suggested next step, whether a new lane may start
now (admission from free memory and load against `BOA_LANE_CAP`, `BOA_ADMIT_MIN_MEM_MB`, `BOA_ADMIT_MAX_LOAD`,
`BOA_LANE_MEM_MB`), every warning (pause, pending owner rules, stale journals, stages over budget, aged transit-queue
lines, unfolded plan lines), resume files, HITL, guard denials and the count of tasks done out of the total. The
session-start hook injects its top into every new session. Options: `--no-gh` (skip the forge's open-PR/MR list),
`--guards` (only the guard health check). Limits: the admission needs the memory and load figures of Linux (`/proc`);
elsewhere it says "unknown". Card: [lead status](../assets/templates/agent-handbook.md#tool-card-lead-status).

## Plan checks

`python3 -I .boa/tools/plan_lanes.py --check` validates the plan's machine block and computes waves, hotspots, the
critical path and progress; it runs after every plan edit and before lanes are filled
([tool card](../assets/templates/agent-handbook.md#tool-card-plan-lanes)).

## Traceability

`python3 -I .boa/tools/trace_check.py` is the one correspondence check: tasks, contracts, specifications, features,
tests, the residue register and the folds must agree. Every feature of `docs/parity/features.toml` maps to its tasks
and to the tests that prove it (`@covers-feature F-ID T-NNN` in a test's header); every contract clause has a running
test (`@covers-contract`); a task without contract clauses, a clause without a test or a contract amended without its
decision is refused. It prints one `MISMATCH` line per problem and `MISMATCHES: <n>`; the project gate runs it, and
`--close` adds the close-out relations (every contract closed, the transit queue empty, every fold folded, the residue
register empty, no open bug, every task done, every feature done and traced), which must report 0. `--report` prints
the feature report (measured parity: counts per milestone, status, tests per feature)
([tool card](../assets/templates/agent-handbook.md#tool-card-traceability);
[14 Contract-driven development](14-contract-driven-development.md#tracing-and-closing)).

## Handbook drift

The installed `docs/agent-handbook.md` maps every tool, path and procedure, with a tool card per BOA tool. It is kept
current by every change, and `python3 -I .boa/tools/handbook_drift.py` (run by the project gate) fails on a file
under `.boa/` the handbook does not name, a named `.boa/` path that does not exist, a tool file on no card, a card
missing a field, a stack block that differs from the plug-in's rows, or a broken relative link (in `AGENTS.md`, the
handbook or, when it exists, `docs/boa-rules.md`); it ends with
`SUMMARY: <n> drift finding(s)`. It knows no agent runtime: the project checks its runtime renderings against their
`.boa/` sources itself ([tool card](../assets/templates/agent-handbook.md#tool-card-handbook-drift)). The handbook is
reviewed periodically, so any agent can take over at any moment.

## Duration control

The project keeps its gate's timings (total, each step, each suite) and judges them at every train: the total against
`BOA_GATE_BUDGET_S`, each step against its budget and its trend, the critical-path suite of every parallel step, and a
step dominated by one suite above `BOA_DOMINANCE_PCT` % even when it is under budget. A step over budget, trending up
or dominated becomes a speed-up task in the integrator's train report: measure first, keep identical coverage, prove
planted faults are still caught. Runs under unusual load are marked suspect. How to build and read it:
[references/duration-control.md](../references/duration-control.md) and the project-wiring item "suite timings and
duration control". Every test run and every planted-fault run is bounded by a timeout derived from its own recorded
duration and never above the cap `run_timeout_cap_s` of the budgets file; a timeout is a failure (for a planted fault that
times out while a covering case is running, a kill by timeout confirmed by a replay alone unless the first run already
ran alone, provided its clean baseline run finished inside the bound; the replay confirms, it is not a retry, and a
replay that ends gives its own verdict; a timeout outside every covering case, confirmed the same way, is invalid,
like a failure there; when the cap clipped the bound, a confirmed timeout is skipped, never killed or invalid: raise the
cap; a plant whose clean baseline run is already over the bound is skipped (not run): raise the bound within the cap or
narrow the cases, as for a mutant), never a reason to repeat the run, and the suite budget stays a reporting target, not a kill timeout.
How a run is stopped is wired too, not only when: a run stopped at its timeout, by an interrupt, by a hangup or by the
end of the agent session is stopped whole, the command and every process it started (its process group, or the
platform's equivalent), its own cleanup given a bounded grace, then forced, with no orphan process and no leftover
file; the wiring proves it with a planted hanging case and an interrupted run.

## Clock, throughput and cost

The project records how long each task takes: wall time from the first builder start to done, the time per role and
per phase (review rounds, the gate), and, where the runtime reports them, the tokens of each agent run (or declares
them unavailable); every agent gets the UTC time for its memory blocks. Records never hold a prompt, a transcript or a
secret. The throughput review (weekly, or every few trains) computes tasks done per day, agent time per role, waits,
lanes active against the cap and the gate's median against its budget, and turns them into proposals with the figure
behind each (more or fewer lanes, a remote runner, a bigger runner, a speed-up task); it is advisory. Spending little
is part of the discipline: targeted runs, delta reviews, the prompt cache kept warm (rule OR-36), the cheaper model
for simple work, and a fresh agent instead of a resume once an agent's context size outgrows the lower of about half its
model's window and `BOA_AGENT_FRESH_TOKENS` (200000 by default), when the round to send would be the agent's third, or when the wait has outlasted the cache lifetime. The project-wiring item: "usage clock and throughput".

## Disk

The project measures only its own paths (the repository, its worktrees, dependency dirs, build and test caches, logs,
its own containers, images and volumes) against `BOA_DISK_WARN_MB` and `BOA_DISK_HARD_MB`, around heavy steps and at
every train, and raises an alert the lead reads at session start; on a breach the project's own leftovers are cleaned
first, never another project's. The project-wiring item: "measure commands".

## Residue

Zero residue, per task and at the end: every leftover that is provably the project's (worktrees, branches local and
remote, scratch dirs, labelled or prefixed containers, networks, volumes and images, deployed-instance objects, a
running daemon) is listed with read-only commands and fails the check unless the residue register
(`memory-bank/04-ARCHITECTURE.md`) names it with its owner task and removal step. It runs at every lane merge, at
milestone closure and at close-out, where the register must be empty; `trace_check.py` checks the register's rows.
The project-wiring item: "deployed-instance objects".

## Logs to read at every train

- the guard log `<BOA_LOG_DIR>/guard-denials.jsonl` (denials, every `OVERRIDE` and `ESCAPE` of the lead), shown in
  the status screen;
- the project's permission log ([05 Safety](05-safety.md#the-permission-log));
- the metalearning file and `metalearning.py curate` ([07 Memory and state](07-memory-and-state.md#metalearning));
- the timing judgement and the throughput figures above.
