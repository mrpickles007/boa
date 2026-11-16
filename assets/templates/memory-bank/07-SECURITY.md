# 07 — Security

> Threat model, known vulnerabilities and their remediation, the standing checklist every task touching these
> areas must satisfy. The reviewer attacks every diff against this file; security facts are added in the task
> that finds them.

## Threat model
| Asset | Threat | Actor | Mitigation | Test |
|---|---|---|---|---|

## Known vulnerabilities (brownfield/refactor: found in the existing code, each with evidence and its fix task)
| ID | Where (`file:line`) | What | Severity | Fix task | Regression test |
|---|---|---|---|---|---|

## Standing security checklist (every task touching these must satisfy)
- Queries use parameter binding only; no string-built SQL or shell commands.
- Every external input is validated and typed at the boundary; output is encoded for its context.
- Authorization checks both the role and the ownership of the object; deny by default.
- Secrets never in the repository, logs, briefs or argv; passwords through the environment or 0600 files.
- No SSRF: outbound fetches of user-supplied URLs go through an allowlist and block private ranges.
- No path traversal: user input never builds a filesystem path without normalisation and a root check.
- Tokens and sessions: signed, expiring, bound to their purpose; constant-time comparisons.
- Dependencies: latest stable, licences on the allowlist, known vulnerabilities scanned in the gate.
- Logs redact credentials and personal data.

## Deployment security (the project's own instance)
- No default credentials; minimal exposure; TLS current; secrets generated at init and stored with mode 0600.

## Memories — security
<!-- Memory blocks of any type with the keyword security are appended here by `.boa/tools/memory_write.py` (`memory-bank/README.md` "Memory blocks"). -->
