"""Checks on the System Security Plan itself."""

from __future__ import annotations

import re
from typing import Any

from ato_readiness_checker.checks import Context
from ato_readiness_checker.model import CheckResult, Severity

DOC = "ssp"


def _get(root: dict[str, Any], path: str) -> Any:
    node: Any = root
    for part in path.split("/"):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


# (path under system-security-plan, label, severity if missing)
REQUIRED_SECTIONS: list[tuple[str, str, Severity]] = [
    ("system-characteristics", "System characteristics", Severity.CRITICAL),
    ("system-characteristics/system-name", "System name", Severity.HIGH),
    ("system-characteristics/system-ids", "System identifier", Severity.MEDIUM),
    ("system-characteristics/description", "System description", Severity.MEDIUM),
    ("system-characteristics/security-sensitivity-level", "Security categorization (sensitivity level)", Severity.HIGH),
    ("system-characteristics/system-information/information-types", "Information types", Severity.HIGH),
    ("system-characteristics/security-impact-level", "Security impact level (C/I/A)", Severity.HIGH),
    ("system-characteristics/status/state", "Operational status", Severity.MEDIUM),
    ("system-characteristics/authorization-boundary/description", "Authorization boundary", Severity.HIGH),
    ("system-characteristics/network-architecture/description", "Network architecture", Severity.MEDIUM),
    ("system-characteristics/data-flow/description", "Data flow", Severity.MEDIUM),
    ("system-implementation/components", "System components", Severity.HIGH),
    ("system-implementation/inventory-items", "System inventory", Severity.MEDIUM),
    ("system-implementation/users", "Users and roles", Severity.MEDIUM),
    ("control-implementation/implemented-requirements", "Control implementation statements", Severity.CRITICAL),
]


def _skip_without_ssp(r: CheckResult, ctx: Context) -> bool:
    if ctx.view.ssp is None:
        r.skipped_reason = "No SSP supplied."
        return True
    return False


def required_sections(ctx: Context) -> CheckResult:
    r = CheckResult(
        "SSP-001",
        "Required SSP sections are present",
        "ssp",
        Severity.HIGH,
        "System characteristics, categorization, boundary, architecture, data flow, "
        "components, inventory, users and control implementation must all be filled in.",
    )
    if _skip_without_ssp(r, ctx):
        return r
    root = ctx.view.ssp.doc.root
    r.evaluated = len(REQUIRED_SECTIONS)
    for path, label, severity in REQUIRED_SECTIONS:
        if not _present(_get(root, path)):
            r.fail(f"Missing or empty: {label} ({path}).", ref=label, document=DOC, severity=severity)
    impact = _get(root, "system-characteristics/security-impact-level") or {}
    if _present(impact):
        for objective in ("confidentiality", "integrity", "availability"):
            if not _present(impact.get(f"security-objective-{objective}")):
                r.fail(
                    f"Security impact level has no {objective} value.",
                    ref="Security impact level (C/I/A)",
                    document=DOC,
                    severity=Severity.HIGH,
                )
    return r


_LEVELS = ("low", "moderate", "high")


