# Procedures catalogue — every procedure BOA installs, where it lives, what enforces it

> The binding text of each procedure is installed into the project (`memory-bank/09-OPERATING-PROCEDURES.md`, the
> agent contracts, the commands; templates in `assets/templates/`). This catalogue maps each one to its home, its
> tools and its enforcement, so the skill (and the documentation set) can check nothing is missing. It holds no
> procedure text of its own (one fact, one home).

| # | Procedure | Installed home | Tools | Enforced / recorded by |
|---|---|---|---|---|
| 1 | Session start (lead) | 09 §1, `RESUME.md` | `lead-status.sh`, project-wiring "measure commands" | session-start hook (`session_status.py`) |
| 2 | Live state registry and journal | 09 §2, handbook §6 | `lane-journal.sh` | sub-agent stop hook (`subagent_stop.py`) |
| 3 | Filling lanes, admission, lane cap | 09 §3, `/run-project` | `plan_lanes.py`, `lane-worktree.sh`, `lead-status.sh`, project-wiring "capabilities record" | registry lines |
| 4 | Agent briefs | 09 §4, `<lead>/brief-common.md` | — | the journal (reports stand alone) |
| 5 | Per-lane pipeline, model routing, sub-agent lifecycle (resume the same agent per task and role), rate-limit fallback | AGENTS.md §6, 09 §5, agent contracts | project-wiring "usage clock and throughput" | the lane journal |
| 6 | Loop guard | AGENTS.md §6, 09 §6 | — | 05 + registry |
| 7 | Merge trains and the `docs(memory)` fold (`merge-trains.md`) | 09 §7, `integrator.md` | project-wiring "the project gate", project-wiring "deployed-instance objects" (residue per lane) | project-wiring "git hooks", the gate |
| 8 | HITL | AGENTS.md §4bis, 09 §8 | — | active-context "Open HITL" |
| 9 | Talking to the owner | 09 §9 | `plan_lanes.py` | — |
| 10 | Disk duties | AGENTS.md §10, 09 §10 | project-wiring "measure commands" | the project's alert, read at session start and in the train report |
| 11 | Safety layer: guard, override, logs, allowlist, git hooks | 09 §11, handbook §3.4/§7 | the hooks, project-wiring "permission log", project-wiring "secret scanning" | the runtime's hook settings, project-wiring "git hooks" |
| 12 | Deployment operations (lead only) | 09 §12, handbook §5.12 | the stack's | registry line, health check |
| 13 | Pause and resume | 09 §13, `/pause-project`, `/resume-project` | `pause-flag.sh` | `pause_guard.py`, `subagent_stop.py`, `lead_stop.py` |
| 14 | Close-out (milestone, project) | 09 §14, `/close-project` | project-wiring "deployed-instance objects" (closing, final), project-wiring "secret scanning", `trace_check.py` | the final report |
| 15 | Duration control and throughput | AGENTS.md §11, 09 §15, `integrator.md` | project-wiring "suite timings and duration control", project-wiring "usage clock and throughput" | train reports, speed-up tasks |
| 16 | Keeping the repository current (owner rules, plan rows, metalearning, handbook) | 09 §16 | `metalearning.py`, `handbook_drift.py` | `lead-status.sh` warnings, the drift check |
| 17 | Lane hygiene | 09 §17, agent contracts | — | the guard |
| 18 | Remote runner and heavy runs | AGENTS.md §9, 09 §18 | project-wiring "remote runners" | project-wiring "light and heavy suites" |
| 19 | Freshness | 09 §19 | the stack's freshness check | milestone closure |
| 20 | Parity registration | 09 §20 | `trace_check.py` | the gate, close-out |
| 21 | Clean-room and provenance (optional) | 09 §21, `docs/clean-room.md` | the contamination check | the integrator refuses merges without Provenance |
| 22 | Clock | 09 §22 | project-wiring "usage clock and throughput" | the project's records |
| 23 | Mode bootstrap; new work enters the plan | 09 §23, `/run-project` | analyzers, `plan_lanes.py --check` | — |
| 24 | Mutation testing | 09 §24, `tester.md`, `integrator.md` | the stack's mutation wrapper (project-wiring "stack plug-in") | project-wiring "project protections", the gate |
| 25 | Contracts (contract-driven) | AGENTS.md §4, 09 §23 and §25, 02 | the stack's contract lint | the gate, the reviewer |
| 26 | Residue (per lane, milestone, final) | AGENTS.md §4, 04 register | project-wiring "deployed-instance objects" | the integrator |
| 27 | Metalearning upkeep | 09 §16.4, 10 | `metalearning.py` | every report's trace |
| 28 | Correspondence closes to zero | AGENTS.md §12, 09 §26, 02/03 markers | `trace_check.py` | integrator report every train; `/close-project` (0 mismatches) |
| 29 | Memory blocks (write) and recall (read) | AGENTS.md §4 and §14, 09 §16.4 and §27, `memory-bank/README.md` | `memory_write.py`, `memory_lint.py`, `memory_search.py` | `memory_check.py` (`post-tool`), `memory_recall.py` (`post-tool-failure`), every report's `Memories used:` |
| 30 | Sub-leads and lead-only powers | 09 §28, `.boa/agents/sub-lead.md` | `lead-status.sh`, `lane-worktree.sh` | the registry's owning lead, the plan's `managed by` |
| 31 | Test evidence: both directions, real inputs, plants, budgets | 09 §29, builder/reviewer/tester contracts | the suites' case filters | the reviewer, the tester |
| 32 | Project wiring and measuring as periodic tooling work | 09 §30, `references/project-wiring.md` | the project's own tools | seeded plan rows, every train's review |
| 33 | Languages (product vs user) | AGENTS.md §1/§4, 09 §31 | `boa language set` | the reviewer |
| 34 | Final requirements review | 09 §14, `/close-project`, `references/close-out.md` | — | the independent reviewer's walk at zero open rows |

When a procedure changes in a project, it changes in 09 (and the handbook) in the same train. When BOA itself
learns a better procedure, it changes the template and this catalogue together.
