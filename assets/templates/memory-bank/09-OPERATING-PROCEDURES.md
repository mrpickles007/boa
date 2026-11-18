# 09-OPERATING-PROCEDURES.md — how the lead and the agents actually work

> **Binding** (AGENTS.md §3). The pipeline *rules* are in AGENTS.md §6/§6bis; the owner's rules are indexed in
> `08-OWNER-RULES.md` (OR-IDs). This file is the *practice*: numbered procedures that a brand-new lead session or
> sub-agent can follow from the repository alone. Append-and-refine: when a procedure changes, change it here in the
> same train and date the change.
> Paths: `<main>` = the main checkout; `<wt>` = a lane worktree `{{BOA_WT_DIR}}/<T>`; `<T>` = a task id
> (`T-NNN`); `<scratch>` = the session scratch root `{{BOA_SCRATCH_ROOT}}` (shared by every lane;
> each agent owns only `<scratch>/<T>-<role>/`); `<lead>` = `<main>/{{BOA_LEAD_DIR}}`. Tools live in `<main>/.boa/`.

## 1. Session start (lead)
1. Read, in this order: `AGENTS.md` (its Modus operandi first: the mood behind every rule) → `docs/agent-handbook.md` → the runtime's own
   instruction file when it has one (it only points to `AGENTS.md`) → `memory-bank/RESUME.md`
   → every
   `memory-bank/*.md` (08 and 09 included) → `<lead>/README.md`, `<lead>/PAUSE` and `<lead>/RESUME-LEAD.md` (after a
   pause) and `<lead>/lanes.md` → `git worktree list` → each lane branch's head (`git -C <wt> log --oneline -3`) →
   the project's disk snapshot and alert (project-wiring "measure commands") → the guard and permission logs.
2. Run `.boa/bin/lead-status.sh`: one screen with every lane (head, ahead, PR, last agent's verdict, suggested next
   step, newest registry line), admission (load, memory, lane cap), warnings, open PRs, Open HITL, new guard
   denials, DONE/total (the disk alert and the suite timings come from the project's own measuring: step 1 and
   §15). The session-start hook already injected its top lines plus the resume protocol
   and a three-line memory-writing reminder (memories only through `.boa/tools/memory_write.py`, the most specific
   type, supersede — never edit).
3. State in one line: active milestone, active lanes, next action.
3b. After a runtime update, on a new machine, in a runtime the capabilities record does not name (or whose wiring
   is absent), or when the runtime that last worked on the project is not this one, re-run the capability
   self-assessment (OR-63), wire this runtime alongside the others (never touching their wiring), set the per-runtime
   keys again (`BOA_SCRATCH_ROOT`, `BOA_SCRATCH_GLOB`) and update the capabilities record before starting lanes;
   paused: §13 "Resume". BOA is installed when `.boa/installed.list` exists or BOA's marked block is in `AGENTS.md` or
   `.gitignore` (a fresh clone, no `.boa/commands/` or `.boa/bin/`: `boa install` from the BOA package first); a
   `.boa/config.env` alone is an install to finish. Installed and the plan has tasks: never a bootstrap again,
   whatever door you came in by.
4. Where the runtime cannot resume an agent across sessions (capabilities record), resume every lane at its recorded stage with **new** agents, giving each one
   the lane's last recorded state: the registry line, the newest entries of `<lead>/lanes/<T>.md` (the previous
   agent's final report, verbatim), the head SHA, the open findings and its `.lane-resume/<role>.md` if any. Within
   the new session OR-16 applies again (same agent per role per task; resume or fresh: §5.3).
5. After an interrupted turn inside a session: first check which agents finished (OR-17; their reports are in
   `<lead>/lanes/<T>.md`), advance those lanes, tell the owner briefly.
6. Start the project's disk measurement if it is not running (project-wiring "measure commands").

## 2. Live state registry (`<lead>/`)
- `<lead>/` is machine-local, git-excluded, never committed. Only the lead writes it (the guard refuses sub-agent
  writes); agents may read it.
  - `lanes.md` — the registry. **Append-only**, one timestamped UTC line per stage change:
    `<ISO time> <T> <stage> (<head SHA>) — <role>, round <n>, bounce reason, lead decision, HITL`. Lines
    start with the time and then the task id, so `lead-status.sh` finds the newest line per lane; the newest wins.
    Train lines name every lane (`TRAIN-<n> (<T-a>+<T-b>) …`). Override evidence (§11) is written here too.
    Agent ids are NOT written here: their one home is the agents registry (below).
  - **Agents registry** (the sub-agent lifecycle, §5.3): the project's clock (project-wiring "usage clock and throughput")
    records every spawn under the first task id of its description and lists, per task, role, agent id, model,
    started and state: the id to resume next to each lane.
  - `lanes/<T>.md` — the **lane journal**, written automatically by the sub-agent stop hook
    (`.boa/bin/lane-journal.sh`): one entry per agent stop, `## <UTC time> | <agent type> | <agent id> | <status>` +
    the agent's final report (capped; copied as written: the journal is private and git-excluded). Agents without a task id land in `lanes/_unassigned.md`. Never
    edited by hand. `lanes/<T>-<role>.md` = resume or closure copies (§13).
  - `owner-rules-pending.md`, `plan-additions-pending.md`, `open-items.md`, `metalearning-inbox.md` (§16, OR-25).
  - `brief-common.md` — the rules pasted into every brief (§4); the lead grows its "project lessons" part.
  - `PAUSE`, `RESUME-LEAD.md` — present only during a pause (§13). `README.md` — what lives here.
  - `lead-status.seen` — the status screen's bookmark (guard denials already seen).
- Durable rules and decisions never go in `<lead>/`: they go in AGENTS.md and `memory-bank/` (08, 06, 03…).
- If `<lead>/` is absent (a fresh clone elsewhere): there is no live lane state; rely on the memory bank (03 status,
  05, active-context), `git worktree list` and the forge's open PRs, and start lanes fresh.

## 3. Filling lanes
1. Eligible tasks: `python3 -I .boa/tools/plan_lanes.py` (wave 1 = deps DONE, no hotspot shared with a running
   lane; `--check` green after any plan edit). Product tasks first; tooling tasks when they unblock product work, measurably speed it up (a faster
   gate or suite, a runner wired) or are planned like product tasks (OR-23).
2. Admission: at most {{BOA_LANE_CAP}} lanes (set from the capabilities record, recalibrated to the machine), one
    integrator, a heavy-step
   semaphore when heavy runs are local, sized by the test-execution decision (project-wiring "light and heavy suites"); start a lane only when `lead-status.sh` shows admission (load and free
   memory under their thresholds) and no disk alert is set (§10). Recalibrate the cap while working: lanes that stall on load mean
   fewer lanes or a remote runner (§15, the throughput review); a cap change is a registry line (an ADR when it becomes the
   norm).
3. One worktree per task, from current `origin/{{BOA_MAIN_BRANCH}}`:
   `.boa/bin/lane-worktree.sh add <T> <branch>` (branch per `{{BOA_BRANCH_GRAMMAR}}`; lean: the sparse and
   dependency rules of the stack plug-in); `.boa/bin/lane-worktree.sh remove <T>` at the end.
4. Append the start to `<lead>/lanes.md`, choose the builder tier (§5.2) and brief it (§4). The sub-agent spawn's
   description starts with the task id, so the agents registry records the spawned agent under the task (§2, §5.3).

## 4. Agent briefs — what every brief MUST contain
Write it out; never assume the agent "knows".
- **Identity:** task id, worktree path, branch, base SHA and current head SHA, the agent's scratch subdir. The Agent
  description starts with the task id (`<T> review r2 …`): the agent binding and the journal bind the agent to it (§11).
