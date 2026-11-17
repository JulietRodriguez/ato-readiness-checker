"""Readiness report as one self-contained HTML file (no scripts, no external assets).

Every value from the input documents is passed through html.escape, because
titles and descriptions in an OSCAL file are free text written by someone else.
"""

from __future__ import annotations

from html import escape

from ato_readiness_checker.review import DISCLAIMER, Review

STYLE = """
:root { --fg:#1b1f24; --muted:#59636e; --line:#d1d9e0; --bg:#ffffff; --soft:#f6f8fa;
  --crit:#a40e26; --high:#bc4c00; --med:#9a6700; --low:#0969da; --info:#59636e; --ok:#1a7f37; }
* { box-sizing: border-box; }
body { font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; color: var(--fg);
  background: var(--bg); max-width: 1100px; margin: 0 auto; padding: 32px 24px 64px; }
h1 { font-size: 26px; margin: 0 0 4px; }
h2 { font-size: 19px; margin: 32px 0 10px; border-bottom: 1px solid var(--line); padding-bottom: 6px; }
h3 { font-size: 16px; margin: 20px 0 8px; }
.meta { color: var(--muted); margin: 0 0 16px; }
.note { background: var(--soft); border-left: 4px solid var(--muted); padding: 10px 14px; margin: 16px 0; }
.banner { display: flex; gap: 24px; align-items: center; border: 1px solid var(--line);
  border-radius: 8px; padding: 16px 20px; margin: 16px 0; }
.level { font-size: 22px; font-weight: 700; }
.level.NOT-READY { color: var(--crit); } .level.NEEDS-WORK { color: var(--high); }
.level.READY-FOR-REVIEW { color: var(--ok); }
.score { font-size: 32px; font-weight: 700; } .score small { font-size: 14px; color: var(--muted); }
table { border-collapse: collapse; width: 100%; margin: 8px 0 16px; font-size: 14px; }
th, td { border: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: var(--soft); } td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.sev { font-weight: 600; text-transform: capitalize; }
.sev.critical { color: var(--crit); } .sev.high { color: var(--high); } .sev.medium { color: var(--med); }
.sev.low { color: var(--low); } .sev.info { color: var(--info); }
.PASS { color: var(--ok); font-weight: 600; } .FAIL { color: var(--crit); font-weight: 600; }
.skipped { color: var(--muted); }
code { background: var(--soft); padding: 1px 4px; border-radius: 4px; font-size: 13px; }
ul.issues { padding-left: 20px; } ul.issues li { margin: 3px 0; }
@media print { body { padding: 0; } h2 { break-after: avoid; } }
"""

SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")


def e(value: object) -> str:
    return escape(str(value), quote=True)


def page(title: str, body: str, extra_style: str = "") -> str:
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{e(title)}</title>\n<style>{STYLE}{extra_style}</style>\n</head>\n<body>\n"
        f"{body}\n</body>\n</html>\n"
    )


def _issue_groups(w, issues: list[dict]) -> None:
    for level in SEVERITY_ORDER:
        group = sorted((i for i in issues if i["severity"] == level), key=lambda x: (x["check_id"], x["ref"]))
        if not group:
            continue
        w(f'<h3><span class="sev {level}">{level}</span> ({len(group)})</h3><ul class="issues">')
        for i in group:
            ref = f" <code>{e(i['ref'])}</code>" if i["ref"] else ""
            w(f"<li><strong>{e(i['check_id'])}</strong>{ref}: {e(i['message'])}</li>")
        w("</ul>")


