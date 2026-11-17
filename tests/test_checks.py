"""Each check, driven by the synthetic clean and flawed packages plus targeted edits."""

import pytest

from ato_readiness_checker.checks import check_catalog
from ato_readiness_checker.model import Severity
from tests.conftest import check, deep


def test_clean_package_has_no_package_issues(clean_review):
    package_issues = [i for r in clean_review.results if r.counts_toward_readiness for i in r.issues]
    assert package_issues == []
    assert clean_review.level == "READY FOR REVIEW"
    assert clean_review.score == 100.0


def test_clean_package_still_reports_risk(clean_review):
    risk = check(clean_review, "RISK-001")
    assert sorted(i.ref.split(" [")[0] for i in risk.issues) == [
        "High-severity patches past due",
        "Stale privileged accounts",
    ]
    assert all(i.severity is Severity.HIGH for i in risk.issues)
    assert len(check(clean_review, "RISK-002").issues) == 1


def test_clean_package_checks_that_need_extras_are_skipped(clean_review):
    skipped = {r.check_id for r in clean_review.results if r.skipped}
    assert skipped == {"REF-006"}  # schema validation is opt-in


# Every deliberate defect in samples/flawed, and the reference the check should report.
EXPECTED_FLAWS = {
    "SSP-001": ["Data flow"],
    "SSP-002": ["confidentiality"],
    "SSP-003": ["Authorizing Official"],
    "SSP-004": ["Authorization boundary"],
    "CTRL-001": ["IA-2(1)"],
    "CTRL-002": ["AU-9"],
    "CTRL-003": ["CP-9"],
    "CTRL-004": ["IA-5", "SI-2"],
    "CTRL-005": ["CM-8"],
    "CTRL-006": ["AC-18"],
    "AR-002": ["SC-28"],
    "AR-003": ["results"],
    "TRC-001": ["CM-8", "IA-5"],
    "TRC-002": ["Legacy finding carried from a prior audit"],
    "POAM-001": ["Database tier scanned without credentials"],
    "POAM-002": ["Container settings deviate from hardening baseline"],
    "POAM-003": ["High-severity patches past due"],
    "POAM-004": ["Stale privileged accounts"],
    "POAM-005": ["Legacy finding carried from a prior audit"],
    "POAM-006": ["Legacy finding carried from a prior audit"],
    "REF-002": [None],
    "REF-003": ["poam.json"],
    "REF-004": [None],
    "REF-005": ["package"],
    "REF-001": [None],
}


@pytest.mark.parametrize(("check_id", "refs"), sorted(EXPECTED_FLAWS.items()))
def test_flawed_package_defect_is_caught(flawed_review, check_id, refs):
    result = check(flawed_review, check_id)
    assert not result.skipped
    got = sorted(i.ref.split(" [")[0] for i in result.issues)
    if refs == [None]:
        assert len(got) == 1
    else:
        assert got == refs


def test_flawed_package_has_no_unexpected_failures(flawed_review):
    failing = {r.check_id for r in flawed_review.results if r.issues and r.counts_toward_readiness}
    assert failing == set(EXPECTED_FLAWS)


def test_flawed_package_is_not_ready(flawed_review):
    assert flawed_review.level == "NOT READY"
    overdue = check(flawed_review, "POAM-004").issues[0]
    assert overdue.severity is Severity.CRITICAL  # overdue High item is raised to critical
    assert "47 days overdue" in overdue.message


def test_flawed_documents_are_still_schema_valid(flawed_review, tmp_path):
    from ato_readiness_checker.extract import build_view  # noqa: F401  (import check only)
    from tests.conftest import SCHEMAS, review_of

    r = check(review_of("flawed", schema_dir=SCHEMAS), "REF-006")
    assert r.evaluated == 3 and r.issues == []


def test_check_ids_are_unique_and_documented():
    catalog = check_catalog()
    ids = [c.check_id for c in catalog]
    assert len(ids) == len(set(ids)) == 30
    assert all(c.title and c.description for c in catalog)


# --- targeted edits on the clean package ---------------------------------------------


def test_missing_documents(clean_docs, write_package):
    r = write_package(clean_docs, include=("poam",))
    pkg = check(r, "PKG-001")
    assert sorted(i.ref for i in pkg.issues) == ["Assessment Results", "SSP"]
    for cid in ("SSP-001", "CTRL-002", "AR-001", "TRC-001", "CTRL-004", "REF-003"):
        assert check(r, cid).skipped, cid


