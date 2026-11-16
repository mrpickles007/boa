# Safety: the guards and the project's protections

The development guards (`.boa/hooks/guard_destructive.py` and the pause guard `.boa/hooks/pause_guard.py`). This
reference says what they protect, how they fail, how the agent wires them and how a project adds its own
protections. Secret scanning and git hooks are not shipped: they are project-wiring items the agent sets up with the
project's own tools (`references/project-wiring.md`, items "secret scanning" and "git hooks").

## Threat model

The guards are a safety net against ACCIDENTS of the agents working on this machine, not a sandbox against an
attacker. Any realistic way an ordinary or careless command gets past a guard, and every way a guard fails open (an
exception, a timeout, a size or depth cutoff, an unreadable event), is a defect: fixed and pinned by a test. A
deliberate evasion through a parser corner no agent produces by mistake is a declared limit (below), not a check to
add. Isolation at the operating-system level (a container, a separate user, a VM) is proposed by the agent from the
environment analysis and decided by the user; it is never built into the guards.

This model covers ONLY the development guards. The project's own product code is reviewed and tested against real
attackers, always.

## Failing closed

A guard that cannot judge a call refuses it:

- an event that is not a well-formed neutral pre-tool event (not one JSON object, an unknown event name or tool
  kind, a shell event without a command, a file-write without a path, an ill-typed field);
- a hook not installed inside a checkout (no project to protect);
- an internal error, or no verdict within the guard's watchdog (8.5 s for `guard_destructive`, 3.5 s for the
  pause guard: under the wiring's timeout of 10 s and 5 s); the refusal follows at once (its log line holds the
  reason only, never the command text);
- a verdict stuck in C (a pattern that backtracks without end holds the interpreter lock, so the watchdog thread
  cannot run): a process backstop ends the guard 1 s after its watchdog with exit 1 and no verdict, which the
  wiring refuses;
- a companion module (`hook_config.py`, `shell_lexer.py`) that cannot be loaded: a deny verdict, then exit 1;
- a size or depth cutoff (a command nested past the guard's limits, an oversized command, script or protection
  file).

The refusal names the lead's escape: a shell command of the lead (an event without `agent_id`) that starts with
`<BOA_ENV_PREFIX>GUARD_LEAD_VERIFIED=<reason> ` (one token of 3+ characters of `[A-Za-z0-9_.-]`, then a blank) is
allowed and logged as an `ESCAPE` record, with the token and the failure, in `<BOA_LOG_DIR>/guard-denials.jsonl`.
An escape is always audited: it is written even when
`<BOA_ENV_PREFIX>GUARD_NOLOG=1` (that switch only silences denials and notes, for tests), and an escape that cannot
be written is refused. The same holds for the lead's override on a normal verdict (`OVERRIDE`). Sub-agents never
have it. The lead uses it only for a command it has proven safe, then reports the guard failure so
it is fixed as a reviewed change. A neutral event other than `pre-tool` is not judged (no output).

The denial log (`<BOA_LOG_DIR>/guard-denials.jsonl`) holds agent, tool and reason (at most 500 characters); a reason
can quote a path or an argument, and the command line itself is not stored.

## Wiring the guards

The agent registers each guard on its runtime's pre-tool event and pipes it the neutral event
(`references/hook-contract.md`):

| Guard | Tool kinds | Fields it reads | Timeout |
|---|---|---|---|
| `guard_destructive.py` | `shell`, `file-write`, `file-read` | `tool_input.command`; `tool_input.file_path`; for file-read also `path` (a directory searched) and `glob` (a path pattern searched); `agent_id`, `agent_type`, `cwd` | 10 s |
| `pause_guard.py` | every kind | `tool_input.command` (shell), `tool_input.file_path` (file-write), `agent_id`, `agent_type`, `cwd` | 5 s |

A guard prints `{"decision": "deny", "reason": …, "context": "", "message": ""}` to refuse, or nothing to allow,
and exits 0. The wiring must fail closed as well: it maps a deny verdict to the runtime's refusal of the call, and
it refuses the call too when the hook exits non-zero, prints something that is not a verdict, or times out (a
runtime whose default treats a crashed hook as "allow" needs that mapping written explicitly). The adapter passes
only the fields of this table (never a written file's content: an event over 4 MiB is refused, so a large file write
would be), and maps each tool's own field names onto them (NotebookEdit's `notebook_path` is the `file_path`, a
path-search tool's pattern is the `glob`).

## Protected commands

The guard knows no database, container engine or service. A project protects its own resources by writing
`.boa/protected-commands.conf` in the main checkout (a project-wiring item, done at bootstrap and whenever the
project adds a resource). One rule per line, `#` comments:

```
<all|lanes> <program>[,<program>...] <pattern> <reason ...>
```

- `all`: everyone, the lead included; `lanes`: sub-agents only.
- programs: basenames, matched after wrappers (`sudo`, `env`, `nice`, …), inside `sh -c`, substitutions and
  `xargs`; a wrapper or a shell is a program too (a rule on `sudo`, `nohup`, `timeout`, `bash` or `xargs` sees the
  whole command from that word on). A shell keyword (`if`, `then`, `do`, `coproc`, …) is never a program the guard
  sees: a rule on one makes the file invalid.
