# 04 — Architecture

> System architecture, module boundaries, stack, data model, contracts, the environment in use and the residue
> register. Brownfield/refactor: reconstructed by the analyzers from the code, every claim cited `file:line`.
> Changed when structure or environment changes, in the same task.

## Stack (actual versions; the choices are ADRs in 06)
| Layer | Choice | Version (verified YYYY-MM-DD) | ADR |
|---|---|---|---|
| <runtime / framework / database / services> | <…> | <…> | <…> |

## Module map
| Module | Responsibility | Entry points | Depends on | Hotspot id |
|---|---|---|---|---|

## Data model notes
<entities, invariants, ownership, migrations policy>

## Third-party contracts (OR-13: never break)
| Contract | Consumers | Where specified | Compatibility test |
|---|---|---|---|

## Glossary (OR-47: user-facing names ↔ code names)
| User-facing name | Code name | Notes |
|---|---|---|

## Environment (keep current; OR-43)
- Capabilities record (project-wiring "capabilities record", YYYY-MM-DD): OS, privileges, runtimes, container engine, CPU/RAM/disk, network,
  forge CLI and authentication, the lane cap computed from it ({{BOA_LANE_CAP}}).
- In use: <versions, paths, ports, services; what was reused vs installed; containers vs native>.
- Shared machine: <other projects/services present (names only, never their data); ports to avoid>.
- Agent runtime: <runtime and version; hooks it runs; what it cannot do and how the rule is applied instead>.
- Remote test runner: `BOA_RUNNER={{BOA_RUNNER}}` (its address lives only in the runner config, never here).
- Deployment (the project's own instance): <where, how it is isolated, operated by the lead only>.

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

## Disk and footprint (project-scoped)
- Thresholds: {{BOA_DISK_WARN_MB}} MB warning, {{BOA_DISK_HARD_MB}} MB ceiling (project-wiring "measure commands"); trend
  and actions are recorded in `active-context.md`.

## Deployment topology
<components, where they run, how they talk, exposure>

## Memories — invariants and constraints
<!-- Memory blocks of type invariant and constraint (not from the owner) are appended here by `.boa/tools/memory_write.py` (`memory-bank/README.md` "Memory blocks"). -->
