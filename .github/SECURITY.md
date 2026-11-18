# Security policy

## Supported versions

Only the latest release receives fixes. A fix ships as a new release.

## Reporting a vulnerability

Report it privately, through this repository's private vulnerability reporting: the Security tab, then "Report a
vulnerability". Do not open a public issue, discussion or pull request for it. Say what is affected (the file or the
command), how to reproduce it, and what an attacker gains.

The report stays private between you and the maintainer until a fix is released; the advisory is then published
with the release, crediting you unless you ask otherwise.

The same private channel takes code-of-conduct reports (start the title with "Code of conduct:").

## Scope

BOA installs tools, hooks and guards into a project. Its guards are a safety net against an agent's accidents, not a
sandbox against attacks: a way to get around a guard on purpose is a known limit (see the README's honest limits),
while a guard that lets an accident through, or any way for BOA's own code to damage a project, a repository or a
machine, is in scope.
