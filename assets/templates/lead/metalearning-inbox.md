# Metalearning inbox (lead; ingested into memory-bank/10-METALEARNING.md by the train fold, OR-35)
# ONLY the lead's own notes and curations — never copies of lane lessons: those reach 10 through the lane fold (each
# lane's .lane-resume/memories.md). A curation that improves a lane lesson SUPERSEDES it (supersedes="memory-N" once it
# has an id, supersedes-brief in the same batch). One memory block each (OR-50; type lesson, gotcha, trap, heuristic or
# edgecase), formatted with `.boa/tools/memory_write.py --format-only` (no id) into this file; the integrator's train
# fold ingests it (the lead never runs --ingest):
#   @@@memory brief="<one-line lesson>" datetime="<YYYY-MM-DDTHH:MM:SSZ from date -u +%Y-%m-%dT%H:%M:%SZ>" keywords="<task ids T-NNN, tools>" type="lesson"
#   <what happened → the lesson, as a check someone can apply>
#   @endmemory
# Once the train's fold commit is on main (never before: a rebuilt fold must still see these lines; a partly landed
# train is not marked), the lead runs
# `memory_write.py --mark <receipt> --train TRAIN-NNN`, which inserts `# [<UTC time>] Folded by TRAIN-NNN into 10:
# ML-a..ML-b` immediately after the ingested prefix (line N).
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
