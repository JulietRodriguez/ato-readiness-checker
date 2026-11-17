import json
import subprocess
import sys

import pytest

from ato_readiness_checker.cli import checks_markdown, main
from ato_readiness_checker.model import CheckResult, Severity
from ato_readiness_checker.scoring import gate_failed, readiness_level, readiness_score
from tests.conftest import ROOT, SAMPLES, SCHEMAS, package_paths


def args_for(name: str) -> list[str]:
    ssp, ar, poam = package_paths(name)
    return ["check", "--ssp", str(ssp), "--ar", str(ar), "--poam", str(poam), "--as-of", "2026-11-17"]


# --- scoring ----------------------------------------------------------------------------


def make(check_id, severity, evaluated, failed, category="x"):
    r = CheckResult(check_id, "t", category, severity, "d", evaluated=evaluated)
    for n in range(failed):
        r.fail("m", ref=str(n))
    return r


def test_score_weights_by_severity():
    results = [make("A", Severity.CRITICAL, 10, 0), make("B", Severity.LOW, 10, 10)]
    assert readiness_score(results) == round(100 * 10 / 11, 1)


def test_score_ignores_skipped_info_and_risk_checks():
    skipped = make("S", Severity.HIGH, 0, 0)
    skipped.skipped_reason = "n/a"
    results = [
        make("A", Severity.HIGH, 4, 1),
        skipped,
        make("I", Severity.INFO, 5, 5),
        make("R", Severity.HIGH, 5, 5, category="risk"),
    ]
    assert readiness_score(results) == 75.0
    assert readiness_score([skipped]) == 0.0


def test_level_ignores_risk_and_gate_does_not():
    risk = make("R", Severity.HIGH, 1, 1, category="risk")
    assert readiness_level([risk]) == "READY FOR REVIEW"
    assert gate_failed([risk], Severity.HIGH)
    assert not gate_failed([risk], Severity.CRITICAL)
    assert not gate_failed([risk], None)
    assert readiness_level([make("H", Severity.HIGH, 1, 1)]) == "NEEDS WORK"


def test_pass_rate_counts_distinct_refs():
    r = make("A", Severity.LOW, 2, 0)
    r.fail("one", ref="x")
    r.fail("two", ref="x")
    assert r.failed == 1 and r.pass_rate == 0.5


def test_severity_parse():
    assert Severity.parse(" High ") is Severity.HIGH
    with pytest.raises(ValueError, match="choose from"):
        Severity.parse("severe")


# --- CLI --------------------------------------------------------------------------------


def test_cli_clean_package_passes_gate(tmp_path, capsys):
    code = main([*args_for("clean"), "-o", str(tmp_path), "--brief", "--oscal", "--fail-on", "critical"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("READY FOR REVIEW: readiness score 100.0/100")
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == [
        "ao-brief-draft.html",
        "ao-brief-draft.md",
        "readiness-report.html",
        "readiness-report.json",
        "readiness-report.md",
        "readiness-review.oscal.json",
    ]


def test_cli_risk_trips_high_gate_on_clean_package(capsys):
    assert main([*args_for("clean"), "--fail-on", "high", "-q"]) == 1
    assert "at or above 'high'" in capsys.readouterr().err


def test_cli_flawed_package_fails_gate(capsys):
    assert main([*args_for("flawed"), "--fail-on", "critical"]) == 1
    captured = capsys.readouterr()
    assert "NOT READY" in captured.out and "CRITICAL POAM-004" in captured.out


def test_cli_without_gate_exits_zero(capsys):
    assert main(args_for("flawed")) == 0


def test_cli_min_score(capsys):
    assert main([*args_for("flawed"), "--min-score", "99", "-q"]) == 1
    assert "below --min-score" in capsys.readouterr().err
    assert main([*args_for("clean"), "--min-score", "99", "-q"]) == 0


def test_cli_format_and_schema_dir(tmp_path, capsys):
    code = main([*args_for("clean"), "-o", str(tmp_path), "--format", "json", "--schema-dir", str(SCHEMAS), "-q"])
    assert code == 0
    assert [p.name for p in tmp_path.iterdir()] == ["readiness-report.json"]
    data = json.loads((tmp_path / "readiness-report.json").read_text())
    ref006 = next(c for c in data["checks"] if c["check_id"] == "REF-006")
    assert ref006["status"] == "pass"


def test_cli_explicit_baseline(capsys, tmp_path):
    baseline = tmp_path / "b.txt"
    baseline.write_text("ac-2\nac-3\npm-1\n")
    main([*args_for("clean"), "--baseline", str(baseline), "-q"])
    assert "READY FOR REVIEW" not in capsys.readouterr().out  # PM-1 is not in the SSP


@pytest.mark.parametrize(
    "extra",
    [["--as-of", "17/11/2026"], ["--fail-on", "severe"], ["--format", "pdf"], ["--format", ","]],
)
def test_cli_bad_arguments(extra):
    with pytest.raises(SystemExit) as exc:
        main([*args_for("clean"), *extra])
    assert exc.value.code == 2


def test_cli_needs_an_input(capsys):
    assert main(["check"]) == 2
    assert "at least one of" in capsys.readouterr().err


def test_cli_load_error(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    assert main(["check", "--ssp", str(bad)]) == 2
    assert "error:" in capsys.readouterr().err


def test_cli_missing_schema_dir(tmp_path, capsys):
    assert main([*args_for("clean"), "--schema-dir", str(tmp_path)]) == 2
    assert "schema file not found" in capsys.readouterr().err


def test_list_checks(capsys):
    assert main(["list-checks"]) == 0
    out = capsys.readouterr().out
    assert "PKG-001" in out and "RISK-002" in out


def test_docs_checks_md_is_current():
    assert (ROOT / "docs" / "checks.md").read_text(encoding="utf-8") == checks_markdown()


def test_list_checks_markdown(capsys):
    main(["list-checks", "--markdown"])
    assert capsys.readouterr().out == checks_markdown()


def test_module_entry_point():
    proc = subprocess.run(
        [sys.executable, "-m", "ato_readiness_checker", "--version"],
        capture_output=True,
        text=True,
        check=False,
        env={"PYTHONPATH": str(ROOT / "src"), "PATH": ""},
    )
    assert proc.returncode == 0 and proc.stdout.startswith("ato-readiness-checker 0.1.0")


def test_samples_are_up_to_date():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "make_samples.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert (SAMPLES / "outputs" / "flawed" / "ao-brief-draft.md").is_file()
