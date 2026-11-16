# 07 Memory and state

Agents remember nothing between sessions: the files are the memory. BOA ships the memory system as code (write,
lint, search, types) and the memory bank, the lead's files and the resume files as templates and procedures. The
reference: [references/memory-types.md](../references/memory-types.md); the card:
[memory](../assets/templates/agent-handbook.md#tool-card-memory).

## The memory bank

`memory-bank/` (versioned) is read in full at every session start:

| File | Holds |
|---|---|
| `RESUME.md` | where to start after a pause or in a fresh session |
| `00-PROJECT-BRIEF.md` ... `02-SPECIFICATIONS.md` | the brief, the blueprint, the specifications and contracts |
| `03-IMPLEMENTATION-PLAN.md` | the plan: the single source of work |
| `04-ARCHITECTURE.md` | the architecture, the environment facts and the residue register |
| `05-PROGRESS.md`, `active-context.md` | what happened and what is active now |
| `06-DECISIONS.md` | the decisions (ADRs), each with its reasons and its compatibility impact |
| `07-SECURITY.md` | security findings, threats and how they are handled |
| `08-OWNER-RULES.md` | every binding rule ([06 Rules pool](06-rules-pool.md)) |
| `09-OPERATING-PROCEDURES.md` | the workflow in practice |
| `10-METALEARNING.md` | what was learned about the way of working |

It is append-and-refine: a fact is superseded with a date, never silently deleted. If the bank and the code disagree,
the code is the truth and the bank is fixed. The installed `docs/agent-handbook.md` is the map of every file and tool,
kept current by every change ([08 Measuring](08-measuring.md#handbook-drift)).

## Memory blocks and types

Every recorded memory (a memory-bank entry, a lead note, an agent's metacognitive trace) is one block:

```
@@@memory-<N> brief="<one-line summary>" datetime="<YYYY-MM-DDTHH:MM:SSZ>" keywords="<search words, task ids such as T-123>" type="<type>"
<the full text of the memory>
@endmemory
```

The types (lesson, gotcha, edgecase, constraint, contract, adr, edr, outcome, trap, heuristic, invariant, goal, nogoal,
requirement, deferred, security, bug), the file each type is routed to, the keyword routes and the recall moments
live in ONE configuration file, `.boa/memory-types.json`; every tool and hook reads it at run time, so a new type works
everywhere at once (add it to the file, then `memory_types.py --check` and `--render-tables`). The memory syntax is always English; the
content is in your language.

## Writing memories

Memories are written only through `memory_write.py`, never by hand. Agents write id-less drafts
(`memory_write.py --format-only`) into their report or their lane's `.lane-resume/memories.md`; the lead writes its
notes into its staging files. Only the integrator's train fold assigns ids: in the train's one `docs(memory)` commit it
runs `memory_write.py --ingest` once over every staging file and lane memories file, then `memory_lint.py`. The memory
lint hook checks a memory file after every write; the project's commit hook runs `memory_lint.py --staged`.

## Supersede, never edit

A memory is never edited: a newer block supersedes it, and the link is recorded both ways (supersedes and
superseded-by). Chains stay coherent: a memory is superseded at most once, the head of a chain is what you supersede,
merges are allowed and forks refused, and the superseded memory must exist and be older. `memory_search.py --chain`
shows a chain.

## Recall and memory search

Recall is as binding as writing: agents search the memory before acting, at the moments `.boa/memory-types.json`
names (task start or resume, an error or surprise, before a decision or a contract change), and cite the memory ids
they relied on. When a problem occurs, memory comes first: search for it before trying a fix. The session status hook
injects the memories of every active task; the recall hook searches the error text of a failed call and injects the
matching lessons; a sub-agent gets its task's memories through its brief.

`memory_search.py --query "<text>"` is hybrid: BM25 over the blocks finds the candidates, then the sentences that
hold a query word are re-ranked by meaning with the embedding environment `boa install` built in `.boa/embed/`
([02 Install and wiring](02-install-and-wiring.md#the-memory-search-environment)). With fewer keyword candidates than
the limit, every remaining memory is compared by meaning, so a search never returns a false zero. Vectors are cached
by content hash (a cache, safe to delete, never a database); nothing goes to the network at query time. Without the
environment, search ranks by BM25 alone and warns. Filters: `--keyword`, `--type`, `--moment`, `--task`,
`--since`/`--until`, `--error`.

## The lead directory

The lead's live state lives in `BOA_LEAD_DIR` (default `.lead/`, machine-local, git-excluded, written only by the lead):

| File | Purpose |
|---|---|
| `lanes.md` | the registry: one timestamped line per stage change; the newest line per lane wins |
| `lanes/<task>.md` | the lane journal: every agent's final report, written by the sub-agent stop hook |
| `brief-common.md` | the rules pasted into every agent brief |
| `open-items.md` | the transit queue of captured to-dos, emptied into the plan at every train |
| `owner-rules-pending.md`, `plan-additions-pending.md` | rules and plan rows waiting for the next fold |
| `metalearning-inbox.md` | lessons from the agents' traces, curated at each train |
| `PAUSE`, `RESUME-LEAD.md` | the pause flag and the lead's resume file ([10](10-pause-resume-close.md)) |

Live lane state lives here, never only in a session, so any agent can take over at any moment. Machine-local state a
lane holds is handed over before the lane merges.

## Lane journals and report capture

At every sub-agent stop, `subagent_stop.py` appends the agent's final report verbatim to its lane journal (a report
over 20 KiB is kept whole beside it, and the cut names it), queues its Leftovers items and flags a task agent's
report without a Leftovers section. The recognised words come from `.boa/markers.json`
([tool card](../assets/templates/agent-handbook.md#tool-card-lane-journal-and-report-capture)).

## Resume files

Each agent keeps its lane state in `<worktree>/.lane-resume/<role>.md` (git-excluded, never committed): what it did,
what is left, how to resume. After a compaction or an interruption an agent re-reads its brief's files, its resume
file and the worktree first; the worktree and git win over any summary.

## Metalearning

Every report ends with a metacognitive trace (mistakes, surprises, what slowed the agent, what it learned about the way
of working), written as id-less memory blocks that reach `10-METALEARNING.md` through the lane's memories at the
fold. The lead keeps its own: `metalearning.py append` turns the lead's notes into drafts in the inbox (never copies
of lane lessons); `metalearning.py curate` lists the lessons of 10 and the inbox seen more than once
([tool card](../assets/templates/agent-handbook.md#tool-card-metalearning)). The fold ingests the inbox into
`10-METALEARNING.md`; the lead turns a lesson seen twice into a rule proposal, a brief line, a contract line or a
tooling task.

## The language change

The machine-recognised words (report sections, the Leftovers label and its "none", review classes, the fold marker,
plan column headers) live in `.boa/markers.json`. To change the product language the lead runs
`boa language set <lang> --texts FILE` first: the file is switched only when every hook recognised samples written in
the new language; English stays accepted as an alias, and the marker-bearing sections of the installed files are
regenerated. `boa language show` and `boa language check` read and validate it
([tool card](../assets/templates/agent-handbook.md#tool-card-language-and-markers)). The memory syntax is never
translated.

## Other memory systems

BOA's memory tools are command-line tools, not a server. The project's memory goes only into the memory bank, through
`memory_write.py`; a runtime's own private memory (where the runtime keeps one: its profile in
[references/runtimes.md](../references/runtimes.md)) is never used for project memory.

## Task ids

Task ids are `T-NNN`: `T-` and at least three digits, with no upper limit (more digits when the plan grows past 999), everywhere (plan,
branches, commits, registry, journals, memories); BOA's tools read `T-` plus three or more digits. The lead assigns
them; agents never open tasks.
