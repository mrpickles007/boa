# Close-out — how a BOA project ends

> Installed procedure: 09 §14 and `/close-project` (the executable checklist). This reference is the design: why each
> question and check exists and how the answers map to closing steps. A project is closed only when every check
> passes and the correspondence check reports 0 mismatches (OR-49).

## Milestone closure (repeats at every milestone)
Full-scope mutation round on the delicate paths (the wrapper's milestone mode, resumable, on the runner when
configured) · every suite tier · the residue check in closing mode · the secret scan of the tree · freshness · the duration
review · the correspondence check · the milestone's open items walked · the optional reviews the adopted rules ask for
(UI screenshots, native-speaker translation review) · the final requirements review of the milestone's rows
(check 9) · then the tag.

## The questionnaire (by project type and goal)
Asked once, in one round, each question with options and a recommendation (OR-12); only the questions that fit:

| Question | Typical options | Fits | Closing steps it drives |
|---|---|---|---|
| Deployment target | a remote server (containers / packages / platform), publish to a registry or store, leave running here, stop | services, apps, libraries | deploy (lead only) with a health check that has an expected answer; or publish with a release; or stop and archive |
| The local instance and data | keep, archive (where), remove | anything with a deployment | backup, archive, remove the project's own containers/volumes (provably ours) |
| Remote repository and visibility | keep private, make public, transfer, archive | all | visibility change, tags and release, branch protection |
| CI | keep as is, enable (cost), remove | all | CI file added/changed/removed through the pipeline |
| Licence | the owner's choice; third-party notices | anything that ships | `LICENSE`, notices, a dependency-licence check |
| Hand-over | the owner, another team, another agent | all | README, operations notes, the handbook as is, open risks |
| BOA tooling | keep installed, uninstall (keep the memory bank as history) | all | `docs/12-uninstall.md` steps of the package |

The answers are recorded as an ADR "Project close-out" before any step runs.

## The order (binding)
1. **Questionnaire** → ADR.
2. **The closing steps the owner chose** (deploy or publish, visibility, tags and release, CI, licence, hand-over),
   each one that changes the repository as a task through the pipeline. Uninstall is not one of them.
3. **THEN the checks below**, on the final state: a check that ran before a closing step would prove the wrong
   state (residue left by a deployment, an open item created by a hand-over, a secret added by a release note).
4. **Uninstall BOA LAST**, only if chosen: the checks have run with the tools in place; the removal is the only change
   after them, and the final report says so.
5. **The final report.**

## The checks (all must pass; each result in the final report)
1. **Secrets:** the tree and the **full history** (the project's scanner, project-wiring "secret scanning"). A hit
   is removed and the secret rotated; a hit in history of a repository that will be shared is an owner decision (rewrite history or keep
   it private), never ignored.
2. **Completeness:** `trace_check.py --close` at 0 mismatches (every live task DONE, every feature DONE and traced to
   running tests, every contract closed and every clause tested, the residue register and the transit queue empty); release acceptance (full-scope mutation on the
   delicate paths, end to end with real client types, security re-audit, zero open findings).
3. **Contracts:** every contract `closed` (implemented, tested, signed off), every contract test in the gate.
4. **Freshness:** zero outdated pins except documented holds.
5. **Final duration review:** the timing check and the throughput report (project-wiring items); the final gate total and per-step times
   recorded.
6. **Open items and folds:** the transit queue `open-items.md` emptied into the plan by the last fold (every captured
   line placed: a plan row, a note on the row that owns it, or no action with its reason), pending owner rules and
   plan rows folded, the metalearning inbox curated.
7. **Correspondence:** `trace_check.py --close` at **0 mismatches**.
8. **Residue:** the register empty, the project's daemons stopped, the residue check in final mode = 0 (project-wiring
   item "deployed-instance objects").
9. **Final requirements review (OR-66):** an independent reviewer walks every requirement against every indication
   the owner gave (the owner rules record, the pending rules, the owner decisions), every planned task, the code and
   the discipline, each checked on its own (no two texts contradicting each other). Open rows become plan rows; the
   walk repeats until zero open rows. It also runs, for the milestone's rows, at every milestone closure.

## The final report
What was built (milestones, DONE/total), where it is (deployment, repository, release), every check and its result,
the close-out decisions, residual risks (documented, with why they are acceptable), the final durations and disk, and
the lessons of `10-METALEARNING.md` worth carrying into the next project.
