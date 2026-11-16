# Choosing the stack from the project's goals

Use this when the IDEA (or the existing code) does not fix the stack. The lead chooses; the user is asked only
when the choice is a genuine fork with no objective winner (then: options, pros/cons, recommendation first).
A brownfield or refactor project keeps its stack unless the IDEA's target says otherwise.

## Method

1. **Write down the goals that constrain the stack**, from the IDEA: what is built (web app, API, CLI, library,
   mobile, desktop, data/ML, embedded, game), who runs it and where (managed hosting, own servers, edge, devices),
   latency and throughput targets, data size, security and compliance needs, third-party contracts to honour,
   the team that will maintain it, licence constraints, budget.
2. **List two or three candidate stacks** that meet them. Prefer mature, well-documented ecosystems with
   long support windows and the built-in features the project needs (framework built-ins first, then an
   extension, a custom build only for a proven gap).
3. **Verify online, now:** the latest stable release of each piece (language, framework, database, runtime),
   its support window, known blockers. Never pick versions from memory.
4. **Check the testing story**, which BOA depends on: a fast unit-test runner, a way to run targeted tests
   (named files), static analysis and a formatter, and a mutation-testing tool for the delicate paths — or code
   plants where none fits.
5. **Plan the stack plug-in**: BOA ships only the generic plug-in template (`<skill>/stacks/generic`); use
   `generic` and plan adapting it into the project's plug-in (test commands, the targeted test runner, heavy tests,
   the mutation wrapper) as an early tooling task (project-wiring item "stack plug-in").
6. **Record the decision as an ADR**: goals, candidates, the verified versions, why the winner, what was given up.

## Starting points (verify every one)

| Goal | Typical candidates | Mutation tool to check |
|---|---|---|
| web application with server-rendered UI and an admin | a full-stack framework in TypeScript, Python, Ruby or another mainstream web language | Stryker (JS/TS), mutmut or cosmic-ray (Python), mutant (Ruby) |
| HTTP/JSON or gRPC service | Go, TypeScript on Node, Python (FastAPI-style), Java/Kotlin, Rust | go-mutesting/gremlins, Stryker, mutmut, PIT, cargo-mutants |
| command-line tool | Go or Rust (single binary); Python when the users have it | gremlins, cargo-mutants, mutmut |
| data processing, ML | Python with the ecosystem's standard libraries | mutmut |
| mobile app | Kotlin (Android) / Swift (iOS), or a cross-platform framework | PIT (JVM), Muter (Swift) |
| desktop app | a web-tech shell with a native core, or the platform's native toolkit | per language |
| low latency, high throughput, systems | Rust, Go, C++ | cargo-mutants, gremlins, Mull (C/C++) |
| shell tooling | bash with strict mode, shellcheck | code plants (no mutation tool fits) |

Datastores: a relational database by default (current PostgreSQL or MariaDB/MySQL, as the hosting allows); a
cache/queue (Redis-compatible) only when a requirement needs it. Containers for every service the tests need.
