Project instructions for this summary ({{BOA_PROJECT_NAME}}, lead session; edit this file to change them):
- Keep every owner rule and owner directive still in force, quoted short and verbatim with its number (as in the
  project's owner-rules file) and the date it was given; mark a superseded one as superseded and name what
  replaced it.
- Keep the live lane state: for each lane in flight, the task id (`T-` and its number), its stage (build,
  review round, test, train), the head commit, the agent id to resume per role, and the next step. Name the train
  in flight and its order.
- Keep the task count as DONE/total and what is ready to merge.
- Keep open HITL questions, lead decisions taken on spec questions, and new or pending plan rows (task ids).
- Keep the security and safety constraints still binding (other projects, demo or production systems, secrets,
  host load) verbatim.
- Do not keep tool output, file dumps or reasoning that the repo, git or the memory bank already record (the lead
  state lives under `{{BOA_LEAD_DIR}}/` and `memory-bank/`).
