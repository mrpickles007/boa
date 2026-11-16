## After a compaction (context-gate): sub-agent

If your context was compacted, your summary may be lossy. Before acting: re-read your brief's files, your lane's
`.lane-resume/<role>.md`, the worktree and git (they win over the summary). When in doubt about what was said or
decided, read your own raw transcript, which stays on disk append-only (the L0 for sub-agents), then `grep`/`sed -n
'a,bp'` the lines you need, never reconstruct them from memory. Where it is:

- Claude Code: `grep -l '<your task id>' ~/.claude/projects/{{BOA_CLAUDE_PROJECT_DIR_NAME}}/*/subagents/agent-*.jsonl`,
  newest first (`ls -t`); yours is the one whose first line is your own brief.
- Other runtimes: {{BOA_SUBAGENT_TRANSCRIPT_LOOKUP}}
