# ato-readiness-checker

[![CI](https://github.com/JulietRodriguez/ato-readiness-checker/actions/workflows/ci.yml/badge.svg)](https://github.com/JulietRodriguez/ato-readiness-checker/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Reviews an OSCAL authorization package (SSP, Assessment Results, POA&M) **before** it goes to the
Authorizing Official, and tells you what's missing, inconsistent or broken.

It covers the **Authorize** step of the NIST SP 800-37 Risk Management Framework.

> **The readiness score and level are this tool's own measures** of package completeness and
> consistency. They are not an official FedRAMP, DoD or NIST metric. **Only the Authorizing Official
> makes the authorization decision.** The AO brief this tool writes is a draft for a human to review.

## The problem

An authorization package is three documents written by different people at different times. By
the time it reaches the AO, they often disagree:

- the SSP says a control is implemented, but the assessment found it not satisfied;
- a not-satisfied finding has no POA&M item, or a POA&M item points at a finding that doesn't exist;
- POA&M items have no due date, no milestones or no owner, or are already overdue;
- the categorization doesn't follow the FIPS 199 high-water mark;
- the boundary section still says "TBD".

A package can pass NIST's OSCAL schema and still have every one of those problems. The schema checks
*shape*; this tool checks whether the package holds together.

## What it checks

30 checks, listed with descriptions in [docs/checks.md](docs/checks.md) (generated from the code):

| Area | Checks |
|---|---|
| Package | All three documents are present |
| SSP | Required sections (boundary, system characteristics, categorization, architecture, data flow, components, inventory, users); FIPS 199 high-water mark; key roles assigned; no "TBD"/placeholder text |
| Controls | Every baseline control has an implemented-requirement; each one has a narrative; implementation status present, valid and consistent; SSP status agrees with the assessment; planned/partial controls are on the POA&M; not-applicable controls are justified |
| Assessment | Results and findings present; every in-scope control assessed; assessment not older than 365 days (configurable) |
| Traceability | Every not-satisfied finding has a POA&M item; every POA&M item traces back to a finding |
| POA&M | Due date, dated milestones, point of contact, not overdue, severity recorded, milestones before the due date |
| References | Every UUID reference resolves (inside a document or across the package); assessed subjects are in the SSP; POA&M and SSP name the same system; UUIDs unique; OSCAL versions consistent; optional NIST schema validation |
| Risk (for the AO) | Open Critical/High/CAT I weaknesses; accepted risks |

**Risk is kept apart from readiness.** A package can be complete and accurate and still carry open
High findings; deciding whether that risk is acceptable is the AO's job. So the two risk checks
are reported in their own section and never change the readiness score or level. The `--fail-on`
gate still sees them, so a pipeline can block on open Critical items if you want it to.

## Quick start

```bash
pip install -e .            # no runtime dependencies
pip install -e ".[schema]"  # optional: adds jsonschema for --schema-dir

ato-readiness-checker check \
  --ssp samples/flawed/ssp.json \
  --ar samples/flawed/assessment-results.json \
  --poam samples/flawed/poam.json \
  --as-of 2026-11-17 \
  -o out --brief --oscal
```

```
NOT READY: readiness score 84.7/100 for SYNTHETIC Case Management System (CMS-DEMO)
  package issues: critical 1, high 7, medium 14, low 5
  risk items for the AO: critical 0, high 2, accepted 1
  CRITICAL POAM-004 [Stale privileged accounts [a1ba1b3a]]: Due 2026-10-01, 47 days overdue as of 2026-11-17.
  HIGH     CTRL-001 [IA-2(1)]: Baseline control is not addressed in the SSP.
  ...
```

Options you'll use most:

| Option | What it does |
|---|---|
| `--ar`, `--poam` | Repeatable: review several Assessment Results or POA&Ms together (e.g. one from scans, one from a 3PAO) |
| `--baseline FILE` | The controls the system must address: an OSCAL profile, an OSCAL catalog, a JSON list, or a text file with one ID per line. If omitted, the SSP's `import-profile` is used when it points at a local file |
| `--as-of DATE` | The date due dates are judged against (default: today, UTC) |
| `--fail-on SEVERITY` | Exit 1 if any issue is at or above `critical`, `high`, `medium`, `low` or `info` |
| `--min-score N` | Exit 1 if the readiness score is below N |
| `--schema-dir DIR` | Also validate each input against NIST's OSCAL 1.1.2 schemas (check REF-006) |
| `-o DIR --format md,html,json --brief --oscal` | Which reports to write |

Exit codes: `0` reviewed and the gate passed, `1` gate failed, `2` bad input or arguments.

### As a CI gate

```yaml
- run: pip install "ato-readiness-checker @ git+https://github.com/JulietRodriguez/ato-readiness-checker"
- run: |
    ato-readiness-checker check --ssp ssp.json --ar sar.json --poam poam.json \
      --fail-on high -o readiness --brief
- uses: actions/upload-artifact@v4
  with: { name: readiness, path: readiness/ }
  if: always()
```

## Outputs

Sample outputs for both packages are committed under [samples/outputs](samples/outputs).

| File | What it is |
|---|---|
| `readiness-report.md` / `.html` / `.json` | Level, score, issue counts, key numbers, every check's result, every issue, and a traceability table (finding → POA&M item, and how the link was found) |
| `ao-brief-draft.md` / `.html` | One page for the AO: categorization, readiness, risk summary, open Critical/High/CAT I items, accepted risks, and **empty** decision boxes (ATO / ATO with conditions / DATO). Marked DRAFT at the top and bottom |
| `readiness-review.oscal.json` | The review as OSCAL 1.1.2 Assessment Results (one observation per failed check), valid against NIST's schema, so the next tool in a pipeline can read it |

The HTML files are self-contained (inline CSS, no scripts, no external requests) and escape all text
taken from the input documents.

## Sample data

Everything in `samples/` is **synthetic**: an invented system ("CMS-DEMO"), parties named only by role,
invented findings. No real system data and no CUI. [`tools/make_samples.py`](tools/make_samples.py)
builds it deterministically, and CI fails if the committed files drift from the script.

| Package | Result | Why |
|---|---|---|
| [`samples/clean`](samples/clean) | READY FOR REVIEW, 100.0 | Complete and consistent. Still carries 2 open High items and 1 accepted risk, which are listed for the AO |
| [`samples/flawed`](samples/flawed) | NOT READY, 84.7 | The same package with 23 deliberate defects (tripping 25 checks), each tagged in the script with the check that catches it. All three documents still pass NIST's OSCAL schema |

## Works with my other tools

The checker reads the OSCAL these repos write. Their real output is in
[tests/fixtures/compat](tests/fixtures/compat) and covered by tests:

| RMF step | Repo | Document |
|---|---|---|
| Implement | [oscal-ssp-generator](https://github.com/JulietRodriguez/oscal-ssp-generator) | SSP |
| Assess | [fedramp-control-validator](https://github.com/JulietRodriguez/fedramp-control-validator), [cmmc-scorecard](https://github.com/JulietRodriguez/cmmc-scorecard) | Assessment Results |
| Monitor | [poam-generator](https://github.com/JulietRodriguez/poam-generator), [stig-poam-builder](https://github.com/JulietRodriguez/stig-poam-builder) | POA&M |

Control IDs are compared in one canonical form, so `AC-2(1)`, `ac-2.1`, `ac-2.1_smt` and `ac-2_obj`
all match. Severity is read from any of the usual places (`severity`, `severity-category`, `CAT I`,
risk characterizations) and bucketed into Critical / High (incl. CAT I) / Moderate (CAT II) / Low (CAT III).

## Design choices (short version)

Plain-language explanations of each choice are in [docs/design-notes.md](docs/design-notes.md).

- **Two ways to trace a finding to a POA&M item.** First by OSCAL UUID reference, then by control ID.
  Most tools generate the AR and POA&M separately, so UUIDs rarely line up. The report says which
  method matched, so a reviewer can judge how strong each link is.
- **Level set by the worst issue, not the score.** A package can't average its way past a critical problem.
- **Risk kept separate from readiness** (see above).
- **Offline and repeatable.** No network calls, no runtime dependencies, `--as-of` for dates, UUIDv5
  for OSCAL output. Same input, same output.
- **Schema-valid is not the same as ready.** Schema validation is one check (REF-006); the other 29 are
  about content.

## Limits

- Reads OSCAL **JSON** only (not XML or YAML), version 1.1.2 (other 1.x versions usually load but
  aren't tested).
- Doesn't ship NIST SP 800-53B or FedRAMP baselines. You supply the baseline (or the SSP's
  `import-profile` points at a local file). Profiles that use `include-all` need a resolved catalog.
- Doesn't fetch remote `import-profile`, `import-ssp` or `import-ap` links, and doesn't read an
  Assessment Plan.
- Traceability by control ID is a heuristic: two different weaknesses on the same control will match
  each other.
- Doesn't judge the *quality* of an implementation narrative, only that one exists and isn't placeholder text.
- Severity names it doesn't recognize are reported as "unknown" (POAM-005), not guessed.
- The readiness score is the tool's own measure, the AO brief is a draft, and neither is an
  authorization decision.

## Development

```bash
pip install -e ".[dev]"
pytest --cov=ato_readiness_checker
ruff check . && ruff format --check .
python tools/make_samples.py              # rebuild samples/ after changing the script or the code
ato-readiness-checker list-checks --markdown > docs/checks.md
```

CI runs lint, tests on Python 3.10–3.14, a samples/docs drift check, and an OSCAL job that downloads
NIST's v1.1.2 schemas, verifies their SHA-256, validates every sample input and output, and checks
that the gate passes the clean package and blocks the flawed one.

## License

[Apache-2.0](LICENSE). Copyright 2026 Juliet Rodriguez.
