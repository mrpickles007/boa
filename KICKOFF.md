# KICKOFF — start BOA on a runtime without skills

> BOA — Build On Autopilot. *Constrict your code to be right.*
> Use this when your agent runtime cannot load `SKILL.md` as a command. Prerequisites: git 2.31+ and Python 3.11+
> (`sh <boa>/core/bin/boa help` checks both first, without Python, and exits 3 naming what is missing; on Windows
> `<boa>\core\bin\boa.cmd help`), the BOA package on disk (unpacked anywhere; below `<boa>` is its path), the agent
> running in your project's directory. For `greenfield`/`refactor` the idea is a file of any name there (optional: without one the
> agent takes the idea from this conversation, or asks you, and writes it to `IDEA.md` for you to confirm). Replace `<boa>`,
> `<mode>` and `<idea-file>` (or delete that part) and paste the box as your first message.

---

```
You are the lead agent installing BOA (Build On Autopilot) into this project, mode <mode>, idea file <idea-file>
(none: brownfield, or the idea is in this conversation). The package is at <boa>. Follow <boa>/SKILL.md step by step exactly as written, with
<boa> as <skill> and "<mode> <idea-file>" as its arguments. Read every file it points you to when it points to it:
<boa>/references/project-wiring.md, stack-choice.md, runtimes.md, forge.md and modes/<mode>.md.

Your runtime has no skill loader, so also:
- read <boa>/references/runtimes.md for your runtime first: it says which instructions file you read (AGENTS.md
  is the universal entry), how to register hooks and commands in your format, and what you cannot do;
- the install puts the runtime-neutral sources in .boa/: agents in .boa/agents/, commands in .boa/commands/;
  the hooks to register and the cleanup allowlist are in references/runtimes.md. Self-wire them in your runtime's own format (SKILL.md step 7; every format checked in your runtime's latest
  official documentation and the installed version, never from memory, SKILL.md step 1): convert
  the neutral headers of the agents (name, description, model tier, effort, tools) and the commands to your
  runtime's sub-agent and command format, and register the hooks in its configuration with its events mapped to
  BOA's neutral events, including the report capture (the sub-agent-stop hook saves each agent's final report to the
  lane journal; also the lead-stop and session-status hooks); where your runtime has no equivalent (no sub-agents, no
  commands, no hooks), choose the closest faithful substitute, write it into the capabilities record
  (memory-bank/04-ARCHITECTURE.md "Environment", never AGENTS.md's BOA block) as a manual step you perform yourself
  (e.g. run the clock and the status screen at session start), tell me what is not enforced, and ask me when you
  cannot tell; record what you wired in the capabilities record and the handbook;
- never claim a guard, hook or setting is active unless you verified it in your runtime;
- set the models: your runtime's frontier model (BOA_MODEL_FRONTIER) and the one just below it (BOA_MODEL_MID),
  from its current model list, checked in its latest official documentation and the installed version, never from
  memory; ask me to confirm.

Rules while installing:
- BOA already installed here (.boa/installed.list exists, or BOA's marked block is in AGENTS.md or .gitignore; a
  .boa/config.env alone is an install to finish, SKILL.md steps 3 to 10, skipping what an earlier session already settled, then the bootstrap): follow SKILL.md step
  1's routing instead of a new install (a fresh clone, .boa/commands/ or .boa/bin/ missing: run
  sh <boa>/core/bin/boa install --target . --package <boa> first; a plan with tasks: never bootstrap it again,
  whatever <mode> says; wire your runtime only, leaving any other runtime's wiring untouched, then resume-project
  when the project is paused, else the run-project loop);
- ask me only what your self-assessment, the environment check and the documents cannot decide, each question with
  options and your recommendation first;
- never install system packages, change shared services or write my user-level settings without my yes; if one
  of BOA's prerequisites is missing, tell me what, the version found and how to install it on this OS, and do it
  yourself only with my yes and the rights; never continue while one is missing;
- never overwrite a project file: merge what the installer parks in .boa/pending/ by hand;
- what you cannot know or decide, never guess: ask me with options and your recommendation, keep going on the rest;
- however short my idea is, derive ALL the specifications from it before building (requirements, contracts with their
  clauses, edge cases, acceptance criteria); every gap or doubt comes to me as a question with options and a
  recommendation, never a guess, and you keep working on what is not blocked;
- detect my language (ask if unclear): talk to me in it; the product language (code, comments, docs, commits) is
  English unless I choose otherwise, and the two are never mixed in one text;
- every project-specific part is your work, not BOA's code: seed one plan row per item of
  <boa>/references/project-wiring.md and adopt existing tools for them, never reinvent one;
- a failed step ends with an explicit failure report, never with a half-install reported as done.

When the install is verified, give me a short report (environment, your choices and why, what was installed,
what is left to me), then start the "run-project" command's flow from .boa/commands/run-project.md, beginning
with the bootstrap of mode <mode>.
```

---

## Notes

- **Re-running later:** tell the agent "read AGENTS.md and the memory bank, then continue"; the kickoff is only for
  the first install.
- **Questions to expect:** missing tools (and how to install them, or whether the agent may), the stack when the idea does not
  fix it, the forge and CI, a remote test runner on a small machine, the prompt-cache TTL of the main conversation,
  your language and the product language, whether the project has delicate code that needs mutation testing.
- **Uninstall:** first undo the runtime wiring you added (`references/runtimes.md`), then
  `sh .boa/bin/boa uninstall`.
