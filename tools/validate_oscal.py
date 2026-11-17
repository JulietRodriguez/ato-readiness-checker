"""Validate OSCAL JSON files against NIST's OSCAL 1.1.2 JSON schemas.

Usage:
    python tools/validate_oscal.py --schema-dir schemas FILE [FILE ...]

The model (SSP, Assessment Results, POA&M, profile) is detected from each
file's top-level key and the matching schema is picked from --schema-dir.
Exits 1 if any file is invalid. See src/ato_readiness_checker/schema.py for why
two Unicode regex classes are translated before validating.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ato_readiness_checker.schema import validate_data

SCHEMAS = {
    "system-security-plan": "oscal_ssp_schema.json",
    "assessment-results": "oscal_assessment-results_schema.json",
    "plan-of-action-and-milestones": "oscal_poam_schema.json",
    "profile": "oscal_profile_schema.json",
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--schema-dir", required=True)
    ap.add_argument("files", nargs="+")
    args = ap.parse_args(argv)
    failed = 0
    for name in args.files:
        data = json.loads(Path(name).read_text(encoding="utf-8"))
        model = next((m for m in SCHEMAS if m in data), None)
        if model is None:
            print(f"FAIL {name}: not an OSCAL SSP, Assessment Results, POA&M or profile")
            failed += 1
            continue
        schema = Path(args.schema_dir) / SCHEMAS[model]
        errors = validate_data(data, schema)
        if errors:
            failed += 1
            print(f"FAIL {name}: {len(errors)} error(s) against {schema.name}")
            for err in errors[:20]:
                print(f"     {err}")
        else:
            print(f"OK   {name}: valid OSCAL {model} per {schema.name}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
