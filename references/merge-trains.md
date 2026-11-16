# Merge trains — landing many tested tasks with one gate

> Rules OR-04 (memory commit first, one gate) and OR-31 (3–4 lanes per gate) of `rules-pool.md`; installed procedure:
> 09 §7, the integrator contract, handbook §5.3. This reference is the design and the reasons: the gate is the most
> expensive step of the pipeline, so it runs once per train, on exactly the tree that lands, and `main` stays green.

## When a train leaves
- **3–4 lanes per train, ONE gate per train.** The lead holds a tested (GREEN) lane until three are green or the
  oldest green lane has waited the hold time (default 60 minutes).
- **Exceptions:** a critical-path lane (others wait on it) or a fix for a red main branch may go alone — or, cheaper
  when a train is about to leave, at the **bottom** of that train, so one gate covers all.
- **Hotspots** (shared modules) are serialised at planning time (`plan_lanes.py`), so two lanes of a train rarely
  touch the same logic.

## Stacking
With no forge (`BOA_FORGE=none`), read `origin/main` below as the local main and skip the pull, the fetch and every
push (the integrator contract and 09 §7 define that path).
1. Order: plan dependencies first, then by independence (independent, low-risk lanes first, a riskier lane last), then
   smallest and least conflicting; a red-main fix or a critical-path lane at
   the bottom.
2. Rebase every lane onto the **current** `origin/main` (a stale base wastes a gate), then stack: lane 2 onto lane 1,
   lane 3 onto lane 2, … (no merge commits).
3. **ONE `docs(memory)` commit for the train, on top of the stack** (the last commit, before any gate; it lands with
   the last lane's merge, so a train that stops part-way never leaves main claiming a lane DONE that did not land;
   the next train's fold covers every lane whose fold has not landed, merged lanes included): per lane the
   plan row's `; DONE — PR #NN` and ledger row, the progress entry, the active-context lines; the memory ingest (the
   only place memory ids are assigned: ONE `--ingest` batch of the lead's staging files and every lane's memories,
   ordered by the tool: supersession targets first, then datetime); the
   folds of the pending owner rules, plan rows and
   metalearning inbox, and the handbook when a fold changes a procedure or tool. Suites pin memory text, so the gate
   must test the exact tree that lands.
4. **Dependencies:** when the stack changes a lockfile under a lane's installed dependencies, the integrator
   refreshes that worktree's dependencies (the stack plug-in's install step) before gating; a gate on stale
   dependencies is not a gate of the tree that lands.
5. Open the PRs/MRs (the forge template's body).

## The gate
- ONE full gate on the stacked tip, the project's gate in pre-merge mode reusing each lane's receipts (project-wiring
  item "the project gate"): every tree step, the full
  gate's budgets and suite selection (never the changed-files mode), on the remote runner when one is configured (unreachable =
  stop the train, never a local gate).
- **Mutation is not re-run** where the testers' receipts still hold: only the files whose receipt no longer holds
  after the rebase run again (changed lines, covering tests).
- Steps that check the deployed instance run after the merge, in the main checkout.

## Merging
- In order, **pinned to the full head SHA** of each gated lane (`gh pr merge <n> --squash --match-head-commit <40-char
  sha>`; `glab mr merge <n> --squash --sha <sha>`); a short SHA is refused by the forge, and a failed merge must never
  be followed by a chained cleanup (check the PR state first).
- After each merge, move the next lane onto the new main (`git rebase --onto origin/main <previous head> <next>`) and
  check its tree equals the gated one — otherwise stop and gate again. After the last merge, main's tree equals the
  gated tip.
- Never let the forge delete a branch whose worktree holds live state (hand it over first).
- With no forge (`BOA_FORGE=none`): no PR/MR is opened; after the one gate the integrator fast-forwards the local main to the gated tip (`git -C <main checkout> merge --ff-only <gated tip>`, never a push), checks that main's tree equals the gated one, and records each lane's landing commit (its head SHA on main) in place of a PR number.

## When the gate is red
1. **Find the breaking lane:** bisect the stack (binary search over the lane heads) re-running only the failing steps.
2. **Bounce only that lane** (builder → reviewer delta → tester), drop it from the train, **rebuild the single
   `docs(memory)` commit without it** (re-ingesting in the new order; ids from the discarded fold never existed),
   **re-stack the others, put the rebuilt fold on top and re-gate**.
3. **A failure caused by main itself** (a new dependency advisory, an expired certificate in a fixture, an upstream
   image change) is not a lane's fault: it becomes a **red-main fix task** (critical path, may go alone or at the
   bottom of the next train), never a lane bounce.
4. `main` is never red: if a merged tree turns it red and the cause cannot be bounced cleanly, revert the merge.

## Conflicts
- The integrator resolves only **mechanical** conflicts: append-only logs and ledgers, lists where both sides add
  entries, whitespace, import order, non-overlapping hunks. Generated artifacts are regenerated, never hand-merged.
- Anything needing **judgement** (two lanes changed the same logic, an interface shape differs, unclear intent) goes
  back to the lane's builder with the hunks and both intents.

## Combination effects
A lane can pass alone, main can pass alone, and the combination still fail:
- **An interface changed by one lane and used by another's tests** (or code): builders grep the main branch — not
  only their own branch — for callers of every signature, contract or fixture they change, and update or report
  them; reviewers check it.
- **A lockfile bumped** under a lane's installed dependencies: the integrator refreshes the lane's dependencies
  before gating.
- **Shared fixtures, migrations or counters** (numbered files, ADR/EDR numbers): numbers come from the lead; memory
  ids are never taken in lanes at all — the integrator's fold assigns them (`memory_write.py --ingest`).
The one gate on the stacked tip is what catches the rest — which is why it runs on the stack, not per lane.

## After the merge (the train report)
Cleanup of worktrees and branches (local and remote) — except a merged lane whose fold has not landed, which keeps its
worktree (registered in the residue register under the lane's own task id, removal step "after the next train's fold
lands") until its fold is on main · residue check per
lane = 0 · main fast-forwarded in the main
checkout · the lead updates the deployed instance if the train needs it (then the deployment checks) · the newly
eligible tasks (`plan_lanes.py`) · the **duration check** (gate total, per step, critical-path suite of each parallel
step, dominance; per-step "can it be optimised?") · the **correspondence check** (`trace_check.py`) · the open items
the train closed · disk delta. The registry gets `TRAIN-<n> … merged`.