- **Goal**, plus the owner's own words when they matter (quoted, with OR-IDs).
- **Memories to know** (OR-51, MANDATORY in every brief): the output of `python3 -I .boa/tools/memory_search.py --task <T>`
  (and of a search on the task's components), pasted as is: this is how a sub-agent gets its own task's memories (the
  sub-agent start hook, where the runtime has one, gives only the reminder and every active lane's memories: the
  agent's task is bound only after it starts, AGENTS.md §14). The agent searches again itself at start and on any
  error, and cites the final ids it used.
- **Acceptance criteria** (copied from the plan row; they go into the PR).
- **What to run:** the named tests and suites the change touches; for the tester the delicate lines to mutate.
- **Rules (always):** paste `<lead>/brief-common.md` (targeted runs, no synthetic load, never touch other projects
  or the deployment, never print secrets, container naming and labels, scratch and cleanup shapes, the guard may
  refuse: adapt, payload-only guard tests, built-in first, commit trailers as given by the session, do not push,
  never edit active-context, ADR numbers from the lead, the clock lines, the handbook duty, the metacognitive trace,
  the Provenance line in a clean-room project).
- **Spec source** (OR-57): the main-checkout paths of the specs, plan, requirements and owner rules; never the
  lane's copy.
- **Budget** (OR-53): the stage's iteration cap and its time budget, computed from what it must run.
- **Report format** (the journal hook stores it verbatim, so it must stand alone): commits; per acceptance
  criterion what was done and which test proves it; files; findings/failures in the role's format; decisions to
  review; open questions; residue; elapsed; **metacognitive trace** (2–5 lines, OR-35); `Memories used:` (the ids, or
  none); and the `Leftovers:` section, last (every open item with its owner, or `none`; a report without it is
  flagged and the same agent is resumed to add it).

Templates (fill the `<…>`):
- **Builder:** "You are the BUILDER for <T>. Worktree <wt>, branch <branch>, base <sha>, scratch <dir>. Goal: <…>
  (owner: "<…>"). Acceptance: <list>. Run only: <tests/suites>. <delicate paths to expect>. <rules block>. Report:
  commits, per-criterion summary, files, assumptions, elapsed, metacognitive trace. Append to 05." Delta round: "Fix
  ONLY these findings: <verbatim list>; per finding say what you changed or why you reject it."
- **Reviewer (read-only):** "You are the adversarial REVIEWER for <T>, <full | delta <old>..<new>>. Attack:
  <criteria, boundaries, security surface, behaviour vs specs/goldens, KISS/YAGNI/DRY, reinvention>. Prior findings
  to verify: <list>. Run only what proves or disproves a finding. Report: `[SEV] [BLOCKING|NON-BLOCKING] [SMALL|LARGE]
  file:line — what — failure scenario — fix — class reason` (SMALL or LARGE on a non-blocking finding only), `Delicate paths for Tester: …`, or `REVIEW CLEAN` + what you
  tried."
- **Tester:** "You are the TESTER for <T> at <sha> (review clean). Verify: <criteria>; suites: <list>; static
  analysis on <paths>; mutation (§24) on <changed delicate lines> through the stack's mutation wrapper; thresholds <…>;
  non-mutable delicate code: planted faults. Docs-only lanes: completeness against the sources. Report: tests added,
  results, MSI per file, survivors and disposition, suite times, verdict GREEN/BOUNCE."
- **Integrator:** "You are the INTEGRATOR for TRAIN-<n>: <T-a (sha), T-b (sha)> in this order (<reason>). Follow
  `integrator.md` and 09 §7. one docs(memory) commit: <plan rows, 05, active-context lines per lane>; ingest
  <staging files, lanes>.
  Report: PRs, gate result, merge SHAs, residue per lane, durations (§15), disk delta, unblocked tasks."

## 5. The per-lane loop, as practised
1. Builder (full) → adversarial reviewer (full) → builder delta (only the findings; each fixed or rejected with a
   reason) → reviewer **delta** (changed lines + what they touch, re-attacked, prior findings verified) → repeat
   until the exit rule (item 9) → tester → integrator (train). Strict roles (OR-30): the builder builds (own tests, static
   analysis/lint on changed paths; no mutation, no suite batteries), the reviewer reviews, the tester runs the
   lane's only mutation runs (one per tester round, at most 3 per lane across bounces) and the train reuses its receipts.
2. **Model routing** (OR-34): simple, low-risk build work (docs/comment fixes, tiny bounces, spec docs, mechanical
   follow-ups) → `builder-mid`; anything delicate or non-trivial → `builder`; when in doubt, `builder`. A
   `builder-mid` that finds the work delicate stops and hands back; the lead moves the lane to `builder`.
3. **Sub-agent lifecycle (OR-16), per round:** the same task and role → resume the SAME agent by its id (the way
   your runtime resumes an agent, as recorded in the capabilities record) for delta fixes, delta re-reviews, re-tests and
   tester confirmations, its context intact; a new task or a genuinely new piece of work → a NEW agent; the train's
   integrator → resumed for the same train (re-stack, re-gate), new for a new train; an agent or session lost → a NEW
   agent of the same role, briefed from `.lane-resume/<role>.md`, the newest journal entry and the lead's notes
   since. The agent to resume is the one the agents registry (§2) lists for the task and role (it records every spawn,
   stop and replacement; never copy ids into `lanes.md`).
   **Resume or start fresh** (the one place of this rule; OR-16): when you send a bounce, a review finding or a next
   round back to a lane, or resume a paused round (§13) (the decision is taken ONLY when you hand out a NEW round: a
   bounce, a finding, a next stage, a resumed round;
   a working agent is NEVER interrupted, cut short or asked to wrap up because of its context size, its round count or
   its elapsed time: it finishes its brief (its own stage budget, OR-53, is part of its brief and still applies) and the triggers apply to
   the NEXT hand-off; the only reasons to stop a
   working agent are the user's request, a pause, the loop guard (OR-06) at a hand-off, or a clear runaway such as a
   hang or a resource emergency, each stated as such),
   - **resume the same agent** while its context is still moderate and the new round follows soon: it already holds
     the facts and the runtime's prompt cache is likely still warm;
   - **start a FRESH agent of the same role**, briefed with the lane's `.lane-resume/<role>.md`, its last report and
     the exact findings, when any trigger holds:
     - size: the agent's context size (the input of its last turn) is past the LOWER of about half of the model's
       context window, as the capabilities record states it for that role's model, and the cost bound
       `BOA_AGENT_FRESH_TOKENS` of the config (the per-turn cost of a large context dominates well before a large
       window is half full); only a context size is compared with the bound: a run's token total (the usage clock's
       figure, `result.tokens`) is not a context size and is never compared; with totals only, or nothing, the
       round count and the wait decide; window unknown: ask the user;
     - rounds: the round you are about to send would be the third the CURRENT agent serves on the lane (a fresh agent
       starts at one; a resumed paused round is the same round continuing and does not count); a fresh agent continues the lane's counts (OR-06 attempts, OR-52 rounds, the mutation cap);
     - wait: the wait since the agent's last turn is past the cache lifetime as wired (OR-36) in the capabilities
       record;
   - why: rereading what a round needs costs less than carrying everything, and a fresh context reasons better;
     compaction is not the lever, it loses detail (the context gate keeps a copy, but the agent works from the
     summary);
   - non-delicate one-line, test-data and wording fixes (OR-34) go to the light builder role, resumed or fresh by the
     same triggers;
   - before you decide, read the agent's context size where the runtime reports it (the clock's agents registry,
     project-wiring "usage clock and throughput"); where it does not, count the rounds and the wait.
4. Docs/memory-only changes skip review (OR-01): builder → tester (completeness against the sources) → integrator.
   A change mixing code and docs is reviewed for its code part.
5. The reviewer is read-only: the lead (or the next builder round) records each review outcome (findings count →
   resolved) in the lane's 05 entry.
6. Decisions the lead takes while relaying findings go in the bounce message, the registry line, and an ADR when
   they are lasting.
7. Rate-limit fallback (OR-33): only after an agent actually stops on a limit, a new agent of the same role on the
   next model, briefed from `.lane-resume/<role>.md` and the stopped agent's last state.
8. Every stage change → one registry line (§2). The journal fills itself.
9. **Review findings and exit** (OR-52): every finding is BLOCKING or NON-BLOCKING with a reason (the lead may
   re-class). The lane leaves review after a round with no findings, or after two consecutive rounds with no
   blocking finding (the second only if code changed after the first). Before it leaves, each open non-blocking
   finding is fixed in the same round when it is small (inside the lane's own task and needing no decision not yet
   taken, whatever the edit size) and relocated to a named task only when it is large (a decision not yet taken,
   another task's or lane's scope, a task not yet landed, or new scope), as OR-52 defines; the fix goes to the builder
   tier OR-34 picks (when in doubt, `builder`). The registry line carries the round and the class counts.
10. **One active stage per lane** (OR-59): never brief a builder while the lane's reviewer or tester is running;
   queue follow-ups for the next builder round. A lane in progress takes only fixes.

## 6. Loop guard
- **Problem → memory first** (OR-67): on any failure, error, bounce or surprise, search the memory with
  `python3 -I .boa/tools/memory_search.py` BEFORE diagnosing; cite the memories found (`Memories used: <ids>`) or
  write `none found`; record the new solution through `memory_write.py`.
- The same finding or failure surviving 3 builder attempts stops the lane: the blocker goes to the registry and 05,
  then the lead asks the owner (§8). When the reviewer's fixes are concrete and small, the recommended first option
  is a final targeted 4th attempt with the exact fixes and a closing criterion; anything left becomes a documented
  residual risk (OR-06). Other lanes keep going.
