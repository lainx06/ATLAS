"""Candidate revisions: snapshot, diff validation, hashing and approval (SPEC §9).

- **Snapshot:** built only from three explicitly permitted inputs of a supported project: the
  manifest (re-serialized from the validated model), the declared table (bytes copied) and the
  entry point (UTF-8, LF-normalized). Nothing else is copied. Symlinks, reparse points, path
  escapes and colliding paths are refused.
- **Bounded reads:** every input is read through one checked path: the path is validated and
  each component lstat-checked, the opened handle must be the same regular file (device and
  inode), its size must be within the input's cap, and at most cap + 1 bytes are read. This
  happens before any parsing (manifest JSON, entry-point AST), and the same bounded reads hash
  the snapshot when it is revalidated.
- **Diff validation (hygiene, not the boundary):** one unified diff that modifies only the
  entry point; no new, deleted, renamed, binary or mode-changing files; at most 64 KiB; hunks
  must apply exactly (no fuzz); the result must `ast.parse`.
- **Hashes:** base_snapshot_hash = sha256 of the canonical inventory (path, sha256) of the
  snapshot; candidate_hash = sha256(bytes.fromhex(base_snapshot_hash) + entry_point bytes).
- **Approval:** {candidate_hash, base_snapshot_hash, approved_at}. The runner recomputes both
  hashes from the exact bytes it is about to mount and refuses on any mismatch.
"""

import ast
import hashlib
import json
import os
import re
import stat
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from atlas.contracts import Manifest
from atlas.intake import MANIFEST_NAME, manifest_reason, source_uses_adapter

MAX_DIFF_BYTES = 64 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
MAX_ENTRY_BYTES = 256 * 1024
MAX_TABLE_BYTES = 64 * 1024 * 1024
_HASH_CHUNK = 1 << 20
_WINDOWS_RESERVED = re.compile(
    r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$", re.IGNORECASE
)
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$")
_FORBIDDEN_HEADERS = (
    "new file mode",
    "deleted file mode",
    "old mode",
    "new mode",
    "rename from",
    "rename to",
    "copy from",
    "copy to",
    "similarity index",
    "dissimilarity index",
    "Binary files",
    "GIT binary patch",
)


class SnapshotError(ValueError):
    pass


class CandidateRejected(ValueError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


@dataclass(frozen=True)
class Snapshot:
    root: Path
    entry_point: str
    table_path: str
    inventory: tuple[tuple[str, str], ...]
    base_hash: str


@dataclass(frozen=True)
class Candidate:
    entry_point: str
    entry_bytes: bytes
    diff_sha256: str


@dataclass(frozen=True)
class Approval:
    candidate_hash: str
    base_snapshot_hash: str
    approved_at: str

    def to_dict(self) -> dict:
        return asdict(self)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_relpath(rel: str) -> str:
    """A normalized relative POSIX path that cannot escape its root on Linux or Windows."""
    if not isinstance(rel, str) or not rel or len(rel) > 200:
        raise SnapshotError(f"invalid path {rel!r}")
    if "\\" in rel or ":" in rel or rel.startswith("/") or "\x00" in rel:
        raise SnapshotError(f"path {rel!r} is absolute or not POSIX")
    parts = rel.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            raise SnapshotError(f"path {rel!r} is not normalized or escapes its root")
        if part != part.rstrip(" .") or any(ord(c) < 32 for c in part):
            raise SnapshotError(f"path {rel!r} has an unsafe component")
        if _WINDOWS_RESERVED.match(part):
            raise SnapshotError(f"path {rel!r} uses a reserved device name")
    return str(PurePosixPath(rel))


def _is_link_like(path: Path) -> bool:
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode):
        return True
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(st, "st_file_attributes", 0) & reparse)


def _open_permitted(root: Path, rel: str, max_bytes: int):
    """Open root/rel for a bounded read: a validated path with no link-like component, a
    regular file within `max_bytes`, and an open handle that is that same file. OS errors
    become SnapshotError."""
    rel = safe_relpath(rel)
    try:
        return _open_checked(root, rel, max_bytes)
    except FileNotFoundError:
        raise SnapshotError(f"{rel} does not exist") from None
    except OSError as exc:
        raise SnapshotError(f"{rel} cannot be read ({type(exc).__name__})") from exc


