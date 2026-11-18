---
name: build-on-autopilot
description: "build-on-autopilot (BOA, Build On Autopilot). Constrict your code to be right. An agent skill that teaches and installs a complete, proven working discipline for building software end to end with a lead agent and specialised sub-agents (builder, adversarial reviewer, tester, integrator, analyzer) — plan, parallel lanes on git worktrees, reviews, tests, merge trains, a typed project memory with hybrid search, measuring, safety, pause, resume and close — for a new project (greenfield), an existing one (brownfield) or a refactor, plus the few generic tools it needs; the agent wires every project-specific part itself. Invoke explicitly as /build-on-autopilot <greenfield|brownfield|refactor> [idea-file] (installed as a plug-in, the plug-in name prefixes it: /boa:build-on-autopilot)."
argument-hint: "<greenfield|brownfield|refactor> [idea-file]"
disable-model-invocation: true
---
# BOA — Build On Autopilot

*Constrict your code to be right.* (Logo: `docs/assets/logo.png`, a coiled snake with a document and the wordmark "BOA - Build on autopilot".)

## What BOA lets you do

BOA lets you, the agent, run a project end to end: start it, work, pause, resume and close it. You do it with:

- a plan as the single source of work, with parallel lanes on worktrees;
- builder → adversarial reviewer → tester → integrator, and merge trains that land the lanes;
- a built-in memory with hybrid search, so nothing learned is lost between sessions;
- guards against destructive accidents, with rules you write for the project;
- traceability from every requirement to a test, walked to zero open rows at close;
- a handbook and a file map of everything you need, and the context-gate that keeps a long session safe;
- HITL: when you cannot know or decide, you ask the user, with alternatives and a recommendation.

Everything project-specific is wired by you from the wiring checklist (`references/project-wiring.md`).

Read the Modus operandi at the top of the installed `AGENTS.md` first (before the install:
`<skill>/assets/templates/AGENTS.md`); it is the mood behind every rule.

You are the **lead**. This skill installs BOA into the project in the current directory, verifies the install
and hands over to `run-project`. `<skill>` below is this skill's base directory (the runtime tells you where it
loaded this file from). Every command here goes through BOA's one entry point, `boa <subcommand>`: before the install
`sh <skill>/core/bin/boa`, after it `sh .boa/bin/boa` (on Windows `<skill>\core\bin\boa.cmd` and `.boa\bin\boa.cmd`);
`boa help` lists the subcommands.

Arguments: `$ARGUMENTS` = `<mode> [idea-file]`: a file with the idea, of any name or path, is optional (step 2).

| Mode | Needs | Bootstrap after the install (`references/modes/<mode>.md`) |
|---|---|---|
| `greenfield` | the idea: what to build (a file, or the conversation) | IDEA → blueprint → specs + **contracts** → plan (spec-side tasks first) |
| `brownfield` | an existing repository | analyzer fan-out reads every line → architecture + the contracts the code honours + goldens; with the pointer block mode, the rules reconciliation |
| `refactor` | an existing repository + the idea: the refactor's target (a file, or the conversation) | brownfield (the rules reconciliation included) + goldens pin today's behaviour; the target becomes contract changes recorded as ADRs |

## Prerequisites (checked first)

BOA needs **git 2.31+** (the project must be or become a git repository) and **Python 3.11+** (BOA's tools use the
standard library only), plus your agent runtime; on Windows, Git for Windows. `boa install` also builds the memory
search environment: a venv of BOA's own in `.boa/embed/` (that Python's venv module and network access to the package
index and the model hub; about 480 MB and half a minute; behind a proxy, set `HTTPS_PROXY`, credentials included,
because the download runs with a redirected home where `~/.netrc` is not read); when that step fails it says what is missing, the rest stays installed, and you
ask the user how to provide it, then re-run the install. The launcher checks
both before anything else, without Python: when one is missing or too old it changes nothing and exits **3**, naming
what is missing and the version found. Then: tell the user, in their language, what is missing, the version found and
how to install it on this OS (verify the current way now); with their yes and the rights to do it, write the steps for
this OS yourself, show them and run them; otherwise the user runs the steps you gave. Check again; never continue
while one is missing.

## Rules for this flow

- Ask the user **only** what your self-assessment, the environment check and the documents cannot decide: one question at a
  time, with options and your recommendation first. Never guess an unknown: stop that item, ask, and keep going on
  the rest.
- Never reinvent the wheel: for every project-specific part, use the built-in feature, extend it or adopt an
  existing library or tool whose upkeep is cheap against the benefit; write from scratch only for a proven gap.
