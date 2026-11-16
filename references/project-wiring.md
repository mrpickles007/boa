# Project wiring: the checklist

> What BOA does not ship as code ships as discipline: each item below is project work the agent does for its project
> at bootstrap (and again whenever the project changes), as a task of the plan under the full pipeline (task,
> review, test), following the reference the item names. Nothing on the list is pre-filled by BOA.

## Items

### CI (only with consent)

- **When:** only when the user said yes to CI in the forge setup (`references/forge.md`, decision 4); otherwise the
  item is closed as "declined" in the forge-setup decision record and the gate stays local and on the runners.
- **The task:** write the project's CI workflow or pipeline from the invariants of `references/forge.md#ci`: it
  runs the project's gate (never a second gate); triggers chosen with the user and targeted (manual by default);
  every action and image pinned by full commit SHA or digest, looked up online as the latest stable release when
  the task runs; least permissions; nothing that costs money without consent. The annotated examples there show
  the shape, never the values.
- **The minutes economy (`references/forge.md#ci-minutes-economy`, OR-71):** on a private repository, or any CI with
  metered minutes, the task also wires the minutes monitor of the project's forge (a periodic tooling task with a
  warning threshold and an alert to the user) after asking the user the monthly budget (HITL), and writes lean
  triggers: cheap Linux jobs on push/PR, expensive runners (macOS, Windows, GPU) only on manual dispatch or release,
  cancel-in-progress on PRs, path filters for docs-only changes, a job that decides which jobs a change needs, every
  job printing the minutes it used, a first-run measurement that disables the workflow when the budget is at risk,
  and no full-matrix re-run for a docs change.
- **Who and how to check:** the builder writes it, the reviewer checks every trigger against that list, and the lead
  runs the first monitor reading and compares it with the threshold; a CI file that starts an expensive runner on
  every push or PR, or a private-repository CI with no recorded budget, is a finding.
- **Done when:** the file is reviewed and merged through the pipeline, one manual run on the forge passed the same
  gate as the integrator's, the forge-setup decision record names the triggers, the pins with their lookup
  date, the expected cost and the monthly budget, and (private or metered) one monitor reading ran and was compared
  with the threshold.

### Config

- **When:** at install, before anything else: `boa install` writes the commented template to `.boa/config.env`
  when the project has none, installs nothing else and exits 1; again whenever a value changes.
- **The task:** fill in every value from what the agent knows about the machine, the runtime and the project, and
  ask the user what it cannot know or decide (each question with a recommendation). The template's comments give
  each key's rule; every REQUIRED key gets a value. Check the values the way a validator would: the slug's
  charset, the branch grammar (holds `<task>` and `<slug>`, never matches the main branch), the worktrees dir and
  the scratch root (absolute, at least two levels deep, never the project nor inside it), the label key, the
  interpreter (`<BOA_PYTHON> -I -c "import json"` runs). Then run `boa install` again.
