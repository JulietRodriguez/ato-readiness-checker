"""UUID references, document identity and OSCAL versions across the package.

OSCAL documents point at each other's objects by UUID (a POA&M item names the
finding and risk it tracks; an SSP statement names the component that
implements it). A reference that resolves to nothing is a broken link: tools
that import the package will drop or reject it, and a reviewer can't follow it.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator
from typing import Any

from ato_readiness_checker.checks import Context
from ato_readiness_checker.loader import Document
from ato_readiness_checker.model import CheckResult, Severity

# Fields whose value is a UUID (or list of UUIDs) that must point at an object.
STRUCTURAL_REF_FIELDS = {
    "finding-uuid",
    "risk-uuid",
    "observation-uuid",
    "component-uuid",
    "task-uuid",
    "party-uuids",
    "location-uuids",
    "member-of-organizations",
    "actor-uuid",
    "response-uuid",
}
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _walk(node: Any, path: str = "") -> Iterator[tuple[str, str, Any, dict[str, Any]]]:
    """Yield (path, key, value, parent) for every key in the document."""
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}/{key}"
            yield child, key, value, node
            yield from _walk(value, child)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _walk(value, f"{path}[{i}]")


def defined_uuids(doc: Document) -> list[str]:
    return [str(v) for _, key, v, _ in _walk(doc.root) if key == "uuid" and isinstance(v, str)]


def _references(doc: Document) -> Iterator[tuple[str, str, str]]:
    """Yield (path, field, uuid) for structural references, including '#uuid' hrefs."""
    for path, key, value, parent in _walk(doc.root):
        if key in STRUCTURAL_REF_FIELDS:
            if key == "actor-uuid" and parent.get("type") == "assessment-platform":
                continue  # points into an assessment plan, which is not part of the package
            values = value if isinstance(value, list) else [value]
            for v in values:
                if isinstance(v, str) and v:
                    yield path, key, v
        elif key == "href" and isinstance(value, str) and value.startswith("#"):
            target = value[1:]
            if _UUID.match(target):
                yield path, "href", target


def _short(path: str) -> str:
    return re.sub(r"\[\d+\]", "", path).strip("/")


def references_resolve(ctx: Context) -> CheckResult:
    r = CheckResult(
        "REF-001",
        "All UUID references resolve",
        "references",
        Severity.HIGH,
        "Every finding-uuid, risk-uuid, observation-uuid, component-uuid, party-uuid and '#uuid' "
        "link must point at an object in the same document or another document in the package.",
    )
    docs = ctx.view.package.documents
    defined = {id(d): set(defined_uuids(d)) for d in docs}
    everywhere = set().union(*defined.values()) if defined else set()
    for doc in docs:
        for path, field, ref in _references(doc):
            r.evaluated += 1
            if ref in defined[id(doc)] or ref in everywhere:
                continue
            r.fail(
                f"{field} does not resolve to any object in the package (at {_short(path)}).",
                ref=f"{doc.path.name}:{ref}",
                document=doc.kind,
            )
    return r


def assessment_subjects_in_ssp(ctx: Context) -> CheckResult:
    r = CheckResult(
        "REF-002",
        "Assessed subjects are described in the SSP",
        "references",
        Severity.LOW,
        "Observation subjects (components, inventory items) in the Assessment Results should match "
        "objects in the SSP. A miss can mean the assessment covered something outside the "
        "documented boundary, or that the two tools use different IDs.",
    )
    if ctx.view.ssp is None or not ctx.view.package.assessment_results:
        r.skipped_reason = "Needs both an SSP and Assessment Results."
        return r
    ssp_uuids = set(defined_uuids(ctx.view.ssp.doc))
    seen: set[str] = set()
    for doc in ctx.view.package.assessment_results:
        own = set(defined_uuids(doc))
        for _, key, value, parent in _walk(doc.root):
            if key != "subject-uuid" or not isinstance(value, str) or value in seen:
                continue
            if parent.get("type") not in ("component", "inventory-item"):
                continue
            seen.add(value)
            r.evaluated += 1
            if value not in ssp_uuids and value not in own:
                title = parent.get("title") or value
                r.fail(f"Subject '{title}' ({parent.get('type')}) is not in the SSP.", ref=value, document=doc.kind)
    return r


def same_system(ctx: Context) -> CheckResult:
    r = CheckResult(
        "REF-003",
        "POA&M identifies the same system as the SSP",
        "references",
        Severity.MEDIUM,
        "The POA&M system-id should match one of the SSP's system-ids.",
    )
    if ctx.view.ssp is None or not ctx.view.package.poams:
        r.skipped_reason = "Needs both an SSP and a POA&M."
        return r
    ssp_ids = set(ctx.view.ssp.system_ids)
    for doc in ctx.view.package.poams:
        r.evaluated += 1
        sid = str(doc.root.get("system-id", {}).get("id", "")).strip()
        if not sid:
            r.fail("POA&M has no system-id.", ref=doc.path.name, document="poam")
        elif sid not in ssp_ids:
            r.fail(f"POA&M system-id {sid} is not one of the SSP's system-ids.", ref=doc.path.name, document="poam")
    return r


def unique_uuids(ctx: Context) -> CheckResult:
    r = CheckResult(
        "REF-004",
        "UUIDs are unique within each document",
        "references",
        Severity.MEDIUM,
        "OSCAL requires each object's UUID to be unique in its document; duplicates make references ambiguous.",
    )
    for doc in ctx.view.package.documents:
        counts = Counter(defined_uuids(doc))
        r.evaluated += len(counts)
        for uuid, n in sorted(counts.items()):
            if n > 1:
                r.fail(f"UUID used {n} times.", ref=f"{doc.path.name}:{uuid}", document=doc.kind)
    return r


def schema_valid(ctx: Context) -> CheckResult:
    r = CheckResult(
        "REF-006",
        "Documents are valid against the NIST OSCAL schemas",
        "references",
        Severity.HIGH,
        "Each document must validate against NIST's OSCAL JSON Schema for its model, or tools that "
        "import the package (eMASS, FedRAMP automation, GRC platforms) may reject it.",
    )
    if ctx.schema_dir is None:
        r.skipped_reason = "Schema validation not requested (use --schema-dir)."
        return r
    from ato_readiness_checker.loader import MODELS
    from ato_readiness_checker.schema import schema_for, validate_data

    model_key = {kind: model for model, kind in MODELS.items()}
    for doc in ctx.view.package.documents:
        r.evaluated += 1
        errors = validate_data({model_key[doc.kind]: doc.root}, schema_for(doc.kind, ctx.schema_dir))
        if errors:
            plus = "+" if len(errors) >= 50 else ""
            r.fail(f"{len(errors)}{plus} schema error(s). First: {errors[0]}", ref=doc.path.name, document=doc.kind)
    return r


def oscal_versions(ctx: Context) -> CheckResult:
    r = CheckResult(
        "REF-005",
        "OSCAL versions are declared and consistent",
        "references",
        Severity.LOW,
        "Each document should declare metadata/oscal-version, and the package should use one OSCAL version.",
    )
    docs = ctx.view.package.documents
    versions = {}
    for doc in docs:
        r.evaluated += 1
        v = doc.oscal_version
        if not v:
            r.fail("No metadata/oscal-version.", ref=doc.path.name, document=doc.kind)
        else:
            versions[doc.path.name] = v
    if len(set(versions.values())) > 1:
        detail = ", ".join(f"{name}={v}" for name, v in sorted(versions.items()))
        r.fail(f"Mixed OSCAL versions: {detail}.", ref="package", document="package")
    return r
