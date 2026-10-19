# Demo fixture replies (NON-LIVE)

`revision.json` is a scripted list of model replies for the fixture agent demo (`--mode agent --fixture-script`). It is **NON-LIVE**: no model is called, and a run that uses it is never proof of live behavior. It is generated from `src/atlas/ui/scripts.py` (the UI's "revision" script) and has the same `name`/`replies` shape as the script written by the CLI Docker integration test (`tests/integration/test_agent_fixture_docker.py`).

`tests/unit/test_demo_fixture_file.py` checks that the file equals the generated script and holds no drive-letter or UNC path.

Regenerate (PowerShell quoting mangles `python -c`, so the generator is a short file; it was run once with `uv run --locked python gen.py` from the repository root):

```python
import json
from atlas.ui.scripts import BY_KEY

obj = {"name": "revision", "replies": BY_KEY["revision"].replies()}
with open("demo/fixtures/revision.json", "w", encoding="utf-8", newline="\n") as f:
    f.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
```