- **Per-machine values:** `.boa/config.env` is versioned, so a value that holds on one machine only (the
  interpreter path `BOA_PYTHON`, the scratch root `BOA_SCRATCH_ROOT`) must not break another machine, a collaborator
  or CI. Keep what can be relative relative (`BOA_WT_DIR=../<slug>-wt`). On another machine, set the machine's own
  value in the environment under the same key: BOA's tools read the environment first, then the file. The guards
  read the committed file only, so the keys they read (the scratch root, the worktrees dir) hold values that are
  safe on every machine (a scratch root outside the temp and home dirs makes the guard use BOA's own one); the `boa`
  launcher falls back to a working `python3` on the PATH when the committed interpreter does not run, and the
  runtime wiring on each machine names that machine's interpreter. CI sets the same keys in its job environment.
- **Done when:** `boa install` ends with exit 0 and no "fill it in" message, and the choices the user made are in
  the decisions log.

### capabilities record

- **When:** at bootstrap, before the config; again when the machine or the runtime changes.
- **The task:** check what BOA and the project need on this machine with the platform's own commands: git 2.31+
  and Python 3.11+ (the `boa` launcher refuses with exit 3 and names what is missing), the forge CLI and its
  authentication when a forge is used, the CPUs, the memory, the load and the free disk the lane cap and the
  admission keys (`BOA_LANE_CAP`, `BOA_LANE_MEM_MB`, `BOA_ADMIT_MIN_MEM_MB`, `BOA_ADMIT_MAX_LOAD`) are computed
  from, the user's rights (root, sudo) and the tools and services the stack needs. What is missing is reported to
  the user with the version found and how to install it on this OS; the agent installs it only with consent and
  the rights. Nothing is installed or changed without consent. The agent also reports any memory of its runtime
  outside the bank (a built-in memory, a memory-like MCP server or plug-in): project memories go only into the
  memory bank through `memory_write.py`, and the agent never writes to or relies on that other memory.
- **Done when:** every prerequisite is present (or its absence is a decision of the user), the lane cap and the
  admission keys are set from the measured figures, and the facts are recorded in the capabilities record:
  `memory-bank/04-ARCHITECTURE.md` "Environment" (versioned; never under `.boa/`, which is git-ignored).

### light and heavy suites

- **When:** at bootstrap, always (the test-execution choice below is made there, runner or not); again whenever
  the stack gains a heavy command.
- **The task:** **test execution, decided once with the user (the single home of this rule).** At project start the
  agent proposes, and the user decides: where the suites run (on the development machine or on a remote runner),
  serial or parallel, and how many at once. The proposal rests on the **measured load** of the runner and of the
  local server (only the local one when there is no remote runner), read with the platform's own commands, never
  guessed. The decision is recorded in the capabilities record (`memory-bank/04-ARCHITECTURE.md` "Environment")
  and in the handbook, and every other document points here instead of restating it. During the work the
  decision is re-tuned by the rules that already exist, not by a new question: the suite-duration watch and the
  tooling task it opens when suites grow slow (`references/duration-control.md`), the runner monitoring at every
  train, load-based lane admission, and no synthetic host load. The user is asked again only when those rules say
  so: a real fork, a spend, or a runner change. An example default the agent may propose: parallel runs at low
  priority (for example at most 3 at once, each under `nice`); it never overrides the runner and heavy-run
  rules below. Whatever is chosen, suites that exercise the guard or have host side effects (destructive plants)
  run alone and first.
  Then make sure heavy work (the integration gate, whole suites, mutation runs, suites with services)
  never runs on the development machine when a runner exists, and that nobody loads a shared machine
  synthetically. Write the project's heavy command forms as protected-command rules of the guard (refused with
  the instruction to run them through the runner), covering the forms an agent produces by accident: the program
  itself, behind a wrapper (`env`, `nice`, `timeout`, `xargs`, ...), as `sh -c` text and inside a script the
  command runs; whole suites are heavy, the light ones the project names are not. CPU or I/O burners run only
  under `nice -n 19` with at most 2 workers; "works under load" is proven with an injected delay. Where the
  guard's rules cannot express a form, the agent writes a small hook of the project's own, tested with payloads.
- **Done when:** the test-execution decision is recorded in the environment record and the handbook, the rules (or
  the hook) are reviewed and tested with payloads for every form above, and the handbook names them.

### project protections

- **When:** at bootstrap, and whenever the project adds a protected path, a host it must not damage, a cleanup
  shape or a tool that must only run one way (typically the mutation tester: targeted at the changed lines, capped
  in time).
