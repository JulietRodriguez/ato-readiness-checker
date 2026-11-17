"""Flatten SSP, Assessment Results and POA&M documents into simple views.

The checks never walk raw OSCAL; they work on these small dataclasses. That
keeps every "where does OSCAL keep X?" decision in one file, which is the part
most likely to need changing when a new producer tool shows up.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from ato_readiness_checker.ids import display_control_id, normalize_control_id, normalize_severity, worst_severity
from ato_readiness_checker.loader import Document, Package

# --- small helpers --------------------------------------------------------------


def props(obj: dict[str, Any], *names: str) -> list[str]:
    """Values of props whose name matches (any namespace, case-insensitive)."""
    wanted = {n.lower() for n in names}
    return [
        str(p.get("value", "")).strip()
        for p in obj.get("props", []) or []
        if isinstance(p, dict) and str(p.get("name", "")).lower() in wanted and str(p.get("value", "")).strip()
    ]


_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        m = _DATE_RE.match(text)
        if m:
            try:
                return date.fromisoformat(m.group(1))
            except ValueError:
                return None
    return None


def _uuids(items: Iterable[dict[str, Any]] | None, key: str) -> list[str]:
    return [str(i[key]) for i in items or [] if isinstance(i, dict) and i.get(key)]


def _text(value: Any) -> str:
    return str(value).strip() if value else ""


# --- SSP --------------------------------------------------------------------------

VALID_IMPLEMENTATION_STATES = ("implemented", "partial", "planned", "alternative", "not-applicable")


@dataclass
class ControlImpl:
    key: str
    control_id: str  # as written in the SSP
    uuids: list[str] = field(default_factory=list)
    requirement_statuses: list[str] = field(default_factory=list)  # implemented-requirement props
    component_statuses: list[str] = field(default_factory=list)  # by-components implementation-status
    statement_texts: list[str] = field(default_factory=list)  # narrative describing the implementation
    remarks: list[str] = field(default_factory=list)

    @property
    def display(self) -> str:
        return display_control_id(self.key)

    @property
    def all_statuses(self) -> list[str]:
        return self.requirement_statuses + self.component_statuses

    @property
    def effective_status(self) -> str | None:
        """The status we treat as the SSP's claim for this control.

        The requirement-level prop wins when present (it is the summary the
        author chose); otherwise the weakest component state, because a
        control is only as implemented as its least-implemented part.
        """
        if self.requirement_statuses:
            return self.requirement_statuses[0]
        order = ["planned", "partial", "alternative", "implemented", "not-applicable"]
        known = [s for s in self.component_statuses if s in order]
        return min(known, key=order.index) if known else None


@dataclass
class SspView:
    doc: Document
    controls: dict[str, ControlImpl]
    component_uuids: set[str]
    system_ids: list[str]

    @property
    def system_name(self) -> str:
        return _text(self.doc.root.get("system-characteristics", {}).get("system-name")) or self.doc.title


def _collect_component_entries(req: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield from req.get("by-components", []) or []
    for stmt in req.get("statements", []) or []:
        yield from stmt.get("by-components", []) or []


def build_ssp_view(doc: Document) -> SspView:
    controls: dict[str, ControlImpl] = {}
    reqs = doc.root.get("control-implementation", {}).get("implemented-requirements", []) or []
    for req in reqs:
        key = normalize_control_id(req.get("control-id"))
        if not key:
            continue
        impl = controls.setdefault(key, ControlImpl(key=key, control_id=str(req.get("control-id"))))
        if req.get("uuid"):
            impl.uuids.append(str(req["uuid"]))
        impl.requirement_statuses += [s.lower() for s in props(req, "implementation-status")]
        for entry in _collect_component_entries(req):
            state = entry.get("implementation-status", {}).get("state")
            if state:
                impl.component_statuses.append(str(state).lower())
            impl.component_statuses += [s.lower() for s in props(entry, "implementation-status")]
            if _text(entry.get("description")):
                impl.statement_texts.append(_text(entry.get("description")))
        for stmt in req.get("statements", []) or []:
            if _text(stmt.get("remarks")):
                impl.remarks.append(_text(stmt.get("remarks")))
        if _text(req.get("remarks")):
            impl.remarks.append(_text(req.get("remarks")))
    components = doc.root.get("system-implementation", {}).get("components", []) or []
    system_ids = _uuids(doc.root.get("system-characteristics", {}).get("system-ids"), "id")
    return SspView(
        doc=doc,
        controls=controls,
        component_uuids={str(c["uuid"]) for c in components if c.get("uuid")},
        system_ids=system_ids,
    )


# --- Assessment Results ---------------------------------------------------------------

SEVERITY_PROP_NAMES = (
    "severity",
    "severity-category",
    "risk-level",
    "risk-rating",
    "cat",
    "category",
    "raw-severity",
    "priority",
)


@dataclass
class ArFinding:
    uuid: str
    key: str | None
    target_id: str
    state: str
    title: str
    severity: str | None
    observation_uuids: list[str]
    doc: Document

    @property
    def display(self) -> str:
        return display_control_id(self.key) if self.key else self.target_id or "(no target)"


@dataclass
class ArView:
    findings: list[ArFinding]
    reviewed_keys: set[str]
    include_all: bool
    assessment_dates: list[date]
    result_count: int


def build_ar_view(docs: list[Document]) -> ArView:
    findings: list[ArFinding] = []
    reviewed: set[str] = set()
    include_all = False
    dates: list[date] = []
    result_count = 0
    for doc in docs:
        for result in doc.root.get("results", []) or []:
            result_count += 1
            for key in ("end", "start"):
                d = parse_date(result.get(key))
                if d:
                    dates.append(d)
                    break
            risks = {str(r.get("uuid")): r for r in result.get("risks", []) or []}
            for sel in result.get("reviewed-controls", {}).get("control-selections", []) or []:
                if "include-all" in sel:
                    include_all = True
                for inc in sel.get("include-controls", []) or []:
                    k = normalize_control_id(inc.get("control-id"))
                    if k:
                        reviewed.add(k)
            for f in result.get("findings", []) or []:
                target = f.get("target", {}) or {}
                target_id = str(target.get("target-id", ""))
                sev_values = props(f, *SEVERITY_PROP_NAMES)
                for rr in f.get("related-risks", []) or []:
                    risk = risks.get(str(rr.get("risk-uuid")))
                    if risk:
                        sev_values += props(risk, *SEVERITY_PROP_NAMES)
                findings.append(
                    ArFinding(
                        uuid=str(f.get("uuid", "")),
                        key=normalize_control_id(target_id),
                        target_id=target_id,
                        state=str(target.get("status", {}).get("state", "")).lower(),
                        title=_text(f.get("title")) or target_id,
                        severity=worst_severity([normalize_severity(v) for v in sev_values]),
                        observation_uuids=_uuids(f.get("related-observations"), "observation-uuid"),
                        doc=doc,
                    )
                )
    return ArView(
        findings=findings,
        reviewed_keys=reviewed,
        include_all=include_all,
        assessment_dates=dates,
        result_count=result_count,
    )


# --- POA&M ---------------------------------------------------------------------------

RISK_STATUSES = ("open", "investigating", "remediating", "deviation-requested", "deviation-approved", "closed")
_STATUS_TEXT = {
    "open": "open",
    "ongoing": "open",
    "not started": "open",
    "in progress": "remediating",
    "remediating": "remediating",
    "investigating": "investigating",
    "delayed": "remediating",
    "risk accepted": "deviation-approved",
    "accepted": "deviation-approved",
    "deviation approved": "deviation-approved",
    "deviation requested": "deviation-requested",
    "closed": "closed",
    "completed": "closed",
    "complete": "closed",
}
POC_PROP_NAMES = ("point-of-contact", "poc", "responsible-party", "poc-name")
DUE_PROP_NAMES = ("scheduled-completion-date", "due-date", "deadline", "planned-completion-date")
CONTROL_PROP_NAMES = ("control", "control-id", "security-control", "related-control", "security-controls")


@dataclass
class Milestone:
    title: str
    due: date | None


@dataclass
class PoamItem:
    uuid: str
    title: str
    keys: set[str]
    severity: str | None
    status: str  # one of RISK_STATUSES or "unknown"
    deadline: date | None
    milestones: list[Milestone]
    pocs: list[str]
    finding_uuids: list[str]  # related-findings (may point into the POA&M or into an AR)
    observation_uuids: list[str]
    doc: Document

    @property
    def is_closed(self) -> bool:
        return self.status == "closed"

    @property
    def is_accepted(self) -> bool:
        return self.status == "deviation-approved"

    @property
    def is_open(self) -> bool:
        return not self.is_closed and not self.is_accepted

    @property
    def label(self) -> str:
        """Title plus the start of the UUID, so two items with the same title stay distinct."""
        return f"{self.title} [{self.uuid[:8]}]" if self.uuid else self.title

    @property
    def controls_display(self) -> str:
        return ", ".join(sorted(display_control_id(k) for k in self.keys)) or "(no control)"


def _walk_tasks(tasks: list[dict[str, Any]] | None) -> Iterator[dict[str, Any]]:
    for task in tasks or []:
        yield task
        yield from _walk_tasks(task.get("tasks"))


def _task_date(task: dict[str, Any]) -> date | None:
    timing = task.get("timing", {}) or {}
    if "on-date" in timing:
        return parse_date(timing["on-date"].get("date"))
    if "within-date-range" in timing:
        return parse_date(timing["within-date-range"].get("end"))
    return None


def _combine_status(values: list[str]) -> str:
    known = [v for v in values if v in RISK_STATUSES]
    if not known:
        return "unknown"
    if all(v == "closed" for v in known):
        return "closed"
    still_open = [v for v in known if v not in ("closed", "deviation-approved")]
    if not still_open:
        return "deviation-approved"
    # Most "open" status wins so nothing is reported as further along than it is.
    return min(still_open, key=RISK_STATUSES.index)


def _party_names(root: dict[str, Any]) -> dict[str, str]:
    return {
        str(p["uuid"]): _text(p.get("name")) or _text(p.get("short-name")) or str(p["uuid"])
        for p in root.get("metadata", {}).get("parties", []) or []
        if p.get("uuid")
    }


def _origin_parties(origins: list[dict[str, Any]] | None, parties: dict[str, str]) -> list[str]:
    names = []
    for origin in origins or []:
        for actor in origin.get("actors", []) or []:
            if actor.get("type") == "party" and actor.get("actor-uuid"):
                names.append(parties.get(str(actor["actor-uuid"]), str(actor["actor-uuid"])))
    return names


def build_poam_items(doc: Document) -> list[PoamItem]:
    root = doc.root
    risks = {str(r.get("uuid")): r for r in root.get("risks", []) or []}
    local_findings = {str(f.get("uuid")): f for f in root.get("findings", []) or []}
    parties = _party_names(root)
    items: list[PoamItem] = []
    for raw in root.get("poam-items", []) or []:
        keys: set[str] = set()
        observation_uuids = _uuids(raw.get("related-observations"), "observation-uuid")
        finding_uuids = _uuids(raw.get("related-findings"), "finding-uuid")
        for fu in finding_uuids:
            lf = local_findings.get(fu)
            if lf:
                k = normalize_control_id(lf.get("target", {}).get("target-id"))
                if k:
                    keys.add(k)
                observation_uuids += _uuids(lf.get("related-observations"), "observation-uuid")
        for value in props(raw, *CONTROL_PROP_NAMES):
            for part in re.split(r"[,;]\s*", value):
                k = normalize_control_id(part)
                if k:
                    keys.add(k)

        linked_risks = [risks[u] for u in _uuids(raw.get("related-risks"), "risk-uuid") if u in risks]

        sev_values = props(raw, *SEVERITY_PROP_NAMES)
        for risk in linked_risks:
            sev_values += props(risk, *SEVERITY_PROP_NAMES)
            for ch in risk.get("characterizations", []) or []:
                for facet in ch.get("facets", []) or []:
                    if str(facet.get("name", "")).lower() in ("severity", "risk", "risk-level", "impact"):
                        sev_values.append(str(facet.get("value", "")))

        statuses = [str(r.get("status", "")).lower() for r in linked_risks]
        if not any(s in RISK_STATUSES for s in statuses):
            statuses = [_STATUS_TEXT.get(s.lower(), "") for s in props(raw, "poam-status", "status")]

        deadlines = [d for d in (parse_date(r.get("deadline")) for r in linked_risks) if d]
        if not deadlines:
            deadlines = [d for d in (parse_date(v) for v in props(raw, *DUE_PROP_NAMES)) if d]

        milestones: list[Milestone] = []
        pocs = props(raw, *POC_PROP_NAMES) + _origin_parties(raw.get("origins"), parties)
        for risk in linked_risks:
            pocs += props(risk, *POC_PROP_NAMES) + _origin_parties(risk.get("origins"), parties)
            for rem in risk.get("remediations", []) or []:
                pocs += _origin_parties(rem.get("origins"), parties)
                for task in _walk_tasks(rem.get("tasks")):
                    if str(task.get("type", "")).lower() == "milestone":
                        milestones.append(Milestone(title=_text(task.get("title")), due=_task_date(task)))
                    for role in task.get("responsible-roles", []) or []:
                        pocs += [parties.get(str(u), str(u)) for u in role.get("party-uuids", []) or []]
        milestones += [Milestone(title=v, due=parse_date(v)) for v in props(raw, "milestone")]

        items.append(
            PoamItem(
                uuid=str(raw.get("uuid", "")),
                title=_text(raw.get("title")) or "(untitled POA&M item)",
                keys=keys,
                severity=worst_severity([normalize_severity(v) for v in sev_values]),
                status=_combine_status(statuses),
                deadline=min(deadlines) if deadlines else None,
                milestones=milestones,
                pocs=list(dict.fromkeys(p for p in pocs if p)),
                finding_uuids=finding_uuids,
                observation_uuids=list(dict.fromkeys(observation_uuids)),
                doc=doc,
            )
        )
    return items


# --- whole package ------------------------------------------------------------------


@dataclass
class PackageView:
    package: Package
    ssp: SspView | None
    ar: ArView
    poam_items: list[PoamItem]

    @property
    def system_name(self) -> str:
        if self.ssp:
            return self.ssp.system_name
        docs = self.package.documents
        return docs[0].title if docs else "(unknown system)"


def build_view(package: Package) -> PackageView:
    items: list[PoamItem] = []
    for doc in package.poams:
        items.extend(build_poam_items(doc))
    return PackageView(
        package=package,
        ssp=build_ssp_view(package.ssp) if package.ssp else None,
        ar=build_ar_view(package.assessment_results),
        poam_items=items,
    )
