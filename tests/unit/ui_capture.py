"""What an AppTest page shows, in document order, as comparable strings (readability pass).

Shared by tests/unit/test_ui_readability.py and tests/fixtures/ui_readability/capture.py, which
recorded the pre-pass baseline (`before.json`) from commit b690af2 with this same code, so a
test can compare today's output with what the page showed before the pass.
"""

import html
import re

TEXT = {"Markdown", "Caption", "Title", "Subheader", "Header", "Code", "Text"}
ALERT = {"Info", "Warning", "Error", "Success", "Exception"}
LABELLED = {"Button", "Toggle", "Selectbox", "Radio", "TextInput", "Checkbox"}


def items(node) -> list[str]:
    """Every element under `node`, in order: "<Type>:<value or label>"; expanders and
    popovers as "Expander:<label>" before their content; tables as CSV."""
    out = []
    for child in getattr(node, "children", {}).values():
        kind = type(child).__name__
        if kind in TEXT or kind in ALERT:
            out.append(f"{kind}:{child.value}")
        elif kind in LABELLED:
            out.append(f"{kind}:{child.label}")
        elif kind == "Table":
            out.append(f"Table:{child.value.to_csv()}")
        elif kind == "Expander":
            out.append(f"Expander:{child.label}")
        if getattr(child, "children", None):
            out += items(child)
    return out


def find(node, key: str):
    """The block or element with this user key (st-key-<key>), depth first."""
    for child in getattr(node, "children", {}).values():
        if getattr(child, "key", None) == key:
            return child
        found = find(child, key)
        if found is not None:
            return found
    return None


_TAG = re.compile(r"<[^>]+>")
_BADGE = re.compile(r":[a-z]+-badge\[")


def segments(item: str) -> list[str]:
    """The visible text pieces of one captured item: markup removed (each tag splits a
    piece), Markdown marks and escapes removed, whitespace collapsed."""
    body = item.split(":", 1)[1] if ":" in item else item
    if item.startswith("Table:"):
        return [" ".join(body.split())]
    body = _BADGE.sub("", body)
    out = []
    for piece in _TAG.split(body):
        piece = html.unescape(piece)
        piece = re.sub(r"\\(.)", r"\1", piece)
        piece = piece.replace("**", "")
        piece = re.sub(r"^\s*#{1,6}\s+", "", piece)
        piece = re.sub(r"^\s*-\s+", "", piece, flags=re.MULTILINE)
        piece = " ".join(piece.split()).strip(" ]")
        if piece:
            out.append(piece)
    return out
