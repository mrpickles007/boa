# 03 The workflow

The shape of a project under BOA:

```
/build-on-autopilot <mode> [idea-file]  ->  assess + install + wire + self-tests
run-project   ->  mode bootstrap (once)  ->  loop: lanes -> pipeline -> merge trains  ->  ...  ->  close-project
pause-project <-> resume-project at any point (state persisted, hooks capture every agent's report)
```

The binding text is the installed `AGENTS.md` and `memory-bank/09-OPERATING-PROCEDURES.md`; the reference behind
them is [references/workflow.md](../references/workflow.md) and the procedures index
[references/procedures.md](../references/procedures.md).

## The plan is the single source of work

The implementation plan (`memory-bank/03-IMPLEMENTATION-PLAN.md`) is the only list of work. It is built for
parallelism: after the analysis, and whenever scope changes, the lead re-plans, splitting tasks until they are small
and independent, with their dependencies, the hotspots that must be serialised, the contract clauses each task
implements and the edge cases it must handle (boundaries, empty or oversized input, concurrency, failure and retry,
permissions, time and locale, partial failure). Task ids are `T-NNN` (at least three digits, no upper limit).
`plan_lanes.py --check` checks the plan and computes waves, hotspots, the critical path and progress
([tool card](../assets/templates/agent-handbook.md#tool-card-plan-lanes)). Tooling tasks are planned like product
tasks.

## Lanes and worktrees

Every independent task runs in its own lane: one git worktree and one branch named by the configured grammar
(`BOA_BRANCH_GRAMMAR`). `boa lane add <task> <branch>` creates a lean worktree from current main and
`boa lane remove` refuses to delete unpushed or uncommitted work
([tool card](../assets/templates/agent-handbook.md#tool-card-lane-worktrees)). The lead keeps as many lanes running
as the dependency graph and the machine allow: `boa status` computes admission from free memory and load against
`BOA_LANE_CAP` ([08 Measuring](08-measuring.md#the-status-screen)). Shared work is done once: a few-line fix in a
running lane's own module is absorbed by that lane, and the tester's receipts are reused by the train. One stage is
active per lane at a time; agents never open tasks themselves.

## The pipeline

Every task runs through:

```
builder -> adversarial reviewer (full, then delta re-reviews) -> tester -> integrator (merge train)
```

- The **builder** (or builder-mid for simple, low-risk work) implements exactly one task from its contract clauses,
  runs only the tests for what it changed, and ends with its report.
- The **reviewer** assumes the diff is broken and tries to prove it; every finding has a concrete failure scenario.
  A change that touches only docs or prose gets no review round.
- The **tester** maps every acceptance criterion and contract clause to a test that runs, runs the touched suites
  and static analysis, and runs the lane's only targeted mutation run (or plant rounds).
- The **integrator** lands tested lanes on main through a merge train: main is never red.

Any stage that finds a problem bounces the lane to its builder; a code fix re-enters review. The roles in detail:
[04 Roles](04-roles.md). An existing project gets every new feature and change through this same flow.

## Specs, plan and requirements from the current main

Every agent reads the specifications, the plan, the requirements and the owner rules from the project's current main
checkout, never from the copy inside its lane worktree, which can be stale (a stacked lane above all): after a fetch
with `git -C <worktree> show origin/<main>:<path>`, or from the main-checkout path its brief gives. A finding judged
against a stale lane copy is void (rule OR-57 of the [rules pool](../references/rules-pool.md)).

## Reviews and their exit rule

Every finding is classed BLOCKING (a broken or untested contract clause, wrong or lost data, a security hole or a
fail-open guard, a regression, a crash on reachable input, a delicate path without a fault-catching test, an unmet
acceptance criterion) or NON-BLOCKING (naming, wording, docs, cosmetics, hardening against unreachable input,
simplification), with a reason; the lead may re-class. Re-reviews are delta reviews by the same reviewer: the changed
lines, what they touch, and whether each earlier finding is resolved. A lane leaves review after a round with no
findings, or after two consecutive rounds with no blocking finding (the second only if code changed). Open
non-blocking findings are fixed in the same round or relocated to a named task, never lost. A clean verdict says what
was tried and failed to break the code. (Rule OR-52 of the [rules pool](../references/rules-pool.md).)

## Tests: targeted runs, case selection and plant rounds

Tests are targeted and fast:

- **Who runs what.** The builder runs only the tests for what it changed; the reviewer runs what proves or disproves
  a finding; the tester runs the suites its change touches; the integrator runs the ONE gate of a train. Nobody runs
  the full battery outside the integrator's gate.
- **Case selection.** Every test runner the project uses has a case filter, so a run can be narrowed to the cases a
  change touches. The generic plug-in's runner contract names it (`--filter=<pattern>`,
  [writing a stack plug-in](11-modes.md#writing-a-stack-plug-in)); the project's own shell suites get one too, and a
  filter that selects nothing fails loudly. BOA ships no selection helper: the agent builds the filter into the
  project's test tooling.
- **Plant rounds.** Where no mutation tool fits (or as its complement), the tester plants faults by hand: one per
  checked behaviour (invert a condition, drop a check, change a boundary). Each plant runs only the cases that cover
  the planted line, in its own scratch copy of the worktree, independent plants in parallel up to the lane cap; a
  plant counts as caught only when a covering case fails for the planted reason, after a green unplanted baseline
  (otherwise a crash is a false kill). The whole suite runs once at the start and once at the end, never per plant.
  At most 3 plant rounds per lane ([Stage budgets](#stage-budgets)).
- **Suites without waste.** One behaviour per case, small independent cases, heavy setup once per suite, no check
  duplicated across suites, a costly case split, self-test plant cases (the permanent plants a suite or gate self-test keeps) next to the
  cases they target (rule OR-72 of the [rules pool](../references/rules-pool.md); the duration watch catches the cost
  side at every train, the reviewer checks the rest).
- **Both directions.** A test that reproduces a fixed defect fails on the code before the fix and passes after it.
- **Real inputs.** Code that maps, validates, renders or installs files another part produces is tested at least
  once per round against the real files on current main, not only fixtures.
- **Light and heavy.** Light suites run locally; heavy runs go to the remote runner when there is one
  ([09 Remote runner](09-remote-runner.md#light-and-heavy-suites)).

The rules behind these: OR-03, OR-54, OR-55, OR-56 of the [rules pool](../references/rules-pool.md); the tester
contract `.boa/agents/tester.md`.

## Mutation testing

Mutation testing runs only on delicate code (security and authorisation, licensing, crypto and tokens, billing and
money, data access and queries, migrations, anything where a silent wrong result is costly), only on the lines the
task changes, with only the tests that cover them, through one wrapper, capped in time. The tester runs the lane's
only mutation runs (one per tester round, at most 3 per lane across bounces); the full scope runs only at milestone closure. Whether there is delicate code and which tool fits
the stack is asked and decided at bootstrap; where no tool fits, planted faults are the honest fallback. The
reference: [references/mutation-testing.md](../references/mutation-testing.md).

## The project gate

The project has ONE gate, written by the agent in the project's own task runner or CI (the project-wiring item
"the project gate"): the checks it chooses for its stack, plus BOA's kept checks, which it must call and never
remove: `trace_check.py` (every contract clause has a running test), `handbook_drift.py`, `memory_lint.py`, and
`trace_check.py --close` at close. A misalignment is a red gate, never a warning. Builders
and testers run one step or the changed files; the integrator runs it once per train on the stacked tip. Its self-test
is discipline too: one planted defect per step, caught once. Its timings feed duration control
([08 Measuring](08-measuring.md#duration-control)).

## Merge trains

When several lanes are green they land together: 3 to 4 lanes stacked on current main in order of independence, ONE
`docs(memory)` commit on top (plan, progress, the memory ingest, the folds of pending rules and plan rows,
metalearning, the handbook), ONE gate on the exact tree that lands, merges pinned to the gated head. On a red gate the
train bisects to the lane that breaks it and bounces only that one; the integrator resolves only mechanical conflicts,
and anything needing judgement bounces to the builder. After the merge: residue checked per lane, durations reviewed,
worktrees and branches removed. The reference: [references/merge-trains.md](../references/merge-trains.md).

## Leftovers and the transit queue

Every report ends with a `Leftovers:` section (or `Leftovers: none`). The sub-agent stop hook captures each item into
the lead's transit queue (`<lead dir>/open-items.md`) and flags a task agent's report without the section
([tool card](../assets/templates/agent-handbook.md#tool-card-lane-journal-and-report-capture)). The next train's fold
places every queued item into the plan: no action with a reason, merged into a duplicate, absorbed by a running lane,
a dated note on the row that owns it, a batch task per area, and only last a new task. There is no parallel to-do
list: the plan is the only source of work, and close-out needs the whole plan done and the queue empty.

## Stage budgets

Every stage has a budget: the tester at most 3 mutation runs and 3 plant rounds per lane and a time budget computed
from what it must run; the builder and the reviewer about 60 minutes per round. At the budget the agent stops
iterating and reports the current state; the lead accepts, bounces or extends once, with a reason. The status screen
flags a lane over budget.

## Schema migrations

Schema migrations are a delicate, serialised path whatever the stack: targeted mutation, real-engine tests in every
isolation mode that matters, lock-first writes, the schema spec amended first, and a migrations hotspot the lead
serialises so only one lane changes the schema at a time (rule OR-62 of the [rules pool](../references/rules-pool.md)).

## Loop guard

When the same finding, failure or bounce survives 3 builder attempts, the lane stops, the blocker is written down and
the lead asks you, with a recommendation (usually a final, targeted fourth attempt). Other lanes keep going.

## Asking the user (HITL)

The lead runs autonomously and stops only for a decision it genuinely cannot take: product and business trade-offs,
legal and licensing, money, anything destructive or irreversible outside the repository, a genuine fork with no
objective winner, or a fact only you know. It asks one question at a time, with the alternatives, their honest pros
and cons, and its recommendation first; it records the question and keeps working on everything not blocked by it.
Everything technical it decides by the standards and records as a decision. A new rule you give reaches every running
agent at once ([06 Rules pool](06-rules-pool.md#a-new-rule-reaches-every-agent)).
