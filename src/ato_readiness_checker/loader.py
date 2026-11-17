"""Load OSCAL JSON documents and sort them into an authorization package."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MODELS = {
    "system-security-plan": "ssp",
    "assessment-results": "assessment-results",
    "plan-of-action-and-milestones": "poam",
}

# A real SSP for a large system can be tens of MB; refuse anything absurd.
MAX_BYTES = 200 * 1024 * 1024


class LoadError(ValueError):
    """Raised when an input file is not a usable OSCAL JSON document."""


@dataclass
class Document:
    kind: str  # ssp / assessment-results / poam
    path: Path
    root: dict[str, Any]  # the object under the model key

    @property
    def label(self) -> str:
        return f"{self.kind} ({self.path.name})"

    @property
    def title(self) -> str:
        return str(self.root.get("metadata", {}).get("title", self.path.name))

    @property
    def oscal_version(self) -> str | None:
        return self.root.get("metadata", {}).get("oscal-version")


@dataclass
class Package:
    ssp: Document | None = None
    assessment_results: list[Document] = field(default_factory=list)
    poams: list[Document] = field(default_factory=list)

    @property
    def documents(self) -> list[Document]:
        docs: list[Document] = []
        if self.ssp is not None:
            docs.append(self.ssp)
        docs.extend(self.assessment_results)
        docs.extend(self.poams)
        return docs


def load_document(path: str | Path, expected: str | None = None) -> Document:
    p = Path(path)
    if not p.is_file():
        raise LoadError(f"{p}: file not found")
    if p.stat().st_size > MAX_BYTES:
        raise LoadError(f"{p}: file is larger than {MAX_BYTES // (1024 * 1024)} MB")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise LoadError(f"{p}: not valid JSON ({exc.msg} at line {exc.lineno})") from exc
    except UnicodeDecodeError as exc:
        raise LoadError(f"{p}: not UTF-8 text") from exc
    if not isinstance(data, dict):
        raise LoadError(f"{p}: expected a JSON object at the top level")
    found = [key for key in MODELS if key in data]
    if not found:
        if "catalog" in data or "profile" in data or "component-definition" in data:
            raise LoadError(f"{p}: this is an OSCAL {next(iter(data))}, not an SSP, AR or POA&M")
        raise LoadError(
            f"{p}: not an OSCAL SSP, Assessment Results or POA&M "
            "(expected a top-level 'system-security-plan', 'assessment-results' or "
            "'plan-of-action-and-milestones' key; only OSCAL JSON is supported)"
        )
    model = found[0]
    kind = MODELS[model]
    if expected and kind != expected:
        raise LoadError(f"{p}: expected an OSCAL {expected} but found {model}")
    root = data[model]
    if not isinstance(root, dict):
        raise LoadError(f"{p}: '{model}' must be a JSON object")
    return Document(kind=kind, path=p, root=root)


def load_package(
    ssp: str | Path | None = None,
    assessment_results: list[str | Path] | None = None,
    poams: list[str | Path] | None = None,
) -> Package:
    pkg = Package()
    if ssp:
        pkg.ssp = load_document(ssp, expected="ssp")
    for ar in assessment_results or []:
        pkg.assessment_results.append(load_document(ar, expected="assessment-results"))
    for poam in poams or []:
        pkg.poams.append(load_document(poam, expected="poam"))
    if not pkg.documents:
        raise LoadError("no input documents given")
    return pkg
