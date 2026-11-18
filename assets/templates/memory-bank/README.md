# Memory bank — protocol

This folder is the **persistent memory** of {{BOA_PROJECT_NAME}}. Agents start each session with no recollection
of previous ones; these files are the only continuity. The rules here are enforced by `AGENTS.md` §3.

## File map

| File | Purpose | Update cadence |
|------|---------|----------------|
| `00-PROJECT-BRIEF.md` | Immutable-ish north star: what, why, who, scope boundaries, hard constraints. | Rarely (scope changes only). |
| `01-BLUEPRINT.md` | Living map of **all** functionality (existing + target), with a verification backlog of `?` items. | Whenever functionality is discovered, added or re-scoped. |
| `02-SPECIFICATIONS.md` | Specs of new and changed features and the contracts of every interface (details in `docs/specs/`, `docs/api/`). | When a feature is specified or refined (before its build task). |
| `03-IMPLEMENTATION-PLAN.md` | The task backlog: every task with milestone, acceptance criteria, dependencies, lane, hotspots, status; the machine-readable plan block; the status ledger. | Continuously — this is the work queue. |
| `04-ARCHITECTURE.md` | Architecture, modules, stack, data model, third-party contracts, glossary, the **environment** in use, the **residue register**. | When structure or environment changes. |
| `05-PROGRESS.md` | Chronological log of what was actually done (per task, per stage), with dates. Append-only. | After every task stage / meaningful change. |
| `06-DECISIONS.md` | ADR log (choice, context, options, rationale, consequences, date). Append-only; numbers from the lead. | When any non-trivial decision is made. |
| `07-SECURITY.md` | Threat model, known vulnerabilities and their remediation, the standing security checklist. | When security facts change. |
| `08-OWNER-RULES.md` | **Binding.** Every owner rule (OR-IDs): the adopted rules pool plus the owner's own rules, with roles, how to apply and where enforced. | When the owner states a rule (via the lead dir's `owner-rules-pending.md`, folded at every merge train). |
| `09-OPERATING-PROCEDURES.md` | **Binding.** How the lead and the agents actually work: session start, live state, briefs, lanes, trains, HITL, disk, safety, deployment, pause/resume, close-out, durations. | When a procedure changes, in the same train. |
| `10-METALEARNING.md` | Curated lessons about the way of working, from every agent's metacognitive trace, each with the change it caused. | At every train (lead). |
| `active-context.md` | The single "where are we right now" file: milestone, lanes, Open HITL, blockers, next action. Short; history goes to 05. | Lead, continuously; the integrator edits only the lines the lead names. |
| `.memory-ids.jsonl` | The memory id ledger: one line per id `memory_write.py --ingest` assigns (id, file, datetime, brief, links). Written ONLY by the tool; a block whose id is not in it (a hand-written id) fails the lint, the post-tool hook and the pre-commit. | By `memory_write.py` only, never by hand. |
| `RESUME.md` | Pointer file: read order and where the live state is. Holds no state, so it never goes stale. | Only when the read order or a location changes. |

## The loop (what you MUST do)

**On session start**
1. Read `AGENTS.md` and `docs/agent-handbook.md`, then the runtime's own
   instruction file when it has one (it only points to `AGENTS.md`), then `RESUME.md`, then every file
   in this
   folder (08 and 09 are binding), then — the lead — the lead dir (`{{BOA_LEAD_DIR}}/`) and the status screen.
2. Open `active-context.md`. State in one line: active milestone, active lanes, next action.
3. If `active-context.md` is stale or empty, reconstruct the state from `05-PROGRESS.md`,
   `03-IMPLEMENTATION-PLAN.md`, `git log` and the lead registry, then rewrite it (the lead).

**While working**
4. Do only work that maps to a task in `03-IMPLEMENTATION-PLAN.md`. If it is not a task, add it first.
5. Run each task through the builder → reviewer → tester → integrator pipeline (`AGENTS.md` §6).

