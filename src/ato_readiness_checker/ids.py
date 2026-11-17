"""Control-ID and severity normalization.

The same control shows up in many spellings across an authorization package:
``AC-2(1)`` in an SSP written by hand, ``ac-2.1`` in OSCAL catalogs,
``ac-2.1_smt`` as a statement target in a POA&M, ``ac-2_obj`` as an objective
target in Assessment Results. To compare documents we reduce every spelling to
one canonical key (the OSCAL catalog form, e.g. ``ac-2.1``).

IDs that are not NIST SP 800-53 style (for example CMMC practice IDs such as
``AC.L2-3.1.1``) are kept as-is apart from case and the ``_smt``/``_obj``
suffixes, so a CMMC package still lines up with itself.
"""

from __future__ import annotations

import re

# ac-2 / AC-2 / AC-2(1) / AC-2 (1) / ac-2.1, optionally followed by an OSCAL
# part suffix such as _smt, _smt.a, _obj, _obj.a-1, _gdn.
_NIST_ID = re.compile(
    r"^\s*([a-z]{2})-(\d{1,3})\s*(?:\(\s*(\d{1,3})\s*\)|\.(\d{1,3}))?"
    r"(?:_(?:smt|obj|gdn|stm|ods)\b.*)?\s*$",
    re.IGNORECASE,
)
_PART_SUFFIX = re.compile(r"_(?:smt|obj|gdn|stm|ods)(?:[._].*)?$", re.IGNORECASE)


def normalize_control_id(raw: str | None) -> str | None:
    """Return the canonical (OSCAL catalog) form of a control ID, or None."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    m = _NIST_ID.match(text)
    if m:
        family, number, enh_paren, enh_dot = m.groups()
        enhancement = enh_paren or enh_dot
        key = f"{family.lower()}-{int(number)}"
        if enhancement is not None:
            key += f".{int(enhancement)}"
        return key
    return _PART_SUFFIX.sub("", text).lower() or None


def display_control_id(key: str) -> str:
    """Turn a canonical key back into the familiar form: ``ac-2.1`` -> ``AC-2(1)``."""
    m = re.match(r"^([a-z]{2})-(\d+)(?:\.(\d+))?$", key)
    if not m:
        return key.upper()
    family, number, enhancement = m.groups()
    out = f"{family.upper()}-{number}"
    if enhancement:
        out += f"({enhancement})"
    return out


# --- Severity -----------------------------------------------------------------
#
# Weakness severity arrives as free text: "Critical", "High", "CAT I", "II",
# "moderate", "very high". We bucket it into four levels. DISA CAT I maps to
# "high" (DISA defines CAT I as the high-severity category); "Critical" and
# "Very High" (NIST SP 800-30 scale) map to "critical".

SEVERITY_LEVELS = ("critical", "high", "moderate", "low")
_SEVERITY_ALIASES = {
    "critical": "critical",
    "very high": "critical",
    "very-high": "critical",
    "high": "high",
    "cat i": "high",
    "cat 1": "high",
    "cati": "high",
    "i": "high",
    "moderate": "moderate",
    "medium": "moderate",
    "cat ii": "moderate",
    "cat 2": "moderate",
    "catii": "moderate",
    "ii": "moderate",
    "low": "low",
    "very low": "low",
    "very-low": "low",
    "cat iii": "low",
    "cat 3": "low",
    "catiii": "low",
    "iii": "low",
    "informational": "low",
    "info": "low",
}


def normalize_severity(raw: str | None) -> str | None:
    """Map a free-text severity to critical/high/moderate/low, or None if unknown."""
    if raw is None:
        return None
    text = re.sub(r"\s+", " ", str(raw).strip().lower())
    text = text.removeprefix("category ").strip()
    return _SEVERITY_ALIASES.get(text)


def worst_severity(values: list[str | None]) -> str | None:
    known = [v for v in values if v in SEVERITY_LEVELS]
    if not known:
        return None
    return min(known, key=SEVERITY_LEVELS.index)
