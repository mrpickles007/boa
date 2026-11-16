# 01 — Blueprint (living functionality map)

> The map of **all** functionality: what exists (brownfield/refactor: reconstructed line by line by the analyzers,
> every claim cited `file:line`) and what we want. One section per functional area; each item says its state
> (`exists`, `planned`, `?` = to verify) and the task(s) that own it. Items marked `?` go to the verification
> backlog below and are resolved against primary evidence, never guessed.

## A. <functional area>
- <item> — <state> — <task ids>

## B. <functional area>
- <item> — <state> — <task ids>

## Target stack (verify the exact latest stable versions at execution)
- <runtime, framework, database, services> — ADR <n>

## Verification backlog (resolve `?` items against the real source)
- [ ] <item> — <what to check, where>
