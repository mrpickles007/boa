# Plan rows and notes to fold into memory-bank/03-IMPLEMENTATION-PLAN.md at the next train's docs(memory)
# One memory block each (OR-50), formatted with `.boa/tools/memory_write.py --format-only`
# (no id) into this file and ingested by the integrator's train fold: a new plan row is type `requirement` WITH the
# keyword `plan-row` (the memory-types keyword route `plan-row` sends it to 03-IMPLEMENTATION-PLAN.md; a requirement
# without it goes to 02), postponed work `deferred` (routed to 03), a note on a task the most specific type (edgecase,
# constraint, gotcha, …):
#   @@@memory brief="<task id T-NNN> — <title or note>" datetime="<YYYY-MM-DDTHH:MM:SSZ from date -u +%Y-%m-%dT%H:%M:%SZ>" keywords="plan-row, <task ids T-NNN>, <topics>" type="requirement"
#   <task id> | <MS> | **<title>** (<source>): <scope> | <acceptance> | <deps> | <Del> | <lane> | <hot> | <contract
# / spec>
#   @endmemory
# The lead's own progress and decision blocks (a pause or resume `outcome`, an `adr` or `edr`) are staged here too: the
# fold routes each by its type (05, 06), so the lead never writes those files directly.
# Blocks whose text says "do not fold" are skipped.
# Once the train's fold commit is on main (never before: a rebuilt fold must still see these lines; a partly landed
# train is not marked), the lead runs
# `memory_write.py --mark <receipt> --train TRAIN-NNN`, which inserts `# [<UTC time>] Folded by TRAIN-NNN into 03:
# <ids>` immediately after the ingested prefix (line N).
# The fold boundary is recorded, never guessed: `memory_write.py --ingest` emits an ingest receipt naming, per
# staging file, the ingested prefix of the file (lines 1..N and the sha256 of that whole prefix); once the train's
# fold commit is on main the lead runs `memory_write.py --mark <receipt> --train TRAIN-NNN`, which inserts the
# single-`#` `Folded by TRAIN-NNN`
# marker immediately AFTER line N (refusing when the prefix hash no longer matches), never at the end of the
# file, so lines appended after the fold (during the gate) stay below the marker. The receipt lives with the train
# (the integrator's report and the lead dir), not in the memory bank.
# Drafts are never consumed: `memory_write.py --ingest` never modifies or deletes a draft. A lane's drafts
# (`.lane-resume/memories.md`) disappear with its worktree, which is removed only after the lane's fold has landed;
# the lead's staging files keep the fold marker the lead writes once the fold is on main, which is the record —
# `--ingest`
# reads a staging file only below its last single-`#` `Folded by` marker.