def _open_checked(root: Path, rel: str, max_bytes: int):
    current = root
    for part in rel.split("/"):
        current = current / part
        if _is_link_like(current):
            raise SnapshotError(f"{rel} passes through a symlink or reparse point")
    checked = os.lstat(current)
    if not stat.S_ISREG(checked.st_mode):
        raise SnapshotError(f"{rel} is not a regular file")
    if not current.resolve().is_relative_to(root.resolve()):
        raise SnapshotError(f"{rel} resolves outside the project")
    if checked.st_size > max_bytes:
        raise SnapshotError(f"{rel} exceeds {max_bytes} bytes")
    f = open(current, "rb")  # noqa: SIM115 - returned to the caller, which closes it
    try:
        opened = os.fstat(f.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            checked.st_dev,
            checked.st_ino,
        ):
            raise SnapshotError(f"{rel} changed while being opened")
        if opened.st_size > max_bytes:
            raise SnapshotError(f"{rel} exceeds {max_bytes} bytes")
    except BaseException:
        f.close()
        raise
    return f


def _permitted_file(root: Path, rel: str, max_bytes: int) -> bytes:
    """The bytes of root/rel, read through `_open_permitted`: at most max_bytes + 1 are read."""
    with _open_permitted(root, rel, max_bytes) as f:
        data = f.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise SnapshotError(f"{rel} exceeds {max_bytes} bytes")
    return data


def _permitted_sha256(root: Path, rel: str, max_bytes: int) -> str:
    """sha256 of root/rel, streamed through `_open_permitted` with the same byte bound."""
    h, total = hashlib.sha256(), 0
    with _open_permitted(root, rel, max_bytes) as f:
        while chunk := f.read(min(_HASH_CHUNK, max_bytes + 1 - total)):
            total += len(chunk)
            if total > max_bytes:
                raise SnapshotError(f"{rel} exceeds {max_bytes} bytes")
            h.update(chunk)
    return h.hexdigest()


def _lf(data: bytes, what: str) -> bytes:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SnapshotError(f"{what} is not UTF-8") from exc
    return data.replace(b"\r\n", b"\n")


def inventory_hash(inventory) -> str:
    canonical = json.dumps([list(item) for item in inventory], separators=(",", ":"))
    return sha256_bytes(canonical.encode("utf-8"))


def input_limits(snapshot: Snapshot) -> dict[str, int]:
    """Byte cap per permitted input path (used again when the snapshot is revalidated)."""
    return {
        MANIFEST_NAME: MAX_MANIFEST_BYTES,
        snapshot.entry_point: MAX_ENTRY_BYTES,
        snapshot.table_path: MAX_TABLE_BYTES,
    }


def build_snapshot(project: Path, dest: Path) -> Snapshot:
    """Copy the three permitted inputs of a supported project into the new directory `dest`.

    The intake decision is made here on bounded in-memory reads (the same checks as
    `intake.load_project`), so nothing is parsed before its path and size are validated.
    """
    project = Path(project)
    raw_manifest = _permitted_file(project, MANIFEST_NAME, MAX_MANIFEST_BYTES)
    try:
        manifest = Manifest.model_validate_json(raw_manifest)
    except (ValueError, RecursionError) as exc:
        raise SnapshotError(
            f"project not supported: manifest unparseable ({type(exc).__name__})"
        ) from exc
    reason = manifest_reason(manifest)
    if reason is not None:
        raise SnapshotError(f"project not supported: {reason}")
    entry = safe_relpath(manifest.entry_point)
    table = safe_relpath(manifest.table.path)
    if not entry.endswith(".py"):
        raise SnapshotError("entry point is not a .py file")
    names = [MANIFEST_NAME, entry, table]
    if len({n.casefold() for n in names}) != 3:
        raise SnapshotError("manifest, entry point and table paths collide")
    entry_bytes = _lf(_permitted_file(project, entry, MAX_ENTRY_BYTES), "entry point")
    table_bytes = _permitted_file(project, table, MAX_TABLE_BYTES)
    try:
        uses = source_uses_adapter(entry_bytes.decode("utf-8"), entry)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
        raise SnapshotError(
            f"entry point cannot be parsed ({type(exc).__name__})"
        ) from exc
    if not uses:
        raise SnapshotError(
            "project not supported: entry point does not use the ATLAS adapter"
        )
    manifest_bytes = (
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    if len(manifest_bytes) > MAX_MANIFEST_BYTES:
        raise SnapshotError(
            f"re-serialized manifest exceeds {MAX_MANIFEST_BYTES} bytes"
        )
    contents = {MANIFEST_NAME: manifest_bytes, entry: entry_bytes, table: table_bytes}
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=False)
    for rel, data in contents.items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "xb") as f:
            f.write(data)
    inventory = tuple(sorted((rel, sha256_bytes(d)) for rel, d in contents.items()))
    return Snapshot(dest, entry, table, inventory, inventory_hash(inventory))