**On every meaningful change**
6. Record what changed, which task and the result as an id-less `--format-only` block (a lane: its
   `.lane-resume/memories.md`; the lead: its staging file); the next fold ingests it into `05-PROGRESS.md`. The lead
   updates `active-context.md`.
7. If design, scope or a choice changed, update `01`/`02`/`04` and/or write an ADR block for `06` (id-less, staged
   the same way) — now, not later.

**Before context runs low / before a compaction**
8. Flush everything durable here. Assume the session dies next turn: a new session reading this folder must be able
   to resume with zero loss.

## Memory blocks (OR-50)

Every new memory — a progress entry (05), a decision record (06: `ADR-NNN` type `adr`, `EDR-NNN` type `edr`), a
metalearning entry (10), a goal, a requirement, an invariant, a lead note, an agent's metacognitive trace — is
**one block** (active-context holds state lines that point to memory ids, not memories):

```
@@@memory-<N> brief="<one-line summary>" datetime="<YYYY-MM-DDTHH:MM:SSZ from date -u +%Y-%m-%dT%H:%M:%SZ>" keywords="<task ids T-NNN, components, tools, error words>" type="<type>"
<the full text of the memory, complete on its own>
@endmemory
```

- **Write memories only through `.boa/tools/memory_write.py`** (never by hand). **Only the integrator's train fold
  assigns memory ids.** A train has ONE `docs(memory)` commit, the last commit of the stack (on top of the last
  lane, so it lands with the last lane's merge; if a train lands only partly, the next train's fold covers every
  lane whose fold has not landed, merged lanes included); in it the integrator runs `memory_write.py --ingest` ONCE,
  with all the staging files (`owner-rules-pending.md`, `metalearning-inbox.md`, any lead memories file) and every
  lane's `.lane-resume/memories.md` as one batch: the tool orders the blocks topologically (every `supersedes`
  target before its superseder), otherwise by datetime, with the staging-file and lane order only as a tie-break;
  then `memory_lint.py`. The lead never runs `--ingest`: it
  only writes id-less blocks to its staging files. On a red gate or a bounce the integrator rebuilds that single
  `docs(memory)` commit from scratch without the bounced lane (re-ingesting the rest in the new order) before
  re-gating. Ids are never reused on main: ids assigned in a discarded fold never existed. Agents in a lane format
  their memories with `memory_write.py --format-only` (no id) into the lane's `.lane-resume/memories.md` and their
  report.
