# 05 Safety

BOA ships two guards (the destructive-command guard and the pause guard) and the agent-to-task binding; every other
protection is the project's own, written by the agent from the project-wiring checklist. The reference with every
detail: [references/safety.md](../references/safety.md); the cards:
[guard](../assets/templates/agent-handbook.md#tool-card-guard) and
[pause](../assets/templates/agent-handbook.md#tool-card-pause).

## Threat model

The guards are a safety net against **accidents** of the agents working on your machine (also in a mode where the
runtime asks no permission), not a sandbox against an attacker. Any realistic way an ordinary or careless command
gets past a guard, and every way a guard fails open, is a defect fixed and pinned by a test; a deliberate evasion
through a parser corner no agent produces by mistake is a declared limit. Isolation at the operating-system level (a
container, a separate user, a virtual machine) is proposed by the agent and decided by you, never built into the
guards. This model covers only the development guards: the project's product code is reviewed and tested against
real attackers, always.

## The role-aware guard

`guard_destructive.py` judges every shell, file-write and file-read call (the runtime's pre-tool event):

- deletions only on paths that are provably the project's own (a recursive deleter, `find -delete` or `rsync --delete`,
  whose start holds a protected path is judged like `rm -rf` of that start; a `find -L`/`-H` that deletes is refused);
  writes kept inside the project's paths;
- a sub-agent is confined to its own lane: its worktree, the scratch root and its lane's labelled resources; it may
  not read or write another lane or another project, and it never pushes to the main branch. Its metadata changes
  (`chmod`, `chown`, `chgrp`, `touch`, `setfacl`, `chattr`) are writes like any other (`chmod -x` of a git hook would
  turn the hook off), and so are the writers and the git commands it runs from `find -exec`; from `xargs` they are
  refused. Its own lane root is no write target (`chmod 755 .` or `touch .` there is refused). Its git commands that
  write an index, HEAD or a work tree (`add`, `commit`, `reset`, `stash`, `checkout`, `bisect`, ...) never run on the
  main checkout, and it never moves the main branch ref (`update-ref`, `branch -f`, `checkout -B`, `fast-import`, a
  fetch into `heads/main`, ...); a git subcommand or ref name computed at run time (`git $cmd`, `branch -f $b`) is
  refused;
- the scratch root: every level above the task entries (the layout `BOA_SCRATCH_GLOB` describes) is shared and never
  deleted, and a sub-agent deletes there only inside its own `<task>-<role>` entry, never another lane's or a lead
  directory;
- every agent: no `/dev` targets, no force push or deletion of main, no `kill` of every process or a process group,
  no `pkill`/`killall`, reboots, filesystem or partition tools; nobody writes the runtime's own configuration names
  from a shell (`BOA_RUNTIME_CONFIG`), and shell writes to `.boa/` are refused for everyone (the lead edits it with
  its file-editing tools, which are not shell writes, or through the logged override);
- the project's protected-command rules ([Protected commands](#protected-commands)).

**The agent-to-task binding** (`agent_binding.py`) records, when the lead spawns a sub-agent, the agent's id and the
first task id of its spawn description; the guard and the pause guard read it to keep the sub-agent in its own lane.
An unbound sub-agent stays in the lane worktrees, noted in the log.

A denial is non-blocking: the call is refused with a reason saying what to do instead, and the session goes on. Every
denial is logged in `<BOA_LOG_DIR>/guard-denials.jsonl` (agent, tool and reason; never the command line itself).

## The lead's logged override

The lead (and only the lead) may run a command it has proven safe by starting it with
`<BOA_ENV_PREFIX>GUARD_LEAD_VERIFIED=<reason> ` (one token, then a blank). It is always logged (`OVERRIDE`, or
`ESCAPE` when the guard itself failed), even when denial logging is silenced, and an override that cannot be logged is
refused. A sub-agent never has it. The lead reads the guard log at every train and turns every guard failure into a
reviewed fix.

## Protected commands

The guard knows no database, container engine, service manager or forge CLI. The project protects its own resources
in `.boa/protected-commands.conf` (versioned), one rule per line:

```
<all|lanes> <program>[,<program>...] <pattern> <reason ...>
```

`all` binds everyone, the lead included; `lanes` only sub-agents. Programs are matched after wrappers (`sudo`, `env`,
`nice`, ...), inside `sh -c`, substitutions and `xargs`. The reason says what to do instead. A file that cannot be
read or holds an invalid line refuses every shell command until it is fixed (fail closed). Every rule is pinned by a
test of the project (a command it must refuse, one it must allow), fed to the guard as neutral events, never by running
the command. Worked examples and host protections to adapt:
[references/safety.md](../references/safety.md#protected-commands).

## Failing closed

A guard that cannot judge a call refuses it: a malformed event, an internal error, no verdict within its watchdog
(8.5 s for the guard, 3.5 s for the pause guard), a companion module that cannot load, a size or depth cutoff. The
refusal names the lead's escape. The wiring must fail closed too: a deny, a non-zero exit, an output that is not a
verdict and a timeout all refuse the call; only the logging hooks (status, report capture, memory hooks) may fail
open, so they never stop the session. The session-start status shows a `GUARD DOWN` warning when a safety hook is
not wired or cannot start.

BOA's own tools never write through a path that is not a regular file: an output path that names a device, a pipe,
a socket or a directory (a symbolic link judged by its target) is refused with a message naming it, before anything
is written, and so is such an input file of the memory writer before it is read, so a mistyped path never replaces a
device or hangs a tool.

## The pause guard

While the pause flag exists, `pause_guard.py` lets a sub-agent only save its state (write its resume file, append to
its lane's memories file, read-only git, commit in its own worktree, remove its own scratch, stop its own processes,
hand back its final report)
and denies everything else with the instruction to do exactly that and end its turn
([10 Pause, resume, close](10-pause-resume-close.md#pause)).

## The cleanup allowlist

If you want no removal prompts, the agent adds the cleanup shapes to its runtime's permission allow and deny lists (their format
checked in the runtime's latest official documentation and the installed version, OR-63):
removals under the scratch root and the lane worktrees dir, worktree removal and prune, deletion of lane branches and
of the project's own prefixed containers (only where it uses containers); denied: removals with `..`, of `/`, the home,
`/tmp` or the projects' parent directory. Routine cleanup then runs without a prompt while the guard stays the safety
net; agents clean up in those literal shapes (absolute paths, one removal per command). How per runtime: [references/runtimes.md](../references/runtimes.md#the-cleanup-allowlist).

## Git hooks, secret scanning and main protection

These are the project's own, built by the agent (project-wiring items "git hooks" and "secret scanning"):

- nothing reaches main except a reviewed, merged pull or merge request: server-side protection where the forge
  offers it (set only with your consent and read back; a protection the forge refuses is reported as a gap), else a
  client-side pre-push hook in every worktree; an exceptional escape is explicit and logged;
- Conventional Commit messages checked at commit time by an existing tool;
- the same content rules as a file (secret scanner, forbidden names, product language, trailers) applied to commit
  messages, and to branch and tag names by a pre-push or server-side check, with the project's existing tools;
- the memory lint on every commit that touches the memory bank;
- a maintained secret scanner on the lines each commit adds, and on the whole tree and every ref's history at
  close-out, commit messages and tag annotations included; a finding prints its location and rule, never the secret; a
  missing scanner refuses the commit.

Secrets are never committed, printed or put on a command line. The forge decisions: [references/forge.md](../references/forge.md).

## Heavy runs and wrapped tools

Also the project's own, written as protected-command rules (or a small hook of the project's own where a rule cannot
express it): heavy work (the integration gate, whole suites, mutation runs, suites with services) never runs on the
development machine when a remote runner exists, covering the forms an agent produces by accident (behind a wrapper,
as `sh -c` text, inside a script); and a wrapped tool (typically the mutation tester) runs only through its wrapper or
the project's trusted runners. Nobody loads a shared machine synthetically: "works under load" is proven with an
injected delay or at most 2 workers under `nice -n 19`.

## The permission log

The project's own (project-wiring item "permission log"): every permission request and denial of the runtime,
capped and redacted, private to you, read by the lead at every train to shape the cleanup allowlist.

## Known limits

The guards judge the command text they are given: not the inside of scripts, inline interpreter code, sourced files,
aliases or anything run later; names computed at run time are not resolved; a protected rule judges the command line,
not the input a program reads (a here-document, a pipe, a redirect). On Windows and macOS some letter-case and path
forms are folded and others are not. The guard does not judge git verbs on protected names: a `git rm`, `git mv`,
`git checkout --`, `git restore`, `git stash` or `git reset` that changes any protected name of the main checkout
(`.boa`, the memory bank, the lead directory, the agent runtime's configuration names in `BOA_RUNTIME_CONFIG`) is not
refused; nor are the runtime's configuration names inside a lane worktree, nor the lead's file-editing tools on them; another runtime's wiring is kept by discipline and by the review. The full list:
[references/safety.md](../references/safety.md#known-limits).