- Keep the two languages apart: the product language (code, comments, docs, commits; default English) and the
  user language (the conversation with the user, memory content, the free text of reports, plans and notes); the
  memory syntax is always English.
- Everything project-specific is discipline, not shipped code: after the install, every item of the project-wiring
  checklist (`references/project-wiring.md`) becomes a plan row that `run-project` works under the full pipeline.
- Never install system packages, change shared services or write **user-level** settings without the user's
  explicit yes; never continue while one of BOA's prerequisites is missing.
- Never overwrite a project file: the installer parks conflicting renderings in `.boa/pending/` and you merge them
  by hand, showing the user what changes.
- BOA provides the tools and hooks; you wire them into your runtime. The installer writes no runtime directory
  and no runtime setting.
- Stop with an explicit failure report if a step fails; a half-install is never reported as done.

## Steps

1. **Capability self-assessment (first).** Before anything else, assess what your runtime gives you, by
   checking it (its latest official documentation and the installed version: `--help`, settings schema, a harmless
   trial), never from memory: hooks and
   their events, sub-agents and parallelism, background tasks, worktrees, a model choice per sub-agent, permission
   modes, scheduling, network access, tools and limits. From it, decide how you implement each part of the
   discipline (pipeline roles, lanes, guards, clock, pause/resume, context-gate), declaring every substitute you
   use and every part you cannot provide (never fake one). Find the context window of the model each role runs on
   (the runtime's or the model provider's latest official documentation and the installed version) and record it in
   the capabilities record next to the role's model: the lead's rule for starting a fresh agent instead of resuming
   one needs it (09 §5.3; its size trigger is the lower of about half that window and the config's `BOA_AGENT_FRESH_TOKENS`: keep its
   default unless half the smallest window is lower, the user states a cost or speed preference or the usage record
   says otherwise; decide the value here, write it at step 5 (Config) with its decision entry and tell the user, as
   the key's comment says). Whatever you cannot determine yourself you ask the
   user, one question at a time with options and a recommendation: owner (HITL) topics, mutation testing (is
   there delicate code? which tool?), CI, a remote runner, the models, protections. Record the result as the
   capabilities record in `memory-bank/04-ARCHITECTURE.md` "Environment" (versioned with the project; once the
   install of step 6 has written that file; never under `.boa/`, which is git-ignored) and the decisions as decision
   entries. The same check comes first at every later adaptation to your runtime (wiring, re-wiring, an update; OR-63
   in `references/rules-pool.md`): record what you checked, where and when; when the installed version is older than
   the documentation, follow the installed version and tell the user an update exists. A date or version in
   `references/runtimes.md` is evidence of a past check, never a reason to skip one.

   **Instruction-file size cap:** check how much of `AGENTS.md` your runtime puts into an agent's context (the runtime
   profile's "instruction-file size cap") against the installed `AGENTS.md` (or, before the install, the rendered
   size of BOA's block plus the project's own text). If the block would be cut, raise the cap in the runtime's
   project-level configuration when it offers one (verified in its latest official documentation and the installed
   version); otherwise use the pointer block mode (`BOA_AGENTS_BLOCK=pointer`). Say which in the capabilities record.
   The pointer block does not help when the project's own text in `AGENTS.md` (outside BOA's block) already exceeds
   the cap: then the runtime cuts the pointer block too. Tell the user and ask, with your recommendation: raise the
   cap where the user can (a setting of theirs), mark the project trusted where the runtime's project-level cap needs
   that, or move part of the project's own text out of `AGENTS.md` into a file it points to.

   **BOA already installed here?** Installed means `.boa/installed.list` exists, or BOA's marked block is in
   `AGENTS.md` (`<!-- boa:start -->`) or `.gitignore` (`# boa:start`): the test `boa install` uses for a clone
   (BOA's block in `.gitignore`), plus BOA's block in `AGENTS.md` (a clone has
   no manifest: it is not versioned). A `.boa/config.env` alone is not an install (`boa install`'s first run writes only that file and stops): finish the
   install (steps 3 to 10, skipping what an earlier session already settled; a key still empty is asked and filled as
   step 5 says), then bootstrap. Installed, but `.boa/commands/` or `.boa/bin/` is missing (a fresh clone: `.boa/` is not
   versioned but for the project's own files): run `sh <skill>/core/bin/boa install --target . --package <skill>`
   first; it restores BOA's files and adopts the versioned ones. Installed and the plan
   (`memory-bank/03-IMPLEMENTATION-PLAN.md`) has tasks: never bootstrap it again, whatever mode you were given (no
   mode analysis, no new idea, no plan, spec or memory rewrite; `boa install` runs again only to upgrade, repair or
   restore BOA's own files); an installed project whose plan has no tasks yet goes on with `run-project`'s bootstrap,
   which runs only then (`run-project`'s own test). After this self-assessment, when the runtime you run in is not
   one the capabilities record names, or its wiring is absent, wire it (step 7) and add it to the capabilities
   record, leaving the other runtime's wiring untouched (the two coexist), and tell the user what this runtime cannot
   enforce. When the runtime that last worked on the project is not this one, set the per-runtime keys again
   (`BOA_SCRATCH_ROOT`, `BOA_SCRATCH_GLOB` in `.boa/config.env`, from this runtime's profile). Then, paused (`PAUSE`
   in the lead dir, `BOA_LEAD_DIR` of `.boa/config.env`): `resume-project`, never before this runtime is wired; not
   paused: `run-project`'s loop. Until that wiring exists no hook reminds you of this: the installed `AGENTS.md`'s
   read order is the only path (a declared limit).
2. **Arguments, repository and idea.** Validate the mode. The project is the git top level of the current
   directory. No repository: in `greenfield`, offer `git init` and run it on the user's yes; in
   `brownfield`/`refactor`, stop and ask for the right directory. Then the idea:
   - when the user names a file, of any name or path (not only `IDEA.md`), read it in full; a named file that does
     not exist is asked about, never guessed;
   - in `greenfield`/`refactor` with no file, take the idea (or the refactor's target) from what the user already
     said in the conversation, or ask the user to describe it; write it into `IDEA.md` in the project, so it is
     versioned, show it to the user, and go on only after the user confirms it;
   - a short idea is fine: you still derive all the specifications and every doubt becomes a question to the user
     (`references/modes/greenfield.md`, step 1);
   - in `brownfield` no idea file is needed; extra direction the user gives in the conversation (constraints,
     priorities) is recorded in the project's memory or plan.
3. **Check the environment** (never installs anything): the project-wiring item "capabilities record"
   (`references/project-wiring.md`) says what to check and how. Judge whether long test waves are expected from the
   IDEA or the code (large test suites, integration or browser tests, slow builds); where a runner is wired, always ask
   the three runner questions of the item "remote runners" (how many runners, each dedicated or shared, with which
   projects and whose admission, how much of each this project may use). Then:
   - something missing: change nothing else; tell the user, in their language, what is missing, the version
     found and how to install it on this OS (package names verified now). With the rights offer to do it: on a
     yes, write the steps for this OS yourself, show them, run them. Otherwise the user runs the steps you gave
     them. Then check again; never continue while anything is missing.
   - `git config user.email` (or `user.name`) empty: ask for the commit identity (project-local `git config`, never
     global).
4. **Questions** (only those still open after steps 1 and 3), each with your recommendation:
   - project name (default: the directory name), the user language (detected from how the user writes; asked
     when unclear) and the product language (default English; changed later only through `boa language set`); a name
     whose letters have no ASCII form (e.g. Cyrillic, CJK, or Latin letters such as sharp s, L with stroke, O with stroke) gets no default slug: propose a transliteration,
     confirm it with the user and pass it as `BOA_PROJECT_SLUG`;
   - **stack**, when the IDEA or the repository does not fix it: choose from the goals per
     `references/stack-choice.md` (latest stable, verified online now; record the choice as an ADR after
     the install), and confirm with the user only if it is a genuine fork;
   - agent runtime: the one your self-assessment (step 1) found, passed as `BOA_RUNTIME` (`references/runtimes.md`);
   - **where BOA's rules go** (`BOA_AGENTS_BLOCK`): `full` (all of them as a marked block of `AGENTS.md`) is the
     default; in `brownfield`/`refactor`, when `AGENTS.md` already holds the project's own rules, recommend `pointer`
     (BOA's rules in `docs/boa-rules.md`, a short pointer block in `AGENTS.md`, the project's rules winning where
     they conflict until the rules reconciliation of `references/modes/brownfield.md` is done) and ask the user;
     `pointer` also when step 1's size-cap check found that the runtime would cut the full block and cannot raise
     its cap in the project's configuration;
   - **models** (no default ships): pick the runtime's frontier model (builder, reviewer, analyzer) and the model
     just below it (builder-mid, tester, integrator) from the runtime's current model list, verified now, and
     confirm them with the user;
   - **forge** (`references/forge.md`): which forge (`github`/`gitlab`/`none`) and repository, when the check did
     not find them; if the CLI is missing or not authenticated, say how to fix it. Then the forge decisions, one
     question at a time, each acted on only with the user's explicit yes: use a forge remote (create one, or use the
     existing one, asked before the first push or PR/MR); its visibility (propose private or public from the
     project's nature, with the reason; the user decides); server-side protection of main; CI, only when it adds
     value (a yes plans the CI task of the project-wiring checklist, `references/project-wiring.md`: written by the
     agent for this project, triggers, images and pins decided and verified then; BOA installs no CI file). A no
     keeps everything local;
   - which files are the project's user documentation (OR-74 in `references/rules-pool.md`): propose the README plus
     `docs/`, minus the files BOA installs there (`docs/agent-handbook.md`, `docs/boa-notice.md`, `docs/boa-rules.md`,
     `docs/parity/` and, in a clean-room project, `docs/clean-room.md`; `docs/api/` and `docs/specs/` are user
     documentation unless the project decides otherwise); the user confirms or changes it, and after step 6
     you record the result in the handbook's file map (its "Documentation" table);
   - where the suites run, serial or parallel, and how many at once (the project-wiring item "light and heavy
     suites": proposed from the measured load, decided once with the user), which includes the remote test runner
     when long test waves are expected or the machine is small: one or a pool; it is set up after the install
     (the project-wiring item "remote runners"), so `BOA_RUNNER` stays `off` until a runner answers.
5. **Config** (the project-wiring item "Config"): `sh <skill>/core/bin/boa install --target . --package <skill>`
   writes the commented template to `.boa/config.env` when there is none and stops; fill in every answer
   (`BOA_RUNTIME`, `BOA_STACK`, `BOA_MODE`, `BOA_AGENTS_BLOCK`, `BOA_PROJECT_NAME`, `BOA_REPLY_LANGUAGE`, `BOA_FORGE`, `BOA_FORGE_REPO`,
   `BOA_RUNNER`, `BOA_MODEL_FRONTIER`, `BOA_MODEL_MID`, …; `BOA_PYTHON`: the python every hook runs). The scratch root
   and its per-task layout are facts of your runtime: take them from your runtime's profile in
   `references/runtimes.md` (read the real temporary directory your runtime gives you, never rebuild it from memory)
   and set `BOA_SCRATCH_ROOT`. Show the user the resulting `.boa/config.env` briefly.
6. **Install:** `sh <skill>/core/bin/boa install --target . --package <skill>` again (try `--dry-run` first on a
   brownfield/refactor project and show the plan). BOA's agents and commands land under `.boa/` only
   (`.boa/agents/`, `.boa/commands/`); no runtime-specific file ships. Everything it writes outside `.boa/`: `AGENTS.md` (a marked block in an existing one; with `pointer`, only the
   pointer block, and BOA's rules in `docs/boa-rules.md`),
   `memory-bank/`, `docs/agent-handbook.md`, `docs/boa-notice.md` (the attribution BOA's licences ask for: kept while
   BOA's files are in the project), `docs/parity/`, the lead dir, the forge's PR/MR template
   (`.github/pull_request_template.md` or `.gitlab/merge_request_templates/Default.md`), and marked blocks in
   `.gitignore`, `.gitattributes` (BOA's files pinned to LF line endings), `.git/info/exclude` and the project's own
   `memory-bank/04-ARCHITECTURE.md` (the residue register). Read its report: for every `conflict` or `kept` line, merge the rendering from `.boa/pending/<path>`
   into the project file by hand (keep the project's content; add BOA's), then re-run the installer until it
   reports no conflicts left that you have not resolved deliberately. An empty REQUIRED or an invalid value stops it
   with the key named: fix it in `.boa/config.env` and re-run.
7. **Wire BOA into your runtime (self-wire in your runtime's own format)** (a project-wiring checklist item; how per
   runtime, as examples with none the default: `references/runtimes.md`). BOA's agent and command files carry a
   neutral header (name, description, model tier, effort, tools) over a runtime-neutral body: you convert them, BOA
   ships no adapter. Do all of it from what step 1 found, each format, event, field and key checked again in your
   runtime's latest official documentation and the installed version (step 1's rule), then verify it in your runtime:
   - (a) the agents of `.boa/agents/` in your runtime's sub-agent format, with the configured model per tier;
   - (b) the commands of `.boa/commands/` in your runtime's command or prompt format;
   - (c) register the hooks BOA ships (the inventory of event, matcher, command in `references/runtimes.md`) in your
     runtime's configuration, its events mapped to BOA's neutral events, including the report capture: the sub-agent-stop
     hook saves each agent's final report verbatim to the lane journal, plus the lead-stop and session-status hooks;
   - (d) where your runtime lacks one of these (no sub-agents, no commands, no hooks, a hook that cannot deny), the
     closest faithful equivalent you choose under the capability self-assessment, declared and never faked; ask the
     user when you cannot tell;
   - (e) the instructions: ALL rules live in AGENTS.md; only a runtime that does not read it natively gets its own
     instruction file, holding nothing but an import of or pointer to AGENTS.md; and the runtime options
     (permissions, the prompt-cache TTL: sub-agents the highest the runtime allows, the main conversation only with
     the user's yes).
   **Your runtime only:** wire only what this runtime needs, nothing extra, and never modify, move, regenerate or
   remove another runtime's wiring (its hooks, agents, commands, settings or skill copies) unless the user explicitly
   asks, even when it looks stale or duplicated: report what you found and leave it alone. Add the other runtimes'
   top-level wiring names (from the capabilities record) to `BOA_RUNTIME_CONFIG` next to this runtime's. That is a
   partial net: the guard then refuses shell writes and deletions of those names in the main checkout, and only that.
   It does not judge git verbs on them, does not cover them in a lane worktree, does not refuse your own file-editing
   tools, and takes top-level names only (a name holding `/` is dropped, so wiring nested in a shared directory is
   kept by discipline alone): everywhere else the rule is yours to keep (`references/runtimes.md`).
   After upgrading BOA, unwire from your runtime's wiring the hooks of tools no longer shipped (from another
   runtime's only on the user's explicit yes) and remove old BOA copies from `.git/hooks`.
   Merge into a project's own runtime files, never replace them; record what you wired (in the capabilities record
   and the handbook, with the substitutes and what is not enforced) so you can undo it. Plan the rest of the
   project-wiring checklist (`references/project-wiring.md`: git hooks, secret scanning, the project gate, ...) as
   tasks, and wire the context-gate
   (`<skill>/context-gate/`, its own instructions) when the package ships them.
8. **Self-tests:** run the install self-checks:
   the config parses (`sh .boa/bin/boa render --config .boa/config.env --get BOA_PROJECT_SLUG`), the
   manifest `.boa/installed.list` exists, a second
   `sh <skill>/core/bin/boa install --target . --package <skill> --dry-run` reports every file `same` (the
   install is idempotent and complete) apart from the marked blocks, which always report `block`, and the conflicts you kept on purpose, and no prerequisite is missing. Any failure → report and stop.
9. **Commit and forge setup:** record BOA's version (the skill's `VERSION` file) in the
   capabilities record; on a branch named by the configured grammar (or as the initial commit of an empty
   repository), conventional commit `chore: install BOA`. `.boa/` and the lead dir are not
   committed (`.boa/` is git-ignored but for `.boa/config.env`, `.boa/protected-commands.conf`,
   `.boa/memory-types.json`, `.boa/markers.json` and the stack plug-in `.boa/stack/`, which are committed: `boa install` puts the rest back in every clone; the lead dir is
   git-excluded). Then only the forge actions the user said yes to in step 4, in the
   order of `references/forge.md`: create the remote and publish main once (or use the existing one), protect main
   and read the protection back (a protection the forge refuses is reported to the user as a gap, never assumed),
   record every answer in the forge-setup decision record; open the PR/MR if the commit went on a branch.
10. **Hand over:** a short report to the user (environment, capabilities and substitutes, choices with reasons,
    what was installed and wired, what is left to them), then start `run-project`, which begins with the mode's
    bootstrap.

Update: when a new release of BOA is out (the periodic check of the operating procedures, section 30, or the user asks),
follow "Re-installing and upgrading" in the new skill's `docs/02-install-and-wiring.md`: keep a copy of the old skill
directory as the merge base, update the skill through the channel that installed it, show the user the dry run,
install, reconcile every `kept` and `conflict` line with a recorded decision, re-wire your runtime, run the
self-tests, then commit `chore: update BOA to vX.Y.Z`.

Uninstall: first undo the wiring you added to your runtime (`references/runtimes.md`), then
`sh .boa/bin/boa uninstall`: it removes exactly what the manifest lists (changed files are kept and
reported; `--force` removes them too). A manifest written by a pre-release version is refused whole, nothing
changed: remove its leftovers by hand.
