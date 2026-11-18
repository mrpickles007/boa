# 08-OWNER-RULES.md — every binding rule of {{BOA_PROJECT_NAME}}

> **Binding** (AGENTS.md §3). Read at every session start, by the lead and by every sub-agent. This file is the
> complete **index** of the owner's rules: the rules pool adopted at install (OR-01…OR-74, proven in practice and
> worded for any project) plus the owner's own rules, added during the project.
>
> **How a new rule gets here** (09 §16): the owner says it in chat → the lead writes it at once into
> `{{BOA_LEAD_DIR}}/owner-rules-pending.md` (date, the owner's words verbatim, the rule in
> {{BOA_DOC_LANGUAGE}}, roles, where it will be enforced) → the next
> merge train's `docs(memory)` commit folds it here with the next free OR-ID and updates the agent contracts, 09 and
> the handbook it touches. The repository is never more than one train behind.
> Append-and-refine: never delete an entry; mark it superseded with the date and a pointer to what replaces it.
> How to do the work in practice: `09-OPERATING-PROCEDURES.md`.
>
> **Languages** (OR-65, 09 §31): product language {{BOA_DOC_LANGUAGE}} (code, comments, docs, commits); user
> language {{BOA_REPLY_LANGUAGE}} (conversation, memory content, free text). Recorded at bootstrap; the product language changes only
> through `boa language set`.

Roles: **lead** (the orchestrating session), **builder** (and builder-mid), **reviewer**, **tester**, **integrator**,
**analyzer**; **all** = every one of them.

## Coverage — where each owner rule came from
The tester of any change to this file re-checks this table against the sources (the pending file, the runtime's
memory).

| Source | Rule(s) |
|---|---|
| BOA rules pool, adopted at install ({{BOA_INSTALL_DATE}}) | OR-01 … OR-74 |

<!-- rules-pool:begin -->
## Process rules (how the work is done)

### OR-01 — Reviews run only when a change touches executable things
- Rule: a review round runs only for a change to code, tests, scripts, configuration or build. A change or fix that
  touches only docs, the memory bank or agent-definition prose goes builder → tester (completeness check) →
  integrator. Cut waste, never quality.
- Why: review rounds on prose cost as much as rounds on code and catch almost nothing the tester's completeness
  check and the gate's doc-pinning suites do not.
- How to apply: the builder says `docs-only fix, no review round` + the files; the lead routes the lane; a change
  that mixes code and docs is reviewed for its code part; the gate still runs the suites that pin doc text.
- Applies to: all (the lead decides the route).
- Enforced: AGENTS.md §6, the builder and reviewer contracts, 09 §5.

### OR-02 — Everything targeted: delta re-reviews, targeted mutation
- Rule: a re-review covers only the changed lines and what they touch (re-attacked) plus each prior finding.
  Mutation runs only on the delicate lines the task changed (OR-29). The full scope runs only at milestone closure.
- Why: full re-reviews and full mutation rounds per task multiply cost without finding more; the delta is where new
  bugs are.
- How to apply: reviewer briefs name the delta range (`<old sha>..<new sha>`) and the prior findings; the tester's
  mutation run is scoped by the wrapper.
- Applies to: reviewer, tester, integrator.
- Enforced: AGENTS.md §6, the reviewer, tester and integrator contracts.

### OR-03 — Builders run only the tests for what they changed
- Rule: a builder runs the named tests of the code it changed, the suites that read or pin a file it changed, and
  static analysis/lint on the changed paths. Never the full battery, never mutation; the full gate
  runs once, at integration.
- Why: every role running every suite turns a 20-minute lane into a two-hour one and saturates the host.
- How to apply: a suite "touches" a change only if it reads or pins a changed file (check with grep, do not guess);
  the stack's targeted test runner takes explicit test files only.
- Applies to: builder (and every agent that runs tests).
- Enforced: AGENTS.md §6, the builder contract, every brief (09 §4).

### OR-04 — Integration: memory commit first, one gate, merge trains
- Rule: the integrator commits the `docs(memory)` update first, then runs ONE gate on that exact final tree; two or
  more ready lanes travel together as a merge train (stack, one gate, merge in order, bisect on red).
- Why: suites pin memory-bank text, so a memory edit after the gate can turn the main branch red; one gate per lane
  wastes the most expensive step of the pipeline.
- How to apply: integrator procedure and 09 §7.
- Applies to: integrator, lead.
- Enforced: AGENTS.md §6, the integrator contract, 09 §7.

### OR-05 — No synthetic host load
- Rule: never create host-wide synthetic CPU load. Prove "works under load" with a deterministic injected delay (an
  environment hook in the test) or at most 2 burners under `nice -n 19`.
- Why: a builder once spawned 17 busy-loop burners for a "runs under load" check; the host load reached 31 and
  starved every other lane and an integration gate.
- How to apply: when a plan row says "under load", design the delay seam first.
- Applies to: all (builder and tester above all).
- Enforced: every brief (09 §4), the builder and tester contracts. The guard cannot see it: a discipline rule.

### OR-06 — Loop guard: stop at 3 attempts, ask, recommend a final targeted 4th
- Rule: the same finding or failure surviving 3 builder attempts stops the lane; the lead asks the owner. When the
  reviewer's fixes are concrete and small, the recommended option is a final targeted 4th attempt with the exact
  fixes and a closing criterion; anything left after it becomes a documented residual risk. One heuristic (a
  detector, a classifier, a parser rule) that bounces with a different finding each round counts as the same
  failure: after 3 rounds on it the lead raises a loop note, the lane fixes it structurally (narrow the heuristic's
  scope, e.g. by file type or input kind) and every further tuning is relocated to a named task. A lane that still
  gets blocking findings at review round 6 is re-planned by the lead before another round.
- Why: thrashing burns budget and context; the owner prefers one last precise attempt to an open-ended loop. A
  heuristic lane once looped 7 rounds because every finding was new, so the same-finding guard never fired.
- How to apply: blocker in 05 and the registry; the lead's question carries options and a recommendation (OR-12);
  the reviewer of a heuristic keeps one cumulative probe file (true cases and look-alikes) and runs it every round.
- Applies to: lead (asks, re-plans), builder (4th attempt, structural fix), reviewer (closing criterion, probe file).
- Enforced: AGENTS.md §6 loop guard, 09 §6.

### OR-07 — Never reinvent the wheel: built-in first, then extend, then from scratch
- Rule: when an existing library or tool does the job and keeping it updated costs little against the benefit,
  adopt it. For every need: (1) use the built-in feature of the framework, library or tool already in use; (2)
  extend it (plugin, configuration, subclass, custom rule) or adopt a maintained library or tool that does it;
  (3) write from scratch only for a proven gap, stated in the PR.
- Why: reinvented helpers are bugs the library already fixed, and code nobody else maintains. A hand-written
  detector once took several review rounds that a maintained tool would have avoided.
- How to apply: the builder names the built-in or library it used (latest stable version and licence checked now),
  or the gap it proved; a new dependency with a real upkeep cost is an ADR; the reviewer flags reinvention as a
  KISS/YAGNI finding. The same holds for the project's tooling (OR-64).
- Applies to: builder, reviewer, lead (tooling too).
- Enforced: the builder and reviewer contracts, the project-wiring tasks.

### OR-08 — Disk is the lead's job
- Rule: the lead measures the project's whole footprint (repository, worktrees, caches, the project's own
  containers, images and volumes), keeps lanes lean, acts on thresholds and trend, and never counts or prunes what
  is not provably the project's.
- Why: worktrees, dependency copies and mutation caches grow fast and silently; a full disk stops every lane.
- How to apply: the project's disk measurement (project-wiring "measure commands") at session start and resume,
  stopped at a pause; snapshot and alert read around heavy steps and at every train; thresholds `{{BOA_DISK_WARN_MB}}` MB (warning) and
  `{{BOA_DISK_HARD_MB}}` MB (ceiling) in the config; clean the project's own leftovers first, report trend + action.
- Applies to: lead (agents keep their own footprint small).
- Enforced: AGENTS.md §10, 09 §10, the project's measurement (project-wiring "measure commands": its alert marker).

### OR-09 — Zero residue, per task and at the end
- Rule: every task ends with no lane-labelled or lane-named containers, networks, volumes or images, no worktree,
  no local or remote branch, no scratch. Anything kept on purpose is in the residue register (04) with its owner
  task and removal step. The final close-out reports zero.
- Why: leftovers accumulate into gigabytes and into "is this ours?" doubts that block cleanup later.
- How to apply: the project's residue check (project-wiring "deployed-instance objects") must pass for the lane
  before it is DONE; in closing mode at milestone closure; in final mode at project close.
- Applies to: all (the integrator verifies per lane).
- Enforced: AGENTS.md §4 "Disk hygiene", the integrator contract, the project's residue check.

### OR-10 — Never touch other projects or shared services
- Rule: delete freely only inside the project's own paths (repository, worktrees dir, own scratch). In shared places
  (`/tmp`, container engine, ports, services) delete only with proof it is ours (our name prefix
  `{{BOA_NAME_PREFIX}}`, our label `{{BOA_LABEL_KEY}}`, creation by a command we ran); if unsure, leave it and report.
  Sub-agents never even name another project's path (reads included); nobody runs git write verbs on another
  project's repository.
- Why: a development host is usually shared; one wrong prune or `rm` destroys someone else's work.
- How to apply: throwaway resources use `--rm`, a `{{BOA_NAME_PREFIX}}<task>-` name and the lane label.
- Applies to: all.
- Enforced: AGENTS.md §9, the guard hook (`.boa/hooks/guard_destructive.py`), 09 §4, §11, §17.

