# Mutation testing — when, how, whether, which tool

> Rules OR-29 (targeted, one wrapper) and OR-30 (strict roles) of `rules-pool.md`; installed procedure: 09 §24, the
> tester and integrator contracts, handbook §4.2. This reference is the full discipline, proven on a real project
> where an untargeted run once took over an hour inside a single lane and more time went into testing than into
> building.

## Why mutation testing at all
A green suite proves the code passes its tests, not that the tests would notice a wrong result. Mutation testing
changes the code in small ways (a `<` becomes `<=`, a condition is negated, a return value is replaced) and checks
that some test fails for each change. On the code where a silent wrong result is costly, that is the only measure
that the tests actually catch faults.

## WHEN — delicate paths only
Mutation-test only the code a task **changed** in these classes:
- security and authorization (role and ownership checks, input validation at trust boundaries);
- crypto, licensing, tokens and sessions (signing, verification, expiry, binding);
- money and credit math (prices, balances, quotas, rounding);
- data access and queries (filters, scoping, joins that enforce ownership);
- migrations (data transformations, defaults, constraints);
- concurrency and locking (lock order, idempotency, retries);
- stream, session or request authentication paths;
- anything else where a silent wrong result is costly (the reviewer names it).
Trivial glue, wiring, boilerplate and pure presentation are **not** mutation-tested: good unit and integration tests
suffice, and mutating them only produces low-value tests.

## HOW — targeted, through one wrapper
1. **Changed lines only.** The scope is the lines the task changed against the merge-base with main (committed,
   uncommitted and untracked), never whole unchanged files, never the whole code base in a task.
2. **Covering tests only.** The coverage run uses only the tests that cover those lines: the tests the task changed or
   added plus those that exercise the changed units; a narrower explicit list may replace the automatic match. Never
   the whole suite as the covering set.
3. **One wrapper.** The stack plug-in's mutation wrapper (written by the agent for the project) is the only way to
   run the mutation tool (a protected-command rule refuses any other: project-wiring item "project protections"). It
   is niced, runs with few threads in a constrained container where the stack
   uses containers, and owns the caps:
   - a **wall-clock cap per batch** (default 20 minutes): the wrapper splits a run into batches expected to fit,
     halves a capped batch and re-runs the halves; a **single file** that passes the cap ends the run with "scope too
     wide" — narrow the covering tests first, then report the numbers (mutants, seconds per mutant, covering tests
     per mutant) to the lead;
   - a **total bound per call** (default 4.5 caps): nothing runs past it; the files it stops are not judged;
   - **only the lead** raises a cap or the bound, for one run, with a written reason printed in the run's output.
   A run expected to take more than about 15 minutes has the wrong scope.
   - **host-aware slots:** the wrapper refuses to start (a distinct exit status; a wait-and-retry option) while the
     host's mutation slots are full: about 2 concurrent runs on a shared development host, about a quarter of the CPUs
     (at least 2) on a dedicated runner, counted from the running mutation containers or processes; on the
     development host it also waits while a train gate runs. The train's own run has priority.
