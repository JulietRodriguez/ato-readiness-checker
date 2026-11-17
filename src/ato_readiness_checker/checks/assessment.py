"""Checks on the Assessment Results."""

from __future__ import annotations

from ato_readiness_checker.checks import Context
from ato_readiness_checker.ids import display_control_id
from ato_readiness_checker.model import CheckResult, Severity

DOC = "assessment-results"


def results_present(ctx: Context) -> CheckResult:
    r = CheckResult(
        "AR-001",
        "Assessment Results contain results and findings",
        "assessment",
        Severity.CRITICAL,
        "Each Assessment Results document needs at least one result with findings.",
    )
    docs = ctx.view.package.assessment_results
    if not docs:
        r.skipped_reason = "No Assessment Results supplied (reported by PKG-001)."
        return r
    for doc in docs:
        r.evaluated += 1
        results = doc.root.get("results", []) or []
        if not results:
            r.fail("Contains no results.", ref=doc.path.name, document=DOC)
        elif not any(res.get("findings") for res in results):
            r.fail("Has results but no findings.", ref=doc.path.name, document=DOC, severity=Severity.HIGH)
    return r


def controls_assessed(ctx: Context) -> CheckResult:
    r = CheckResult(
        "AR-002",
        "Every in-scope control was assessed",
        "assessment",
        Severity.MEDIUM,
        "Each baseline control (or each SSP control when no baseline is given) should have a "
        "finding or be listed in the assessment's reviewed controls.",
    )
    if not ctx.view.package.assessment_results:
        r.skipped_reason = "No Assessment Results supplied."
        return r
    if ctx.baseline is not None:
        scope, scope_name = set(ctx.baseline.controls), "baseline"
    elif ctx.view.ssp is not None:
        scope, scope_name = set(ctx.view.ssp.controls), "SSP"
    else:
        r.skipped_reason = "Needs a baseline or an SSP to know which controls are in scope."
        return r
    assessed = {f.key for f in ctx.view.ar.findings if f.key} | ctx.view.ar.reviewed_keys
    r.evaluated = len(scope)
    for key in sorted(scope - assessed):
        r.fail(f"No assessment finding for this {scope_name} control.", ref=display_control_id(key), document=DOC)
    return r


def assessment_current(ctx: Context) -> CheckResult:
    r = CheckResult(
        "AR-003",
        "Assessment is current",
        "assessment",
        Severity.MEDIUM,
        "The most recent assessment result should fall within the allowed age (default 365 days).",
    )
    if not ctx.view.package.assessment_results:
        r.skipped_reason = "No Assessment Results supplied."
        return r
    r.evaluated = 1
    dates = ctx.view.ar.assessment_dates
    if not dates:
        r.fail("No assessment start or end dates recorded.", ref="results", document=DOC, severity=Severity.LOW)
        return r
    latest = max(dates)
    age = (ctx.as_of - latest).days
    if age > ctx.max_assessment_age_days:
        r.fail(
            f"Latest assessment ended {latest.isoformat()}, {age} days before {ctx.as_of.isoformat()} "
            f"(limit {ctx.max_assessment_age_days}).",
            ref="results",
            document=DOC,
        )
    return r
