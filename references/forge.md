# Forge setup and CI (GitHub, GitLab, any other forge)

> Loaded by the lead at the skill's step 4 (the forge questions) and step 9 (commit and forge setup), when the CI
> task of the project-wiring checklist runs, and at close-out (visibility, CI). BOA ships no forge adapter and no CI
> file: the agent runs the forge's own CLI, with the user's consent, from the profile below.

## Consent (binding)

Creating or changing anything on a forge is an outward-facing act. The agent never does it on its own:

- **Every forge action needs the user's explicit yes**, asked **one decision at a time**, each question with the
  options and the agent's recommendation first. The decisions are listed in the next section; each command of the
  profile names the decision it needs. No yes, no call: a declined or unanswered decision means its commands are
  never run.
- **Reading needs no consent** (authentication status, whether a repository exists, the protection in force): it
  changes nothing. A read whose result needs a change leads to a question, never to the change.
- **Declining keeps everything local.** The pipeline works the same without a forge: lanes, review, tests and the
  gate run locally and on the remote runners; the project's git hooks still refuse pushes to main; with no remote
  (`BOA_FORGE=none`) nothing is pushed: after its one gate passes, the integrator lands the lane on the local main
  by a fast-forward to the gated tip (never a push, no PR; the landing commit is recorded in place of the PR
  number).
- **Recorded.** The answers go into one forge-setup decision record (an EDR in `memory-bank/06-DECISIONS.md`,
  keywords `forge, ci, visibility, protection`), each with who decided; a later change (CI enabled, visibility
  changed) is a new EDR that supersedes it. The project's documents point to that record for the CI in force.
- **Secrets never pass through a command line, a log or the chat.** A secret value is read from a file the user
  created or typed by the user into the CLI's own prompt; the agent never sees it. A secret the forge returns (a
  runner registration token) goes straight into a new mode-0600 file (`umask 077`) and is never printed or read by
  the agent.
