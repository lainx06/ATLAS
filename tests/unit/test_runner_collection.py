"""Host-side output collection for the Docker runner: frame, archive and bounded IO. Offline.

The archives here are built by the test, standing in for a malicious or broken supervisor.
"""

import hashlib
import io
import json
import subprocess
import sys
import tarfile

import pytest

from atlas.runner.docker import (
    FRAME_MAGIC,
    CollectionError,
    Limits,
    communicate_bounded,
    extract_archive,
    parse_frame,
)

SMALL = Limits(output_bytes=4096, max_output_files=4)


def tar_bytes(entries) -> bytes:
    """entries: (name, data | None, type); type defaults to a regular file."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for entry in entries:
            name, data, kind = (*entry, tarfile.REGTYPE)[:3]
            info = tarfile.TarInfo(name)
            info.type = kind
            if kind == tarfile.SYMTYPE or kind == tarfile.LNKTYPE:
                info.linkname = "/etc/passwd"
            payload = data or b""
            info.size = len(payload) if kind == tarfile.REGTYPE else 0
            tar.addfile(info, io.BytesIO(payload) if kind == tarfile.REGTYPE else None)
    return buf.getvalue()


def frame(archive: bytes, **header) -> bytes:
    head = {
        "version": 1,
        "archive_bytes": len(archive),
        "archive_sha256": hashlib.sha256(archive).hexdigest(),
        **header,
    }
    return FRAME_MAGIC + json.dumps(head).encode() + b"\n" + archive


# --- frame ---------------------------------------------------------------------------------


def test_valid_frame_round_trips(tmp_path):
    archive = tar_bytes([("runtime.json", b"{}"), ("predictions/f0.parquet", b"x")])
    header, body = parse_frame(frame(archive, child_returncode=0), SMALL)
    assert header["child_returncode"] == 0
    files = extract_archive(body, tmp_path / "out", SMALL)
    assert [f["path"] for f in files] == ["runtime.json", "predictions/f0.parquet"]
    assert (tmp_path / "out" / "predictions" / "f0.parquet").read_bytes() == b"x"


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"", "missing_frame"),
        (b"noise before" + frame(b""), "missing_frame"),
        (FRAME_MAGIC + b"{not json}\n", "malformed_header"),
        (FRAME_MAGIC + b"[1, 2]\n", "malformed_header"),
        (
            FRAME_MAGIC + b'{"version": 2, "archive_bytes": 0, "archive_sha256": ""}\n',
            "malformed_header",
        ),
        (FRAME_MAGIC + b"x" * (300 * 1024), "malformed_header"),
        (frame(b"abc") + b"trailing", "archive_length_mismatch"),
    ],
    ids=[
        "empty",
        "noise_before_magic",
        "header_not_json",
        "header_not_object",
        "wrong_version",
        "header_over_cap",
        "trailing_bytes",
    ],
)
def test_malformed_frames_are_rejected(data, code):
    with pytest.raises(CollectionError) as exc:
        parse_frame(data, SMALL)
    assert exc.value.code == code


def test_hash_mismatch_is_rejected():
    data = bytearray(frame(b"abcd"))
    data[-1] ^= 1
    with pytest.raises(CollectionError) as exc:
        parse_frame(bytes(data), SMALL)
    assert exc.value.code == "archive_hash_mismatch"


def test_oversized_archive_is_rejected():
    archive = b"\0" * (SMALL.max_archive_bytes + 1)
    with pytest.raises(CollectionError) as exc:
        parse_frame(frame(archive), SMALL)
    assert exc.value.code == "archive_too_large"


# --- archive entries -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("entries", "code"),
    [
        ([("/etc/cron.d/x", b"1")], "unsafe_path"),
        ([("../escape.txt", b"1")], "unsafe_path"),
        ([("a/../../escape.txt", b"1")], "unsafe_path"),
        ([("a\\b.txt", b"1")], "unsafe_path"),
        ([("C:/Windows/x.txt", b"1")], "unsafe_path"),
        ([("nul.txt", b"1")], "unsafe_path"),
        ([("link", None, tarfile.SYMTYPE)], "unsafe_entry_type"),
        ([("hard", None, tarfile.LNKTYPE)], "unsafe_entry_type"),
        ([("dir", None, tarfile.DIRTYPE)], "unsafe_entry_type"),
        ([("fifo", None, tarfile.FIFOTYPE)], "unsafe_entry_type"),
        ([("dev", None, tarfile.CHRTYPE)], "unsafe_entry_type"),
        ([("a.txt", b"1"), ("a.txt", b"2")], "duplicate_entry"),
        ([("A.txt", b"1"), ("a.txt", b"2")], "duplicate_entry"),
        ([("a", b"1"), ("a/b", b"2")], "path_conflict"),
        ([("a/b", b"1"), ("a", b"2")], "path_conflict"),
        ([(f"f{i}", b"1") for i in range(5)], "file_count_exceeded"),
        ([("big", b"x" * 4097)], "expanded_bytes_exceeded"),
        ([("x", b"x" * 3000), ("y", b"y" * 3000)], "expanded_bytes_exceeded"),
    ],
)
def test_unsafe_archives_are_rejected_before_writing(tmp_path, entries, code):
    dest = tmp_path / "out"
    with pytest.raises(CollectionError) as exc:
        extract_archive(tar_bytes(entries), dest, SMALL)
    assert exc.value.code == code
    assert not dest.exists()  # validation happens before anything is written


def test_corrupt_archive_is_rejected(tmp_path):
    with pytest.raises(CollectionError) as exc:
        extract_archive(b"\x01" * 1024, tmp_path / "out", SMALL)
    assert exc.value.code == "malformed_archive"


# --- parser resource bounds (Codex review of f494c95, finding 3) ---------------------------


def test_deeply_nested_header_is_a_collection_error():
    """A few KB of nesting, far below the header byte cap (Codex's reproduction)."""
    header = b'{"nested":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}"
    with pytest.raises(CollectionError) as exc:
        parse_frame(FRAME_MAGIC + header + b"\n", SMALL)
    assert exc.value.code == "malformed_header"


def _pax_record(payload: bytes, kind=tarfile.XHDTYPE) -> bytes:
    info = tarfile.TarInfo("pax")
    info.type, info.size = kind, len(payload)
    padding = b"\0" * (-len(payload) % tarfile.BLOCKSIZE)
    return info.tobuf(format=tarfile.USTAR_FORMAT) + payload + padding


def _member(name: str, data: bytes, size: int | None = None) -> bytes:
    info = tarfile.TarInfo(name)
    info.size = len(data) if size is None else size
    padding = b"\0" * (-len(data) % tarfile.BLOCKSIZE)
    return info.tobuf(format=tarfile.USTAR_FORMAT) + data + padding


END = b"\0" * (2 * tarfile.BLOCKSIZE)


def test_consecutive_pax_headers_are_a_collection_error(tmp_path):
    """600 chained extension records recurse in tarfile (Codex's reproduction)."""
    archive = _pax_record(b"10 path=x\n") * 600 + _member("file.txt", b"x") + END
    assert len(archive) <= Limits().max_archive_bytes
    with pytest.raises(CollectionError) as exc:
        extract_archive(archive, tmp_path / "out", Limits())
    assert exc.value.code == "malformed_archive"
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "archive",
    [
        _pax_record(b"10 path=x\n", tarfile.XGLTYPE) + _member("a.txt", b"x") + END,
        _pax_record(b"a" * 120 + b"\0", tarfile.GNUTYPE_LONGNAME)
        + _member("a.txt", b"x")
        + END,
        _pax_record(b"9 size=0\n") + _member("a.txt", b"x") + END,
        _pax_record(b"10 path=x\n") + END,
        _pax_record(b"99 path=x\n") + _member("a.txt", b"x") + END,
        _member("a.txt", b"x") + END + b"\x01" + b"\0" * 511,
    ],
    ids=[
        "global_pax",
        "gnu_longname",
        "pax_size_override",
        "pax_without_member",
        "bad_pax_record",
        "data_after_end",
    ],
)
def test_unexpected_tar_structure_is_rejected(tmp_path, archive):
    with pytest.raises(CollectionError) as exc:
        extract_archive(archive, tmp_path / "out", SMALL)
    assert exc.value.code == "malformed_archive"
    assert not (tmp_path / "out").exists()


