# 10 Pause, resume, close

The three commands ship as runtime-neutral files (`.boa/commands/pause-project.md`, `resume-project.md`,
`close-project.md`); the references behind them are [references/pause-resume.md](../references/pause-resume.md) and
[references/close-out.md](../references/close-out.md).

## Pause

A pause is a signal, not a message: running agents do not re-read their briefs, so a flag file and a guard stop them.

1. `pause-project` writes the flag (`boa pause-flag set <reason>`, the file `<lead dir>/PAUSE` with the time and
   reason) and the lead messages every running agent.
2. Each sub-agent finishes its atomic step, commits `wip(<task>): ...` in its own worktree (or declares uncommitted
   work), writes its resume file `.lane-resume/<role>.md`, cleans its scratch and ends its turn. The pause guard leaves
   it nothing else: while the flag exists a sub-agent may only write its resume file, append to its lane's
   `.lane-resume/memories.md`, run read-only git, commit in its own worktree, remove its own scratch, stop its own
   processes and hand back its final report ([card](../assets/templates/agent-handbook.md#tool-card-pause)).
3. The sub-agent stop hook copies each resume file into the lead directory (`lanes/<task>-<role>.md`) and journals
   "paused".
4. The lead records the pause in the registry, pushes the lane branches as a backup (no pull requests), updates the
   progress log and the active context, and stops the project's background processes.
5. The lead's stop hook renders the status screen as a marked block of `<lead dir>/RESUME-LEAD.md` (between
   `<!-- boa:lead-stop:begin -->` and `<!-- boa:lead-stop:end -->`); the lead checks it and completes the file
   outside the block. The hook keeps every byte outside its block, so a hand-written handover file is never lost; on a
   file without the markers it keeps the whole file and puts the block on top.

The integrator stops before starting the next merge; a merge already running completes, and its resume file states
the stack (which lanes merged and at which commits, which are stacked and gated). A pause during a train gate
interrupts the gate; the train re-runs after the resume. A paused lane cannot remove its own containers or services
(the pause guard knows no engine): it names them in its resume file and the lead removes them. Without a pre-tool hook
that can deny, the flag is not enforced: the lead messages every agent and checks each resume file by hand.

## Resume

`resume-project` clears the flag (`boa pause-flag clear`), restarts the project's background processes, prints the
status screen and a per-lane plan: the same agents if the session survived (they keep their context), unless the
size trigger or the wait trigger of operating procedures section 5.3 holds at the resume (the agent's context has grown
large, or the pause outlasted the cache lifetime: then a fresh agent; a resumed paused round never counts toward the
third-round trigger); if the session that paused is gone, new agents of the same role, each briefed with its resume
file, the newest journal entry and the lead's notes since the stop. The code and git win over a resume file that
disagrees with them. A flag left behind after a crash makes
`run-project` refuse to start and point to `resume-project`.

### Resuming in another runtime

A project paused in one agent runtime (say its usage limit ran out) can be resumed by a different runtime that never
worked on it, on the same repository. Everything the pause left is plain files (the flag, `RESUME-LEAD.md`, the resume
files, the journals, the memory bank, the `AGENTS.md` block) and reaches the new agent through `AGENTS.md`'s read
order; the first runtime's wiring is not read by the second. So the new agent first redoes the capability
self-assessment for its own runtime and wires it, before it clears the flag or resumes any lane; it leaves the other
runtime's wiring untouched (never modified, moved, regenerated or removed unless you ask, even when it looks stale),
adds its runtime to the capabilities record and tells you what it cannot enforce. Whatever door the agent comes in by
(the skill with a mode, a command, `AGENTS.md` alone), an installed project whose plan has tasks is never bootstrapped
again ("installed": `.boa/installed.list` exists or BOA's marked block is in `AGENTS.md` or `.gitignore`; a fresh
clone gets `boa install` from the BOA package first, so the agent may ask you where the package is). A known limit:
until the new runtime is wired, no hook reminds the agent of any of this; `AGENTS.md`'s read order is the only path.
Another known limit: runtimes take turns. Two runtimes working on the same project at the same time is not supported
(one lead, one scratch root); resuming in one after the other has paused is.

## Close

`close-project` ends the project in a fixed order:

1. **The questionnaire** ([The close questionnaire](#the-close-questionnaire)), recorded as a decision before any step
   runs.
2. **The closing steps you chose** (deploy or publish, visibility, tags and release, CI, licence, hand-over), each one
   that changes the repository as a task through the pipeline.
3. **The checks**, on the final state: secrets in the tree and the full history (the project's scanner); completeness
   and correspondence (`trace_check.py --close` at 0: every task done, every feature traced to running tests, every
   contract closed, the residue register and the transit queue empty); freshness (no outdated pin except documented
   holds); the docs sweep (every user chapter checked against what landed); the final
   duration review; every pending rule and plan row folded and the metalearning inbox curated; the
   residue check in final mode with the project's background processes stopped; and
   [the final requirements review](#the-final-requirements-review).
4. **Uninstall BOA last**, only if you chose it ([12 Uninstall](12-uninstall.md)).
5. **The final report:** what was built (tasks done out of the total), where it is, every check and its result, the
   close-out decisions, residual risks with why they are acceptable, the final durations and disk, and the lessons
   worth carrying into the next project.

## Milestone closure

At every milestone: the full-scope mutation round on the delicate paths, every suite tier, the residue check in
closing mode, the secret scan of the tree, freshness, the duration review, the docs sweep (every user chapter checked
against what landed), the correspondence check, the milestone's rows walked by the final requirements review, then
the tag.

## The close questionnaire

Asked once, each question with options and a recommendation, only the questions that fit the project's type and goal:

| Question | Typical options |
|---|---|
| Deployment target | a remote server, publish to a registry or store, leave running here, stop |
| The local instance and data | keep, archive, remove |
| Remote repository and visibility | keep private, make public, transfer, archive |
| CI | keep as is, enable (cost), remove |
| Licence | your choice, with third-party notices |
| Hand-over | you, another team, another agent |
| BOA tooling | keep installed, uninstall (the memory bank stays as history) |

## The final requirements review

Before a project is done, an independent reviewer walks every requirement against every indication you gave (your
rules, the pending rules, your decisions), every planned task, the code and the discipline, each checked on its own so
no two texts contradict each other. Open rows become plan rows and the walk repeats until zero rows are open. It also
runs for the milestone's rows at every milestone closure.
