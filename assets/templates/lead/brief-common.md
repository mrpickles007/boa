## Common rules for every {{BOA_PROJECT_NAME}} lane agent (paste into every brief)

### For the lead, before sending a brief (OR-16, sub-agent lifecycle)
- Same task and role as a recorded agent → do NOT spawn, unless 09 §5.3 calls for a fresh one (large context, piled-up
  rounds, expired cache): resume that agent by its id (the way your
  runtime allows; capabilities record) with
  the round's delta (findings, failures, the new head). New task or new work → spawn a new agent (its description
  starts with the
  task id, so the agents registry records it: task | role | agent id | model | started | state;
  project-wiring "usage clock and throughput"). Lost agent → a new one of the same role, given `.lane-resume/<role>.md` + your notes since. Train
  integrators: resumed for
  the same train, new for a new train.

### Generic (BOA; change only through an owner rule)
- Follow `AGENTS.md` (binding), the agent handbook and your agent definition; 08 and 09 are binding.
- Read the Modus operandi at the top of `AGENTS.md` first; it is the mood behind every rule.
- **Identity first:** your task id, worktree, branch, base and head SHA, your scratch subdir
  `{{BOA_SCRATCH_ROOT}}/<task>-<role>/`. Work only there.
- **Targeted runs only** (OR-03, OR-30): the tests your change touches (a suite "touches" it only if it reads or pins
  a file you changed — check with grep), the gate's static steps on the changed paths; builders and reviewers run no
  mutation; the tester's run is the lane's only one, through the stack's mutation wrapper (changed lines, covering tests,
  caps, receipts; OR-29). Heavy suites as the project's test-execution decision says (project-wiring "light and heavy suites"); while a train gate runs, only light work.
- **Heavy runs** (OR-32, `BOA_RUNNER={{BOA_RUNNER}}`): with the runner on, every heavy run goes through
  the project's runner command (project-wiring "remote runners"); with the runner on, its command not configured on this machine or not reachable: STOP and report, never a local fallback; with the runner off, heavy runs run locally.
- **No synthetic CPU load** (OR-05): an injected delay or at most 2 burners under `nice -n 19`.
- **Never touch** the project's deployed instance, other projects, or the host (`/dev`, `/etc`, services, package
  managers) (OR-10). Never print or commit secrets; passwords via the environment, never argv (OR-41).
- **No permission prompts from deletes** (OR-11): never `rm` with a glob, a variable path or inside a compound line;
  write each run into a fresh `mktemp -d` dir under your scratch subdir and remove your whole subdir ONCE at the end
  with one literal `rm -rf /abs/path`. Create the scratch dir first and check it
  (`d=$(mktemp -d "$SCRATCH/x.XXXXXX") && [ -n "$d" ] && [ -d "$d" ] || exit 1`); `set -u` in helpers; never write at
  `/` or outside your worktree and scratch.
- **Containers** (when the project uses a container engine): throwaway ones are removed on exit, named
  `{{BOA_NAME_PREFIX}}<task>-<what>` and labelled `{{BOA_LABEL_KEY}}=<task>`; never the deployment's own project or
  labels.
- **The guard hook may refuse a command: adapt, don't work around it.** Guard and destructive-path work is tested
  only on JSON payloads or in a throwaway container (OR-24).
- **Edit files with the runtime's file-editing tools**, not inline interpreters; helper logic in a script file run as
  `bash /abs/script.sh`; no compound `cd <main> && …`, no nested `bash -c` quoting.
- **Before editing any doc, contract, spec or agent text,** grep the suites that pin it and run them in the same
  change. Shell changes: shellcheck (and the stack's shell lints) on the changed files.
- **Built-in → extend → from scratch** (OR-07); **tiny fixes** in your own module are absorbed, anything else is a
  follow-up for the lead (OR-28).
- **Handbook** (OR-26): any tool, hook, command, suite, path or procedure change updates `docs/agent-handbook.md` in
  the same commit.
- **Commits:** conventional, atomic (OR-42), ending with the trailers your project's rules ask for, if any (a model
  trailer names the model you really run on, OR-27); do not push (the integrator does). Add a `05-PROGRESS.md`
  entry. Never edit `memory-bank/active-context.md`; ADR and EDR numbers come from the lead. Clean-room projects: the
  `Provenance:` line in the main commit body and in the 05 entry.
- **Clock:** the project's clock (project-wiring "usage clock and throughput"): start, long steps, end, and the elapsed
  line in your report.
- **Pause:** if the pause guard refuses your calls, write `.lane-resume/<role>.md`, commit wip, end
  your turn.
- **Memory recall** (OR-51): search the memory (`.boa/tools/memory_search.py`) at start and on any error, refused
  command or surprise; follow or supersede what you find; cite `Memories used: <ids>` in your report.
- **Report** (stored verbatim by the journal hook, so it must stand alone): commits, acceptance → test map, test
  results with times, decisions to review, open questions, residue, elapsed, and a **metacognitive trace** as
  `@@@memory` blocks (OR-50) (2–5
  lines: mistakes, surprises, what slowed you, lessons about the way of working; OR-35), `Memories used:` (the ids,
  or none) and, last, the `Leftovers:` section (every open item with its owner, or `none`).

### Project lessons (the lead appends; each dated, with the train or task that taught it)
- <none yet>
