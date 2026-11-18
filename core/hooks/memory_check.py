#!/usr/bin/env python3
"""BOA memory check (a post-tool hook on file writes): right after a memory file is written, lint the whole

Purpose:  catch a broken memory at the write that broke it, and keep the generated memory-type tables current.
When:     runs by itself after every file write of an agent.
Wire:     the runtime's after-tool event of a file write, mapped onto the neutral `post-tool` event (tool
          `file-write`, tool_input.file_path), piped to `python3 -I .boa/hooks/memory_check.py`.
Verify:   write a memory block with a hand-made id: the hook answers with `decision: block` and the finding.
Outputs:  a block verdict with the findings, a context after regenerating the tables, else nothing.
Limits:   lints after the write (it cannot prevent it): the agent repairs through memory_write.py.
memory bank (memory_lint.py: fields, types, ids against the id ledger, supersession links across files) and, when it
finds anything, tell the agent at once with `decision: block` and the findings (the write itself already happened:
the agent must repair it — through memory_write.py, never by hand-editing ids or links). A memory file is a `*.md` or
the id ledger in the memory bank (BOA_MEMORY_DIR); the lead's inbox (<BOA_LEAD_DIR>/metalearning-inbox.md of the main
checkout, also from a worktree) is linted as drafts. Any other file: nothing. Fail-safe: never fails the tool call;
prints nothing when all is well; exit 0.
Input: the neutral post-tool event of a file write on stdin; output: the neutral verdict (tools/hook_contract.py).
"""

from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))


def check(ev) -> "object":
    """The core: a neutral post-tool event of a file write -> a `block` verdict with the lint findings, or none."""
    import hook_contract as hc
    v = hc.Verdict()
    if ev.kind != "post-tool" or ev.tool != "file-write":
        return v
    path = ev.tool_input.get("file_path")
    if not isinstance(path, str) or not path:
        return v
    import boa_config
    import memory_lint as ml
    import memory_types
    root = os.path.realpath(ml.ROOT)
    path = os.path.realpath(path if os.path.isabs(path) else os.path.join(ev.cwd or root, path))
    mdir = os.path.realpath(ml.memory_dir(root))
    # the inbox is in the MAIN checkout's lead dir, also when the agent works in a lane worktree
    inbox = os.path.realpath(os.path.join(boa_config.main_of(root), boa_config.load()["BOA_LEAD_DIR"],
                                          "metalearning-inbox.md"))
    if path == os.path.realpath(memory_types.default_path()):
        return types_written(path)
    names = memory_types.load().names
    if path == inbox:
        texts, unread, _ = ml.read_files([path])   # one stat first: a special file is a finding, never opened
        _, findings = ml.lint_texts(texts, names, True, None, False)
        findings = unread + findings
    elif path.startswith(mdir + os.sep) and (path.endswith(".md") or path.endswith(ml.LEDGER)):
        texts, unread, _ = ml.read_files(ml.files_of([mdir]))
        _, findings = ml.lint_texts(texts, names, False, os.path.join(mdir, ml.LEDGER), True)
        findings = unread + findings
    else:
        return v
    if findings:
        shown = "\n".join(findings[:15]) + (f"\n… and {len(findings) - 15} more" if len(findings) > 15 else "")
        v.decision = "block"
        v.reason = (f"memory lint after this edit of {os.path.relpath(path, root).replace(os.sep, '/')}: {len(findings)} finding(s). Repair "
                    "through .boa/tools/memory_write.py (ids and supersession links are never hand-written):\n"
                    f"{shown}")
    return v


def types_written(path: str) -> "object":
    """The memory-types file was written: an invalid one is refused at once (every memory tool would refuse it too:
    restore the previous version); a valid one regenerates the generated tables of the docs that hold them."""
    import hook_contract as hc
    import memory_types
    try:
        t = memory_types.load(path)
    except memory_types.TypesError as exc:
        return hc.Verdict(decision="block", reason=f"the memory types file is now invalid, every memory tool refuses it: "
                          f"{exc}. Fix it or restore the previous version (the generated tables were left as they were).")
    top = memory_types._bt().toplevel(path)   # the checkout that holds the written file (a lane, never its main)
    stale = memory_types.sync_docs(t, memory_types.docs_with_sections(top), True)
    if not stale:
        return hc.Verdict()
    return hc.Verdict(context="memory types changed: the generated tables were rewritten in "
                      + ", ".join(os.path.relpath(d, top).replace(os.sep, "/") for d in stale) + " (commit them with the types file)")


def main(argv: list[str]) -> int:
    import boa_tool as bt
    bt.on_term_exit(0)   # a regeneration goes through a temp file: a stop still removes it; a hook exits 0
    import hook_contract as hc
    out = hc.write_verdict(check(hc.read_event(sys.stdin.buffer.read(4 << 20).decode("utf-8", "replace"))))
    if out:
        print(out)
    return 0


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception:  # noqa: BLE001  (a hook never fails the tool call)
        pass
    sys.exit(0)