def _level(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip().lower().removeprefix("fips-199-")
    return text if text in _LEVELS else None


def categorization_consistent(ctx: Context) -> CheckResult:
    r = CheckResult(
        "SSP-002",
        "Security categorization is consistent (FIPS 199 high-water mark)",
        "ssp",
        Severity.HIGH,
        "Each C/I/A impact must be at least the highest impact of the system's information types, "
        "and the overall sensitivity level must equal the highest of C, I and A.",
    )
    if _skip_without_ssp(r, ctx):
        return r
    chars = ctx.view.ssp.doc.root.get("system-characteristics", {}) or {}
    info_types = chars.get("system-information", {}).get("information-types", []) or []
    declared = chars.get("security-impact-level", {}) or {}
    if not info_types or not declared:
        r.skipped_reason = "Information types or security impact level missing (reported by SSP-001)."
        return r

    water = {"confidentiality": None, "integrity": None, "availability": None}
    for it in info_types:
        r.evaluated += 1
        title = str(it.get("title", it.get("uuid", "information type")))
        for objective in water:
            impact = it.get(f"{objective}-impact", {}) or {}
            level = _level(impact.get("selected") or impact.get("base"))
            if level is None:
                r.fail(
                    f"Information type '{title}' has no valid {objective} impact.",
                    ref=title,
                    document=DOC,
                    severity=Severity.MEDIUM,
                )
                continue
            if water[objective] is None or _LEVELS.index(level) > _LEVELS.index(water[objective]):
                water[objective] = level

    declared_levels = {}
    for objective, high_water in water.items():
        r.evaluated += 1
        stated = _level(declared.get(f"security-objective-{objective}"))
        declared_levels[objective] = stated
        if stated is None:
            r.fail(f"Security impact level has no valid {objective} value.", ref=objective, document=DOC)
        elif high_water and _LEVELS.index(stated) < _LEVELS.index(high_water):
            r.fail(
                f"{objective.capitalize()} is categorized {stated} but an information type is {high_water}; "
                "FIPS 199 requires the high-water mark.",
                ref=objective,
                document=DOC,
            )

    r.evaluated += 1
    sensitivity = _level(chars.get("security-sensitivity-level"))
    known = [v for v in declared_levels.values() if v]
    if known:
        expected = max(known, key=_LEVELS.index)
        if sensitivity != expected:
            r.fail(
                f"Security sensitivity level is {sensitivity or 'missing'} but the highest of C/I/A is {expected}.",
                ref="security-sensitivity-level",
                document=DOC,
                severity=Severity.MEDIUM,
            )
    return r


KEY_ROLES: list[tuple[str, tuple[str, ...]]] = [
    ("System Owner", ("system-owner", "information-system-owner")),
    ("Authorizing Official", ("authorizing-official", "ao")),
    (
        "Information System Security Officer",
        ("isso", "information-system-security-officer", "system-security-officer"),
    ),
]


def key_roles_assigned(ctx: Context) -> CheckResult:
    r = CheckResult(
        "SSP-003",
        "Key roles are assigned to people",
        "ssp",
        Severity.MEDIUM,
        "System Owner, Authorizing Official and ISSO each need a named party in metadata responsible-parties.",
    )
    if _skip_without_ssp(r, ctx):
        return r
    meta = ctx.view.ssp.doc.root.get("metadata", {}) or {}
    assigned = {
        str(rp.get("role-id", "")).lower() for rp in meta.get("responsible-parties", []) or [] if rp.get("party-uuids")
    }
    r.evaluated = len(KEY_ROLES)
    for label, ids in KEY_ROLES:
        if not assigned.intersection(ids):
            r.fail(f"No party is assigned the {label} role.", ref=label, document=DOC)
    return r


PLACEHOLDER = re.compile(
    r"\b(TBD|TODO|FIXME|to be determined|lorem ipsum|placeholder)\b|review and refine|\[insert|<insert",
    re.IGNORECASE,
)


def draft_language(ctx: Context) -> CheckResult:
    r = CheckResult(
        "SSP-004",
        "No draft or placeholder language",
        "ssp",
        Severity.MEDIUM,
        "Text such as TBD, TODO, '[insert ...]' or 'review and refine' means the SSP is still a draft.",
    )
    if _skip_without_ssp(r, ctx):
        return r
    root = ctx.view.ssp.doc.root
    fields = [
        ("System description", _get(root, "system-characteristics/description")),
        ("Authorization boundary", _get(root, "system-characteristics/authorization-boundary/description")),
        ("Network architecture", _get(root, "system-characteristics/network-architecture/description")),
        ("Data flow", _get(root, "system-characteristics/data-flow/description")),
    ]
    for impl in ctx.view.ssp.controls.values():
        for text in impl.statement_texts + impl.remarks:
            fields.append((impl.display, text))
    for label, text in fields:
        if not isinstance(text, str) or not text.strip():
            continue
        r.evaluated += 1
        m = PLACEHOLDER.search(text)
        if m:
            r.fail(f"Contains draft language: '{m.group(0)}'.", ref=label, document=DOC)
    return r
