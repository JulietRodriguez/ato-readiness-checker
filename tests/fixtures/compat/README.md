# Compatibility fixtures

Real output from Juliet Rodriguez's other OSCAL tools, generated from each
repo's own synthetic example data. The tests feed these to the checker to prove
it reads what those tools write.

| File | Produced by | Commit | Input |
|---|---|---|---|
| `oscal-ssp-generator_ssp.json` | oscal-ssp-generator | bd12541 | `examples/terraform.tfstate` |
| `fedramp-control-validator_ar.json` | fedramp-control-validator | 57f177c | `examples/aws_config_findings.json` |
| `cmmc-scorecard_ar.json` | cmmc-scorecard | c80ccfc | `samples/prowler_sample.json` |
| `poam-generator_poam.json` | poam-generator | c19d097 | built-in demo findings |
| `stig-poam-builder_poam.json` | stig-poam-builder | e597b03 | `samples/outputs/poam_2026-11-17.oscal.json` |

These files come from different sample systems, so a review that combines them
is expected to report mismatches (different system IDs, findings without POA&M
items). The tests check what is parsed, not that the combination is clean.
