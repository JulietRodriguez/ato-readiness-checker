import pytest

from ato_readiness_checker.ids import display_control_id, normalize_control_id, normalize_severity, worst_severity


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("AC-2", "ac-2"),
        ("ac-2", "ac-2"),
        ("AC-02", "ac-2"),
        ("AC-2(1)", "ac-2.1"),
        ("AC-2 (1)", "ac-2.1"),
        ("ac-2.1", "ac-2.1"),
        ("ac-2_smt", "ac-2"),
        ("ac-2_smt.a", "ac-2"),
        ("ac-2_obj", "ac-2"),
        ("ac-17.2_smt", "ac-17.2"),
        ("ia-5.1_smt", "ia-5.1"),
        ("  SC-28  ", "sc-28"),
        ("AC.L2-3.1.1", "ac.l2-3.1.1"),
        ("AC.L2-3.1.1_obj", "ac.l2-3.1.1"),
    ],
)
def test_normalize_control_id(raw, expected):
    assert normalize_control_id(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_normalize_control_id_empty(raw):
    assert normalize_control_id(raw) is None


@pytest.mark.parametrize(("key", "shown"), [("ac-2", "AC-2"), ("ac-2.1", "AC-2(1)"), ("ac.l2-3.1.1", "AC.L2-3.1.1")])
def test_display_control_id(key, shown):
    assert display_control_id(key) == shown


@pytest.mark.parametrize(
    ("raw", "level"),
    [
        ("Critical", "critical"),
        ("very high", "critical"),
        ("High", "high"),
        ("CAT I", "high"),
        ("Category I", "high"),
        ("cat  ii", "moderate"),
        ("Medium", "moderate"),
        ("moderate", "moderate"),
        ("CAT III", "low"),
        ("Informational", "low"),
        ("whatever", None),
        (None, None),
    ],
)
def test_normalize_severity(raw, level):
    assert normalize_severity(raw) == level


def test_worst_severity():
    assert worst_severity(["low", None, "high", "moderate"]) == "high"
    assert worst_severity([None, None]) is None
