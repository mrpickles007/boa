# 06 — Decision log (ADR and EDR records)

> Append-only. Two kinds of decision records, each one memory block (OR-50, `memory-bank/README.md`):
> - **`ADR-NNN`**, type `adr` — an architectural decision: a choice that shapes the system's structure (stack, module
>   boundaries, data model, protocols, security model, a contract's change with its compatibility impact).
> - **`EDR-NNN`**, type `edr` — an execution decision: a choice about how the work is carried out (a lane ruling, a
>   fix approach, a tool setting, a budget or threshold, a merge or deploy call, a process change).
> The contracts themselves live in `docs/api/` and `docs/specs/` with the 02 contracts index; this log holds the
> decisions about them. Numbers come from the lead (lanes ask, never pick one). A record is never edited: an
> amendment or a reversal is a new block with `supersedes="memory-<N>"`, written through `.boa/tools/memory_write.py`
> (which stamps `superseded-by` on the old one); the old one stays.

ADR block format:
```
@@@memory-<N> brief="ADR-NNN — <title>" datetime="<YYYY-MM-DDTHH:MM:SSZ from date -u +%Y-%m-%dT%H:%M:%SZ>" keywords="ADR-NNN, <task ids T-NNN>, <components>" type="adr"
ADR-NNN — <title>
- Status: proposed | accepted | superseded (by ADR-MMM)
- Context: <why a decision is needed>
- Options: <A / B / C with pros and cons>
- Decision: <what was chosen>, decided by <who>
- Rationale: <why; which principle (first principles, KISS/YAGNI/DRY), which spec or contract>
- Consequences: <trade-offs, follow-ups, compatibility impact>
- Rejected: <what and why>
@endmemory
```

EDR block format:
```
@@@memory-<N> brief="EDR-NNN — <title>" datetime="<YYYY-MM-DDTHH:MM:SSZ from date -u +%Y-%m-%dT%H:%M:%SZ>" keywords="EDR-NNN, <task ids T-NNN>, <tools>" type="edr"
EDR-NNN — <title>
- Options: <…>
- Choice: <what>, decided by <who>
- Why: <…>
- Rejected: <what and why>
- Reversible: <yes/no, how>
- Steps: <if it is a procedure>
@endmemory
```

## Memories — decision records (ADR, EDR)

@@@memory-2 brief="EDR-001 — Way of working: BOA (Build On Autopilot)" datetime="{{BOA_INSTALL_DATE}}" keywords="EDR-001, BOA, pipeline, install" type="edr"
EDR-001 — Way of working: BOA (Build On Autopilot)
- Options: an ad-hoc agent workflow, or the BOA discipline.
- Choice: the BOA discipline as installed (AGENTS.md, the handbook, 08, 09, the role contracts, commands, hooks and
  tools under `.boa/`), decided by the owner at install. Mode `{{BOA_MODE}}`, stack `{{BOA_STACK}}`, forge
  `{{BOA_FORGE}}`, remote runner `{{BOA_RUNNER}}`.
- Why: a lead agent and sub-agents need a pipeline, memory, safety and measuring that survive sessions.
- Rejected: an ad-hoc workflow (no memory across sessions, no safety net, no measured gate).
- Reversible: yes (`/close-project` can uninstall BOA and keep the memory bank).
- Steps: every task follows `AGENTS.md` §6; owner rules in 08; procedures in 09.
@endmemory

@@@memory-3 brief="EDR-002 — Mutation thresholds and duration budgets (defaults)" datetime="{{BOA_INSTALL_DATE}}" keywords="EDR-002, mutation, MSI, budgets, disk" type="edr"
EDR-002 — Mutation thresholds and duration budgets (defaults; the owner may change them)
- Options: no thresholds; uniform thresholds; thresholds per risk class.
- Choice: mutation on delicate paths only (OR-29): MSI ≥ 80 % (covered MSI ≥ 90 %), ≥ 90 % on crypto, licensing,
  tokens and money, 0 skipped mutants. Gate budget {{BOA_GATE_BUDGET_S}} s, per-step and per-suite budgets in the
  budgets file (overrides each with a written reason), dominance threshold {{BOA_DOMINANCE_PCT}} % (OR-20). Disk
  thresholds {{BOA_DISK_WARN_MB}} / {{BOA_DISK_HARD_MB}} MB (OR-08). Decided at install (BOA defaults).
- Why: thresholds per risk class put the testing effort where a silent wrong result costs most.
- Rejected: uniform thresholds (too weak on money and crypto, wasteful on glue).
- Reversible: yes (a new EDR block that supersedes this one).
@endmemory
