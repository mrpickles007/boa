# 14 Contract-driven development

BOA builds **contracts first, code second, contracts enforced by tests** (rule OR-48 of the
[rules pool](../references/rules-pool.md); the reference: [references/workflow.md](../references/workflow.md#contracts-contract-driven-development)).
Contracts are the backbone of the whole discipline, not a phase.

## What a contract is

A contract is the written, versioned description of an external surface, precise enough that a builder and a tester
agree on it without asking. Every external surface gets one before it is built:

| Surface | Typical form |
|---|---|
| APIs | OpenAPI, AsyncAPI, protobuf or the stack's equivalent, with error models and limits |
| data | schema specs: tables, columns, keys, invariants, the migrations policy |
| protocols and file formats | the format, its versions and its compatibility rule |
| command-line or user-interface behaviour third parties rely on | flags, outputs, exit codes, visible behaviour |
| interfaces between modules | the calls, their inputs, outputs and failures |

A task with no external surface states its contract as checkable acceptance criteria in its plan row. Third parties
that depend on a contract are named in it.

## Where contracts live

In the repository, versioned, as the source of truth: `docs/api/` and `docs/specs/` (or the project's contracts
directory), indexed in `memory-bank/02-SPECIFICATIONS.md` between `<!-- contracts:begin -->` and
`<!-- contracts:end -->`, one row per contract: id `C-<NAME>`, version, where, consumers, compatibility rule, tasks,
tests, features and status (`open` or `closed`).

## Writing a contract

A spec-side task writes the contract (greenfield) or characterises it from the code with goldens (brownfield,
refactor) before any build task that implements it; a build task starts only when its contract is on main. Each
contract is made of **clauses**: a line of the contract file that starts with the clause id, such as
`C-API.1: every response carries a request id` (a heading, a list item, a table row or bold text all work). The
traceability check reads the clauses, so every clause is defined once.

## Every task names its clauses

Every task, whether planned at the start or added later from a review, a leftover, your chat or a bug, names the
contract clauses it implements or amends in the plan's `Contract / spec` column before it is built (or
`none: <category>` with acceptance criteria when it has no external surface), and lists its edge cases. A new
requirement first amends or adds the contract (a spec-side step), then the build follows. The builder implements and
cites the clauses; a missing or ambiguous contract is a spec question, never a guess. The reviewer attacks the diff
against the clauses; the tester maps every clause to a passing test.

## Testing contracts

Every clause has at least one test that runs and carries `@covers-contract <clause> <task>` in its header. Contract
tests pin behaviour: API contract lint in the gate, contract and golden tests that fail when behaviour drifts,
characterisation goldens for existing behaviour (preserve behaviour, not the legacy shape), schema checks, and
third-party compatibility suites where clients depend on the contract, so nobody breaks them silently.

## Amending a contract

Changing a contract is an explicit decision: a decision record stating the compatibility impact (who breaks, the
migration path, the deprecation window, the version bump), then a spec-side task that updates the contract, its
changelog and its tests together, then the build. A version after the first is named by its decision record
(`C-<NAME> v<version>`); the traceability check refuses a new version without one.

## Tracing and closing

`trace_check.py` checks the relations at every train: every task names its clauses (or `none:` with acceptance
criteria), every clause it names is defined, every contract lists its tasks and they name it back, every clause has a
running test, every contract test names a known contract and one of its tasks, and every feature traces to its tests.
Milestone closure and close-out re-run every contract test, and `trace_check.py --close` requires every contract
`closed` (implemented, tested, signed off) and zero open clauses; the final requirements review walks the contracts as
well as the requirements ([08 Measuring](08-measuring.md#traceability)).

## Edge cases

Every plan row lists the edge cases its task must handle (boundaries, empty or oversized input, concurrency, failure
and retry, permissions, time and locale, partial failure), or `none, because ...`; the reviewer attacks them and the
tester maps each to a running test, like a clause.
