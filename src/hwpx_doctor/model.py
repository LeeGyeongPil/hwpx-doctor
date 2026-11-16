"""Data types shared by the checker, the fixer and the renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class HwpxDoctorError(Exception):
    """Base class for errors raised by hwpx-doctor."""


class InputError(HwpxDoctorError):
    """The input path is missing/unreadable, or an output would clash (CLI exit code 2)."""


@dataclass(frozen=True)
class Finding:
    """One defect. ``line`` is None for container-level findings."""

    rule: str
    severity: str
    part: str
    path: str
    line: int | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "part": self.part,
            "path": self.path,
            "line": self.line,
            "message": self.message,
        }


@dataclass
class Report:
    """All findings for one file, sorted by (rule, part, line)."""

    file: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warning"]

    def failed(self, strict: bool = False) -> bool:
        """True if the file fails: any error, or (with ``strict``) any warning."""
        return bool(self.errors) or (strict and bool(self.warnings))

    def to_dict(self) -> dict[str, Any]:
        return {"file": self.file, "findings": [f.to_dict() for f in self.findings]}


@dataclass
class FixResult:
    """Outcome of :func:`hwpx_doctor.fix`; ``report`` is the re-check of the result."""

    applied: list[str]
    wrote: bool
    report: Report
