"""Fixtures for the hosted-mode tests (T-12): a disposable local PostgreSQL, like stage D.

The database tests need Docker: one `postgres:17-alpine` container per test session, with a
loopback-only port, throwaway credentials, no mounts, bounded memory and PIDs, removed at the
end. Each test gets its own fresh database in it. With ATLAS_REQUIRE_DOCKER=1 an unavailable
Docker fails these tests instead of skipping them. Nothing here reaches Neon or Nebius.
"""

import os
import secrets
import shutil
import subprocess
import time

import pytest

IMAGE = "postgres:17-alpine"
REQUIRE_DOCKER = os.environ.get("ATLAS_REQUIRE_DOCKER") == "1"


def _docker(*args, check=True, timeout=120):
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=check, timeout=timeout
    )


def _unavailable(message: str):
    if REQUIRE_DOCKER:
        pytest.fail(message)
    pytest.skip(message)


@pytest.fixture(scope="session")
def postgres_server():
    """(host, port, user, password) of a disposable PostgreSQL server."""
    if shutil.which("docker") is None:
        _unavailable("docker CLI not found")
    try:
        _docker("info", "--format", "{{.ServerVersion}}", timeout=30)
    except (subprocess.SubprocessError, OSError) as exc:
        _unavailable(f"Docker unavailable: {type(exc).__name__}")
    if _docker("image", "inspect", IMAGE, check=False).returncode != 0:
        _unavailable(f"{IMAGE} is not present locally (docker pull {IMAGE})")
    name = f"atlas-t12-pg-{secrets.token_hex(4)}"
    password = secrets.token_hex(16)
    _docker(
        "run", "-d", "--rm", "--name", name,
        "-e", "POSTGRES_USER=atlas_test", "-e", f"POSTGRES_PASSWORD={password}",
        "-e", "POSTGRES_DB=atlas_test",
        "-p", "127.0.0.1::5432", "--memory", "512m", "--pids-limit", "256",
        IMAGE,
    )  # fmt: skip
    try:
        port = int(_docker("port", name, "5432/tcp").stdout.strip().rsplit(":", 1)[1])
        import psycopg

        deadline = time.time() + 90
        while True:
            try:
                psycopg.connect(
                    host="127.0.0.1", port=port, user="atlas_test", password=password,
                    dbname="atlas_test", connect_timeout=3,
                ).close()  # fmt: skip
                break
            except psycopg.OperationalError:
                if time.time() > deadline:
                    raise
                time.sleep(0.5)
        yield ("127.0.0.1", port, "atlas_test", password)
    finally:
        _docker("rm", "-f", name, check=False)


@pytest.fixture
def database_url(postgres_server):
    """A fresh, empty database for one test; dropped afterwards."""
    import psycopg

    host, port, user, password = postgres_server
    dbname = f"t_{secrets.token_hex(6)}"
    admin = f"postgresql://{user}:{password}@{host}:{port}/atlas_test"
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{dbname}"')
    yield f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)')
