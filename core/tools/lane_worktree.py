"""BOA lean lane worktrees: one git worktree per task, created from the remote's main branch.

Purpose:  give every task its own isolated checkout (a git worktree on its own branch) that costs little disk: a sparse
          checkout without large read-only directories, dependency directories hard-linked from the main checkout,
          and a removal that never drops unpushed work.
When:     the lead, when it starts a lane (`add`, then `deps` when the stack has dependency directories); the tester or
          integrator when it needs the excluded directories (`full`); the integrator after the merge (`remove`).
Wire:     nothing to wire: the lead's procedures call it; the stack plug-in sets BOA_DEP_DIRS and BOA_DEP_PRIVATE, the
          config BOA_SPARSE_EXCLUDES, BOA_WT_DIR and BOA_BRANCH_GRAMMAR.
Verify:   `lane-worktree.sh add T-001 m1/T-001-try` then `git worktree list` shows <WT root>/T-001; `remove T-001`
          takes it away again.
Outputs:  the worktree <WT root>/<TASK> and its branch; one line per action on stdout; refusals on stderr.
Limits:   hard links need the lane on the main checkout's filesystem; never edit, chmod or truncate a shared
          dependency file in place in a lane (it would change the main checkout's copy). On Windows a `deps` copy
          killed from outside (no signal reaches a native process there) leaves its .deps.tmp.* directory in the
          lane: remove it by hand before the next `deps` (elsewhere a stop runs the cleanup).

Usage: .boa/bin/lane-worktree.sh add <TASK> <branch> [--full]
       .boa/bin/lane-worktree.sh deps <TASK>
       .boa/bin/lane-worktree.sh full <TASK>
       .boa/bin/lane-worktree.sh remove <TASK> [--force]
  add       new worktree <WT root>/<TASK> on a new branch from <BOA_REMOTE>/<BOA_MAIN_BRANCH> (fetched first).
            With BOA_SPARSE_EXCLUDES (space-separated top-level directories, e.g. a large read-only snapshot a build
            task must not read) the lane is a git sparse checkout without exactly those top-level directories: every
            other path (new ones too) is checked out, and the excluded ones stay tracked. --full (or no excludes)
            checks out everything. The branch must follow BOA_BRANCH_GRAMMAR (default m<ms>/<task>-<slug>, lower-case
            slug) for this TASK and must not exist.
  deps      share the project's dependency directories with the lane (BOA_DEP_DIRS, space-separated paths relative to
            the root; set by the stack plug-in): each one is a hard-linked copy of the main checkout's, so a lane costs
            only its private files. The paths of BOA_DEP_PRIVATE (relative to each dependency directory: the files the
            package manager regenerates) are private copies instead, and are refused when they hold an absolute path of
            the main checkout (the lane would load the main checkout's code). Every directory is checked before
            anything is created; none may exist in the lane yet.
  full      materialise the excluded directories in a sparse lane (git sparse-checkout disable), for the suites that
            read them (tester, integrator).
  remove    git worktree remove <WT root>/<TASK>, then delete its local branch if it is the task's branch (the grammar
            for this TASK); only a worktree of this repository registered at exactly that path is touched. Without
            --force it first refuses, touching nothing, when the commits it would drop are unpushed (the branch tip, or
            a detached HEAD, is not contained in <remote>/<branch> or <remote>/<main branch>) or the worktree has
            uncommitted changes. --force drops both. The remote branch stays (the integrator deletes it after the
            merge).
TASK: T-NNN (T- and at least three digits, an optional lower-case letter). WT root: BOA_WT_DIR (relative to the main
checkout, default ../<project slug>-wt). The project is the git repository of the current directory (run from the main
checkout or any worktree). Exit: 0 ok, 1 refused/failed, 2 usage.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True   # no __pycache__ next to the installed tools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_tool as bt  # noqa: E402

TOOL = "lane-worktree"


def du_bytes(paths: list[str], seen: set | None = None) -> int:
    """Disk usage in bytes of the paths together, as `du -s -B1` counts it: allocated blocks (the size where the
    platform has no block count), symlinks never followed, a hard-linked file counted once, at its first path.
    Unreadable entries count 0. `seen` (shared between calls) carries the files already counted, so several calls
    count a hard-linked file once, like one `du` over all their paths."""
    seen = set() if seen is None else seen
    total = 0

    def one(st: os.stat_result) -> int:
        key = (st.st_dev, st.st_ino)
        if key in seen:
            return 0
        seen.add(key)
        blocks = getattr(st, "st_blocks", None)
        return blocks * 512 if blocks is not None else st.st_size

    for top in paths:
        try:
            total += one(os.lstat(top))
        except OSError:
            continue
        if not os.path.isdir(top) or os.path.islink(top):
            continue
        for d, dirs, files in os.walk(top, onerror=lambda e: None):
            for n in dirs + files:
                try:
                    total += one(os.lstat(os.path.join(d, n)))
                except OSError:
                    pass
    return total


class Refused(Exception):
    pass


def die(msg: str) -> None:
    raise Refused(msg)


def say(msg: str) -> None:
    print(f"{TOOL}: {msg}", flush=True)


def git(*args: str, quiet: bool = False) -> int:
    """A git command with its own output on the terminal (or none with quiet); its exit status."""
    out = subprocess.DEVNULL if quiet else None
    return subprocess.run(["git", *args], stdout=out, stderr=out).returncode


def git_out(*args: str) -> str | None:
    return bt.git(*args)


def norm(p: str) -> str:
    """A path as compared here: normalised, and case-folded where the platform is case-insensitive (Windows; git
    prints `C:/...` there, Python `C:\\...`)."""
    return os.path.normcase(os.path.normpath(p))


def same(a: str, b: str) -> bool:
    return norm(a) == norm(b)


def inside(child: str, parent: str) -> bool:
    """`child` is `parent` or lies below it (paths on different drives: never)."""
    try:
        return os.path.commonpath([norm(child), norm(parent)]) == norm(parent)
    except ValueError:
        return False


def plain_rel(p: str) -> bool:
    """A relative path with no `.` or `..` component, with `/` or `\\` separators, not rooted or on a drive."""
    q = p.replace("\\", "/")
    return (not q.startswith("/") and not re.match(r"[A-Za-z]:", q) and "/../" not in f"/{q}/"
            and "/./" not in f"/{q}/")


class Lanes:
    def __init__(self) -> None:
        common = (git_out("rev-parse", "--path-format=absolute", "--git-common-dir") or "").strip()
        if not common:
            die("not inside a git repository")
        if os.path.basename(common) != ".git":
            die(f"unsupported repository layout (git dir {common})")
        self.main = os.path.dirname(common)
        if not os.environ.get("BOA_ROOT"):
            os.environ["BOA_ROOT"] = self.main
        self.env = bt.init(os.path.abspath(__file__), TOOL)
        self.wt_root = self.env.path(self.env["BOA_WT_DIR"])
        m = self.main
        if same(os.path.dirname(norm(self.wt_root)), norm(self.wt_root)) or inside(self.wt_root, m) \
                or inside(m, self.wt_root):
            die(f"the worktrees directory must be outside the main checkout: {self.wt_root}")
        self.base = f"{self.env['BOA_REMOTE']}/{self.env['BOA_MAIN_BRANCH']}"
        # Sparse rules (non-cone: the cone mode can only list what to include, so it would drop new top-level
        # directories): everything, except the excluded top-level directories.
        self.excludes: list[str] = []
        self.sparse_rules = ["/*"]
        for d in self.env["BOA_SPARSE_EXCLUDES"].split():
            if not re.fullmatch(r"[A-Za-z0-9._][A-Za-z0-9._-]*", d) or d in (".", ".."):
                die(f"BOA_SPARSE_EXCLUDES: '{d}' is not a top-level directory name")
            self.excludes.append(d)
            self.sparse_rules.append("!/" + d + "/")
        self.lane = self.lane_branch = self.lane_head = ""

    def branch_re(self, task: str) -> str:
        return bt.branch_re(self.env["BOA_BRANCH_GRAMMAR"], re.escape(task))

    def registered(self, path: str) -> bool:
        """Sets lane_branch (empty if detached) and lane_head of the worktree at `path`; False if none is there."""
        found, cur = False, ""
        self.lane_branch = self.lane_head = ""
        for line in (git_out("-C", self.main, "worktree", "list", "--porcelain") or "").split("\n"):
            if line.startswith("worktree "):
                cur = line[9:]
            elif line.startswith("HEAD ") and cur and same(cur, path):
                self.lane_head = line[5:]
            elif line.startswith("branch refs/heads/") and cur and same(cur, path):
                self.lane_branch = line[len("branch refs/heads/"):]
            elif line == "":
                cur = ""
            if cur and same(cur, path):
                found = True
        return found

    def lane_path(self, task: str) -> None:
        """The lane of `task`: a worktree of this repository at exactly <WT root>/<TASK>, no symlink on the way."""
        if not re.fullmatch(bt.TASK_RE, task):
            die(f"invalid task id '{task}' (want T-<3+ digits>[a-z])")
        self.lane = os.path.join(self.wt_root, task)
        if not same(os.path.realpath(self.lane), self.lane):
            die(f"{self.lane} goes through a symlink: refused")
        if not self.registered(self.lane):
            die(f"{self.lane} is not a registered worktree of {self.main}")

    # --- add -------------------------------------------------------------------------------------------------
    def add(self, task: str, branch: str, mode: str = "build") -> None:
        if not re.fullmatch(bt.TASK_RE, task):
            die(f"invalid task id '{task}' (want T-<3+ digits>[a-z])")
        if not re.search(self.branch_re(task), branch):
            die(f"branch must follow {self.env['BOA_BRANCH_GRAMMAR']} for {task} (lower-case slug), got '{branch}'")
        if git("check-ref-format", "--branch", branch, quiet=True) != 0:
            die(f"invalid branch name '{branch}'")
        lane = os.path.join(self.wt_root, task)
        if os.path.lexists(lane):
            die(f"{lane} already exists")
        if not same(os.path.realpath(self.wt_root), self.wt_root):
            die(f"{self.wt_root} goes through a symlink: refused")
        if git("-C", self.main, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}") == 0:
            die(f"branch {branch} already exists")
        if git("-C", self.main, "fetch", "--quiet", self.env["BOA_REMOTE"], self.env["BOA_MAIN_BRANCH"]) != 0:
            die(f"git fetch {self.env['BOA_REMOTE']} {self.env['BOA_MAIN_BRANCH']} failed")
        os.makedirs(self.wt_root, exist_ok=True)
        if mode == "full" or not self.excludes:
            rc = git("-C", self.main, "worktree", "add", "--quiet", "-b", branch, lane, self.base)
            if rc != 0:
                raise SystemExit(rc)
            say(f"added full lane {lane} on {branch} (everything checked out)")
            return
        rc = git("-C", self.main, "worktree", "add", "--quiet", "--no-checkout", "-b", branch, lane, self.base)
        if rc != 0:
            raise SystemExit(rc)
        # Rules first, then populate: the excluded directories are never written to disk.
        leaked = False
        if git("-C", lane, "sparse-checkout", "set", "--no-cone", *self.sparse_rules) == 0 \
                and git("-C", lane, "read-tree", "-mu", "HEAD") == 0:
            leaked = any(os.path.lexists(os.path.join(lane, d)) for d in self.excludes)   # post-check
        else:
            leaked = True
        if leaked:
            git("-C", self.main, "worktree", "remove", "--force", lane)
            git("-C", self.main, "branch", "-D", branch, quiet=True)
            die(f"sparse checkout of {lane} failed; lane rolled back")
        say(f"added build lane {lane} on {branch} ({' '.join(self.excludes)} not checked out; 'full {task}' "
            "materialises them)")

    # --- deps ------------------------------------------------------------------------------------------------
    def deps(self, task: str) -> None:
        self.lane_path(task)
        dirs = self.env["BOA_DEP_DIRS"].split()
        private = self.env["BOA_DEP_PRIVATE"].split()
        if not dirs:
            die("no dependency directories configured (BOA_DEP_DIRS, set by the stack plug-in)")
        for p in private:
            if not plain_rel(p):
                die(f"BOA_DEP_PRIVATE: '{p}' must be a relative path without . or ..")
        for d in dirs:
            if not plain_rel(d):
                die(f"BOA_DEP_DIRS: '{d}' must be a relative path without . or ..")
            src, dst = os.path.join(self.main, d), os.path.join(self.lane, d)
            parent = os.path.dirname(dst)
            if not os.path.isdir(src) or os.path.islink(src):
                die(f"no dependency directory in the main checkout: {src}")
            if not os.path.isdir(parent) or os.path.islink(parent):
                die(f"no {d.rsplit('/', 1)[0]}/ directory in {self.lane}")
            if os.path.lexists(dst):
                die(f"{dst} already exists")
            if os.stat(src).st_dev != os.stat(parent).st_dev:
                die(f"{src} and {self.lane} are on different filesystems: hard links impossible")
            # Generated paths must be relative; an absolute path to the main checkout would make the lane load the
            # main checkout's code.
            for p in private:
                if os.path.lexists(os.path.join(src, p)) and holds(os.path.join(src, p), main_spellings(self.main)):
                    die(f"{src}/{p} holds absolute paths of {self.main}: a linked copy would load the main "
                        "checkout's code")
        for d in dirs:
            src, dst = os.path.join(self.main, d), os.path.join(self.lane, d)
            tmp = None
            try:   # removed on any exit: an interrupted copy leaves nothing
                with bt.held_stop_signals():   # recorded before a stop can land (the finally below)
                    tmp = tempfile.mkdtemp(prefix=".deps.tmp.", dir=os.path.dirname(dst))
                shutil.copytree(src, os.path.join(tmp, "d"), symlinks=True, copy_function=os.link)
                # The package manager rewrites these on every install: private copies, so no writer can reach main's.
                for p in private:   # private copies
                    f = os.path.join(tmp, "d", p)
                    if os.path.lexists(f):
                        if os.path.isdir(f) and not os.path.islink(f):
                            shutil.rmtree(f)
                        else:
                            os.remove(f)
                        s = os.path.join(src, p)
                        if os.path.isdir(s) and not os.path.islink(s):
                            shutil.copytree(s, f, symlinks=True)
                        else:
                            shutil.copy2(s, f, follow_symlinks=False)
                os.rename(os.path.join(tmp, "d"), dst)
            finally:
                if tmp is not None:
                    shutil.rmtree(tmp, ignore_errors=True)
            full, priv = du_bytes([src]), du_bytes([src, dst]) - du_bytes([src])
            say(f"deps: {dst} hard-linked to {src}; lane-private {priv // 1048576} MiB of {full // 1048576} MiB "
                f"(saved {(full - priv) // 1048576} MiB)")

    # --- full ------------------------------------------------------------------------------------------------
    def full(self, task: str) -> None:
        self.lane_path(task)
        if (git_out("-C", self.lane, "config", "--get", "core.sparseCheckout") or "").strip() != "true":
            say(f"{self.lane} is not sparse: everything already checked out")
            return
        rc = git("-C", self.lane, "sparse-checkout", "disable")
        if rc != 0:
            raise SystemExit(rc)
        for d in self.excludes:
            if (git_out("-C", self.lane, "ls-files", "--", d) or "").strip() and \
                    not os.path.isdir(os.path.join(self.lane, d)):
                die(f"{d}/ still missing in {self.lane}")
        say(f"everything checked out in {self.lane}")

    # --- remove ----------------------------------------------------------------------------------------------
    def unpushed_guard(self) -> None:
        """Refuses (before anything is removed) when the commits remove would drop are not on the remote."""
        tip = self.lane_head
        if self.lane_branch:
            tip = (git_out("-C", self.main, "rev-parse", "--verify", "--quiet",
                           f"refs/heads/{self.lane_branch}^{{commit}}") or "").strip() or self.lane_head
        if not tip:
            return
        remote = self.env["BOA_REMOTE"]
        refs = [r for r in (f"refs/remotes/{remote}/{self.lane_branch}", f"refs/remotes/{self.base}")
                if r != f"refs/remotes/{remote}/" and git("-C", self.main, "show-ref", "--verify", "--quiet", r) == 0]
        for r in refs:
            if git("-C", self.main, "merge-base", "--is-ancestor", tip, r, quiet=True) == 0:
                return
        n = (git_out("-C", self.main, "rev-list", "--count", tip, "--not", *refs) or "?").strip()
        die(f"branch {self.lane_branch or '(detached HEAD)'} has {n} unpushed commit(s): push or use --force; "
            "nothing removed")

    def remove(self, task: str, force: bool) -> None:
        self.lane_path(task)
        drop_branch = bool(self.lane_branch) and re.search(self.branch_re(task), self.lane_branch) is not None
        opt: list[str] = []
        if force:
            opt = ["--force"]
        elif drop_branch or not self.lane_branch:
            self.unpushed_guard()
        if os.path.isdir(self.lane):
            if git("-C", self.main, "worktree", "remove", *opt, self.lane) != 0:
                die(f"git worktree remove refused {self.lane} (uncommitted changes? use --force to discard them)")
        git("-C", self.main, "worktree", "prune")
        if drop_branch:
            git("-C", self.main, "branch", "-D", self.lane_branch, quiet=True)
            say(f"removed {self.lane} and its branch {self.lane_branch}")
        else:
            say(f"removed {self.lane}; branch '{self.lane_branch or 'detached'}' kept (not {task}'s branch per "
                f"{self.env['BOA_BRANCH_GRAMMAR']})")
        remote = self.env["BOA_REMOTE"]
        if git("-C", self.main, "show-ref", "--verify", "--quiet",
               f"refs/remotes/{remote}/{self.lane_branch or 'none'}") == 0:
            say(f"note: {remote}/{self.lane_branch} still exists (deleted by the integrator after the merge)")


def main_spellings(main: str, windows: bool = os.name == "nt") -> list[str]:
    """The ways a generated file spells a path below the main checkout: `<main>/`; on Windows also with `\\` and with
    the doubled `\\\\` of an escaped string (PHP, JSON), compared without regard to case (see holds)."""
    if not windows:
        return [main + "/"]
    m = main.replace("\\", "/").rstrip("/")
    return [m + "/", m.replace("/", "\\") + "\\", m.replace("/", "\\\\") + "\\\\"]


def holds(path: str, needles: list[str], windows: bool = os.name == "nt") -> bool:
    """True if a file below `path` (or `path` itself) contains one of `needles` (on Windows without regard to case)."""
    files = [path] if not os.path.isdir(path) else [os.path.join(d, f) for d, _, fs in os.walk(path) for f in fs]
    nbs = [n.lower().encode() if windows else n.encode() for n in needles]
    for f in files:
        try:
            with open(f, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        if windows:
            data = data.lower()
        if any(nb in data for nb in nbs):
            return True
    return False


def usage() -> int:
    sys.stdout.write(bt.help_text(__doc__))
    return 2


def main(argv: list[str]) -> int:
    bt.on_term_exit()   # a stop mid-copy still removes the temp dir (the finally blocks run)
    if argv[:1] in (["-h"], ["--help"]):
        sys.stdout.write(bt.help_text(__doc__))
        return 0
    if len(argv) < 2:
        return usage()
    cmd, n = argv[0], len(argv)
    try:
        if cmd == "add":
            if n not in (3, 4) or (n == 4 and argv[3] != "--full"):
                return usage()
            Lanes().add(argv[1], argv[2], "full" if n == 4 else "build")
        elif cmd in ("deps", "full"):
            if n != 2:
                return usage()
            getattr(Lanes(), cmd)(argv[1])
        elif cmd == "remove":
            if n not in (2, 3) or (n == 3 and argv[2] != "--force"):
                return usage()
            Lanes().remove(argv[1], n == 3)
        else:
            return usage()
    except Refused as exc:
        print(f"{TOOL}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
