"""Readiness score and readiness level.

The score is this tool's own measure. It is not a FedRAMP, DoD or NIST
metric, and it is not an authorization decision.

How it works, in plain words: each check that ran gets a pass rate (the share
of the objects it looked at that passed). The score is the average of those
pass rates, weighted by how serious the check is (critical 10, high 5,
medium 2, low 1, info 0), times 100.

Only package checks count. Risk checks (category "risk": open Critical/High/CAT I
weaknesses, accepted risks) are left out of the score and the level, because a
complete, accurate package can still carry high risk; weighing that risk is the
AO's job. The --fail-on gate still sees risk issues.

The readiness level is driven by the worst open package issue, not by the
score, so a package can't average its way past a critical problem:

* NOT READY        -- at least one critical issue
* NEEDS WORK       -- no critical issues, at least one high issue
* READY FOR REVIEW -- no critical or high issues
"""

from __future__ import annotations

from ato_readiness_checker.model import CheckResult, Issue, Severity

WEIGHTS = {
    Severity.CRITICAL: 10,
    Severity.HIGH: 5,
    Severity.MEDIUM: 2,
    Severity.LOW: 1,
    Severity.INFO: 0,
}

LEVELS = {
    "NOT READY": "At least one critical issue must be resolved before the package goes to the AO.",
    "NEEDS WORK": "No critical issues, but high issues should be resolved or explained to the AO.",
    "READY FOR REVIEW": "No critical or high issues. The package can go to the AO for a decision.",
}


def readiness_score(results: list[CheckResult]) -> float:
    total_weight = 0.0
    earned = 0.0
    for r in results:
        if not r.counts_toward_readiness:
            continue
        rate = r.pass_rate
        weight = WEIGHTS[r.severity]
        if rate is None or weight == 0:
            continue
        total_weight += weight
        earned += weight * rate
    if total_weight == 0:
        return 0.0
    return round(100.0 * earned / total_weight, 1)


def all_issues(results: list[CheckResult], *, readiness_only: bool = False) -> list[Issue]:
    issues = [i for r in results if r.counts_toward_readiness or not readiness_only for i in r.issues]
    return sorted(issues, key=lambda i: (i.severity.rank, i.check_id, i.ref))


def readiness_level(results: list[CheckResult]) -> str:
    severities = {i.severity for i in all_issues(results, readiness_only=True)}
    if Severity.CRITICAL in severities:
        return "NOT READY"
    if Severity.HIGH in severities:
        return "NEEDS WORK"
    return "READY FOR REVIEW"


def issue_counts(results: list[CheckResult], *, readiness_only: bool = True) -> dict[str, int]:
    counts = {s.value: 0 for s in Severity}
    for i in all_issues(results, readiness_only=readiness_only):
        counts[i.severity.value] += 1
    return counts


def risk_issue_counts(results: list[CheckResult]) -> dict[str, int]:
    counts = {s.value: 0 for s in Severity}
    for r in results:
        if not r.counts_toward_readiness:
            for i in r.issues:
                counts[i.severity.value] += 1
    return counts


def gate_failed(results: list[CheckResult], fail_on: Severity | None) -> bool:
    """True when any issue (package or risk) is at or above the --fail-on severity."""
    if fail_on is None:
        return False
    return any(i.severity.rank <= fail_on.rank for i in all_issues(results))