- Agents NEVER write `@@@memory-<N>` ids or `superseded-by` by hand: only `memory_write.py` assigns ids (only the
  integrator's train fold, with `--ingest`); a lane produces id-less blocks with `memory_write.py
  --format-only`, which may carry `supersedes="memory-N"` (an existing final id) or `supersedes-brief="<brief>"`
  (another new block of the same lane or batch); the fold's `memory_write.py --ingest` resolves them and stamps both
  directions atomically. The id ledger `memory-bank/.memory-ids.jsonl`, written only by the tool, makes a
  hand-written id fail the lint, the post-tool hook and the pre-commit.
- Supersession chains are always coherent: a memory is superseded at most ONCE (a single `superseded-by`); to
  replace a memory that is already superseded, supersede the CURRENT head of its chain (`memory_search.py --chain
  <id>` shows it); one memory may supersede several current memories (a merge); two memories superseding the same
  one (a fork) are refused by `memory_write.py` and by the lint.
  Supersession runs forward in time: a memory that supersedes another has a `datetime` strictly later (and a higher
  id) than every memory it supersedes; `memory_write.py` refuses a supersession whose stamped datetime is not later
  (a clock problem to fix, never a hand edit), and the lint reports any pair out of time order. `supersedes` may
  list several ids; the check is PER ID: each listed id must exist and be strictly older (an earlier `datetime` and
  a lower id).
- **Supersession:** a replacing memory names the old ones by final id, `supersedes="memory-12,memory-31"`; the writer
  stamps `superseded-by="memory-<N>"` on each superseded block's opening tag — the ONLY edit ever made to an existing
  memory. A memory is current while it has no `superseded-by`. Nobody hand-edits ids or links. `Memories used:` cites
  final ids only; a lane's own new memories are cited by their brief until the fold.
- **`datetime` is exactly `YYYY-MM-DDTHH:MM:SSZ`** (UTC, seconds, a literal `Z`), as `date -u +%Y-%m-%dT%H:%M:%SZ` prints
  it; never typed or guessed.
- **One block, one fact; the most specific type** of the types of `.boa/memory-types.json` (by default: lesson,
  gotcha, edgecase, constraint, contract, adr, edr, outcome, trap, heuristic, invariant, goal, nogoal, requirement,
  deferred, security, bug); `keywords` carry the task ids (`T-NNN`, at least
  three digits) and the words someone would search for; the text is complete on its own.
- **Checks:** `.boa/tools/memory_lint.py` validates every block (fields, the exact datetime format, the type, ids
  unique and progressive, every `supersedes` id exists, `supersedes` and `superseded-by` agree both ways, no cycles,
  no fork, every supersession forward in time);
  the `pre-commit` git hook runs `memory_lint.py --staged` and refuses a commit with broken links; the post-tool hook
  `.boa/hooks/memory_check.py` lints a memory file right after a file write of it; `.boa/tools/memory_search.py`
  finds memories by keyword, type, task id or date (current ones by default, the supersession chain on request).
- **Legacy cutoff:** in a memory file that already held notes before BOA (brownfield, refactor), the line
  `<!-- boa:memory-cutoff -->` separates them: everything above it is legacy and exempt from the checks; every
  memory below it is a block.
- Ledgers and registries keep their line formats (the plan block, the contracts index, the residue register, the
  transit queue open-items.md, the lane registry): they are not memories.

**Where each memory goes** (routing by type, generated from `.boa/memory-types.json`; `memory_write.py --ingest` picks
the file; staging files hold `--format-only` blocks until the fold; ids are one global sequence across all memory
files; the runtime's
own private memory is never used for project memory):

Each type's file is the `File` column of the types table; the keyword routes override it (any type, unless a route
names one). Each memory-bank file that receives memories has a `## Memories — …` section, under which
`memory_write.py` appends the blocks.

<!-- memory-types:begin -->
| type | What it records | Use it when | Must contain | File | Recall moments |
|---|---|---|---|---|---|
| `lesson` | something learned from experience that changes how we work next time | a mistake, a slow round or a surprise taught us a better way of working | what happened, why, what we do differently now | `10-METALEARNING.md` | error, plan |
| `gotcha` | a surprising behaviour of a tool, library, platform or environment that trips you even when you do things "right" | a tool did something unexpected (a flag needs a full SHA, a hook drops output in sub-agents) | the exact behaviour, how to recognise it, how to avoid it | `10-METALEARNING.md` | error |
| `edgecase` | a specific boundary input or state the code or the spec must handle | a review or test found an input at the edge (empty, max, encoding, race window) | the input or state, the expected behaviour, the test that pins it | `02-SPECIFICATIONS.md` | error, review |
| `constraint` | a hard limit imposed from outside that bounds every choice | the owner, a law, a platform, a budget or a compatibility promise fixes something | the limit, its source, what it rules out | `04-ARCHITECTURE.md` | start, decision, close |
| `contract` | an agreed interface or behaviour that other parts or third parties rely on (API, schema, protocol, file format, module boundary) | a contract is created, changed or clarified | the contract id and version, the surface, consumers, compatibility rule, where it lives | `02-SPECIFICATIONS.md` | start, contract-change, review |
| `adr` | an architectural decision record: a choice that shapes the system's structure (stack, module boundaries, data model, protocols, security model) | an architectural choice is made or reversed | context, options, the choice, who decided, why, consequences, what was rejected, status (proposed/accepted/superseded) | `06-DECISIONS.md` | start, decision, contract-change |
| `edr` | an execution decision record: a choice about how to carry the work out (implementation approach, process or operational call) — not architecture | the lead, owner or an agent chose how to do something | the options, the choice, who decided, why, what was rejected, whether it is reversible, the steps if it is a procedure | `06-DECISIONS.md` | start, decision |
| `outcome` | the factual result of an action, task, train or run | something finished (merged, deployed, measured) | what was done, numbers, ids/SHAs, where the evidence is — no opinion | `05-PROGRESS.md` | plan |
| `trap` | a tempting approach that looks right but leads to failure | a design or process idea failed, or would fail, for a non-obvious reason | the tempting idea, why it fails, the safe alternative | `10-METALEARNING.md` | error, review |
| `heuristic` | a rule of thumb that usually works | you found a reliable shortcut for estimating, choosing or prioritising | the rule, when it applies, when it does not | `10-METALEARNING.md` | decision, plan |
| `invariant` | a property that must always hold | a guarantee the system or process relies on is identified | the property, how it is enforced, the test or check that proves it | `04-ARCHITECTURE.md` | start, contract-change, review |
| `goal` | a desired result with success criteria | a milestone, task or project objective is set | the target, the measurable success criteria, the owner | `00-PROJECT-BRIEF.md` | close |
| `nogoal` | something explicitly out of scope | the owner or lead rules something out, to prevent scope creep | what is excluded, why | `00-PROJECT-BRIEF.md` | decision |
| `requirement` | something the product or process must do | the owner or a spec states a need | the requirement, its source, acceptance criteria, its id (e.g. R-NN) | `02-SPECIFICATIONS.md` | start, contract-change, close |
| `deferred` | something consciously postponed | work is moved later on purpose | what, why, the owner task (T-NNN), the trigger or date to revisit | `03-IMPLEMENTATION-PLAN.md` | start, close |
| `security` | a security-relevant fact: threat, weakness, control, secret-handling rule or security finding | a threat or weakness is found, a control is added or changed, a security review concludes | asset or surface, threat or weakness, control or mitigation, status, evidence or test | `07-SECURITY.md` | start, error, decision, contract-change, review, close |
| `bug` | a defect found in the product or the tooling (not a third-party tool's surprise: gotcha; not a boundary the spec must handle: edgecase) | a defect is found, reproduced or fixed | symptom, how to reproduce, root cause, fix (task T-NNN / commit), the regression test that pins it, status (open/fixed) | `05-PROGRESS.md` | start, error, review, close |
<!-- memory-types:end -->

<!-- memory-routes:begin -->
| Keyword | Type | Priority | File |
|---|---|---|---|
| `owner-rule` | any | 100 | `08-OWNER-RULES.md` |
| `plan-row` | any | 90 | `03-IMPLEMENTATION-PLAN.md` |
| `security` | any | 50 | `07-SECURITY.md` |
<!-- memory-routes:end -->

**Route precedence:** a keyword route wins over the type's own route; every keyword route carries an explicit
integer `priority`, and when a block matches several keyword routes the highest priority wins (defaults:
`owner-rule` 100 → 08, `plan-row` 90 → 03, `security` 50 → 07). Two keyword routes with equal priority are a
configuration error: `memory_types.py --check` refuses the file. Security goes to 07 whatever its type, except owner
rules (08) and plan rows (03), which keep the security keyword so search finds them (the security route yields to
the owner-rule and plan-row routes).

What each type is: the BOA package's `references/memory-types.md`; in short: `adr` = a structure-shaping
decision, `edr` = how the work is carried out, `contract` = an agreed interface or behaviour, `outcome` = a factual
result.

## Invariants

- **Code is truth.** If a memory file contradicts the code, fix the file.
- **No orphan knowledge.** Anything a future session needs goes in a file here.
- **Logs are append-only.** `05-PROGRESS.md`, `06-DECISIONS.md` and `10-METALEARNING.md` keep history as memory
  blocks; a block is superseded by a newer one, never edited or erased.
- **One fact, one home.** Put a fact in the most specific file; cross-reference instead of duplicating.
- **Dates on everything** in the logs (ISO `YYYY-MM-DD`). Compute the real date; never guess it.