def current_inventory(
    root: Path, limits: dict[str, int]
) -> tuple[tuple[str, str], ...]:
    """Re-hash a tree from disk, bounded: `limits` maps each expected file to its byte cap.

    Refuses at the first entry that is neither an expected file nor one of their parent
    directories (so enumeration stops early), any symlink or reparse point, missing files and
    files over their cap. Hashes are streamed with the bounded reads of `_open_permitted`.
    """
    root = Path(root)
    expected_dirs = {
        "/".join(parts[:i])
        for parts in (rel.split("/") for rel in limits)
        for i in range(1, len(parts))
    }
    found, pending = [], [""]
    try:
        while pending:
            rel_dir = pending.pop()
            with os.scandir(root / rel_dir if rel_dir else root) as entries:
                for entry in entries:
                    rel = f"{rel_dir}/{entry.name}" if rel_dir else entry.name
                    if rel not in limits and rel not in expected_dirs:
                        raise SnapshotError(
                            "staged files differ from the snapshot's permitted inputs "
                            f"(unexpected {rel[:200]!r})"
                        )
                    if _is_link_like(root / rel):
                        raise SnapshotError(f"{rel} is a symlink or reparse point")
                    if rel in expected_dirs:
                        if not entry.is_dir(follow_symlinks=False):
                            raise SnapshotError(f"{rel} is not a directory")
                        pending.append(rel)
                    else:
                        found.append((rel, _permitted_sha256(root, rel, limits[rel])))
    except OSError as exc:  # e.g. a directory removed while being listed
        raise SnapshotError(f"tree cannot be read ({type(exc).__name__})") from exc
    if sorted(rel for rel, _ in found) != sorted(limits):
        raise SnapshotError("staged files differ from the snapshot's permitted inputs")
    return tuple(sorted(found))


def candidate_hash(base_snapshot_hash: str, entry_bytes: bytes) -> str:
    return sha256_bytes(bytes.fromhex(base_snapshot_hash) + entry_bytes)


def approve(snapshot: Snapshot, candidate: Candidate, approved_at=None) -> Approval:
    """Record approval of one exact candidate against one exact snapshot."""
    when = approved_at or datetime.now(UTC).isoformat()
    return Approval(
        candidate_hash(snapshot.base_hash, candidate.entry_bytes),
        snapshot.base_hash,
        when,
    )


# --- diff validation ------------------------------------------------------------------------


def _header_path(line: str, prefix: str) -> str:
    raw = line[len(prefix) :].split("\t", 1)[0]
    if raw == "/dev/null":
        raise CandidateRejected("file_created_or_deleted", raw)
    for strip in ("a/", "b/"):
        if raw.startswith(strip):
            raw = raw[len(strip) :]
            break
    try:
        return safe_relpath(raw)
    except SnapshotError as exc:
        raise CandidateRejected("path_escape", str(exc)) from exc