def test_missing_poam(clean_docs, write_package):
    r = write_package(clean_docs, include=("ssp", "ar"))
    assert [i.ref for i in check(r, "PKG-001").issues] == ["POA&M"]
    assert check(r, "POAM-001").skipped_reason == "No POA&M supplied."
    assert check(r, "TRC-002").skipped
    # planned/partial controls now have nothing tracking them
    assert len(check(r, "CTRL-005").issues) == 6  # five partial + one planned


def test_missing_system_characteristics_is_critical(clean_docs, write_package):
    del clean_docs["ssp"]["system-security-plan"]["system-characteristics"]
    r = write_package(clean_docs)
    sevs = {i.ref: i.severity for i in check(r, "SSP-001").issues}
    assert sevs["System characteristics"] is Severity.CRITICAL
    assert check(r, "SSP-002").skipped


def test_impact_level_missing_one_objective(clean_docs, write_package):
    chars = clean_docs["ssp"]["system-security-plan"]["system-characteristics"]
    del chars["security-impact-level"]["security-objective-availability"]
    r = write_package(clean_docs)
    assert any("availability" in i.message for i in check(r, "SSP-001").issues)
    assert any("availability" in i.message for i in check(r, "SSP-002").issues)


def test_sensitivity_level_must_match_high_water(clean_docs, write_package):
    chars = clean_docs["ssp"]["system-security-plan"]["system-characteristics"]
    chars["security-sensitivity-level"] = "fips-199-high"
    r = write_package(clean_docs)
    issue = check(r, "SSP-002").issues[0]
    assert issue.ref == "security-sensitivity-level" and issue.severity is Severity.MEDIUM


def test_info_type_without_impact(clean_docs, write_package):
    it = clean_docs["ssp"]["system-security-plan"]["system-characteristics"]["system-information"]
    it["information-types"][0]["integrity-impact"] = {"base": "extreme"}
    r = write_package(clean_docs)
    assert any("no valid integrity impact" in i.message for i in check(r, "SSP-002").issues)


def test_selected_impact_overrides_base(clean_docs, write_package):
    it = clean_docs["ssp"]["system-security-plan"]["system-characteristics"]["system-information"]
    it["information-types"][0]["availability-impact"] = {"base": "fips-199-low", "selected": "fips-199-high"}
    r = write_package(clean_docs)
    assert any("Availability is categorized low" in i.message for i in check(r, "SSP-002").issues)


def _req(docs, cid):
    reqs = docs["ssp"]["system-security-plan"]["control-implementation"]["implemented-requirements"]
    return next(x for x in reqs if x["control-id"] == cid)


def test_status_missing_and_invalid(clean_docs, write_package):
    ac3 = _req(clean_docs, "ac-3")
    ac3["props"] = []
    for bc in ac3["by-components"]:
        del bc["implementation-status"]
    _req(clean_docs, "ac-6")["props"][0]["value"] = "mostly-done"
    r = write_package(clean_docs)
    msgs = {i.ref: i.message for i in check(r, "CTRL-003").issues}
    assert msgs["AC-3"] == "No implementation status."
    assert "mostly-done" in msgs["AC-6"]


@pytest.mark.parametrize(
    ("requirement", "components", "fragment"),
    [
        (["implemented", "partial"], ["implemented"], "more than one status"),
        (["planned"], ["implemented"], "every component is implemented"),
        (["not-applicable"], ["implemented"], "not-applicable but a component"),
    ],
)
def test_status_conflicts(clean_docs, write_package, requirement, components, fragment):
    req = _req(clean_docs, "ac-3")
    req["props"] = [{"name": "implementation-status", "value": v} for v in requirement]
    req["by-components"][0]["implementation-status"]["state"] = components[0]
    r = write_package(clean_docs)
    assert any(fragment in i.message for i in check(r, "CTRL-003").issues)


def test_satisfied_but_ssp_says_planned_is_low(clean_docs, write_package):
    req = _req(clean_docs, "ac-3")
    req["props"][0]["value"] = "planned"
    req["by-components"][0]["implementation-status"]["state"] = "planned"
    r = write_package(clean_docs)
    issue = next(i for i in check(r, "CTRL-004").issues if i.ref == "AC-3")
    assert issue.severity is Severity.LOW


