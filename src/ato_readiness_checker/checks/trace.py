"""Traceability between assessment findings and POA&M items.

Two ways to link a finding to a POA&M item, tried in this order:

1. By UUID: the POA&M item's related-findings or related-observations point at
   the Assessment Results finding (or one of its observations). This is the
   OSCAL-native link and is unambiguous.
2. By control: the POA&M item covers the same control the finding targets.
   Most tools today generate the AR and the POA&M separately, so UUIDs never
   line up; matching on the control is the practical fallback. The report shows
   which method matched so a reviewer can judge how strong the link is.
"""

from __future__ import annotations

from dataclasses import dataclass

from ato_readiness_checker.checks import Context
from ato_readiness_checker.extract import ArFinding, PackageView, PoamItem
from ato_readiness_checker.model import CheckResult, Severity


@dataclass
class TraceRow:
    finding: ArFinding
    items: list[PoamItem]
    method: str  # "uuid", "control" or "none"


def _uuid_match(f: ArFinding, item: PoamItem) -> bool:
    if f.uuid and f.uuid in item.finding_uuids:
        return True
    return bool(set(f.observation_uuids) & set(item.observation_uuids))


def trace_findings(view: PackageView) -> list[TraceRow]:
    rows = []
    for f in view.ar.findings:
        if f.state != "not-satisfied":
            continue
        by_uuid = [i for i in view.poam_items if _uuid_match(f, i)]
        if by_uuid:
            rows.append(TraceRow(f, by_uuid, "uuid"))
            continue
        by_control = [i for i in view.poam_items if f.key and f.key in i.keys]
        rows.append(TraceRow(f, by_control, "control" if by_control else "none"))
    return rows


def findings_have_poam_items(ctx: Context) -> CheckResult:
    r = CheckResult(
        "TRC-001",
        "Every not-satisfied finding has a POA&M item",
        "traceability",
        Severity.HIGH,
        "Each weakness the assessment found must be tracked on the POA&M (or the AO must be told why not).",
    )
    if not ctx.view.package.assessment_results:
        r.skipped_reason = "No Assessment Results supplied."
        return r
    for row in trace_findings(ctx.view):
        r.evaluated += 1
        if row.method == "none":
            r.fail(
                f"Not-satisfied finding '{row.finding.title}' has no POA&M item.",
                ref=row.finding.display,
                document="assessment-results",
            )
    return r


def poam_items_trace_to_findings(ctx: Context) -> CheckResult:
    r = CheckResult(
        "TRC-002",
        "Every POA&M item traces to an assessment finding",
        "traceability",
        Severity.MEDIUM,
        "Each open POA&M item should link (by UUID or control) to a not-satisfied finding in the "
        "Assessment Results, so the AO can see where the weakness came from.",
    )
    if not ctx.view.package.assessment_results or not ctx.view.poam_items:
        r.skipped_reason = "Needs both Assessment Results and POA&M items."
        return r
    open_findings = [f for f in ctx.view.ar.findings if f.state == "not-satisfied"]
    for item in ctx.view.poam_items:
        if item.is_closed:
            continue
        r.evaluated += 1
        linked = any(_uuid_match(f, item) for f in open_findings) or any(
            f.key and f.key in item.keys for f in open_findings
        )
        if not linked:
            r.fail(
                f"No not-satisfied finding in the Assessment Results for {item.controls_display}.",
                ref=item.label,
                document="poam",
            )
    return r