- **Verify the CLI before the first use.** CLIs change: check each command of the profile against `gh <command>
  --help` / `glab <command> --help` (or the forge's current documentation) at execution, never from memory.

## The decisions, in order

Asked at the skill's step 4, one at a time; acted on at step 9 in this order. Secrets and forge runners are asked
only when the CI task needs them. A project that already has a remote (`git remote get-url origin` answers) still gets
decision 1, answered "use the existing one" or "no", before its first push or PR/MR.

| # | Decision | The question | Recommendation | If declined |
|---|---|---|---|---|
| 1 | `remote` | use a forge remote: create `<owner/repo>` (where, which name), or use the existing one | yes when the user wants an off-machine copy, collaboration or PR/MR review on the forge | local only, `BOA_FORGE=none`, nothing pushed |
| 2 | `visibility` | private or public (internal only on request) | the proposal of the table below, with its reason | nothing is created until it is answered |
| 3 | `protection` | set the forge's server-side protection of main | yes | the local pre-push hook is the only net: reported as a gap and recorded |
| 4 | `ci` | add a CI workflow/pipeline | only when it adds value, targeted (see [CI](#ci)) | the gate runs locally and on the runners |
| 5 | `secrets` | store the secrets the CI or the deploy needs, each by name | only the ones a consented job needs | none stored |
| 6 | `runners` | register a forge runner (CI on a machine of the user's) | only when the CI needs one and hosted runners do not fit | hosted runners or no CI |

## Visibility: the proposal

The agent proposes from the nature of the project, with the reason, and the user decides.

| Project nature | Proposal | Reason |
|---|---|---|
| proprietary or commercial work | private | the code is the product's value; publishing it cannot be undone |
| client work | private | the code belongs to the client; publishing needs the client's permission |
| security-sensitive work | private | the code and its history expose the attack surface and past mistakes |
| an open-source library or tool the user wants to share | public | sharing is the goal; public repositories also get the forge's free protection features |
| unsure | private | making a repository public later is easy; undoing a publication is not |

Visibility is **asked every time**, before any repository is created, even when the nature of the project makes the
proposal obvious and even for a throwaway project: the agent never picks it by default, never infers it from an
earlier answer, and a repository is never created while the answer is open. A public repository also changes the
CI economics below (hosted minutes of public repositories are normally free, private ones are metered), so the answer
is recorded in the forge-setup EDR and read again when the CI is planned.

## CI minutes economy

Hosted CI minutes are metered on a private repository and on any CI the forge bills, and an expensive runner
(macOS, Windows, GPU) multiplies the cost of every minute. The agent keeps the CI lean and watches the bill. All of
it is discipline: BOA ships no monitor and no workflow, the agent wires them for the project's forge.

**1. The minutes monitor.** On a private repository, or on any CI with metered minutes, the CI task (project-wiring
checklist, CI item) also wires a minutes monitor:

- **Ask the user for the monthly budget** (a HITL, options with a recommendation): minutes or money per month, and
  the warning threshold (recommended: 70% of the budget). Unknown means asked, never guessed. The answer goes into the
  forge-setup EDR.
- **Run it as a periodic tooling task** (the periodic-tooling facility of the project, the same as the other
  measurements): each run reads the month's usage, compares it with the budget, writes the number to the project's
  measurements and, over the threshold, **alerts the user** (the project's alert channel, with the number, the
  budget and the biggest consumers). A read needs no consent (it changes nothing).
- **Use the forge's own usage API or CLI**; the commands below are examples, none is mandatory (a project may use any
  other reading that gives the same number). Verify each against the forge's current documentation or the CLI's
  `--help` at execution:

| Forge | Example reading | What it gives |
|---|---|---|
| GitHub | `gh api -X GET 'users/<account>/settings/billing/usage/summary?year=<y>&month=<m>&product=actions'` (an organization: `organizations/<org>/settings/billing/usage/summary`; the detailed report is the same path without `/summary`) | usage and cost of the Actions product for the month, by SKU (the SKU names the runner type) and, with `&repository=<owner/repo>`, by repository; needs a token allowed to read billing (the user authenticates, never the chat) |
| GitLab | `glab api namespaces/<namespace-id>` and read `ci_minutes_usage` (total, monthly-quota and purchased minutes used in the billing period) next to `shared_runners_minutes_limit` (the monthly quota) | compute minutes of a top-level group; the quota fields are shown on GitLab.com or where compute quotas are configured; on a self-managed instance without quotas the reading is the job durations summed from the forge's pipelines or jobs API (verified at execution) |
| Any other | the forge's billing or usage API or CLI, found in its documentation | the month's minutes or cost |

**2. Lean launches: the checklist.** The CI task writes the triggers from this list, and the reviewer checks each
item against the file:

- Cheap Linux jobs run on push and PR/MR; the full suites run only where a change needs them.
- Expensive runners (macOS, Windows, GPU, large Linux) run only on manual dispatch or on a release, never on every
  push or PR/MR.
- Cancel in progress on PRs/MRs: a new push cancels the run of the one before.
- Path filters: a change that touches only docs (or other files no job covers) starts no CI.
- A first job decides which jobs a change needs (a changed-files filter), so a change starts only the jobs it
  affects.
- Every job prints the minutes it used (its duration, and the runner type), so a run's cost is read in its log.
- After the first run, measure the billed minutes (the monitor's reading). When the budget is at risk, **disable the
  workflow** (the forge's own switch, a recorded EDR) until the triggers are fixed; a disabled CI is better than an
  exhausted budget.
- Never re-run the full matrix just to check a docs change: re-run only the failed job, or none. On expensive
  runners (macOS, Windows, GPU or other) a re-run after a small fix is targeted: the manual dispatch takes a suite
  filter (an input listing the suites to run, validated against the project's suite names, never interpolated into
  the shell) and only the touched suites run there; the full matrix on every OS runs once, at the end (before a
  release, or when the change set warrants it).

**3. Who and when.** The CI task writes and reviews them; the lead asks the budget at decision 4 (`ci`) and runs the
first measurement; the periodic task repeats it; the alert goes to the user. Done when the budget is recorded, one
monitor reading ran and its number was compared with the threshold, and the review checked every item above.

## The forge profile: commands

The commands for GitHub (`gh`) and GitLab (`glab`). Consent `—` = a read (no consent needed); `remote` = decision 1
answered "create" or "use the existing one"; `remote: create` = answered "create" only. Placeholders:

- `<owner/repo>`: `BOA_FORGE_REPO` (an account or group path and the repository name);
- `<visibility>`: `private`, `public` or `internal`, as decided;
- `<main>`: `BOA_MAIN_BRANCH`, as is (a field value, the ruleset's ref, a branch name in the CLI's own options);
- `<main-url>`: `<main>` URL-encoded for an API path or query (`release/1.x` → `release%2F1.x`, `+` → `%2B`):
  a raw `/` or `+` there names another resource;
- `<merge-level>`: the merge access level main's own rule had at the first read (`40`, Maintainer, when there was
  none): carried over, never changed by the protection;
- `<ruleset.json>`: the ruleset below, saved to a scratch file with `<main>` filled in;
- `<branch>`, `<title>`, `<body-file>`, `<n>`, `<sha>`: a lane's branch, its PR/MR title, the body file (from the
  forge template), the PR/MR number, the gated head's full commit SHA;
- `<workflow>`, `<ref>`: the CI workflow file name and the branch it runs on;
- `<NAME>`, `<value-file>`: a secret's name and the file the user put its value in (deleted after);
- `<project-id>`: the GitLab project's numeric id (`glab api projects/:id` shows it);
- `<token-file>`: a new file for a runner registration token, never inside the repository: under the scratch root
  (`BOA_SCRATCH_ROOT`) or the machine-local `~/.config/boa/<slug>/`; created mode 0600 (`umask 077`) and never over
  an existing file (`set -C`, the command fails instead), read only by the runner's registration on the runner
  machine, never by the agent, deleted after use. `gh` stores only the token (`--jq .token`); `glab api` has no
  output filter, so its file holds the registration's JSON answer (id and token), read the same way.

`{owner}`, `{repo}` (gh) and `:id` (glab) are filled in by the CLI from the repository of the current directory.
Every write through the API names its method (`-X`): both CLIs switch to POST silently when fields or a body are
given, so an unnamed method is how a read turns into a write by accident.

| Action | Consent | GitHub | GitLab |
|---|---|---|---|
| Check the CLI's authentication | — | `gh auth status` | `glab auth status` |
| Check whether the repository exists | — | `gh repo view <owner/repo> --json visibility` | `glab repo view <owner/repo> --output json` |
| Create the remote repository and add it as `origin` | `remote: create`, `visibility` | `gh repo create <owner/repo> --<visibility> --source . --remote origin` | `glab repo create <owner/repo> --<visibility> --defaultBranch <main> --remoteName origin` |
| Change the visibility | `visibility` | `gh repo edit <owner/repo> --visibility <visibility> --accept-visibility-change-consequences` | `glab api -X PUT projects/:id -f visibility=<visibility>` |
| Read the protection of main | — | `gh api repos/{owner}/{repo}/rules/branches/<main-url>` | `glab api --paginate projects/:id/protected_branches` |
| List the branches the bridge would cover | — | — | `glab api --paginate 'projects/:id/repository/branches?search=^<main-url>'` |
| Bridge: protect `<main>*` with push no one while main's own rule is replaced | `protection` | — | `glab api -X POST projects/:id/protected_branches -f 'name=<main>*' -F push_access_level=0 -F merge_access_level=<merge-level> -F allow_force_push=false` |
| Remove main's own rule (GitLab protects the default branch on its first push) | `protection` | — | `glab api -X DELETE projects/:id/protected_branches/<main-url>` |
| Protect main | `protection` | `gh api -X POST repos/{owner}/{repo}/rulesets --input <ruleset.json>` | `glab api -X POST projects/:id/protected_branches -f name=<main> -F push_access_level=0 -F merge_access_level=<merge-level> -F allow_force_push=false` |
| Remove the bridge | `protection` | — | `glab api -X DELETE 'projects/:id/protected_branches/<main-url>%2A'` |
| Open a PR/MR for a lane | `remote` | `gh pr create --base <main> --head <branch> --title <title> --body-file <body-file>` | `glab mr create --target-branch <main> --source-branch <branch> --title <title> --description-file <body-file> --yes` |
| Merge a PR/MR pinned to the gated head | `remote` | `gh pr merge <n> --squash --match-head-commit <sha>` | `glab mr merge <n> --squash --sha <sha>` |
| Store a CI secret | `secrets` | `gh secret set <NAME> < <value-file>` | `glab variable set <NAME> --masked --protected < <value-file>` |
| Start the CI by hand | `ci` | `gh workflow run <workflow> --ref <ref>` | `glab ci run --branch <ref>` |
| Get a forge-runner registration token into a 0600 file | `runners` | `(set -C; umask 077; gh api -X POST repos/{owner}/{repo}/actions/runners/registration-token --jq .token > <token-file>)` | `(set -C; umask 077; glab api -X POST user/runners -f runner_type=project_type -F project_id=<project-id> > <token-file>)` |

The PR/MR rows are the routine of the pipeline once the user consented to the remote (the integrator's contract and
09 §7 say when); every other write runs only for its decision.

### Any other forge

The same consent rules, the same decisions, the same order. The agent writes the equivalent profile for that
forge's CLI or API, verified against its current documentation at execution, records it in the project (the
handbook and `memory-bank/04-ARCHITECTURE.md`) and tests each command once with a read before any write. Where the
forge has no server-side protection of a branch, that is a gap, reported as below.

## Forge setup (the skill's step 9)

After the install commit, the consented actions, in order:

1. **Read first:** the CLI's authentication and whether the repository exists. Not authenticated: tell the user how
   to log in (`gh auth login` / `glab auth login`, run by the user) and wait; never ask for a token in the chat.
2. **The remote.** "Create": create it (`remote: create`, `visibility`), then **publish main once:** a plain
   `git push -u origin <main>` before the project's git hooks exist (they are installed after the forge setup,
   project-wiring "git hooks"), recorded as "initial publication" through the progress staging; from then on main
   moves only through reviewed merges. "Use the existing
   one": nothing is created and main is not pushed; the install commit goes through a PR/MR like any change, and
   only after this yes. "No": nothing is pushed at all.
3. **Protect main** (`protection`): read the protection in force (every page: GitLab lists 20 rules per page, and a
   permissive rule on a later page still applies), set it, then **read it again to verify**. Each write runs only
   after the previous one succeeded; a removal answered 404 means there was nothing to remove and the setup goes
   on. GitLab cannot change a rule's push level in place on every plan (the API's access-level updates are not in
   the free tier), and a branch matched by several rules gets the most permissive one, so main stays covered at
   every step: first the bridge (`<main>*`, push no one), then main's own rule is removed and set again with push
   no one, and the bridge is removed only after the read shows main's own rule protected; both carry over main's
   merge level (`<merge-level>`). **When the first read already meets "Protected means", nothing is written and
   nothing is asked** (for an existing remote this read comes before the protection question): the record says so.
   On GitLab, before any write:
   - **stop and ask the user** when main's own rule carries more than access levels and force push (code-owner
     approval, user, group, deploy-key or custom-role (`member_role_id`) entries, an unprotect level other than the
     default): replacing the rule would drop them;
   - **stop and ask the user** when a rule named `<main>*` already exists (the bridge would collide with it; a 409
     on the bridge means the same: "a rule with that name already exists", a question, not a gap);
   - list the branches the bridge would cover and name the ones besides main in the protection question: while the
     bridge stands nobody can push to them (on a new remote there are none; branches the user was not told about
     mean asking again first).
   If main's own rule cannot be set, the bridge stays as main's protection; if the bridge cannot be removed, main is
   protected but the bridge stays too: either way the report names the branches the bridge still covers and asks
   whether to keep it or remove it by hand. Protected means:
   - GitHub: the rules of main include `pull_request`, `non_fast_forward` and `deletion`;
   - GitLab: at least one rule matches main (its own name or a wildcard), and every matching rule has at least one
     push access level, all of them `0` (no one), and `allow_force_push` false.
   Anything else is a gap (below), never assumed protected.
