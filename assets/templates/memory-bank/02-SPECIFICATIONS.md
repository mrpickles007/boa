# 02 — Specifications and contracts

> **Contract-driven (OR-48): contracts first, code second, contracts enforced by tests.** Every external surface has
> a written, versioned contract in the repository before the build task that implements it starts; the contract is
> the source of truth. This file indexes every spec and contract and holds the short ones; detailed specs live in
> `docs/specs/<area>.md`, interface contracts in `docs/api/`. A build task that finds a contract missing or ambiguous
> raises a spec question (a spec-side task); it never fills the gap by guessing. Brownfield/refactor: the analyzers
> reconstruct the contracts of the existing code (cited `file:line`) and characterisation goldens pin them before
> any change.
>
> Spec ids are stable (`SPEC-<milestone>-<n>`). Each spec: goal, behaviour (inputs, outputs, errors, limits),
> the contracts it defines or uses, acceptance criteria, security notes, open questions.

## What needs a contract
| Surface | Contract form | Where | Enforced by |
|---|---|---|---|
| HTTP/RPC APIs | OpenAPI (or the stack's equivalent: GraphQL schema, protobuf, …) | `docs/api/` | contract lint in the gate, contract tests (requests/responses against the schema) |
| Data schemas | schema spec with every invariant (keys, uniqueness, nullability, ranges, ownership) | `docs/specs/schema.md` | schema checks (migrations against the spec), invariant tests |
| Protocols and file formats | message/format spec with examples and error cases | `docs/specs/` | golden tests (byte-for-byte or structural) |
| Behaviour third parties rely on (CLI, UI flows, outputs) | behaviour spec + goldens | `docs/specs/` | compatibility suites (OR-13), characterisation goldens |
| Interfaces between modules | interface spec (operations, pre/postconditions, errors) | `docs/specs/` | contract tests at the module boundary |

## Contract versioning and change (09 §25)
- Each contract carries a version and a changelog section. A change is an ADR in 06 that names the contract and
  its new version (`C-<NAME> v2`; `trace_check.py` refuses a version after the first without it) with its **compatibility
  impact** (who breaks, migration path, deprecation window) and a spec-side task that updates the contract and its
  tests before any build task depends on the change. Third-party contracts never break silently (OR-13).

## M1 — <milestone name>

### SPEC-M1-1 — <title>
- Goal: <…>
- Behaviour: <inputs, outputs, errors, limits>
- Contracts: <C-IDs it defines or uses>
- Tasks: <task ids: the spec-side task(s) first, then the build task(s)>
- Acceptance: <checkable criteria, each mapped to a contract test>
- Security: <threats and mitigations, 07 checklist items>
- Open questions: <…>

## Contract clauses
A contract is a list of clauses, each one checkable promise with a stable id `C-<NAME>.<n>`, written in its contract
file on its own line, starting with the id (`C-API.1 …`, `# C-API.1: …` in YAML, `### C-API.1 — …`, `| C-API.1 | …`).
Fenced code blocks and the Changelog section define nothing (a changelog entry starts with the version, never with the
clause id — `- 1.1: C-API.8 added` — since a line starting with the id ends the section and is read as a clause); a
clause id among the first three words of any other line is refused as a definition the check cannot read. Tasks name
the clauses they implement or amend; every clause has a test that runs with the header
`@covers-contract C-<NAME>.<n> <task>` (`trace_check.py` refuses an untested clause).

## Contracts index (parsed by `.boa/tools/trace_check.py`, 09 §26)
One row per contract, between the markers. **ID** `C-<NAME>` (capitals, digits, `-`; stable, never reused) ·
**Version** · **Where** (repository path of the contract file) · **Consumers** · **Compatibility** (`never break` |
`versioned` | `internal`) · **Tasks** (every task that writes, characterises or implements it, comma-separated) ·
**Tests** (repository paths of its contract tests; each carries the header `@covers-contract C-<NAME>.<n> <task>`) ·
**Features** (`F-` ids of `docs/parity/features.toml`, or `—`) · **Status** (`open` | `closed`: closed only when every
task is DONE, every test exists and carries the header, and the reviewer signed it off).

<!-- contracts:begin -->
| ID | Version | Where | Consumers | Compatibility | Tasks | Tests | Features | Status |
|----|---------|-------|-----------|---------------|-------|-------|----------|--------|
| `C-EXAMPLE` | 1 | `docs/api/example.yaml` | <who depends on it> | never break | T-001 | <tests/contract/…> | — | open |
<!-- contracts:end -->

## Memories — requirements, contracts and edge cases
<!-- Memory blocks of type requirement, contract (indexing the contract file) and edgecase are appended here by `.boa/tools/memory_write.py` (`memory-bank/README.md` "Memory blocks"). -->
