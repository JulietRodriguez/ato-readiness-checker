# Authorization Package Readiness Report

**System:** SYNTHETIC Case Management System (CMS-DEMO)  
**As of:** 2026-11-17  
**Generated:** 2026-11-17T12:00:00+00:00 by ato-readiness-checker 0.1.0

> The readiness score and level are this tool's own measures of package completeness and consistency. They are not an official FedRAMP, DoD or NIST metric. Only the Authorizing Official makes the authorization decision.

## Result: READY FOR REVIEW (readiness score 100.0 / 100)

No critical or high issues. The package can go to the AO for a decision.

Package issues (these set the level and score):

| Critical | High | Medium | Low | Info |
|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 | 0 |

30 checks: 27 passed, 2 failed, 1 skipped.

## Package

| Document | File | Title | OSCAL |
|---|---|---|---|
| ssp | ssp.json | System Security Plan: SYNTHETIC Case Management System (CMS-DEMO) | 1.1.2 |
| assessment-results | assessment-results.json | Security Assessment Results: SYNTHETIC Case Management System (CMS-DEMO) | 1.1.2 |
| poam | poam.json | POA&M: SYNTHETIC Case Management System (CMS-DEMO) | 1.1.2 |

Baseline: 22 controls from `samples/clean/baseline-profile.json`.

## Key numbers

- SSP: 22 controls (implemented 15, not-applicable 1, partial 5, planned 1).
- Assessment: 21 findings in 1 result(s): 15 satisfied, 6 not satisfied. Latest assessment: 2026-10-09.
- POA&M: 7 items: 5 open, 1 risk accepted, 1 closed. 0 open item(s) overdue.
- Open by severity: Critical 0, High/CAT I 2, Moderate/CAT II 2, Low/CAT III 1, unknown 0.

## Checks

| ID | Check | Severity | Result | Evaluated | Failed |
|---|---|---|---|---:|---:|
| PKG-001 | Package has an SSP, Assessment Results and a POA&M | critical | PASS | 3 | 0 |
| SSP-001 | Required SSP sections are present | high | PASS | 15 | 0 |
| SSP-002 | Security categorization is consistent (FIPS 199 high-water mark) | high | PASS | 6 | 0 |
| SSP-003 | Key roles are assigned to people | medium | PASS | 3 | 0 |
| SSP-004 | No draft or placeholder language | medium | PASS | 29 | 0 |
| CTRL-001 | Every baseline control has an implementation statement | high | PASS | 22 | 0 |
| CTRL-002 | Implemented requirements describe how the control is met | high | PASS | 21 | 0 |
| CTRL-003 | Implementation status is present, valid and consistent | medium | PASS | 22 | 0 |
| CTRL-004 | SSP status agrees with the assessment | medium | PASS | 21 | 0 |
| CTRL-005 | Planned and partial controls are tracked on the POA&M | medium | PASS | 6 | 0 |
| CTRL-006 | Not-applicable controls are justified | low | PASS | 1 | 0 |
| AR-001 | Assessment Results contain results and findings | critical | PASS | 1 | 0 |
| AR-002 | Every in-scope control was assessed | medium | PASS | 22 | 0 |
| AR-003 | Assessment is current | medium | PASS | 1 | 0 |
| TRC-001 | Every not-satisfied finding has a POA&M item | high | PASS | 6 | 0 |
| TRC-002 | Every POA&M item traces to an assessment finding | medium | PASS | 6 | 0 |
| POAM-001 | POA&M items have a scheduled completion date | high | PASS | 6 | 0 |
| POAM-002 | Open POA&M items have dated milestones | medium | PASS | 5 | 0 |
| POAM-003 | POA&M items have a point of contact | medium | PASS | 6 | 0 |
| POAM-004 | No overdue POA&M items | high | PASS | 5 | 0 |
| POAM-005 | POA&M items record a severity | low | PASS | 6 | 0 |
| POAM-006 | Milestones fall on or before the item's due date | low | PASS | 5 | 0 |
| REF-001 | All UUID references resolve | high | PASS | 72 | 0 |
| REF-002 | Assessed subjects are described in the SSP | low | PASS | 5 | 0 |
| REF-003 | POA&M identifies the same system as the SSP | medium | PASS | 1 | 0 |
| REF-004 | UUIDs are unique within each document | medium | PASS | 147 | 0 |
| REF-005 | OSCAL versions are declared and consistent | low | PASS | 3 | 0 |
| REF-006 | Documents are valid against the NIST OSCAL schemas | high | skipped | 0 | 0 |
| RISK-001 | Open Critical, High or CAT I weaknesses | high | FAIL | 5 | 2 |
| RISK-002 | Accepted risks are listed for the AO | info | FAIL | 6 | 1 |

Skipped checks:

- **REF-006**: Schema validation not requested (use --schema-dir).

## Package issues

No package issues found.

## Risk items for the AO

Open Critical/High/CAT I weaknesses and accepted risks. These describe the system's risk, not the
package's quality, so they do not change the readiness score or level. `--fail-on` still sees them.

### High (2)

- **RISK-001** `High-severity patches past due [d4b0da7c]`: Open High / CAT I weakness (SI-2).
- **RISK-001** `Stale privileged accounts [a1ba1b3a]`: Open High / CAT I weakness (AC-2).

### Info (1)

- **RISK-002** `Weekly (not daily) audit review: risk accepted [02be1f1e]`: Risk accepted (Low / CAT III, AU-6).

## Traceability: not-satisfied findings to POA&M items

Match = how the link was found: `uuid` (OSCAL reference), `control` (same control ID), or `none`.

| Finding | Control | Match | POA&M item(s) |
|---|---|---|---|
| AC-2 Account Management | AC-2 | uuid | Stale privileged accounts [a1ba1b3a] |
| AU-6 Audit Record Review, Analysis, and Reporting | AU-6 | uuid | Weekly (not daily) audit review: risk accepted [02be1f1e] |
| CM-6 Configuration Settings | CM-6 | control | Container settings deviate from hardening baseline [d3d0a820] |
| CM-8 System Component Inventory | CM-8 | uuid | Automated component inventory not yet in place [cbf6f6a5] |
| RA-5 Vulnerability Monitoring and Scanning | RA-5 | uuid | Database tier scanned without credentials [e51103f1] |
| SI-2 Flaw Remediation | SI-2 | uuid | High-severity patches past due [d4b0da7c] |
