# Authorization Package Readiness Report

**System:** SYNTHETIC Case Management System (CMS-DEMO)  
**As of:** 2026-11-17  
**Generated:** 2026-11-17T12:00:00+00:00 by ato-readiness-checker 0.1.0

> The readiness score and level are this tool's own measures of package completeness and consistency. They are not an official FedRAMP, DoD or NIST metric. Only the Authorizing Official makes the authorization decision.

## Result: NOT READY (readiness score 84.7 / 100)

At least one critical issue must be resolved before the package goes to the AO.

Package issues (these set the level and score):

| Critical | High | Medium | Low | Info |
|---:|---:|---:|---:|---:|
| 1 | 7 | 14 | 5 | 0 |

30 checks: 2 passed, 27 failed, 1 skipped.

## Package

| Document | File | Title | OSCAL |
|---|---|---|---|
| ssp | ssp.json | System Security Plan: SYNTHETIC Case Management System (CMS-DEMO) | 1.1.2 |
| assessment-results | assessment-results.json | Security Assessment Results: SYNTHETIC Case Management System (CMS-DEMO) | 1.1.2 |
| poam | poam.json | POA&M: SYNTHETIC Case Management System (CMS-DEMO) | 1.1.1 |

Baseline: 22 controls from `samples/flawed/baseline-profile.json`.

## Key numbers

- SSP: 21 controls (implemented 15, not-applicable 1, partial 4, planned 1).
- Assessment: 20 findings in 1 result(s): 13 satisfied, 7 not satisfied. Latest assessment: 2025-08-29.
- POA&M: 7 items: 5 open, 1 risk accepted, 1 closed. 1 open item(s) overdue.
- Open by severity: Critical 0, High/CAT I 2, Moderate/CAT II 2, Low/CAT III 0, unknown 1.

## Checks

| ID | Check | Severity | Result | Evaluated | Failed |
|---|---|---|---|---:|---:|
| PKG-001 | Package has an SSP, Assessment Results and a POA&M | critical | PASS | 3 | 0 |
| SSP-001 | Required SSP sections are present | high | FAIL | 15 | 1 |
| SSP-002 | Security categorization is consistent (FIPS 199 high-water mark) | high | FAIL | 6 | 1 |
| SSP-003 | Key roles are assigned to people | medium | FAIL | 3 | 1 |
| SSP-004 | No draft or placeholder language | medium | FAIL | 25 | 1 |
| CTRL-001 | Every baseline control has an implementation statement | high | FAIL | 22 | 1 |
| CTRL-002 | Implemented requirements describe how the control is met | high | FAIL | 20 | 1 |
| CTRL-003 | Implementation status is present, valid and consistent | medium | FAIL | 21 | 1 |
| CTRL-004 | SSP status agrees with the assessment | medium | FAIL | 19 | 2 |
| CTRL-005 | Planned and partial controls are tracked on the POA&M | medium | FAIL | 5 | 1 |
| CTRL-006 | Not-applicable controls are justified | low | FAIL | 1 | 1 |
| AR-001 | Assessment Results contain results and findings | critical | PASS | 1 | 0 |
| AR-002 | Every in-scope control was assessed | medium | FAIL | 22 | 1 |
| AR-003 | Assessment is current | medium | FAIL | 1 | 1 |
| TRC-001 | Every not-satisfied finding has a POA&M item | high | FAIL | 7 | 2 |
| TRC-002 | Every POA&M item traces to an assessment finding | medium | FAIL | 6 | 1 |
| POAM-001 | POA&M items have a scheduled completion date | high | FAIL | 6 | 1 |
| POAM-002 | Open POA&M items have dated milestones | medium | FAIL | 5 | 1 |
| POAM-003 | POA&M items have a point of contact | medium | FAIL | 6 | 1 |
| POAM-004 | No overdue POA&M items | high | FAIL | 5 | 1 |
| POAM-005 | POA&M items record a severity | low | FAIL | 6 | 1 |
| POAM-006 | Milestones fall on or before the item's due date | low | FAIL | 3 | 1 |
| REF-001 | All UUID references resolve | high | FAIL | 67 | 1 |
| REF-002 | Assessed subjects are described in the SSP | low | FAIL | 6 | 1 |
| REF-003 | POA&M identifies the same system as the SSP | medium | FAIL | 1 | 1 |
| REF-004 | UUIDs are unique within each document | medium | FAIL | 141 | 1 |
| REF-005 | OSCAL versions are declared and consistent | low | FAIL | 3 | 1 |
| REF-006 | Documents are valid against the NIST OSCAL schemas | high | skipped | 0 | 0 |
| RISK-001 | Open Critical, High or CAT I weaknesses | high | FAIL | 5 | 2 |
| RISK-002 | Accepted risks are listed for the AO | info | FAIL | 6 | 1 |

