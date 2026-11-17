"""One-page draft AO decision brief.

The brief summarizes risk for the Authorizing Official. It is always marked
DRAFT, leaves the decision boxes empty, and says that only the AO decides.
The tool never recommends an authorization decision.
"""

from __future__ import annotations

from html import escape

from ato_readiness_checker import __version__
from ato_readiness_checker.extract import PoamItem
from ato_readiness_checker.ids import SEVERITY_LEVELS
from ato_readiness_checker.model import Severity
from ato_readiness_checker.reports.html import page
from ato_readiness_checker.reports.markdown import md_escape
from ato_readiness_checker.review import DISCLAIMER, Review
from ato_readiness_checker.scoring import all_issues

DRAFT_BANNER = "DRAFT FOR HUMAN REVIEW. This is not an authorization decision."
MAX_ITEMS = 8
MAX_ACCEPTED = 5
MAX_PROBLEMS = 5
_SEV_LABEL = {"critical": "Critical", "high": "High / CAT I", "moderate": "Moderate / CAT II", "low": "Low / CAT III"}
DECISIONS = (
    "Authorization to Operate (ATO)",
    "ATO with conditions (list conditions below)",
    "Denial of Authorization to Operate (DATO)",
)


def _sort_key(item: PoamItem) -> tuple:
    rank = SEVERITY_LEVELS.index(item.severity) if item.severity in SEVERITY_LEVELS else len(SEVERITY_LEVELS)
    return (rank, item.deadline.isoformat() if item.deadline else "9999-12-31", item.title)


def _level(value: object) -> str:
    text = str(value or "").removeprefix("fips-199-")
    return text.capitalize() if text else "not stated"


def brief_data(review: Review) -> dict:
    view = review.view
    chars = view.ssp.doc.root.get("system-characteristics", {}) if view.ssp else {}
    impact = chars.get("security-impact-level", {}) or {}
    open_items = sorted(review.open_items(), key=_sort_key)
    attention = [i for i in open_items if i.severity in ("critical", "high")]
    accepted = sorted((i for i in view.poam_items if i.is_accepted), key=_sort_key)
    problems = [
        i for i in all_issues(review.results, readiness_only=True) if i.severity in (Severity.CRITICAL, Severity.HIGH)
    ]
    return {
        "system": review.system_name,
        "as_of": review.as_of.isoformat(),
        "files": [d.path.name for d in view.package.documents],
        "categorization": {
            "overall": _level(chars.get("security-sensitivity-level")),
            "c": _level(impact.get("security-objective-confidentiality")),
            "i": _level(impact.get("security-objective-integrity")),
            "a": _level(impact.get("security-objective-availability")),
        },
        "status": (chars.get("status", {}) or {}).get("state", "not stated"),
        "baseline": f"{len(review.baseline)} controls" if review.baseline else "not supplied",
        "stats": review.stats,
        "level": review.level,
        "score": review.score,
        "counts": review.to_dict()["issue_counts"],
        "problems": problems,
        "attention": attention,
        "accepted": accepted,
        "overdue": [i for i in open_items if i.deadline and i.deadline < review.as_of],
    }


def _item_row(item: PoamItem, as_of) -> tuple[str, str, str, str, str]:
    due = item.deadline.isoformat() if item.deadline else "none"
    if item.deadline and item.deadline < as_of:
        due += " (overdue)"
    return (
        item.title,
        item.controls_display,
        _SEV_LABEL.get(item.severity or "", "unknown"),
        due,
        ", ".join(item.pocs) or "none",
    )