def _parse_hunks(lines: list[str], start: int) -> list[dict]:
    hunks, i = [], start
    while i < len(lines):
        m = _HUNK.match(lines[i])
        if not m:
            raise CandidateRejected("malformed_diff", f"unexpected line {i + 1}")
        old_start = int(m.group(1))
        old_count = int(m.group(2)) if m.group(2) is not None else 1
        new_count = int(m.group(4)) if m.group(4) is not None else 1
        old, new, i = [], [], i + 1
        while i < len(lines) and (len(old) < old_count or len(new) < new_count):
            line = lines[i]
            tag, text = line[:1], line[1:] + "\n"
            if tag == " ":
                old.append(text)
                new.append(text)
            elif tag == "-":
                old.append(text)
            elif tag == "+":
                new.append(text)
            else:
                raise CandidateRejected("malformed_diff", f"bad hunk line {i + 1}")
            i += 1
            if i < len(lines) and lines[i].startswith("\\"):
                # "\ No newline at end of file" applies to the line just read.
                if tag in " -":
                    old[-1] = old[-1][:-1]
                if tag in " +":
                    new[-1] = new[-1][:-1]
                i += 1
        if len(old) != old_count or len(new) != new_count:
            raise CandidateRejected("malformed_diff", "hunk line counts do not match")
        hunks.append({"old_start": old_start, "old": old, "new": new})
    if not hunks:
        raise CandidateRejected("malformed_diff", "no hunks")
    return hunks


def _apply(original: str, hunks: list[dict]) -> str:
    src = original.splitlines(keepends=True)
    out, pos = [], 0
    for h in hunks:
        start = h["old_start"] - 1 if h["old"] else h["old_start"]
        if start < pos or start + len(h["old"]) > len(src):
            raise CandidateRejected(
                "does_not_apply", "hunks overlap or exceed the file"
            )
        if src[start : start + len(h["old"])] != h["old"]:
            raise CandidateRejected(
                "does_not_apply", f"context mismatch at line {start + 1}"
            )
        out.extend(src[pos:start])
        out.extend(h["new"])
        pos = start + len(h["old"])
    out.extend(src[pos:])
    return "".join(out)


def validate_diff(snapshot: Snapshot, diff) -> Candidate:
    """Validate a unified diff against the snapshot's entry point; return the candidate."""
    data = diff.encode("utf-8") if isinstance(diff, str) else bytes(diff)
    if len(data) > MAX_DIFF_BYTES:
        raise CandidateRejected("too_large", f"{len(data)} > {MAX_DIFF_BYTES} bytes")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CandidateRejected("not_utf8") from exc
    if "\r" in text or "\x00" in text:
        raise CandidateRejected("malformed_diff", "carriage return or NUL in diff")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for line in lines:
        if line.startswith(_FORBIDDEN_HEADERS):
            raise CandidateRejected("forbidden_change", line[:80])
    minus = [i for i, ln in enumerate(lines) if ln.startswith("--- ")]
    plus = [i for i, ln in enumerate(lines) if ln.startswith("+++ ")]
    if len(minus) != 1 or len(plus) != 1 or plus[0] != minus[0] + 1:
        raise CandidateRejected(
            "multiple_or_missing_files", "exactly one file header pair"
        )
    for i, line in enumerate(lines[: minus[0]]):
        if not (line.startswith(("diff --git ", "index "))):
            raise CandidateRejected(
                "malformed_diff", f"unexpected preamble line {i + 1}"
            )
    old_path = _header_path(lines[minus[0]], "--- ")
    new_path = _header_path(lines[plus[0]], "+++ ")
    if old_path != snapshot.entry_point or new_path != snapshot.entry_point:
        raise CandidateRejected(
            "path_not_allowed", f"{old_path} -> {new_path}; only {snapshot.entry_point}"
        )
    original = _permitted_file(
        snapshot.root, snapshot.entry_point, MAX_ENTRY_BYTES
    ).decode("utf-8")
    result = _apply(original, _parse_hunks(lines, plus[0] + 1))
    result_bytes = result.encode("utf-8")
    if len(result_bytes) > MAX_ENTRY_BYTES:
        raise CandidateRejected("too_large", "resulting entry point")
    if result == original:
        raise CandidateRejected("no_change")
    try:
        ast.parse(result, filename=snapshot.entry_point)
    except (SyntaxError, ValueError) as exc:
        raise CandidateRejected("syntax_error", str(exc)) from exc
    except (RecursionError, MemoryError) as exc:
        raise CandidateRejected("too_complex", type(exc).__name__) from exc
    return Candidate(snapshot.entry_point, result_bytes, sha256_bytes(data))