4. **0 skipped mutants.** A mutant is *skipped* when it never ran, because the clean baseline run of its covering tests
   already exceeds the bound: raise the bound within the cap (`run_timeout_cap_s`) or narrow the covering tests, then
   re-run; a skipped mutant is never a pass. A mutant that ran and timed out is not skipped: it is *killed* by timeout.
   **Bounded runs:** every mutant run and every hand-planted fault run runs under a timeout derived from that run's own
   recorded duration, never a fixed number: from the suite or case timings the project keeps (the gate's timing record,
   or the stack runner's), for example about three times the median of its recent runs, and never above the cap
   `run_timeout_cap_s` of the project's budgets file; a run with no history uses the cap itself. The suite budget
   (`default_suite_budget_s`) is the duration target for OVER-BUDGET reporting and is never used as a kill timeout. A
   mutant or planted-fault run uses the duration of the covering cases' clean baseline run (the run before the plant). A
   timeout is a failure, and for a mutant or planted fault that times out while a covering case is running it counts
   as killed by timeout, recorded as such, provided the clean baseline run finished inside the bound, and the control
   run replays it like any other kill (a planted fault's timeout is confirmed by a replay alone, unless the first run
   already ran alone: the replay uses the same timeout, a second timeout confirms the kill, while a replay that ends
   gives its own verdict; a timeout outside every covering case is confirmed the same
   way and is invalid, like a failure there; when the cap clipped the bound (the timeout derived from the clean
   baseline run is above the cap), a confirmed timeout is skipped, never killed or invalid: raise the cap); a plant
   whose clean baseline run is already over the bound is skipped (not run): raise the bound within the cap or narrow the
   cases, as for a mutant. A test that waits on a lock, a queue or the network sets its own short bound, never the
   product's long default. A hanging run is never repeated in the hope that it passes (OR-06): the cause is
   investigated. The replay alone of a timed-out plant is not such a retry: it confirms a kill, and a replay that ends
   points at contention (a shared lock, the host's load) as the cause to investigate.
5. **No false kills.** A kill counts only when it comes from the mutation: a control run replays each killed, errored
   or timed-out mutant's own test process **without** the mutation; a test that is red there made a false kill, and
   the run fails naming them. (Environments that intercept file access for mutation can make tests fail for reasons
   unrelated to the code; the control run is what keeps such results from passing as kills.)
6. **Thresholds per risk class**, per file, recorded in 06: default MSI ≥ 80 % and covered MSI ≥ 90 %; crypto,
   licensing, tokens and money ≥ 90 % / 90 %. A per-path floors file raises them for named paths.
7. **Survivors:** killed with a better test, or — for a genuinely equivalent mutant (no observable difference) — a
   narrow ignore: one mutant, one line, the reason, approved by the lead and recorded in 05. **An equivalence claim
   needs a proof, not an argument** (why no input can tell the mutant from the original: the reachable values, the
   invariant that makes the branches agree), especially on arithmetic, positions and boundaries. Never a whole file,
   never
   a mutator switched off to make a number.
8. **Receipts.** A passing batch writes one receipt per file that pins exactly what decides that file's verdict: the
   file's hash, its changed lines against the run's base, the tests that ran against its mutants (and the test code
   they name), the mutation configuration as it applies to that file, the runtime version. Receipts are never deleted
   before a run ends: a pass replaces them, a judged failure removes them, anything else (a cap, a signal) leaves them.

## WHO
- **Builder:** none. **Reviewer:** none; it names the delicate changed functions and lines for the tester and flags
  any untargeted or builder run.
- **Tester:** the lane's **only** mutation runs (one per tester round, at most 3 per lane across bounces), each against
  the lane's base, leaving its receipts in the lane.
- **Integrator:** the train's gate re-uses every lane's receipts (the wrapper's receipt reuse) and re-runs only the files whose receipt
  no longer holds after the rebase (nothing, when the delicate code and its covering tests are unchanged).
- **Lead:** cap overrides with a reason; the milestone round.

## The full scope — milestone closure only
A milestone-mode call of the wrapper mutates every line under the source directories (base = the empty tree), with
the unit and feature suites as covering tests, the same caps per batch and bound per call. The round spans calls: its
receipts carry the commit, so a call skips what the round already judged (exit "not complete yet" until every file
has its receipt). It runs only on a clean tree and, when a remote runner is configured, only there. It is the
backstop for what a lane's receipt cannot pin (a fixture change, another file the tests go through).

## WHETHER and WHICH tool — per stack
A mutation tool is worth it when the stack has a maintained one that supports **changed-line scoping** (or file
scoping fine enough), a **per-test coverage map** (to pick covering tests), machine-readable results, and runs in
reasonable time. The stack plug-in names the tool and implements the wrapper (`plugin.env` and a
wrapper script of the project's own). Common choices (verify the latest stable at install):

| Ecosystem | Tools to consider |
|---|---|
| JavaScript / TypeScript | Stryker Mutator |
| JVM (Java, Kotlin) | PIT (pitest) |
| .NET | Stryker.NET |
| Python | mutmut, Cosmic Ray |
| Go | gremlins, go-mutesting |
| Rust | cargo-mutants |
| Ruby | mutant |
| C / C++ | Mull |
| Any other stack | the maintained tool the project picks at bootstrap (recorded in an ADR) |

**When no tool fits** (shell scripts, hooks, infrastructure, configuration, generated code, a stack without a usable
tool): the tester **plants faults by hand** — one per checked behaviour (invert a condition, drop a check, change a
boundary, remove a cleanup) — shows each one is caught by the suite, restores the tree (and proves it restored), and
lists the plants and their results in the report. A tool that exists but cannot scope to changed lines is wrapped to
scope by file and the cap; if even that is too slow, planted faults on the delicate functions are the honest fallback,
recorded as an ADR.