### OR-11 — No blocking cleanup prompts; the guard is the safety net
- Rule: agents clean up only with the allowlisted shapes (literal absolute paths under the scratch root or the
  worktrees dir, one deletion per command, no `cd && rm`, no variable paths, no globs outside those roots; worktree
  remove/prune, lane branch deletion, lane container/network/volume removal, the project's residue check). Anything else
  prompts on purpose. The pre-tool guard denies destructive commands on things not provably ours (non-blocking:
  the agent reads the reason and adapts).
- Why: in an autonomous run, a permission prompt nobody answers stalls the lane for hours.
- How to apply: write each run into a fresh `mktemp -d` dir under your own scratch subdir and remove the whole
  subdir once, at the end, with one literal `rm -rf /abs/path`.
- Applies to: all.
- Enforced: the runtime's permission settings (allowlist, deny rules), the permission log, the guard, 09 §4 and §11.

### OR-12 — Ask the owner only for owner decisions, with options and a recommendation; unknown → ask
- Rule: owner decisions (product, business, money, legal, brand, irreversible actions outside the repository,
  shared-environment changes, the loop guard) are asked with 2–4 self-contained options, the recommended one first
  and marked "(Recommended)". Technical forks are the lead's: decide by the standards (KISS/YAGNI/DRY, first
  principles), record an ADR, tell the owner briefly afterwards. Wherever an agent cannot know or decide (a
  capability of its runtime, a project choice, an owner decision), it never guesses: it stops that item, asks with
  alternatives and a recommendation, and keeps working on everything the question does not block. Sub-agents never
  ask the owner: they report the question to the lead, who decides it or asks the owner.
- Why: technical questions waste the owner's time and stall the loop; unasked owner decisions and guessed unknowns
  produce work that is thrown away.
- How to apply: record the question and the recommendation in active-context "Open HITL"; one question at a time;
  keep working on everything it does not block.
- Applies to: lead (agents escalate to the lead).
- Enforced: AGENTS.md §4bis, 09 §8, every agent contract.

### OR-13 — Third-party contracts never break
- Rule: compatibility with third parties (public APIs, client apps, file and wire formats, integrations listed in
  04 "Third-party contracts") must never break. Clean standards apply only where no third party has a contract.
  Security fixes may change only behaviour no legitimate client relies on, never the success-path contract.
- Why: a "cleaner" API that breaks deployed clients is a regression for every user of the product.
- How to apply: the contract list lives in 04; the reviewer attacks every change touching a listed contract; a
  compatibility test (goldens) pins each one.
- Applies to: all.
- Enforced: 04, 07, the reviewer contract.

### OR-14 — Who the owner is and how to work with them
- Rule: the owner owns architecture and high-level design and the product decisions; replies to the owner are in
  {{BOA_REPLY_LANGUAGE}}, code and docs in {{BOA_DOC_LANGUAGE}}. Full autonomy on routine and technical work; after
  any interruption resume at once (OR-17); never drop a requirement or a feature silently.
- Why: the owner must be able to trust the work without re-checking it and without repeating requirements.
- How to apply: the owner's own words go into the plan and 08 verbatim; a feature cut is an owner decision (OR-12).
- Applies to: lead (all: never drop a feature silently).
- Enforced: AGENTS.md §1, §4bis, 09 §9.

### OR-15 — "Where are we" = the task count, in one line
- Rule: when the owner asks for status, the first line is DONE on the main branch / total plan tasks (%), the
  work-weighted %, and how many lanes are tested and waiting to merge. Lane detail only if asked.
- Why: the owner wants one number they can compare day to day, not a wall of lane states.
- How to apply: `python3 -I .boa/tools/plan_lanes.py` (progress table) or the last line of
  `.boa/bin/lead-status.sh`.
- Applies to: lead.
- Enforced: 09 §9.

### OR-16 — The sub-agent lifecycle: same task and role → the same agent; new work → a new agent
- Rule: every spawned agent's id is recorded per task and role (task, role, agent id, model, started, state: the
  project's clock, project-wiring "usage clock and throughput", or the lead's registry, the one home of agent ids). For every later round of the
  same task and role (delta fixes after a review, delta re-reviews,
  re-tests, tester confirmations) the lead RESUMES that same agent by its id (a message to it, its context intact).
  A new task or a genuinely new piece of work gets a NEW agent. A train's integrator is resumed for the same train
  (re-stack, re-gate) and new for a new train. When the agent or the session is lost, a new agent of the same role
  is briefed from the lane's `.lane-resume/<role>.md`, the newest journal entry and the lead's notes since. Resuming
  holds while the agent's context is moderate and the next round follows soon; when its context has grown large,
  rounds have piled up or the cache has surely expired, a fresh agent of the same role is briefed instead (09 §5.3
  says when).
- Why: a resumed agent reuses its context and prompt cache (rounds cost far less) and keeps its knowledge of the lane
  (the reviewer remembers its own findings, the builder its design); a fresh agent per round pays the whole context
  again and loses what the lane taught it, until the context outgrows what a re-brief costs (09 §5.3).
