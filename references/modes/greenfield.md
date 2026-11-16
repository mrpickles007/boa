# Mode `greenfield`: from an IDEA to contracts to a plan

Input: the idea, an idea or architecture document of what to build: a file the user names (any name or path), or, with
no file, what the user said in the conversation, which the lead writes into `IDEA.md` in the project and the user
confirms before anything goes on (SKILL.md, step 2). BOA is contract-driven: the bootstrap
produces **contracts before any build task** (`references/workflow.md`, "Contracts").

## Bootstrap (the first tasks of `run-project`, run through the normal pipeline)

1. **Read the IDEA in full.** List every goal, constraint, user, external system and open question. Questions
   that only the user can answer become one HITL round (options + recommendation); everything else the lead
   decides by the standards and records as ADRs.
   A short IDEA is never a reason for thin specs or for guessing: derive all the specifications from it (steps 3 to
   5: requirements, contracts with their clauses, edge cases, acceptance criteria), raise every gap as a HITL with
   alternatives and a recommendation, and keep working on what is not blocked.
2. **Stack**, if the IDEA does not fix it: `references/stack-choice.md` (latest stable, verified online, ADR).
3. **Project brief** (`memory-bank/00-PROJECT-BRIEF.md`): north star, why, who, scope and out of scope, hard
   constraints, open blockers.
4. **Blueprint** (`memory-bank/01-BLUEPRINT.md`): the functionality map, every feature with an ID, and a
   verification backlog of the `?` items still to settle.
5. **Specifications and contracts** (`memory-bank/02-SPECIFICATIONS.md` + `docs/specs/`, contracts under the
   project's contracts directory): for every feature its behaviour and acceptance criteria, and the contracts it
   exposes or consumes — API contracts (e.g. OpenAPI/AsyncAPI/protobuf), schema specs (tables, columns, keys,
   migrations policy), protocols and file formats, module interfaces, error models, limits. A contract is precise
   enough that a builder and a tester agree on it without asking. Third parties that will depend on a contract
   are named in it.
6. **Architecture** (`memory-bank/04-ARCHITECTURE.md`): modules and their boundaries, data flow, the environment,
   the residue register. **Security** (`memory-bank/07-SECURITY.md`): threat model and standing checklist.
7. **Implementation plan** (`memory-bank/03-IMPLEMENTATION-PLAN.md`): tasks small and independent, each with
   acceptance criteria, dependencies, size, delicate flag, lane and hotspot; **spec-side tasks first** (the specs
   and contracts each build task needs), then build tasks that implement and test against them; the parity file
   lists every feature with its tasks. Check it with the plan tool, then fill the lanes.

Builders never invent a contract: a gap goes back to a spec task. A contract changes only through a task that
updates the spec, the contract and its tests together, with an ADR stating its compatibility impact for every
change (OR-48).
