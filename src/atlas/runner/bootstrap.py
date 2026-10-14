"""Child-process entry: install the recorder, run a trusted fixture's entry point, write evidence.

Started only by atlas.runner.trusted (isolated mode, after the inventory allowlist check).
"""

import json
import runpy
import sys
from pathlib import Path

import atlas
from atlas import adapter
from atlas.contracts import Manifest
from atlas.intake import MANIFEST_NAME, read_table


def _runtime_record(project: Path) -> dict:
    """Where imports resolve from in this child: evidence for the import-control rule."""
    resolved = {str(Path(p).resolve()) for p in sys.path if p}
    return {
        "atlas_origin": str(Path(atlas.__file__).resolve()),
        "isolated": sys.flags.isolated,
        "safe_path": bool(sys.flags.safe_path),
        "project_dir_on_sys_path": str(project.resolve()) in resolved,
        "cwd_on_sys_path": "" in sys.path or str(Path.cwd().resolve()) in resolved,
        "python": sys.version.split()[0],
    }


def main(project: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "runtime.json").write_text(
        json.dumps(_runtime_record(project), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = Manifest.model_validate_json(
        (project / MANIFEST_NAME).read_text(encoding="utf-8")
    )
    table = read_table(project, manifest)
    with adapter.session(manifest.model_dump(), table, out_dir):
        runpy.run_path(str(project / manifest.entry_point), run_name="__main__")
