"""Host-side output collection for the Docker runner: frame, archive and bounded IO. Offline.

The archives here are built by the test, standing in for a malicious or broken supervisor.
"""

import hashlib
import io
import json
import random
import subprocess
import sys
import tarfile

import pytest

from atlas.runner import docker as dr
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


# --- one interpretation for checks and parsing (Codex verification of repair 1, 44c5a84) ----


@pytest.fixture
def json_loads_calls(monkeypatch):
    """Counts json.loads calls: a refused header must be refused before the parser runs."""
    calls, real = [], json.loads

    def spy(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)

    monkeypatch.setattr(json, "loads", spy)
    return calls


def _header_text(extra: str) -> str:
    """A valid frame header (for an empty archive) with `extra` as its first member."""
    rest = json.dumps(
        {
            "version": 1,
            "archive_bytes": 0,
            "archive_sha256": hashlib.sha256().hexdigest(),
        }
    )
    return "{" + extra + "," + rest[1:]


def _nest(depth: int) -> str:
    return "[" * depth + "0" + "]" * depth


@pytest.mark.parametrize("depth", [20, 2000])
@pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16-be", "utf-16", "utf-32"])
def test_non_utf8_header_is_refused_before_parsing(json_loads_calls, encoding, depth):
    """Codex's reproduction: the escaped quote made the byte scan lose string boundaries in
    UTF-16, while json.loads(bytes) auto-detected UTF-16 and parsed the nesting."""
    raw = _header_text('"\\"":' + _nest(depth)).encode(encoding)
    with pytest.raises(CollectionError) as exc:
        parse_frame(FRAME_MAGIC + raw + b"\n", SMALL)
    assert exc.value.code == "malformed_header"
    assert json_loads_calls == []


@pytest.mark.parametrize(
    "raw",
    [
        b"\xef\xbb\xbf" + _header_text('"a":1').encode(),
        _header_text('"a":"\xff"').encode("latin-1"),
        _header_text('"a":1').encode().replace(b'"a"', b'"\0"'),
    ],
    ids=["utf8_bom", "invalid_utf8", "nul_byte"],
)
def test_header_must_be_plain_utf8(json_loads_calls, raw):
    with pytest.raises(CollectionError) as exc:
        parse_frame(FRAME_MAGIC + raw + b"\n", SMALL)
    assert exc.value.code == "malformed_header"
    assert json_loads_calls == []


@pytest.mark.parametrize(
    "key",
    ['"\\""', '"\\\\"', '"a\\"[{"', '"\\u0022"', '"é\\"ü"'],
    ids=[
        "escaped_quote",
        "escaped_backslash",
        "brackets_after_quote",
        "unicode_escape",
        "utf8",
    ],
)
def test_escaped_strings_cannot_hide_nesting(json_loads_calls, key):
    raw = _header_text(key + ":" + _nest(20)).encode("utf-8")
    with pytest.raises(CollectionError) as exc:
        parse_frame(FRAME_MAGIC + raw + b"\n", SMALL)
    assert exc.value.code == "malformed_header"
    assert json_loads_calls == []


@pytest.mark.parametrize(
    "extra",
    [
        '"\\"[[[[[[[[[[\\\\":"]]]]]]]]]]{{{{{{{{{"',
        '"é":"ü \\u00e9 \\ud83d\\ude00 [[[[[[[[[["',
        '"a\\\\":"\\"\\\\\\"\\/\\b\\f\\n\\r\\t"',
        '"deep":' + _nest(7),
    ],
    ids=["brackets_in_strings", "non_ascii", "every_escape", "depth_at_the_limit"],
)
def test_valid_utf8_headers_with_escapes_are_accepted(extra):
    header, _ = parse_frame(FRAME_MAGIC + _header_text(extra).encode() + b"\n", SMALL)
    assert header["version"] == 1


