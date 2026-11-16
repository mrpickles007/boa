# Workflow — how a BOA project runs end to end

> BOA (Build On Autopilot): "Constrict your code to be right." This reference is the overview the skill, the
> documentation set and the mode references point to. The binding, installed texts are `AGENTS.md` §6/§6bis and
> `memory-bank/09-OPERATING-PROCEDURES.md` (templates in `assets/templates/`); this file explains the shape and the
> reasons, and never contradicts them.

## The shape
```
/build-on-autopilot <mode> [idea-file]  →  assess + install + wire + self-tests
/run-project           →  mode bootstrap (once)  →  loop: lanes → pipeline → merge trains  →  … →  /close-project
/pause-project ⇄ /resume-project at any point (state persisted, hooks capture every agent's report)
```

- **The lead designs and measures; sub-agents execute.** The lead plans, briefs, routes, folds and reports; every
  stage of a task is a sub-agent with a focused context (builder or builder-mid, reviewer, tester, integrator;
  analyzers for reconstruction).
- **The pipeline per task:** builder → adversarial reviewer (full, then delta re-reviews until the exit rule: a
  round with no findings, or two consecutive rounds with no blocking finding) →
  tester (acceptance → test map, touched suites, the lane's only targeted mutation run) → integrator (merge train,
  one gate, main always green). Docs-only changes skip review. Loop guard after 3 failed attempts.
- **Parallel lanes:** one git worktree per task, a dependency graph with hotspots serialised, product first, an
  admission cap calibrated to the machine; shared work is done once (receipts reused by trains, tiny fixes absorbed
  by the lane that owns the module).
- **Merge trains:** 3–4 green lanes stacked on current main, ONE `docs(memory)` commit on top of the stack (plan,
  progress, the memory ingest,
  folds of pending rules and plan rows, metalearning, handbook), ONE gate on the exact tree that lands, merges pinned
  to the gated head, residue checked per lane, durations reviewed.
- **Memory that never forgets:** the memory bank (00–10, active-context, RESUME pointer), the lead dir (registry,
  journal, ledgers, pending files), the agent handbook; every new rule or feature enters through a pending file and
  is folded at the next train.
