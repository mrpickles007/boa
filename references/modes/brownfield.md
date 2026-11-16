# Mode `brownfield`: reconstruct the architecture and the contracts from the code

Input: the existing repository; no idea file is needed. Extra direction the user gives in the conversation
(constraints, priorities) is recorded in the project's memory or plan. The bootstrap reconstructs what the code **is** and the **contracts it
actually honours** before anyone changes it (`references/workflow.md`, "Contracts").

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
6. **Plan**: improvements and new features enter `03-IMPLEMENTATION-PLAN.md` like any task, spec-side first.

Behaviour is preserved unless a task explicitly authorises a change; the goldens prove it. Never break a
contract that third parties rely on; a security fix changes only behaviour no legitimate client depends on.

## After the bootstrap: every new feature goes through BOA

Once the bootstrap is done, the project is no different from a new one: every new feature and every later change
goes through the full BOA flow (a plan row, contract clauses first, builder → adversarial reviewer → tester →
integrator, a merge train, memory and traceability). Nothing is edited outside it because the code predates BOA.
Existing code a new feature touches gets its contract clauses and goldens first, so the change is reviewed and tested
against them.
