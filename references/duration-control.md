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
- `default_suite_budget_s` and `suite_budget_s` overrides — **each override with a written reason**; the budget is the
  duration target for OVER-BUDGET reporting, never a kill timeout;
- `run_timeout_cap_s` — the cap on the timeout of any test run, planted-fault run or mutant run (see "Bounding a run");
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

## Bounding a run
Every test run and every planted-fault run runs under a timeout derived from that run's own recorded duration, never a
fixed number: from the suite or case timings the project keeps (the gate's timing record, or the stack runner's), for
example about three times the median of its recent runs, and never above the cap `run_timeout_cap_s` of the project's
budgets file; a run with no history uses the cap itself. The suite budget (`default_suite_budget_s`) is the duration
target for OVER-BUDGET reporting and is never used as a kill timeout. A planted-fault run uses the duration of the
covering cases' clean baseline run (the run before the plant). A timeout is a failure, and for a planted fault that
times out while a covering case is running it counts as killed by timeout, recorded as such, provided the clean
baseline run finished inside the bound and the timeout is confirmed by a replay alone, unless the first run already
ran alone (no other run active at any time during it): a replay of the plant alone, under the same timeout, times out
too, while a replay that ends gives its own verdict; a timeout outside every covering case is confirmed the same way
and is invalid, like a failure there; when the cap clipped the bound (the timeout derived from the clean baseline run
is above the cap), a confirmed timeout is skipped, never killed or invalid: raise the cap; a plant whose clean baseline
run is already over the bound is skipped (not run): raise the bound within the cap or narrow the cases, as for a mutant.
A test that waits on a lock, a queue or the network sets its own short bound, never the product's long default. A
hanging run is never repeated in the hope that it passes (OR-06): the cause is investigated. The replay alone of a
timed-out plant is not such a retry: it confirms a kill, and a replay that ends points at contention (a shared lock,
the host's load) as the cause to investigate.

## Stopping a run
The timeout says WHEN a run stops; this says HOW. A run stopped at its timeout, by an interrupt, by a hangup or by the
end of the agent session that started it is stopped whole:
1. **Everything it started.** The run is started so that it can be stopped as one unit: its own process group or
   session on Linux and macOS, the platform's equivalent elsewhere (a job object on Windows), and the stop reaches the
   command and every process it started, never only the first one. A wrapper that starts several parts (a remote part
   and a local part, a suite and its services) starts each as such a unit and stops all of them.
2. **Its own cleanup first, bounded.** The stop first asks politely (the termination signal, or the platform's
   equivalent), once: the run's own cleanup (removing its temporary files, cancelling its remote run, stopping its
   containers) is given a bounded grace to finish (a few seconds to about half a minute, recorded with the budgets);
   a repeated interrupt only waits, it never restarts that cleanup. After the grace the stop is forced (kill).
3. **No orphan, no leftover.** Nothing of the run keeps running after the stop, and nothing it created stays: its
   temporary files and directories, its labelled resources, and, on a remote runner, its run directory and its
   processes there (project-wiring "remote runners", the cleanup bullet). A leftover found later is residue, and the
   stop that left it is a defect of the wiring.
4. **The session's end counts.** When the agent session ends (it is closed, it loses its terminal, its runtime stops
   it), the runs it started receive the hangup or the termination and stop the same way; a run meant to outlive the
   session is never started by a test step.
5. **Proved, not assumed.** The wiring proves it once with a planted hanging case stopped at its derived timeout and
   with an interrupted run (an interrupt, then a hangup): afterwards no process of the run is alive (by its process
   group, its label or its run id) and no file of it is left; the same proof on the runner when one is wired.

## Throughput (agent time, not test time)
The project's throughput review reads the clock ledger: tasks per day, wall time per lane against its size estimate, time
per stage (build, review rounds, test, waiting for a train), the gate time per train, the runner queue, and the tokens
per agent run where the runtime exposes them (otherwise the clock says "declared unavailable", never an estimate). It proposes
remedies: fewer lanes when lanes stall on host load, more when the host idles, a remote runner (or a bigger one) when
heavy runs queue, worker counts, tiering. A proposal that costs money (a bigger runner) goes to the owner as a HITL
with options and a recommendation; the rest the lead decides and records.
