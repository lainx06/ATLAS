"""Human approval at the terminal (SPEC §9.5; T-06 lead disposition; slice 3).

Before the original project code or a candidate runs, the person at the terminal sees what will
run and must type the **first 12 hexadecimal characters** of its hash. The approval records the
**full** hash and the snapshot hash it is bound to. Anything else declines.

- **No terminal** (stdin is not interactive) or end of input: `ApprovalUnavailable`, which the
  controller turns into NEEDS_INPUT with nothing executed.
- **Untrusted text is shown inert.** The diff and the model's rationale are model-written. Before
  printing, every control character other than newline (escape sequences, carriage returns,
  backspaces, bidirectional overrides) is replaced by a visible `\\x..` / `\\u....` escape, so
  the text cannot move the cursor, hide lines or recolor the prompt.
- The confirmation compares the typed text, stripped of surrounding whitespace and lowercased,
  with the first 12 characters of the hash. One attempt per request; a mismatch declines.
"""

import sys
import unicodedata
from datetime import UTC, datetime

from atlas.candidates import Approval

CONFIRM_CHARS = 12


class ApprovalUnavailable(Exception):
    """No approver can be asked (no terminal, or input closed): the run needs input."""


def inert(text: str) -> str:
    """Text safe to print on a terminal: control and format characters become visible escapes."""
    out = []
    for ch in text:
        if ch == "\n":
            out.append(ch)
        elif ch == "\t":
            out.append("    ")
        elif unicodedata.category(ch) in ("Cc", "Cf", "Cs", "Co", "Cn") or ch in "  ":
            code = ord(ch)
            out.append(f"\\x{code:02x}" if code < 0x100 else f"\\u{code:04x}")
        else:
            out.append(ch)
    return "".join(out)


class TerminalApprover:
    """Approves one exact request after the typed confirmation; `last_reason` says why not."""

    def __init__(self, stdin=None, stdout=None, now=None):
        self.stdin = stdin if stdin is not None else sys.stdin
        self.stdout = stdout if stdout is not None else sys.stdout
        self.now = now or (lambda: datetime.now(UTC).isoformat())
        self.last_reason: str | None = None

    def _write(self, text: str) -> None:
        self.stdout.write(text)
        self.stdout.flush()

    def decide(self, request):
        self.last_reason = None
        isatty = getattr(self.stdin, "isatty", None)
        if not callable(isatty) or not isatty():
            self.last_reason = "no_terminal"
            raise ApprovalUnavailable("no interactive terminal to approve on")
        kind = getattr(request, "kind", "candidate")
        lines = ["", "=" * 72]
        if kind == "original":
            lines.append("APPROVAL REQUIRED: run the ORIGINAL, unmodified project code")
            lines.append("in the isolated Docker runner.")
        else:
            lines.append(
                "APPROVAL REQUIRED: run this CANDIDATE revision in the isolated Docker runner."
            )
        lines += [
            f"Entry point:    {inert(request.entry_point)}",
            f"Snapshot hash:  {request.base_snapshot_hash}",
            f"Code hash:      {request.candidate_hash}",
        ]
        if kind != "original":
            lines += [
                "Model-written rationale (untrusted):",
                inert(request.model_rationale or "(none)"),
                "Proposed diff (untrusted; control characters shown as escapes):",
                inert(request.diff),
            ]
        lines += [
            "=" * 72,
            (
                f"Type the first {CONFIRM_CHARS} characters of the code hash to approve; "
                "anything else declines: "
            ),
        ]
        self._write("\n".join(lines))
        line = self.stdin.readline()
        if line == "":
            self.last_reason = "input_closed"
            raise ApprovalUnavailable("input closed before a confirmation was typed")
        typed = line.strip().lower()
        if typed != request.candidate_hash[:CONFIRM_CHARS]:
            self.last_reason = "confirmation_mismatch"
            self._write("Confirmation did not match: NOT approved.\n")
            return None
        self.last_reason = "confirmed"
        self._write("Approved.\n")
        return Approval(request.candidate_hash, request.base_snapshot_hash, self.now())
