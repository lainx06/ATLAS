"""The fixed, generic ATLAS adapter reference in the model's context (T-06 slice 4f).

Derived from the source of `atlas.adapter` itself, so it cannot drift from the code a candidate
runs against: each public function, in the module's order, with its signature and the first
line of its docstring as its contract, plus the row-selection rule. It names no project, file,
column or benchmark and is identical for every run. It is trusted, read-only context written by
ATLAS, not model or project text. Rendered as text (`TEXT`), it ends the system prompt, so the
user-message budget, which is derived from the system prompt, already accounts for it.
"""

import ast
from pathlib import Path

from atlas import adapter

# Public names the runner uses to install the recorder around a run; project code never calls
# them (an adapter session is already active while the entry point runs).
HARNESS_ONLY = ("session",)
TAKE_RULE = (
    "Row selection must go through adapter.take(obj, row_ids): select the rows of the X and y "
    "returned by load_table only with it (not with .loc, .iloc, boolean masks or other "
    "indexing), so each subset keeps its connection to the source rows."
)


def build() -> dict:
    tree = ast.parse(Path(adapter.__file__).read_text(encoding="utf-8"))
    functions = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
            continue
        if node.name in HARNESS_ONLY:
            continue
        signature = f"adapter.{node.name}({ast.unparse(node.args)})"
        if node.returns is not None:
            signature += f" -> {ast.unparse(node.returns)}"
        doc = ast.get_docstring(node) or ""
        functions.append(
            {
                "name": node.name,
                "signature": signature,
                "contract": doc.splitlines()[0] if doc else "",
            }
        )
    return {
        "title": "ATLAS adapter reference (fixed; identical for every project)",
        "import": "from atlas import adapter",
        "functions": functions,
        "rule": TAKE_RULE,
    }


def render(reference: dict) -> str:
    """The reference as the text appended to the system prompt."""
    lines = [f"{reference['title']}. Project code uses `{reference['import']}`:"]
    lines += [f"- {f['signature']}: {f['contract']}" for f in reference["functions"]]
    lines.append(f"Rule: {reference['rule']}")
    return "\n".join(lines)


REFERENCE = build()
TEXT = render(REFERENCE)