4. **CI** (`ci`): nothing is created here. A yes adds the CI task to the plan (the project-wiring checklist item);
   the task writes the CI under the pipeline (see [CI](#ci)).
5. **Record** every answer and every result in the forge-setup EDR; open the PR/MR of the install commit when it
   went on a branch.

### GitHub: the ruleset for main

Saved to a scratch file with `<main>` filled in, passed to the "Protect main" command, then the scratch file is
removed. No bypass actors: nobody pushes to main directly, the integrator merges through the PR.

```json
{
  "name": "main only through reviewed pull requests",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["refs/heads/<main>"], "exclude": []}},
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "pull_request", "parameters": {
      "required_approving_review_count": 0,
      "dismiss_stale_reviews_on_push": false,
      "require_code_owner_review": false,
      "require_last_push_approval": false,
      "required_review_thread_resolution": false}}
  ]
}
```

`required_approving_review_count` is 0 because the review happens in the pipeline (the adversarial reviewer) and a
single-account project cannot approve its own pull request; when the user has a second reviewer and wants a human
approval on the forge too, it is 1 (the user decides).

### Gaps: protection the forge refuses

A forge or a plan may refuse server-side protection. GitHub answers HTTP 403 ("Upgrade to GitHub Pro or make this
repository public to enable this feature") for rulesets and branch protection on a private repository of a free
personal account; a self-managed GitLab may restrict the API. Then:

- **report it to the user** in plain words: main is protected only by the local pre-push hook, which a
  `--no-verify` push or a clone without the hooks gets past (when the first read already showed no rule at all,
  say that main is unprotected on the server and treat it as urgent);
- **give the options** with a recommendation: a plan that includes protection (it costs money: the user's call),
  making the repository public (only when its nature allows it, decision 2), or the local hook only;
- **record** the gap and the user's choice in the forge-setup EDR and as a HITL row of the plan (through the transit queue open-items.md) until it is decided.

## CI

CI is project work: BOA ships no CI file, no CI key and no pin. When the user consents (decision 4), the CI task of
the project-wiring checklist writes it for this project, through the pipeline (task, review, test), from these
invariants:

1. **CI runs the project's gate, never a second gate.** The job calls the project's gate in its heavy mode (the
   heavy steps of the pre-merge run alone), exactly as the remote runner runs them (project-wiring items "the project
   gate" and "remote runners"); it never re-implements a check, so the gate and the CI cannot drift. BOA's static
   checks stay in the local gate (the integrator's pre-merge run, from the main checkout's `.boa/tools/`): a CI
   checkout has no `.boa/` tools, which are git-ignored. A check
   that belongs in CI belongs in the gate (a stack plug-in step).
2. **Triggers are chosen per project and targeted.** Manual start by default (the rules pool: hosted minutes cost
   money); automatic triggers only with the user's yes, and then narrow: the main branch's PR/MR only, path filters
   for what the job really covers, no schedule without a reason. Every trigger and its reason go in the CI task's
   record.
3. **Pinned and verified at execution.** Every action is pinned by its full commit SHA and every image by its
   `sha256` digest, each looked up online when the task runs as the latest stable release and named in a comment
   (version and lookup date). Never a tag, a branch or a pin copied from an example or from memory; a CI file with
   a placeholder left is never committed. Hosted runner labels cannot be pinned by digest: they are versioned
   (`ubuntu-24.04`-style, the latest verified at execution), never a moving `-latest` label.
4. **Least permissions.** Read-only repository access unless a step needs more (then only that permission, on that
   job); no credentials persisted in the checkout; secrets only through decision 5, only for the jobs that need them.
5. **Nothing that costs money without consent.** Hosted minutes, paid runners, artifacts storage, scheduled runs:
   each is part of the user's yes, with the expected cost when it is known. A job has a timeout.

The machine-local values in `.boa/config.env` (the Python path, the runner switch) that the heavy steps read must
hold on the CI machine too:
the task picks an image where they do, or sets the same keys in the job's environment (BOA's tools read the
environment first; project-wiring "Config", per-machine values), and proves it with one manual run.

### Example: GitHub Actions (annotated, not installed)

The shape only: the task replaces every `<…>` after the online lookup, and decides the triggers with the user.

```yaml
# <project> gate on GitHub Actions. Written by the CI task; triggers decided with the user (manual by default).
name: gate

on:
  workflow_dispatch:            # manual start; `pull_request: {branches: [<main>], paths: [...]}` only on a yes

permissions:
  contents: read                # least permissions: read-only unless a step needs more

concurrency:
  group: gate-${{ github.ref }}
  cancel-in-progress: true

jobs:
  gate:
    runs-on: ubuntu-<version>   # a versioned label, verified at execution; hosted minutes cost money
    timeout-minutes: 60
    steps:
      - name: Checkout
        uses: actions/checkout@<full commit SHA of the latest stable release>   # <version>, looked up <date>
        with:
          persist-credentials: false
          fetch-depth: 0
      # the stack's toolchain setup, pinned the same way (decided by the task)
      - name: Gate, heavy steps (as the remote runner runs them; BOA's static checks stay in the local gate)
        run: <the project's gate command, its heavy steps alone>
```

### Example: GitLab CI (annotated, not installed)

```yaml
# <project> gate on GitLab CI. Written by the CI task; triggers decided with the user (manual by default).
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "web" || $CI_PIPELINE_SOURCE == "api"'   # manual start only
    - when: never                                                           # no push, MR or schedule pipelines

gate:
  image: <registry>/<image>@sha256:<digest of the latest stable release>   # <version>, looked up <date>
  timeout: 60 minutes
  when: manual                  # the job still waits for a click
  variables:
    GIT_DEPTH: "0"
  script:
    - <the project's gate command, its heavy steps alone>   # as the runner runs them; BOA's static checks stay local
```
