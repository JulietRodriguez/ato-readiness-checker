"""Result types shared by the checks, the scorer and the report writers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """How much a failed check matters for the authorization package.

    These are the tool's own levels for *package problems*. They are not the
    severity of the security weaknesses inside the POA&M (those use
    critical/high/moderate/low, see ``ids.normalize_severity``).
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def rank(self) -> int:
        return _RANK[self]

    @classmethod
    def parse(cls, value: str) -> Severity:
        try:
            return cls(value.strip().lower())
        except ValueError as exc:
            choices = ", ".join(s.value for s in cls)
            raise ValueError(f"unknown severity {value!r} (choose from {choices})") from exc


_RANK = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


@dataclass(frozen=True)
class Issue:
    """One object that failed a check."""

    check_id: str
    severity: Severity
    message: str
    ref: str = ""  # what the problem is attached to, e.g. "AC-2" or a POA&M item title
    document: str = ""  # ssp / assessment-results / poam / package

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "severity": self.severity.value,
            "message": self.message,
            "ref": self.ref,
            "document": self.document,
        }


@dataclass
class CheckResult:
    """Outcome of one check across every object it looked at."""

    check_id: str
    title: str
    category: str
    severity: Severity
    description: str
    evaluated: int = 0
    issues: list[Issue] = field(default_factory=list)
    skipped_reason: str | None = None

    @property
    def counts_toward_readiness(self) -> bool:
        """Risk checks describe the system's risk for the AO, not the package's quality."""
        return self.category != "risk"

    @property
    def skipped(self) -> bool:
        return self.skipped_reason is not None

    @property
    def failed(self) -> int:
        # An object can produce more than one issue; count distinct refs.
        return len({(i.document, i.ref) for i in self.issues}) if self.issues else 0

    @property
    def passed(self) -> bool:
        return not self.skipped and not self.issues

    @property
    def pass_rate(self) -> float | None:
        if self.skipped or self.evaluated <= 0:
            return None
        return max(0.0, (self.evaluated - min(self.failed, self.evaluated)) / self.evaluated)

    def fail(self, message: str, ref: str = "", document: str = "", severity: Severity | None = None) -> None:
        self.issues.append(
            Issue(
                check_id=self.check_id,
                severity=severity or self.severity,
                message=message,
                ref=ref,
                document=document,
            )
        )

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "title": self.title,
            "category": self.category,
            "counts_toward_readiness": self.counts_toward_readiness,
            "severity": self.severity.value,
            "description": self.description,
            "status": "skipped" if self.skipped else ("pass" if self.passed else "fail"),
            "evaluated": self.evaluated,
            "failed": self.failed,
            "skipped_reason": self.skipped_reason,
            "issues": [i.to_dict() for i in self.issues],
        }
