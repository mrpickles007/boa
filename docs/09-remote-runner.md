# 09 Remote runner

BOA ships **no runner code**. A remote test runner is discipline: the project-wiring item "remote runners"
([references/project-wiring.md](../references/project-wiring.md)) that the agent builds for the project, with an
existing tool, as plan tasks under the full pipeline. Nothing in BOA's own tools assumes Linux; the runner itself is
always a Linux server.

## When to use a remote runner

When long test waves are expected (large suites, integration or browser tests, slow builds) or the development
machine is small or shared, the agent proposes a runner (one, or a pool) at bootstrap and you decide; the throughput
review may propose one later ([08 Measuring](08-measuring.md#clock-throughput-and-cost)). `BOA_RUNNER` in the config
says whether heavy runs go to the project's runner (`on`) or stay local (`off`); it stays `off` until a runner
answers.

## What BOA ships and what you build

BOA ships the rule (heavy runs never run locally when a runner is configured, rule OR-32 of the
[rules pool](../references/rules-pool.md)), the checklist item with its guarantees, and the protected-command
mechanism of the guard that refuses the heavy forms locally. The agent builds the rest by adopting an existing way to
run a lane's heavy command there: a self-hosted CI runner, or ssh plus the project's own small scripts (written,
reviewed and tested as plan tasks), and the provisioning of the server for the project's services.

A project may use one runner or several. When the agent wires them it asks you, one question at a time: how many
runners there are and whether each is dedicated to the project or shared, with which projects and who owns their
admission, and how much of each the project may use. The capabilities record keeps one entry per runner (its
capacity, its slots, the project's share); admission, fair share and monitoring work per runner, and the project's
runner command picks the runner with the most free capacity for each run and skips one that is down, saying so.

## What the runner must guarantee

- **Heavy runs off the development host:** it runs exactly what git would commit, streams the output, returns the
  exit status and brings back only the declared results. That is enough: the heavy steps call the stack plug-in
  (`.boa/stack/`) and read `.boa/config.env`, both versioned, while BOA's own checks are light static steps of the
  gate that run where BOA is installed, never on the runner (`.boa/` is git-ignored and never synced); a pool is chosen by free capacity and a runner that is down
  is skipped and reported; a heavy command never falls back to the development machine: with the runner on, its
  command not configured on this machine or no runner reachable, the run stops and the agent reports to the lead
  (the integrator stops the train); with the runner off, the gate runs locally.
- **Admission on the runner itself:** every run takes a ticket in a first-in, first-out queue and waits for a free
  slot; the number of slots comes from the runner's measured capacity (cores, memory) and is recorded; a run weighs
  what it starts (a gate with containers or services counts more than a plain suite) and also waits while the
  runner's load is over a threshold derived from its core count. A runner that already has an admission point (a
  dispatcher, a CI runner's own concurrency) is wired through it, never given a second one.
- **Fair share:** when several projects use the same runner and more than one has queued runs, the slots alternate
  between them; no project holds every slot while another waits, and a project alone may use all of them. The rules
  are agreed with the other projects' owners, never imposed (when a runner is wired you are always asked, one question at a time: dedicated or shared, which projects and whose admission, and how much of it this project may use).
- **Isolation:** an allowlist on the runner accepts only the project's heavy commands; runs are isolated per project
  and per lane (own directory, own labelled resources) and never touch another project on the server. Every identity
  there (run directories, run ids, container, volume and network labels, a shared store such as a cache of git
  objects) carries the project as well as the lane: task ids repeat across projects.
- **Cleanup:** every run removes what it created, also after a failure or an interrupted run; a cleanup or a kill
  selects by project and lane, never by the lane alone.
- **No secrets in logs:** the runner's address and credentials live in a machine-local file outside git, with least
  privilege; logs, reports and briefs never carry a secret.

Done when one suite gives the same output and exit status locally and on the runner, a command outside the allowlist
is refused there, a run (also an interrupted one) leaves no residue, no secret shows in its logs, a run beyond the
free slots waits its turn, and two projects using the same lane id are planted: a cleanup of one leaves the other
untouched.

## Light and heavy suites

Every suite is classed light or heavy, with a reason: light means seconds, with no database, service, container,
network or host side effect; everything else is heavy. Light suites, static reads and targeted tests on explicitly
named files run locally; heavy runs (gate steps that run tests, mutation, whole suites, container and database
suites) run only on the runner when one is configured. The classification is revisited from the measured durations
at every train. The project's protected-command rules refuse the heavy forms locally, including the forms an agent
produces by accident (behind a wrapper, as `sh -c` text). The guards do not judge what runs inside a script
([05 Safety](05-safety.md#known-limits)): where a rule cannot express a form, such as a heavy command run from a
script, the agent writes a small hook of the project's own, tested with payloads (the project-wiring item "light and
heavy suites"). Without a runner, heavy runs stay local, with the parallelism the project's test-execution decision sets, and nobody loads a
shared machine synthetically.

## Where the suites run, decided once

Where the suites run (the development machine or a runner), serial or parallel, and how many at once is decided once,
at project start, with you: the agent proposes it from the measured load of the runner and of the local server (the
local one only, when there is no runner), and records it in the environment record and the handbook. It is then
re-tuned by the rules that already exist (the suite-duration watch, a tooling task when suites grow slow, runner
monitoring, load-based lane admission, no synthetic load), and you are asked again only for a real fork, a spend or a
runner change. The rule lives in the project-wiring item "light and heavy suites".

## Monitoring the runners

The runners' status (load, free slots, queue and wait, disk, cleanup of finished runs) is read at every train with the
project's own commands, against thresholds the project sets for each runner; a runner over a threshold or down is
reported and skipped, and the residue check covers runner runs. A run stopped at its timeout, by an interrupt, by a
hangup or by the end of the agent session is stopped whole on the runner too: the remote command and everything it
started, then its run directory and the resources it labelled
([08 Measuring](08-measuring.md#duration-control)).

## Attack surface and secrets

A runner is remote execution: the allowlist, per-lane isolation and least-privilege credentials kept out of git are
what keep it from becoming an open door. Provisioning or changing a shared server needs your approval (rule OR-43).
