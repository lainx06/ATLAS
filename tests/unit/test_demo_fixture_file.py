"""The committed demo fixture script equals the UI's "revision" script (NON-LIVE) and holds no host path."""

import json
import re
from pathlib import Path

from atlas.ui.scripts import BY_KEY

FIXTURE = Path(__file__).resolve().parents[2] / "demo" / "fixtures" / "revision.json"


def test_the_demo_fixture_equals_the_ui_revision_script():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data == {"name": "revision", "replies": BY_KEY["revision"].replies()}


def test_the_demo_fixture_holds_no_drive_or_unc_path():
    text = json.dumps(
        json.loads(FIXTURE.read_text(encoding="utf-8")), ensure_ascii=False
    )
    decoded = json.loads(FIXTURE.read_text(encoding="utf-8"))
    strings = []

    def walk(v):
        if isinstance(v, str):
            strings.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(decoded)
    assert text and strings
    for value in strings:
        assert not re.search(r"[A-Za-z]:\\", value)
        assert not re.search(r"\\\\", value)
