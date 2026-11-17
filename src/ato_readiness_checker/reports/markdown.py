"""Readiness report as Markdown (renders on GitHub, pastes into tickets)."""

from __future__ import annotations

from ato_readiness_checker.review import DISCLAIMER, Review

SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")


def md_escape(text: object) -> str:
    """Keep table cells and list items intact: escape pipes, flatten newlines."""
    return str(text).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _status(check: dict) -> str:
    return {"pass": "PASS", "fail": "FAIL", "skipped": "skipped"}[check["status"]]


def _issue_groups(w, issues: list[dict]) -> None:
    for level in SEVERITY_ORDER:
        group = [i for i in issues if i["severity"] == level]
        if not group:
            continue
        w(f"### {level.capitalize()} ({len(group)})")
        w("")
        for i in sorted(group, key=lambda x: (x["check_id"], x["ref"])):
            ref = f" `{md_escape(i['ref'])}`" if i["ref"] else ""
            w(f"- **{i['check_id']}**{ref}: {md_escape(i['message'])}")
        w("")


def report_markdown(review: Review) -> str:
    d = review.to_dict()
    out: list[str] = []
    w = out.append
    w("# Authorization Package Readiness Report")
    w("")
    w(f"**System:** {md_escape(d['system_name'])}  ")
    w(f"**As of:** {d['as_of']}  ")
    w(f"**Generated:** {d['generated_at']} by ato-readiness-checker {d['tool']['version']}")
    w("")
    w(f"> {DISCLAIMER}")
    w("")
    r = d["readiness"]
    w(f"## Result: {r['level']} (readiness score {r['score']} / 100)")
    w("")
    w(r["level_meaning"])
    w("")
    w("Package issues (these set the level and score):")
    w("")
    w("| Critical | High | Medium | Low | Info |")
    w("|---:|---:|---:|---:|---:|")
    c = d["issue_counts"]
    w(f"| {c['critical']} | {c['high']} | {c['medium']} | {c['low']} | {c['info']} |")
    w("")
    cs = d["checks_summary"]
    w(f"{cs['total']} checks: {cs['passed']} passed, {cs['failed']} failed, {cs['skipped']} skipped.")
    w("")

    w("## Package")
    w("")
    w("| Document | File | Title | OSCAL |")
    w("|---|---|---|---|")
    for doc in d["documents"]:
        w(
            f"| {doc['kind']} | {md_escape(doc['file'])} | {md_escape(doc['title'])} | "
            f"{md_escape(doc['oscal_version'] or '-')} |"
        )
    w("")
    if d["baseline"]:
        w(f"Baseline: {d['baseline']['controls']} controls from `{md_escape(d['baseline']['source'])}`.")
    else:
        w("Baseline: none supplied, so baseline coverage (CTRL-001) was skipped.")
    w("")

    w("## Key numbers")
    w("")
    s = d["stats"]
    if "ssp" in s:
        statuses = ", ".join(f"{k} {v}" for k, v in s["ssp"]["implementation_status"].items())
        w(f"- SSP: {s['ssp']['controls']} controls ({statuses}).")
    a = s["assessment"]
    w(
        f"- Assessment: {a['findings']} findings in {a['results']} result(s): "
        f"{a['satisfied']} satisfied, {a['not_satisfied']} not satisfied. "
        f"Latest assessment: {a['latest_assessment'] or 'unknown'}."
    )
    p = s["poam"]
    sev = p["open_by_severity"]
    w(
        f"- POA&M: {p['items']} items: {p['open']} open, {p['risk_accepted']} risk accepted, "
        f"{p['closed']} closed. {p['overdue']} open item(s) overdue."
    )
    w(
        f"- Open by severity: Critical {sev['critical']}, High/CAT I {sev['high']}, "
        f"Moderate/CAT II {sev['moderate']}, Low/CAT III {sev['low']}, unknown {sev['unknown']}."
    )
    w("")

    w("## Checks")
    w("")
    w("| ID | Check | Severity | Result | Evaluated | Failed |")
    w("|---|---|---|---|---:|---:|")
    for chk in d["checks"]:
        w(
            f"| {chk['check_id']} | {md_escape(chk['title'])} | {chk['severity']} | {_status(chk)} | "
            f"{chk['evaluated']} | {chk['failed']} |"
        )
    w("")
    skipped = [chk for chk in d["checks"] if chk["status"] == "skipped"]
    if skipped:
        w("Skipped checks:")
        w("")
        for chk in skipped:
            w(f"- **{chk['check_id']}**: {md_escape(chk['skipped_reason'])}")
        w("")

    w("## Package issues")
    w("")
    issues = [i for chk in d["checks"] if chk["counts_toward_readiness"] for i in chk["issues"]]
    if not issues:
        w("No package issues found.")
        w("")
    _issue_groups(w, issues)

    w("## Risk items for the AO")
    w("")
    w("Open Critical/High/CAT I weaknesses and accepted risks. These describe the system's risk, not the")
    w("package's quality, so they do not change the readiness score or level. `--fail-on` still sees them.")
    w("")
    risk = [i for chk in d["checks"] if not chk["counts_toward_readiness"] for i in chk["issues"]]
    if not risk:
        w("No open Critical/High/CAT I weaknesses and no accepted risks.")
        w("")
    _issue_groups(w, risk)

    w("## Traceability: not-satisfied findings to POA&M items")
    w("")
    if not d["traceability"]:
        w("No not-satisfied findings in the Assessment Results.")
    else:
        w("Match = how the link was found: `uuid` (OSCAL reference), `control` (same control ID), or `none`.")
        w("")
        w("| Finding | Control | Match | POA&M item(s) |")
        w("|---|---|---|---|")
        for row in d["traceability"]:
            items = "; ".join(md_escape(x) for x in row["poam_items"]) or "**none**"
            w(f"| {md_escape(row['finding_title'])} | {md_escape(row['finding'])} | {row['match']} | {items} |")
    w("")
    return "\n".join(out)
