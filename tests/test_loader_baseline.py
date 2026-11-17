import json

import pytest

from ato_readiness_checker.baseline import baseline_from_ssp, load_baseline
from ato_readiness_checker.loader import LoadError, load_document, load_package
from tests.conftest import SAMPLES


def write(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return p


# --- loader -------------------------------------------------------------------------


def test_load_document_detects_model():
    doc = load_document(SAMPLES / "clean" / "poam.json")
    assert doc.kind == "poam"
    assert doc.oscal_version == "1.1.2"
    assert "POA&M" in doc.title
    assert doc.label.startswith("poam (")


def test_load_document_accepts_utf8_bom(tmp_path):
    p = tmp_path / "bom.json"
    p.write_bytes(b"\xef\xbb\xbf" + json.dumps({"plan-of-action-and-milestones": {"uuid": "x"}}).encode())
    assert load_document(p).kind == "poam"


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("{not json", "not valid JSON"),
        ("[1, 2]", "JSON object at the top level"),
        ({"catalog": {}}, "OSCAL catalog"),
        ({"hello": 1}, "not an OSCAL SSP"),
        ({"system-security-plan": []}, "must be a JSON object"),
    ],
)
def test_load_document_errors(tmp_path, content, message):
    with pytest.raises(LoadError, match=message):
        load_document(write(tmp_path, "x.json", content))


def test_load_document_missing_file(tmp_path):
    with pytest.raises(LoadError, match="file not found"):
        load_document(tmp_path / "nope.json")


def test_load_document_not_utf8(tmp_path):
    p = tmp_path / "latin.json"
    p.write_bytes(b'{"a": "\xff"}')
    with pytest.raises(LoadError, match="UTF-8"):
        load_document(p)


def test_load_document_wrong_kind():
    with pytest.raises(LoadError, match="expected an OSCAL ssp"):
        load_document(SAMPLES / "clean" / "poam.json", expected="ssp")


def test_load_package_needs_a_document():
    with pytest.raises(LoadError, match="no input documents"):
        load_package()


def test_load_package_multiple_poams():
    p = SAMPLES / "clean" / "poam.json"
    pkg = load_package(None, [], [p, p])
    assert len(pkg.poams) == 2
    assert pkg.ssp is None


# --- baseline -------------------------------------------------------------------------


def test_baseline_from_profile():
    b = load_baseline(SAMPLES / "clean" / "baseline-profile.json")
    assert len(b) == 22
    assert "ia-2.1" in b.controls


def test_baseline_profile_exclude_controls(tmp_path):
    profile = {
        "profile": {
            "imports": [
                {
                    "href": "x",
                    "include-controls": [{"with-ids": ["ac-1", "ac-2", "AC-2(1)"]}],
                    "exclude-controls": [{"with-ids": ["ac-1"]}],
                }
            ]
        }
    }
    assert load_baseline(write(tmp_path, "p.json", profile)).controls == {"ac-2", "ac-2.1"}


def test_baseline_profile_include_all_rejected(tmp_path):
    profile = {"profile": {"imports": [{"href": "x", "include-all": {}}]}}
    with pytest.raises(LoadError, match="include-all"):
        load_baseline(write(tmp_path, "p.json", profile))


def test_baseline_from_catalog(tmp_path):
    catalog = {
        "catalog": {
            "groups": [{"id": "ac", "controls": [{"id": "ac-1"}, {"id": "ac-2", "controls": [{"id": "ac-2.1"}]}]}],
            "controls": [{"id": "pm-1"}],
        }
    }
    assert load_baseline(write(tmp_path, "c.json", catalog)).controls == {"ac-1", "ac-2", "ac-2.1", "pm-1"}


@pytest.mark.parametrize(
    "content",
    [["AC-2", "ac-3", 5], {"controls": ["AC-2", "AC-3"]}, "# my baseline\nAC-2\n\nac-3  # access enforcement\n"],
)
def test_baseline_simple_formats(tmp_path, content):
    name = "b.txt" if isinstance(content, str) else "b.json"
    assert load_baseline(write(tmp_path, name, content)).controls == {"ac-2", "ac-3"}


@pytest.mark.parametrize(
    ("content", "message"),
    [("{broken", "not valid JSON"), ({"foo": 1}, "unrecognized"), ("# nothing\n", "no control IDs")],
)
def test_baseline_errors(tmp_path, content, message):
    with pytest.raises(LoadError, match=message):
        load_baseline(write(tmp_path, "b.json", content))


def test_baseline_missing_file(tmp_path):
    with pytest.raises(LoadError, match="not found"):
        load_baseline(tmp_path / "none.txt")


def test_baseline_from_ssp_follows_local_import_profile():
    ssp = load_document(SAMPLES / "clean" / "ssp.json")
    b = baseline_from_ssp(ssp)
    assert b is not None and len(b) == 22


def _ssp_with_href(tmp_path, href, back_matter=None):
    root = {"import-profile": {"href": href}}
    if back_matter:
        root["back-matter"] = back_matter
    return load_document(write(tmp_path, "ssp.json", {"system-security-plan": root}))


def test_baseline_from_ssp_ignores_remote_and_missing(tmp_path):
    assert baseline_from_ssp(_ssp_with_href(tmp_path, "https://example.com/profile.json")) is None
    assert baseline_from_ssp(_ssp_with_href(tmp_path, "missing.json")) is None
    assert baseline_from_ssp(_ssp_with_href(tmp_path, "")) is None


def test_baseline_from_ssp_back_matter_reference(tmp_path):
    write(tmp_path, "base.txt", "ac-2\n")
    rid = "11111111-1111-4111-8111-111111111111"
    bm = {"resources": [{"uuid": rid, "rlinks": [{"href": "base.txt"}]}]}
    b = baseline_from_ssp(_ssp_with_href(tmp_path, f"#{rid}", bm))
    assert b is not None and b.controls == {"ac-2"}
