# Mode `brownfield`: reconstruct the architecture and the contracts from the code

Input: the existing repository; no idea file is needed. Extra direction the user gives in the conversation
(constraints, priorities) is recorded in the project's memory or plan. The bootstrap reconstructs what the code **is** and the **contracts it
actually honours** before anyone changes it (`references/workflow.md`, "Contracts").

## Brownfield with existing tooling

A project that already runs its own tooling (guards, a status screen, a journal, a memory bank, a gate, hooks)
gets BOA without a second copy of anything. In this order:

1. **Inventory, before installing.** For every item BOA ships, find the project's existing equivalent, one by one,
   with its file paths: the guards (the destructive-command guard and any heavy-run or mutation guard), the status
   screen, the lane journal and the report capture, the agent binding, pause and resume, the memory bank and its
   block format, the plan and its columns, the gate steps, the git hooks, the residue register, the agent
   contracts, the commands, and the rule files (`AGENTS.md` and the runtime's instruction file). "None" is an answer
   too; a guess is not.
2. **Decide each item.** KEEP-PROJECT (the project's implementation satisfies it; extend it only where BOA's does
   more), ADOPT (the project has none: BOA's is used) or MERGE (one implementation from both). Record every decision
   in the decisions log. Never register a second implementation of the same function on the same event: no two
   destructive-command guards, no two status screens, no two journal writers, no two pre-push hooks.
3. **Wire only what the project lacks**, in the runtime's own format, through the project's own adapter where it
   has one, following the runtime profile and the capability self-assessment (OR-63: the runtime's current
   documentation and the installed version, never memory).
4. **Prepare the files the shipped tools rewrite or lint, before the install.** Legacy memory history goes above the
   `<!-- boa:memory-cutoff -->` line (the memory lint and the id-ledger seed judge only what follows it), and every
   legacy block moved there loses its id: strip `@@@memory-<N>` to `@@@memory`, or convert the block to plain text.
   The id allocator counts only the blocks after the marker, so a legacy id left above it would be reused by the
   next writes; an
   existing residue register gets the `<!-- residue-register:begin -->` / `<!-- residue-register:end -->` lines
   around it. A handover file the project keeps as `<lead dir>/RESUME-LEAD.md` stays the project's: at a pause the
   lead stop hook writes only its own marked block (`<!-- boa:lead-stop:begin -->` ... `<!-- boa:lead-stop:end -->`)
   into it and keeps every other byte of the file as it was.
5. **Skip what existing artefacts already cover.** A bootstrap step whose result already exists is not redone: the
   analyzer fan-out that reconstructs the architecture and the contracts is not needed when specifications, a memory
   bank and a plan already exist. Record what was skipped and why, in the decisions log.
6. **Verify after the install:** no hook registered twice for the same function and event, nothing left unreviewed
   in `.boa/pending/`, every existing guard and suite of the project still green.

## At install: fit BOA to what the project already has

Part of the Config step (project-wiring "Config"), asked of the user when unclear: a project that already keeps its
own guard denial log sets `BOA_LOG_DIR` to a `.boa/<name>` directory of BOA's own, so BOA's logs (the guard's
denials among them) never mix with or overwrite the project's, and the handbook names both; a project that already
has its own prefix for a logged guard override sets `BOA_ENV_PREFIX` to it, so the lead's escape
(`<prefix>GUARD_LEAD_VERIFIED=<reason>`) has one form in the project. Each choice is a decision record.

## Bootstrap

1. **Inventory.** `git ls-files` with line counts per directory; entry points, build files, configs, schemas,
   migrations, scripts, tests, CI, deployment files. Untracked artefacts that matter (dumps, vendored code) are
   listed too.
2. **Fan-out plan.** The lead splits the code into slices by area (module, layer, entry point) sized so that one
   analyzer can read its slice **line by line** in one context, and decides how many analyzers to run in
   parallel. The plan is a table: slice → analyzer → files. Every tracked file belongs to exactly one slice;
   generated or vendored files are listed as such, with the reason.
3. **Analyzers** (read-only, frontier model), one per slice, each reports with `file:line` evidence:
   structure and entry points; data flow and trust boundaries; persistence (schema, queries, any unparameterised
   one); dependencies and runtime assumptions; dead and legacy code; security-relevant paths (authn/authz,
   secrets, crypto, shell/exec, file paths, outbound fetches); **the contracts the slice exposes or consumes** —
   public APIs, endpoints and their exact shapes, CLI flags, file formats, database schema, events, environment
   variables, and especially what third-party clients and integrations depend on; open questions it could not
   settle from the code.
4. **Consolidation** by the lead: `memory-bank/04-ARCHITECTURE.md` (the real structure), `01-BLUEPRINT.md`
   (functionality map), `02-SPECIFICATIONS.md` + `docs/specs/` and the contracts directory (each contract as
   the code honours it today, marked "observed"), `07-SECURITY.md` (threats and known weaknesses). A coverage
   check confirms that every file of the plan was read by its analyzer; an unread file is a gap to close, not a
   detail.
5. **Characterisation goldens** for every contract a third party or a user depends on: recorded inputs and the
   exact outputs of today's code (responses, files, side effects), committed with the tests that replay them.
   They pin current behaviour so later changes cannot alter it silently.
6. **Plan**: improvements and new features enter `03-IMPLEMENTATION-PLAN.md` like any task, spec-side first. A
   plan the project already keeps under its own column names is not renamed: map those names as `aliases` of the
   plan columns in `.boa/markers.json`, through the safe edit of 09 §23 (a copy, checked first, then moved into
   place), then run `.boa/tools/trace_check.py`.

## Rules reconciliation (when BOA was installed with `BOA_AGENTS_BLOCK=pointer`)

The pointer mode is also the suggestion when the project's own `AGENTS.md` plus BOA's full block would exceed the
instruction-file size cap of a runtime that works on the project and whose project-level configuration cannot
raise it (`references/runtimes.md`, the runtime profile): the block is appended after the project's text, so the cap
would cut BOA's rules, its routing paragraph included. The pointer block does not help when the project's own text
in `AGENTS.md` already exceeds the cap: the runtime cuts the pointer block too. Then tell the user and ask, with
your recommendation: raise the cap where the user can (a setting of theirs), mark the project trusted where the
runtime's project-level cap needs that, or move part of the project's own text out of `AGENTS.md` into a file it
points to. A project whose `AGENTS.md` already holds its own rules gets BOA's rules in `docs/boa-rules.md` and only
a pointer block in `AGENTS.md`, which says the project's rules win where they conflict until this task is done. It
is a bootstrap task of its own, planned first and run through the pipeline like any task:

1. **Map.** Read the project's own rules in full (`AGENTS.md` outside BOA's block, and any other instruction file
   the project keeps) and BOA's (`docs/boa-rules.md`, `memory-bank/08-OWNER-RULES.md`). Build the table, one row
   per rule of either side that the other side also speaks about: BOA rule (section or OR id), the project's rule
   (file and line), how they relate (same, BOA stricter, project stricter, contradiction, only one side), the
   decision, the reason.
2. **Decide each row.** **Adopt** BOA's rule (the project's text is changed to it or removed), **adapt** it (one
   rule written for the project, in `AGENTS.md` outside BOA's block or as an owner rule in 08, naming the BOA rule it
   replaces), or **keep** the project's (BOA's rule does not apply here, with the reason). A row that changes how
   the owner works (approvals, publication, money, anything irreversible) is a question to the user with
   alternatives and a recommendation; the rest is the lead's, decided by the standards.
3. **Record.** The table is a decision entry in `memory-bank/06-DECISIONS.md`; the project's files are changed in
   the same task so that `AGENTS.md` no longer contradicts a BOA rule silently. A conflict found later becomes a new
   row of the table, never a silent choice.

Done when every rule of both sides that overlaps has a row and a decision, the user answered the rows that were
theirs, and no contradiction is left unrecorded. The project may stay in the pointer mode; switching to `full` is a
re-install with the new value, after the reconciliation.

Behaviour is preserved unless a task explicitly authorises a change; the goldens prove it. Never break a
contract that third parties rely on; a security fix changes only behaviour no legitimate client depends on.

## After the bootstrap: every new feature goes through BOA

Once the bootstrap is done, the project is no different from a new one: every new feature and every later change
goes through the full BOA flow (a plan row, contract clauses first, builder → adversarial reviewer → tester →
integrator, a merge train, memory and traceability). Nothing is edited outside it because the code predates BOA.
Existing code a new feature touches gets its contract clauses and goldens first, so the change is reviewed and tested
against them.
