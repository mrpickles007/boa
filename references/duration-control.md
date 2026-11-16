# Duration control, done properly

> Rule OR-20 of `rules-pool.md`; installed procedure: 09 §15 and `AGENTS.md` §11; the integrator's "Timing watch".
> This reference explains the design and the reasons, for the skill, the documentation and anyone tuning budgets.
> BOA ships none of the tools named below: the project builds them with its own gate, CI or test runner (the
> project-wiring items "suite timings and duration control" and "usage clock and throughput"); the names are
> the shape to follow.

## The problem it solves
Every task adds a few seconds of tests. Nobody notices one suite growing from 40 to 70 seconds, but a project with
hundreds of tasks ends with an hour-long gate, and a single suite can come to own a whole parallel step while still
"under budget". Speed-ups found late are expensive; the same speed-up found when the step first became dominated is
cheap. Duration control makes the growth visible at every merge train and turns it into a task at once.

## What is measured (the ledger)
The project's timing writer appends one JSON record per gate run (pass, fail or interrupted) to the timing ledger:
the commit, the mode (pre-merge, changed files, one step), the gate total, **each step's wall time**, each suite's
time, exit status and timeout flag, which suites ran in the parallel batch, the worker count, the load averages and
CPU count, and whether the run came from the remote runner (the runner copies back exactly one shape-checked record
per run). The gate starts the parallel batch longest-first (from the ledger), so a parallel step's wall time is
about its longest suite.

## The budgets file (`suite-budgets.json`)
- `default_suite_budget_s` and `suite_budget_s` overrides — **each override with a written reason**;
- `step_budget_s` — a budget per gate step;
- `total_budget_s` — the gate total;
- `dominance_pct` — the share of a parallel step's wall time above which one suite "dominates" it;
- `trend` — `window` (runs compared), `regression_pct` and `min_delta_s` (both must be exceeded);
- `load` — `max_per_cpu` (runs above it are excluded from the trend), `skew_per_cpu` and `suspect_floor_per_cpu`
  (a regression under load skew is SUSPECT, not REGRESSED).
Budgets change only with a written reason recorded in 06.

## The check (the project's timing check)
Read-only, a few seconds, comparable runs only (same mode, same worker count, not a self-test, load under the limit).
For the gate total, for **each step**, and for each suite: OVER-BUDGET (median of the last window over budget),
REGRESSED (median up by more than the threshold and the minimum delta against the previous window), SUSPECT
(regression under load skew), TIMED-OUT. For each **parallel step** it names the **critical-path suite** (the
longest, which bounds the step) and its share; a share above `dominance_pct` is DOMINATED **even under budget**.
The last line is `SUMMARY: …`; a clean verdict, findings, a configuration error and too few samples are told apart.

## When it runs
At the end of every gate (its `SUMMARY:` closes the gate output), at every merge train (the integrator puts the table
in its report, also after a failed gate), at milestone closure, at close-out, and in the lead's train report.

## What the lead does with it — every train
1. For each step: **"can it be optimised?"** The integrator's report gives a per-step verdict.
2. Open a speed-up task **at once** (a plan row through the pending fold, not a note) when the gate total, a step or
   a suite is OVER-BUDGET, REGRESSED, or a step is DOMINATED. "Watching" a growing suite is how it comes to own the
   step.
3. A SUSPECT row is re-judged at the next unloaded train, never by re-running under load; never synthetic load.

## The speed-up playbook (for the speed-up task's builder and tester)
1. **Measure first:** where does the time go — per check, per external call, per process spawn, per container start.
2. **Change the expensive part:** fewer spawns, shared fixtures, caching, parallelism inside the suite, splitting a
   dominating suite, tiering (a suite whose inputs did not change since its last pass may be skipped by the default
   gate and runs at milestone closure, with `--tier all`, and whenever its inputs change).
3. **Prove identical coverage:** the same recorded call set (stubs record every call; the set before and after is
   identical), every planted fault still caught, the same checks counted.
4. **Record before/after timings** in the task's 05 entry; adjust the budget only with a written reason.
5. **Speed never trades away coverage:** a speed-up that drops a check, a case or a planted fault is rejected.

## Throughput (agent time, not test time)
The project's throughput review reads the clock ledger: tasks per day, wall time per lane against its size estimate, time
per stage (build, review rounds, test, waiting for a train), the gate time per train, the runner queue, and the tokens
per agent run where the runtime exposes them (otherwise the clock says "declared unavailable", never an estimate). It proposes
remedies: fewer lanes when lanes stall on host load, more when the host idles, a remote runner (or a bigger one) when
heavy runs queue, worker counts, tiering. A proposal that costs money (a bigger runner) goes to the owner as a HITL
with options and a recommendation; the rest the lead decides and records.