- One heuristic bouncing with a new finding each round counts as the same failure: after 3 rounds the lead
  raises a loop note, asks for a structural fix (narrow the heuristic's scope) and relocates further tuning to a
  named task.
- Review round 6 with blocking findings still appearing: the lead re-plans the lane (split, re-scope, re-spec)
  before any further round.

## 7. Merge trains
**No forge** (`BOA_FORGE=none`): with no forge, read `origin/{{BOA_MAIN_BRANCH}}` as the local
`{{BOA_MAIN_BRANCH}}` and skip the pull, the fetch and every push, here and wherever a procedure names
`origin/{{BOA_MAIN_BRANCH}}`; no PR is opened, and the landing is the fast-forward of step 7.
1. When: 3–4 lanes tested GREEN per gate (OR-31): hold a green lane until 3 are green or the oldest green lane has
   waited 60 minutes; a critical-path lane or a red-main fix may go alone, or (cheaper) at the bottom of the next
   train. One gate per train.
2. Order: plan-dependency order first, then by independence (OR-31): independent, low-risk lanes first,
   a riskier lane last; then smallest / least conflicting.
3. Rebase every lane head onto **current** `origin/{{BOA_MAIN_BRANCH}}` first (stale bases waste a gate); stack them
   (lane 2 on lane 1, …).
4. **docs(memory) fold** — ONE `docs(memory)` commit for the train, the last commit of the stack (on top of the last
   lane, so it lands with the last lane's merge; if a train lands only partly, the next train's fold covers every
   lane whose fold has not landed, merged lanes included), before any gate: for every lane the plan row's `; DONE —
   PR #NN` and its ledger
   row, the 05 integration entry, the active-context lines the lead names; the memory ingest of §16.4 (one batch,
   ordered by the tool, then the lint); the folds of §16
   (pending owner rules into 08, pending plan rows into 03, the
   metalearning inbox into 10) with the handbook updated in the same commit when a fold changes a procedure or tool.
4b. Dependencies: when the stack changes a lockfile under a lane's installed dependencies, refresh that worktree's
   dependencies (the stack plug-in's install step) before gating.
5. Open the PRs (body: acceptance criteria, review sign-off, test results, Provenance line in a clean-room project);
   with no forge (`BOA_FORGE=none`) none is opened.
6. Prefix checks, then the gate. The prefix checks run first, on every train, with or without a forge: the light
   static checks that read the plan, the feature ledger and the generated files (`plan_lanes.py --check`,
   `trace_check.py`, the project's rendering drift check) run on EVERY prefix of the stack (each lane head in order,
   the fold commit with the last), not only on its tip: a train can land partly, so each prefix must hold alone.
   Lanes whose prefix fails only because a later lane completes it name each other: they land together, in one
   train, never split by a partial landing; any other failing prefix bounces like a red gate.
   Gate: ONE run on the final stacked tree, before the merge, in the worktree of the stack tip:
   the project's gate in pre-merge mode, reusing the lane receipts (project-wiring "the project gate") — every tree step on exactly the tree that lands, the
   full gate's budgets and suite selection (never the changed-files mode); the mutation step reuses the testers' receipts and
   re-runs only what the rebase changed. With the runner on (OR-32) it runs there:
   through the project's runner command (project-wiring "remote runners"); with the runner on, its command not
   configured on this machine or not reachable: STOP the train and report, never a local gate; with the runner off,
   the gate runs locally. Steps that check the deployed instance run after the merge, in the main
   checkout (the gate's deployment steps, when the stack plug-in has such steps). When the train touches the gate
   itself, the gate's self-test runs with the train gate (its tree cases, on the runner when configured; one planted
   defect per step, each caught) and its deployment cases run in the main checkout right after the deployment
   steps.
7. Merge in order, pinned to the gated head: GitHub `gh pr merge <n> --squash --match-head-commit <full sha>`; GitLab
   `glab mr merge <n> --squash --sha <full sha>`. Never let the forge delete a branch whose worktree holds live
   state (OR-18). After each merge move the next branch with `git rebase --onto origin/{{BOA_MAIN_BRANCH}} <previous
   lane head> <next branch>` and check its tree equals the gated one. Never chain cleanup after a merge command
   without checking the PR state first. With no forge (`BOA_FORGE=none`): no PR/MR is opened; after the one gate the integrator fast-forwards the local main to the gated tip (`git -C <main checkout> merge --ff-only <gated tip>`, never a push), checks that main's tree equals the gated one, and records each lane's landing commit (its head SHA on main) in place of a PR number (the plan row's status `DONE`).
7b. **Drafts are never consumed:** `memory_write.py --ingest` never modifies or deletes a draft. A lane's drafts
    (`.lane-resume/memories.md`) disappear with its worktree, which is removed only after the lane's fold has
    landed; the lead's staging files keep the fold marker the lead writes once the fold is on main, which is the
    record —
    `--ingest` reads a staging file only below its last single-`#` `Folded by` marker. The fold boundary is
    recorded, never guessed: `memory_write.py --ingest` emits an ingest receipt naming, per staging file, the
    ingested prefix of the file (lines 1..N and the sha256 of that whole prefix); once the train's fold commit is on
    main the lead runs `memory_write.py --mark <receipt> --train TRAIN-NNN`, which inserts the single-`#` `Folded by
    TRAIN-NNN` marker immediately AFTER line N (refusing when the prefix hash no longer matches), never at the end
    of the file, so lines appended
    after the fold (during the gate) stay below the marker. The receipt lives with the train (the integrator's
    report and the lead dir), not in the memory bank.
8. Red gate → bisect over the lane heads with only the failing steps (the gate's failing steps only, at each
   head); bounce the first breaking lane (builder → reviewer delta → tester), REBUILD the train's single `docs(memory)`
   commit from scratch without it (re-ingesting the staging files and the remaining lanes in the new order; ids from the
   discarded fold never existed) on top of the re-stacked rest, gate again.
   A failure caused by main itself (a new dependency advisory, an upstream change) is a **red-main fix task**
   (critical path), never a lane bounce. Combination effects (an interface one lane changed and another's tests use):
   the builders grep main for callers of every signature they change; the gate on the stack catches the rest.
9. Per lane (A merged lane whose fold has not landed (a partly landed train) keeps its worktree — at least
   `.lane-resume/memories.md` — until its fold is on main: it is not cleaned; it is recorded in the residue register
   with owner = the lane's own task (`T-NNN`) and the removal step "after the next train's fold lands" and listed as
   "merged, fold pending" in the report and at a pause.):
   the project's residue check for the lane (project-wiring "deployed-instance objects") must pass; then `.boa/bin/lane-worktree.sh remove <T>` (or
   `git worktree remove <wt>`), `git branch -D <branch>`, `git push origin --delete <branch>`, `git worktree prune`.
10. Main checkout: fast-forward only (`git -C <main> pull --ff-only`); never `reset --hard` or `clean` it (it holds
    the lead dir, logs and local secrets). If the train changed the project's git hooks, re-install them from the
    main checkout (project-wiring "git hooks").
11. Also at every train: the correspondence check (§26: `python3 -I .boa/tools/trace_check.py`, its result in the
    report, every new mismatch a task or a ledger item at once), the duration review (§15), the guard and permission
    log review (§11), disk (§10), the
    transit queue open-items.md emptied into the plan (OR-25), the metalearning inbox (§16).
12. Report: merged PRs, gate result, durations, residue, disk delta, newly unblocked tasks; registry line
    `TRAIN-<n> … merged`.

## 8. HITL
- Only for owner decisions (OR-12): product/business, legal/IP, spending money, destructive actions outside the
  repository, shared-environment changes, a genuine fork with no objective winner, the loop guard (§6).
- Ask with 2–4 options, the recommended one first and marked "(Recommended)", each self-contained (what happens,
  pros/cons). Use the runtime's question tool when it has one (capabilities record).
- Unknown → ask (OR-12): whatever an agent cannot know or decide, it does not guess; sub-agents report the
  question to the lead with alternatives and a recommendation, and keep working on the rest.
- Record it in the registry and in active-context "Open HITL" (with the recommendation); keep working on
  everything it does not block; act on the answer only when it comes (or when the rules allow).

## 9. Talking to the owner
- Reply in {{BOA_REPLY_LANGUAGE}}, plain and short; explain jargon before the owner has to ask.
- A status question → first line: DONE on main / total tasks (%), work-weighted %, how many lanes are tested and
  waiting to merge (OR-15). Lane detail only on request.
- Report outcomes faithfully, failures included; never claim more than the evidence shows.
- Relay review findings in plain terms (what would break, for whom), not as raw finding lists.

## 10. Disk duties (OR-08)
- Check the project's disk snapshot and alert (project-wiring "measure commands") around heavy steps and at every
  train; report trend + action.
- Clean only what is provably ours: worktrees of closed lanes, lane-labelled / lane-named containers, registered
  residue at its removal step. Never a global prune; shared build cache is reported as unattributed and pruned only
  by explicit record id after proof (§11 override). Thresholds: {{BOA_DISK_WARN_MB}} MB warning,
  {{BOA_DISK_HARD_MB}} MB ceiling, plus the project's per-area limits.
- Lanes stay lean: sparse worktrees and hard-linked dependency copies where the stack plug-in supports them.
- On an alert the lead notifies the owner through the configured channel (webhook or chat bot, set in a machine-local
  config, never in the repository), or — when none is set — writes the alert prominently into
  `active-context.md`; then clears the marker once the project's own leftovers are cleaned.

## 11. Safety layer
- **Guard hook** `.boa/hooks/guard_destructive.py` (on the runtime's pre-tool event for its shell, file-write
  and file-read tools: the matcher is in the runtime's profile, checked per OR-63; wired in the runtime's hook settings). It reads each command with a shell lexer
  (`.boa/hooks/shell_lexer.py`: quotes, substitutions, heredocs, redirections, wrappers such as `sudo`/`env`/`nice`/
  `timeout`/`xargs`) and denies, among others:
  - deletions outside the scratch root, the project's own temp prefix and worktree subpaths; `..` in delete paths;
    the whole scratch root; symlinks that resolve elsewhere; the main checkout's protected dirs (`memory-bank`,
    `.env*`, `.boa`, the runtime's own configuration named in `BOA_RUNTIME_CONFIG`, the lead dir, logs); `.git`
    anywhere;
  - **sub-agent writes** (redirections, `mv`/`cp`/`tee`/`ln`/`install`/`rsync` destinations, `sed -i`, `dd of=`, the
    file-write tools) outside their own lane worktree, the scratch root and the project's temp prefix; **everyone's**
    shell writes to `<main>/.boa/`, `<main>/.env*` and the runtime's configuration (`BOA_RUNTIME_CONFIG`; the lead uses
    its file tools or the override);
  - a sub-agent touching **another lane** (bound by the agent binding, `.boa/hooks/agent_binding.py`, to the first
    task id of its sub-agent spawn's description; the integrator may act on any lane; an unbound agent stays confined to the
    lane worktrees, its destructive commands there noted in the log);
  - `/dev/*` as an `ln`/`mv`/`install`/write target, permission changes or mounts on `/dev`, `dd` to a device;
  - **other projects**: a sub-agent naming any path of another project (reads included), `cd` into one; for
    everyone, git write verbs on another project's repository;
  - the project's **protected commands** (`.boa/protected-commands.conf`, written at bootstrap as a project-wiring
    item: `<all|lanes> <program>[,...] <pattern> <reason>` per line): how the project protects its own resources
    (databases, containers, services, the deployed instance); the guard itself knows none of them. The agent fills
    the package-manager shapes of `references/safety.md` for every language and package manager the host uses, each
    with all its invocation forms (versioned name, interpreter module form, other front ends). An invalid file
    refuses every shell command until it is fixed (the BOA package's `references/safety.md`);
  - destructive git (`clean`, `reset --hard`, `checkout` of paths, `stash drop`) outside the lane; force-push or
    deletion of `{{BOA_MAIN_BRANCH}}`; sub-agent pushes to `{{BOA_MAIN_BRANCH}}`;
  - a sub-agent piping into a shell (`curl … | sh`); `pkill`/`killall`.
  - NOT in the guard: service managers, package installs, firewall changes and the forge's destructive commands are
    host protections the project registers in `.boa/protected-commands.conf` (example rules: the BOA package's
    `references/safety.md` "Host protections"); until it does, nothing refuses them.
- Denials are **non-blocking**: the agent gets the reason and adapts. Every denial is logged (time, agent, tool,
  the reason capped at 500 characters; the command line itself is not stored); `NOTE:` lines record allowed actions it could not fully verify.
- It is a **best-effort net, not a sandbox**, and it **fails closed** on an internal error, a timeout, a cutoff or
  unreadable input (OR-23, OR-40); its threat model is accidents, not attacks (product code is always reviewed and tested against real attackers). **Known
  limits** (documented, not chased): it cannot see inside scripts, `python -c`/`node -e` bodies, sourced files,
  aliases or anything run later (cron, git hooks, container entrypoints); command names or paths computed at run
  time are not resolved; a failed `cd` is assumed to have worked; writers it does not model are not write-checked;
  time-of-check races; after a parse failure a sub-agent command naming a checked program is denied, any other is
  allowed.
- **Testing the guard** (OR-24): only by feeding JSON payloads or inside a throwaway container, never by running the
  command on the host.
- **Log review** (OR-22, every train): read the denials and the permission requests since the last check,
  classify each as a near-miss or a false positive, fix false positives in the guard with a test case (a reviewed
  code change), note the result in the registry.
- **Lead-only override** (OR-39): a command that *starts* with `{{BOA_ENV_PREFIX}}GUARD_LEAD_VERIFIED=<single
  token, ≥ 3 chars> ` is allowed and logged as an override. Sub-agents can never use it; it does not work
  mid-command; a reason with spaces or quotes is not recognised. Use it only after proving the target is ours
  (creation inside the lane, no other users, our name or label), with the evidence in `<lead>/lanes.md`.
- **Heavy-run and wrapped-tool rules** (the project's protected-command rules, project-wiring
  "light and heavy suites" and "project protections"): role-blind (they apply to the lead too). The first refuses the stack's heavy
  commands locally when a runner is configured (§18); the second refuses the stack's mutation tool outside its
  wrapper (§24).
- **Pause guard** `.boa/hooks/pause_guard.py`: while `<lead>/PAUSE` exists, a sub-agent may only do the pause set of
  §13; everything else is denied.
- **Permission log** (project-wiring "permission log"): every permission prompt is logged (redacted), to find what still
  prompts.
- **Cleanup allowlist** (the runtime's permission settings, their format checked per OR-63): literal `rm` shapes under the scratch root
  and the worktrees dir, `git worktree remove/prune`, lane branch deletion (local and remote), removal of
  `{{BOA_NAME_PREFIX}}*` containers/networks/volumes; deny rules for `rm` with `..` and `rm -rf`
  of `/`, `/tmp` and the projects dir. Agents use exactly these shapes and never stall on a prompt (OR-11).
- **Git hooks** (OR-38, OR-41, OR-42): the project's hooks refuse pushes to `{{BOA_MAIN_BRANCH}}` (an exceptional
  escape is explicit, logged, fail-closed, its reason recorded through the progress staging), scan the staged diff
  for secrets, run `memory_lint.py --staged` (refusing a commit whose memory blocks have broken ids or links) and
  check the Conventional Commit format and trailers. The project's own hooks in the shared hooks
  dir of every worktree (project-wiring "git hooks"); prefer the forge's server-side branch protection where
  available.

## 12. Deployment operations (lead only, never from a lane)
The project's own instance (demo, staging) lives in the main checkout or its own host and is operated only by the
lead. After a train that changes what it runs:
1. back up its state (database dump into a git-ignored backup dir; secrets passed through the environment, never
   argv);
2. deploy: apply migrations, rebuild or restart only the affected services (never the others);
3. health check with an **expected answer** (e.g. the URL answers the expected status, the services are healthy);
4. record it in `<lead>/lanes.md` (and the deployment section of active-context when the URL or access changes).
A failing check after a merge is a deployment problem for the lead; the merge is reverted only when the merged
tree itself causes it. Lanes never start, stop, recreate or reconfigure it.

## 13. Pause and resume (`/pause-project`, `/resume-project`)
Pause (the owner asks to stop, e.g. a usage limit is ending):
1. The lead runs `.boa/bin/pause-flag.sh set "<reason>"`: it writes `<lead>/PAUSE` (time, reason). **The pause set:**
   from its next tool call a sub-agent may only: write its own `.lane-resume/<role>.md`; append (only) to its lane's
   `.lane-resume/memories.md`; run read-only git;
   `git add` / `git commit` in its own worktree; `rm` its own scratch subdir; `kill` its own PIDs (the cleanup needs
   the task: the agent binding, else the lane worktree's name); hand back its final report (the report tool call,
   neutral kind `report`, where the runtime delivers it so). Everything else is denied
   with the
   instruction to do exactly these and end its turn. The lead also messages every running agent "finish the atomic
   step, then stop" (an agent inside a long tool call sees the flag at its next call). **Integrator:** it stops BEFORE
   starting the next merge; a merge command already running completes; it never leaves a half-merged train
   unreported (its resume file states the stack state: which lanes merged and at which SHAs, which are stacked and
   gated, which are not).
2. A read-only role (reviewer, analyzer) writes no file: it ends with its state and its memory blocks in its final
   message (journaled verbatim) and the lead writes its resume file and appends its blocks from it. Each other agent
   appends any memory it still has as `--format-only` blocks to `.lane-resume/memories.md` (so the next
   fold ingests it), commits coherent work as `wip(<T>): …` (or leaves it uncommitted and says so) and writes
   `<wt>/.lane-resume/<role>.md` (git-excluded): task and goal, branch, head SHA, uncommitted work, every
   deliverable done/partial/not started with paths, what remains in order, every lead message received, open
   questions, commands to verify. Enough for a fresh agent with no memory. Then it cleans its scratch, leaves no
   processes, names in the resume file any other resource its lane started (containers, services: the lead removes
   them with the project's own commands) and ends its turn.
3. The sub-agent stop hook (`.boa/hooks/subagent_stop.py`) copies each resume file to `<lead>/lanes/<T>-<role>.md`
   and journals the stop as "paused" (it warns when no resume file exists: expected for a read-only role, whose
   resume file and lead-dir copy the lead writes from its final message, step 2). The lead's stop hook
   (`.boa/hooks/lead_stop.py`) renders the status screen as the marked block of `<lead>/RESUME-LEAD.md` (every byte
   outside the block kept); the lead stops the project's
   daemons; `RESUME-LEAD.md` lists every lane "merged, fold pending" (its worktree kept for the next train's fold). The
   lead appends the pause to `<lead>/lanes.md` and pushes the lane branches as a backup (no PRs).
Resume:
In another runtime, first: when the runtime you resume in is not one the capabilities record names, or its wiring is
absent, redo the capability self-assessment for this runtime (its latest official documentation and the installed
version) and wire it before you clear the flag or resume any lane. Do only what this runtime needs; leave the other
runtime's wiring untouched (never modify, move, regenerate or remove it unless the user explicitly asks; report what
looks stale), the two coexist. Add this runtime to the capabilities record and tell the user what it cannot enforce.
When the runtime that last worked on the project is not this one, set `BOA_SCRATCH_ROOT` and `BOA_SCRATCH_GLOB` again.
Until the wiring exists no hook reminds you: `AGENTS.md`'s read order is the only path to this step (a declared limit).
4. `.boa/bin/pause-flag.sh clear`, then §1; restart the project's daemons; `lead-status.sh` lists `RESUME-LEAD.md` and every
   `.lane-resume/<role>.md`.
5. If the session survived, apply §5.3 at the resume: a resumed paused round is the SAME round continuing, so it never
   counts toward the third-round trigger; the size trigger (the agent's context size past the LOWER of about half of
   the model's context window and `BOA_AGENT_FRESH_TOKENS`) and the wait trigger (the pause outlasted the cache
   lifetime) apply: a fresh agent when either holds, else the SAME agent (OR-16, message "resume from your resume
   file"); otherwise start NEW agents, each given its resume-file path plus the lead's notes since the stop. Resume files are removed with the
   worktree by the integrator (never committed).

## 14. Close-out
- **Milestone closure:** the full-scope mutation round on the delicate paths (the stack's mutation wrapper in its
  milestone mode, on the runner when configured), every suite tier, the residue check in closing mode, the secret
  scan of the tree (project-wiring "secret scanning"), freshness (§19), the duration review (§15), every row of the
  milestone DONE, the docs sweep (OR-74: a task that checks every user chapter against what landed; the release notes
  follow OR-73), the optional reviews the adopted rules ask for (UI, translations), then the tag.
- **Project end** (`/close-project`), in this order: (1) the close-out questionnaire (how the project ends: deploy
  target, leave in place, remote repository and visibility, CI, licence, hand-over, keep or uninstall BOA), recorded
  as an ADR; (2) the closing steps the owner chose, through the pipeline (uninstall excluded); (3) THEN the final
  checks: the secret scan of the tree **and the full history** (project-wiring "secret scanning"),
  every feature traced (`trace_check.py`), the docs sweep (OR-74), release acceptance, freshness, the final duration review, the
  whole plan DONE, the transit queue open-items.md empty and the pending folds at zero (OR-25), the correspondence check
  `python3 -I .boa/tools/trace_check.py --close` at **0 mismatches** (§26), the project's daemons stopped,
  the residue check in final mode = zero (the register empty), the final requirements review at zero open
  rows (below); (4) uninstall BOA LAST, only if chosen — the
  checks ran with the tools in place and the final report says so; (5) the final report.
- **Final requirements review** (OR-66; mandatory at milestone closure for the milestone's rows and at project
  end for all of them; an independent reviewer, never a lane's own). Walk every requirement (02 and the
  requirements ledger) and check, row by row:
  1. every indication the owner gave is a requirement row: 08 (the owner's own rules and product decisions), the
     pending owner-rules file, the owner decisions in 06, the owner's verbatim words quoted in 03;
  2. every planned task in 03 traces to a requirement, and every requirement to its tasks, all DONE;
  3. CODE, checked on its own: every shipped part against its requirement rows, its running tests and its handbook
     row;
  4. DISCIPLINE, checked on its own: every rule (08), procedure (09), agent contract, template and document against
     its requirement rows and against each other: no two say different things;
  5. each row ends `done` with its proving artifact and a test that ran, or open with an owner task (OR-25).
  Repeat the walk after the fixes; the project (or milestone) is not done until it reports zero open rows. The
  report lists the rows walked, the open ones and their tasks, and the contradictions found.

## 15. Duration control (OR-20)
Every agent must know this:
1. **What is measured:** for every gate run, the gate total, each step's wall time, every suite's time, exit status
   and timeout, the worker count and the load, appended by the project's gate to the timing
   ledger (project-wiring "suite timings and duration control") with the commit it ran on. The agent clock (§22) measures the agents' own time.
2. **Budgets:** the project's budgets file: a default per-suite budget (overrides each with a written
   reason; the duration target for OVER-BUDGET reporting, never a kill timeout), the run timeout cap
   (`run_timeout_cap_s`, §15 item 10), a budget per gate step, the gate total ({{BOA_GATE_BUDGET_S}} s), the trend window and regression
   threshold, the dominance threshold ({{BOA_DOMINANCE_PCT}} %), and the load limits that mark a run SUSPECT.
3. **When:** the project's timing check runs at the end of every gate (its `SUMMARY:` line closes the gate
   output), at every merge train (the integrator reports its table, even after a failed gate), at milestone closure
   and in the lead's train report.
4. **What the report says:** the gate total against budget and trend; each step against its budget and trend; for
   each **parallel** step its **critical-path suite** (the longest, which bounds the step's wall time) and its share
   of the step; every TIMED-OUT, OVER-BUDGET, REGRESSED or SUSPECT suite.
5. **The lead's question at every train: "can it be optimised?"** — a speed-up task is opened **at once** (plan row,
   not a note) when the gate total, a step or a suite is over budget, trending up, **or a parallel step is dominated
   by one suite above the threshold even under budget**. A step that is merely watched is how one suite comes to own
   it.
6. **Speed-up playbook:** measure where the time goes (per check, per external call, per process spawn) → change the
   expensive part (fewer spawns, shared fixtures, caching, parallelism, tiering of suites whose inputs did not
   change) → **prove identical coverage** (the same recorded call set before and after, the planted faults still
   caught) → before/after timings in the task's 05 entry. Budgets change only with a written reason.
7. **Never** re-run a suite to "confirm" a timing; loaded runs are labelled and excluded from the trend; no synthetic
   load (OR-05).
8. **Throughput review** (every train and when the work feels slow): the project's throughput review (project-wiring "usage clock and throughput") reads the clock
   ledger (lane wall time vs size, queue wait before trains, gate time per train, runner queue) and proposes
   remedies: more or fewer lanes, a remote runner or a bigger one, worker counts, tiering. Proposals that cost money
   go to the owner as a HITL with options.
9. **Speed never trades away coverage**: a speed-up that drops a check, a case or a planted fault is rejected.
10. **Bounded runs:** every test run and every planted-fault run runs under a timeout derived from that run's own
   recorded duration, never a fixed number: from the suite or case timings the project keeps (the gate's timing record,
   or the stack runner's), for example about three times the median of its recent runs, and never above the cap
   `run_timeout_cap_s` of the project's budgets file; a run with no history uses the cap itself. The suite budget
   (`default_suite_budget_s`) is the duration target for OVER-BUDGET reporting and is never used as a kill timeout. A
   planted-fault run uses the duration of the covering cases' clean baseline run (the run before the plant). A timeout
   is a failure, and for a planted fault that times out while a covering case is running it counts as killed by
   timeout, recorded as such, provided the clean baseline run finished inside the bound and the timeout is confirmed
   by a replay alone, unless the first run already ran alone (no other run active at any time during it): a replay of
   the plant alone, under the same timeout, times out too, while a replay that ends gives its own verdict; a timeout
   outside every covering case is confirmed the same way and is invalid, like a failure there; when the cap clipped
   the bound (the timeout derived from the clean baseline run is above the cap), a confirmed timeout is skipped, never
   killed or invalid: raise the cap; a plant whose clean baseline run is already over the bound is skipped (not run):
   raise the bound within the cap or narrow the cases, as for a mutant. A test that waits on a lock, a queue or the
   network sets its own short bound, never the product's long default. A hanging run is never repeated in the hope
   that it passes (OR-06): the cause is investigated. The replay alone of a timed-out plant is not such a retry: it
   confirms a kill, and a replay that ends points at contention (a shared lock, the host's load) as the cause to
   investigate.

## 16. Keeping the repository current between merges (OR-21, OR-25, OR-26, OR-35)
1. A new owner rule said in chat goes **immediately** into `<lead>/owner-rules-pending.md` as one memory block
   (type `constraint`, keyword `owner-rule`: the owner's words verbatim, "How to apply"), formatted with
   `.boa/tools/memory_write.py --format-only` (no id) and ingested at the next fold (§16.4). The runtime's own
   private memory is never used for project rules or memories.
1b. **Propagate at once** (OR-58): in the same step, send the new or changed rule to every running agent
   whose work it affects (what changes from its next step; done work is not redone), check each
   acknowledgement (a registry line), and put it in every later brief.
2. A new task or plan note the lead decides goes into `<lead>/plan-additions-pending.md` the same way (one block each;
   a new plan row is type `requirement` with the keyword `plan-row`, which the memory-types keyword route sends to 03;
   a requirement without it goes to 02).
3. Every merge train's `docs(memory)` commit folds both (new OR-IDs in 08 with the coverage table; rows in 03, with
   `plan_lanes.py --check` green) and updates the handbook and the agent contracts the fold touches in the same
   commit. **Only once the train's fold commit is on main** — never before, because a rebuilt fold must still see
   the lines — the lead marks each staging file (owner-rules-pending, plan-additions-pending, metalearning-inbox)
   with `memory_write.py --mark`; a partly landed train is not marked (the next train's fold covers its lanes and
   re-reads the same lines). The fold boundary is recorded,
   never guessed: `memory_write.py --ingest` emits an ingest receipt naming, per staging file, the ingested prefix
   of the file (lines 1..N and the sha256 of that whole prefix); once the train's fold commit is on main the lead
   runs `memory_write.py --mark
   <receipt> --train TRAIN-NNN`, which inserts the single-`#` `Folded by TRAIN-NNN` marker immediately AFTER line N
   (refusing when the prefix hash no longer matches), never at the end of the file, so lines appended after the
   fold (during the gate) stay below the marker. The receipt lives with the train (the integrator's report and the
   lead dir), not in the memory bank. The repository is never more than one train behind; `lead-status.sh` warns
   when a pending line is older than 24 h.
4. **Memory blocks (OR-50):** every new memory is one `@@@memory-<N> brief="…" datetime="…" keywords="…" type="…"` …
   `@endmemory` block, one fact, the most specific type of `.boa/memory-types.json`, task ids `T-NNN`, `datetime` from
   `date -u +%Y-%m-%dT%H:%M:%SZ` in exactly `YYYY-MM-DDTHH:MM:SSZ`, written ONLY through `.boa/tools/memory_write.py`.
   **Only the integrator's train fold assigns memory ids.** A train has ONE `docs(memory)` commit, the last commit
   of the stack (on top of the last lane, so it lands with the last lane's merge; if a train lands only partly, the
   next train's fold covers every lane whose fold has not landed, merged lanes included); in it the integrator runs
   `memory_write.py --ingest` ONCE, with all the staging files (`owner-rules-pending.md`, `metalearning-inbox.md`,
   any lead memories file) and every lane's `.lane-resume/memories.md` as one batch: the tool orders the blocks
   topologically (every `supersedes` target before its superseder), otherwise by datetime, with the staging-file and
   lane order only as a tie-break; then `memory_lint.py`.
   The lead never runs `--ingest`: it only writes id-less blocks to its staging files. On a red gate or a bounce the
   integrator rebuilds that single `docs(memory)` commit from scratch without the bounced lane (re-ingesting the
   rest in the new order) before re-gating. Ids are never reused on main: ids assigned in a discarded fold never
   existed.
   - **lanes** never write id-bearing blocks into memory-bank files: each agent formats its memories with
     `memory_write.py --format-only` (no id) into its lane's `.lane-resume/memories.md` and into its report;
   - **the lead** writes id-less blocks to its staging files only (never `--ingest`).
   Agents NEVER write `@@@memory-<N>` ids or `superseded-by` by hand: only `memory_write.py` assigns ids (only the
   integrator's train fold, with `--ingest`); a lane produces id-less blocks with `memory_write.py
   --format-only`, which may carry `supersedes="memory-N"` (an existing final id) or `supersedes-brief="<brief>"`
   (another new block of the same lane or batch); the fold's `memory_write.py --ingest` resolves them and stamps
   both directions atomically. The id ledger `memory-bank/.memory-ids.jsonl`, written only by the tool, makes a
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
   Nobody hand-edits ids or links; `Memories used:` cites final ids only (a lane's own new memories by their brief
   until the fold). Decision records are `ADR-NNN` (type `adr`) and `EDR-NNN` (type `edr`) in 06; a defect is a `bug`
   memory plus a task. The `pre-commit` hook runs `memory_lint.py --staged` and refuses broken links; the post-tool
   hook `.boa/hooks/memory_check.py` lints a memory file after every file write; the session-start status carries a
   three-line memory-writing reminder and the current memories for each active task id. A file with notes from before
   BOA keeps them above a `<!-- boa:memory-cutoff -->` line (legacy, exempt). Types, routes and recall moments: one
   file, `.boa/memory-types.json` (`.boa/tools/memory_types.py --check` validates it, `--render-tables` regenerates
   the doc tables).
4b. Metalearning: every report ends with a metacognitive trace (memory blocks); **lane lessons reach
   `memory-bank/10-METALEARNING.md` only through the train fold** (the lane's `.lane-resume/memories.md`, routed by
   type). The lead's `<lead>/metalearning-inbox.md` holds ONLY the lead's own notes and curations; a lead curation that
   improves a lane lesson **supersedes** it (`supersedes="memory-N"` once it has an id, `supersedes-brief` in the same
   batch), never copies it (each entry with the change it caused or "watch"; `.boa/tools/metalearning.py` checks the
   format and finds repeats). A lesson seen twice becomes a rule proposal (to the owner), a brief line or a tooling
   task.
5. The lane journal and the registry keep in-flight state current; `lead-status.sh` warns when a lane's newest journal
   entry is older than its worktree's last commit (someone worked without a recorded stop) or when a lane has commits
   but no journal entry.
6. `active-context.md` is refreshed at every train (the integrator edits the lines the lead names). `RESUME.md`
   stays a pointer file.
7. The handbook (OR-26): every tool, path or procedure change updates `docs/agent-handbook.md` in the same commit;
   `python3 -I .boa/tools/handbook_drift.py` fails on drift. The lead reviews the handbook as a whole at each
   milestone closure.
8. User documentation (OR-74): a change that alters what a user of the project sees updates the project's user
   documentation (the files the handbook's file map names) in the same change; the reviewer flags the missing update.

## 17. Lane hygiene
- Own scratch subdir only (`<scratch>/<T>-<role>/`); create it first and check it
  (`d=$(mktemp -d "$SCRATCH/x.XXXXXX") && [ -n "$d" ] && [ -d "$d" ] || exit 1`); `set -u` in helper scripts; suites
  keep their own temp dirs under the default `TMPDIR`. Never write at `/` or outside the worktree and the scratch
  subdir; never a bare relative path when the cwd may be `/`.
- Never a broad `pkill -f`/`killall`: kill only PIDs you started. Every wait loop has a timeout and is tied to your
  own PID or file.
- Throwaway containers (when the project uses a container engine): removed on exit, name
  `{{BOA_NAME_PREFIX}}<T>-<what>`, label `{{BOA_LABEL_KEY}}=<T>`; never the deployment's own project or its labels.
- Edit files with the runtime's file-editing tools, not with inline interpreters (`python3 - <<EOF`, `sed -i`, `perl -pi`): they
  trigger permission prompts that stall the lane. Helper logic goes in a script file run as `bash /abs/script.sh`;
  no compound `cd <main> && …`, no nested `bash -c '…'` quoting.
- Before editing any doc, contract, spec or agent text, grep the test suites for the ones that pin it and run them
  in the same change.
- Shell changes: run the stack's shell lint (shellcheck and the pipefail lint where the stack has them) on the
  changed files.
- Heavy suites run as the project's test-execution decision says (where, serial or parallel, how many at once:
  project-wiring "light and heavy suites", recorded in the capabilities record); while a train gate runs, lanes run
  only light work.
- Ad-hoc suite runs never set the gate's own environment flag (`{{BOA_ENV_PREFIX}}GATE`, set only by the gate): it
  turns a suite's skips into failures.
- A worktree may hold copied gitignored state (local secrets, credentials, dependency copies): it disappears with
  the worktree, so at integration the worktree directory is deleted **entirely** (`lane-worktree.sh remove`, then
  check the directory is gone) after any live state was handed over (OR-18).
- Lanes never edit `memory-bank/active-context.md`; ADR and EDR numbers come from the lead; when a task is DONE its
  row gets
  `; DONE — PR #NN` **appended**, never rewritten.

## 18. Remote test runner and heavy runs (OR-32; `BOA_RUNNER={{BOA_RUNNER}}`)
- Wiring a runner always starts with three questions to the user, answered into the capabilities record, one entry per
  runner (how many runners, each dedicated or shared; with which projects and whose admission; how much of each this
  project may use): project-wiring "remote runners".
- With a runner: every heavy run (gate test steps, mutation, whole suites, container and database suites) runs as
  the project's runner command (project-wiring "remote runners"): it syncs exactly what git would commit (never ignored files, secrets or
  `.lane-resume/`; the stack plug-in `.boa/stack/` is versioned, BOA's tools are not and never go there: the gate's
  BOA checks are light static steps run locally from the main checkout's `.boa/tools/`), runs through the runner's allowlist, streams the output, returns the exit status and copies
  back receipts, logs and one timing record. With the runner on, its command "not configured" on this machine or
  "unreachable" (their own exit statuses, recorded in the handbook): STOP and report to the lead; never a local
  fallback. With the runner off, the gate and the heavy runs run locally. The runners' status is read at every train,
  each runner on its own; with several, the runner command picks the one with the most free capacity and skips a
  runner that is down, reporting it.
- The local guard hooks do not see inside the runner session: there the runner's allowlist is the guard.
  Agents never edit the runner config, never change its provisioning outside its planned task, never open a session
  to it by hand; its address and key
  live only in the runner config, never in a document, a brief or a log.
- Without a runner: heavy runs stay local, serial or parallel as the project's test-execution decision records
  (project-wiring "light and heavy suites"; the machine's measured load and `lead-status.sh` admission); when long test waves are expected or the throughput review shows lanes waiting on the
  host, the lead proposes a runner to the owner.

## 19. Freshness (OR-46)
At milestone closure, release and on demand: every pinned version (images, packages, actions, tools) checked online
against the latest stable (the stack plug-in's freshness check where it has one); zero outdated except documented
holds with a review date; updates are plan tasks.

## 20. Parity registration (OR-45)
Every task is registered in `docs/parity/features.toml`: a product task in its `[[feature]]` entries, any other in
`[not_features]` with a categorised reason (`tooling:`, `process:`, `documentation:`, `spec:`, …). Before DONE, a
real, running test names it in its header: `@covers-feature F-ID <T>`. Check:
`python3 -I .boa/tools/trace_check.py`. A task not yet in the plan block cannot be registered: the lead
registers it with the train that folds its plan row.

## 21. Clean-room and provenance (optional; refactor mode or an IP-sensitive project)
When the optional clean-room rule is adopted (08): spec-side tasks may read the original's readable artifacts and
write specs and goldens in their own words; build tasks never open the original; every handoff, PR body and 05
entry carries `Provenance: sources = <…>; forbidden sources used: <none | what and when>`; the integrator refuses a
merge without it; the contamination check (project-wiring "clean-room check") runs in every review and gate; an untrusted source archive is scanned
before anyone reads it. The protocol lives in `docs/clean-room.md` (written by the lead at bootstrap).

## 22. Clock
The project's clock (project-wiring "usage clock and throughput") records session and sub-agent runs; agents mark the
start and end of their run and of long steps and add an elapsed line to their report. Its report gives wall time
per task, role and phase; the lead uses it to refine
size estimates, the train cadence and the throughput review (§15).

## 23. Mode bootstrap and new work (run-project, first run)
- **Self-wire first (every mode):** BOA's agent and command files are runtime-neutral (a neutral header over a
  neutral body). Before the mode's work, the lead has them in its runtime's own format, each format checked in the runtime's
  latest official documentation and the installed version, never from memory (OR-63): (a) the agents as sub-agents,
  (b) the commands as the runtime's commands or prompts, (c) the hooks registered in the runtime's configuration, its
  events mapped to BOA's neutral ones, **report capture included**: the sub-agent-stop hook saves each agent's final
  report verbatim to the lane journal, plus the lead-stop and session-status hooks; (d) where the runtime lacks one
  of these, the closest faithful equivalent, decided under the capability self-assessment, declared and never faked,
  asked of the user when unknown; (e) what was wired is recorded in the capabilities record and the handbook. The
  formats per runtime are examples in the BOA package's `references/runtimes.md`. The lead re-does it when the
  runtime changes (§30).
- **Greenfield:** `IDEA.md` → 00 brief → 01 blueprint → specs and contracts (02, `docs/specs/`, `docs/api/`) →
  milestones in AGENTS.md §2 → the plan with lanes (03) → stack choice ADR when not given (latest stable, verified).
- **Brownfield:** analyzer fan-out (as many as the code base needs, one area each, read line by line) → 04
  architecture, 01 blueprint (`exists`), contracts reconstructed (02, `docs/api/`), 07 known issues → the owner
  confirms goals → plan. A plan the project already keeps under its own column names is not renamed: the agent adds
  those names as `aliases` of the plan columns in `.boa/markers.json`, safely: it edits a copy, checks it with
  `BOA_MARKERS` naming the copy (`BOA_MARKERS=<copy> .boa/bin/boa language check` in a POSIX shell; in the Windows
  command prompt `set "BOA_MARKERS=<copy>" && .boa\bin\boa.cmd language check`, then `set BOA_MARKERS=` to clear
  it; the same variable lets `.boa/tools/trace_check.py` preview the effect), then moves the copy into place and runs
  `.boa/tools/trace_check.py`, so its mismatches are real gaps, not naming.
- **Refactor:** as brownfield, then characterise current behaviour (tests or goldens) before any change, then the
  refactor plan from `IDEA.md`; the clean-room rule when the IP situation needs it.
- **Spec-side tasks precede build tasks** (OR-48): the plan carries, for every contract, the task that writes it
  (greenfield) or characterises it (brownfield/refactor: goldens of the current behaviour), and every build task that
  implements it depends on that task. A build task starts only when its contract is on main.
- Every later feature request enters the same way: spec and contract first, then plan rows (pending → fold), then
  lanes.
- **An existing project is no exception (OR-69):** after a brownfield or refactor bootstrap, every new feature and
  every later change enters as a plan row with its contract clauses first (the existing code it touches gets its
  clauses and goldens first), then the pipeline and a train; nothing is edited outside a lane.

## 24. Mutation testing (OR-29, OR-30)
- **When:** only on delicate code the task changed: security and authz, crypto, licensing and tokens, money and
  credit math, data access and queries, migrations, concurrency and locking, stream or session authentication,
  anything where a silent wrong result is costly. Trivial glue is not mutation-tested.
- **How:** only through the stack's mutation wrapper (a protected-command rule refuses the tool otherwise,
  project-wiring "project protections"): only the changed lines (against the merge-base with main), only the tests that cover them, niced, a
  wall-clock cap per batch and a total bound per call (the wrapper batches by itself; a single file over the cap is
  "scope too wide": narrow the covering tests, then report to the lead — only the lead raises a cap, for one run,
  with a written reason), **0 skipped mutants**, a control run that rejects false kills, receipts per file pinning
  what decides its verdict.
- **Host-aware slots:** the wrapper refuses to start (or waits and retries, when asked to) while the host's mutation slots are full
  (about 2 on a shared development host, about a quarter of the CPUs, at least 2, on a dedicated runner) and, on the
  development host, while a train gate runs; the train's own run has priority.
- **Thresholds** per risk class (06): default MSI ≥ 80 % and covered MSI ≥ 90 %; crypto, licensing, tokens and money
  ≥ 90 %. Survivors: killed with a better test, or ignored narrowly (one mutant, one line) with a written reason the
  lead approves, recorded in 05; an equivalence claim needs a proof (why no input tells the mutant from the
  original), not an argument.
- **Who:** the tester's run is the lane's only one; the builder and the reviewer run none; the integrator's train
  run reuses the testers' receipts and re-runs only files whose receipt no longer holds. The full scope runs only
  at milestone closure (§14), on the runner when configured.
- **Which tool:** the stack plug-in names it (`.boa/stack/plugin.env`); where no mutation tool fits the code (shell,
  infrastructure, configuration), the tester plants faults by hand and shows the suites catch each one.

## 25. Contracts (OR-48)
1. **Where:** APIs in `docs/api/` (OpenAPI or the stack's equivalent), schemas, protocols, formats, third-party
   behaviour and module interfaces in `docs/specs/`; all indexed in `02-SPECIFICATIONS.md` with version, consumers,
   compatibility rule, contract tests and the features they serve.
2. **Enforced by tests:** the gate lints API contracts; contract and golden tests fail when behaviour drifts;
   schema checks compare migrations with the schema spec; third-party compatibility suites run on every train;
   characterisation goldens pin existing behaviour before a brownfield/refactor change.
3. **Traceability:** feature (`docs/parity/features.toml`) → contract (02 index) → tests (`@covers-feature F-ID <T>`
   on the contract tests); `trace_check.py` measures it.
4. **A build task** implements a contract and cites it; a missing or ambiguous contract → the builder stops that part
   and reports a spec question → the lead opens or routes a spec-side task.
5. **A contract change:** an ADR in 06 stating the compatibility impact (who breaks, migration, deprecation window,
   version bump) → a spec-side task updates the contract, its changelog and its tests → only then the build tasks
   that depend on it. The reviewer treats an unannounced contract change as a blocker; a third-party contract never
   breaks silently (OR-13).
6. **A short idea (OR-70):** whatever the size of `IDEA.md`, all the specifications are derived before any build:
   requirements, contracts with their clauses, edge cases and acceptance criteria; each gap is a HITL (options and a
   recommendation) while the unblocked work goes on; never a guess.

## 26. Correspondence closes to zero (OR-49)
1. **The check:** `python3 -I .boa/tools/trace_check.py` cross-checks plan tasks ↔ contracts ↔ specs ↔ features ↔
   proving tests ↔ residue register ↔ transit queue (open-items.md) ↔ pending folds, and prints one line per mismatch plus a
   `MISMATCHES: <n>` total (exit 0 only at zero).
2. **The markers it reads** (keep them current in every task):
   - 03: the `Contract / spec` column of every task row (`C-<NAME>.<n>` clauses, `C-` ids, `SPEC-` ids, or
     `none: <category>` with acceptance criteria), the `Managed by` column, and the plan block's status;
   - 02: the contracts index between `<!-- contracts:begin -->` and `<!-- contracts:end -->` (ID, Version, Where,
     Consumers, Compatibility, Tasks, Tests, Features, Status) and every spec's `- Contracts:` and `- Tasks:` lines;
     each contract file's clause lines; 06's ADRs naming `C-<NAME> v<version>`;
   - tests: the header lines `@covers-contract C-<NAME>.<n> <task>` and `@covers-feature F-<ID> <task>`;
   - `docs/parity/features.toml` (features → tasks), the residue register in 04, `<lead>/open-items.md` (the transit
     queue: its open `- [ ]` lines, read only at close), the pending files (lines after the last fold marker).
3. **What must hold:** every task names contract clauses/a spec or declares `none: <category>` with acceptance
   criteria; every task lists its edge cases and has a `Managed by` owner; every named id exists; every contract defines clauses, lists tasks
   that exist and tests that exist and carry its header; every clause has a test that runs; a contract version after
   the first has its ADR; a contract is `closed` only when its tasks are DONE; every feature has a proving test; every residue row has an owner task and a removal step; no
   pending line older than one train.
4. **When:** at every merge train (the integrator reports it; new mismatches become tasks or ledger items at once)
   and at close-out, where it must be **0** or the project is not done.
5. **Modes and exit status:** the default (train) mode checks item 3. **`--close`** (close-out) = the train mode PLUS:
   every live task is DONE; every feature is DONE and traced by a running test; every contract's status is `closed`;
   the transit queue is empty (zero open `- [ ]` lines in open-items.md, owned or not); every pending fold is folded
   (no pending owner rule or plan row after the last fold marker); the residue register is empty (the project's residue
   check in final mode runs beside it); no bug memory is open. Exit 0 only at 0 mismatches, 1 otherwise, 2 on a usage error.

## 27. Memory recall (OR-51)
0. **Every memory tool, option and when to use it, and supersede-only** (a memory is never edited or deleted; a new
   one supersedes it; the default search shows the current ones, `--all` and `--chain` show the history): the BOA
   package's `references/memory-types.md`.
1. **When and what:** the table of `AGENTS.md` §14 — at task start or resume, on any error / failing test / refused
   command / surprise, before a decision, before a contract change, when reviewing or testing, when planning, at
   close-out — with the listed types first, through `python3 -I .boa/tools/memory_search.py` (current memories by
   default; the supersession chain on request).
2. **Then:** follow the memory or supersede it with a better one (`memory_write.py`); never silently ignore it. Nothing
   found and a non-obvious problem solved → write the memory.
3. **Cite:** every report carries `Memories used: <ids>` (or `none found`); the lead's briefs name the memories a
   lane must know (§4); the reviewer flags a report that ignored a memory it should have followed.
4. **Wired support** (where the runtime has the events; verified at every wiring, OR-63): the post-tool-failure hook
   `.boa/hooks/memory_recall.py` searches the memory for a failed tool call's error text and injects the matching
   gotcha/trap/lesson ids; the session-start status prints the current memories for every active task id; at a
   sub-agent's start, where the runtime injects context there, `.boa/hooks/memory_recall.py --session` gives the
   starting agent the memory reminder and every active lane's current memories (the agent→task binding lands only
   after the agent starts, so no hook can pick its own task then); a sub-agent gets its own task's memories through
   its brief (§4, mandatory). Discipline only: no runtime event marks a decision, planning or the
   close-out, and no shipped hook acts on a contract file's write (the post-write hook only lints the memory files); at
   those moments the agent searches itself (AGENTS.md §14). A BOA update has its own procedure (§30, docs/02
   "Re-installing and upgrading"). The review moment is served in part by the sub-agent start hook, and for the rest by
   the brief's "memories to know" (§4).
5. **The lead's own recall:** before planning or splitting lanes (outcome, heuristic, lesson), before a ruling (adr,
   edr, constraint, nogoal), and at close-out (deferred, goal, requirement, constraint — they must be closed or
   superseded).

## 28. Sub-leads and lead-only powers (OR-61)
1. **When:** the plan has disjoint streams (no shared hotspot, no producer/consumer pair across them) and the
   capability self-assessment found nested sub-agents. Unknown → ask the user (OR-12). A sub-lead runs as a
   sub-agent bound to its stream's task, never as a peer session (the guard would treat a session without an agent
   id as the lead, override included); the lead creates its lanes' worktrees and writes their registry lines from
   the sub-lead's stage reports.
2. **Brief** (template; fill the `<…>`): "You are a SUB-LEAD for the stream <name>: tasks <T-…>. You have the
   lead's tools and knowledge; follow `.boa/agents/sub-lead.md`, 09 and 08. Run your lanes (builder → reviewer →
   tester) within <n> of the global lane cap. Report to the lead: per lane, its stage, head SHA and verdict; every
   question you cannot decide; Leftovers. You never merge, never create tasks, never touch lanes outside your
   stream."
3. **One plan, one integrator:** every plan row names who manages it (`managed by`: the lead or a sub-lead); the
   registry records each lane's owning lead; tested lanes of every stream go to the ONE integrator queue, whose train
   order the lead sets.
4. **Lead-only powers** (never delegated): the plan and task ids, `managed by`, owner rules and HITL, the train
   order, the migrations hotspot (OR-62), deployment operations (§12), the guard override (§11), the main checkout.

## 29. Test evidence (OR-54, OR-55, OR-56, OR-53)
- **Both directions:** a fix comes with a test that fails on the unfixed code, for the defect's reason, and passes
  on the fix; the builder shows both results; a timing pin is shown slow on the old code first.
- **Real inputs:** code that consumes files another part produces has a case on the real files of current main,
  run every round.
- **Plants:** only the covering cases, each plant in its own scratch copy, independent plants in parallel up to the
  lane cap; a green clean baseline run first; whole suite once at the start and once at the end.
- **Budgets:** at the budget, stop and report the current state; the lead accepts, bounces or extends once.

## 30. Project wiring and measuring (OR-64, OR-07)
- At bootstrap the lead seeds one plan row per project-wiring checklist item (the BOA package's
  `references/project-wiring.md`) and works them under the pipeline; each adopts an existing tool where one exists.
- When the project changes (a new stack part, a new service, a runtime update), the lead re-walks the checklist and
  adds rows for what changed.
- Measuring (agent clock, disk, suite timings, residue, throughput) runs through the tools the project wired; their
  output is a standing item of every train and of milestone closure (§15); a problem it shows is a planned tooling
  task, never a note.
- What each project-wired capability must guarantee, whatever tool the project adopts for it (every row is binding
  even before its tool exists: apply it by hand until then, and say so in the registry):

| Capability | Guarantee | When | Who | Checked by |
|---|---|---|---|---|
| Config and environment facts | `.boa/config.env` written from the shipped template, every value valid; the facts the plan needs (OS, CPU, memory, disk, tools and versions, rights, lane cap) probed, never assumed | bootstrap; after a host or runtime change | lead | the install self-test; the capabilities record |
| Gate | one command runs every check, in order, on exactly the tree that lands; tiers for lanes; non-removable alignment steps (plan lanes check `plan_lanes.py --check`, correspondence, contract tests, requirements, memory lint, handbook drift, lane residue, mutation-scope coverage); each suite's case filter proven to select only what it names | every train (pre-merge, stack tip); lanes run targeted parts | integrator; tester for touched steps | a gate self-test that plants one defect per step, each caught, whenever the gate changes |
| Heavy-run refusal and runners | with a runner configured, heavy runs never run locally; with several runners a down one is skipped and reported; with the runner on, no runner reachable or its command not configured = stop, never a local fallback (§18); every suite classed light or heavy with a reason, reclassified from durations every train; runner status, thresholds and cleanup of finished runs read every train | every heavy run; every train | all; lead reviews | a role-blind refusal hook tested on payloads; the train report |
| Mutation wrapper | the mutation library runs only through the wrapper: changed lines, covering tests, caps, receipts, 0 skipped | every tester run; train reuse | tester, integrator | a refusal of the bare tool; receipts |
| Git hooks | nobody pushes to main (local refusal + server-side protection with consent); conventional commit messages; staged secrets and broken memory links refused | every push and commit, every worktree (shared hooks dir; reinstalled when a train changes them) | all | the hooks' own tests; the integrator |
| Secret scanning | an adopted, maintained scanner: staged diff, whole tree, full history | every commit; milestone closure (tree); close-out (tree + history) | all; lead at closure | the pre-commit hook; the close-out report |
| Clock | session and sub-agent runs recorded per task, role and phase; stage times visible against budgets | always (hooks); agents mark long steps | all; lead reads | the status screen; stage-budget flags |
| Disk watch | the project's own footprint only, per area, warning and ceiling thresholds, alert marker and notification | from session start to pause; around heavy steps | lead | the alert marker, read at session start and in the train report (§10) |
| Residue check | no unregistered leftover (containers, volumes, worktrees, branches, scratch, deployed-instance objects, runner runs) | each lane before DONE; milestone closure; close-out | integrator; lead | fails on any unregistered item |
| Suite timings and budgets | every gate run's total, step and suite times recorded; budgets, trend, critical path and dominance reported | every gate; every train; milestone closure | integrator reports; lead opens speed-up tasks | the train report (§15) |
| Throughput and cost | lane wall time, queue and gate time, tokens per agent run where the runtime exposes them; proposals (lanes, runner size) | every train; when work feels slow | lead | the train report; HITL for money |
| Permission log | every permission prompt logged, redacted | always | lead reviews every train with the guard denials | the registry note (§11) |
| BOA release check | the installed BOA version (the capabilities record) compared with the newest release of the channel it came from; a newer one becomes a plan row `chore: update BOA to vX.Y.Z`, run outside a train by the update procedure (the BOA package's `docs/02-install-and-wiring.md` "Re-installing and upgrading"); never an update in the middle of a train; no network: said, checked at the next closure | milestone closure; close-out; when the user asks | lead | the capabilities record; the plan row |

## 31. Languages (OR-65)
- At bootstrap the lead detects the user language (or asks it) and records the product language (default English)
  and the user language in 08.
- Conversation, memory content and the free text of reports, plans and notes: user language. Code, comments, docs,
  commit messages: product language. Memory syntax: always English.
- A product-language change: the lead runs `boa language set <lang> --texts <file>` FIRST (the file: every entry
  of `.boa/markers.json` translated by the agent, corrected by the user if he wishes); the tool refuses a missing
  translation, self-checks every hook on samples written in the new language (the report capture with its Leftovers
  section, the review classes, the fold marker, the plan columns), keeps English as an alias and regenerates the
  marker-bearing sections of the installed files (then copy `.boa/agents` and `.boa/commands` into the runtime
  again, its format checked again per OR-63; the plan columns' `aliases` stay as they are, never translated); reports
  stay English until the self-check passes; then the product follows the new language. The memory
  syntax is never a marker and never translated.
<!-- boa:markers:begin keys=section.leftovers,leftovers.none,review.blocking,review.non_blocking,fold,plan.contract_column -->
  Machine-recognised words (`.boa/markers.json`, product language `en`; the English texts are always accepted too): section.leftovers = `Leftovers`; leftovers.none = `none`; review.blocking = `BLOCKING`; review.non_blocking = `NON-BLOCKING`; fold = `Folded by`; plan.contract_column = `Contract / spec`.
<!-- boa:markers:end -->
