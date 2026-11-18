# BOA notice

Parts of {{BOA_PROJECT_NAME}} come from BOA (Build On Autopilot), the agent skill that set up the way this project
is built:

BOA (Build On Autopilot): https://github.com/mrpickles007/boa
Copyright (c) 2026 Giulio Alberello

This file is their attribution, which both licences below ask for: keep it while those parts are in the project.

- **The texts BOA wrote from its templates** are under the Creative Commons Attribution 4.0 International licence
  (CC BY 4.0, https://creativecommons.org/licenses/by/4.0/): BOA's rules (the marked block of `AGENTS.md`, and
  `docs/boa-rules.md` when it exists), `docs/agent-handbook.md`, the lead directory (`{{BOA_LEAD_DIR}}/`), the
  forge's pull or merge request template, the agent and command definitions rendered from BOA's templates (wherever
  the agent wired them), and BOA's template text in `memory-bank/` and `docs/parity/`. What the project writes there
  (its plan, specifications, decisions, memories, features) is the project's own, and so are `.boa/config.env` and
  `.boa/protected-commands.conf`, which the agent writes for the project. Change BOA's texts as the project needs;
  when you share them (in a public repository, say), keep this notice and say that they were changed.
- **The code and data files BOA copied** are under the MIT licence below: the stack plug-in (`.boa/stack/`),
  `.boa/memory-types.json`, `.boa/markers.json` and the context-gate skill (`.context-gate/` and the skill's own copy
  where the runtime keeps its skills, which also carries this licence as its `LICENSE`).
- **BOA's tools**, the copies in `.boa/bin/`, `.boa/tools/`, `.boa/hooks/` and `.boa/embed.json`, are under the GNU
  AGPL-3.0-only. They are git-ignored, are not part of this project's sources and are not meant to be redistributed:
  every clone gets them back from `boa install`.

What you build with BOA is yours: none of these licences covers the project's own code, documents or data.

## The MIT licence

MIT License

Copyright (c) 2026 Giulio Alberello

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
