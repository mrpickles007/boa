# 06 Rules pool

## What the rules pool is

[references/rules-pool.md](../references/rules-pool.md) holds the generic working rules (the owner rules) of BOA:
every one was proven in practice on a real project run by a lead agent and sub-agents, then reworded so it holds for
any project. Each rule states the **Rule**, **Why** (the failure it prevents), **How to apply** (what each role does),
**Applies to** and **Enforced** (where it is written down or checked in an installed project). Rule ids are `OR-NN`.
The rules cover how the work is done (reviews, tests, trains, budgets, plan and leftovers), safety (guards, pushes,
secrets, shared machines), memory and metalearning, contracts and correspondence, language and cost.

The whole working discipline is shipped in this generic form: every owner rule and operating procedure has a
generic home in the pool, `AGENTS.md`, the operating procedures (`memory-bank/09-OPERATING-PROCEDURES.md`) or the
agent contracts, with no project, person or runtime named.

## Adopting rules at install

The adopted section of the pool is copied verbatim into the project's `memory-bank/08-OWNER-RULES.md`, between its
`rules-pool` markers: that file is the complete index of the project's rules, read at every session start by the
lead and every sub-agent. The **optional** rules (for example the UI quality bar for a project with a user
interface, clean-room provenance for a project with an IP risk) are adopted by the lead at bootstrap when they apply,
by copying the block into 08 under "Optional rules adopted for this project".

## Adding and changing rules

You add your own rules during the project, simply by saying them. The lead writes each one down at once (your words
verbatim, the rule in the product language, the roles it binds, where it will be enforced) and it gets the next free
`OR-` id at the next fold. To adapt a pool rule, its wording in 08 is changed, never silently: the change is dated
and the old wording kept, marked superseded; or a project rule narrows it. A rule never goes away without your say.

## Pending and the fold

A new rule first goes into the lead's pending file (`<lead dir>/owner-rules-pending.md`), as one memory block of
type `constraint` with the keyword `owner-rule`. The integrator's next merge train folds it into 08 in its
`docs(memory)` commit, with the next free id, and updates the agent contracts, the operating procedures and the
handbook it touches; the repository is never more than one train behind. New plan rows follow the same path through
`<lead dir>/plan-additions-pending.md`, and the metalearning inbox through its own file
([07 Memory and state](07-memory-and-state.md#the-lead-directory)).

## A new rule reaches every agent

A rule written only into files is not propagated: running agents do not re-read their briefs. When you give or change
a rule, the lead, in the same step, records it, sends it at once to every running agent whose work it affects (what
changes from its next step; finished work is not redone), checks that each acknowledged it, and briefs every later
agent with it (rule OR-58).

## Optional rules

The pool ends with the optional rules and a sample domain rule, kept as a model for the project's own domain rules.
The lead adopts an optional rule when the project's mode or type calls for it, and records the choice as a decision.
