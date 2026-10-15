"""Inspect an exact publication set for the probe repository (local, read-only).

Checks that the set is exactly the expected files, that they contain no ATLAS source, personal
documentation, credentials, provider-key wording or connection string, and that no file imports a
network module other than the one database driver a set explicitly allows.
Prints sizes and SHA-256 so the files copied into the repository can be compared.
Run: uv run --locked python hosting_probe/check_publication.py [stage_a|stage_d]
"""

import ast
import hashlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
# name -> (directory, exact file names, exact requirements.txt words, allowed driver imports)
SETS = {
    "stage_a": (HERE / "stage_a", {"app.py", "requirements.txt"}, ["streamlit"], set()),
    "stage_d": (
        HERE / "stage_d",
        {"app.py", "budget_probe.py", "requirements.txt"},
        ["streamlit", "psycopg[binary]"],
        {"psycopg"},
    ),
}
NETWORK_MODULES = {
    "urllib", "http", "socket", "requests", "httpx", "openai", "aiohttp", "ftplib",
    "smtplib", "websocket", "websockets", "ssl", "atlas", "dotenv", "psycopg",
    "psycopg2", "asyncpg", "sqlalchemy", "pg8000",
}  # fmt: skip
FORBIDDEN_TEXT = [
    (re.compile(r"nebius", re.IGNORECASE), "provider reference"),
    (
        re.compile(r"api[_-]?key|token factory|bearer", re.IGNORECASE),
        "credential wording",
    ),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"), "key-shaped string"),
    (re.compile(r"postgres(ql)?://", re.IGNORECASE), "connection string"),
    (re.compile(r"[A-Za-z]:\\?Users", re.IGNORECASE), "local Windows path"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "email address"),
    (
        re.compile(r"adnan|lainx06|handoff|playbook", re.IGNORECASE),
        "personal or project document name",
    ),
    (re.compile(r"\.env\b"), ".env reference"),
]


def problems(name: str = "stage_a") -> list[str]:
    directory, expected, requirements, allowed = SETS[name]
    found = []
    files = {p.name for p in directory.iterdir() if p.is_file()}
    subdirs = [
        p.name for p in directory.iterdir() if p.is_dir() and p.name != "__pycache__"
    ]
    if files != expected or subdirs:
        found.append(
            f"{name} is {sorted(files)} + dirs {subdirs}, expected {sorted(expected)}"
        )
    for file in sorted(files & expected):
        text = (directory / file).read_text(encoding="utf-8")
        for pattern, label in FORBIDDEN_TEXT:
            if pattern.search(text):
                found.append(f"{file}: {label}")
        if file.endswith(".py"):
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, ast.Import):
                    modules = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [node.module or ""]
                else:
                    continue
                for module in modules:
                    root = module.split(".")[0]
                    if root in NETWORK_MODULES and root not in allowed:
                        found.append(f"{file} imports {module}")
    words = (directory / "requirements.txt").read_text(encoding="utf-8").split()
    if words != requirements:
        found.append(f"requirements.txt is {words}, expected {requirements}")
    return found


if __name__ == "__main__":
    selected = sys.argv[1:] or list(SETS)
    bad = False
    for name in selected:
        directory, expected, _, _ = SETS[name]
        print(f"[{name}]")
        for file in sorted(expected):
            data = (directory / file).read_bytes()
            print(
                f"  {file}: {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()}"
            )
        issues = problems(name)
        print("  problems:", issues or "none")
        bad = bad or bool(issues)
    sys.exit(1 if bad else 0)
