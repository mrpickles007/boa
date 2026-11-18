# 13 FAQ and limits

## Honest limits

- **The guards are a net, not a sandbox.** They protect against accidents of the agents, not against an attacker;
  they judge the command text they are given, not the inside of scripts or anything run later
  ([05 Safety](05-safety.md#known-limits)). Operating-system isolation is your decision.
- **Discipline is enforced by the runtime you have.** Where the runtime has no hooks, no sub-agents, no commands or a
  hook that cannot deny, the agent uses the closest faithful substitute and declares what is not enforced (for
  example, without a pre-tool hook that denies, the guards and the pause flag are rules the agents follow, not
  checks).
- **Most of the discipline is the agent's work in your project.** BOA ships few tools; the gate, the git hooks, the
  secret scanner, the runners and the measuring tools are built by the agent from the checklist, and they are as good
  as those tasks were reviewed and tested.
- **Memory search needs its environment for meaning.** Without `.boa/embed/` it ranks by keywords (BM25) alone and
  warns; building the environment needs network access once and about 480 MB.
- **The status screen's admission needs Linux figures.** The memory and load it reads come from `/proc`; elsewhere
  admission is "unknown" and the lead decides from the capabilities record.
- **No hook before the wiring.** A runtime new to the project (a pause resumed in it, a clone) runs none of BOA's
  hooks until its agent has wired it: until then `AGENTS.md`'s read order is the only path to the resume and wiring
  steps, so that file must reach the agent whole (a runtime may cut it at its instruction-file size cap).
- **Runtimes take turns.** Two agent runtimes working on the same project at the same time is not supported (one
  lead, one scratch root); resuming in one after the other has paused is.
- **Another runtime's wiring is kept by discipline.** The guard refuses shell writes and deletions of the runtime
  configuration names in the main checkout only: the lead's file-editing tools, git verbs and lane worktrees are not
  guarded there, so the rule "never touch another runtime's wiring without your yes" is the agents' discipline and
  the reviewer's check.
- **Text checks are heuristics.** The language and no-trace checks of BOA's own files, and the guard's command
  parsing, are documented heuristics, not proofs.

## Locks

- BOA's file locks are operating-system locks (`fcntl.flock` on Linux and macOS, `msvcrt.locking` on Windows):
  released by the system when their process ends, so a crash never leaves a stale lock, and a waiter gives up after
  a timeout naming the lock. A platform with neither is refused; there is no weaker fallback (no lock-file-by-creation
  scheme that would depend on process ids).
- A lock is only as good as the file system's own locking: keep BOA's state and lock directories on a local file
  system of the machine that runs the agents; never share one lock directory between machines or containers.
- On Windows a lock file in use cannot be deleted; the installer removes its lock after releasing it.
- The install lock (`boa-install.lock` in the git directory) admits one install at a time. Known limit: when a run
  removes the lock while a second run waits and a third starts, those two can overlap (three concurrent runs on a
  project with nothing installed).

## Platforms

BOA's tools run on Windows, Linux and macOS: Python standard library logic behind thin POSIX `sh` launchers and
`boa.cmd`, hooks that call Python directly, no symlinks, LF line endings pinned by `.gitattributes`, names compared
case-insensitively where the file system is. On Windows the guards read paths in one form (`\` as `/`, an MSYS drive
path as `C:/...`) and some forms are not folded ([references/safety.md](../references/safety.md#known-limits)). A
remote test runner is always a Linux server.

## FAQ

**Does BOA install anything on my machine?** Nothing outside the project without your yes. `boa install` writes
inside the project only (and builds its own virtual environment in `.boa/embed/`); a missing prerequisite is
explained and installed only with your consent and the rights to do it.

**Which agent runtime do I need?** One that can run a skill, or any agent you can paste
[KICKOFF.md](../KICKOFF.md) into. Runtimes with hooks and sub-agents get the most enforcement; the profiles of known
runtimes are in [references/runtimes.md](../references/runtimes.md), none is the default.

**Which models?** BOA ships no default: the agent picks your runtime's frontier model and the one just below it and
confirms them with you ([04 Roles](04-roles.md#the-model-roster)).

**Which programming languages?** Any. Python is only BOA's own runtime; the project's language lives in its stack
plug-in ([11 Modes](11-modes.md#writing-a-stack-plug-in)).

**Does BOA push or publish anything?** Only what you said yes to: a remote repository, its visibility, branch
protection and CI are each asked separately, and CI is planned with a minutes budget
([references/forge.md](../references/forge.md)).

**Can I change the rules?** Yes: say a new rule and it is written down and folded into the project's rules at the
next train ([06 Rules pool](06-rules-pool.md)).

**Can I switch the documentation language later?** Yes, through `boa language set`, which switches only after every
hook passes on samples in the new language ([07 Memory and state](07-memory-and-state.md#the-language-change)).

**How do I stop everything for a while?** `pause-project`; `resume-project` picks up from the saved state
([10 Pause, resume, close](10-pause-resume-close.md)).

**How do I update BOA?** Ask the agent to update BOA to the new release (it also checks for one periodically). It
keeps a copy of the old skill, updates the skill through the channel that installed it, shows you a dry run, installs,
and merges every file the project changed with BOA's new version, never overwriting yours; then it re-wires its
runtime, runs the self-tests and commits `chore: update BOA to vX.Y.Z`
([02 Install and wiring](02-install-and-wiring.md#re-installing-and-upgrading)).

**How do I remove BOA?** [12 Uninstall](12-uninstall.md).
