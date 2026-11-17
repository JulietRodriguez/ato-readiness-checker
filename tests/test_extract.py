from datetime import date

import pytest

from ato_readiness_checker.extract import _combine_status, build_poam_items, parse_date, props
from ato_readiness_checker.loader import Document
from tests.conftest import SAMPLES


def poam_doc(items, risks=(), findings=(), parties=()):
    from pathlib import Path

    root = {
        "metadata": {"title": "t", "parties": list(parties)},
        "poam-items": list(items),
        "risks": list(risks),
        "findings": list(findings),
    }
    return Document(kind="poam", path=Path("p.json"), root=root)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-11-17", date(2026, 11, 17)),
        ("2026-11-17T23:59:59Z", date(2026, 11, 17)),
        ("2026-11-17T23:59:59+00:00", date(2026, 11, 17)),
        ("2026-11-17 garbage", date(2026, 11, 17)),
        ("2026-13-45", None),
        ("soon", None),
        (None, None),
    ],
)
def test_parse_date(value, expected):
    assert parse_date(value) == expected


def test_props_matches_any_namespace_case_insensitive():
    obj = {"props": [{"name": "Severity", "ns": "https://x", "value": " High "}, {"name": "other", "value": "x"}]}
    assert props(obj, "severity") == ["High"]


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([], "unknown"),
        (["closed", "closed"], "closed"),
        (["closed", "deviation-approved"], "deviation-approved"),
        (["remediating", "open"], "open"),
        (["closed", "remediating"], "remediating"),
        (["bogus"], "unknown"),
    ],
)
def test_combine_status(values, expected):
    assert _combine_status(values) == expected


def test_poc_from_task_responsible_roles_and_remediation_origins():
    parties = [{"uuid": "p1", "type": "person", "name": "Owner A"}, {"uuid": "p2", "type": "person", "name": "B"}]
    risk = {
        "uuid": "r1",
        "status": "open",
        "remediations": [
            {
                "origins": [{"actors": [{"type": "party", "actor-uuid": "p2"}, {"type": "tool", "actor-uuid": "t"}]}],
                "tasks": [
                    {
                        "type": "action",
                        "title": "parent",
                        "responsible-roles": [{"role-id": "isso", "party-uuids": ["p1"]}],
                        "tasks": [
                            {
                                "type": "milestone",
                                "title": "nested",
                                "timing": {"within-date-range": {"start": "2026-01-01", "end": "2026-02-01T00:00:00Z"}},
                            }
                        ],
                    }
                ],
            }
        ],
    }
    item = {"uuid": "i1", "title": "x", "related-risks": [{"risk-uuid": "r1"}]}
    (parsed,) = build_poam_items(poam_doc([item], [risk], parties=parties))
    assert parsed.pocs == ["B", "Owner A"]
    assert [(m.title, m.due) for m in parsed.milestones] == [("nested", date(2026, 2, 1))]
    assert parsed.status == "open"


def test_severity_from_risk_characterization_facets():
    risk = {
        "uuid": "r1",
        "status": "open",
        "characterizations": [{"facets": [{"name": "risk", "system": "https://x", "value": "moderate"}]}],
    }
    item = {"uuid": "i1", "title": "x", "related-risks": [{"risk-uuid": "r1"}]}
    (parsed,) = build_poam_items(poam_doc([item], [risk]))
    assert parsed.severity == "moderate"


def test_controls_from_local_findings_and_props():
    finding = {
        "uuid": "f1",
        "target": {"target-id": "ac-17.2_smt"},
        "related-observations": [{"observation-uuid": "o1"}],
    }
    item = {
        "uuid": "i1",
        "title": "x",
        "related-findings": [{"finding-uuid": "f1"}, {"finding-uuid": "elsewhere"}],
        "props": [{"name": "related-control", "value": "SC-13; SC-8"}],
    }
    (parsed,) = build_poam_items(poam_doc([item], findings=[finding]))
    assert parsed.keys == {"ac-17.2", "sc-13", "sc-8"}
    assert parsed.observation_uuids == ["o1"]
    assert parsed.controls_display == "AC-17(2), SC-13, SC-8"
    assert parsed.status == "unknown"
    assert parsed.is_open


def test_untitled_item_and_label():
    (parsed,) = build_poam_items(poam_doc([{"description": "d"}]))
    assert parsed.title == "(untitled POA&M item)"
    assert parsed.label == "(untitled POA&M item)"
    assert parsed.controls_display == "(no control)"


def test_clean_sample_items_parse(clean_review):
    by_title = {i.title: i for i in clean_review.view.poam_items}
    ac2 = by_title["Stale privileged accounts"]
    assert ac2.severity == "high" and ac2.status == "remediating" and ac2.deadline == date(2027, 1, 15)
    assert ac2.pocs == ["ISSO, CMS-DEMO (synthetic)"]  # from item origins
    assert len(ac2.milestones) == 2
    assert by_title["Weekly (not daily) audit review: risk accepted"].is_accepted
    assert by_title["TLS 1.0 enabled on legacy endpoint (closed)"].is_closed
    assert by_title["Automated component inventory not yet in place"].pocs == ["ISSO, CMS-DEMO (synthetic)"]


def test_ssp_effective_status_prefers_requirement_level(clean_review):
    controls = clean_review.view.ssp.controls
    assert controls["ac-2"].effective_status == "partial"
    assert controls["ac-18"].effective_status == "not-applicable"
    assert controls["ac-2"].display == "AC-2"
    assert clean_review.view.ssp.system_name.startswith("SYNTHETIC")
    assert (SAMPLES / "clean" / "ssp.json").is_file()
