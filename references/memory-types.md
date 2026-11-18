# Memory types and the memory block — how every memory is recorded and recalled

> Rules OR-50 (write) and OR-51 (recall) of `rules-pool.md`; installed in `AGENTS.md` §4 and §14,
> `memory-bank/README.md`, 09 §16.4 and §27. **The types, their routes and their recall moments come from ONE
> configuration file, `.boa/memory-types.json`** (shipped default `core/memory-types.json`): `memory_write`,
> `memory_lint`, `memory_search`, the recall hook and the session-start reminder read it, and every table below is
> generated from it (`.boa/tools/memory_types.py --render-tables`) and checked equal by a suite. Adding a type, a
> route or a recall moment means editing that one file. Tools: `.boa/tools/memory_write.py` (the only writer),
> `.boa/tools/memory_lint.py`, `.boa/hooks/memory_check.py`, `.boa/tools/memory_search.py`,
> `.boa/hooks/memory_recall.py`, `.boa/tools/memory_types.py`.

## The block
Every recorded memory — a memory-bank entry (routed by type, below), a lead note (the inbox and pending files) and
every agent's metacognitive trace — is one block:

```
@@@memory-<N> brief="<one-line summary>" datetime="<YYYY-MM-DDTHH:MM:SSZ>" keywords="<search words, task ids such as T-123>" type="<type>"
<the full text of the memory>
@endmemory
```

Rules for every block:
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
  re-gating. Ids are never reused on main: ids assigned in a discarded fold never existed. **Lanes never write
  id-bearing blocks into memory-bank files:** an agent in a lane formats its memories with `memory_write.py
  --format-only` (a block without an id) into its lane's `.lane-resume/memories.md` and into its report.
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
- **Supersession:** a memory that replaces earlier ones names them by final id, `supersedes="memory-12,memory-31"`; the
  writer stamps `superseded-by="memory-<N>"` on the opening tag of each superseded block — the ONLY edit ever made to
  an existing memory; its text never changes. A memory is current while it has no `superseded-by`. Nobody hand-edits
  ids or links.
- **Citations:** `Memories used:` in a report names only final ids (`memory-12`); a lane's own new memories are cited
  by their brief until the fold gives them ids.
- **`datetime` is exactly `YYYY-MM-DDTHH:MM:SSZ`** (UTC, seconds, a literal `Z`), as `date -u +%Y-%m-%dT%H:%M:%SZ` prints
  it; never typed or guessed.
- **One block, one fact; the most specific type** (the types table below); `brief` is one line (about 100 characters)
  a search result can be judged by; `keywords` carry the task ids (`T-NNN`, at least three digits) and the words
  someone would search for; the text is complete on its own.
- **Checks:** `.boa/tools/memory_lint.py` validates every block (fields, the exact datetime format, the type from the
  configuration, ids unique and progressive, every `supersedes` id exists, the links agree both ways, no cycles, no
  fork, every supersession forward in time); the
  project's `pre-commit` (project-wiring "git hooks") runs `memory_lint.py --staged` and refuses a commit with broken links; the post-tool hook
  `.boa/hooks/memory_check.py` lints a memory file right after a file write of it; `.boa/tools/memory_search.py`
  finds memories by keyword, type, task id or date (current ones by default, the supersession chain on request).
- **Legacy cutoff:** in a memory file that already held notes before BOA (brownfield, refactor), the line
  `<!-- boa:memory-cutoff -->` separates them: everything above it is legacy and exempt from the checks; every
  memory below it is a block.
- Ledgers and registries keep their line formats (the plan block, the contracts index, the residue register, the
  transit queue open-items.md, the lane registry): they are not memories.

