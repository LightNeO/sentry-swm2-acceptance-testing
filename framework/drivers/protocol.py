"""Parses SWM-2 console output. No I/O here, so it's unit-testable without hardware.

Lines look like ``I (205039) sentry: [VALVE] OPEN (command)`` - level/tick/tag/msg.
Background logs can get glued into a command's echo (``reI (205039) sentry: ...``), so the
regex searches inside the line instead of anchoring at the start.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
LOG_RE = re.compile(r"([IWE]) \((\d+)\) ([\w.]+): (.*)")
CODE_RE = re.compile(r"\b([EW]\d{3})\b")
# Background telemetry the PRD declares informational (not bugs). Filtered on request.
NOISE_PREFIXES = ("[NAV]", "[ACU]", "[PWR]", "[HW]")
BOOT_READY_RE = re.compile(r"ready\. state 1 NORMAL")
VERSION_RE = re.compile(r"fw v(\d+\.\d+\.\d+)")


class ErrorCode(str, Enum):
    """Console error/warning codes the tests check for (the full list is in docs/requirements.md).

    Members are plain strings, so ``resp.has_code(ErrorCode.E808)`` and ``resp.has_code("E808")`` are the same call."""

    W510 = "W510"  # lamp already on/off
    E509 = "E509"  # lamp scene is empty
    W605 = "W605"  # relay schedule is not running
    E602 = "E602"  # relay switch rate limit
    W801 = "W801"  # guard already arming
    W802 = "W802"  # guard not armed
    E803 = "E803"  # wrong guard PIN
    E804 = "E804"  # bad PIN format
    E805 = "E805"  # no sonar reading to arm on
    E807 = "E807"  # PIN change while armed
    E808 = "E808"  # guard zone out of range


@dataclass(frozen=True)
class LogLine:
    """One console line, split into fields if it's a firmware log line."""

    raw: str
    level: str | None = None
    tick: int | None = None
    tag: str | None = None
    msg: str = ""
    codes: tuple[str, ...] = ()

    @property
    def is_noise(self) -> bool:
        return self.msg.startswith(NOISE_PREFIXES)


def parse_line(raw: str) -> LogLine:
    """Parse one cleaned line. Non-log text (echo, prompts) just keeps ``msg`` as the raw text."""
    text = raw.rstrip("\r\n")
    m = LOG_RE.search(text)
    if m:
        msg = m.group(4)
        return LogLine(text, m.group(1), int(m.group(2)), m.group(3), msg, tuple(CODE_RE.findall(msg)))
    return LogLine(text, msg=text.strip(), codes=tuple(CODE_RE.findall(text)))


def clean_text(data: bytes) -> str:
    """Decode bytes, strip ANSI escapes and bare CRs."""
    return ANSI_RE.sub("", data.decode("utf-8", errors="replace")).replace("\r", "")


@dataclass
class Response:
    """Everything the DUT printed after a command + assertion helpers."""

    command: str
    text: str
    timed_out: bool = False
    elapsed: float = 0.0
    lines: list[LogLine] = field(default_factory=list)

    @classmethod
    def from_text(cls, command: str, text: str, timed_out: bool = False, elapsed: float = 0.0) -> Response:
        lines = [parse_line(line) for line in text.split("\n") if line.strip()]
        return cls(command, text, timed_out, elapsed, lines)

    @property
    def codes(self) -> list[str]:
        """All E###/W### codes, in order."""
        return [code for line in self.lines for code in line.codes]

    @property
    def errors(self) -> list[str]:
        return [c for c in self.codes if c.startswith("E")]

    def has_code(self, code: str | ErrorCode) -> bool:
        return code in self.codes

    def has(self, substring: str) -> bool:
        return substring in self.text

    def search(self, pattern: str) -> re.Match[str] | None:
        return re.search(pattern, self.text)

    def without_noise(self) -> list[LogLine]:
        return [line for line in self.lines if not line.is_noise]

    def __str__(self) -> str:
        return self.text
