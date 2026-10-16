"""Model reply schemas: exactly one bounded action, validated over the whole reply (SPEC §11).

A reply is the model's entire message content, with only surrounding whitespace removed, and
must be one JSON object `{"action": {...}}` holding exactly one action from the allowed set.
There is no extraction from prose, no Markdown fence stripping and no repair: anything else is
a schema failure, which authorizes no action (DECISIONS.md "Initial model and response
approach"; T-06 dispositions: no format-repair retry).

The schemas are strict (no type coercion), forbid unknown fields at every level, bound every
string and reject duplicate JSON keys, so a reply cannot smuggle a second action, an approval,
an assertion list or an outcome. No action can approve a candidate, change the required
assertion set or declare a scientific result: `finish` carries only model-written text, which
reports label as such.
"""

import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from atlas.candidates import MAX_DIFF_BYTES

MAX_REPLY_BYTES = 128 * 1024  # a 64 KiB diff plus JSON escaping
MAX_PATH_CHARS = 200
MAX_TEXT_CHARS = 4000
CHECKS = (
    "split_integrity",
    "fit_provenance",
    "independent_metrics",
    "temporal_availability",
)


class _Action(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ListProjectFiles(_Action):
    tool: Literal["list_project_files"]


class ReadProjectFile(_Action):
    tool: Literal["read_project_file"]
    path: str = Field(min_length=1, max_length=MAX_PATH_CHARS)


class InspectEvidence(_Action):
    tool: Literal["inspect_evidence"]
    check: Literal[CHECKS]


class ProposePatch(_Action):
    tool: Literal["propose_patch"]
    diff: str = Field(min_length=1, max_length=MAX_DIFF_BYTES)
    rationale: str = Field(max_length=MAX_TEXT_CHARS)

    @field_validator("diff")
    @classmethod
    def _diff_bytes(cls, value: str) -> str:
        """The diff limit is in UTF-8 bytes, as `validate_diff` measures it (max_length above
        counts characters, which multibyte text could exceed in bytes)."""
        try:
            size = len(value.encode("utf-8"))
        except UnicodeEncodeError:
            raise ValueError("diff is not encodable as UTF-8") from None
        if size > MAX_DIFF_BYTES:
            raise ValueError(
                f"diff is {size} UTF-8 bytes; the limit is {MAX_DIFF_BYTES}"
            )
        return value


class Finish(_Action):
    tool: Literal["finish"]
    summary: str = Field(max_length=MAX_TEXT_CHARS)


Action = Annotated[
    ListProjectFiles | ReadProjectFile | InspectEvidence | ProposePatch | Finish,
    Field(discriminator="tool"),
]
TOOL_NAMES = (
    "list_project_files",
    "read_project_file",
    "inspect_evidence",
    "propose_patch",
)


class Reply(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Action


class ReplyRejected(ValueError):
    """The reply is not one valid action; `code` names the first problem found."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def _no_duplicate_keys(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ReplyRejected("duplicate_key", f"repeated key in {sorted(set(keys))[:5]}")
    return dict(pairs)


def parse_reply(content) -> Reply:
    """Validate a whole reply. Raises ReplyRejected; never returns a partial action."""
    if not isinstance(content, str):
        raise ReplyRejected("missing_content", type(content).__name__)
    if len(content.encode("utf-8", "surrogatepass")) > MAX_REPLY_BYTES:
        raise ReplyRejected("too_large", f"over {MAX_REPLY_BYTES} bytes")
    text = content.strip()
    if not text:
        raise ReplyRejected("empty")
    try:
        data = json.loads(text, object_pairs_hook=_no_duplicate_keys)
    except ReplyRejected:
        raise
    except (ValueError, RecursionError) as exc:
        raise ReplyRejected("not_json", type(exc).__name__) from None
    if not isinstance(data, dict):
        raise ReplyRejected("not_an_object", type(data).__name__)
    try:
        return Reply.model_validate(data)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first.get("loc", ()))
        raise ReplyRejected("schema", f"{where}: {first.get('type')}") from None


def schema_text() -> str:
    """The reply contract as shown to the model (also logged by hash)."""
    return json.dumps(Reply.model_json_schema(), sort_keys=True)
