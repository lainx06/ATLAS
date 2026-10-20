"""The tamper demo (UI restructure slice 2, part D): one byte changed in a copy of a recorded
run, then the real recorded-run check (`atlas.ui.recorded.verify`, unchanged) run on the copy.

Nothing executes here except reading, copying and hashing files: no project code, no
subprocess, no network. That is why the demo works in hosted mode (ATLAS_HOSTED=1) without
`atlas.hosted.refuse_if_hosted`: that guard protects execution entry points, and none is
reached from here (tests/unit/test_ui_tamper.py runs the demo with ATLAS_HOSTED=1 under a
subprocess and socket tripwire).

`run_demo`, in order:

1. the file to change must be one of the fixed files (`copy.TAMPER_FILES`) and one the run
   recorded a hash for;
2. the run directory is scanned without following links: any symbolic link or other reparse
   point refuses the demo, and so does a total size over `MAX_BYTES` (50 MB);
3. the original must verify (`verify`, intact) and every file's SHA-256 is taken;
4. the run is copied into a fresh temporary directory (`tempfile.mkdtemp`, never inside the
   repository), the copy's file gets exactly one byte changed (its last byte: a line break
   becomes a space, anything else becomes a space too, and a space becomes a line break), and
   `verify` runs on the copy;
5. the temporary directory is deleted, whatever happened (also on an error);
6. the original is verified again and every file's SHA-256 must be unchanged; otherwise
   `OriginalChanged` is raised and no result is returned.

`SessionLimit` holds the per-session limits: one demo at a time, at most `PER_HOUR` per hour.
"""

import os
import shutil
import stat
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import recorded as R
from atlas.ui.catalogue import ROOT

MAX_BYTES = 50 * 1024 * 1024
MAX_MB = 50
PER_HOUR = 5
WINDOW_S = 3600.0
FILES = tuple(rel for rel, _label in C.TAMPER_FILES)
LABELS = dict(C.TAMPER_FILES)
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class Refused(Exception):
    """The demo did not start; `message` is fixed copy."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class OriginalChanged(Exception):
    """The original recording did not verify, or a file changed, after the demo."""


@dataclass(frozen=True)
class Demo:
    rel: str  # the file changed in the copy, relative to the run
    offset: int
    old: int
    new: int
    checks: tuple[R.Check, ...]  # verify() on the changed copy
    original_checks: tuple[R.Check, ...]  # verify() on the original, after the demo
    original_files: int  # files in the original, each byte-for-byte unchanged

    @property
    def differing(self) -> list[R.Check]:
        return [c for c in self.checks if not c.ok]


def options(checks: list[R.Check]) -> list[str]:
    """The fixed files this run recorded a hash for (in `copy.TAMPER_FILES` order)."""
    hashed = {c.item for c in checks if c.ok and ":" not in c.item}
    return [rel for rel in FILES if rel in hashed]


def label(item: str) -> str:
    """A differing item in plain words (Expert view shows the item itself)."""
    if item in LABELS:
        return LABELS[item]
    return C.TAMPER_ITEM_OUTCOME if ":" in item else C.TAMPER_ITEM_FILE


def _is_link(path: Path) -> bool:
    st = os.lstat(path)
    return stat.S_ISLNK(st.st_mode) or bool(
        getattr(st, "st_file_attributes", 0) & _REPARSE
    )


def scan(run_dir: Path) -> list[str]:
    """Every file under `run_dir` (relative, forward slashes), without following links. A link
    or reparse point anywhere refuses the demo; so does a total over MAX_BYTES."""
    run_dir = Path(run_dir)
    if _is_link(run_dir) or not run_dir.is_dir():
        raise Refused(C.TAMPER_LINK)
    files, total, todo = [], 0, [run_dir]
    while todo:
        folder = todo.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                path = Path(entry.path)
                if _is_link(path):
                    raise Refused(C.TAMPER_LINK)
                if entry.is_dir(follow_symlinks=False):
                    todo.append(path)
                elif entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                    if total > MAX_BYTES:
                        raise Refused(C.TAMPER_TOO_LARGE.format(mb=MAX_MB))
                    files.append(path.relative_to(run_dir).as_posix())
    return sorted(files)


def hashes(run_dir: Path, files: list[str]) -> dict[str, str]:
    return {rel: A.sha256_file(Path(run_dir) / rel) for rel in files}


def _check(run_dir: Path) -> list[R.Check]:
    return R.verify(run_dir, A.read_json(Path(run_dir) / "agent_report.json"))


def _inside(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
    except ValueError:
        return False
    return True


def _copy(run_dir: Path, files: list[str], dest: Path) -> None:
    for rel in files:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(run_dir) / rel, target, follow_symlinks=False)


def change_one_byte(path: Path) -> tuple[int, int, int]:
    """Changes the file's last byte (a space becomes a line break; any other byte becomes a
    space) and returns (offset, old, new)."""
    data = bytearray(Path(path).read_bytes())
    if not data:
        raise Refused(C.TAMPER_UNKNOWN_FILE)
    offset, old = len(data) - 1, data[-1]
    new = 0x0A if old == 0x20 else 0x20
    data[offset] = new
    Path(path).write_bytes(bytes(data))
    return offset, old, new


def run_demo(run_dir: Path, rel: str, *, tmp_parent: str | None = None) -> Demo:
    """See the module docstring. Raises Refused (nothing copied or changed) or
    OriginalChanged; any other error propagates after the temporary directory is deleted."""
    run_dir = Path(run_dir)
    if rel not in FILES:
        raise Refused(C.TAMPER_UNKNOWN_FILE)
    files = scan(run_dir)
    before_checks = _check(run_dir)
    if not R.intact(before_checks):
        raise Refused(C.TAMPER_NOT_INTACT)
    if rel not in options(before_checks) or rel not in files:
        raise Refused(C.TAMPER_UNKNOWN_FILE)
    before = hashes(run_dir, files)
    tmp = Path(tempfile.mkdtemp(prefix="atlas-tamper-", dir=tmp_parent))
    try:
        if _inside(tmp, ROOT) or _inside(tmp, run_dir):
            raise Refused(C.TAMPER_FAILED)
        copy = tmp / "run"
        _copy(run_dir, files, copy)
        offset, old, new = change_one_byte(copy / rel)
        checks = tuple(_check(copy))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    after_checks = original_intact(run_dir, before)
    return Demo(rel, offset, old, new, checks, tuple(after_checks), len(before))


def original_intact(run_dir: Path, before: dict[str, str]) -> list[R.Check]:
    """The original verified again, with every file's hash equal to `before`."""
    try:
        files = scan(run_dir)
    except Refused as exc:
        raise OriginalChanged() from exc
    checks = _check(run_dir)
    if files != sorted(before) or hashes(run_dir, files) != before:
        raise OriginalChanged()
    if not R.intact(checks):
        raise OriginalChanged()
    return checks


@dataclass
class SessionLimit:
    """One demo at a time per session, at most PER_HOUR per WINDOW_S."""

    clock: Callable[[], float] = time.monotonic
    started: list[float] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def acquire(self) -> str | None:
        """None when a demo may start now (the caller must call `release`); else the
        refusal message."""
        if not self.lock.acquire(blocking=False):
            return C.TAMPER_BUSY
        now = self.clock()
        self.started = [t for t in self.started if now - t < WINDOW_S]
        if len(self.started) >= PER_HOUR:
            self.lock.release()
            return C.TAMPER_RATE.format(n=PER_HOUR)
        self.started.append(now)
        return None

    def release(self) -> None:
        self.lock.release()