- **The task:** write the project's protections into the guard's protected-command rules (or a small hook of the
  project's own where a rule cannot express it, tested with payloads): the protected paths and commands of this
  project and host (services, packages, schedulers, firewalls, the forge's destructive commands, the databases of
  the deployed instance), the cleanup shapes the runtime's allowlist lets run without a prompt, and every wrapped
  tool: it runs only through its wrapper or the project's trusted runners (the gate, the runner), never by hand or
  from an agent's own script; a rule refuses the tool's program, its package-manager script and an interpreter
  running it, and names the wrapper in the reason. Paths that only name the tool (its cache, `which`) stay
  allowed. These rules are role-blind (the lead too) and never honour the lead's override.
- **Done when:** every rule is tested with payloads (for a wrapped tool: direct run, behind a wrapper, through a
  script refused; the wrapper allowed) and the handbook names the rules and the wrapper.

### git hooks

- **When:** at bootstrap, after the forge setup.
- **The task:** guarantee that nothing reaches the main branch except a reviewed, merged pull/merge request: no
  direct push, no force push, no deletion of main; an exceptional escape is explicit, logged with its reason and
  recorded in the progress log. Prefer server-side protection (branch protection or rulesets, protected branches)
  where the forge offers it (`references/forge.md`); where it does not, a client-side pre-push hook installed for
  every worktree (a hooks framework such as pre-commit or the project's own). Commit messages follow Conventional
  Commits (allowed types, a subject length limit, the required trailers): checked at commit time by an existing
  tool (commitlint, a pre-commit hook, or the forge's push rules). Every hook fails closed when its own parts are
  missing.
  **Memory lint at commit:** run `.boa/tools/memory_lint.py --staged` (the main checkout's copy, so a lane cannot
  weaken it) on every commit that touches the memory bank, and refuse the commit on a broken memory (unknown ids, orphan links,
  cycles, a block without an id); fail closed when the interpreter or the lint is missing. The same lint runs in
  every train's gate on the whole memory bank.
- **Done when:** a direct push to main and a malformed commit message are both refused in a test repository, the
  escape is logged, and the handbook names the mechanism; a commit with a broken memory link is refused in a test
  repository.

### secret scanning

- **When:** at bootstrap; the staged diff at every commit, the whole tree and the full history at close-out.
- **The task:** wire a maintained scanner (gitleaks, trufflehog or the forge's own scanning) so that a credential
  never lands: the lines a commit adds are scanned before the commit (refused on a finding), the whole tree and
  every ref's history are scanned at close-out, binary and UTF-16 content included. A finding prints its location
  and rule, never the secret. False positives are handled the scanner's way (an allow comment, a path allowlist
  read from git, never from the working tree); a catch-all allowlist is refused. A missing scanner refuses the
  commit (fail closed).
- **Done when:** a planted fake key is refused at commit and found in the history scan, and the close-out
  procedure names the scan.

### the project gate

- **When:** at bootstrap, with the stack plug-in; again whenever a step, the plug-in or the test runner changes.
- **The task:** the agent writes the project's ONE gate itself, in the project's own task runner or CI, with the
  checks it chooses and wires for its stack (tests, static analysis, linters, mutation on the changed lines). The
  gate MUST call BOA's kept checks: `.boa/tools/trace_check.py` (its `@covers-contract` relation: every contract
  clause has a running test), `.boa/tools/handbook_drift.py`, `.boa/tools/memory_lint.py`, and
  `.boa/tools/trace_check.py --close` at close, and `.boa/tools/plan_lanes.py --check` (the plan's lane block is
  consistent). A misalignment is a red gate, never a warning. The gate sets its own environment flag
  (`<BOA_ENV_PREFIX>GATE=1`) for the suites it runs: under it a skipped case is a failure; ad-hoc runs never set
  it. A project with a schema (a database, a message format) adds a schema and migration check step: the
  migrations apply cleanly from empty and from the last release, and the schema they produce matches the declared
  one. Modes: one step or the
  changed files for builders and testers; ONE pre-merge run per merge train on the stacked tip (on the runner when
  there is one); timings recorded ("suite timings and duration control"). Its self-test is discipline too ("a check
  that cannot fail is not a check"): plant one defect per gate step once and prove the gate catches it.
- **Done when:** the gate passes on the clean tree, every planted defect is caught, and the handbook and the
  integrator's contract name the commands.

### remote runners

- **When:** at bootstrap when the user wants heavy runs off the development machine (`BOA_RUNNER=on`), or when the
  duration review proposes one.
- **The task:** the remote test runner is always a Linux server, set up and used by discipline: BOA ships no runner
  code, and nothing in BOA's own tools assumes Linux (the skill keeps working on Windows, Linux and macOS). Adopt an
  existing way to run a lane's heavy command there: a self-hosted CI runner, or ssh plus the project's own scripts
  (written, reviewed and tested as plan tasks). It must guarantee:
  - **heavy runs off the development host:** it runs exactly what git would commit, streams the output, returns the
    exit status and brings back only the declared results; a pool of runners is chosen by free capacity and a
    runner that is down is skipped and reported; a heavy command never falls back to the development machine (no
    runner: stop and report to the lead);
  - **isolation:** an allowlist on the runner accepts only the project's heavy commands and refuses the rest; runs
    are isolated per lane (own directory, own labelled resources) and never touch another project on the server;
  - **cleanup:** every run removes what it created (the lane's directory, processes and labelled resources), also
    after a failure or an interrupted run;
  - **no secrets in logs:** the runner's address and credentials live in a machine-local file outside git, with
    least privilege; logs, reports and briefs never carry a secret;
  - **a clear refusal:** "runner not configured" and "runner not reachable" end with their own exit status, distinct
    from a failing command, recorded in the handbook; the agent contracts stop on it and report to the lead;
  - **the services the heavy suites need** (a database, a broker, a browser) are provisioned on the runner by a
    planned task, idempotently, isolated per lane and removed by the cleanup above;
  - **monitoring:** the runner's status (reachable, free capacity, disk) is read at every train against thresholds
    the project sets, and what a run left behind is cleaned then.
- **Done when:** one suite run gives the same output and exit status locally and on the runner, a command outside
  the allowlist is refused there, a run (also an interrupted one) leaves no residue on the runner, no secret shows in
  its logs, an unreachable runner returns its recorded exit status, a heavy suite's services start on the runner from
  the provisioning task, the train report carries the runner's status against its thresholds, and the procedures and
  the handbook name the command and its exit statuses.

### usage clock and throughput

- **When:** at bootstrap. Throughput: weekly or at every few trains, from the time records.
- **The task:** record, with the runtime's own facilities or a small project tool, how long each task takes: wall
  time from its first builder start to its `done` mark, the time per role and per phase (review rounds, the gate),
  running and stale runs; give every agent the UTC time (`date -u +%Y-%m-%dT%H:%M:%SZ`: the datetime of memory
  blocks), and which agent to resume per task and role; the tokens each agent run used (input, output, cache) where
  the runtime exposes them, and otherwise the record says "declared unavailable" for that runtime, never an
  estimate. Records never hold a prompt, a transcript or a secret (labels redacted). A project clock may read or extend the
  agent binding BOA keeps (`.boa/hooks/agent_binding.py`, `<BOA_STATE_DIR>/agent-bindings.jsonl`). A project that
  needs redacted journals or logs (the lane journal, the guard log) wires its own redactor.
  **Throughput review:** compute tasks done per day, agent time per role and its share, the waits (wall time minus agent
  time), the lanes active against the cap and the gate's median total against its budget, and turn them into
  proposals with the figure behind each (more or fewer lanes, a remote runner, a bigger runner, a speed-up task).
  Advisory: it never fails a gate.
- **Done when:** the train report shows the time per task and per role from the records, and the tokens per agent
  run (or "declared unavailable"), and the handbook names the tool; the lead's train report carries the figures and
  the proposals.

### measure commands

- **When:** at bootstrap; checked around heavy steps and at every train.
- **The task:** measure only this project's own paths (the repository, its worktrees, dependency dirs, build and
  test caches, logs, the project's own containers, images and volumes when provably its own) with `du`-style and
  the container engine's own commands, never another project's and never the whole machine; compare the total with
  `BOA_DISK_WARN_MB` and `BOA_DISK_HARD_MB` and raise an alert the lead reads at session start (a marker file, a
  notification through the project's channel). On a breach the project's own leftovers are cleaned first.
- **Done when:** the measurement runs, a lowered threshold raises the alert, and the lead reads it at session start
  and in the train report.

### deployed-instance objects

- **When:** at every lane merge, at milestone closure and at close-out.
- **The task:** list every leftover that is provably the project's (worktrees, branches local and remote, scratch
  dirs, the lane's labelled or prefixed containers, networks, volumes and images, deployed-instance objects, a
  running daemon) with git and the engine's own listing commands, read-only, and fail on anything not in the
  residue register (`trace_check.py` checks the register's rows): per lane only that lane's leftovers and rows;
  at closing, unregistered leftovers of done tasks fail; at close-out the register is empty and every leftover
  fails. A paused lane cannot remove its own containers or services (the pause guard knows no engine): it names them
  in its resume file and the lead removes them with these same commands.
- **Done when:** a planted leftover makes the check fail in each mode, and the integrator's contract names it.

### suite timings and duration control

- **When:** at bootstrap with the gate; reviewed at every train.
- **The task:** keep the gate's timings (total, each step, each suite) from the gate's own records or the CI's and
  test runner's duration reports, and judge them at every train: the total against `BOA_GATE_BUDGET_S`, each step
  against its budget and its trend, the critical-path suite of every parallel step, and a step dominated by one
  suite above `BOA_DOMINANCE_PCT` % even under budget. A step over budget, trending up or dominated becomes a
  speed-up task in the train report (measure first, keep identical coverage). Runs under unusual load are marked
  suspect.
- **Done when:** the train report carries the judgement and a planted slow suite produces the speed-up line.

### licence and dependency audit

- **When:** at bootstrap, as a step of the project gate; again whenever a dependency is added or upgraded, and at
  every release.
- **The task:** wire maintained tools of the stack (the package manager's own audit, a licence checker, an
  advisory or malware scanner such as the forge's dependency alerts) so that: every third-party dependency's
  licence is checked against an allowlist the user approves (a licence outside it, or an unknown one, fails and
  becomes a HITL question); every dependency, direct and transitive, is checked against the advisory and malware
  databases (a known vulnerability or malicious package fails, with its id and the fixed version); the lock file
  is the input, never the working tree's resolved guess. Stack freshness (the latest stable versions) stays the
  milestone rule of the procedures; shell scripts get the stack's own linter.
- **Done when:** the gate runs both checks, a planted dependency with a refused licence and one with a known
  advisory each turn it red, the allowlist and its approval are in the decisions log, and the handbook names the
  tools.

### clean-room check (optional)

- **When:** only for a project that rewrites an existing product it may not copy (refactor mode or an IP-sensitive
  project, as decided at bootstrap); otherwise the item is closed as "not applicable" in the decisions log.
- **The task:** wire a check in the project gate that compares what lands with the forbidden sources the
  clean-room procedure names (09 "Clean-room and provenance", `docs/clean-room.md`: the old code and its assets): long identical or near-identical passages,
  distinctive identifiers, comments and asset hashes are refused with their location; the forbidden sources are
  read only by the check and the spec-side roles, never by a build task; every pull/merge request carries the
  provenance line, and the check refuses one without it.
- **Done when:** a planted copied passage and a request without the provenance line each turn the gate red, and the
  procedures and the handbook name the check.

### permission log

- **When:** at bootstrap, when wiring the runtime.
- **The task:** record every permission request and denial of the runtime (its own log or a hook on its permission
  events), capped and redacted (the input withheld when it cannot be redacted), private to the user, so the lead
  can shape the cleanup allowlist and the work around what still prompts.
- **Done when:** a prompted command appears in the log and the lead's status or train review reads it.

### wire BOA into your runtime

- **When:** right after the install, and whenever the runtime changes.
- **The task:** register BOA's hooks (the inventory in `references/runtimes.md`: event, matcher, command), the
  agents of `.boa/agents/` with the configured model per tier, the commands of `.boa/commands/`, the instructions
  (ALL rules in AGENTS.md; a runtime that does not read it natively gets its own instruction file holding only an
  import of or pointer to AGENTS.md) and the runtime options (permissions, the cleanup
  allowlist, the prompt-cache TTL), merging into the project's own runtime files and recording what was wired so it
  can be undone (`references/runtimes.md`). Set the runtime facts BOA's code does not know from the runtime profile:
  `BOA_SCRATCH_ROOT` and `BOA_SCRATCH_GLOB` (its scratch layout) and `BOA_RUNTIME_CONFIG` (its own configuration
  names in the project, which the guard then keeps shell writes off). What the runtime cannot do is declared, never
  faked. The runtime's
  renderings of the agents and commands are re-generated in the same commit as their `.boa/` source and checked
  against it by the project (the handbook drift check knows no runtime).
- **Done when:** the status screen shows no "GUARD DOWN" line, the handbook drift check is clean, every runtime
  rendering matches its `.boa/` source, `BOA_RUNTIME_CONFIG` names the runtime's configuration files (or the runtime
  has none), and the wiring record lists every entry.

### model roster per runtime

- **When:** at bootstrap, and when the runtime's model list changes.
- **The task:** pick the runtime's frontier model (builder, reviewer, analyzer) and the model just below it
  (builder-mid, tester, integrator) from the runtime's current model list, verified then, confirm them with the
  user and set `BOA_MODEL_FRONTIER` and `BOA_MODEL_MID` (`references/runtimes.md`); BOA ships no default.
- **Done when:** the agents' frontmatter names the chosen models and the decision is recorded.

### stack plug-in

- **When:** at bootstrap, once the stack is chosen; again when the stack's tools change.
- **The task:** adapt `.boa/stack/` from the generic template into the project's plug-in: `plugin.env` (the test
  commands per kind of test file, the per-call cap, the heavy tests' image when the project has heavy tests), the
  targeted test runner's contract (explicit files, a case filter, a heavy switch), the mutation tool and its
  wrapper when the project has delicate code (`references/mutation-testing.md`; planted faults where no tool fits),
  the lint and static analysis steps the project gate runs, and `handbook-rows.md` naming every file of the plug-in.
- **Done when:** the targeted runner runs one test of each kind, the case filter is proven by a two-case probe (case
  A passes, case B always fails, the filter naming A runs only A and passes), the wrapper (if any) runs on a changed
  line, and the handbook's stack block equals the plug-in's rows.
