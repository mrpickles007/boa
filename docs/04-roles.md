# 04 Roles

The role contracts ship as runtime-neutral files (`.boa/agents/*.md`: a neutral header, then the contract); the agent
converts them into its runtime's sub-agent format at bootstrap
([02 Install and wiring](02-install-and-wiring.md#wiring-boa-into-your-runtime)). The contract text is the binding
one; this chapter is the overview.

## Modus operandi

The installed `AGENTS.md` opens with the Modus operandi, the mood behind every rule: aim for perfection knowing it
will not always be reached, and therefore analyse everything every time: verify instead of assume, read the evidence
instead of trusting the report, check the whole and not only the part just touched, and ask "what did I not look
at?" before calling anything done. The lead, every sub-lead and every sub-agent read it first; every contract points
to it.

## The lead

The agent that runs the skill. It designs and measures; sub-agents execute. It plans and re-plans for parallelism,
fills lanes, writes each brief (with the task's contract clauses, edge cases, budget and the memories that matter),
routes work to the right model, relays findings and bounces, decides every technical question by the standards and
records it, asks you only for owner decisions, curates metalearning and keeps the memory bank current. It does not do
the builder, reviewer, tester or integrator work itself. Its live state lives in the lead directory, never only in a
session ([07 Memory and state](07-memory-and-state.md#the-lead-directory)). "Where are we?" is answered with the count
of tasks done out of the total, in one line.

## Sub-leads

Where the runtime allows recursive delegation, the lead may hand one stream of the plan to a **sub-lead**
(`.boa/agents/sub-lead.md`): it fills its own lanes (builder, reviewer, tester), relays findings and bounces and
reports every lane's state to the lead. It runs as a sub-agent bound to its stream (never as a peer session, which
the guard would treat as the lead); the lead creates its lanes' worktrees and writes their registry lines from its
reports. It never merges, never creates tasks and never touches lanes outside its stream. The lead keeps the plan and task ids, the owner rules and HITL, the train order, the migrations hotspot,
deployment operations, the guard override and the main checkout; one integrator lands everything.

## The sub-agents

| Role | Does | Never |
|---|---|---|
| analyzer | read-only deep analysis of an area (brownfield and refactor fan-out), reports with file:line evidence | changes code |
| builder | implements exactly one task from its contract clauses, with its tests; on a bounce changes only what the findings require and answers every finding | runs mutation testing or the full battery |
| builder-mid | the builder's contract, for simple, low-risk work only | touches a delicate path |
| reviewer | adversarial review: crafts failing inputs, attacks boundaries, error paths, concurrency, authorisation and injection; checks the diff against the contract clauses; classes every finding; names the delicate paths for mutation; delta re-reviews | rubber-stamps: a clean verdict says what was tried |
| tester | acceptance and contract clause to test map, the touched suites, static analysis, the lane's only targeted mutation run or plant rounds | bypasses review: a failure bounces to the builder |
| integrator | lands tested lanes as a merge train: rebase, `docs(memory)` commit, ONE gate, merge, cleanup, residue check | resolves a conflict that needs judgement |

Strict stage roles: each check runs where it belongs, once. Every agent works only in its own lane worktree and
scratch directory, enforced by the guard and the agent-to-task binding ([05 Safety](05-safety.md#the-role-aware-guard)).

## The model roster

Each role's model and effort are set in its agent header from `BOA_MODEL_FRONTIER` and `BOA_MODEL_MID`: builder,
reviewer and analyzer on the frontier model, effort high; builder-mid, tester and integrator on the model just below
it, effort high. BOA ships no default model: the agent picks both from the runtime's current model list, verified at
bootstrap, and confirms them with you. Only you change the roster. A temporary switch to another model happens only
after an agent actually stopped on a rate limit, never when merely close to it, and commit trailers always name the
model the agent really ran on.

## Model routing

Simple, low-risk build work (docs or comment fixes, tiny bounces such as a rename or a one-line fix, spec-side docs,
mechanical follow-ups) goes to builder-mid; anything delicate (the one list is in the installed `AGENTS.md`, section 6:
concurrency and locks, security and authorisation, crypto, privileged or remote execution, firewall, money,
third-party contracts, non-trivial new code) goes to builder; when in doubt, builder. The lead chooses for every task; builders design from first principles, with KISS, YAGNI and DRY in
balance.

## Reports

Every agent ends with a report the lead can act on: what was done, the files, the acceptance to test map, the suite
results, the decisions to review, open questions, residue and elapsed time, then:

- a `Leftovers:` section (or `Leftovers: none`), captured by the sub-agent stop hook into the transit queue
  ([03 The workflow](03-the-workflow.md#leftovers-and-the-transit-queue));
- a **metacognitive trace**: 2 to 5 lines on mistakes, surprises, what slowed the agent and what it learned about the
  way of working, as id-less memory drafts ([07 Memory and state](07-memory-and-state.md#metalearning));
- for a builder, one line per requirement row it owns.

The report is saved verbatim into the lane journal by the sub-agent stop hook, whatever happens to the session. The
machine-recognised words of a report (section names, the Leftovers label and its "none", review classes) come from
`.boa/markers.json`, so the capture works in any product language.

## The agent lifecycle

Every spawned agent's id is recorded per task and role. For every later round of the same task and role (a delta fix,
a delta re-review) the lead resumes the same agent with its context; new work always gets a new agent. After an
interruption the lead first harvests the agents that finished, then advances the lanes.
