# 03 — Implementation plan (the work queue)

> Every task runs through builder → adversarial reviewer → tester → integrator (`AGENTS.md` §6). Living plan:
> expand, split, reorder — but never work off-plan. New work (new features included) gets a task id
> (`T-NNN`), milestone, acceptance criteria, dependencies, size, lane and hotspots before it
> starts. Keep ids stable (never renumber); a split parent keeps its row with `; SPLIT into <ids>` appended.
> Task ids: `T-` and at least three digits, no upper limit (after `T-NNN` comes `T-NNNN`), assigned by the lead only,
> never reused; the number means nothing (milestone and area are columns of the row).
>
> **Task status:** `TODO` · `BUILD` · `REVIEW` · `REVIEW-DELTA` · `TEST` · `INTEGRATE` · `BLOCKED` · `DONE`
> (`DONE` = merged on a green main by the integrator, worktree cleaned). When a task is DONE the integrator
> **appends** `; DONE — PR #NN` to its row and sets its ledger row; row text is never rewritten (suites may pin it).
>
> **Sizing rule.** One task = one coherent slice that can be reviewed and tested on its own (one module or one part
> of a module, clear acceptance); target a few hundred changed lines of production code, delicate paths smaller.
> Do not split below the fixed per-task overhead (agent context, PR, the train gate): no single-function tasks.
>
> **Parallelism.** After the mode bootstrap the lead re-plans for parallelism (`AGENTS.md` §6bis step 0): the
> dependency graph, the lanes, the shared-module hotspots that must be serialized. The machine block below is the
> source of `python3 -I .boa/tools/plan_lanes.py` (eligible tasks = wave 1, critical path, progress); after any plan
> edit `python3 -I .boa/tools/plan_lanes.py --check` must stay green.

## How to pick the next tasks (fill the lanes)
1. `python3 -I .boa/tools/plan_lanes.py`: wave 1 = eligible now (deps DONE). Tasks of the same wave that share a
   hotspot run in one lane, never in parallel.
2. Spec-side before build-side (OR-48): a build task depends on the task that writes or characterises its contract.
3. Product tasks first; tooling tasks when they unblock product work or are planned like product tasks.
4. Admission: up to the lane cap ({{BOA_LANE_CAP}}), recalibrated to the machine (`lead-status.sh` shows it).

## Tasks

Each row: id, title, milestone, **contract / spec** (parsed by `trace_check.py`, 09 §26: the contract clauses
`C-<NAME>.<n>` the task implements or amends, the whole contract `C-<NAME>` for the spec-side task that writes it, and
the `SPEC-` ids, comma-separated; or `none: <category>` for a task with no external surface — `tooling`, `process`,
`documentation`, `environment`, … — whose acceptance criteria are then its contract), acceptance criteria, **edge
cases** (boundaries, empty or oversized input, concurrency, failure and retry, permissions, time and locale, partial
failure, hostile input — or `none, because …`), **managed by** (`lead`, or the sub-lead that runs the task; never
empty), deps; the machine columns are in the block below. The tools find the contract, acceptance, edge-case
and managed-by columns by their header names (`.boa/markers.json`, where a plan's own names are added as aliases). A new feature enters as spec-side task(s) plus build task(s) that depend on
them (OR-48).

| ID | Title | MS | Contract / spec | Acceptance criteria | Edge cases | Managed by | Deps |
|----|-------|----|-----------------|---------------------|------------|------------|------|
| T-001 | <first task, written by the lead at bootstrap> | M1 | <C-….n / SPEC-… / none: process> | <checkable criteria> | <cases, or none, because …> | <lead or sub-lead> | — |

## Plan block (machine-readable; read by `plan_lanes.py`, `trace_check.py`)

Columns: `ID` · `Size` (S/M/L; XL = split it) · `MS` (milestone) · `Deps` (comma-separated ids or —) · `Del`
(delicate: Y/N — mutation-tested) · `Heavy` (Y/N: needs the runner or the heavy-step semaphore) · `Lane` · `Hot`
(hotspots, comma-separated, or —) · `Status`. A closing task of a milestone carries `Closing:` in its row title.

<!-- plan-lanes:begin -->
| ID | Size | MS | Deps | Del | Heavy | Lane | Hot | Status |
|----|------|----|------|-----|-------|------|-----|--------|
| `T-001` | S | M1 | — | N | N | L1 | — | TODO |
<!-- plan-lanes:end -->

### Status ledger
| ID | Status | Notes |
|----|--------|-------|
| T-001 | TODO | |

## Coverage checklist
Every item of the blueprint (01) and every spec (02) maps to at least one task; the parity inventory
(`docs/parity/features.toml`) traces each feature to its tasks and tests (`trace_check.py`). A gap here is a missing
task.

## Memories — plan rows and deferred work
<!-- Memory blocks of type requirement with the keyword plan-row (new plan rows) and type deferred (each names its owner task T-NNN) are appended here by `.boa/tools/memory_write.py` (`memory-bank/README.md` "Memory blocks"). -->
