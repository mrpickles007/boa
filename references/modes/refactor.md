# Mode `refactor`: pin today's behaviour, then change it on purpose

Input: the existing repository and the idea, which says what the refactor must achieve (a new runtime version,
a new architecture, removed debt, performance, security, a port to another stack): a file the user names (any name
or path), or, with no file, what the user said in the conversation, which the lead writes into `IDEA.md` in the
project and the user confirms before anything goes on (SKILL.md, step 2).

## Bootstrap

1. **Brownfield first**: run the whole `references/modes/brownfield.md` bootstrap — inventory, analyzer fan-out
   reading every line, architecture, the contracts the code honours (including what third-party clients depend
   on), **characterisation goldens that pin current behaviour**, and the rules reconciliation when BOA was installed
   with `BOA_AGENTS_BLOCK=pointer`.
2. **Target as contract changes.** Read the IDEA in full and express its target against the observed contracts:
   for each contract, kept as is (the default), changed (what, why, who is affected, migration path) or removed.
   Every change and removal is an **ADR**; the specs and contracts are updated in the same task, and the goldens
   that pin a changed behaviour are re-recorded by that task only, never silently.
3. **Plan**: refactor steps small enough to keep the goldens green at every merge; spec-side tasks first; the
   delicate paths (security, data access, migrations, money, concurrency) flagged for mutation testing.
4. **Preserve behaviour, not shape**: do not port duplication, dead code or accidental complexity; keep each
   change reviewable and behaviour-neutral unless its task authorises the change.

## After the bootstrap: every new feature goes through BOA

A refactor does not end at the last refactor step: every new feature and every later change to the product goes
through the full BOA flow (a plan row, contract clauses first, builder → adversarial reviewer → tester → integrator,
a merge train, memory and traceability), with no bypass because the code predates BOA. Existing code a new feature
touches gets its contract clauses and goldens first, so the change is reviewed and tested against them (a new
contract is added; a changed one is an ADR, as above).

## Optional module: clean-room (refactoring code you may not copy)

When the original code belongs to a third party and its licence does not allow copying it into your product,
enable the clean-room module and record the decision as an ADR:

- **Two sides.** Spec-side tasks may read the original (readable artefacts only) and write specifications,
  contracts and goldens **in their own words**; build-side tasks never read the original and work only from
  those specs, contracts and goldens. Reviewers may compare against the original only to detect contamination.
- **Sources.** A written list of allowed and forbidden sources (e.g. decompiled or leaked copies of the original
  are forbidden for everyone, always, also when a web search returns them); an accidental read is reported and the
  lead decides whether the work is redone in a fresh context.
- **Provenance line** on every task and PR: the sources consulted and "forbidden sources used: none" (or what and
  when).
- **Copy check** in the gate: no byte-identical copy of the original's files (by content hash) in any commit
  since the start, and the original never in a build output.
- **Untrusted original**: scan an untrusted source archive for malware before anyone reads it; run the original
  only black-box, in an isolated sandbox without network egress, to record goldens.

The clean-room module is a mitigation of legal risk, not legal advice; say so to the user.
