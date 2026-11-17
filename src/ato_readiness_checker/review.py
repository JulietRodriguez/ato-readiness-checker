"""Run every check on a package and collect the numbers the reports need."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from ato_readiness_checker import OSCAL_VERSION, __version__
from ato_readiness_checker.baseline import Baseline, baseline_from_ssp
from ato_readiness_checker.checks import Context, run_checks
from ato_readiness_checker.checks.trace import TraceRow, trace_findings
from ato_readiness_checker.extract import PackageView, PoamItem, build_view
from ato_readiness_checker.ids import SEVERITY_LEVELS
from ato_readiness_checker.loader import Package
from ato_readiness_checker.model import CheckResult, Issue
from ato_readiness_checker.scoring import (
    LEVELS,
    all_issues,
    issue_counts,
    readiness_level,
    readiness_score,
    risk_issue_counts,
)

DISCLAIMER = (
    "The readiness score and level are this tool's own measures of package completeness and "
    "consistency. They are not an official FedRAMP, DoD or NIST metric. Only the Authorizing "
    "Official makes the authorization decision."
)


@dataclass
class Review:
    view: PackageView
    results: list[CheckResult]
    baseline: Baseline | None
    as_of: date
    generated_at: str
    score: float
    level: str
    trace: list[TraceRow]
    stats: dict = field(default_factory=dict)

    @property
    def issues(self) -> list[Issue]:
        return all_issues(self.results)

    @property
    def level_text(self) -> str:
        return LEVELS[self.level]

    @property
    def system_name(self) -> str:
        return self.view.system_name

    def open_items(self) -> list[PoamItem]:
        return [i for i in self.view.poam_items if i.is_open]

    def to_dict(self) -> dict:
        pkg = self.view.package
        checks = self.results
        return {
            "tool": {"name": "ato-readiness-checker", "version": __version__},
            "generated_at": self.generated_at,
            "as_of": self.as_of.isoformat(),
            "disclaimer": DISCLAIMER,
            "system_name": self.system_name,
            "documents": [
                {"kind": d.kind, "file": d.path.name, "title": d.title, "oscal_version": d.oscal_version}
                for d in pkg.documents
            ],
            "baseline": ({"source": self.baseline.source, "controls": len(self.baseline)} if self.baseline else None),
            "readiness": {
                "score": self.score,
                "level": self.level,
                "level_meaning": self.level_text,
            },
            "checks_summary": {
                "total": len(checks),
                "passed": sum(1 for c in checks if c.passed),
                "failed": sum(1 for c in checks if not c.passed and not c.skipped),
                "skipped": sum(1 for c in checks if c.skipped),
            },
            "issue_counts": issue_counts(checks),
            "risk_issue_counts": risk_issue_counts(checks),
            "stats": self.stats,
            "traceability": [
                {
                    "finding": row.finding.display,
                    "finding_title": row.finding.title,
                    "finding_uuid": row.finding.uuid,
                    "match": row.method,
                    "poam_items": [i.label for i in row.items],
                }
                for row in self.trace
            ],
            "checks": [c.to_dict() for c in checks],
        }


def _stats(view: PackageView, as_of: date) -> dict:
    stats: dict = {}
    if view.ssp is not None:
        status_counts = Counter(c.effective_status or "none" for c in view.ssp.controls.values())
        stats["ssp"] = {
            "controls": len(view.ssp.controls),
            "implementation_status": dict(sorted(status_counts.items())),
        }
    findings = view.ar.findings
    stats["assessment"] = {
        "results": view.ar.result_count,
        "findings": len(findings),
        "satisfied": sum(1 for f in findings if f.state == "satisfied"),
        "not_satisfied": sum(1 for f in findings if f.state == "not-satisfied"),
        "latest_assessment": max(view.ar.assessment_dates).isoformat() if view.ar.assessment_dates else None,
    }
    items = view.poam_items
    open_items = [i for i in items if i.is_open]
    stats["poam"] = {
        "items": len(items),
        "open": len(open_items),
        "risk_accepted": sum(1 for i in items if i.is_accepted),
        "closed": sum(1 for i in items if i.is_closed),
        "open_by_severity": {
            level: sum(1 for i in open_items if i.severity == level) for level in (*SEVERITY_LEVELS, None)
        },
        "overdue": sum(1 for i in open_items if i.deadline and i.deadline < as_of),
    }
    # JSON keys must be strings
    stats["poam"]["open_by_severity"]["unknown"] = stats["poam"]["open_by_severity"].pop(None)
    return stats


def run_review(
    package: Package,
    *,
    baseline: Baseline | None = None,
    as_of: date | None = None,
    max_assessment_age_days: int = 365,
    schema_dir: str | Path | None = None,
    generated_at: str | None = None,
) -> Review:
    view = build_view(package)
    if baseline is None and package.ssp is not None:
        baseline = baseline_from_ssp(package.ssp)
    as_of = as_of or datetime.now(timezone.utc).date()
    ctx = Context(
        view=view,
        baseline=baseline,
        as_of=as_of,
        max_assessment_age_days=max_assessment_age_days,
        schema_dir=Path(schema_dir) if schema_dir else None,
    )
    results = run_checks(ctx)
    return Review(
        view=view,
        results=results,
        baseline=baseline,
        as_of=as_of,
        generated_at=generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        score=readiness_score(results),
        level=readiness_level(results),
        trace=trace_findings(view),
        stats=_stats(view, as_of),
    )


__all__ = ["DISCLAIMER", "OSCAL_VERSION", "Review", "run_review"]