def brief_markdown(review: Review) -> str:
    b = brief_data(review)
    s = b["stats"]
    out: list[str] = []
    w = out.append
    w(f"> **{DRAFT_BANNER}**")
    w("")
    w(f"# Draft AO Decision Brief: {md_escape(b['system'])}")
    w("")
    w(f"Prepared {b['as_of']} by ato-readiness-checker {__version__} from: {', '.join(map(md_escape, b['files']))}.")
    w("")
    w("## 1. System")
    cat = b["categorization"]
    w(
        f"- Security categorization: **{cat['overall']}** (C: {cat['c']}, I: {cat['i']}, A: {cat['a']}). "
        f"Status: {md_escape(b['status'])}. Baseline: {b['baseline']}."
    )
    if "ssp" in s:
        w(f"- SSP documents {s['ssp']['controls']} controls.")
    w("")
    w("## 2. Package readiness (tool measure, not an official score)")
    c = b["counts"]
    w(
        f"- **{b['level']}**, readiness score {b['score']} / 100. Package issues: {c['critical']} critical, "
        f"{c['high']} high, {c['medium']} medium, {c['low']} low."
    )
    for issue in b["problems"][:MAX_PROBLEMS]:
        w(f"- {issue.check_id}: {md_escape(issue.ref)}: {md_escape(issue.message)}")
    if len(b["problems"]) > MAX_PROBLEMS:
        w(f"- ...and {len(b['problems']) - MAX_PROBLEMS} more critical/high package issues in the full report.")
    w("")
    w("## 3. Risk summary")
    a, p = s["assessment"], s["poam"]
    sev = p["open_by_severity"]
    w(
        f"- Assessment: {a['findings']} findings, {a['not_satisfied']} not satisfied "
        f"(latest assessment {a['latest_assessment'] or 'unknown'})."
    )
    w(
        f"- Open POA&M items: {p['open']} (Critical {sev['critical']}, High/CAT I {sev['high']}, "
        f"Moderate/CAT II {sev['moderate']}, Low/CAT III {sev['low']}, unknown {sev['unknown']}); "
        f"{p['overdue']} overdue; {p['risk_accepted']} risk accepted."
    )
    w("")
    w("## 4. Open Critical / High / CAT I items")
    if not b["attention"]:
        w("None.")
    else:
        w("| Item | Control(s) | Severity | Due | POC |")
        w("|---|---|---|---|---|")
        for item in b["attention"][:MAX_ITEMS]:
            w("| " + " | ".join(md_escape(x) for x in _item_row(item, review.as_of)) + " |")
        if len(b["attention"]) > MAX_ITEMS:
            w(f"\n...and {len(b['attention']) - MAX_ITEMS} more in the full report.")
    w("")
    if b["accepted"]:
        w("## 5. Accepted risks")
        for item in b["accepted"][:MAX_ACCEPTED]:
            w(f"- {md_escape(item.title)} ({item.controls_display}, {_SEV_LABEL.get(item.severity or '', 'unknown')})")
        if len(b["accepted"]) > MAX_ACCEPTED:
            w(f"- ...and {len(b['accepted']) - MAX_ACCEPTED} more in the full report.")
        w("")
    w("## Decision (to be completed by the Authorizing Official)")
    for option in DECISIONS:
        w(f"- [ ] {option}")
    w("")
    w("Conditions / authorization termination date: ______________________________")
    w("")
    w("AO name, signature and date: ______________________________")
    w("")
    w(f"*{DISCLAIMER}*")
    w("")
    return "\n".join(out)


BRIEF_STYLE = """
body { max-width: 820px; font-size: 13.5px; padding: 20px 28px; }
h1 { font-size: 21px; } h2 { font-size: 15px; margin: 16px 0 6px; }
.draft { border: 2px solid var(--crit); color: var(--crit); font-weight: 700; text-align: center;
  padding: 6px; margin-bottom: 12px; letter-spacing: .02em; }
ul { margin: 4px 0; padding-left: 18px; } table { font-size: 12.5px; }
.sign { margin-top: 14px; } .sign div { border-bottom: 1px solid var(--fg); height: 26px; margin-bottom: 8px; }
.box { display: inline-block; width: 12px; height: 12px; border: 1.5px solid var(--fg); margin-right: 6px; }
@page { size: letter; margin: 0.5in; }
@media print { body { font-size: 11px; padding: 0; } h1 { font-size: 17px; } h2 { margin: 10px 0 4px; } }
"""


