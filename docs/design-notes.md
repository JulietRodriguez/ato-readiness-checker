# Design notes

Why ato-readiness-checker works the way it does, in plain language. Each section is a choice I made,
the reason for it, and what I gave up.

## 1. What "ready" means here

**Choice:** "Ready" means the package is complete and internally consistent enough for the AO to make
a decision. It does not mean the system is secure enough to authorize.

**Why:** In RMF the AO weighs residual risk (NIST SP 800-37 Rev. 2, Authorize step). A reviewer's job
before that meeting is to make sure the AO is looking at a package that holds together: the SSP
matches the assessment, every weakness is on the POA&M, every POA&M item has a date and an owner.
A tool that said "authorize" or "deny" would be taking the AO's decision, so this one never does.

**Trade-off:** The tool can call a package READY FOR REVIEW while the system still has serious risk.
That's deliberate, and it's why risk gets its own section (next).

## 2. Risk is reported, but kept out of the readiness level

**Choice:** Two checks are in a "risk" category: open Critical/High/CAT I weaknesses (RISK-001) and
accepted risks (RISK-002). They appear in the report and the AO brief, but they don't change the
readiness score or level. The `--fail-on` gate still counts them.

**Why:** I first wrote "open High item" as a critical package issue. Then the clean sample package,
which is complete and correct but has two open High items, came out NOT READY. That was wrong: the
package was ready; the *system* had risk. Mixing the two would push teams to close POA&M items on
paper to make the package "pass". Keeping them separate lets the report say both things honestly:
"the package is ready" and "here are the two High risks the AO must weigh". A team that wants CI to
block on open Critical items can still do that with `--fail-on critical`.

## 3. The level comes from the worst issue; the score is secondary

**Choice:** NOT READY if any critical package issue, NEEDS WORK if any high one, otherwise READY FOR
REVIEW. The 0–100 score is a weighted average of each check's pass rate (critical 10, high 5,
medium 2, low 1).

**Why:** Averages hide problems. The flawed sample scores 84.7 because most of its hundreds of
objects are fine, but one overdue High POA&M item makes it NOT READY. The score is useful for
tracking progress between drafts; the level is what you act on.

**Trade-off:** The weights are my judgment, not a standard. The docs say so, and both the score and
the level are labeled as the tool's own measure everywhere they appear.

## 4. Two ways to link a finding to a POA&M item

**Choice:** First look for an OSCAL UUID link (the POA&M item's `related-findings` or
`related-observations` point at the assessment finding or its observation). If there isn't one,
match on the control ID. The report shows which method matched (`uuid`, `control` or `none`).

**Why:** The UUID link is the correct OSCAL way and is unambiguous. But in practice the AR and the
POA&M come from different tools (my fedramp-control-validator and poam-generator, for example), and
their UUIDs never line up. Matching on the control is how an ISSO would do it by hand. Showing the
method keeps the weaker match visible.

**Trade-off:** Two different weaknesses on the same control will match each other by control ID.
That's listed as a known limit.

## 5. One canonical control ID

**Choice:** Every control ID is reduced to the OSCAL catalog form before comparing: `AC-2(1)`,
`ac-2.1`, `ac-2.1_smt` and `ac-2_obj` all become `ac-2.1`. CMMC practice IDs like `AC.L2-3.1.1` are
kept as they are, apart from case.

**Why:** My own tools write control IDs four different ways (uppercase in the SSP generator,
`_obj` objective IDs in the validator, `_smt` statement IDs in both POA&M tools). Without
normalizing, every comparison would fail and the tool would report false gaps.

## 6. Severity is read from many places and bucketed

**Choice:** Severity is read from props named `severity`, `severity-category`, `risk-level` and
similar, and from risk characterization facets, in any namespace. It's bucketed into Critical, High
(including DISA CAT I), Moderate (CAT II) and Low (CAT III). If more than one value is found, the
worst one wins. Anything unrecognized is "unknown", and POAM-005 flags it.

**Why:** OSCAL doesn't standardize where weakness severity goes, so each tool picks its own prop.
Taking the worst value means the tool never understates a weakness. Flagging unknown severity is
better than guessing.

## 7. Where the POA&M's owner and milestones come from

**Choice:** A point of contact is accepted from a `point-of-contact` prop, a `party` in the item's or
risk's `origins`, or a party on a remediation task's `responsible-roles`. Milestones are remediation
tasks of type `milestone` (including nested tasks), with dates from `on-date` or the end of
`within-date-range`.

