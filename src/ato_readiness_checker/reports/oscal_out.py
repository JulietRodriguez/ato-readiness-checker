"""Write the review as OSCAL 1.1.2 Assessment Results.

Why Assessment Results: OSCAL has no "authorization package review" model, and
a readiness review is an examination of documents, which is what an AR result
records. Each failed check becomes an observation (method EXAMINE) whose
subjects are the package documents, listed as back-matter resources. That lets
the next tool in a pipeline read the review in a standard format.

What it is not: this is not the security assessment of the system. The result
title, description and metadata remarks say so, and reviewed-controls is left
as include-all because the review looks at documents, not at controls.

UUIDs are UUIDv5 values derived from the system name, the as-of date and the
check ID, so running the review twice on the same package gives the same file.
"""

from __future__ import annotations

import uuid

from ato_readiness_checker import OSCAL_VERSION, __version__
from ato_readiness_checker.review import DISCLAIMER, Review

NS = "https://github.com/JulietRodriguez/ato-readiness-checker/ns/oscal"
_ROOT = uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/JulietRodriguez/ato-readiness-checker")
CHECKS_DOC = "https://github.com/JulietRodriguez/ato-readiness-checker/blob/main/docs/checks.md"


def _uuid(*parts: str) -> str:
    return str(uuid.uuid5(_ROOT, "|".join(parts)))


def _prop(name: str, value: object) -> dict:
    return {"name": name, "ns": NS, "value": str(value)}


def review_to_oscal(review: Review) -> dict:
    system = review.system_name
    as_of = review.as_of.isoformat()
    seed = (system, as_of)
    docs = review.view.package.documents

    resources = []
    doc_resource: dict[str, str] = {}
    for doc in docs:
        rid = _uuid(*seed, "doc", doc.kind, doc.path.name)
        doc_resource[doc.kind] = doc_resource.get(doc.kind, rid)
        resources.append(
            {
                "uuid": rid,
                "title": doc.title,
                "description": f"Input {doc.kind} reviewed for authorization readiness.",
                "props": [_prop("document-kind", doc.kind)],
                "rlinks": [{"href": doc.path.name, "media-type": "application/oscal+json"}],
            }
        )
    method_id = _uuid(*seed, "method")
    resources.append(
        {
            "uuid": method_id,
            "title": f"ato-readiness-checker {__version__} check catalog",
            "description": "The readiness checks applied in this review. This is not an assessment plan.",
            "rlinks": [{"href": CHECKS_DOC}],
        }
    )
    all_doc_ids = [r["uuid"] for r in resources if r["uuid"] != method_id]

    observations = []
    for check in review.results:
        if check.skipped or not check.issues:
            continue
        kinds = {i.document for i in check.issues}
        subjects = [doc_resource[k] for k in sorted(kinds) if k in doc_resource] or all_doc_ids
        lines = [f"{check.title}. {check.description}", ""]
        for i in check.issues:
            ref = f" {i.ref}:" if i.ref else ""
            lines.append(f"- [{i.severity.value}]{ref} {i.message}")
        observations.append(
            {
                "uuid": _uuid(*seed, "obs", check.check_id),
                "title": f"{check.check_id}: {check.title}",
                "description": "\n".join(lines),
                "props": [
                    _prop("check-id", check.check_id),
                    _prop("check-severity", check.severity.value),
                    _prop("evaluated", check.evaluated),
                    _prop("failed", check.failed),
                ],
                "methods": ["EXAMINE"],
                "types": ["finding"],
                "subjects": [{"subject-uuid": sid, "type": "resource"} for sid in subjects],
                "collected": review.generated_at,
            }
        )

    result = {
        "uuid": _uuid(*seed, "result"),
        "title": "Authorization package readiness review",
        "description": (
            f"Automated completeness and consistency review of the authorization package for {system}. "
            "This is a review of the package documents, not a security control assessment."
        ),
        "start": review.generated_at,
        "end": review.generated_at,
        "props": [
            _prop("readiness-score", review.score),
            _prop("readiness-level", review.level.lower().replace(" ", "-")),
            _prop("as-of", as_of),
        ],
        "reviewed-controls": {
            "control-selections": [
                {
                    "description": "Package-level review; no individual control was tested.",
                    "include-all": {},
                }
            ]
        },
        "remarks": DISCLAIMER,
    }
    if observations:
        result["observations"] = observations

    return {
        "assessment-results": {
            "uuid": _uuid(*seed, "ar"),
            "metadata": {
                "title": f"Authorization package readiness review: {system}",
                "last-modified": review.generated_at,
                "version": __version__,
                "oscal-version": OSCAL_VERSION,
                "props": [_prop("generator", f"ato-readiness-checker {__version__}")],
                "remarks": DISCLAIMER,
            },
            "import-ap": {
                "href": f"#{method_id}",
                "remarks": "No assessment plan applies; this points at the readiness check catalog.",
            },
            "results": [result],
            "back-matter": {"resources": resources},
        }
    }