def test_ar_without_results_or_findings(clean_docs, write_package):
    result = clean_docs["ar"]["assessment-results"]["results"][0]
    del result["findings"]
    r = write_package(clean_docs)
    assert check(r, "AR-001").issues[0].severity is Severity.HIGH
    clean_docs["ar"]["assessment-results"]["results"] = []
    r = write_package(clean_docs)
    assert check(r, "AR-001").issues[0].severity is Severity.CRITICAL
    assert check(r, "AR-003").issues[0].message.startswith("No assessment start or end dates")


def test_controls_assessed_uses_ssp_when_no_baseline(clean_docs, write_package):
    clean_docs["ssp"]["system-security-plan"]["import-profile"]["href"] = "https://example.com/p.json"
    r = write_package(clean_docs)
    assert check(r, "CTRL-001").skipped
    assert check(r, "AR-002").evaluated == 22  # SSP controls stand in for the baseline


def test_assessment_age_is_configurable(write_package, clean_docs):
    r = write_package(clean_docs, max_assessment_age_days=30)
    assert "days before 2026-11-17" in check(r, "AR-003").issues[0].message


def test_trace_by_uuid_observation_and_control(clean_review):
    methods = {row.finding.display: row.method for row in clean_review.trace}
    assert methods["AC-2"] == "uuid"  # related-findings -> AR finding UUID
    assert methods["SI-2"] == "uuid"  # related-observations -> AR observation UUID
    assert methods["CM-6"] == "control"  # POA&M-local finding on the same control


def test_poam_milestone_without_date_is_low(clean_docs, write_package):
    risk = clean_docs["poam"]["plan-of-action-and-milestones"]["risks"][0]
    del risk["remediations"][0]["tasks"][0]["timing"]
    r = write_package(clean_docs)
    issue = check(r, "POAM-002").issues[0]
    assert issue.severity is Severity.LOW and "no date" in issue.message


def test_open_critical_weakness_is_critical_risk(clean_docs, write_package):
    for risk in clean_docs["poam"]["plan-of-action-and-milestones"]["risks"]:
        if risk["title"] == "Stale privileged accounts":
            risk["props"][0]["value"] = "Critical"
    for item in clean_docs["poam"]["plan-of-action-and-milestones"]["poam-items"]:
        item["props"] = [p for p in item["props"] if p["name"] != "severity"]
    r = write_package(clean_docs)
    sevs = sorted(i.severity.value for i in check(r, "RISK-001").issues)
    assert sevs == ["critical", "high"]
    assert r.level == "READY FOR REVIEW"  # risk does not change package readiness


def test_poam_status_and_deadline_from_props(clean_docs, write_package):
    poam = clean_docs["poam"]["plan-of-action-and-milestones"]
    item = poam["poam-items"][0]
    del item["related-risks"]
    item["props"] += [
        {"name": "poam-status", "value": "Ongoing"},
        {"name": "scheduled-completion-date", "value": "2026-01-01"},
    ]
    r = write_package(clean_docs)
    overdue = [i.ref for i in check(r, "POAM-004").issues]
    assert any(ref.startswith(item["title"]) for ref in overdue)


def test_unique_uuid_and_version_checks(clean_docs, write_package):
    del clean_docs["poam"]["plan-of-action-and-milestones"]["metadata"]["oscal-version"]
    r = write_package(clean_docs)
    assert [i.message for i in check(r, "REF-005").issues] == ["No metadata/oscal-version."]


def test_poam_without_system_id(clean_docs, write_package):
    del clean_docs["poam"]["plan-of-action-and-milestones"]["system-id"]
    r = write_package(clean_docs)
    assert check(r, "REF-003").issues[0].message == "POA&M has no system-id."


def test_href_fragment_must_resolve(clean_docs, write_package):
    clean_docs["ar"]["assessment-results"]["import-ap"]["href"] = "#00000000-0000-4000-8000-000000000000"
    r = write_package(clean_docs)
    assert any("href does not resolve" in i.message for i in check(r, "REF-001").issues)


def test_schema_check_reports_invalid_document(clean_docs, write_package):
    from tests.conftest import SCHEMAS

    del clean_docs["poam"]["plan-of-action-and-milestones"]["metadata"]["title"]
    r = write_package(clean_docs, schema_dir=SCHEMAS)
    issue = check(r, "REF-006").issues[0]
    assert issue.ref == "poam.json" and "'title' is a required property" in issue.message


def test_deep_helper_is_a_copy(clean_docs):
    copy = deep(clean_docs)
    copy["ssp"]["x"] = 1
    assert "x" not in clean_docs["ssp"]