Skipped checks:

- **REF-006**: Schema validation not requested (use --schema-dir).

## Package issues

### Critical (1)

- **POAM-004** `Stale privileged accounts [a1ba1b3a]`: Due 2026-10-01, 47 days overdue as of 2026-11-17.

### High (7)

- **CTRL-001** `IA-2(1)`: Baseline control is not addressed in the SSP.
- **CTRL-002** `AU-9`: No implementation narrative.
- **POAM-001** `Database tier scanned without credentials [e51103f1]`: No scheduled completion date.
- **REF-001** `poam.json:69cbc939-287d-50fc-a74c-c2dcf236d5b9`: risk-uuid does not resolve to any object in the package (at poam-items/related-risks/risk-uuid).
- **SSP-002** `confidentiality`: Confidentiality is categorized low but an information type is moderate; FIPS 199 requires the high-water mark.
- **TRC-001** `CM-8`: Not-satisfied finding 'CM-8 System Component Inventory' has no POA&M item.
- **TRC-001** `IA-5`: Not-satisfied finding 'IA-5 Authenticator Management' has no POA&M item.

### Medium (14)

- **AR-002** `SC-28`: No assessment finding for this baseline control.
- **AR-003** `results`: Latest assessment ended 2025-08-29, 445 days before 2026-11-17 (limit 365).
- **CTRL-003** `CP-9`: Inconsistent status: marked implemented but a component is partial.
- **CTRL-004** `IA-5`: SSP says implemented, but the assessment found it not satisfied ('IA-5 Authenticator Management').
- **CTRL-004** `SI-2`: SSP says implemented, but the assessment found it not satisfied ('SI-2 Flaw Remediation').
- **CTRL-005** `CM-8`: SSP status is planned but no open POA&M item covers it.
- **POAM-002** `Container settings deviate from hardening baseline [d3d0a820]`: No milestones.
- **POAM-003** `High-severity patches past due [d4b0da7c]`: No point of contact.
- **REF-003** `poam.json`: POA&M system-id 42294d76-2b8a-52d3-98af-8bdaf0a8c01e is not one of the SSP's system-ids.
- **REF-004** `poam.json:48a7e19f-6a93-5dbb-9abc-c594816b9dc0`: UUID used 2 times.
- **SSP-001** `Data flow`: Missing or empty: Data flow (system-characteristics/data-flow/description).
- **SSP-003** `Authorizing Official`: No party is assigned the Authorizing Official role.
- **SSP-004** `Authorization boundary`: Contains draft language: 'TBD'.
- **TRC-002** `Legacy finding carried from a prior audit [4928980d]`: No not-satisfied finding in the Assessment Results for PL-2.

### Low (5)

- **CTRL-006** `AC-18`: Marked not-applicable with no justification.
- **POAM-005** `Legacy finding carried from a prior audit [4928980d]`: No recognizable severity.
- **POAM-006** `Legacy finding carried from a prior audit [4928980d]`: 1 milestone(s) after the due date 2027-01-31.
- **REF-002** `fee3bfb0-cd1f-53a6-aa19-9f59da269576`: Subject 'fee3bfb0-cd1f-53a6-aa19-9f59da269576' (component) is not in the SSP.
- **REF-005** `package`: Mixed OSCAL versions: assessment-results.json=1.1.2, poam.json=1.1.1, ssp.json=1.1.2.

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
| CM-8 System Component Inventory | CM-8 | none | **none** |
| IA-5 Authenticator Management | IA-5 | none | **none** |
| RA-5 Vulnerability Monitoring and Scanning | RA-5 | uuid | Database tier scanned without credentials [e51103f1] |
| SI-2 Flaw Remediation | SI-2 | uuid | High-severity patches past due [d4b0da7c] |
