# 12 Uninstall

Removing BOA takes three steps, in this order: the runtime wiring, the installed files, then whatever the project
built for itself that it no longer wants. At close-out, uninstalling is the very last step, after every check
([10 Pause, resume, close](10-pause-resume-close.md#close)).

## Before you uninstall

Decide what stays: the memory bank (`memory-bank/`), `AGENTS.md`, the agent handbook and the plan are project
knowledge and are usually kept as history. The lead directory and BOA's logs are machine-local. Run
`sh .boa/bin/boa uninstall --dry-run` to see exactly what would be removed and kept.

## Undo the runtime wiring

The installer never wrote a runtime file, so the agent undoes what it wired, from the wiring record it kept (the
capabilities record and the handbook): the hook registrations, its renderings of the agents and commands, the
instruction file pointer, the runtime options (permissions, the cleanup allowlist, the prompt-cache setting). It
removes only its own entries from runtime files the project also uses, never the files. How per runtime:
[references/runtimes.md](../references/runtimes.md).

## Run boa uninstall

```
sh .boa/bin/boa uninstall [--target DIR] [--force] [--dry-run]
```

On Windows `.boa\bin\boa.cmd uninstall`. It removes exactly what `.boa/installed.list` lists:

- the files BOA installed and nobody changed; a changed file is kept and reported (`--force` removes it too);
- BOA's marked blocks, restoring `.gitignore`, `.gitattributes`, `.git/info/exclude`, `AGENTS.md` and your
  `memory-bank/04-ARCHITECTURE.md` byte for byte to what they were without them;
- the directories it created, when empty;
- BOA's machine-local directories: the memory search environment `.boa/embed/`, BOA's state and logs (locks and logs,
  never project knowledge).

A manifest with an entry outside the project, or written by a pre-release version, is refused whole and nothing is
changed: remove its leftovers by hand. Exit codes: 0 done (some files may be kept, see the report), 1 error, 2 usage.

## What stays

- `.boa/config.env`, which the agent wrote for the project: kept and reported; delete it by hand to remove every
  trace (and `.boa/protected-commands.conf` and `.boa/memory-types.json` if the agent wrote them).
- Files you changed since the install (unless `--force`) and files behind a symlink.
- Everything outside the manifest: your code, the project's own wiring (below), the lead directory's content the lead
  wrote after the install.
- What BOA's tools wrote after the install: the memory id ledger (once a memory was written; while it is still as
  the install seeded it, it goes with the installed memories), the lane journals, the pause flag and the lead-status
  bookmark, unless `--force`.

Known limits:

- A file you kept as your own is outside the manifest from then on: an uninstall that kept a changed file, then a
  reinstall that reports a conflict on it, leave it yours, so a later uninstall (with or without `--force`) neither
  removes nor names it, nor the directories that hold it.
- `--force` removes the id ledger even when kept memories still carry its ids; a later install seeds a new ledger
  from them.

## The project's own wiring

What the agent built for the project from the project-wiring checklist is project code, not BOA's: git hooks, the
secret scanner, the project gate, CI, runner scripts, the clock and measuring tools, the residue check. Keep what the
project still wants; remove the rest as normal tasks. Remove old copies of BOA's git hooks from `.git/hooks` if any are
left from an older version.

## Removing the context-gate

Remove the pre-compaction hook entry the agent registered in the runtime's settings and delete `.context-gate/` (its
`conversations/` folder holds the transcript snapshots): [context-gate/SKILL.md](../context-gate/SKILL.md#uninstall).