- How to apply: the agents registry (the project's clock, project-wiring "usage clock and throughput") names the
  agent to resume; resume it the way the
  runtime allows (verified at every wiring, OR-63, and recorded in the capabilities record; the runtime profiles are in the BOA
  package's `references/runtimes.md`) and, where it cannot be resumed, brief a new agent from the resume file.
- Applies to: lead.
- Enforced: 09 §1, §3 and §5, the lead registry, AGENTS.md §6.

### OR-17 — After an interruption, harvest finished agents first
- Rule: on resuming after an interrupted turn, first find which background agents finished (the lane journal
  `{{BOA_LEAD_DIR}}/lanes/<task>.md`), advance each lane, and tell the owner briefly what finished.
- Why: agents keep working while the lead is stalled; their results sit unread otherwise.
- How to apply: `lead-status.sh` shows each lane's newest journal verdict and the suggested next step.
- Applies to: lead.
- Enforced: 09 §1 and §13, the sub-agent stop journal hook.

### OR-18 — Hand over machine-local state before merging a lane that holds it
- Rule: before merging a lane whose worktree holds gitignored state that must survive (a running instance's
  secrets, credentials), copy it to the main checkout and verify it; merge without deleting the branch through the
  forge and remove the worktree by hand after the handover.
- Why: a forge CLI's "delete branch" on merge can remove the linked worktree, and with it secrets nobody else had.
- How to apply: checksum the main checkout's copies before and after the merge; they must be unchanged.
- Applies to: integrator, lead.
- Enforced: the integrator contract (step 6), 09 §7.

### OR-19 — Live lane state lives in the lead dir, never in a session
- Rule: the lead's live lane registry is `{{BOA_LEAD_DIR}}/lanes.md` (machine-local, git-excluded), append-only, one
  timestamped line per stage change. The session's scratch directory dies with the session and holds nothing durable.
  Durable rules never go in the lead dir: they live in AGENTS.md and `memory-bank/`.
- Why: a new lead session (or another agent) must know where every lane stands without the old session.
- How to apply: 09 §2.
- Applies to: lead (agents report; the journal hook records their final reports).
- Enforced: 09 §2, `lead-status.sh`.

### OR-20 — Duration control, done properly
- Rule: every gate run records the gate total, each step's wall time and every suite's time in a ledger. At every
  merge train and milestone closure the integrator reports, against budgets and trend: the gate total, each step's
  wall time, and the **critical-path suite of each parallel step** (the longest, which bounds the step) with its
  share of the step. The lead asks "can it be optimised?" for each step and opens a speed-up task at once when a
  step or a suite is over budget, trending up, **or a step is dominated by one suite above
  {{BOA_DOMINANCE_PCT}} % even under budget**. Speed-up tasks measure first, keep identical coverage (the same
  recorded call set, planted faults still caught) and record before/after timings. When the clock and the timings
  show the work is slow, the lead proposes capacity changes (runner size, worker counts, parallel lanes) — to the
  owner when they cost money. Speed never trades away coverage.
- Why: suites grow a few seconds per task; unwatched, the gate ends a project at an hour per train. Under-budget
  growth that is only "watched" is how a single suite comes to own a whole parallel step.
- How to apply: 09 §15 and the integrator's "Timing watch"; the project's timing check and throughput review
  (project-wiring "suite timings and duration control", "usage clock and throughput").
- Applies to: lead (opens tasks, proposes capacity), integrator (reports at every train), builder and tester of
  speed-up tasks.
- Enforced: the project's timing records and check, its throughput review, 09 §15, the
  integrator and tester contracts.

### OR-21 — Everything stays current; any agent can take over at any moment
- Rule: the rules and the workflow live in the repository (08, 09, AGENTS.md, the agent definitions, the
  handbook); live state is recorded automatically and continuously: the sub-agent stop hook journals every agent's
  final report, the lead appends every stage change to the registry, `lead-status.sh` shows everything on one screen
  and is injected at every session start, pending owner rules wait at most one train, active-context is refreshed at
  every train, RESUME.md is a pointer file that holds no state. On a pause every agent writes its resume file.
- Why: sessions die (limits, compaction, crashes); a project that only one session understands dies with it.
- How to apply: 09 §1, §2, §13, §16.
- Applies to: all (lead and integrator above all).
- Enforced: the journal and status hooks, 09, the integrator contract.

### OR-22 — The guard and permission logs are reviewed at every train
- Rule: at every merge train the lead reads the guard denials and the permission requests since the last check,
  classifies each denial as a real near-miss or a false positive, fixes false positives in the guard with a test
  case (a code change: reviewed and tested), and notes the result in the registry.
- Why: an unreviewed guard either blocks real work silently or lets a near-miss repeat.
- How to apply: `lead-status.sh` counts the new denials since its bookmark.
- Applies to: lead.
- Enforced: 09 §11.

### OR-23 — The guard is a best-effort net; product before tooling
- Rule: where an OS sandbox would block autonomous operation, there is none and the guard hooks are the only
  layer: a best-effort net, improved only for common-shape bypasses or false positives that hit real lanes, with
  the rest documented as known limits. When filling lanes, product tasks come first; a tooling task runs when it
  unblocks product work, when it measurably speeds up product work (for example a gate or a suite made faster, or a
  runner wired), or when it is planned like a product task; otherwise product tasks fill the lanes first.
- Why: unbounded guard work and tooling rounds eat the budget meant for the product.
- How to apply: 09 §3 and §11; known limits listed in 09 §11 and the handbook §7.
- Applies to: lead, all.
- Enforced: 09 §3 and §11.

### OR-24 — Guard and destructive-path work is tested only on payloads or in a throwaway container
- Rule: guard and destructive-path work is tested only by feeding JSON payloads to the guard, or inside a throwaway
  container or namespace, never by running the command on the host. `/dev/*` is never a write, `ln` or `mv` target.
- Why: a builder writing guard tests once ran `ln -sf /etc /dev/null` on the host; `/dev/null` pointed at `/etc` for
  a minute and a concurrent gate failed.
- How to apply: the guard's suite feeds payloads only; destructive scripts are exercised in containers.
- Applies to: all (builders and testers of tooling above all).
- Enforced: the guard (denies `/dev` targets), its suite, 09 §4 and §11, the builder and tester contracts.

### OR-25 — Forget nothing: the plan is the single source of work
- Rule: every to-do (an agent report's Leftovers, relocated review findings, integrator and lead notes, the owner's
  chat, owner-only actions as HITL rows, temporary measures, flakes ruled non-regressions, pending deployment steps,
  spec questions) becomes a plan row or a dated note on the row that owns it. There is no parallel list:
  `{{BOA_LEAD_DIR}}/open-items.md` is only the transit queue of captured to-dos not yet placed, and the next train's
  fold empties it into the plan. Capture never multiplies tasks; each item is resolved in this order, a new task
  only last: (1) no action, with a reason (observation, nice-to-have, speculative); (2) a duplicate, merged into the
  existing row; (3) a few-line fix in a running lane's module, absorbed (OR-28); (4) covered by an open task, a
  dated note on its row; (5) small unowned items, one open batch task per area ("follow-ups: <area>"); (6) real,
  sizeable, unowned work, a new task. Agents never create tasks: they report a Leftovers line (or a `bug` memory)
  and the lead places it. When new rows outpace DONE rows for 3 trains, the lead consolidates before starting new
  lanes. Milestone closure = its rows DONE; close-out = the whole plan DONE and the queue empty.
- Why: deferred items are the ones lost between sessions; a second list drifts from the plan; capture without a
  resolution order multiplies tasks.
- How to apply: every report ends with `Leftovers:` (or `none`); the lead copies each line into the queue at once
  (one `- [ ]` line with its date and owner); `lead-status.sh` ages queue lines and warns; the train fold places them.
- Applies to: lead (capture, placement), integrator (fold), all (Leftovers).
- Enforced: every agent contract (Leftovers), the queue, `lead-status.sh`, `trace_check.py` (close mode: zero open
  lines), 09 §14 and §16.

### OR-26 — One always-current agent handbook and file map, linked from AGENTS.md
- Rule: `AGENTS.md` links the agent handbook `docs/agent-handbook.md`: where every piece of information lives and
  every tool (what, when, how, who). The handbook's file map lists EVERY file of the discipline in the project, in
  any format (documents, JSON/JSONL ledgers and receipts, config, templates, state and log files the agents read,
  tools and hooks), each with what it is for, when to read it, and when and by whom it is updated. Every agent reads
  it at start. Any change that adds, changes, renames or removes a tool, script, suite, agent, hook, command, path,
  discipline file or procedure updates the handbook in the same commit; a drift check fails when a tool or a file is
  missing from it. Every discipline file stays plain readable text, within a readable size (split or rotate it).
  The duty is in every agent's contract.
- Why: an agent that does not know a tool or a file exists reinvents it, works around it or forgets it.
- How to apply: builder updates; reviewer flags a missing update (major, blocks); tester runs the drift check;
  integrator refuses undocumented tool changes and updates the handbook in the `docs(memory)` fold; analyzer reports
  gaps; lead keeps the lead-dir and deployment sections current and reviews the handbook as a whole at each
  milestone closure.
- Applies to: all.
- Enforced: the handbook drift check (`python3 -I .boa/tools/handbook_drift.py`), every agent contract.

### OR-27 — The model and effort roster is an owner setting; trailers name the real model
- Rule: each role's model and effort are set in its agent frontmatter and in AGENTS.md §6: builder and reviewer on
  the frontier model ({{BOA_MODEL_FRONTIER}}), effort high; builder-mid, tester and integrator on the model just
  below ({{BOA_MODEL_MID}}), effort high; analyzer like the builder. Only the owner changes the roster. Commit
  trailers name the model the agent really ran on.
- Why: the frontier model finds the subtle bugs that cost the most later; the cheaper model is enough where the
  work is mechanical, and the weekly budget goes further.
- How to apply: the lead never edits the frontmatter on its own initiative; a temporary switch follows OR-33.
- Applies to: lead (spawns the agents), all (trailers).
- Enforced: the agent frontmatter, AGENTS.md §6, the handbook §3.3.

### OR-28 — Tiny fixes in a running lane's own module are absorbed by that lane
- Rule: a fix of a few lines in the same files or module a running lane already touches is done by that lane (same
  builder, same review round, listed in the PR) instead of becoming a new task; anything in another module, or real
  work, stays a separate task.
- Why: tiny tasks cost a full pipeline round each; widening a lane into other modules makes lanes drift and collide.
- How to apply: the builder reports out-of-module follow-ups instead of widening its diff; the lead routes them.
- Applies to: lead, builder.
- Enforced: the lead brief (`{{BOA_LEAD_DIR}}/brief-common.md`), the lead's routing.

### OR-29 — Mutation testing is targeted: changed lines, covering tests, one wrapper
- Rule: mutation testing runs only on delicate code (09 §24: security/authz,
  crypto/licensing/tokens, money, data access, migrations, concurrency, anything where a silent wrong result is
  costly), mutates **only the lines the task changed**, runs **only the tests that cover them**, and goes through
  **one wrapper** around the project's mutation library (chosen for the stack at bootstrap: latest stable version
  and licence verified, recorded in an ADR) with a wall-clock cap per batch, a total bound per call and receipts;
  0 skipped mutants; thresholds per risk class (default ≥ 80 % MSI and ≥ 90 % covered MSI, ≥ 90 % on crypto,
  licensing, tokens and money);
  survivors are killed by a better test or justified as equivalent with a narrow, recorded ignore the lead approves.
  A run expected to take more than about 15 minutes has the wrong scope. The full scope runs only at milestone
  closure, on the remote runner when one is configured. Where no mutation library fits the code (shell,
  infrastructure, configuration), planted faults prove the suites catch errors (OR-55). A project with no delicate
  code needs no mutation library; whether it has any is asked at bootstrap when unclear (OR-12).
- Why: an untargeted run once took over an hour inside one lane; more time went into testing than into building.
- How to apply: the tester's runs are the lane's only ones (one per tester round, at most 3 per lane across bounces; OR-30, OR-53); the integrator's train run reuses its receipts and
  re-runs only what the rebase changed. The project wires the wrapper and a refusal of the bare tool (OR-64).
- Applies to: tester, integrator, reviewer (names the changed delicate lines), lead (briefs, cap overrides).
- Enforced: the tester, integrator and reviewer contracts, the project's mutation wrapper, 09 §24 (the BOA
  package's `references/mutation-testing.md` explains it).

### OR-30 — Strict stage roles
- Rule: the builder builds: code and the task's own tests, run quick and targeted, plus static analysis/lint on the
  changed paths; no mutation, no suite batteries. The reviewer reviews and runs only what proves or disproves a
  finding. The tester tests: acceptance map, planted faults, the touched suites and the lane's only mutation runs
  (one per tester round, at most 3 per lane across bounces);
  the train reuses the tester's receipts.
- Why: every role re-running every check multiplied the rounds without catching more.
- How to apply: each contract's "Owner rules" section; every brief repeats the role's limits.
- Applies to: builder, reviewer, tester, integrator, lead.
- Enforced: the four contracts, AGENTS.md §6, 09 §5.

### OR-31 — Merge trains carry 3–4 tested lanes per gate, ordered by independence
- Rule: the lead holds a green lane until 3 are green or the oldest green lane has waited 60 minutes; a
  critical-path lane or a fix for a red main branch may go alone, or at the bottom of the next train. One gate per
  train on the stacked tip, reusing the testers' receipts, still merged one PR at a time pinned to the full head SHA.
  Order the stack by independence: independent, low-risk lanes first, a riskier lane last; never stack independent
  lanes on top of a riskier one. On red: bisect, bounce only the breaking lane, re-stack and re-gate; a failure
  caused by main itself is a red-main fix task, not a lane bounce. Builders grep main for callers of every signature
  they change; the integrator refreshes a lane's dependencies after a lockfile change before gating.
- Why: the gate is the most expensive step; one gate for four lanes costs a quarter per lane. A lane can pass alone
  and break in combination, which only a gate on the stack catches. Independent lanes stacked on a failing risky
  one each paid an extra gate cycle.
- How to apply: 09 §7, `references/merge-trains.md` of the BOA package.
- Applies to: lead, integrator.
- Enforced: 09 §7, the integrator contract, AGENTS.md §6.

### OR-32 — With a remote test runner, heavy runs never execute locally
- Rule: when a remote runner is configured (`BOA_RUNNER=on`), heavy runs (gate steps that run tests, mutation, whole
  test suites, container and database suites) run only there, through the project's runner command
  (project-wiring "remote runners"). With the runner on, its command not configured on this machine or not reachable
  means STOP and report to the lead, never a local fallback; with the runner off, heavy runs stay local. Locally: the light doc and lint suites, static reads, and targeted tests on explicitly named files.
  Without a runner, heavy runs stay local, with the parallelism the project's test-execution decision sets
  (project-wiring "light and heavy suites").
- Why: heavy runs on a shared development host starve every lane and the other projects on it.
- How to apply: protected-command rules refuse the heavy forms locally when the runner is on (project-wiring
  "light and heavy suites").
- Applies to: all.
- Enforced: the project's heavy-run rules, its runner command, every contract, 09 §7 and §18.

### OR-33 — Rate-limit fallback only after an actual stop
- Rule: an agent moves to another model only when it has actually stopped on a rate limit (the runtime's limit
  error), never when it is merely close to it. The lead then continues that role on the next model: a new agent of
  the same role, briefed from the lane's `.lane-resume/<role>.md` and the stopped agent's last state. New spawns use
  the fallback until the owner says the limit has reset.
- Why: switching early wastes the better model's budget; switching late loses work mid-step.
- How to apply: the stop is the signal; no hook. Trailers name the model really used (OR-27).
- Applies to: lead, builder, reviewer.
- Enforced: the builder and reviewer contracts, the lead's procedure (09 §5).

### OR-34 — Model routing: two builder tiers; builders design from first principles
- Rule: the lead runs SIMPLE, low-risk build work on `builder-mid` (docs/comment-only fixes, tiny bounces such as a
  rename, a one-line fix or test data, spec-side docs tasks, mechanical follow-ups) and everything touching a
  delicate path (concurrency/locks, security/authz, crypto, privileged or remote execution, firewall, money,
  third-party contracts, or non-trivial new code) on `builder`. **When in doubt: `builder`.** `builder-mid` stops and
  hands back when the work turns out delicate. The same reasoning picks every role's model: judgement-heavy roles
  (builder, reviewer, analyzer) on the frontier model, procedure-heavy roles (tester, integrator) on the model
  below. Every builder designs from first principles with recursive reasoning (break the problem down while
  designing, check the pieces compose back into the requirement) and balances KISS/YAGNI/DRY; no extra self-review
  loop after the build: the reviewer reviews.
- Why: the frontier model costs several times more of the weekly budget; spending it on renames is waste, saving it
  on a lock or an auth check is a false economy.
- How to apply: the lead names the agent in the brief and the registry line; the builder contracts carry the
  "Build discipline" section.
- Applies to: lead, builder, builder-mid.
- Enforced: the builder and builder-mid contracts, AGENTS.md §6 roster, the handbook §3.3.

### OR-35 — Metalearning: every report ends with a metacognitive trace
- Rule: every sub-agent report (and the lead's own train notes) ends with a short metacognitive trace (2–5 lines:
  mistakes, surprises, what slowed the work, lessons about the way of working), written as `@@@memory` blocks
  (OR-50; types lesson, gotcha, trap, heuristic: the types routed to 10). The lead curates them into
  `memory-bank/10-METALEARNING.md`: dated, deduplicated entries, each with the change it caused (a rule, a brief
  line, a tooling task) or "watch". A lesson seen twice becomes a rule proposal, a brief line or a tooling task.
- Why: the same mistakes recur across lanes and sessions unless someone collects them and turns them into rules.
- How to apply: the journal hook stores the trace with the report; lane lessons reach 10 only through the train
  fold (each lane's `.lane-resume/memories.md`); the lead's inbox (`{{BOA_LEAD_DIR}}/metalearning-inbox.md`) holds only
  its own notes and curations, and a curation that improves a lane lesson supersedes it, never copies it
  (`.boa/tools/metalearning.py` finds repeats).
- Applies to: all (lead curates).
- Enforced: every contract's "Output" section, 10-METALEARNING.md, 09 §16.

### OR-36 — Cost hygiene: keep the prompt cache warm
- Rule: the sub-agents' prompt-cache TTL is the highest the runtime allows: the agent sets it when wiring BOA
  (references/runtimes.md); the main
  conversation's TTL changes only with the user's agreement (a longer TTL costs more per cache write). The setting
  names, values and defaults are facts of the runtime: its profile in the BOA package's `references/runtimes.md`
  (verify at every wiring, OR-63: names and values change).
  Where the agent may not set them, the lead tells the owner exactly what to change and why.
- Why: sub-agents wait on long test runs, so a short cache expires between their turns and every turn pays the
  whole context again; a longer cache write costs more once and saves far more over a lane.
- How to apply: when wiring BOA the agent checks them, sets the sub-agent TTL and asks the user about the main one
  (the BOA package's `references/runtimes.md`); the lead re-checks after a runtime update; resuming the same agent per round (OR-16) is part of the same hygiene.
- Applies to: lead.
- Enforced: the runtime settings the agent wired, AGENTS.md §6 "Cost hygiene".

## Safety rules (the role-aware guard)

### OR-37 — Sub-agents are confined to their own lane
- Rule: a sub-agent writes only in its own lane worktree, its own scratch subdir (`<scratch root>/<task>-<role>/`)
  and its task's throwaway resources (name `{{BOA_NAME_PREFIX}}<task>-*`, label `{{BOA_LABEL_KEY}}=<task>`). It never
  touches another lane: the guard binds each sub-agent to the first task id (`T-NNN`) of its spawn
  description, so **every sub-agent spawn's description starts with the lane's task id**. Only the integrator may act on any
  lane.
- Why: parallel lanes share a host and a repository; one agent cleaning "its" files in another lane destroys work.
- How to apply: briefs name the worktree, the scratch subdir and the task id first.
- Applies to: all sub-agents, lead (descriptions).
- Enforced: the guard (`guard_destructive.py`, reading the agent binding `agent_binding.py` recorded at the spawn),
  09 §4 and §11.

### OR-38 — Nobody pushes to the main branch
- Rule: the main branch (`{{BOA_MAIN_BRANCH}}`) changes only through reviewed PR/MR merges by the integrator (with no
  forge: the integrator's local fast-forward to the gated tip, after the one gate). Where
  the forge offers server-side branch protection, use it; otherwise a versioned pre-push hook refuses any push to
  it, with an audited escape hatch (logged, refused when the log cannot be written, the reason recorded in 05).
- Why: a direct push skips the gate; a red main branch blocks every lane.
- How to apply: the project's git hooks (project-wiring "git hooks": pre-push, pre-commit with the secret scan,
  commit-msg) in the shared hooks dir of every worktree; the lead re-installs them after a hook changes on main.
- Applies to: all (sub-agents never push at all; the integrator pushes lane branches and merges PRs).
- Enforced: the git hooks, the guard (sub-agent pushes to main), the integrator contract.

### OR-39 — The lead's exemptions pass only through one logged override
- Rule: what only the lead should do (operate the deployed instance, act on a path outside the project, prune a
  provably-own object outside the lane filters) passes the guard only through a command that starts with
  `{{BOA_ENV_PREFIX}}GUARD_LEAD_VERIFIED=<single-token-reason> `, after proving the target is ours (creation time,
  our name or label, no other user), with the evidence written in the registry. The override is logged; it never
  works for a sub-agent and never mid-command.
- Why: the lead needs a door the sub-agents do not have, and every use of it must leave a trace.
- How to apply: a reason with spaces or quotes is not recognised: one token (`reason_with_underscores`).
- Applies to: lead.
- Enforced: the guard, its log, 09 §11.

### OR-40 — The guard is non-blocking, fails closed and logs; its threat model is accidents
- Rule: a guard denial is a reason the agent reads and adapts to (never a stall waiting for a human), and every
  denial is logged. On an internal error, a timeout, a size or depth cutoff or unreadable input a guard refuses
  (fails closed) with a message naming the logged lead override (OR-39). The development guards' threat model is
  accidents, not attacks: realistic accidental bypasses and every fail-open are fixed and pinned by a test;
  deliberate parser-corner evasions no agent produces by mistake are documented known limits. This scope covers
  only the development guards: product code is always reviewed and tested against real attackers. The project's
  own protections (protected commands, heavy-run refusals, wrapped tools) follow the same rules and apply to the
  lead too.
- Why: a guard that silently allows on a crash protects nothing exactly when it matters; a guard without a log
  cannot be improved; chasing deliberate evasions in a safety net costs rounds without preventing accidents.
- How to apply: "The guard may refuse a command: adapt, don't work around it" is in every brief; a reviewer classes
  a fail-open or a realistic accidental bypass BLOCKING and a deliberate parser-corner evasion NON-BLOCKING (OR-52).
- Applies to: all.
- Enforced: the hooks, their suites, 09 §11.

### OR-41 — Secrets are never committed, printed or put on argv
- Rule: no secret in the repository, in a log, in a brief or in a command line; passwords pass through the
  environment or files with mode 0600. Every commit's staged diff is scanned; the whole tree and the full history
  are scanned at milestone closure and at close-out. The scanner is an existing, maintained secret scanner the
  agent adopts and wires for the project (OR-07, OR-64), with project patterns added in its configuration; never a
  hand-written detector.
- Why: a secret in history is public forever once the repository is shared; vendor token formats change faster than
  a home-made pattern list.
- How to apply: the project's pre-commit hook runs the scanner on the staged diff; the close-out runs it on the
  tree and the history; a hit is removed and the secret rotated, never "ignored".
- Applies to: all.
- Enforced: the project's pre-commit hook, the gate, the close-out (09 §14).

### OR-42 — Commits are small, atomic and conventional
- Rule: one logical change per commit, Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`,
  `chore:`, `build:`), the trailers the runtime gives for the session; one task → one branch → one PR.
- Why: atomic commits make bisecting and reverting cheap; a consistent log is the project's history.
- How to apply: split unrelated edits before committing; `wip(<task>): …` only at a pause.
- Applies to: all.
- Enforced: the `commit-msg` git hook, the integrator (refuses a PR whose commits break the format).

## Environment and product-quality rules

### OR-43 — Shared environment changes need the owner's approval; deployments are isolated
- Rule: before installing or reconfiguring anything on a shared machine, inventory what is there and prefer
  reusing it; changes to shared components are an owner decision (OR-12). The project's own deployment (a demo, a
  staging instance) runs isolated: its own ports, data, users and configuration, operated by the lead only, from the
  main checkout.
- Why: one global version switch can break every other project on the host.
- How to apply: the capabilities record (project-wiring "capabilities record") holds the inventory; 04 "Environment" records what is used.
- Applies to: lead (all: lanes never operate the deployment).
- Enforced: AGENTS.md §9, 09 §12.

### OR-44 — CI runs only with the owner's OK when it costs money
- Rule: hosted CI minutes cost money: the CI pipeline is manual-only (or off) unless the owner chose otherwise; the
  agent writes the project's CI only with the owner's consent; the gate runs locally or on the remote runner.
- Why: an automatic pipeline on every push burns the budget and duplicates the local gate.
- How to apply: a manual-only CI file has no push/merge triggers (the annotated CI examples in the BOA package's
  `references/forge.md`).
- Applies to: lead.
- Enforced: the forge-setup decision record in 06 (the owner's yes per forge decision), AGENTS.md §7, the CI task's
  review.

### OR-45 — The final bar: complete, zero known bugs, proven
- Rule: at the end everything in scope is there and works: every feature traced to the tasks that build it and to
  running tests (a gap fails a check), release acceptance passed (full-scope mutation on the delicate paths, end to
  end with real client types, security re-audit, zero open findings). Honestly stated: the measurable bar is "zero
  known bugs, every gate green, completeness proven", never an unprovable absolute.
- Why: "done" that cannot be proven is not done; claims the evidence does not support destroy trust.
- How to apply: parity registration on every task (09 §20); the close-out checks (09 §14).
- Applies to: all.
- Enforced: `.boa/tools/trace_check.py`, the close-out.

### OR-46 — Always the latest stable stack and standards
- Rule: every new dependency, image and tool on its latest stable version, verified online at execution (never from
  memory), pinned (version and digest); current standards (security baselines, protocols). Freshness is checked at
  milestone closure and release: zero outdated except documented holds with a review date.
- Why: a project built on last year's versions starts its life with a migration backlog and known vulnerabilities.
- How to apply: ADR per stack choice; the freshness check of the stack plug-in where it has one.
- Applies to: all.
- Enforced: 06, 09 §19.

### OR-47 — User-facing text uses the names the users know
- Rule: user-facing text (UI, docs, messages, pricing) uses the names customers know; code identifiers may stay
  neutral. A glossary in 04 maps the two.
- Why: internal names leaking into the product confuse users and support.
- How to apply: the glossary is updated with the first task that introduces a user-facing name.
- Applies to: all.
- Enforced: 04 glossary, the reviewer.

### OR-48 — Contract-driven: contracts first, code second, contracts enforced by tests
- Rule: every external surface has a written contract before it is built: APIs (OpenAPI or the stack's
  equivalent), data schemas (with their invariants), protocols and file formats, CLI or UI behaviour third parties
  rely on, and the interfaces between modules. Contracts live in the repository (`docs/api/`, `docs/specs/`), are
  versioned and are the source of truth: a build task implements a contract; a missing or ambiguous contract is a
  spec question (a spec-side task), never a guess. Contract tests pin them: API contract lint, contract and golden
  tests that fail when behaviour drifts, characterisation goldens for existing behaviour (brownfield/refactor:
  preserve behaviour, not the legacy shape), schema checks, third-party compatibility suites. Every feature traces
  to its contract and to the tests that prove it. Changing a contract is an ADR stating its compatibility impact.
- Why: code written against an unwritten contract encodes one agent's guess; parallel lanes then build against
  different guesses, and clients break silently.
- How to apply: the plan puts spec-side tasks (write or characterise the contract) before the build tasks that
  depend on them; the builder implements the contract and cites it; the reviewer attacks behaviour against the
  contract; the tester maps every acceptance criterion to a contract test; a contract change goes through 09 §25.
- Applies to: all (lead: plan order; analyzer: reconstructs contracts from existing code).
- Enforced: AGENTS.md §4 and §6, 02-SPECIFICATIONS.md, 09 §23 and §25, the builder, reviewer and tester contracts,
  `trace_check.py`.
### OR-49 — Correspondence closes to zero
- Rule: everything the project tracks corresponds, and one check proves it: every plan task maps to its contract or
  spec (or is declared tooling/process); every contract lists its tasks, its tests and its features; every feature is
  proven by running tests; every residue has an owner task and a removal step; every captured to-do in the transit queue (open-items.md) has an owner and is placed in the plan by the next fold; every
  pending owner rule or plan row is folded within one train. `python3 -I .boa/tools/trace_check.py` cross-checks plan
  tasks ↔ contracts ↔ specs ↔ features ↔ proving tests ↔ residue register ↔ transit queue (open-items.md) ↔ pending folds (the
  markers of 09 §26). It runs at every merge train (its result is in the integrator's report; each new mismatch
  becomes a task or a ledger item at once) and at close-out, where it must report **0 mismatches**: every contract
  closed (implemented, tested, signed off), every residue removed, every open item and pending fold at zero.
- Why: drift between plan, contracts, tests and ledgers is invisible until the end, when it is most expensive; a
  project whose correspondence does not close is not done, however green its gate.
- How to apply: keep the markers (02 contracts index, the 03 `Contract / spec` column, `@covers-contract` and
  `@covers-feature` test headers, the 04 register, the ledgers' formats) current in every task; the tester checks the
  task's rows; the integrator runs the check every train; `/close-project` refuses to close above zero.
- Applies to: all (lead and integrator above all).
- Enforced: `trace_check.py`, the integrator and tester contracts, 09 §7, §14, §26, `/close-project`.
### OR-50 — Every memory is one typed block, written through the memory tool; never edited, superseded
- Rule: every recorded memory (a memory-bank entry in 05, 06, 10 or active-context, a lead note in the inbox or the
  pending files, every agent's metacognitive trace) is one block
  `@@@memory-<N> brief="…" datetime="…" keywords="…" type="…"` … `@endmemory`, holding one fact, of the most specific
  of the types of `.boa/memory-types.json` (by default: lesson, gotcha, edgecase, constraint, contract, adr, edr,
  outcome, trap, heuristic, invariant, goal, nogoal, requirement, deferred, security, bug) — one configuration file
  defines the types, their routes and recall moments; every doc table is
  generated from it. Memories are written ONLY through `.boa/tools/memory_write.py`, `datetime` from the UTC clock in
  exactly `YYYY-MM-DDTHH:MM:SSZ`. Only the integrator's train fold assigns the progressive ids (`memory_write.py
  --ingest` in the train's single
  `docs(memory)` commit: ONE `--ingest` call with all the staging files and every lane's `.lane-resume/memories.md`
  as one batch, ordered by the tool topologically (every `supersedes` target first), otherwise by datetime, the
  staging-file and lane order only a tie-break;
  rebuilt from scratch without a bounced lane; ids never reused on main); lanes and the lead write `--format-only`
  blocks (no id). A replacing memory names the old ones in
  `supersedes="memory-12,memory-31"`; the writer stamps `superseded-by="memory-<N>"` on each — the only edit ever made
  to an existing memory. Nobody hand-edits ids or links; `Memories used:` cites final ids only.
  Agents NEVER write `@@@memory-<N>` ids or `superseded-by` by hand: only `memory_write.py` assigns ids (only the
  integrator's train fold, with `--ingest`); a lane produces id-less blocks with `memory_write.py
  --format-only`, which may carry `supersedes="memory-N"` (an existing final id) or `supersedes-brief="<brief>"`
  (another new block of the same lane or batch); the fold's `memory_write.py --ingest` resolves them and stamps both
  directions atomically. The id ledger `memory-bank/.memory-ids.jsonl`, written only by the tool, makes a
  hand-written id fail the lint, the post-tool hook and the pre-commit.
  Supersession chains are always coherent: a memory is superseded at most ONCE (a single `superseded-by`); to
  replace a memory that is already superseded, supersede the CURRENT head of its chain (`memory_search.py --chain
  <id>` shows it); one memory may supersede several current memories (a merge); two memories superseding the same
  one (a fork) are refused by `memory_write.py` and by the lint.
  Supersession runs forward in time: a memory that supersedes another has a `datetime` strictly later (and a higher
  id) than every memory it supersedes; `memory_write.py` refuses a supersession whose stamped datetime is not later
  (a clock problem to fix, never a hand edit), and the lint reports any pair out of time order. `supersedes` may
  list several ids; the check is PER ID: each listed id must exist and be strictly older (an earlier `datetime` and
  a lower id).
  A defect found in the product or the tooling is a `bug` memory (symptom, reproduction, root cause, fix, regression test, status; an open
  bug names its owner task T-NNN) plus a task. Task ids
  are `T-NNN` (at least three digits). Decisions are `ADR-NNN` blocks of type `adr` (architecture) and `EDR-NNN`
  blocks of type `edr` (how the work is carried out). In a file that held notes before BOA, a
  `<!-- boa:memory-cutoff -->` line exempts the legacy part above it.
- Why: free-form notes cannot be searched, typed or checked; a typed, dated, keyworded block with an id can be found
  by any agent at any time and linted; links stamped by one tool cannot drift, and superseding instead of editing
  keeps the history that explains today's state.
- How to apply: `.boa/tools/memory_write.py` writes; `.boa/tools/memory_lint.py` validates (fields, datetime format,
  type, ids unique and progressive, links agree both ways, no cycles) and runs on every commit (`pre-commit`,
  `--staged`, refusing broken links); the post-tool hook `.boa/hooks/memory_check.py` lints a memory file after every
  file write; `.boa/tools/memory_types.py` validates the types configuration and renders the doc tables;
  `.boa/tools/memory_search.py` finds memories; the session-start status carries a three-line memory-writing
  reminder. The type table: the BOA package's
  `references/memory-types.md`, summarised in `memory-bank/README.md`.
- Applies to: all.
- Enforced: `memory_write.py`, `memory_lint.py`, `memory_check.py` (hook), AGENTS.md §4, `memory-bank/README.md`,
  09 §16, every agent contract.
### OR-51 — Recall: search the memory before acting, cite what you used
- Rule: an agent searches the memory (`.boa/tools/memory_search.py`, current memories by default; hybrid: BM25
  finds the candidates, their keyword-bearing sentences are re-ranked by embedding similarity) BEFORE it acts at
  these moments, with the types the AGENTS.md §14 table lists for each moment first (the table is generated from
  `.boa/memory-types.json`; never a list typed from memory): starting or resuming a task; an error, a failing test,
  a refused command or a surprise; before a decision; before changing a contract, schema or public behaviour;
  reviewing or testing; planning, estimating, splitting lanes; closing a project. It follows what it finds or supersedes it (never silently ignores it), cites the ids it relied on in
  its report (`Memories used: …`), and writes a memory when the search found nothing and it then solved something
  non-obvious.
- Why: a memory nobody reads is a cost with no return; the same gotcha hit twice by two lanes is the failure the
  memory exists to prevent, and citations show which memories earn their keep.
- How to apply: AGENTS.md §14 (the table), every agent contract ("Memory recall" section), 09 §27; wired support: the
  post-tool-failure hook `.boa/hooks/memory_recall.py` injects matching gotcha/trap/lesson ids after a failed tool
  call (where the runtime has that event; verified at every wiring, OR-63); the session-start status prints the current memories for every
  active task id; a sub-agent gets its own task's memories through its brief ("memories to know", 09 §4); at a
  sub-agent's start, only where the runtime injects context there (verified at every wiring, OR-63),
  `memory_recall.py --session` adds the reminder and every active lane's memories; a decision, planning, a contract
  change, an update and the close-out are discipline only (AGENTS.md §14).
- Applies to: all.
- Enforced: every agent contract (recall step, citation in the report), the reviewer (a report that ignores a memory
  it should have followed is a finding), `memory_recall.py`.

## Rules from later practice

### OR-52 — Review findings are classed; a lane leaves review by the exit rule
- Rule: every review finding is classed BLOCKING (a broken or untested contract clause, wrong or lost data, a
  security hole or a fail-open guard, a regression, a crash or hang on reachable input, a delicate path without a
  fault-catching test, an unmet acceptance criterion) or NON-BLOCKING (naming, wording, docs, comments, cosmetic UI
  within the quality rules, hardening against unreachable input, simplification, a nice-to-have test), with a
  reason; the lead may re-class. A lane leaves review after a round with no findings, or after two consecutive
  rounds with no blocking finding; the second round is needed only if code changed after the first. Before the
  lane leaves review, each open non-blocking finding is fixed in the same round when it is SMALL, and relocated to a
  named task (a dated note on its row or the area batch task, OR-25) only when it is LARGE; never lost, never holding
  the lane. SMALL: inside the lane's own task (its files and its requirement) and needing no decision not yet taken,
  whatever the size of the edit (wording, docs, comments, a rename, a one-line or local fix, test data, a missing
  test for a line the lane changed, a hardening of the lane's own code). LARGE: it needs a spec or owner decision
  not yet taken (asked first), belongs to another task's or lane's scope or depends on a task not yet landed, or is
  new scope (a new feature, requirement, tool or suite). The fix goes to the builder tier OR-34 picks: `builder-mid`
  for docs or comment-only fixes, wording, a rename, a one-line fix, test data and mechanical follow-ups; `builder`
  for a delicate path or non-trivial code; when in doubt, `builder`.
- Why: a "zero findings" loop once ran seven rounds of one to three minor findings each.
- How to apply: the reviewer writes `[BLOCKING|NON-BLOCKING] [SMALL|LARGE] file:line — what — failure scenario — fix —
  reason` (SMALL or LARGE on a non-blocking finding only); re-reviews are delta reviews; the lead records the round and the class counts in the registry.
- Applies to: reviewer, lead, builder.
- Enforced: the reviewer contract, 09 §5 and §6.

### OR-53 — Stage budgets: stop and report at the budget
- Rule: every stage has a budget. Tester: at most 3 mutation runs (one per tester round, across bounces) and 3 plant
  rounds per lane, and a time budget
  computed from what it must run (suites × their measured durations × planned rounds, mutation scope × measured cost,
  expected runner wait, plus a margin). Builder and reviewer: about 60 minutes per round. At the budget the agent
  stops iterating and reports the current state (results, open survivors with an equivalence or killability
  judgement, what slowed it); the lead accepts, bounces (testability) or extends once, with a reason.
- Why: unbounded test stages once ran for hours and starved the rest of the project.
- How to apply: the lead states the budget in the brief (otherwise the agent computes it at start and writes it in
  its resume file); `lead-status.sh` and the registry show stages over budget.
- Applies to: tester, builder, reviewer, lead.
- Enforced: every brief (09 §4), the tester, builder and reviewer contracts.

### OR-54 — An error is reproduced in both directions
- Rule: where a defect is fixed (a bug, a review finding, a failing case), a test reproduces it first: it fails on
  the code before the fix, for the reason the defect explains, and passes after it. A timing or performance pin is
  shown slow on the old code first. A test that passes on both versions proves nothing and is not evidence.
- Why: a "regression test" written after the fix often passes on the broken code too; the obvious input is not
  always the one that triggers the defect.
- How to apply: the builder runs the new test on the unfixed code (stash the fix, or plant the old line back) and
  reports both results; the reviewer asks for it when it is missing; the tester checks it on the delicate paths.
- Applies to: builder, reviewer, tester.
- Enforced: the builder, reviewer and tester contracts.

### OR-55 — Plants run only the covering cases, in parallel
- Rule: a planted fault runs only the test cases that cover the planted line (every suite, any kind: the suite's
  case filter or the framework's own filter), and counts as caught only when a covering case fails for the planted
  reason or its run times out while a covering case is running (killed by timeout, see How to apply). Independent plants run in parallel, each in its
  own scratch copy of the worktree, up to the lane cap. The whole suite runs once at the start and once at the end,
  never per plant. Builders and reviewers run only the cases they touch.
- Why: whole-suite plants run one after another once made a single tester stage last hours; a plant round should
  cost about its slowest covering cases.
- How to apply: every copy has a green clean baseline run (else a crash is a false kill); the verdict has four
  states: a failing case, a crash, clean, and a run that times out while a covering case is running; the fourth counts
  as killed by timeout, recorded as such, provided the clean baseline run finished inside the bound and the timeout
  is confirmed by a replay alone, unless the first run already ran alone (no other run active at any time during
  it): a replay of the plant alone, under the same timeout, times out too, while a replay that ends gives its own
  verdict; a timeout outside every covering case, before the first one or in code no case gates, is confirmed the
  same way and is invalid, like a failure there; when the cap clipped the bound (the timeout derived from the clean
  baseline run is above the cap), a confirmed timeout is skipped, never killed or invalid: raise the cap; a plant whose
  clean baseline run is already over the bound is skipped (not run): raise the bound within the cap or narrow the cases,
  as for a mutant; a killing test asserts the specific effect.
- Applies to: tester (builder and reviewer for their own runs).
- Enforced: the tester contract, every suite's case filter.

### OR-56 — Real-input tests for code that consumes produced files
- Rule: code that maps, validates, renders or installs files another part of the project produces (templates,
  configs, manifests, schemas) is tested at least once per round against the REAL files on current main, not only
  against fixtures. A fixture-only green is not evidence. A lane that consumes another lane's output rebases and
  tests against main every round; producer/consumer lane pairs are hotspots: serialise them, or the consumer tests
  against the real files on main every round.
- Why: fixture-only suites once hid for several rounds that an installer no longer matched the real templates.
- How to apply: the builder adds the real-input case; the tester checks that such a case exists and runs; the lead
  treats producer/consumer pairs as hotspots when filling lanes.
- Applies to: builder, tester, lead.
- Enforced: the builder and tester contracts, 09 §3.

### OR-57 — Specs, plan and rules are read from the current main
- Rule: every agent reads the specs, the plan, the requirements and the owner rules from the project's CURRENT main
  checkout, never from the copy inside its lane worktree (a lane, a stacked one above all, carries a stale copy).
  Briefs give the main-checkout paths. A finding judged against a lane copy that main has changed is void.
- Why: a reviewer once judged a lane against a removed config key that still sat in its stale copy.
- How to apply: read with `git -C <worktree> show origin/<main>:<path>` after a fetch (with no forge: the local
  `<main>`, no fetch; 09 §7), or from the main checkout path the brief gives.
- Applies to: all.
- Enforced: every brief (09 §4), every agent contract.

### OR-58 — A new rule reaches every running agent at once
- Rule: when the owner gives a new rule or changes one, the lead, in the same step: (1) records it (the pending
  file, briefs, templates); (2) sends it at once to every running agent whose work it affects, saying what changes
  from its next step and that work already done is not redone; (3) checks that each agent acknowledged it; (4)
  briefs every later agent with it. A rule written only into briefs or files is not propagated.
- Why: running agents never re-read the briefs; the owner once had to ask why a new rule was ignored.
- How to apply: one message per running agent; the acknowledgement goes in the registry.
- Applies to: lead (every agent acknowledges).
- Enforced: 09 §16.

### OR-59 — One active stage per lane; agents never open tasks; briefs carry the memories
- Rule: a lane has ONE active stage at a time (never a builder editing while its reviewer reviews); a lane in
  progress takes only fixes, follow-ups wait for the next builder round or become plan rows; agents never create
  tasks (they report Leftovers, OR-25); the same integrator runs a train to the end; every brief carries the task's
  current memories and every report cites `Memories used:`.
- Why: edits made under a running review went unreviewed; tasks opened by agents multiplied the plan.
- How to apply: the lead queues follow-ups; the registry shows the one stage per lane.
- Applies to: lead, all.
- Enforced: 09 §4 and §5, every agent contract.

### OR-60 — Every plan row lists its edge cases
- Rule: every task row names its edge cases (boundaries, empty or oversized input, concurrency, failure and retry,
  permissions, time and locale, partial failure, hostile input on external surfaces) or says "none, because …". The
  builder covers them, the reviewer attacks them, the tester maps each one to a running test.
- Why: the cases nobody wrote down are the ones nobody tested.
- How to apply: the lead fills the plan template's edge-cases field when it adds a row; a row without it is not
  ready to build.
- Applies to: lead, builder, reviewer, tester.
- Enforced: the plan template (03), the builder, reviewer and tester contracts.

### OR-61 — Sub-leads: delegated streams, one integrator, lead-only powers
- Rule: where the runtime supports it (nested sub-agents, found by the capability self-assessment; a sub-lead runs as
  a sub-agent bound to its stream, never as a peer session, which the guard would treat as the lead;
  unknown → ask the user), the lead may delegate a disjoint stream of tasks to a sub-lead with the same tools and
  knowledge. A sub-lead runs its own lanes and reports to the lead; it never merges, never creates tasks, never
  touches lanes outside its stream. One plan, one integrator queue for all streams, one global lane cap; every plan
  row names who manages it (`managed by`). **Lead-only powers:** the plan and task ids, `managed by`, owner rules
  and HITL, the train order, the migrations hotspot, deployment operations, the guard override, the main checkout.
- Why: one lead becomes the bottleneck on large plans; parallel merges without one integrator break main.
- How to apply: 09 §28 (the sub-lead brief and contract); the registry records each lane's owning lead.
- Applies to: lead, sub-lead, integrator.
- Enforced: the sub-lead contract, 09 §28, the guard's lane binding.

### OR-62 — Schema migrations are a delicate, serialised path
- Rule: schema migrations are delicate: targeted mutation, tests on the real engine in every isolation mode that
  matters, lock-first writes, the schema spec amended first (OR-48); migrations are a hotspot the lead serialises
  (or orders collision-free); lanes that add migrations run the schema and migration suites; only the lead applies
  merged migrations to running instances, after a backup.
- Why: two lanes adding migrations in parallel collide at merge; a migration applied without a backup is
  irreversible.
- How to apply: the plan marks migration tasks with the hotspot; 09 §12 for applying them.
- Applies to: lead, builder, reviewer, tester.
- Enforced: the plan's hotspots, the reviewer and tester contracts, 09 §12.

### OR-63 — Assess, decide, ask: the capability self-assessment
- Rule: at bootstrap, and whenever its runtime or environment changes, the agent assesses its own capabilities by
  checking them (documentation, help output, a harmless trial), never from memory: hooks and their events,
  sub-agents and parallel runs, background tasks, worktrees, model choice per sub-agent, permission modes,
  scheduling, network, tools, limits. It decides how it implements each part of the discipline with them, declares
  every substitute and every part it cannot provide (never fakes one), and asks the user what it cannot determine
  (OR-12): owner topics, mutation testing, CI, runners, models, protections. The result is recorded (capabilities
  record and decision entries) and re-checked when the runtime changes.
  Every adaptation to the runtime checks the runtime's latest official documentation and the installed version
  (its help, its settings schema, a harmless trial), every time and never from memory: wiring or re-wiring hooks and
  their events and fields, sub-agents and their header (model names and aliases, effort, tools), commands, settings
  keys, permission modes, the context-gate profile, the protected-command rules, the runtime part of an update. Record
  what was checked, where and when. When the installed version is older than the documentation, follow the installed
  version's behaviour and tell the user an update exists. Dates and versions in BOA's runtime profiles are evidence
  of a past check, never permission to skip one.
- Why: a discipline written for one runtime silently breaks on another; a faked capability is worse than a declared
  gap; runtimes change between versions, and a fact remembered or copied from an older check is wrong without a sign.
- How to apply: the skill's first step; the lead re-runs it after a runtime update; every wiring or re-wiring
  step starts with the check.
- Applies to: lead, and any agent that adapts something to the runtime.
- Enforced: the capabilities record, 09 §1.

### OR-64 — Project specifics are wired by the agent; measuring is periodic tooling work
- Rule: what is specific to the project is done by the agent, in the project, as planned tasks under the full
  pipeline, following the project-wiring checklist (the BOA package's `references/project-wiring.md`): the stack
  plug-in (gate steps, test runner with its case filter, mutation library or plants, lint and static analysis), the
  gate itself, the git hooks, the secret scanner, the project's protected-command rules for the guard, heavy-run and
  wrapped-tool refusals, CI (only with consent), runners and their deploy script, the model roster, the measuring
  tools (clock, disk watch, suite timings, residue check, throughput), the notification channel, the runtime wiring
  of hooks and context-gate. Each is built with an existing tool where one exists (OR-07). Measuring is periodic
  tooling work: its output is reviewed at every train and at milestone closure, and each problem it shows becomes a
  planned tooling task.
- Why: shipped adapters for every stack, vendor and service are maintenance nobody wants; a project knows its own
  tools best.
- How to apply: the checklist items are seeded as plan rows at bootstrap; each one is closed by its Done-when check.
- Applies to: lead (plans, decides with the user), builder, reviewer, tester.
- Enforced: the plan's wiring rows, 09 §15 and §23.

### OR-65 — Product language and user language are kept apart
- Rule: the PRODUCT language ({{BOA_DOC_LANGUAGE}}) is the language of identifiers, comments, documentation,
  commit messages and the project's own texts. The USER language ({{BOA_REPLY_LANGUAGE}}) is the language the user
  writes in: the conversation with the owner, the content (brief and text) of memories and the free text of reports,
  plans and notes are in it; the product's user-facing strings follow it when the project decides so, only through
  the localisation files. Default: everything English. The agent detects or asks the user language at bootstrap
  (OR-12) and records both in this file. The memory syntax (block markers, field names, type names) is always
  English; the machine-recognised words of reports, plans and folds come from `.boa/markers.json`. A change of the
  product language is run by the lead FIRST, through `boa language set <lang>`: it adds the translated markers to
  `.boa/markers.json` (English kept as aliases) and self-checks every hook; reports stay English until that check
  passes; then the product follows the new language. Never mix the two in one text: a product artifact is wholly
  in the product language, process text wholly in the user language.
- Why: mixed-language code and docs are hard to read, search and review; an owner addressed in the wrong language
  misreads decisions; a marker the hooks no longer recognise loses reports silently.
- How to apply: replies and process text in the user language; every product file in the product language; the
  reviewer flags a mixed artifact; on a language change, `boa language set` before anything else.
- Applies to: all (lead: bootstrap question, language change).
- Enforced: AGENTS.md §1 and §4, every agent contract, `boa language set` (its hook self-check).

### OR-66 — The final requirements review walks every requirement to zero
- Rule: before a milestone is closed and before the project is declared done, a review walks EVERY requirement
  against: every indication the owner gave (08, its pending file and the decisions in 06); every planned task (03);
  the shipped CODE (each part against its requirements, tests and tool docs) and the shipped DISCIPLINE (each rule,
  procedure, template and doc against its requirements and against each other, no contradiction), each checked
  separately. Each row ends `done` with its proving artifact and running test, or open with an owner task. The
  project is not done until the walk reaches zero open rows.
- Why: green suites prove what was tested, not that everything the owner asked for was built; a rule and a template
  that say different things mislead every later agent.
- How to apply: an independent reviewer (not the lane's) runs the walk with the checklist of 09 §14; every open row
  becomes a plan row (OR-25); the walk repeats until zero.
- Applies to: lead (orders it), reviewer (walks it), all (fix the open rows).
- Enforced: 09 §14, `/close-project`.

### OR-67 — A problem: memory first
- Rule: when any problem occurs (a failure, an error, a bounce, a surprise), the agent FIRST searches the memory
  (`.boa/tools/memory_search.py`) for the same or a similar problem already met or solved, BEFORE it diagnoses or
  tries a fix. It uses what it finds and says so in its report (`Memories used: <ids>`); when nothing matches it
  writes `none found`. A new solution is recorded as a memory through `.boa/tools/memory_write.py`.
- Why: the same problem solved twice from scratch is wasted work and the failure the memory exists to prevent;
  stating "none found" shows the search was done.
- How to apply: AGENTS.md §14 (the `error` moment), 09 §6 and §27, every agent contract; a bounce brief names the
  memories found for its finding.
- Applies to: all.
- Enforced: every agent contract, 09 §6, the reviewer (a report with a problem and no memory citation or `none
  found` is a finding).

### OR-68 — BOA is a tool, never the project
- Rule: BOA is a tool the agent uses, never part of the product. Its files, tests, logs, tasks and tooling are never
  mixed with the project's own, and nothing of BOA goes into the product or its releases. `.boa/` is git-ignored
  (`/.boa/*`) and reinstalled with `boa install`, except the files the agent writes for the project there
  (`.boa/config.env`, `.boa/protected-commands.conf`, `.boa/memory-types.json`, `.boa/markers.json`, the stack plug-in
  `.boa/stack/` it adapts). What the agent writes FOR the
  project (those files, the memory bank, the plan, the specs, the handbook, AGENTS.md) is project knowledge and
  stays versioned in the repository.
- Why: a product that carries the tool that built it ships foreign files, and a plan or test suite that mixes the
  tool's work with the product's hides what the product really needs.
- How to apply: never add a `.boa/` path other than those four files and `.boa/stack/` to a commit, and none to a package or a release; BOA's own tests, logs and tasks stay
  out of the project's suites, plan and reports; when `.boa/` is lost or stale, reinstall it with `boa install`.
- Applies to: all.
- Enforced: the installer's `.gitignore` block (`/.boa/*` ignored, the project files and `.boa/stack/` kept),
  AGENTS.md, the handbook.

### OR-69 — An existing project: every new feature and change goes through the full flow
- Rule: when BOA is added to a project that already exists (brownfield or refactor), every new feature and every
  later change to the product is implemented through the full BOA flow: a plan row, the contract clauses first, then
  builder → adversarial reviewer → tester → integrator, a merge train, memory and traceability. Nothing bypasses the
  flow because the code predates BOA. Existing code a change touches gets its contract clauses and goldens first, so
  the change is reviewed and tested against them.
- Why: a project adopting BOA is tempted to keep editing the old way "just this once"; those changes escape the
  contracts, the review, the tests and the traceability, and the discipline decays at the exact place it is needed
  most.
- How to apply: the bootstrap (09 §23) ends with the pre-existing contracts characterised; from then on a request
  enters as a plan row (OR-25), its contracts and goldens are written or extended first (OR-48), and the lane runs the
  pipeline and the train (09 §5, §7); a "quick fix" outside a lane is a defect to bounce, not a shortcut.
- Applies to: all.
- Enforced: 09 §23, `/run-project`, the brownfield and refactor mode references, the reviewer (a change with no plan
  row or no contract clause is a finding).

### OR-70 — A short idea still gets complete specifications; every gap goes to the user
- Rule: however short the IDEA is, before any build the agent derives from it ALL the specifications: the
  requirements, the contracts with their clauses, the edge cases and the acceptance criteria of every feature. Every
  doubt or gap it cannot settle from the idea is raised to the user as a HITL (options with pros and cons, and a
  recommendation); the agent keeps working on everything not blocked by it.
- Why: a short idea invites thin specs or guesses, and what was guessed is built, tested against itself and found
  wrong only when the user sees the product.
- How to apply: the bootstrap (09 §23) lists every goal, constraint, user, external system and open question, turns
  them into requirements, contracts, edge cases (OR-60) and acceptance criteria, and asks the user the open ones in
  one round (OR-12); a build task never starts on a spec that has a gap.
- Applies to: lead (derives and asks), analyzer, builder (a gap goes back to a spec task), reviewer.
- Enforced: 09 §23 and §25, `/run-project`, the greenfield mode reference, KICKOFF.md, the reviewer (a thin spec or a
  guessed contract is a finding).
### OR-71 — CI minutes are a budget: ask the visibility, monitor the usage, launch lean
- Rule: the visibility of the remote repository (public or private) is asked every time, before it is created. On a
  private repository, or any CI with metered minutes, the agent asks the user the monthly budget, wires a minutes
  monitor for the project's forge (its billing or usage API or CLI) as a periodic tooling task with a warning
  threshold and an alert to the user, and keeps the CI lean: cheap Linux jobs on push/PR, expensive runners (macOS,
  Windows, GPU) only on manual dispatch or release, cancel-in-progress on PRs, path filters so docs-only changes skip
  CI, a job that decides which jobs a change needs, each job printing its minutes. After the first run the billed
  minutes are measured; when the budget is at risk the workflow is disabled until the triggers are fixed; the full
  matrix is never re-run to check a docs change. A manual dispatch of the expensive runners takes a suite filter
  (validated against the project's suite names, never interpolated into the shell), so a re-run after a small fix
  runs only the touched suites; the full matrix runs once, at the end (before a release).
- Why: hosted minutes cost money, an expensive runner multiplies the cost, and a budget burned by an automatic
  trigger is found only when the bill arrives.
- How to apply: the CI task follows `references/forge.md` (the visibility question, the minutes economy) and the CI
  item of the project-wiring checklist; the budget and the threshold go into the forge-setup EDR (OR-12).
- Applies to: lead (asks, measures, alerts), builder (writes the CI), reviewer (checks the triggers).
- Enforced: the forge-setup decision record (visibility, budget), the periodic minutes monitor, the CI task's review.

### OR-72 — Suites are designed without waste
- Rule: a suite is built so that selecting and re-running it is cheap: one behaviour per case, small independent
  cases; heavy setup once per suite (or in shared fixtures), never per check; no check duplicated across suites; a
  case whose cost makes selection or plant rounds expensive is split; self-test plant cases (the permanent plants a
  suite or gate self-test keeps) live in or next to the cases they target, never all in one catch-all case.
- Why: a bloated or duplicated case makes every targeted run, plant round and re-run on an expensive runner slow, and
  hides which behaviour failed.
- How to apply: the builder and the tester write and review suites by this list; the duration watch (OR-20) catches the cost
  side at every train; the reviewer checks the rest.
- Applies to: builder, tester, reviewer.
- Enforced: the duration review (OR-20, 09 §15) and the reviewer (a bloated or duplicated suite is a finding).

### OR-73 — Every surface that leaves the machine is checked like a file
- Rule: commit messages, branch and tag names, PR/MR titles and bodies and release notes are checked against the same
  content rules as a file: the secret scanner's rules (OR-41), the project's forbidden names or terms, the product
  language (OR-65), the required and forbidden trailers (OR-42). A tool checks it wherever the project has one (the
  `commit-msg` hook, a pre-push or server-side rule for branch and tag names, the forge's push rules); by hand only
  where none exists, and the gap is recorded.
- Why: the checks on files leave the text that travels beside them unguarded: a secret, a forbidden name, a message in
  the wrong language or a forbidden trailer in a commit message or a PR body reaches the history and the forge as
  surely as one in a file.
- How to apply: the `commit-msg` hook and the close-out scan run the content rules on the message text (project-wiring
  "git hooks" and "secret scanning"); the builder checks its own commit messages and branch name, the integrator the
  squash or merge message, the PR/MR title and body and the release notes, the reviewer the commit messages and the
  branch name as part of the diff.
- Applies to: all.
- Enforced: the `commit-msg` hook and the branch and tag name check, the close-out scan, the integrator and the
  reviewer.

### OR-74 — The project's user documentation is kept current in the same change
- Rule: a change that alters what a user of the project sees (a behaviour, a command, a flag, a config key, an API, an
  error message) updates the project's user documentation (README, guides, API reference, changelog) in the same
  change; otherwise the task is not done. The project decides which files are its user documentation; the default the
  agent proposes at bootstrap is the README plus `docs/`, minus the files BOA installs there (`docs/agent-handbook.md`,
  `docs/boa-notice.md`, `docs/boa-rules.md`, `docs/parity/` and, in a clean-room project, `docs/clean-room.md`; `docs/api/`
  and `docs/specs/` are user documentation unless the project decides otherwise); the project confirms or changes it, and the result is recorded in the
  handbook's file map. Before every release or milestone
  closure a docs sweep task checks every user chapter against what landed, and the release notes follow OR-73.
- Why: documentation that lags the product misleads the users it is written for; the agent handbook rule (OR-26)
  keeps the agents' map current, and nothing else keeps the users' one.
- How to apply: the builder updates the user documentation with the change; the reviewer flags a user-visible change
  without its documentation update (severity major, blocks, as for the handbook, OR-26); the lead plans the docs sweep
  as a task before each release or milestone closure (09 §14); the handbook's file map names the user documentation; a
  docs-only fix of a review finding is verified by the tester against the finding, and the reviewer's exit counts it
  resolved.
- Applies to: all.
- Enforced: the builder and reviewer contracts, 09 §14 and §16, the docs sweep task.

<!-- rules-pool:end -->

## Optional rules adopted for this project
<!-- The lead copies here, at bootstrap, the optional rules of the BOA rules pool that apply (UI quality bar,
     clean-room and provenance, domain rules), renumbered after the last rule. "none" if none applies. -->
- none yet

## Product decisions (what we build)
<!-- Owner decisions about the product (providers, models, naming, pricing rules…), one OR-ID each, with the
     owner's words, the rule, the tasks it binds and where it is enforced. -->
- none yet

## Owner rules added during the project
<!-- Folded from the lead dir's owner-rules-pending.md by each train's docs(memory) commit, with the next free OR-ID.
     Format:
### OR-NN — <title>
- Owner, YYYY-MM-DD (verbatim): "<…>"
- Rule: <…>
- Why: <…>
- How to apply: <…>
- Applies to: <roles>
- Enforced: <where>
-->
- none yet

## Memories — owner rules
<!-- Memory blocks of type constraint with the keyword owner-rule are appended here by `.boa/tools/memory_write.py`
     (`memory-bank/README.md` "Memory blocks"); each folded OR entry above names its block (`memory-<N>`). -->
