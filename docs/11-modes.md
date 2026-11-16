# 11 Modes

The mode is the first argument of `/build-on-autopilot`. Every mode ends its bootstrap with contracts and a plan; the
bootstrap tasks run through the normal pipeline. The references: [greenfield](../references/modes/greenfield.md),
[brownfield](../references/modes/brownfield.md), [refactor](../references/modes/refactor.md).

## Greenfield

Input: the idea, what to build: a file you name (any name or path), or, with no file, what you said in the conversation,
which the lead writes into `IDEA.md` in the project and you confirm. The lead reads it in full, lists every goal, constraint, user, external system and
open question, then writes the project brief, the blueprint (every feature with an id), the specifications and the
**contracts** (APIs, schemas, protocols and file formats, module interfaces, error models, limits), the architecture
and security files, and the implementation plan with spec-side tasks first. Builders never invent a contract: a gap
goes back to a spec task ([14 Contract-driven development](14-contract-driven-development.md)).

## Brownfield

Input: an existing repository; no idea file is needed, and any direction you give in the conversation (constraints,
priorities) is recorded in the memory or the plan. The bootstrap reconstructs what the code is before anyone changes it: an
inventory of every tracked file, a fan-out plan that gives every file to exactly one analyzer, analyzers reading their
slice line by line and reporting with `file:line` evidence (structure, data flow, persistence, dependencies, dead
code, security-relevant paths, the contracts the code honours and what third-party clients depend on), the lead's
consolidation into the memory bank (contracts marked "observed"), a coverage check that every file was read, and
**characterisation goldens** that pin today's behaviour for every contract a user or a third party depends on.
Behaviour is preserved unless a task authorises a change; a contract third parties rely on is never broken.

## Refactor

Input: an existing repository and the idea, the refactor's target: a file you name or the conversation (written into
`IDEA.md` and confirmed by you, as in greenfield). The brownfield bootstrap runs first; then the
target is expressed as contract changes (each contract kept, changed or removed; every change and removal a decision
record, the goldens of a changed behaviour re-recorded by that task only), and the plan keeps the goldens green at
every merge. Behaviour is preserved, not the legacy shape: duplication, dead code and accidental complexity are not
ported. An optional **clean-room** module covers refactoring code you may not copy (spec side and build side, an
allowed-sources list, a provenance line on every task, a copy check in the gate); it mitigates legal risk and is not
legal advice.

## Full specifications from any idea

However short the IDEA is, the agent derives all the specifications before building: requirements, contracts with
their clauses, edge cases and acceptance criteria. Every gap goes to you as a question with alternatives and a
recommendation, and the work goes on with what is not blocked (rule OR-70).

## New work on an existing project

Once BOA is added to a project that already exists (brownfield or refactor), every new feature and every later change
goes through the full flow: a plan row, contract clauses first, the pipeline, a merge train, memory and traceability.
Nothing is edited outside it because the code predates BOA; existing code a new feature touches gets its contract
clauses and goldens first (rule OR-69).

## Choosing the stack

When the IDEA or the repository does not fix the stack, the lead chooses it from the goals: the goals that constrain
it, two or three candidates, the latest stable release of each piece verified online at that moment (never from
memory), the testing story (a fast runner, targeted tests, static analysis, a mutation tool or planted faults), then a
decision record. You are asked only when the choice is a genuine fork with no objective winner. An existing project
keeps its stack unless the target says otherwise. The method and starting points:
[references/stack-choice.md](../references/stack-choice.md). The project stays on the latest stable stack: freshness
is checked at every milestone and at close-out (rule OR-46).

## Writing a stack plug-in

BOA is language-neutral: projects in any language; Python is only BOA's own runtime. Everything specific to the
project's language lives in its **stack plug-in**, which the agent writes at bootstrap (the project-wiring item "stack
plug-in"). BOA ships only the generic plug-in template, `stacks/generic/`, installed as `.boa/stack/`; from then on it
is project code:

- **`plugin.env`**: assignments only, sourced in POSIX sh by the stack's tools and the project's gate.
  - `TEST_COMMANDS`: how the project's tests run, one `<glob>=<command>` per line; `{}` stands for the test file and
    `{dir}` for its directory, written unquoted (the runner passes them to the command as separate arguments, never as
    text, so any file name works); the first matching glob wins; shell suites (`*.sh`, `*.bash`) always run with
    bash.
  - `TEST_RUNNER_MAX_FILES` (default 50): how many test files the runner takes per call; the project's gate calls it
    in chunks of that size.
  - `TEST_HEAVY_IMAGE`: the container image of the service the heavy tests need. BOA names none and has no default:
    the service and its image are the project's decision, recorded as a decision.
- **`test-runner.sh`**: the targeted test runner. It runs explicit test files only and refuses a directory, a glob, a
  missing file, an absolute path, a `..`, an unknown option and a file no glob maps (exit 64); exit 0 when every file
  passed, 1 when one failed. Its header states the contract a project's runner fulfils, which the agent completes
  when the project needs it: a **case filter** `--filter=<pattern>` (a restricted pattern passed to the test tool as
  one word, never through a shell), a **heavy switch** `--heavy` (refused while `TEST_HEAVY_IMAGE` is empty; it
  tells the test tool, through its environment, to run the heavy tests and which image to start), and the per-call cap.
- **`handbook-rows.md`**: the plug-in's rows of the agent handbook, naming every file of the plug-in; the handbook's
  stack block must equal them (the drift check compares them).

The agent also wires, for the project: the mutation tool and its wrapper where the project has delicate code (changed
lines only, covering tests only, a time cap, receipts the train reuses; planted faults where no tool fits:
[references/mutation-testing.md](../references/mutation-testing.md)), the lint and static analysis steps, and the
project gate that runs them. The plug-in is done when the targeted runner runs one test of each kind, the wrapper (if
any) runs on a changed line, and the handbook's stack block equals the plug-in's rows. There is no command that
generates a plug-in: the agent adapts the template, under review and tests like any task.