def brief_html(review: Review) -> str:
    b = brief_data(review)
    s = b["stats"]

    def e(value: object) -> str:
        return escape(str(value))

    cat = b["categorization"]
    c = b["counts"]
    a, p = s["assessment"], s["poam"]
    sev = p["open_by_severity"]
    parts = [
        f'<div class="draft">{e(DRAFT_BANNER)}</div>',
        f"<h1>Draft AO Decision Brief: {e(b['system'])}</h1>",
        f'<p class="meta">Prepared {e(b["as_of"])} by ato-readiness-checker {e(__version__)} from: '
        f"{e(', '.join(b['files']))}.</p>",
        "<h2>1. System</h2><ul>",
        f"<li>Security categorization: <strong>{e(cat['overall'])}</strong> (C: {e(cat['c'])}, I: {e(cat['i'])}, "
        f"A: {e(cat['a'])}). Status: {e(b['status'])}. Baseline: {e(b['baseline'])}.</li>",
    ]
    if "ssp" in s:
        parts.append(f"<li>SSP documents {s['ssp']['controls']} controls.</li>")
    parts += [
        "</ul><h2>2. Package readiness (tool measure, not an official score)</h2><ul>",
        f"<li><strong>{e(b['level'])}</strong>, readiness score {e(b['score'])} / 100. Package issues: "
        f"{c['critical']} critical, {c['high']} high, {c['medium']} medium, {c['low']} low.</li>",
    ]
    for issue in b["problems"][:MAX_PROBLEMS]:
        parts.append(f"<li>{e(issue.check_id)}: {e(issue.ref)}: {e(issue.message)}</li>")
    if len(b["problems"]) > MAX_PROBLEMS:
        parts.append(f"<li>...and {len(b['problems']) - MAX_PROBLEMS} more critical/high package issues.</li>")
    parts += [
        "</ul><h2>3. Risk summary</h2><ul>",
        f"<li>Assessment: {a['findings']} findings, {a['not_satisfied']} not satisfied (latest assessment "
        f"{e(a['latest_assessment'] or 'unknown')}).</li>",
        f"<li>Open POA&amp;M items: {p['open']} (Critical {sev['critical']}, High/CAT I {sev['high']}, "
        f"Moderate/CAT II {sev['moderate']}, Low/CAT III {sev['low']}, unknown {sev['unknown']}); "
        f"{p['overdue']} overdue; {p['risk_accepted']} risk accepted.</li></ul>",
        "<h2>4. Open Critical / High / CAT I items</h2>",
    ]
    if not b["attention"]:
        parts.append("<p>None.</p>")
    else:
        parts.append("<table><tr><th>Item</th><th>Control(s)</th><th>Severity</th><th>Due</th><th>POC</th></tr>")
        for item in b["attention"][:MAX_ITEMS]:
            parts.append("<tr>" + "".join(f"<td>{e(x)}</td>" for x in _item_row(item, review.as_of)) + "</tr>")
        parts.append("</table>")
        if len(b["attention"]) > MAX_ITEMS:
            parts.append(f"<p>...and {len(b['attention']) - MAX_ITEMS} more in the full report.</p>")
    if b["accepted"]:
        parts.append("<h2>5. Accepted risks</h2><ul>")
        for item in b["accepted"][:MAX_ACCEPTED]:
            label = _SEV_LABEL.get(item.severity or "", "unknown")
            parts.append(f"<li>{e(item.title)} ({e(item.controls_display)}, {e(label)})</li>")
        if len(b["accepted"]) > MAX_ACCEPTED:
            parts.append(f"<li>...and {len(b['accepted']) - MAX_ACCEPTED} more in the full report.</li>")
        parts.append("</ul>")
    parts.append("<h2>Decision (to be completed by the Authorizing Official)</h2>")
    parts += [f'<div><span class="box"></span>{e(option)}</div>' for option in DECISIONS]
    parts += [
        '<div class="sign">Conditions / authorization termination date:<div></div>',
        "AO name, signature and date:<div></div></div>",
        f'<p class="meta"><em>{e(DISCLAIMER)}</em></p>',
    ]
    return page(f"DRAFT AO brief: {b['system']}", "\n".join(parts), BRIEF_STYLE)
