<!-- residue-register:begin -->
### Residue register (kept leftovers; zero residue rule OR-09, AGENTS.md §4 "Disk hygiene")
Anything a task leaves behind on purpose is listed here with its owner task and removal step; anything not listed
is residue and must go. The integrator checks each lane with the project's residue check (project-wiring
"deployed-instance objects"), the milestone closure runs it in closing mode, the project close-out in final mode and
empties this list. `trace_check.py` and the residue check read this table: **ID** holds one or more `` `kind:glob` `` (kinds `container`, `network`, `volume`, `branch`,
`remote-branch` = a name; `image` = `repo:tag`, `repo@digest` or a 12-hex id; `worktree`, `dir`, `scratch`,
`backup` = an absolute path). IDs are anchored: only `*` and `?` are wildcards, and a wildcard only in a row owned
by a task whose literal prefix (before the first wildcard) holds that task id plus a separator (e.g.
`{{BOA_NAME_PREFIX}}T-123-*`); rows owned by "lead" are fully literal (the kept worktree of a merged lane whose fold
has not landed is a row owned by
that lane's task, `T-NNN`, removal step "after the next train's fold lands"); a path lies under the
project root, the worktrees dir (`{{BOA_WT_DIR}}`) or the agent scratch root, with no `.`/`..` component and a
literal last component. A literal path that exists but is not met by the scans is reported PRESENT; a row matching
nothing is reported STALE. The final mode requires this table to be **empty** and the project's daemons stopped.

| ID | Item | Owner task | Why kept | Removal step |
|----|------|-----------|----------|--------------|
<!-- residue-register:end -->
