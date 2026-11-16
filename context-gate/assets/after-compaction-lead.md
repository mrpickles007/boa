## After a compaction (context-gate): lead

If your context was compacted, your summary may be lossy. Before acting: read the memory bank (resume file first),
the lead state under `{{BOA_LEAD_DIR}}/`, the working tree and git (they win over the summary). When in doubt about
what was said or decided, read your own raw transcript (L0), which the context-gate copied byte-exact to disk at
every compaction (it ends at the last compaction): `grep -l '<a string you know was said>'
.context-gate/conversations/*/session_transcript_*.jsonl`, newest first (`ls -t`), then `grep`/`sed -n 'a,bp'` the
lines you need, never reconstruct them from memory.