def test_single_pax_header_for_a_non_ascii_name_is_accepted(tmp_path):
    """The supervisor writes PAX: a non-ASCII name needs one extension header."""
    archive = tar_bytes([("résumé.txt", b"1")])
    files = extract_archive(archive, tmp_path / "out", SMALL)
    assert [f["path"] for f in files] == ["résumé.txt"]


def test_existing_destination_is_not_overwritten(tmp_path):
    (tmp_path / "out").mkdir()
    with pytest.raises(FileExistsError):
        extract_archive(tar_bytes([("a", b"1")]), tmp_path / "out", SMALL)


# --- bounded IO ------------------------------------------------------------------------------


def _python(code: str) -> subprocess.Popen:
    """A trusted helper process written by this test (not candidate code)."""
    return subprocess.Popen(
        [sys.executable, "-c", code],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _finish(proc, result):
    proc.kill()
    proc.wait(timeout=10)
    for t in result["threads"]:
        t.join(timeout=5)


def test_stdout_cap_stops_reading_early():
    limits = Limits(output_bytes=1024, max_output_files=1, host_deadline_s=20)
    proc = _python("import sys\nwhile True: sys.stdout.buffer.write(b'x' * 65536)")
    result = communicate_bounded(proc, limits)
    _finish(proc, result)
    assert result["problems"] == ["stdout_cap_exceeded"]
    assert len(result["stdout"]) <= limits.max_stdout_bytes
    assert not result["host_timed_out"]


def test_stderr_cap_stops_reading_early():
    limits = Limits(max_stderr_bytes=4096, host_deadline_s=20)
    proc = _python("import sys\nwhile True: sys.stderr.buffer.write(b'e' * 65536)")
    result = communicate_bounded(proc, limits)
    _finish(proc, result)
    assert result["problems"] == ["stderr_cap_exceeded"]


def test_host_deadline_returns_promptly():
    proc = _python("import time; time.sleep(60)")
    result = communicate_bounded(proc, Limits(host_deadline_s=1.0))
    _finish(proc, result)
    assert result["host_timed_out"] is True