**Why:** These are the OSCAL-native places (origins, tasks) plus the prop my poam-generator uses.
Accepting all of them means the check reflects whether an owner exists, not which field the author
happened to use.

## 8. Every check counts objects, not just pass/fail

**Choice:** Each check records how many objects it looked at and which ones failed, with a reference
(the control, the POA&M item title plus the first 8 characters of its UUID, the file name).

**Why:** "CTRL-002 failed" isn't actionable. "CTRL-002: AU-9 has no implementation narrative" is.
The counts also feed the score. The UUID prefix keeps two POA&M items with the same title apart.

## 9. A baseline is an input, not built in

**Choice:** The tool doesn't ship 800-53B or FedRAMP baselines. You give it one with `--baseline`
(OSCAL profile, OSCAL catalog, JSON list or text list), or it follows the SSP's `import-profile` when
that points at a local file. Without a baseline, the baseline coverage check is skipped (and the
report says so) and the SSP's own control list is used as the scope for "was every control assessed".

**Why:** Shipping baselines means keeping them current. My next repo (security-categorizer) produces
the baseline from the categorization, and this tool takes it as input. That's the RMF order:
categorize, select, then authorize.

**Trade-off:** A profile that uses `include-all` can't be resolved without its catalog, so the
tool refuses it with a clear message instead of guessing.

## 10. Schema validation is one check, not the whole review

**Choice:** NIST schema validation is optional (`--schema-dir`, check REF-006). Every flawed sample
document still passes the schema.

**Why:** This is the main point of the tool. The schema says a POA&M item needs a title and a UUID.
It can't say that the item's due date passed 47 days ago, or that the SSP calls a control
implemented when the assessment says it isn't. Those are the problems that get packages sent back.

## 11. The AO brief is a draft and decides nothing

**Choice:** The brief is one page: system and categorization, package readiness, risk summary, open
Critical/High/CAT I items with due dates and owners, accepted risks, and the decision options (ATO,
ATO with conditions, DATO) with empty boxes and a blank signature line. "DRAFT FOR HUMAN REVIEW. This
is not an authorization decision." is at the top, and the disclaimer is at the bottom.

**Why:** AOs are busy; the brief is the summary I'd want to hand one. But the recommendation and the
decision belong to people: the ISSM/SCA recommends and the AO decides. The tool fills in facts and
leaves every judgment blank.

## 12. The review is also written as OSCAL

**Choice:** `--oscal` writes the review as OSCAL 1.1.2 Assessment Results: one result, one
observation (method EXAMINE) per failed check, with the input documents listed as back-matter
resources and used as the observation subjects. The readiness score and level are props on the result.

**Why:** OSCAL has no "package review" model, and a readiness review is an examination of documents,
which is what an AR result records. Writing OSCAL means the next tool in my RMF pipeline (rmf-toolchain)
can read the review in a standard format. The result's description and remarks say plainly that it
is a document review, not a control assessment, and `reviewed-controls` uses `include-all` because no
control was tested.

## 13. Offline, deterministic, no runtime dependencies

**Choice:** The checks and all report formats use only the Python standard library. Nothing is
fetched from the network (remote `import-profile` links are ignored on purpose). Dates are judged
against `--as-of`. OSCAL output uses UUIDv5 values derived from the system name, the date and the
check ID.

**Why:** A package review should give the same answer every time it runs on the same files, including
inside an air-gapped enclave. No dependencies also means nothing to get through a software approval
board before the tool can run. jsonschema is optional, and only needed for `--schema-dir`.

## 14. Safe handling of other people's files

**Choice:** Inputs over 200 MB are refused. JSON is parsed with the standard library. The HTML
reports escape every value taken from the input documents, and include no scripts and no external
assets. Markdown table cells escape pipes and flatten newlines.

**Why:** An SSP is free text written by someone else. A title like `<script>` must show up as text
in the report, not run.

## 15. Synthetic samples with a drift check

**Choice:** `tools/make_samples.py` builds a clean package and a flawed copy, with each defect tagged
with the check that should catch it, plus every output for both. CI regenerates everything and fails
if the committed files differ.

**Why:** The samples are the demo, the documentation and the regression test at once. The tests
assert that each tagged defect is caught by the check it's tagged with, and that no other package
check fails, so a change in check behavior shows up immediately.
