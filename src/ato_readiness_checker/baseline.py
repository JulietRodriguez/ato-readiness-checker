"""Load the list of controls the system must address (its baseline).

Accepted formats:

* An OSCAL profile (JSON) -- the controls named in ``imports[].include-controls[].with-ids``
  minus any ``exclude-controls``. A profile that uses ``include-all`` can't be
  resolved without its catalog, so it is rejected with a clear message.
* An OSCAL catalog (JSON) -- every control and enhancement in it.
* A JSON list of control IDs, or ``{"controls": [...]}``.
* A text file with one control ID per line (``#`` starts a comment).

Any spelling works (``AC-2(1)``, ``ac-2.1``); IDs are normalized.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ato_readiness_checker.ids import normalize_control_id
from ato_readiness_checker.loader import Document, LoadError


@dataclass(frozen=True)
class Baseline:
    controls: frozenset[str]
    source: str

    def __len__(self) -> int:
        return len(self.controls)


def _ids(values: list[Any]) -> set[str]:
    out = set()
    for v in values:
        key = normalize_control_id(v if isinstance(v, str) else None)
        if key:
            out.add(key)
    return out


def _from_profile(profile: dict[str, Any], source: str) -> set[str]:
    include: set[str] = set()
    exclude: set[str] = set()
    for imp in profile.get("imports", []):
        if "include-all" in imp:
            raise LoadError(
                f"{source}: profile uses include-all, which needs the source catalog to resolve; "
                "pass a resolved profile catalog or a plain control list instead"
            )
        for sel in imp.get("include-controls", []):
            include |= _ids(sel.get("with-ids", []))
        for sel in imp.get("exclude-controls", []):
            exclude |= _ids(sel.get("with-ids", []))
    return include - exclude


def _from_catalog(catalog: dict[str, Any]) -> set[str]:
    out: set[str] = set()

    def walk(node: dict[str, Any]) -> None:
        for control in node.get("controls", []):
            key = normalize_control_id(control.get("id"))
            if key:
                out.add(key)
            walk(control)
        for group in node.get("groups", []):
            walk(group)

    walk(catalog)
    return out


def load_baseline(path: str | Path) -> Baseline:
    p = Path(path)
    if not p.is_file():
        raise LoadError(f"{p}: baseline file not found")
    text = p.read_text(encoding="utf-8-sig")
    stripped = text.lstrip()
    if stripped.startswith(("{", "[")):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LoadError(f"{p}: not valid JSON ({exc.msg})") from exc
        if isinstance(data, list):
            controls = _ids(data)
        elif isinstance(data, dict) and "profile" in data:
            controls = _from_profile(data["profile"], str(p))
        elif isinstance(data, dict) and "catalog" in data:
            controls = _from_catalog(data["catalog"])
        elif isinstance(data, dict) and isinstance(data.get("controls"), list):
            controls = _ids(data["controls"])
        else:
            raise LoadError(f"{p}: unrecognized baseline JSON (expected a profile, catalog or list)")
    else:
        lines = [line.split("#", 1)[0].strip() for line in text.splitlines()]
        controls = _ids([line for line in lines if line])
    if not controls:
        raise LoadError(f"{p}: baseline contains no control IDs")
    return Baseline(controls=frozenset(controls), source=str(p))


def baseline_from_ssp(ssp: Document) -> Baseline | None:
    """Follow the SSP's import-profile when it points at a local file.

    Remote URLs are deliberately not fetched: a package review should run
    offline and give the same answer every time.
    """
    href = str(ssp.root.get("import-profile", {}).get("href", "")).strip()
    if not href:
        return None
    if href.startswith("#"):
        href = _resolve_back_matter(ssp.root, href[1:]) or ""
    if not href or "://" in href:
        return None
    candidate = ssp.path.parent / href
    if not candidate.is_file():
        return None
    return load_baseline(candidate)


def _resolve_back_matter(root: dict[str, Any], uuid: str) -> str | None:
    for res in root.get("back-matter", {}).get("resources", []):
        if res.get("uuid") == uuid:
            for rlink in res.get("rlinks", []):
                if rlink.get("href"):
                    return str(rlink["href"])
    return None
