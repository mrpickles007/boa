# Lane registry — append-only, one line per stage change, newest line per lane wins
# Format: <ISO UTC time> <task|TRAIN-NNN> <stage> (<head sha>) — <role>, round <n>, <bounce reason | lead decision | HITL | override evidence>
# A stage past its budget: the line carries the token OVER-BUDGET (exactly so) and what was used, e.g.
# "… — tester, round 2, OVER-BUDGET: 3 plant rounds used"; the status screen flags a lane while its newest line has it.
# Agent ids are not written here: the agents registry is their one home (the project's clock, project-wiring
# "usage clock and throughput"). Same task and role -> resume that agent (or a fresh one, 09 §5.3); new work -> a new agent.
