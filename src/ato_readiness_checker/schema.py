"""Validate OSCAL JSON against NIST's published OSCAL JSON Schemas (optional).

Needs the ``jsonschema`` package (``pip install "ato-readiness-checker[schema]"``)
and the schema files from the OSCAL v1.1.2 GitHub release:
``oscal_ssp_schema.json``, ``oscal_assessment-results_schema.json`` and
``oscal_poam_schema.json``.

NIST's schemas use Unicode property escapes (``\\p{L}`` letters, ``\\p{N}``
numbers) in token patterns. Python's ``re`` module, which jsonschema uses,
doesn't support them, so those two classes are translated to equivalent
``re`` classes before validating. Every other keyword is used as published.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SCHEMA_FILES = {
    "ssp": "oscal_ssp_schema.json",
    "assessment-results": "oscal_assessment-results_schema.json",
    "poam": "oscal_poam_schema.json",
}
_REWRITES = {r"\p{L}": r"[^\W\d_]", r"\p{N}": r"\d"}


class SchemaUnavailable(RuntimeError):
    """jsonschema is not installed or a schema file is missing."""


def _rewrite(node: Any) -> Any:
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key == "pattern" and isinstance(value, str):
                for src, dst in _REWRITES.items():
                    value = value.replace(src, dst)
            out[key] = _rewrite(value)
        return out
    if isinstance(node, list):
        return [_rewrite(v) for v in node]
    return node


@lru_cache(maxsize=8)
def _validator(schema_path: str):
    try:
        from jsonschema import Draft7Validator
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise SchemaUnavailable(
            "schema validation needs jsonschema: pip install 'ato-readiness-checker[schema]'"
        ) from exc
    path = Path(schema_path)
    if not path.is_file():
        raise SchemaUnavailable(f"schema file not found: {path}")
    schema = _rewrite(json.loads(path.read_text(encoding="utf-8")))
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema)


def validate_data(data: dict, schema_path: str | Path, limit: int = 50) -> list[str]:
    """Return up to ``limit`` human-readable schema errors (empty list = valid)."""
    validator = _validator(str(Path(schema_path).resolve()))
    errors = sorted(validator.iter_errors(data), key=lambda err: [str(p) for p in err.absolute_path])
    return [f"{'/'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message[:300]}" for err in errors[:limit]]


def schema_for(kind: str, schema_dir: str | Path) -> Path:
    return Path(schema_dir) / SCHEMA_FILES[kind]
