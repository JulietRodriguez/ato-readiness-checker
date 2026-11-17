from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path

import pytest

from ato_readiness_checker.loader import load_package
from ato_readiness_checker.review import run_review

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
SCHEMAS = ROOT / "schemas"
COMPAT = Path(__file__).parent / "fixtures" / "compat"
AS_OF = date(2026, 11, 17)


def package_paths(name: str) -> tuple[Path, Path, Path]:
    d = SAMPLES / name
    return d / "ssp.json", d / "assessment-results.json", d / "poam.json"


def review_of(name: str, **kwargs):
    ssp, ar, poam = package_paths(name)
    return run_review(load_package(ssp, [ar], [poam]), as_of=kwargs.pop("as_of", AS_OF), **kwargs)


@pytest.fixture(scope="session")
def clean_review():
    return review_of("clean")


@pytest.fixture(scope="session")
def flawed_review():
    return review_of("flawed")


@pytest.fixture
def clean_docs() -> dict:
    """Fresh, editable copies of the clean package documents."""
    ssp, ar, poam = package_paths("clean")
    return {
        "ssp": json.loads(ssp.read_text(encoding="utf-8")),
        "ar": json.loads(ar.read_text(encoding="utf-8")),
        "poam": json.loads(poam.read_text(encoding="utf-8")),
        "baseline": json.loads((SAMPLES / "clean" / "baseline-profile.json").read_text(encoding="utf-8")),
    }


@pytest.fixture
def write_package(tmp_path):
    """Write (possibly edited) documents to tmp_path and review them."""

    def _write(docs: dict, *, include=("ssp", "ar", "poam"), **kwargs):
        paths = {}
        for key, name in (("ssp", "ssp.json"), ("ar", "assessment-results.json"), ("poam", "poam.json")):
            if key in include and key in docs:
                p = tmp_path / name
                p.write_text(json.dumps(docs[key]), encoding="utf-8")
                paths[key] = p
        if "baseline" in docs:
            (tmp_path / "baseline-profile.json").write_text(json.dumps(docs["baseline"]), encoding="utf-8")
        pkg = load_package(
            paths.get("ssp"), [paths["ar"]] if "ar" in paths else [], [paths["poam"]] if "poam" in paths else []
        )
        return run_review(pkg, as_of=kwargs.pop("as_of", AS_OF), **kwargs)

    return _write


def check(review, check_id: str):
    return next(r for r in review.results if r.check_id == check_id)


def deep(doc: dict) -> dict:
    return copy.deepcopy(doc)