def _max_depth(value) -> int:
    depth, stack = 0, [(value, 1)]
    while stack:
        item, level = stack.pop()
        if isinstance(item, (list, dict)):
            depth = max(depth, level)
            children = item.values() if isinstance(item, dict) else item
            stack.extend((child, level + 1) for child in children)
    return depth


def test_header_depth_check_agrees_with_the_parsed_value():
    """Not just the sample bytes: for generated headers full of quotes, backslashes and
    brackets inside strings, the header is accepted exactly when its real depth is <= 8."""
    rng = random.Random(20261015)
    alphabet = '"\\[]{}:,é\u2028 ab/u'

    def text():
        return "".join(rng.choice(alphabet) for _ in range(rng.randrange(8)))

    def value(depth):
        if depth == 0:
            return rng.choice([0, text(), None])
        if rng.random() < 0.5:
            return [value(depth - 1)]
        return {text(): value(depth - 1)}

    for _ in range(400):
        nested = value(rng.randrange(12))
        head = {
            "version": 1,
            "archive_bytes": 0,
            "archive_sha256": hashlib.sha256().hexdigest(),
            text(): nested,
        }
        raw = json.dumps(head, ensure_ascii=rng.random() < 0.5).encode("utf-8")
        expected = _max_depth(head)
        try:
            parse_frame(FRAME_MAGIC + raw + b"\n", SMALL)
            accepted = True
        except CollectionError as exc:
            assert exc.code == "malformed_header"
            accepted = False
        assert accepted == (expected <= dr.MAX_HEADER_DEPTH), raw


@pytest.fixture
def tarfile_opens(monkeypatch):
    """Counts tarfile.open calls: a refused archive must be refused before tarfile reads it."""
    calls, real = [], tarfile.open

    def spy(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)

    monkeypatch.setattr(tarfile, "open", spy)
    return calls


def _pax_with_padding(declared: bytes, hidden: bytes) -> bytes:
    """A PAX header declaring `declared`, with `hidden` in the padding that tarfile reads."""
    info = tarfile.TarInfo("pax")
    info.type, info.size = tarfile.XHDTYPE, len(declared)
    block = (declared + hidden).ljust(tarfile.BLOCKSIZE, b"\0")
    return info.tobuf(format=tarfile.USTAR_FORMAT) + block


def _hidden_chain() -> bytes:
    """Codex's reproduction: `size=0` in the padding makes tarfile parse the envelope's data,
    600 chained PAX headers, as headers."""
    chain = _pax_record(b"10 path=x\n") * 600 + _member("nested.txt", b"x")
    return (
        _pax_with_padding(b"10 path=x\n", b"9 size=0\n")
        + _member("envelope.txt", chain)
        + END
    )


@pytest.mark.parametrize(
    "archive",
    [
        _pax_with_padding(b"10 path=x\n", b"9 size=0\n")
        + _member("file.txt", b"x")
        + END,
        _hidden_chain(),
        _pax_with_padding(b"10 path=x\n", b"18 path=../escape\n")
        + _member("a.txt", b"x")
        + END,
        _pax_with_padding(b"10 path=x\n", b"\x01") + _member("a.txt", b"x") + END,
    ],
    ids=["hidden_size_zero", "hidden_header_chain", "hidden_path", "nonzero_byte"],
)
def test_nonzero_pax_padding_is_refused_before_tarfile(
    tmp_path, tarfile_opens, archive
):
    assert len(archive) <= Limits().max_archive_bytes
    with pytest.raises(CollectionError) as exc:
        extract_archive(archive, tmp_path / "out", Limits())
    assert exc.value.code == "malformed_archive"
    assert tarfile_opens == []
    assert not (tmp_path / "out").exists()


def _pax(*records: bytes) -> bytes:
    return _pax_record(b"".join(records))


def _record(key: bytes, value: bytes) -> bytes:
    """One PAX record; its length field counts the whole record, itself included."""
    body = b" " + key + b"=" + value + b"\n"
    length = len(body)
    while len(body) + len(str(length)) != length:
        length = len(body) + len(str(length))
    return str(length).encode() + body


