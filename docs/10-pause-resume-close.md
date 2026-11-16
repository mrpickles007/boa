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
   `.lane-resume/memories.md`, run read-only git, commit in its own worktree, remove its own scratch and stop its own
   processes ([card](../assets/templates/agent-handbook.md#tool-card-pause)).
3. The sub-agent stop hook copies each resume file into the lead directory (`lanes/<task>-<role>.md`) and journals
   "paused".
4. The lead records the pause in the registry, pushes the lane branches as a backup (no pull requests), updates the
   progress log and the active context, and stops the project's background processes.
5. The lead's stop hook renders `<lead dir>/RESUME-LEAD.md` from the status screen; the lead checks and completes it.

The integrator stops before starting the next merge; a merge already running completes, and its resume file states
the stack (which lanes merged and at which commits, which are stacked and gated). A pause during a train gate
interrupts the gate; the train re-runs after the resume. A paused lane cannot remove its own containers or services
(the pause guard knows no engine): it names them in its resume file and the lead removes them. Without a pre-tool hook
that can deny, the flag is not enforced: the lead messages every agent and checks each resume file by hand.

## Resume

`resume-project` clears the flag (`boa pause-flag clear`), restarts the project's background processes, prints the
status screen and a per-lane plan: the same agents if the session survived (they keep their context), otherwise new
agents of the same role, each briefed with its resume file, the newest journal entry and the lead's notes since the
stop. The code and git win over a resume file that disagrees with them. A flag left behind after a crash makes
`run-project` refuse to start and point to `resume-project`.

## Close

`close-project` ends the project in a fixed order:

1. **The questionnaire** ([The close questionnaire](#the-close-questionnaire)), recorded as a decision before any step
   runs.
2. **The closing steps you chose** (deploy or publish, visibility, tags and release, CI, licence, hand-over), each one
   that changes the repository as a task through the pipeline.
3. **The checks**, on the final state: secrets in the tree and the full history (the project's scanner); completeness
   and correspondence (`trace_check.py --close` at 0: every task done, every feature traced to running tests, every
   contract closed, the residue register and the transit queue empty); freshness (no outdated pin except documented
   holds); the final duration review; every pending rule and plan row folded and the metalearning inbox curated; the
   residue check in final mode with the project's background processes stopped; and
   [the final requirements review](#the-final-requirements-review).
4. **Uninstall BOA last**, only if you chose it ([12 Uninstall](12-uninstall.md)).
5. **The final report:** what was built (tasks done out of the total), where it is, every check and its result, the
   close-out decisions, residual risks with why they are acceptable, the final durations and disk, and the lessons
   worth carrying into the next project.

## Milestone closure

At every milestone: the full-scope mutation round on the delicate paths, every suite tier, the residue check in
closing mode, the secret scan of the tree, freshness, the duration review, the correspondence check, the milestone's
rows walked by the final requirements review, then the tag.

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