- **Measured:** the clock (per task, role, phase), the timing ledger and duration check (gate total, per step,
  critical-path suite of each parallel step, dominance), throughput proposals, disk watch, residue, parity
  traceability, guard and permission logs, the metalearning file (the clock, the timings, throughput, disk watch and
  the residue check are the project's own, wired from `references/project-wiring.md`).
- **Safe by default:** the role-aware guard (sub-agents confined to their own lane by the agent binding; the lead's exemptions only
  through a logged single-token override), the project's protected-command rules (heavy runs, wrapped tools), the
  pause guard, the cleanup allowlist, the project's git hooks (no push to main, secret scan, commit format).

## Mode bootstrap (detail per mode in `references/modes/`)
- **greenfield:** `IDEA.md` → brief → blueprint → **contracts and specs** → milestones → plan with lanes; the stack is
  chosen from the goals when not given (`references/stack-choice.md`).
- **brownfield:** analyzer fan-out reads the code line by line → architecture, blueprint, **reconstructed
  contracts**, known issues → the owner confirms goals → plan.
- **refactor:** as brownfield + **characterisation goldens** of current behaviour before any change → refactor plan
  from `IDEA.md`; the clean-room option when the IP situation needs it.

## Contracts (contract-driven development)
BOA builds **contracts first, code second, contracts enforced by tests** (rule OR-48 of `rules-pool.md`; installed
procedure: 09 §23 and §25; template: `memory-bank/02-SPECIFICATIONS.md`). The mode references point here.
- **What gets a contract:** every external surface — APIs (OpenAPI or the stack's equivalent), data schemas with
  their invariants, protocols and file formats, CLI or UI behaviour third parties rely on, inter-module interfaces.
- **Where:** in the repository, versioned, the source of truth: `docs/api/` and `docs/specs/`, indexed in 02 with
  version, consumers, compatibility rule, contract tests and the features they serve.
- **Plan order:** a spec-side task (write the contract in greenfield; characterise it from the code with goldens in
  brownfield/refactor) precedes every build task that implements it; a build task starts only when its contract is
  on main.
- **During the build:** the builder implements and cites the contract; a missing or ambiguous contract is a spec
  question, never a guess. The reviewer attacks behaviour against the contract. The tester maps every acceptance
  criterion to a contract test.
- **Enforcement:** API contract lint in the gate, contract and golden tests that fail on drift, schema checks,
  third-party compatibility suites (never break clients silently), characterisation goldens for existing behaviour
  (preserve behaviour, not the legacy shape).
- **Traceability:** feature → contract → tests (`@covers-feature`), measured by `trace_check.py`.
- **Change:** an ADR stating the compatibility impact (who breaks, migration, deprecation window, version bump), then
  a spec-side task that updates contract, changelog and tests, then the build.

## Who decides what
- The owner: product, business, money, legal, brand, irreversible actions, shared-environment changes, the model
  roster, the loop guard — asked with 2–4 options and a recommendation.
- The lead: everything technical, by the standards (first principles, KISS/YAGNI/DRY, built-in first), recorded as
  ADRs; model routing (builder vs builder-mid; when in doubt builder); lane admission; when to open speed-up tasks.
- Sub-agents: their task within their lane; they escalate, never ask the owner.

## Where each piece is specified
| Topic | Installed text | Package reference |
|---|---|---|
| Rules | `memory-bank/08-OWNER-RULES.md` | `rules-pool.md` |
| Procedures | `memory-bank/09-OPERATING-PROCEDURES.md` | `procedures.md` |
| Durations | 09 §15, AGENTS.md §11 | `duration-control.md` |
| Mutation | 09 §24, the tester contract | `mutation-testing.md` |
| Pause and resume | 09 §13, `/pause-project`, `/resume-project` | `pause-resume.md` |
| Close-out | 09 §14, `/close-project` | `close-out.md` |
| Merge trains | 09 §7, `integrator.md` | `merge-trains.md` |
| Runtimes and wiring | `AGENTS.md` "Wiring" | `runtimes.md` |

## Correspondence (trace_check.py)

The project keeps one correspondence that must reach **0 mismatches at close**: plan tasks ↔ contracts ↔
specifications ↔ features ↔ proving tests ↔ residue register ↔ transit queue ↔ pending folds.
`python3 -I .boa/tools/trace_check.py` prints one `MISMATCH <relation>: <detail>` line per gap and
`MISMATCHES: <n>` last; exit 0 only at 0. `--close` (close-out) also requires every live task DONE, every feature
DONE and traced, every contract closed, an empty residue register, an empty transit queue and no open bug; the project's residue
check in final mode runs beside it.

Markers it reads:
- **Plan (03):** every task row of a table with a `Contract / spec` column names the contract clauses
  `C-<NAME>.<n>` it implements or amends (the whole `C-<NAME>` for the spec-side task that writes it) and the
  `SPEC-…` specs (comma-separated), or `none: <category>` (a category of `trace_check.py`: tooling, process,
  documentation, environment, …) with its acceptance criteria as its contract; every row lists its `Edge cases` (or
  `none, because …`) and has a `Managed by` owner.
- **Specifications (02):** each `SPEC-…` id is defined in 02 or under `docs/specs/`; the contracts index sits between
  `<!-- contracts:begin -->` and `<!-- contracts:end -->` with the columns
  `ID | Version | Where | Consumers | Compatibility | Tasks | Tests | Features | Status` (status `open|closed`;
  closed only when every task is DONE); a version after the first is named by an ADR in 06 as `C-<NAME> v<version>`.
- **Contract files:** each clause on its own line, starting with its id (`C-API.1 …`, `# C-API.1: …`).
- **Tests:** a contract test carries `@covers-contract C-<NAME>.<n> <task>` for every clause it proves in its file
  header (next to `@covers-feature F-ID <task>`); every clause has one; the Tests column lists it.
- **Features:** `docs/parity/features.toml`, checked by `trace_check.py` (the feature relation; `--report` prints the feature report).
- **Residue register (04):** every row has an owner task and a removal step; at close the register is empty.
- **Transit queue (lead dir `open-items.md`):** never a source of work (the plan is); at close no `- [ ]` line is
  left.
- **Pending folds (lead dir):** no `- ` / `## ` line after the last `# … Folded …` marker of
  `plan-additions-pending.md` and `owner-rules-pending.md` ("do not fold" lines excepted).
