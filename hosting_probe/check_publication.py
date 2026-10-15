"""Inspect the exact publication set for the stage A probe repository (local, read-only).

Checks that the set is exactly two files, that they contain no ATLAS source, personal
documentation, credentials or Nebius reference, and that the app imports no network modules.
Prints sizes and SHA-256 so the files copied into the new repository can be compared.
Run: uv run --locked python hosting_probe/check_publication.py
"""

import ast
import hashlib
import re
import sys
from pathlib import Path

SET = Path(__file__).with_name("stage_a")
EXPECTED = {"app.py", "requirements.txt"}
NETWORK_MODULES = {
    "urllib", "http", "socket", "requests", "httpx", "openai", "aiohttp", "ftplib",
    "smtplib", "websocket", "websockets", "ssl", "atlas", "dotenv",
}  # fmt: skip
FORBIDDEN_TEXT = [
    (re.compile(r"nebius", re.IGNORECASE), "Nebius reference"),
    (
        re.compile(r"api[_-]?key|token factory|bearer", re.IGNORECASE),
        "credential wording",
    ),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"), "key-shaped string"),
    (re.compile(r"[A-Za-z]:\\?Users", re.IGNORECASE), "local Windows path"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "email address"),
    (
        re.compile(r"adnan|lainx06|handoff|playbook", re.IGNORECASE),
        "personal or project document name",
    ),
    (re.compile(r"\.env\b"), ".env reference"),
]


def problems() -> list[str]:
    found = []
    files = {p.name for p in SET.iterdir() if p.is_file()}
    subdirs = [p.name for p in SET.iterdir() if p.is_dir() and p.name != "__pycache__"]
    if files != EXPECTED or subdirs:
        found.append(
            f"publication set is {sorted(files)} + dirs {subdirs}, expected {sorted(EXPECTED)}"
        )
    for name in sorted(files & EXPECTED):
        text = (SET / name).read_text(encoding="utf-8")
        for pattern, label in FORBIDDEN_TEXT:
            if pattern.search(text):
                found.append(f"{name}: {label}")
    tree = ast.parse((SET / "app.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        for n in names:
            if n.split(".")[0] in NETWORK_MODULES:
                found.append(f"app.py imports {n}")
    requirements = (SET / "requirements.txt").read_text(encoding="utf-8").split()
    if requirements != ["streamlit"]:
        found.append(f"requirements.txt is {requirements}, expected ['streamlit']")
    return found


if __name__ == "__main__":
    for name in sorted(EXPECTED):
        data = (SET / name).read_bytes()
        print(f"{name}: {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()}")
    issues = problems()
    print("problems:", issues or "none")
    sys.exit(1 if issues else 0)
