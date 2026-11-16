| Tool | What, when, how | Who | Side effects / safety |
|---|---|---|---|
| `.boa/stack/plugin.env` | the generic plug-in's settings: TEST_COMMANDS (test-file glob → command), TEST_RUNNER_MAX_FILES, TEST_HEAVY_IMAGE (the image of the service the heavy tests need; no default); the agent configures the project's tools here at bootstrap | lead at bootstrap; read by the tools | assignments only |
| `.boa/stack/test-runner.sh` | the targeted test runner: explicit test files only (refuses directories, globs and symlinks); shell suites with bash, every other kind through the command TEST_COMMANDS maps to it; its header states the contract a project's runner fulfils (explicit files, a case filter `--filter=<pattern>`, a heavy switch `--heavy` with its image setting, a per-call cap) | builder, tester | none beyond the tests |
| `.boa/stack/handbook-rows.md` | this stack's rows of the handbook (the block above) | — | — |
