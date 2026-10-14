"""Child-process entry: install the recorder, run a trusted fixture's entry point, write evidence.

Invoked only by atlas.runner.trusted after the allowlist check.
"""

import runpy
import sys
from pathlib import Path

from atlas import adapter
from atlas.contracts import Manifest
from atlas.intake import MANIFEST_NAME, read_table


def main(project: Path, out_dir: Path) -> None:
    manifest = Manifest.model_validate_json(
        (project / MANIFEST_NAME).read_text(encoding="utf-8")
    )
    table = read_table(project, manifest)
    with adapter.session(manifest.model_dump(), table, out_dir):
        runpy.run_path(str(project / manifest.entry_point), run_name="__main__")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
