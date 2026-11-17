"""Checks on control implementation statements in the SSP."""

from __future__ import annotations

from ato_readiness_checker.checks import Context
from ato_readiness_checker.extract import VALID_IMPLEMENTATION_STATES
from ato_readiness_checker.ids import display_control_id
from ato_readiness_checker.model import CheckResult, Severity

DOC = "ssp"


def baseline_coverage(ctx: Context) -> CheckResult:
    r = CheckResult(
        "CTRL-001",
        "Every baseline control has an implementation statement",
        "controls",
        Severity.HIGH,
        "Each control in the selected baseline must appear in the SSP's implemented-requirements.",
    )
    if ctx.view.ssp is None:
        r.skipped_reason = "No SSP supplied."
        return r
    if ctx.baseline is None:
        r.skipped_reason = (
            "No baseline supplied. Pass --baseline (OSCAL profile, catalog, or control list), "
            "or point the SSP's import-profile at a local file."
        )
        return r
    r.evaluated = len(ctx.baseline.controls)
    for key in sorted(ctx.baseline.controls - set(ctx.view.ssp.controls)):
        r.fail("Baseline control is not addressed in the SSP.", ref=display_control_id(key), document=DOC)
    return r


def implementation_statements(ctx: Context) -> CheckResult:
    r = CheckResult(
        "CTRL-002",
        "Implemented requirements describe how the control is met",
        "controls",
        Severity.HIGH,
        "Each implemented-requirement needs narrative text (by-components description, "
        "statement narrative or remarks) explaining the implementation. Not-applicable controls are "
        "covered by CTRL-006 instead.",
    )
    if ctx.view.ssp is None:
        r.skipped_reason = "No SSP supplied."
        return r
    for impl in ctx.view.ssp.controls.values():
        if impl.effective_status == "not-applicable":
            continue  # CTRL-006 covers the justification for not-applicable controls
        r.evaluated += 1
        if not impl.statement_texts and not impl.remarks:
            r.fail("No implementation narrative.", ref=impl.display, document=DOC)
    return r


def _conflict(impl_requirement: list[str], components: list[str]) -> str | None:
    if len(set(impl_requirement)) > 1:
        return f"implemented-requirement lists more than one status ({', '.join(sorted(set(impl_requirement)))})"
    if not impl_requirement or not components:
        return None
    stated = impl_requirement[0]
    comp = set(components)
    if stated == "implemented" and comp & {"planned", "partial"}:
        return f"marked implemented but a component is {'/'.join(sorted(comp & {'planned', 'partial'}))}"
    if stated == "planned" and comp == {"implemented"}:
        return "marked planned but every component is implemented"
    if stated == "not-applicable" and comp - {"not-applicable"}:
        return "marked not-applicable but a component claims an implementation"
    return None


def implementation_status(ctx: Context) -> CheckResult:
    r = CheckResult(
        "CTRL-003",
        "Implementation status is present, valid and consistent",
        "controls",
        Severity.MEDIUM,
        "Each control needs an implementation status (implemented, partial, planned, alternative, "
        "not-applicable), and the control-level and component-level statuses must agree.",
    )
    if ctx.view.ssp is None:
        r.skipped_reason = "No SSP supplied."
        return r
    for impl in ctx.view.ssp.controls.values():
        r.evaluated += 1
        statuses = impl.all_statuses
        if not statuses:
            r.fail("No implementation status.", ref=impl.display, document=DOC)
            continue
        invalid = sorted({s for s in statuses if s not in VALID_IMPLEMENTATION_STATES})
        if invalid:
            r.fail(f"Unrecognized implementation status: {', '.join(invalid)}.", ref=impl.display, document=DOC)
            continue
        problem = _conflict(impl.requirement_statuses, impl.component_statuses)
        if problem:
            r.fail(f"Inconsistent status: {problem}.", ref=impl.display, document=DOC)
    return r


def ssp_matches_assessment(ctx: Context) -> CheckResult:
    r = CheckResult(
        "CTRL-004",
        "SSP status agrees with the assessment",
        "controls",
        Severity.MEDIUM,
        "A control the SSP calls 'implemented' should not have a not-satisfied finding, and a "
        "control assessed as satisfied should not still be 'planned' in the SSP.",
    )
    if ctx.view.ssp is None or not ctx.view.package.assessment_results:
        r.skipped_reason = "Needs both an SSP and Assessment Results."
        return r
    controls = ctx.view.ssp.controls
    for f in ctx.view.ar.findings:
        impl = controls.get(f.key or "")
        if impl is None or f.state not in ("satisfied", "not-satisfied"):
            continue
        r.evaluated += 1
        status = impl.effective_status
        if f.state == "not-satisfied" and status == "implemented":
            r.fail(
                f"SSP says implemented, but the assessment found it not satisfied ('{f.title}').",
                ref=impl.display,
                document=DOC,
            )
        elif f.state == "satisfied" and status == "planned":
            r.fail(
                "Assessed as satisfied, but the SSP still says planned.",
                ref=impl.display,
                document=DOC,
                severity=Severity.LOW,
            )
    return r


def planned_controls_on_poam(ctx: Context) -> CheckResult:
    r = CheckResult(
        "CTRL-005",
        "Planned and partial controls are tracked on the POA&M",
        "controls",
        Severity.MEDIUM,
        "A control the SSP says is only planned or partially implemented is a known gap, so it "
        "should have a POA&M item.",
    )
    if ctx.view.ssp is None:
        r.skipped_reason = "No SSP supplied."
        return r
    tracked = {k for item in ctx.view.poam_items if not item.is_closed for k in item.keys}
    for impl in ctx.view.ssp.controls.values():
        if impl.effective_status not in ("planned", "partial"):
            continue
        r.evaluated += 1
        if impl.key not in tracked:
            r.fail(
                f"SSP status is {impl.effective_status} but no open POA&M item covers it.",
                ref=impl.display,
                document=DOC,
            )
    return r


def not_applicable_justified(ctx: Context) -> CheckResult:
    r = CheckResult(
        "CTRL-006",
        "Not-applicable controls are justified",
        "controls",
        Severity.LOW,
        "A control marked not-applicable needs text explaining why.",
    )
    if ctx.view.ssp is None:
        r.skipped_reason = "No SSP supplied."
        return r
    for impl in ctx.view.ssp.controls.values():
        if impl.effective_status != "not-applicable":
            continue
        r.evaluated += 1
        if not impl.statement_texts and not impl.remarks:
            r.fail("Marked not-applicable with no justification.", ref=impl.display, document=DOC)
    return r
