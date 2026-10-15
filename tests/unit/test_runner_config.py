"""Docker runner configuration: CLI resolution, flags, build context, dependency set and the
mounted-code import closure. Offline (no Docker needed)."""

import ast
import os
import re
import sys
import tomllib
from pathlib import Path

import pytest

from atlas.runner import docker as dr

ROOT = Path(__file__).resolve().parents[2]
EXE = "docker.exe" if os.name == "nt" else "docker"
# Imported-name -> distribution for the third-party imports the mounted code may use.
IMPORT_TO_DIST = {"numpy": "numpy", "pandas": "pandas", "sklearn": "scikit-learn"}


def fake_cli(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    exe = directory / EXE
    exe.write_bytes(b"")
    return exe


# --- CLI resolution ------------------------------------------------------------------------


def test_cli_from_absolute_path_entry(tmp_path):
    exe = fake_cli(tmp_path / "bin")
    assert dr.resolve_docker_cli({"PATH": str(tmp_path / "bin")}) == exe.resolve()


def test_relative_path_entries_and_cwd_are_never_searched(tmp_path, monkeypatch):
    fake_cli(tmp_path / "rel")
    fake_cli(tmp_path)
    monkeypatch.chdir(tmp_path)
    env = {"PATH": os.pathsep.join(["rel", ".", ""])}
    assert dr.resolve_docker_cli(env) is None


def test_excluded_candidate_directories_are_skipped(tmp_path):
    candidate_bin = fake_cli(tmp_path / "candidate" / "bin").parent
    real = fake_cli(tmp_path / "real")
    env = {"PATH": os.pathsep.join([str(candidate_bin), str(real.parent)])}
    resolved = dr.resolve_docker_cli(env, exclude=[tmp_path / "candidate"])
    assert resolved == real.resolve()


def test_known_per_user_location_is_used_when_path_lacks_docker(tmp_path):
    exe = fake_cli(tmp_path / "Programs" / "DockerDesktop" / "resources" / "bin")
    env = {"PATH": "", "LOCALAPPDATA": str(tmp_path)}
    assert dr.resolve_docker_cli(env) == exe.resolve()


def test_cli_env_drops_secret_names_and_prefers_cli_dir(tmp_path):
    exe = fake_cli(tmp_path / "bin")
    env = {
        "PATH": "/usr/bin",
        "NEBIUS_API_KEY": "k",
        "GITHUB_TOKEN": "t",
        "DB_PASSWORD": "p",
        "MY_SECRET": "s",
        "DOCKER_HOST": "npipe:////./pipe/docker_engine",
    }
    out = dr.cli_env(exe, env)
    assert set(out) == {"PATH", "DOCKER_HOST"}
    assert out["PATH"].split(os.pathsep)[0] == str(exe.parent)


# --- container flags -----------------------------------------------------------------------


def test_run_arguments_enforce_the_policy(tmp_path):
    limits = dr.Limits()
    args = dr.docker_run_args(
        "atlas-t05-x", "run1", tmp_path / "p", tmp_path / "c", "sha256:abc", limits
    )
    joined = " ".join(args)
    pairs = {(args[i], args[i + 1]) for i in range(len(args) - 1)}
    for pair in [
        ("--network", "none"),
        ("--user", "10001:10001"),
        ("--cap-drop", "ALL"),
        ("--security-opt", "no-new-privileges=true"),
        ("--memory", str(1 << 30)),
        ("--memory-swap", str(1 << 30)),
        ("--cpus", "1"),
        ("--pids-limit", "128"),
        ("--ipc", "none"),
        ("--pull", "never"),
    ]:
        assert pair in pairs, pair
    assert "--read-only" in args
    assert f"/tmp:rw,noexec,nosuid,nodev,size={64 << 20},mode=1777" in args
    assert f"/work/out:rw,noexec,nosuid,nodev,size={32 << 20},mode=1777" in args
    mounts = [args[i + 1] for i, a in enumerate(args) if a == "--mount"]
    assert len(mounts) == 2
    assert all(m.endswith(",readonly") and m.startswith("type=bind,") for m in mounts)
    for forbidden in ("--privileged", "-e", "--env", "--env-file", "docker.sock", "-v"):
        assert forbidden not in args
    assert "docker.sock" not in joined and "--cap-add" not in joined
    image_index = args.index("sha256:abc")
    assert args[image_index + 1 :][:4] == [
        "-I",
        "-B",
        "/opt/atlas/atlas_runner_entry.py",
        "supervise",
    ]
    assert args[-3:] == ["30.0", "256", str(32 << 20)]


def test_default_limits_match_the_decided_values():
    lim = dr.Limits()
    assert (lim.memory_bytes, lim.cpus, lim.pids, lim.exec_timeout_s) == (
        1 << 30,
        "1",
        128,
        30.0,
    )
    assert (lim.scratch_bytes, lim.output_bytes) == (64 << 20, 32 << 20)
    assert lim.deadline_s > lim.exec_timeout_s


# --- build context and image recipe ----------------------------------------------------------


def test_build_context_is_the_allowlist_only(tmp_path):
    files = dr.write_build_context(tmp_path / "ctx")
    assert files == ["Dockerfile", "runner-requirements.txt"]
    for path in (tmp_path / "ctx").iterdir():
        assert b"NEBIUS" not in path.read_bytes()
        assert b"\r\n" not in path.read_bytes()


def test_dockerfile_pins_the_base_by_digest_and_runs_non_root():
    text = (ROOT / "Dockerfile.runner").read_text(encoding="utf-8")
    froms = [ln for ln in text.splitlines() if ln.startswith("FROM ")]
    assert len(froms) == 1 and re.search(r"@sha256:[0-9a-f]{64}$", froms[0])
    assert "USER 10001:10001" in text
    assert "--require-hashes" in text and "--no-deps" in text
    copies = [ln for ln in text.splitlines() if ln.startswith(("COPY", "ADD"))]
    assert copies == ["COPY runner-requirements.txt /tmp/runner-requirements.txt"]


def test_recipe_hash_covers_both_context_files():
    assert re.fullmatch(r"[0-9a-f]{64}", dr.recipe_sha256())


# --- dependency set --------------------------------------------------------------------------


def _pins() -> dict[str, str]:
    text = (ROOT / "docker" / "runner-requirements.txt").read_text(encoding="utf-8")
    pins = dict(re.findall(r"^([a-z0-9_.-]+)==([^\s\\]+)", text, flags=re.MULTILINE))
    blocks = re.split(r"^(?=[a-z0-9_.-]+==)", text, flags=re.MULTILINE)[1:]
    assert all("--hash=sha256:" in b for b in blocks), "every pin must carry hashes"
    return pins


def _locked() -> dict[str, list[str]]:
    data = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for pkg in data["package"]:
        out.setdefault(pkg["name"], []).append(pkg["version"])
    return out


def test_runner_pins_match_uv_lock():
    locked = _locked()
    for name, version in _pins().items():
        assert version in locked.get(name, []), f"{name}=={version} not in uv.lock"


def test_runner_set_includes_parquet_engine_and_transitive_dependencies():
    pins = _pins()
    # pyarrow: DataFrame.to_parquet in adapter.write_predictions; narwhals, scipy, joblib
    # (and its cloudpickle), threadpoolctl: scikit-learn; python-dateutil and six: pandas.
    for name in (
        "numpy",
        "pandas",
        "scikit-learn",
        "pyarrow",
        "scipy",
        "joblib",
        "cloudpickle",
        "threadpoolctl",
        "narwhals",
        "python-dateutil",
        "six",
    ):
        assert name in pins, name
    for absent in ("openai", "python-dotenv", "streamlit", "pydantic", "httpx"):
        assert absent not in pins


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
            names |= {f"{node.module}.{a.name}" for a in node.names}
    return names


def test_mounted_code_imports_only_mounted_modules_and_pinned_packages():
    pins = _pins()
    mounted = {f"atlas.{n[:-3]}" for n in dr.MOUNTED_MODULES if n != "__init__.py"}
    files = [dr.PACKAGE_DIR / n for n in dr.MOUNTED_MODULES] + [dr.ENTRY_SOURCE]
    for path in files:
        for name in _imports(path):
            top = name.split(".")[0]
            if top == "atlas":
                module = ".".join(name.split(".")[:2])
                assert name == "atlas" or module in mounted, (
                    f"{path.name} imports {name}"
                )
            elif top in sys.stdlib_module_names:
                continue
            else:
                assert IMPORT_TO_DIST.get(top) in pins, f"{path.name} imports {name}"


def test_policy_and_evaluator_code_is_not_mounted(tmp_path):
    inventory = dr.stage_code(tmp_path / "code")
    paths = sorted(rel for rel, _ in inventory)
    assert paths == [
        "atlas/__init__.py",
        "atlas/adapter.py",
        "atlas/recorder.py",
        "atlas/reports.py",
        "atlas/tables.py",
        "atlas_runner_entry.py",
    ]
    for forbidden in ("policy", "audit", "contracts", "intake", "checks", "candidates"):
        assert not any(forbidden in p for p in paths)


def test_docker_runner_never_imports_the_host_runner():
    names = _imports(Path(dr.__file__))
    assert not any(
        n.startswith(("atlas.runner.trusted", "atlas.runner.bootstrap")) for n in names
    )
    assert "runpy" not in names


@pytest.mark.parametrize("module", ["adapter.py", "recorder.py", "tables.py"])
def test_mounted_modules_do_not_import_pydantic_or_policy(module):
    names = _imports(dr.PACKAGE_DIR / module)
    assert not any(n.split(".")[0] == "pydantic" for n in names)
    assert not any(
        n.startswith(("atlas.policy", "atlas.contracts", "atlas.intake")) for n in names
    )
