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
4. **0 skipped mutants.** A mutant skipped because its tests ran too long is a re-run, never a pass.
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