Example — memory-42 replaces memory-17 (ingested by `memory_write.py`, which also adds `superseded-by="memory-42"` to
memory-17's opening tag):

```
@@@memory-42 brief="Gate runs only on the remote runner" datetime="2026-11-12T17:40:00Z" keywords="gate, runner, T-123" type="constraint" supersedes="memory-17"
Heavy runs (gate steps, mutation, full suites) go to the remote runner through the project's runner command; the development host
runs only light suites and the stack checks.
@endmemory
```

## Supersede-only (the one rule)
A memory is **never edited and never deleted**. To correct, refine, merge or retire one, write a NEW memory that
`supersedes` it (an id-less `memory_write.py --format-only --supersedes memory-N` block in a lane's
`.lane-resume/memories.md` or the lead's staging file; the fold's `--ingest` writes it): the writer stamps
`superseded-by` on the old block, the ONLY change ever made to it, and its text stays as history. The default search
shows only the CURRENT memories (no `superseded-by`); `memory_search.py --all` adds the superseded ones and
`--chain memory-N` shows one memory's whole history, oldest first, the head marked. A wrong or obsolete memory is
retired by a superseding memory that says so, never by an edit or a removal. AGENTS §4/§14 and 09 §16.4/§27 point here.

## The types — what each one is and when to use it
Pick the MOST specific type; one block holds one fact; if two types fit, split it into two blocks. Generated from
`.boa/memory-types.json`:

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

## Recall: when to read memory (as binding as writing it; OR-51)

Search the memory (`python3 -I .boa/tools/memory_search.py`, current memories by default) BEFORE acting in these
moments, with these types first, and cite the memory ids you relied on in your report. Generated from
`.boa/memory-types.json`:

<!-- memory-recall:begin -->
| Moment | When | Search for | Types to look at first |
|---|---|---|---|
| `start` | starting or resuming a task | the task id, the module/component names, the files it will touch | `constraint`, `contract`, `adr`, `edr`, `invariant`, `requirement`, `deferred`, `security`, `bug` |
| `error` | an error, a failing test, a refused command, anything surprising | the error text, tool name, symptom words | `lesson`, `gotcha`, `edgecase`, `trap`, `security`, `bug` |
| `decision` | before taking a decision (design or execution) | the subject and the options | `constraint`, `adr`, `edr`, `heuristic`, `nogoal`, `security` |
| `contract-change` | before changing a contract, schema or public behaviour | the contract id, the surface, the consumers | `contract`, `adr`, `invariant`, `requirement`, `security` |
| `review` | reviewing or testing | the module, the delicate paths | `edgecase`, `contract`, `trap`, `invariant`, `security`, `bug` |
| `plan` | planning, estimating, splitting lanes | the area, similar past tasks | `lesson`, `outcome`, `heuristic` |
| `close` | closing a project | everything still open | `constraint`, `goal`, `requirement`, `deferred`, `security`, `bug` |
<!-- memory-recall:end -->

A problem occurring (a failure, an error, a bounce, a surprise) is a recall moment: the `error` row above applies before
any diagnosis (OR-67), and the report cites what was found or says `none found`.

- **Free-text search:** `memory_search.py --query "<words>"` ranks the current memories best first: BM25 finds the
  candidates, then the sentences holding the query words are re-ranked by embedding similarity through the
  environment `boa install` builds in `.boa/embed/` (a multilingual model: memories in the user's language are
  matched too; a query takes a few seconds while the model loads). No false zero: when BM25 finds fewer memories than `--limit`,
  every memory is also compared by meaning, so one in another language or with other words is still found (the
  output says so); each memory's vector is cached by content hash (`.boa/embed/cache/memory-vectors.bin`, appended to,
  safe to delete), computed at install and when `memory_write.py` writes it (in the background). On a large bank never embedded, a query fills the cache within a time budget and says how many
  memories it has not compared yet; the next queries finish the job.
  If the output carries a `memory-search: WARNING` line, the
  environment is missing or broken: re-run `boa install` (if that fails, ask the user for what it names).
- If a memory already answers the question, **follow it — or supersede it with a better one** (through
  `memory_write.py`); never silently ignore it.
- If the search finds nothing and you then solve a non-obvious problem, **write the memory** (lesson, gotcha, trap,
  edgecase, …) so the next agent finds it.
- **Cite** the final ids you relied on: `Memories used: memory-12, memory-31` (or `Memories used: none found`).
- **What is wired** (each where the runtime has the event; verified at every wiring, OR-63): the session-start status
  prints the current memories for every active task id; the post-tool-failure hook `.boa/hooks/memory_recall.py`
  injects the gotcha/trap/lesson ids matching a failed tool call's error text; at a sub-agent's start, where the
  runtime injects context there, `.boa/hooks/memory_recall.py --session` gives the starting agent the memory reminder
  and the current memories of every active lane (the lanes exist before the spawn; the agent→task binding lands only
  after the agent starts, so no hook can pick the agent's own task at that moment). A sub-agent gets its own task's
  memories through its **brief** — the lead pastes the `memory_search.py --task <T>` output ("memories to know") into
  every brief (09 §4). **Discipline only:** no runtime event marks a decision, planning or the
  close-out, and no shipped hook acts on a contract file's write (the post-write hook only lints the memory files):
  at those moments the agent searches itself. A BOA update has its own procedure (09 §30, docs/02 "Re-installing and
  upgrading"). The review moment is served in part by the sub-agent start hook, and for the rest by the brief's
  "memories to know". The hooks help; they never replace the agent's own search.

## Where each memory goes (routing by type)

`memory_write.py --ingest` picks the file from the configuration's routes. Staging files (each lane's
`.lane-resume/memories.md`, the lead's inbox and pending files) hold `--format-only` blocks until the fold. Ids are
one global sequence across
all memory files, so `supersedes` may point to a block in another file; the lint checks the links across the whole
memory bank. The runtime's own private memory (an assistant's auto-memory) is never used for project memory.
Each type's file is the `File` column of the types table; the keyword routes override it (any type, unless a route
names one). Each memory-bank file that receives memories has a `## Memories — …` section, under which
`memory_write.py` appends the blocks.
The keyword routes, generated from `.boa/memory-types.json`:

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

