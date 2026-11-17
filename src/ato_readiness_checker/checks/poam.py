"""Checks on POA&M items.

"Open" means not closed and not an approved deviation (risk acceptance).
Approved deviations are listed separately (RISK-002) so the AO sees every
risk that was accepted rather than fixed.
"""

from __future__ import annotations

from ato_readiness_checker.checks import Context
from ato_readiness_checker.model import CheckResult, Severity

DOC = "poam"

_HIGH = ("critical", "high")
_SEVERITY_LABEL = {
    "critical": "Critical",
    "high": "High / CAT I",
    "moderate": "Moderate / CAT II",
    "low": "Low / CAT III",
}


def _skip_without_items(r: CheckResult, ctx: Context) -> bool:
    if not ctx.view.poam_items:
        r.skipped_reason = "No POA&M items." if ctx.view.package.poams else "No POA&M supplied."
        return True
    return False


def due_dates(ctx: Context) -> CheckResult:
    r = CheckResult(
        "POAM-001",
        "POA&M items have a scheduled completion date",
        "poam",
        Severity.HIGH,
        "Every item that is not closed needs a due date (risk deadline or scheduled-completion-date).",
    )
    if _skip_without_items(r, ctx):
        return r
    for item in ctx.view.poam_items:
        if item.is_closed:
            continue
        r.evaluated += 1
        if item.deadline is None:
            r.fail("No scheduled completion date.", ref=item.label, document=DOC)
    return r


def milestones(ctx: Context) -> CheckResult:
    r = CheckResult(
        "POAM-002",
        "Open POA&M items have dated milestones",
        "poam",
        Severity.MEDIUM,
        "Each open item needs at least one milestone, and each milestone needs a date.",
    )
    if _skip_without_items(r, ctx):
        return r
    for item in ctx.view.poam_items:
        if not item.is_open:
            continue
        r.evaluated += 1
        if not item.milestones:
            r.fail("No milestones.", ref=item.label, document=DOC)
        elif any(m.due is None for m in item.milestones):
            r.fail("A milestone has no date.", ref=item.label, document=DOC, severity=Severity.LOW)
    return r


def points_of_contact(ctx: Context) -> CheckResult:
    r = CheckResult(
        "POAM-003",
        "POA&M items have a point of contact",
        "poam",
        Severity.MEDIUM,
        "Someone must own each item: a point-of-contact prop, an origin party, or a task responsible party.",
    )
    if _skip_without_items(r, ctx):
        return r
    for item in ctx.view.poam_items:
        if item.is_closed:
            continue
        r.evaluated += 1
        if not item.pocs:
            r.fail("No point of contact.", ref=item.label, document=DOC)
    return r


def overdue_items(ctx: Context) -> CheckResult:
    r = CheckResult(
        "POAM-004",
        "No overdue POA&M items",
        "poam",
        Severity.HIGH,
        "An open item past its due date needs a new date with a documented reason, or closure. "
        "This is a package problem (the POA&M is not being maintained). Overdue Critical/High "
        "items are raised to critical.",
    )
    if _skip_without_items(r, ctx):
        return r
    for item in ctx.view.poam_items:
        if not item.is_open:
            continue
        r.evaluated += 1
        if item.deadline and item.deadline < ctx.as_of:
            days = (ctx.as_of - item.deadline).days
            severity = Severity.CRITICAL if item.severity in _HIGH else Severity.HIGH
            r.fail(
                f"Due {item.deadline.isoformat()}, {days} days overdue as of {ctx.as_of.isoformat()}.",
                ref=item.label,
                document=DOC,
                severity=severity,
            )
    return r


def open_high_severity(ctx: Context) -> CheckResult:
    r = CheckResult(
        "RISK-001",
        "Open Critical, High or CAT I weaknesses",
        "risk",
        Severity.HIGH,
        "Lists each open Critical, High or CAT I item for the AO. This is risk, not a package defect, "
        "so it does not affect the readiness score or level; open Critical items are critical issues "
        "and High/CAT I items are high issues for the --fail-on gate.",
    )
    if _skip_without_items(r, ctx):
        return r
    for item in ctx.view.poam_items:
        if not item.is_open:
            continue
        r.evaluated += 1
        if item.severity in _HIGH:
            r.fail(
                f"Open {_SEVERITY_LABEL[item.severity]} weakness ({item.controls_display}).",
                ref=item.label,
                document=DOC,
                severity=Severity.CRITICAL if item.severity == "critical" else Severity.HIGH,
            )
    return r


def severity_recorded(ctx: Context) -> CheckResult:
    r = CheckResult(
        "POAM-005",
        "POA&M items record a severity",
        "poam",
        Severity.LOW,
        "Without a severity (Critical/High/Moderate/Low or CAT I/II/III) the item can't be prioritized.",
    )
    if _skip_without_items(r, ctx):
        return r
    for item in ctx.view.poam_items:
        if item.is_closed:
            continue
        r.evaluated += 1
        if item.severity is None:
            r.fail("No recognizable severity.", ref=item.label, document=DOC)
    return r


def milestones_before_due_date(ctx: Context) -> CheckResult:
    r = CheckResult(
        "POAM-006",
        "Milestones fall on or before the item's due date",
        "poam",
        Severity.LOW,
        "A milestone scheduled after the completion date means the plan and the due date disagree.",
    )
    if _skip_without_items(r, ctx):
        return r
    for item in ctx.view.poam_items:
        if not item.is_open or not item.deadline or not item.milestones:
            continue
        r.evaluated += 1
        late = [m for m in item.milestones if m.due and m.due > item.deadline]
        if late:
            r.fail(
                f"{len(late)} milestone(s) after the due date {item.deadline.isoformat()}.",
                ref=item.label,
                document=DOC,
            )
    return r


def accepted_risks(ctx: Context) -> CheckResult:
    r = CheckResult(
        "RISK-002",
        "Accepted risks are listed for the AO",
        "risk",
        Severity.INFO,
        "Items with an approved deviation (risk acceptance) are listed so the AO sees every "
        "risk that is being carried rather than fixed. Informational; does not affect the score or level.",
    )
    if _skip_without_items(r, ctx):
        return r
    for item in ctx.view.poam_items:
        if item.is_closed:
            continue
        r.evaluated += 1
        if item.is_accepted:
            sev = _SEVERITY_LABEL.get(item.severity or "", "unknown severity")
            r.fail(f"Risk accepted ({sev}, {item.controls_display}).", ref=item.label, document=DOC)
    return r
