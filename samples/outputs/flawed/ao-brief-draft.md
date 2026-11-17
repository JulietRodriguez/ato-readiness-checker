> **DRAFT FOR HUMAN REVIEW. This is not an authorization decision.**

# Draft AO Decision Brief: SYNTHETIC Case Management System (CMS-DEMO)

Prepared 2026-11-17 by ato-readiness-checker 0.1.0 from: ssp.json, assessment-results.json, poam.json.

## 1. System
- Security categorization: **Moderate** (C: Low, I: Moderate, A: Low). Status: operational. Baseline: 22 controls.
- SSP documents 21 controls.

## 2. Package readiness (tool measure, not an official score)
- **NOT READY**, readiness score 84.7 / 100. Package issues: 1 critical, 7 high, 14 medium, 5 low.
- POAM-004: Stale privileged accounts [a1ba1b3a]: Due 2026-10-01, 47 days overdue as of 2026-11-17.
- CTRL-001: IA-2(1): Baseline control is not addressed in the SSP.
- CTRL-002: AU-9: No implementation narrative.
- POAM-001: Database tier scanned without credentials [e51103f1]: No scheduled completion date.
- REF-001: poam.json:69cbc939-287d-50fc-a74c-c2dcf236d5b9: risk-uuid does not resolve to any object in the package (at poam-items/related-risks/risk-uuid).
- ...and 3 more critical/high package issues in the full report.

## 3. Risk summary
- Assessment: 20 findings, 7 not satisfied (latest assessment 2025-08-29).
- Open POA&M items: 5 (Critical 0, High/CAT I 2, Moderate/CAT II 2, Low/CAT III 0, unknown 1); 1 overdue; 1 risk accepted.

## 4. Open Critical / High / CAT I items
| Item | Control(s) | Severity | Due | POC |
|---|---|---|---|---|
| Stale privileged accounts | AC-2 | High / CAT I | 2026-10-01 (overdue) | ISSO, CMS-DEMO (synthetic) |
| High-severity patches past due | SI-2 | High / CAT I | 2026-12-17 | none |

## 5. Accepted risks
- Weekly (not daily) audit review: risk accepted (AU-6, Low / CAT III)

## Decision (to be completed by the Authorizing Official)
- [ ] Authorization to Operate (ATO)
- [ ] ATO with conditions (list conditions below)
- [ ] Denial of Authorization to Operate (DATO)

Conditions / authorization termination date: ______________________________

AO name, signature and date: ______________________________

*The readiness score and level are this tool's own measures of package completeness and consistency. They are not an official FedRAMP, DoD or NIST metric. Only the Authorizing Official makes the authorization decision.*