## The memory tools — every command and option, and when to use it

Every tool runs as `python3 -I .boa/tools/<tool>.py …`; `--help` lists the flags, the module docstring the details.
Exit codes: 0 ok, 1 refused or nothing found, 2 usage.

### `memory_write.py` — the only writer
| Command | When to use it |
|---|---|
| `--type T --brief B --keywords K [--text TEXT]` | Write one memory now: it gets the next id, `datetime` = now, a file chosen by the type and the keywords, under that file's `## Memories — …` section. The text is `--text`, else stdin. Prints `memory-N <file>`. This is the primitive behind the fold: use it only where no lane or train exists (the install seed, a single-agent project); in a lane use `--format-only`. |
| `--supersedes memory-12,memory-31` | With a write: this memory replaces those CURRENT ones (each must exist, be current and be strictly older). One memory may supersede several; two may never supersede the same one. |
| `--file PATH` | Override the route with a file inside the memory bank. Documented exceptions only; normally the type and keywords route it. |
| `--root ROOT` | Another project root (a worktree or a test copy); default the current project. |
| `--format-only` (+ the fields above, and `--supersedes-brief "<brief> \| <brief>"`) | Print an id-less draft, touching nothing: for a lane's `.lane-resume/memories.md`, a report trace, a lead staging file. `--supersedes-brief` names another new draft of the same batch (it has no id yet) instead of a final id. |
| `--ingest FILE…` | The train fold only (the integrator, ONCE per train, one `docs(memory)` commit): reads the drafts of all the files, assigns ids so they ascend with time, stamps every supersession, routes by type. All or nothing; a draft already ingested is skipped, never duplicated; the draft files are never changed. |
| `--receipt PATH` (with `--ingest`) | Record what each file contributed (a hash of the prefix read) outside the bank, so the lead can mark it folded. |
| `--mark RECEIPT --train TRAIN-NNN` | After the fold has landed: the lead inserts the `Folded by` marker in each staging file at the receipt's line, so the next fold reads only what was added below it. A second run is a no-op. |
| `--seed` | Adopt the ids of an existing memory bank (blocks after the cutoff) into a new ledger. Brownfield only: the install seeds a missing ledger, and so does every write. |
| `--repair-ledger [--adopt memory-N,… --reason "…"]` | After a crash the lint reports orphans or a missing `superseded-by`: this voids ids whose block is missing and fixes the stamp. A block present in the bank but missing from the ledger (written by hand) is refused unless adopted explicitly with `--adopt` and a `--reason`. Then lint, then redo the interrupted write. |
| `--no-vectors` | Skip the background caching of the search vectors after a write (tests, a machine with no environment); the search computes missing ones itself. |
| `--type`, `--brief`, `--keywords`, `--text` | The fields of a block: the most specific type, a one-line brief (about 100 characters), the words and task ids someone will search for, the full text. |

