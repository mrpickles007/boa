---
description: Close the project — ask the owner how it ends (by project type and goal), check secrets, residue and forgotten work, do every closing step, report.
---
<!-- BOA neutral command metadata: the header above (description, optional argument-hint) is converted by the agent to its runtime's format at bootstrap; the body is the runtime-neutral contract. -->

Close {{BOA_PROJECT_NAME}} (09 §14). Nothing is declared done before every check below passes.

## 1. Preconditions
- Every milestone DONE (`python3 -I .boa/tools/plan_lanes.py`), no lane open, `{{BOA_MAIN_BRANCH}}` green. If not,
  say what is left and stop (or continue `/run-project` with the owner's OK).

## 2. Ask the owner how the project ends (one question round, options + recommendation each; OR-12)
Pick the questions that fit the project type and goal (a library, a web service, an app, a CLI, an internal tool):
1. **Deployment target:** deploy to a remote server (which; how: containers, packages, a platform), publish (package
   registry, app store), leave it running where it is, or stop the local instance?
2. **The local instance and data:** keep, archive (where) or remove the project's own deployment, containers,
   volumes and data?
3. **Repository:** keep the remote repository on `{{BOA_FORGE}}` (`{{BOA_FORGE_REPO}}`), change its visibility
   (private/public), transfer it, archive it? Push tags and a release?
4. **CI:** leave CI as it is, enable it (costs?), or remove it?
5. **Licence:** which licence (and third-party notices) for the code that ships?
6. **Hand-over:** who maintains it next (the owner, another team, another agent)? What documentation do they need
   (README, operations notes, the agent handbook as is)?
7. **The BOA tooling:** keep the discipline installed (for future work) or uninstall it (hooks, agents, commands,
   `.boa/`, the lead dir), keeping the memory bank as history?
Record the answers as an ADR "Project close-out": an id-less `--format-only` block in the lead's staging file
`{{BOA_LEAD_DIR}}/plan-additions-pending.md`; it lands with the last train's fold (§3).

## 3. Do the closing steps the owner chose (uninstall excluded)
Deploy or publish (lead only, with a health check that has an expected answer), set the repository visibility, push
tags and the release, configure or remove CI, add the licence, write the hand-over notes. Every step that changes the
repository is a task through the pipeline (builder → reviewer → tester → integrator). If the owner chose to
uninstall BOA, that comes LAST (step 5), after the checks.
**The close record goes in the last train's fold:** before the last closing task's train, stage the close-out ADR
(§2) and an id-less `outcome` block (what was built, the closing steps done) in
`{{BOA_LEAD_DIR}}/plan-additions-pending.md`; that train's `docs(memory)` fold lands them in 06 and 05. Nothing is
staged after it: §4 requires zero pending folds, and §5 may remove `.boa/` and the lead dir.

## 4. Final checks (after the closing steps; all must pass; each result goes in the final report)
1. **Secrets:** the project's scanner on the tree and the full history (project-wiring "secret scanning"). A hit is removed, the secret
   rotated, and — if it is in history and the repository will be shared — the owner decides between a history
   rewrite and keeping it private.
2. **Completeness:** `python3 -I .boa/tools/trace_check.py --close` at 0 mismatches (every live task DONE, every
   feature DONE and traced to running tests, every contract closed and every clause tested, the residue register and
   the transit queue empty); release acceptance done (full-scope mutation on the delicate paths, end to end, security
   re-audit, zero open findings).
3. **Freshness:** zero outdated pins except documented holds (09 §19).
4. **Final duration review:** the project's timing check and throughput review (project-wiring
   "suite timings and duration control", "usage clock and throughput"); record the final gate total, the per-step
   times and the project's throughput in the final report (§6; nothing is staged after the last train).
5. **The plan and the transit queue:** every plan row DONE (or handed over by name) and the transit queue
   `{{BOA_LEAD_DIR}}/open-items.md` empty (each line placed in the plan); pending owner rules
   and plan rows folded; the metalearning inbox curated into `10-METALEARNING.md`.
6. **Correspondence (OR-49):** `python3 -I .boa/tools/trace_check.py --close` reports **0 mismatches**: every
   contract closed (implemented, tested, signed off), every task mapped, every feature proven, every residue
   removed, every open item and pending fold at zero. Above zero the project is not closed: fix each mismatch (a task
   through the pipeline when it needs code) and run it again.
7. **Residue:** the residue register emptied; the project's daemons stopped; the project's residue check in final
   mode (project-wiring "deployed-instance objects") = zero (no lane containers, networks, volumes or images, worktrees, lane branches local or remote, scratch).
8. **Final requirements review (OR-66, mandatory; 09 §14 checklist):** an independent reviewer walks every
   requirement against every indication the owner gave (08, the pending owner rules, the owner decisions in 06),
   every planned task, the code and the discipline (each checked on its own, no two texts contradicting each other).
   Every open row becomes a plan row and the walk repeats; the project is not closed until it reports zero open rows.
A closing step that runs after a check (none should) means that check runs again.

## 5. Uninstall BOA — LAST, only if the owner chose it
The checks of step 4 have run with the tools in place; now remove the BOA tooling (hooks, agents, commands, `.boa/`,
the lead dir, the git hooks; keep the memory bank as history) as the BOA package's `docs/12-uninstall.md` says. The
final report states that the checks ran before the tools were removed and that the removal is the only change after
them.

## 6. Final report (to the owner, in {{BOA_REPLY_LANGUAGE}})
What was built (milestones, DONE/total), where it is (deployment, repository, release), the closing steps done, the
checks and their results (and, if BOA was uninstalled, that they ran before the removal), the decisions taken at
close-out, residual risks (documented), the final durations and disk, and the lessons of `10-METALEARNING.md` worth
carrying to the next project. Update `active-context.md` (closed); the close record already landed with the last
train's fold (§3), and this report is the record of the checks.
