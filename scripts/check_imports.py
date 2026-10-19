"""Environment import check: proves the locked dependencies import; not a product test.

Run: uv run --locked python scripts/check_imports.py
"""

import importlib
import importlib.metadata as md
import sys

# (import name, distribution name)
PAIRS = [
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("sklearn", "scikit-learn"),
    ("pydantic", "pydantic"),
    ("streamlit", "streamlit"),
    ("openai", "openai"),
    ("dotenv", "python-dotenv"),
    ("psycopg", "psycopg"),
    ("pytest", "pytest"),
    ("atlas", "atlas"),
]


def main() -> int:
    print("python", sys.version.split()[0], sys.executable)
    failed = 0
    for mod, dist in PAIRS:
        try:
            importlib.import_module(mod)
            print(f"OK   {mod:10s} {md.version(dist)}")
        except (ImportError, md.PackageNotFoundError) as exc:  # report every failure
            failed += 1
            print(f"FAIL {mod:10s} {type(exc).__name__}: {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
