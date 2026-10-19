"""Publication check for the hosted demo bundle (T-12 step 3). Read-only.

    uv run --locked python scripts/check_recorded.py [--root demo/recorded] [--json OUT]

Scans every bundled file and reports what it finds; it never rewrites a byte (that would
break the viewer's hash verification). The lead decides what to do with each finding.

Checks:
1. **Copy fidelity:** every file listed in BUNDLE.json is present with its recorded SHA-256,
   and no unlisted file is present (BUNDLE.json itself excepted).
2. **Viewer verification:** every bundled run is intact under `ui.recorded.verify`.
3. **Publication scan** of each file's text (binary files decoded leniently):
   - `host_path`: absolute host paths (Windows drive or UNC paths, `/home/<name>`,
     `/Users/<name>`, `/root/`, `/tmp/`);
   - `username`: the local account name and home-directory name, and the git user name;
   - `email`: e-mail-shaped strings;
   - `key_shaped`: strings shaped like credentials (`sk-...`, JWTs, bearer tokens, AWS and
     GitHub tokens, private-key headers, `key=`/`secret=`/`token=`/`password=` assignments,
     database URLs with a password). Their values are never printed, only the kind,
     file and line;
   - `env_reference`: references to `.env` files or the secret names (NEBIUS_API_KEY,
     DATABASE_URL, JUDGE_ACCESS_CODE, HOSTED_LIVE_ENABLED).

Exit 0 when the bundle is intact and nothing is found, 1 when anything is found, 2 when the
bundle is missing.
"""

import argparse
import getpass
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "demo" / "recorded"
MANIFEST = "BUNDLE.json"
EXCERPT = 100

HOST_PATH = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z]:(?:\\\\|\\|/)[^\s\"'<>|]*"  # C:\..., C:/..., C:\\... (JSON)
    r"|(?<![A-Za-z0-9\\])\\\\\\\\?[A-Za-z0-9._-]+\\\\?\\[^\s\"']*"  # \\server\share
    r"|/(?:home|Users)/[A-Za-z0-9._-]+[^\s\"']*"
    r"|/root/[^\s\"']*"
    r"|(?<![A-Za-z0-9._-])/tmp/[^\s\"']*"
)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
KEY_SHAPED = {
    "sk_token": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    "bearer": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[\"']?\s*[:=]\s*"
        r"[\"']?(?!null|none|true|false)[A-Za-z0-9._~+/=-]{8,}"
    ),
    "database_url": re.compile(
        r"\b(?:postgres(?:ql)?|mysql|mongodb)(?:\+\w+)?://[^\s:@/]+:[^\s@/]+@"
    ),
}
ENV_REFERENCE = re.compile(
    r"(?<![A-Za-z0-9_])\.env(?![A-Za-z0-9_])|\bdotenv\b"
    r"|\b(?:NEBIUS_API_KEY|DATABASE_URL|JUDGE_ACCESS_CODE|HOSTED_LIVE_ENABLED)\b"
)


def sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def local_names() -> list[str]:
    """The local account and home-directory names and the git user name (if any)."""
    names = {Path.home().name}
    for getter in (getpass.getuser, lambda: os.environ.get("USERNAME", "")):
        try:
            names.add(getter())
        except Exception:  # noqa: BLE001, S110
            pass
    try:
        out = subprocess.run(
            ["git", "config", "user.name"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        if out:
            names.add(out)
            names.update(p for p in out.split() if len(p) >= 3)
    except (OSError, subprocess.SubprocessError):
        pass
    return sorted(n for n in names if n and len(n) >= 3)


MASK = "<key-shaped>"


def _masked(line: str) -> str:
    """The line with every key-shaped value replaced, so no excerpt or match can carry one."""
    for pattern in KEY_SHAPED.values():
        line = pattern.sub(MASK, line)
    return line


def _excerpt(line: str, start: int, end: int) -> str:
    left = max(0, start - 20)
    return _masked(line[left : min(len(line), end + 20)])[:EXCERPT]


def scan_text(text: str, names: list[str]) -> list[dict]:
    """Findings in one file's text: kind, line and (except for key-shaped strings) an
    excerpt."""
    found = []
    name_patterns = [
        (
            n,
            re.compile(
                rf"(?<![A-Za-z0-9]){re.escape(n)}(?![A-Za-z0-9])", re.IGNORECASE
            ),
        )
        for n in names
    ]
    for number, raw in enumerate(text.splitlines(), start=1):
        for sub, pattern in KEY_SHAPED.items():
            for m in pattern.finditer(raw):
                found.append({"kind": "key_shaped", "subkind": sub, "line": number,
                              "column": m.start() + 1, "length": len(m.group(0))})  # fmt: skip
        # Every other detector sees the line with key-shaped values masked, so no excerpt
        # or match can carry one.
        line = _masked(raw)
        for m in HOST_PATH.finditer(line):
            found.append({"kind": "host_path", "line": number,
                          "excerpt": _excerpt(line, m.start(), m.end())})  # fmt: skip
        for name, pattern in name_patterns:
            for m in pattern.finditer(line):
                found.append({"kind": "username", "line": number, "match": name,
                              "excerpt": _excerpt(line, m.start(), m.end())})  # fmt: skip
        for m in EMAIL.finditer(line):
            found.append(
                {"kind": "email", "line": number, "match": _masked(m.group(0))}
            )
        for m in ENV_REFERENCE.finditer(line):
            found.append({"kind": "env_reference", "line": number,
                          "match": _masked(m.group(0)),
                          "excerpt": _excerpt(line, m.start(), m.end())})  # fmt: skip
    return found


def check(root: Path, names: list[str] | None = None) -> dict:
    root = Path(root)
    manifest_path = root / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    names = local_names() if names is None else names
    fidelity, listed = [], set()
    for run in manifest.get("runs", []):
        for rel, digest in (run.get("files") or {}).items():
            path = root / run["path"] / rel
            listed.add(path.resolve())
            if not path.is_file():
                fidelity.append({"file": f"{run['path']}/{rel}", "problem": "missing"})
            elif sha256(path) != digest:
                fidelity.append({"file": f"{run['path']}/{rel}", "problem": "changed"})
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.resolve() not in listed and path != manifest_path:
            fidelity.append(
                {"file": path.relative_to(root).as_posix(), "problem": "unlisted"}
            )

    sys.path.insert(0, str(ROOT / "src"))
    from atlas.ui import artifacts as A
    from atlas.ui import recorded as RR

    viewer = {}
    for run in manifest.get("runs", []):
        run_dir = root / run["path"]
        checks = RR.verify(run_dir, A.read_json(run_dir / "agent_report.json"))
        viewer[run["path"]] = {
            "intact": bool(checks) and RR.intact(checks),
            "items": len(checks),
            "changed": [c.item for c in checks if not c.ok],
        }

    findings = defaultdict(list)
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        text = path.read_bytes().decode("utf-8", "replace")
        for f in scan_text(text, names):
            findings[path.relative_to(root).as_posix()].append(f)
    counts = Counter(f["kind"] for fs in findings.values() for f in fs)
    return {
        "root": str(root),
        "fidelity_problems": fidelity,
        "viewer": viewer,
        "counts": dict(sorted(counts.items())),
        "files_with_findings": len(findings),
        "findings": dict(findings),
        "names_checked": len(names),
    }


def summary(result: dict) -> list[str]:
    lines = [f"Bundle {result['root']}"]
    lines.append(
        f"Copy fidelity: {len(result['fidelity_problems'])} problem(s)"
        + "".join(
            f"\n  {p['problem']}: {p['file']}" for p in result["fidelity_problems"]
        )
    )
    for run, v in result["viewer"].items():
        state = "intact" if v["intact"] else f"CHANGED {v['changed'][:5]}"
        lines.append(f"Viewer: {run}: {state} ({v['items']} items)")
    lines.append(f"Findings by kind: {result['counts'] or 'none'}")
    by_kind_file = defaultdict(Counter)
    for file, fs in result["findings"].items():
        for f in fs:
            by_kind_file[f["kind"]][file] += 1
    for kind in sorted(by_kind_file):
        lines.append(f"{kind}:")
        for file, n in sorted(by_kind_file[kind].items()):
            first = next(f for f in result["findings"][file] if f["kind"] == kind)
            detail = (
                f"{first.get('subkind')} at line {first['line']} (value not shown)"
                if kind == "key_shaped"
                else f"line {first['line']}: {first.get('excerpt') or first.get('match')}"
            )
            lines.append(f"  {file}: {n} (first: {detail})")
    return lines


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="check_recorded")
    p.add_argument("--root", type=Path, default=DEFAULT_BUNDLE)
    p.add_argument("--json", type=Path, help="also write the full findings as JSON")
    args = p.parse_args(argv)
    if not (args.root / MANIFEST).is_file():
        print(f"No {MANIFEST} under {args.root}", file=sys.stderr)
        return 2
    result = check(args.root)
    print("\n".join(summary(result)))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
        )
    clean = (
        not result["fidelity_problems"]
        and all(v["intact"] for v in result["viewer"].values())
        and not result["counts"]
    )
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
