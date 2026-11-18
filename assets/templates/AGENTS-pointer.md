## BOA (Build On Autopilot)

{{BOA_PROJECT_NAME}} is built with BOA, installed with its rules in a file of their own
(`BOA_AGENTS_BLOCK=pointer` in `.boa/config.env`): **[docs/boa-rules.md](docs/boa-rules.md)** holds BOA's
Modus operandi, its read order, its numbered sections and the owner rules (OR-NN) it adopts. Read it in full after
this file. Wherever a BOA file (an agent contract, a command, the agent handbook, the memory bank, a hook's message)
says `AGENTS.md` for one of BOA's rules, sections or its Modus operandi, read it in `docs/boa-rules.md`. The map of
every file and tool: [docs/agent-handbook.md](docs/agent-handbook.md).

**Before anything else.** BOA is installed here: never bootstrap it again once the plan has tasks, whatever door
you came in by. Read this file and `docs/boa-rules.md` in full from disk before acting: your runtime may cut an
instruction file silently (an instruction-file size cap). Fresh clone (`.boa/commands/` or `.boa/bin/` missing):
find the BOA package (a copy installed as a skill on this machine, else ask the user where it is) and run
`sh <package>/core/bin/boa install --target . --package <package>` first. Paused project
(`{{BOA_LEAD_DIR}}/PAUSE` exists): read `{{BOA_LEAD_DIR}}/RESUME-LEAD.md` and follow
`.boa/commands/resume-project.md`. A runtime this project has not worked in: wire it first, leaving the other
runtime's wiring untouched (`docs/boa-rules.md`, "Read order").

**Precedence.** Where this project's own rules (the rest of this file) and BOA's rules conflict, this project's
rules win until the rules reconciliation is done: a bootstrap task that maps every rule of this file against BOA's
(adopt BOA's, adapt it, or keep the project's), records the table as a decision in `memory-bank/06-DECISIONS.md`
and updates this file's own rules to match it. After that, the table says which rule applies wherever the two
still differ; a conflict found later goes back into the table, never resolved silently.
