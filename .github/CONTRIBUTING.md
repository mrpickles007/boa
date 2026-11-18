# Contributing to BOA

Thank you for helping. Issues, discussions and pull requests are welcome here; this page says how they reach a
release.

## How a contribution reaches a release

This repository holds only release trees: each release is one commit holding exactly the skill's files, built from
the maintainer's development repository, and a check before every push refuses any other tree. So a pull request is
never merged here as it is. When a contribution is accepted, the maintainer ports it into the development repository,
where it goes through BOA's own discipline (review, tests, the full gate), and it reaches this repository with the
next release. The maintainer credits you for it in that release's notes. If a port changes your proposal, the pull
request says how and why before it is closed.

## Where to start

- **A question or an idea:** open a discussion (the Discussions tab).
- **A bug:** open an issue with the bug report template: what you ran, what you expected, what happened, and the
  output of `sh <skill>/core/bin/boa help` (or `sh .boa/bin/boa help` after an install).
- **A security problem:** never in a public issue; see [SECURITY.md](SECURITY.md).
- **A change:** open an issue or a discussion first for anything larger than a typo, so that the design can be agreed
  before you write it.

## What a change must respect

- **English only**, in files, code, comments and output.
- **Project-agnostic:** no project, person, host, path or account name in a shipped file outside the README's pinned
  lines; everything that depends on a user's project is taught as discipline and done by the agent in that project.
- **Runtime-agnostic:** concrete facts about an agent runtime and model names live only in the runtime profiles
  (`references/runtimes.md`, `references/runtimes/`, `context-gate/`); every other text speaks of roles and
  capabilities.
- **Portable:** the tools are Python 3.11+ standard library with thin POSIX `sh` launchers; LF line endings; no
  symbolic links.
- **Scaffolding, not a framework:** BOA ships mainly discipline and few tools. A new tool needs a reason the
  discipline alone cannot meet.
- **Surgical edits** to existing documents: change what the change needs, keep what works.

This repository carries no test suites (they live in the development repository); the maintainer runs them when
porting. In your pull request, say what you checked yourself, for example an install into a throwaway repository
(`boa install`, then `boa uninstall`).

## Licence of contributions

Contributions are accepted under the licence of the files they touch: AGPL-3.0-only for BOA's code, MIT for the code
BOA copies into a project, CC-BY-4.0 for the texts (see the licence section of the [README](../README.md#licence) and
`REUSE.toml`).

## Code of conduct

Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).
