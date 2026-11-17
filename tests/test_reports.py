import json

import pytest

from ato_readiness_checker.reports import (
    brief_html,
    brief_markdown,
    report_html,
    report_json,
    report_markdown,
    review_to_oscal,
)
from ato_readiness_checker.review import DISCLAIMER
from ato_readiness_checker.schema import validate_data
from tests.conftest import SCHEMAS


def test_json_report_structure(flawed_review):
    d = json.loads(report_json(flawed_review))
    assert d["readiness"]["level"] == "NOT READY"
    assert d["disclaimer"] == DISCLAIMER
    assert d["checks_summary"]["total"] == len(d["checks"]) == 30
    assert d["issue_counts"]["critical"] == 1
    assert d["risk_issue_counts"] == {"critical": 0, "high": 2, "medium": 0, "low": 0, "info": 1}
    assert d["stats"]["poam"]["open_by_severity"]["unknown"] == 1
    assert {row["match"] for row in d["traceability"]} == {"uuid", "control", "none"}
    assert d["baseline"]["controls"] == 22


def test_markdown_report(flawed_review):
    md = report_markdown(flawed_review)
    assert md.startswith("# Authorization Package Readiness Report")
    assert "## Result: NOT READY" in md
    assert DISCLAIMER in md
    assert "## Package issues" in md and "## Risk items for the AO" in md
    assert "| TRC-001 |" in md
    assert "**none**" in md  # an untraced finding


def test_markdown_escapes_table_breakers(clean_review, monkeypatch):
    monkeypatch.setattr(type(clean_review), "system_name", property(lambda self: "A | B\nC"))
    md = report_markdown(clean_review)
    assert "A \\| B C" in md


def test_clean_markdown_says_no_package_issues(clean_review):
    md = report_markdown(clean_review)
    assert "No package issues found." in md
    assert "READY FOR REVIEW" in md


def test_html_report_is_self_contained_and_escaped(clean_docs, write_package):
    clean_docs["ssp"]["system-security-plan"]["system-characteristics"]["system-name"] = "<script>alert(1)</script>"
    review = write_package(clean_docs)
    html = report_html(review)
    assert html.startswith("<!DOCTYPE html>")
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "http" not in html.split("<body>")[0]  # no external assets in <head>


def test_html_report_sections(flawed_review):
    html = report_html(flawed_review)
    assert "NOT READY" in html and "Risk items for the AO" in html
    assert 'class="sev critical"' in html


@pytest.mark.parametrize("render", [brief_markdown, brief_html])
def test_brief_is_marked_draft_and_decides_nothing(flawed_review, render):
    text = render(flawed_review)
    assert "DRAFT FOR HUMAN REVIEW" in text
    assert "not an authorization decision" in text
    assert "Only the Authorizing Official makes the authorization decision" in text
    assert "[x]" not in text.lower()
    assert "Stale privileged accounts" in text  # open High item listed for the AO
    assert "(overdue)" in text
    assert "Weekly (not daily) audit review" in text  # accepted risk listed


def test_brief_markdown_decision_boxes_unchecked(clean_review):
    md = brief_markdown(clean_review)
    assert md.count("- [ ] ") == 3
    assert "Security categorization: **Moderate** (C: Moderate, I: Moderate, A: Low)" in md


def test_brief_truncates_long_lists(clean_docs, write_package):
    poam = clean_docs["poam"]["plan-of-action-and-milestones"]
    template = poam["poam-items"][0]
    for n in range(12):
        poam["poam-items"].append({**template, "uuid": f"00000000-0000-4000-8000-{n:012d}", "title": f"Extra {n}"})
    review = write_package(clean_docs)
    assert "more in the full report" in brief_markdown(review)
    assert "more in the full report" in brief_html(review)


@pytest.mark.parametrize("fixture", ["clean_review", "flawed_review"])
def test_oscal_output_is_schema_valid(request, fixture):
    review = request.getfixturevalue(fixture)
    doc = review_to_oscal(review)
    assert validate_data(doc, SCHEMAS / "oscal_assessment-results_schema.json") == []
    result = doc["assessment-results"]["results"][0]
    props = {p["name"]: p["value"] for p in result["props"]}
    assert props["readiness-level"] == review.level.lower().replace(" ", "-")
    assert doc["assessment-results"]["metadata"]["oscal-version"] == "1.1.2"


def test_oscal_output_is_deterministic(flawed_review):
    a, b = review_to_oscal(flawed_review), review_to_oscal(flawed_review)
    assert a == b
    observations = a["assessment-results"]["results"][0]["observations"]
    ids = [o["props"][0]["value"] for o in observations]
    assert "POAM-004" in ids and "PKG-001" not in ids  # only failing checks become observations
    resources = {r["uuid"] for r in a["assessment-results"]["back-matter"]["resources"]}
    for o in observations:
        assert {s["subject-uuid"] for s in o["subjects"]} <= resources
