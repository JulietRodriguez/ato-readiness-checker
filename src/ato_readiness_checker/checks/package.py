"""Package-level checks."""

from __future__ import annotations

from ato_readiness_checker.checks import Context
from ato_readiness_checker.model import CheckResult, Severity


def package_complete(ctx: Context) -> CheckResult:
    r = CheckResult(
        "PKG-001",
        "Package has an SSP, Assessment Results and a POA&M",
        "package",
        Severity.CRITICAL,
        "An authorization package needs all three core documents for the AO to weigh risk.",
    )
    pkg = ctx.view.package
    r.evaluated = 3
    if pkg.ssp is None:
        r.fail("No System Security Plan supplied.", ref="SSP", document="package")
    if not pkg.assessment_results:
        r.fail("No Assessment Results supplied.", ref="Assessment Results", document="package")
    if not pkg.poams:
        r.fail("No POA&M supplied.", ref="POA&M", document="package")
    return r
