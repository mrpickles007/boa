"""Portable file locks and paths for the BOA Python tools (no module-level platform import).

FileLock(path): an exclusive lock held on `path` (a lock file, created when missing) for the `with` block:
  * POSIX (Linux, macOS): fcntl.flock on the lock file;
  * Windows: msvcrt.locking on its first byte (retried every 50 ms).
Both are released by the operating system when their process ends, so a lock is never left stale. A holder may remove
the lock file before it releases: a waiter that then gets the lock on the removed file sees the path gone (or holding
another file) and locks the file at the path again, so a lock file can be deleted safely (POSIX; on Windows a lock file
in use cannot be deleted). A file system that reports no inode numbers is trusted as is. A platform with
neither refuses with LockError (no weaker fallback). Every kind waits at most `timeout` seconds (default 60), then
raises LockTimeout (a LockError) naming the lock: its holder is a live process.
makedirs_private(dir): create `dir` and every missing parent with mode 0700 (the state dir and its locks/ are private
  whoever creates them first; an existing directory is left as it is).
lock_path(state_dir, target): the lock file of a target file (one per real path, under <state_dir>/locks/), so two tools
that rewrite or read the same file (metalearning append, memory_write --ingest and --mark) take the same lock.
posix_rel(path, root): `path` relative to `root` with `/` separators on every platform (what the ledger stores).
same_path(a, b): equal after normpath + normcase (Windows is case-insensitive).
Python 3 standard library only.
"""

from __future__ import annotations

import hashlib
import os
import pathlib
import time


class LockError(Exception):
    pass


class LockTimeout(LockError):
    pass


def _impl() -> str | None:
    try:
        import fcntl  # noqa: F401
        return "fcntl"
    except ImportError:
        pass
    try:
        import msvcrt  # noqa: F401
        return "msvcrt"
    except ImportError:
        return None


def makedirs_private(d: str) -> None:
    missing = []
    while d and not os.path.isdir(d):
        missing.append(d)
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    for x in reversed(missing):
        try:
            os.mkdir(x, 0o700)
        except FileExistsError:
            continue
        os.chmod(x, 0o700)   # exactly 0700, whatever the umask


class FileLock:
    def __init__(self, path: str, timeout: float = 60.0):
        self.path, self.timeout = path, timeout
        self.kind = _impl()
        self.fh = None

    def __enter__(self) -> "FileLock":
        if self.kind is None:
            raise LockError("no file locking on this platform: BOA needs fcntl (Linux, macOS) or msvcrt (Windows)")
        makedirs_private(os.path.dirname(self.path) or ".")
        deadline = time.monotonic() + self.timeout
        self.fh = None
        while True:
            if self.fh is None:
                self.fh = open(self.path, "a+")
            try:
                if self.kind == "fcntl":
                    import fcntl
                    fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    import msvcrt
                    self.fh.seek(0)
                    msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                if time.monotonic() > deadline:
                    self.fh.close()
                    self.fh = None
                    raise LockTimeout(f"lock {self.path}: busy for {self.timeout:.0f} s — another process holds it "
                                      f"({self.kind} locks are released when their process ends, so the holder is "
                                      "alive): wait for it to finish, or stop it")
                time.sleep(0.05)
                continue
            if self.kind != "fcntl" or self._same_file():
                return self
            # locked a lock file its holder removed before releasing: lock the one at the path now (within the deadline)
            self._release()
            if time.monotonic() > deadline:
                raise LockTimeout(f"lock {self.path}: the lock file keeps being replaced for {self.timeout:.0f} s")
            time.sleep(0.05)

    def _same_file(self) -> bool:
        """The locked file is the one at the path (POSIX). A file system that reports no inode (0) cannot tell: yes."""
        try:
            a, b = os.fstat(self.fh.fileno()), os.stat(self.path)
        except OSError:
            return False
        if a.st_ino == 0 or b.st_ino == 0:
            return True
        return (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino)

    def _release(self) -> None:
        self.__exit__()

    def __exit__(self, *exc: object) -> None:
        if self.fh is None:
            return
        if self.kind == "msvcrt":
            import msvcrt
            try:
                self.fh.seek(0)
                msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        self.fh.close()  # closing releases an fcntl lock
        self.fh = None


def lock_path(state_dir: str, target: str) -> str:
    key = hashlib.sha256(os.path.normcase(os.path.realpath(target)).encode()).hexdigest()[:16]
    return os.path.join(state_dir, "locks", f"{key}.lock")


def posix_rel(path: str, root: str, pathmod=os.path) -> str:
    return pathmod.relpath(path, root).replace(pathmod.sep, "/")


def same_path(a: str, b: str, pathmod=os.path) -> bool:
    return pathmod.normcase(pathmod.normpath(a)) == pathmod.normcase(pathmod.normpath(b))


def from_posix(root: str, rel: str, pathmod=os.path) -> str:
    """A path stored with `/` (the ledger, git) joined to `root` with the platform's separators."""
    return pathmod.normpath(pathmod.join(root, *pathlib.PurePosixPath(rel).parts))