@pytest.mark.parametrize(
    "pax",
    [
        _pax(_record(b"mtime", b"1.5")),
        _pax(_record(b"hdrcharset", b"BINARY"), _record(b"path", b"x")),
        _pax(_record(b"uname", b"root")),
        _pax(_record(b"path", b"a"), _record(b"path", b"b")),
        _pax(_record(b"path", b"\xff")),
        _pax(b"6 =ab\n"),
        _pax(_record(b"path", b"x") + b"\0" * 4),
    ],
    ids=[
        "mtime",
        "hdrcharset",
        "uname",
        "duplicate_path",
        "non_utf8_path",
        "empty_key",
        "nul_after_records",
    ],
)
def test_pax_records_other_than_one_utf8_path_are_refused(tmp_path, tarfile_opens, pax):
    with pytest.raises(CollectionError) as exc:
        extract_archive(pax + _member("a.txt", b"x") + END, tmp_path / "out", SMALL)
    assert exc.value.code == "malformed_archive"
    assert tarfile_opens == []
    assert not (tmp_path / "out").exists()


def _with_field(member: bytes, start: int, end: int, value: bytes) -> bytes:
    """Overwrite one header field and recompute the checksum, as a hostile writer could."""
    block = bytearray(member[: tarfile.BLOCKSIZE])
    block[start:end] = value.ljust(end - start, b"\0")
    block[148:156] = b" " * 8
    block[148:156] = b"%06o\0 " % sum(block)
    return bytes(block) + member[tarfile.BLOCKSIZE :]


def test_member_tarfile_would_silently_drop_is_refused(tmp_path, tarfile_opens):
    """tarfile treats an invalid number in a later header as the end of the archive and
    returns fewer members; the pre-check must not count members tarfile never yields."""
    bad = _with_field(_member("b.txt", b"y"), 136, 148, b"not-octal")
    archive = _member("a.txt", b"x") + bad + END
    with pytest.raises(CollectionError) as exc:
        extract_archive(archive, tmp_path / "out", SMALL)
    assert exc.value.code == "malformed_archive"
    assert tarfile_opens == []
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "tamper",
    [
        lambda layout: [layout[0]._replace(size=layout[0].size + 1), *layout[1:]],
        lambda layout: [layout[0]._replace(next_offset=layout[0].next_offset + 512)],
        lambda layout: [layout[0]._replace(pax={"path": "other.txt"}), *layout[1:]],
        lambda layout: layout[:1],
        lambda layout: [*layout, layout[-1]],
    ],
    ids=["size", "next_offset", "pax", "tarfile_has_more", "tarfile_has_fewer"],
)
def test_tarfile_must_agree_with_the_prechecked_layout(tmp_path, monkeypatch, tamper):
    """The safety net behind the pre-check: tarfile is stepped one member at a time, and any
    difference from the pre-checked layout is refused before tarfile reads further."""
    archive = tar_bytes([("résumé.txt", b"1"), ("b.txt", b"2")])
    real = dr._check_tar_structure
    monkeypatch.setattr(dr, "_check_tar_structure", lambda *a: tamper(list(real(*a))))
    with pytest.raises(CollectionError) as exc:
        extract_archive(archive, tmp_path / "out", SMALL)
    assert exc.value.code == "malformed_archive"
    assert not (tmp_path / "out").exists()


def test_prechecked_layout_matches_tarfile_for_supervisor_archives(tmp_path):
    names = ["a.txt", "résumé.txt", "d/" + "n" * 150 + ".txt", "e.bin"]
    archive = tar_bytes([(n, n.encode() * 3) for n in names])
    layout = dr._check_tar_structure(archive, Limits())
    assert [e.pax for e in layout] == [{}, {"path": names[1]}, {"path": names[2]}, {}]
    files = extract_archive(archive, tmp_path / "out", Limits())
    assert [f["path"] for f in files] == names


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