- pattern: a Python regular expression without blanks (`\s` for whitespace), searched in the command's text: the
  program's basename and its arguments joined by single blanks, quotes removed. A text over 8192 characters of a
  program that has rules is refused, never truncated. Prefer patterns without nested repetition (`(a+)+`): one that
  backtracks without end is ended by the guard's backstop, which refuses the call.
- reason: shown in the refusal; say what to do instead.

Worked example (a project with a database server and containers named after the project's name prefix `acme-`):

```
all mysql,psql (?i)\bdrop\s+(database|schema|user|role)\b the server holds other projects' data: drop inside the lane's own database container
lanes docker ^docker\s+((container|volume)\s+)?(rm|stop|kill)\s(.*\s)?(?!-|acme-)\S lanes remove only their own containers (acme-*)
all docker ^docker\s+(\S+\s+)?prune\b(?!.*\s--filter[\s=]label=acme\.lane=) a prune touches every project: add the lane filter
```

### Host protections

The guard keeps the protections that name no tool in code: deletions and writes outside the project's paths,
another lane or another project, git's main branch and force pushes, `/dev` targets, `kill` of every process or a
process group, `pkill`/`killall`, reboots, filesystem and partition tools. Everything that names a specific service
manager, package manager, firewall, scheduler or forge CLI is the project's to register, for the tools its machine
and forge actually have. Examples to adapt (a Linux host with systemd, apt, pip, snap and the usual firewalls, and a
GitHub or GitLab forge); keep the lines that fit, write the ones your platform needs instead:

```protected-commands
# host protections (examples)
all systemctl,service \s(stop|restart|disable|mask|kill|reload|daemon-reload|isolate|reset-failed)\b the host's services belong to the machine's owner: ask (HITL)
all apt,apt-get,aptitude \s(remove|purge|autoremove)\b removing packages changes the shared host: ask (HITL)
all dpkg \s(-r|-P|--remove|--purge)(\s|$) removing packages changes the shared host: ask (HITL)
all snap \sremove\b removing packages changes the shared host: ask (HITL)
all pip,pip3 \suninstall\b removing packages changes the shared host: ask (HITL); use the project's virtual environment
lanes apt,apt-get,aptitude,dpkg \s(install|upgrade|dist-upgrade|full-upgrade|-i)(\s|$) installs on the host need the owner's approval: use a container
all crontab ^crontab(?!(\s+-u\s+\S+)*\s+-l(\s+-u\s+\S+)*$) the host's crontab is not the project's: list it with -l only
lanes ufw,iptables,ip6tables,nft,iptables-legacy,iptables-nft \s(-[AIDFXPNRZEf]|--(append|insert|delete|flush|delete-chain|policy|new-chain|replace|zero|rename-chain)|add|delete|flush|insert|replace|create|destroy|rename|reset|allow|deny|reject|limit|enable|disable|reload)(\s|$) firewall changes on the host are not for lanes (listing is fine)
all gh,glab ^(gh|glab)\s+(repo|release)\s+delete\b deleting a repository or a release is the owner's decision
```

Pin every rule the project keeps with a test of its own (a command it must refuse, one it must allow).

A file that cannot be read, is over 64 KiB, or holds a line that is not a valid rule refuses every shell command
until it is fixed (fail closed); the lead fixes it with its file-editing tool or uses the escape. Each rule is
proven by a test of the project (a command it must refuse, one it must allow), fed to the guard as neutral events.

## Known limits

- The guards judge the command text they are given: not the inside of scripts, `python -c` / `node -e` bodies,
  sourced files, aliases, or anything run later (cron, git hooks, container entrypoints, a program's own children).
- Names or paths computed at run time are not resolved; a failed `cd` is assumed to have worked; writers the guard
  does not model are not write-checked; time-of-check races.
- git options that run an inline command line of their own (`rebase -x/--exec`, `bisect run`, `submodule foreach`,
  `difftool -x/--extcmd`, `grep -O/--open-files-in-pager`, `filter-branch` filters, `--exec-path`) are judged only as
  far as the guard's git model goes.
- A protected command's own file writes (e.g. a copy out of a container) are not write-checked.
- On Windows the guards read every path in one form: `\` as `/`, an MSYS drive path (`/c/x`) as `C:/x`, the drive
  letter upper case. On Windows and macOS (file systems that ignore letter case) the protected top-level names -
  `.git`, `.boa`, `.env*`, the main checkout's protected names, the runtime's configuration names - are compared
  without regard to case (`.GIT` is `.git`); whole paths are compared as written, so the project's own path spelt in
  another case reads as another path (it falls on the refusing side of the rules that need a known root, such as
  deletions). Other MSYS mount points (`/tmp`, `/usr`) are not mapped to Windows paths.
- Not folded on Windows: a name with a trailing dot or space (`.git.`, `.git `, which Windows strips) and some Unicode
  case variants (a dotless i for `i`). These are deliberate corners no agent types by accident, not checks to add.
- A protected rule judges the command line only, never the input the program reads: a here-document
  (`mysql <<'SQL' … DROP DATABASE … SQL`), piped input (`echo "DROP DATABASE x" | mysql`), redirected input
  (`mysql < drop.sql`) and the commands `find -exec` runs on its matches pass a rule that matches the command line
  only. Register a rule on the program itself (e.g. `all mysql ^mysql\b(?!.*\s-e\s) …` refuses every non-`-e` call)
  when such input must be refused too.
