"""The checker reads what Juliet's other OSCAL tools write (see fixtures/compat/README.md)."""

from datetime import date

from ato_readiness_checker.extract import build_ar_view, build_poam_items, build_ssp_view
from ato_readiness_checker.loader import load_document, load_package
from ato_readiness_checker.review import run_review
from tests.conftest import COMPAT, check


def test_oscal_ssp_generator_ssp():
    view = build_ssp_view(load_document(COMPAT / "oscal-ssp-generator_ssp.json", expected="ssp"))
    assert len(view.controls) == 21
    assert view.controls["ac-2"].effective_status == "implemented"  # uppercase "AC-2" normalized
    assert view.controls["cm-8"].effective_status == "planned"
    assert all(c.statement_texts or c.remarks for c in view.controls.values())
    assert view.system_name == "Sample AWS Environment"


def test_fedramp_control_validator_ar():
    ar = build_ar_view([load_document(COMPAT / "fedramp-control-validator_ar.json")])
    assert len(ar.findings) == 29
    assert {f.state for f in ar.findings} == {"satisfied", "not-satisfied"}
    ac2 = next(f for f in ar.findings if f.target_id == "ac-2_obj")
    assert ac2.key == "ac-2" and ac2.state == "not-satisfied"
    assert len(ar.reviewed_keys) > 0


def test_cmmc_scorecard_ar_practice_ids():
    ar = build_ar_view([load_document(COMPAT / "cmmc-scorecard_ar.json")])
    assert len(ar.findings) == 102
    assert ar.findings[0].key == "ac.l2-3.1.1"
    assert ar.findings[0].display == "AC.L2-3.1.1"


def test_poam_generator_poam():
    items = build_poam_items(load_document(COMPAT / "poam-generator_poam.json"))
    assert len(items) == 5
    first = items[0]
    assert first.severity == "critical"
    assert first.keys == {"ac-2"}
    assert first.pocs == ["Jane Smith, ISSO"]  # point-of-contact prop in poam-generator's namespace
    assert len(first.milestones) == 4
    assert first.status == "remediating"
    assert {i.status for i in items} == {"open", "remediating", "deviation-approved"}


def test_stig_poam_builder_poam():
    items = build_poam_items(load_document(COMPAT / "stig-poam-builder_poam.json"))
    assert len(items) == 15
    fips = next(i for i in items if "FIPS-validated" in i.title)
    assert fips.severity == "high"  # CAT I
    assert fips.keys == {"ac-17.2", "sc-13"}
    assert fips.deadline == date(2026, 12, 17)
    assert fips.milestones == [] and fips.pocs == []  # left for the ISSO to fill in


def test_full_review_of_mixed_tool_outputs():
    pkg = load_package(
        COMPAT / "oscal-ssp-generator_ssp.json",
        [COMPAT / "fedramp-control-validator_ar.json"],
        [COMPAT / "poam-generator_poam.json", COMPAT / "stig-poam-builder_poam.json"],
    )
    review = run_review(pkg, as_of=date(2026, 11, 17))
    assert len(review.view.poam_items) == 20
    assert check(review, "REF-001").issues == []  # every internal reference resolves
    assert check(review, "REF-004").issues == []
    assert len(check(review, "REF-003").issues) == 2  # sample systems differ, as expected
    # The SSP generator writes placeholder boundary text; the checker should flag it.
    assert [i.ref for i in check(review, "SSP-004").issues] == ["Authorization boundary"]
