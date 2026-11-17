"""Readiness checks.

Every check is a plain function ``(ctx) -> CheckResult``. ``CHECKS`` lists them
in report order. To add a check: write the function, add it to ``CHECKS``, add
a test, and document it in docs/checks.md.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ato_readiness_checker.baseline import Baseline
from ato_readiness_checker.extract import PackageView
from ato_readiness_checker.model import CheckResult


@dataclass
class Context:
    view: PackageView
    baseline: Baseline | None
    as_of: date
    max_assessment_age_days: int = 365
    schema_dir: Path | None = None


CheckFn = Callable[[Context], CheckResult]


def _registry() -> list[CheckFn]:
    from ato_readiness_checker.checks import assessment, controls, package, poam, refs, ssp, trace

    return [
        package.package_complete,
        ssp.required_sections,
        ssp.categorization_consistent,
        ssp.key_roles_assigned,
        ssp.draft_language,
        controls.baseline_coverage,
        controls.implementation_statements,
        controls.implementation_status,
        controls.ssp_matches_assessment,
        controls.planned_controls_on_poam,
        controls.not_applicable_justified,
        assessment.results_present,
        assessment.controls_assessed,
        assessment.assessment_current,
        trace.findings_have_poam_items,
        trace.poam_items_trace_to_findings,
        poam.due_dates,
        poam.milestones,
        poam.points_of_contact,
        poam.overdue_items,
        poam.severity_recorded,
        poam.milestones_before_due_date,
        refs.references_resolve,
        refs.assessment_subjects_in_ssp,
        refs.same_system,
        refs.unique_uuids,
        refs.oscal_versions,
        refs.schema_valid,
        poam.open_high_severity,
        poam.accepted_risks,
    ]


def run_checks(ctx: Context) -> list[CheckResult]:
    return [check(ctx) for check in _registry()]


def check_catalog() -> list[CheckResult]:
    """Every check's ID, title, category, severity and description (run on an empty package)."""
    from ato_readiness_checker.extract import build_view
    from ato_readiness_checker.loader import Package

    ctx = Context(view=build_view(Package()), baseline=None, as_of=date(2000, 1, 1))
    catalog = []
    for check in _registry():
        r = check(ctx)
        catalog.append(CheckResult(r.check_id, r.title, r.category, r.severity, r.description))
    return catalog