### `memory_lint.py` — the checker
| Command | When to use it |
|---|---|
| `memory_lint.py` | After any change to a memory file, and after every fold: the whole bank (fields, exact datetime, type, unique and progressive ids, links both ways, no cycle or fork, forward in time, ids against the ledger). Prints each finding as `<file>:<line>: <finding>` and a last summary line. |
| `memory_lint.py PATH…` | Only those files or directories (`*.md` under them). |
| `--drafts` | Check id-less blocks (a lane's `.lane-resume/memories.md`, a report, a lead staging file): header fields without an id, `supersedes` / `supersedes-brief` allowed. |
| `--staged` | The staged memory bank, for a pre-commit hook the project wires (project-wiring "git hooks"). |
| `--ledger FILE` / `--no-ledger` | Check against another ledger file, or skip the ledger check (a copy of a bank outside the project). |

The post-tool hook `memory_check.py` runs the same lint on a memory file right after a file write of it and reports
at once; repair a finding through `memory_write.py`, never by editing ids or links.

### `memory_search.py` — the recall
All the filters combine (AND); results are the current memories unless `--all`; they print oldest first, except
`--error` and `--query`, best first. Default search scope: the memory bank and the lead dir (drafts included); `PATH…`
narrows it to those files or directories.
| Option | When to use it |
|---|---|
| `--task T-NNN` | At a task's start or resume, and for a brief's "memories to know": the task id stands alone in the keywords, brief or text. Repeatable: all must match. |
| `--moment M` | Before acting at a recall moment (`start`, `error`, `decision`, `contract-change`, `review`, `plan`, `close`, or one a project added): the types that moment lists. |
| `--type T` | One kind of memory (a type of `memory-types.json`). Repeatable: any of them. |
| `--keyword W` | A word (case-insensitive) in the keywords, brief or text: a component, a tool, an error word. Repeatable: all must match. |
| `--since DATE` / `--until DATE` | Memories from or up to a date: `YYYY-MM-DD` (the whole UTC day) or `YYYY-MM-DDTHH:MM:SSZ`; "what changed this week". |
| `--error TEXT` | After a failure, BEFORE diagnosing: the error text against the `error` moment's types (gotcha, trap, lesson, edgecase, …), ranked by shared words, at most `--limit`. Not combinable with `--query`. |
| `--query TEXT` | Free text when you do not know the task id or the exact word. Hybrid, best first: BM25 over keywords, brief and text finds the candidates; the sentences holding the query words are re-ranked by meaning with the model `boa install` puts in `.boa/embed/`. A query takes a few seconds while the model loads. Not combinable with `--error`, `--chain` or `--next-id`. |
| the no-false-zero fallback (part of `--query`) | When BM25 finds fewer memories than `--limit`, every memory left by the filters is also compared by meaning and those at similarity 0.5 or more are added after the BM25 ones, so a memory in another language or with other words is still found. The output says so. A `memory-search: WARNING` line means the environment is missing: re-run `boa install`, else ask the user for what it names; the BM25 result still comes. |
| `--limit N` | At most N results for `--query` and `--error` (default 5, at least 1); raise it when the first page misses. `--no-vectors` belongs to `memory_write.py` only: the search needs no such flag, it falls back to BM25 by itself when the environment is missing. |
| `--warm` | Cache the vector of every memory not cached yet (no time limit; `boa install` runs it once). Run it after a bulk import so the first queries are fast. Best effort, exit 0. |
| `--warm-ids memory-N,memory-M` | The same for those memories only; `memory_write.py` starts it in the background after a write. |
| `--all` | Include the superseded memories too: to see what was tried and replaced before a decision, or to audit. |
| `--chain memory-N` | One memory's supersession history, its predecessors and its successors up to the current head, oldest first, the head marked: use it BEFORE superseding, to find the head to supersede. |
| `--brief` | One line per match (`memory-N file:line datetime type brief`) when only a list is needed. |
| `--next-id` | The next free id, for information only (ids are assigned by the writer). |
| `PATH…` | Search only these files or directories (e.g. a lane's drafts). |

Exit 0 with a match, 1 with none (then, if you solve a non-obvious problem, write the memory), 2 on a usage error.

### `memory_types.py` — the configuration, and adding a memory type
The types, their routes and the recall moments live only in `.boa/memory-types.json` (schema `boa/memory-types/1`;
the environment variable `BOA_MEMORY_TYPES` names another file). Every tool and hook reads it.
| Command | When to use it |
|---|---|
| `memory_types.py --check [FILE]` | After editing the file: validates names, routes, priorities (two keyword routes with the same priority are refused) and recall ids. Exit 0 ok, 1 invalid. |
| `memory_types.py --render-tables [FILE]` | Prints the three generated tables above (types, recall moments, routes). Regenerate and paste between the markers after a change; never write the tables by hand. |

To add a type: add `{name, records, use_when, must_contain[], route, recall[]}` to `types` in the file (`name`
lowercase `[a-z][a-z0-9-]*`, unique; `route` a file of the memory bank, `NN-NAME.md`; `recall` ids of existing
moments); to add a route for a keyword, a `keyword_routes` entry `{keyword, route, priority[, type]}`; to add a
recall moment, a `recall_moments` entry `{id, when, search_for}`. Then `--check`, regenerate the tables, run the lint
on the bank. The new type is then valid in `memory_write.py`, the lint, the search (`--type`, `--moment`) and the
hooks. Give the route's file a `## Memories — …` section so the writer has a place. Never rename or remove a type
that existing blocks use: add the new one and supersede those blocks.

### The recall hooks (wired by the agent where the runtime has the event, `references/runtimes.md`)
| Hook | What it does |
|---|---|
| `hooks/memory_recall.py` on a failed tool call (`post-tool-failure`) | Searches `--error` with the failure's text and injects the top 5 matching memories (`memory-12 gotcha: <brief>`); nothing when none match. It helps; it never replaces your own search before diagnosing. |
| `hooks/memory_recall.py --session [T-NNN…]` | Prints the three-line memory reminder and the current memories of the given tasks, or of every lane's task when none is given: used by the session-start status, and wired at a sub-agent's start where the runtime injects context there (it reads no event and prints plain text: the wiring passes it on as the context). |
| `hooks/memory_check.py` on a file write (`post-tool` of a `file-write`) | Lints the memory bank right after a memory file is written and blocks with the findings, so a broken block is repaired at once. |
Both hooks never fail the tool call (exit 0).