def report_html(review: Review) -> str:
    d = review.to_dict()
    r = d["readiness"]
    c = d["issue_counts"]
    s = d["stats"]
    parts: list[str] = []
    w = parts.append
    w("<h1>Authorization Package Readiness Report</h1>")
    w(
        f'<p class="meta">{e(d["system_name"])} &middot; as of {e(d["as_of"])} &middot; generated '
        f"{e(d['generated_at'])} by ato-readiness-checker {e(d['tool']['version'])}</p>"
    )
    w(f'<div class="note">{e(DISCLAIMER)}</div>')
    level_class = r["level"].replace(" ", "-")
    w(
        f'<div class="banner"><div><div class="level {level_class}">{e(r["level"])}</div>'
        f"<div>{e(r['level_meaning'])}</div></div>"
        f'<div class="score">{e(r["score"])}<small> / 100 readiness score</small></div></div>'
    )
    w("<table><tr>" + "".join(f'<th class="num">{lvl.capitalize()}</th>' for lvl in SEVERITY_ORDER) + "</tr><tr>")
    w("".join(f'<td class="num"><span class="sev {lvl}">{c[lvl]}</span></td>' for lvl in SEVERITY_ORDER))
    w("</tr></table>")
    cs = d["checks_summary"]
    w(f"<p>{cs['total']} checks: {cs['passed']} passed, {cs['failed']} failed, {cs['skipped']} skipped.</p>")

    w("<h2>Package</h2><table><tr><th>Document</th><th>File</th><th>Title</th><th>OSCAL</th></tr>")
    for doc in d["documents"]:
        w(
            f"<tr><td>{e(doc['kind'])}</td><td>{e(doc['file'])}</td><td>{e(doc['title'])}</td>"
            f"<td>{e(doc['oscal_version'] or '-')}</td></tr>"
        )
    w("</table>")
    if d["baseline"]:
        w(f"<p>Baseline: {d['baseline']['controls']} controls from <code>{e(d['baseline']['source'])}</code>.</p>")
    else:
        w("<p>Baseline: none supplied, so baseline coverage (CTRL-001) was skipped.</p>")

    w("<h2>Key numbers</h2><ul>")
    if "ssp" in s:
        statuses = ", ".join(f"{k} {v}" for k, v in s["ssp"]["implementation_status"].items())
        w(f"<li>SSP: {s['ssp']['controls']} controls ({e(statuses)}).</li>")
    a = s["assessment"]
    w(
        f"<li>Assessment: {a['findings']} findings in {a['results']} result(s): {a['satisfied']} satisfied, "
        f"{a['not_satisfied']} not satisfied. Latest assessment: {e(a['latest_assessment'] or 'unknown')}.</li>"
    )
    p = s["poam"]
    sev = p["open_by_severity"]
    w(
        f"<li>POA&amp;M: {p['items']} items: {p['open']} open, {p['risk_accepted']} risk accepted, "
        f"{p['closed']} closed. {p['overdue']} open item(s) overdue.</li>"
        f"<li>Open by severity: Critical {sev['critical']}, High/CAT I {sev['high']}, Moderate/CAT II "
        f"{sev['moderate']}, Low/CAT III {sev['low']}, unknown {sev['unknown']}.</li></ul>"
    )

    w(
        "<h2>Checks</h2><table><tr><th>ID</th><th>Check</th><th>Severity</th><th>Result</th>"
        '<th class="num">Evaluated</th><th class="num">Failed</th></tr>'
    )
    for chk in d["checks"]:
        result = {"pass": "PASS", "fail": "FAIL", "skipped": "skipped"}[chk["status"]]
        title = e(chk["title"])
        if chk["skipped_reason"]:
            title += f'<br><span class="skipped">{e(chk["skipped_reason"])}</span>'
        w(
            f"<tr><td>{e(chk['check_id'])}</td><td>{title}</td>"
            f'<td><span class="sev {e(chk["severity"])}">{e(chk["severity"])}</span></td>'
            f'<td class="{result}">{result}</td><td class="num">{chk["evaluated"]}</td>'
            f'<td class="num">{chk["failed"]}</td></tr>'
        )
    w("</table>")

    package_issues = [i for chk in d["checks"] if chk["counts_toward_readiness"] for i in chk["issues"]]
    risk_issues = [i for chk in d["checks"] if not chk["counts_toward_readiness"] for i in chk["issues"]]
    w("<h2>Package issues</h2>")
    if not package_issues:
        w("<p>No package issues found.</p>")
    _issue_groups(w, package_issues)
    w("<h2>Risk items for the AO</h2>")
    w(
        "<p>Open Critical/High/CAT I weaknesses and accepted risks. These describe the system's risk, not the "
        "package's quality, so they do not change the readiness score or level. <code>--fail-on</code> still "
        "sees them.</p>"
    )
    if not risk_issues:
        w("<p>No open Critical/High/CAT I weaknesses and no accepted risks.</p>")
    _issue_groups(w, risk_issues)

    w("<h2>Traceability: not-satisfied findings to POA&amp;M items</h2>")
    if not d["traceability"]:
        w("<p>No not-satisfied findings in the Assessment Results.</p>")
    else:
        w(
            "<p>Match = how the link was found: <code>uuid</code> (OSCAL reference), "
            "<code>control</code> (same control ID), or <code>none</code>.</p>"
            "<table><tr><th>Finding</th><th>Control</th><th>Match</th><th>POA&amp;M item(s)</th></tr>"
        )
        for row in d["traceability"]:
            items = "<br>".join(e(x) for x in row["poam_items"]) or "<strong>none</strong>"
            w(
                f"<tr><td>{e(row['finding_title'])}</td><td>{e(row['finding'])}</td>"
                f"<td>{e(row['match'])}</td><td>{items}</td></tr>"
            )
        w("</table>")
    return page(f"Readiness report: {d['system_name']}", "\n".join(parts))
