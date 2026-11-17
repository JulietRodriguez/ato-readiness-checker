"""Build the synthetic sample packages in samples/.

    python tools/make_samples.py            # write samples/clean and samples/flawed
    python tools/make_samples.py --check    # exit 1 if the committed files differ

Everything here is SYNTHETIC: an invented system, invented parties (named by
role only), invented findings. No real system data and no CUI.

samples/clean   -- a complete, consistent package. It still carries risk (two
                   open High items and one accepted risk) because a ready
                   package and a risk-free system are different things.
samples/flawed  -- the same package with deliberate defects. Each defect is
                   tagged with the check that should catch it. Every flawed
                   document is still valid against NIST's OSCAL schemas: the
                   point is that schema-valid is not the same as AO-ready.

Output is deterministic (UUIDv5 and fixed dates) so the files only change
when this script changes.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
NS_ROOT = uuid.UUID("6d1b0b5a-6a0e-5c38-9a51-3a1b8f0c2e11")
OSCAL = "1.1.2"
FED_NS = "https://github.com/JulietRodriguez/ato-readiness-checker/ns/oscal"
SYSTEM = "SYNTHETIC Case Management System (CMS-DEMO)"
LAST_MODIFIED = "2026-11-01T00:00:00+00:00"


def uid(*parts: str) -> str:
    return str(uuid.uuid5(NS_ROOT, "|".join(parts)))


SYSTEM_ID = uid("system")

# --- parties and roles ----------------------------------------------------------

PARTIES = {
    "owner": ("System Owner, CMS-DEMO (synthetic)", "system-owner"),
    "ao": ("Authorizing Official, Example Agency (synthetic)", "authorizing-official"),
    "isso": ("ISSO, CMS-DEMO (synthetic)", "isso"),
    "sysadmin": ("Lead Systems Administrator, CMS-DEMO (synthetic)", None),
    "dba": ("Database Administrator, CMS-DEMO (synthetic)", None),
}
ROLES = [
    {"id": "system-owner", "title": "System Owner"},
    {"id": "authorizing-official", "title": "Authorizing Official"},
    {"id": "isso", "title": "Information System Security Officer"},
    {"id": "system-administrator", "title": "System Administrator"},
]


def party(key: str) -> dict:
    return {"uuid": uid("party", key), "type": "person", "name": PARTIES[key][0]}


# --- baseline ------------------------------------------------------------------------

# A small synthetic subset, enough to exercise every check. Not an official baseline.
BASELINE = [
    "ac-2", "ac-3", "ac-6", "ac-17", "ac-18", "au-2", "au-6", "au-9", "ca-7", "cm-2", "cm-6",
    "cm-8", "cp-9", "ia-2", "ia-2.1", "ia-5", "ra-5", "sc-7", "sc-8", "sc-28", "si-2", "si-4",
]  # fmt: skip

TITLES = {
    "ac-2": "Account Management", "ac-3": "Access Enforcement", "ac-6": "Least Privilege",
    "ac-17": "Remote Access", "ac-18": "Wireless Access", "au-2": "Event Logging",
    "au-6": "Audit Record Review, Analysis, and Reporting", "au-9": "Protection of Audit Information",
    "ca-7": "Continuous Monitoring", "cm-2": "Baseline Configuration", "cm-6": "Configuration Settings",
    "cm-8": "System Component Inventory", "cp-9": "System Backup",
    "ia-2": "Identification and Authentication (Organizational Users)",
    "ia-2.1": "Multi-factor Authentication to Privileged Accounts", "ia-5": "Authenticator Management",
    "ra-5": "Vulnerability Monitoring and Scanning", "sc-7": "Boundary Protection",
    "sc-8": "Transmission Confidentiality and Integrity", "sc-28": "Protection of Information at Rest",
    "si-2": "Flaw Remediation", "si-4": "System Monitoring",
}  # fmt: skip


def display(cid: str) -> str:
    fam, _, rest = cid.partition("-")
    num, _, enh = rest.partition(".")
    return f"{fam.upper()}-{num}" + (f"({enh})" if enh else "")


def baseline_profile() -> dict:
    return {
        "profile": {
            "uuid": uid("profile"),
            "metadata": {
                "title": "SYNTHETIC sample baseline (22-control subset for demonstration; not an official baseline)",
                "last-modified": LAST_MODIFIED,
                "version": "1.0",
                "oscal-version": OSCAL,
            },
            "imports": [
                {
                    "href": "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json",
                    "include-controls": [{"with-ids": BASELINE}],
                }
            ],
        }
    }


# --- SSP ------------------------------------------------------------------------------

COMPONENTS = {
    "this-system": ("this-system", "CMS-DEMO", "The case management system as a whole."),
    "web": ("software", "Case management web application", "Containerized web application tier."),
    "db": ("software", "Case database", "Managed PostgreSQL database holding case records."),
    "idp": ("service", "Identity provider", "Agency single sign-on with MFA."),
    "log": ("service", "Central logging", "Log aggregation and alerting service."),
}

# control -> (status, component keys, narrative)
IMPLEMENTATION = {
    "ac-2": ("partial", ["idp"], "Accounts are provisioned through the identity provider; quarterly privileged "
             "account reviews are being automated (see POA&M)."),
    "ac-3": ("implemented", ["web"], "Role-based access checks in the application enforce approved authorizations."),
    "ac-6": ("implemented", ["web", "db"], "Application and database roles grant least privilege by job function."),
    "ac-17": ("implemented", ["idp"], "Remote access is only through the SSO portal over TLS with MFA."),
    "ac-18": ("not-applicable", [], "The system has no wireless components; it runs in a cloud region with no "
              "wireless access to the boundary."),
    "au-2": ("implemented", ["log"], "Security-relevant events from all tiers are sent to central logging."),
    "au-6": ("partial", ["log"], "Audit records are reviewed weekly; daily review is a documented risk acceptance."),
    "au-9": ("implemented", ["log"], "Logs are stored write-once with access limited to the security team."),
    "ca-7": ("implemented", ["this-system"], "Monthly continuous monitoring reports go to the AO."),
    "cm-2": ("implemented", ["web", "db"], "Infrastructure-as-code defines the approved baseline configuration."),
    "cm-6": ("partial", ["web"], "Hardened settings are applied; three container settings deviate (see POA&M)."),
    "cm-8": ("planned", ["this-system"], "An automated component inventory feed is planned (see POA&M)."),
    "cp-9": ("implemented", ["db"], "Daily encrypted database backups are retained for 35 days."),
    "ia-2": ("implemented", ["idp"], "All organizational users authenticate through the agency identity provider."),
    "ia-2.1": ("implemented", ["idp"], "The identity provider enforces MFA for privileged accounts."),
    "ia-5": ("implemented", ["idp"], "Authenticator lifetime and strength are enforced by identity provider policy."),
    "ra-5": ("partial", ["this-system"], "Weekly scans cover the web tier; authenticated database scans are "
             "being added (see POA&M)."),
    "sc-7": ("implemented", ["web"], "A web application firewall and security groups restrict traffic at the "
             "boundary."),
    "sc-8": ("implemented", ["web"], "TLS 1.2 or higher protects all data in transit."),
    "sc-28": ("implemented", ["db"], "Case data at rest is encrypted with agency-managed keys."),
    "si-2": ("partial", ["web", "db"], "Monthly patching is in place; two High findings are being remediated."),
    "si-4": ("implemented", ["log"], "Alerting rules in central logging monitor for indicators of attack."),
}  # fmt: skip


def ssp() -> dict:
    components = []
    for key, (ctype, title, desc) in COMPONENTS.items():
        components.append(
            {"uuid": uid("comp", key), "type": ctype, "title": title, "description": desc,
             "status": {"state": "operational"}}
        )  # fmt: skip
    inventory = [
        {
            "uuid": uid("inv", key),
            "description": f"{COMPONENTS[key][1]} (synthetic asset)",
            "props": [{"name": "asset-type", "value": "software" if key in ("web", "db") else "service"}],
            "implemented-components": [{"component-uuid": uid("comp", key)}],
        }
        for key in ("web", "db", "idp", "log")
    ]
    reqs = []
    for cid, (status, comps, text) in IMPLEMENTATION.items():
        req = {
            "uuid": uid("req", cid),
            "control-id": cid,
            "props": [{"name": "implementation-status", "value": status}],
        }
        if comps:
            req["by-components"] = [
                {
                    "component-uuid": uid("comp", c),
                    "uuid": uid("byc", cid, c),
                    "description": text,
                    "implementation-status": {"state": status},
                }
                for c in comps
            ]
        else:
            req["remarks"] = text
        reqs.append(req)
    return {
        "system-security-plan": {
            "uuid": uid("ssp"),
            "metadata": {
                "title": f"System Security Plan: {SYSTEM}",
                "last-modified": LAST_MODIFIED,
                "version": "2.0",
                "oscal-version": OSCAL,
                "roles": ROLES,
                "parties": [party(k) for k in PARTIES],
                "responsible-parties": [
                    {"role-id": role, "party-uuids": [uid("party", key)]} for key, (_, role) in PARTIES.items() if role
                ],
                "remarks": "SYNTHETIC sample for ato-readiness-checker. Not a real system.",
            },
            "import-profile": {"href": "baseline-profile.json"},
            "system-characteristics": {
                "system-ids": [{"identifier-type": "https://ietf.org/rfc/rfc4122", "id": SYSTEM_ID}],
                "system-name": SYSTEM,
                "system-name-short": "CMS-DEMO",
                "description": "A synthetic case management system used to demonstrate package review.",
                "security-sensitivity-level": "fips-199-moderate",
                "system-information": {
                    "information-types": [
                        {
                            "uuid": uid("info", "case-records"),
                            "title": "Case records (synthetic information type)",
                            "description": "Case files and status history managed by the system.",
                            "confidentiality-impact": {"base": "fips-199-moderate"},
                            "integrity-impact": {"base": "fips-199-moderate"},
                            "availability-impact": {"base": "fips-199-low"},
                        },
                        {
                            "uuid": uid("info", "system-monitoring"),
                            "title": "System and network monitoring (synthetic information type)",
                            "description": "Security logs and monitoring data about the system.",
                            "confidentiality-impact": {"base": "fips-199-low"},
                            "integrity-impact": {"base": "fips-199-moderate"},
                            "availability-impact": {"base": "fips-199-low"},
                        },
                    ]
                },
                "security-impact-level": {
                    "security-objective-confidentiality": "fips-199-moderate",
                    "security-objective-integrity": "fips-199-moderate",
                    "security-objective-availability": "fips-199-low",
                },
                "status": {"state": "operational"},
                "authorization-boundary": {
                    "description": "The boundary covers the web application, case database, and the tenant "
                    "configuration of the identity provider and central logging services."
                },
                "network-architecture": {
                    "description": "Users reach the web tier through a web application firewall; the web tier "
                    "reaches the database on a private subnet only."
                },
                "data-flow": {
                    "description": "Case data flows from users over TLS to the web tier and is stored encrypted "
                    "in the database; security events flow to central logging."
                },
            },
            "system-implementation": {
                "users": [
                    {"uuid": uid("user", "caseworker"), "title": "Caseworker", "role-ids": ["system-administrator"]},
                ],
                "components": components,
                "inventory-items": inventory,
            },
            "control-implementation": {
                "description": "How CMS-DEMO implements each control in its baseline.",
                "implemented-requirements": reqs,
            },
        }
    }


# --- Assessment Results ---------------------------------------------------------------

# control -> (state, severity of the weakness if not satisfied, component assessed, observation text)
ASSESSMENT = {
    "ac-2": ("not-satisfied", "high", "idp", "Seven privileged accounts belong to staff who left more than "
             "90 days ago."),
    "si-2": ("not-satisfied", "high", "web", "Two High-severity patches are more than 30 days past release."),
    "ra-5": ("not-satisfied", "moderate", "db", "The database tier is scanned without credentials."),
    "cm-6": ("not-satisfied", "moderate", "web", "Three container settings deviate from the hardening baseline."),
    "cm-8": ("not-satisfied", "low", "this-system", "The component inventory is maintained by hand."),
    "au-6": ("not-satisfied", "low", "log", "Audit records are reviewed weekly rather than daily."),
}  # fmt: skip
ASSESS_START = "2026-09-14T13:00:00+00:00"
ASSESS_END = "2026-10-09T21:00:00+00:00"


def assessment_results() -> dict:
    observations, findings = [], []
    for cid in BASELINE:
        if cid == "ac-18":
            continue  # not applicable: listed in reviewed-controls, no test performed
        state, severity, comp, text = ASSESSMENT.get(
            cid, ("satisfied", None, IMPLEMENTATION[cid][1][0] if IMPLEMENTATION[cid][1] else "this-system", "")
        )
        obs = {
            "uuid": uid("obs", cid),
            "title": f"{display(cid)} test",
            "description": text or f"{display(cid)} ({TITLES[cid]}) was tested and operates as described in the SSP.",
            "methods": ["TEST"] if state == "not-satisfied" else ["EXAMINE", "TEST"],
            "types": ["finding"] if state == "not-satisfied" else ["control-objective"],
            "subjects": [{"subject-uuid": uid("comp", comp), "type": "component"}],
            "collected": ASSESS_END,
        }
        observations.append(obs)
        finding = {
            "uuid": uid("finding", cid),
            "title": f"{display(cid)} {TITLES[cid]}",
            "description": text or f"{display(cid)} is satisfied.",
            "target": {"type": "objective-id", "target-id": f"{cid}_obj", "status": {"state": state}},
            "related-observations": [{"observation-uuid": obs["uuid"]}],
        }
        if severity:
            finding["props"] = [{"name": "severity", "ns": FED_NS, "value": severity}]
        findings.append(finding)
    return {
        "assessment-results": {
            "uuid": uid("ar"),
            "metadata": {
                "title": f"Security Assessment Results: {SYSTEM}",
                "last-modified": LAST_MODIFIED,
                "version": "1.0",
                "oscal-version": OSCAL,
                "remarks": "SYNTHETIC sample for ato-readiness-checker. Not a real assessment.",
            },
            "import-ap": {"href": "#" + uid("ap-resource")},
            "results": [
                {
                    "uuid": uid("result"),
                    "title": "Annual assessment 2026",
                    "description": "Assessment of the CMS-DEMO baseline controls.",
                    "start": ASSESS_START,
                    "end": ASSESS_END,
                    "reviewed-controls": {
                        "control-selections": [{"include-controls": [{"control-id": c} for c in BASELINE]}]
                    },
                    "observations": observations,
                    "findings": findings,
                }
            ],
            "back-matter": {
                "resources": [
                    {
                        "uuid": uid("ap-resource"),
                        "title": "Security Assessment Plan, CMS-DEMO (synthetic, not included)",
                    }
                ]
            },
        }
    }


# --- POA&M --------------------------------------------------------------------------------

# key -> settings for one POA&M item
POAM_ITEMS = {
    "ac2": {
        "control": "ac-2", "severity": "High", "status": "remediating", "deadline": "2027-01-15",
        "title": "Stale privileged accounts", "link": "finding", "poc": ("origin", "isso"),
        "milestones": [("Disable the seven stale accounts", "2026-11-30"),
                       ("Automate quarterly privileged account review", "2027-01-15")],
    },
    "si2": {
        "control": "si-2", "severity": "High", "status": "open", "deadline": "2026-12-17",
        "title": "High-severity patches past due", "link": "observation", "poc": ("prop", "sysadmin"),
        "milestones": [("Apply patches in staging", "2026-12-03"), ("Apply patches in production", "2026-12-17")],
    },
    "ra5": {
        "control": "ra-5", "severity": "Moderate", "status": "remediating", "deadline": "2027-02-26",
        "title": "Database tier scanned without credentials", "link": "finding", "poc": ("origin", "dba"),
        "milestones": [("Create scan service account", "2027-01-29"), ("Run first authenticated scan", "2027-02-26")],
    },
    "cm6": {
        "control": "cm-6", "severity": "Moderate", "status": "open", "deadline": "2027-03-31",
        "title": "Container settings deviate from hardening baseline", "link": "control", "poc": ("prop", "sysadmin"),
        "milestones": [("Update container build files", "2027-03-31")],
    },
    "cm8": {
        "control": "cm-8", "severity": "Low", "status": "open", "deadline": "2027-04-30",
        "title": "Automated component inventory not yet in place", "link": "finding", "poc": ("task", "isso"),
        "milestones": [("Select inventory tool", "2027-02-01"), ("Feed inventory into ConMon", "2027-04-30")],
    },
    "au6": {
        "control": "au-6", "severity": "Low", "status": "deviation-approved", "deadline": "2027-10-31",
        "title": "Weekly (not daily) audit review: risk accepted", "link": "finding", "poc": ("prop", "isso"),
        "milestones": [("Re-evaluate risk acceptance", "2027-10-31")],
    },
    "sc8": {
        "control": "sc-8", "severity": "Moderate", "status": "closed", "deadline": "2026-08-31",
        "title": "TLS 1.0 enabled on legacy endpoint (closed)", "link": "control", "poc": ("prop", "sysadmin"),
        "milestones": [("Disable TLS 1.0", "2026-08-31")],
    },
}  # fmt: skip


def _prop(name: str, value: str) -> dict:
    return {"name": name, "ns": FED_NS, "value": value}


def poam() -> dict:
    risks, items, findings = [], [], []
    for key, cfg in POAM_ITEMS.items():
        risk_uuid = uid("risk", key)
        tasks = [
            {
                "uuid": uid("task", key, str(i)),
                "type": "milestone",
                "title": title,
                "timing": {"on-date": {"date": f"{day}T00:00:00+00:00"}},
            }
            for i, (title, day) in enumerate(cfg["milestones"])
        ]
        how, who = cfg["poc"]
        remediation = {
            "uuid": uid("rem", key),
            "lifecycle": "completed" if cfg["status"] == "closed" else "planned",
            "title": "Remediation plan",
            "description": f"Plan to resolve: {cfg['title']}.",
            "tasks": tasks,
        }
        if how == "task":
            tasks[0]["responsible-roles"] = [{"role-id": "isso", "party-uuids": [uid("party", who)]}]
        risks.append(
            {
                "uuid": risk_uuid,
                "title": cfg["title"],
                "description": f"{cfg['title']} ({display(cfg['control'])}).",
                "statement": f"Weakness in {display(cfg['control'])} {TITLES[cfg['control']]}.",
                "props": [_prop("severity", cfg["severity"])],
                "status": cfg["status"],
                "deadline": f"{cfg['deadline']}T23:59:59+00:00",
                "remediations": [remediation],
            }
        )
        item = {
            "uuid": uid("item", key),
            "title": cfg["title"],
            "description": f"{cfg['title']} ({display(cfg['control'])}).",
            "props": [_prop("control", display(cfg["control"])), _prop("severity", cfg["severity"])],
            "related-risks": [{"risk-uuid": risk_uuid}],
        }
        if how == "prop":
            item["props"].append(_prop("point-of-contact", PARTIES[who][0]))
        if how == "origin":
            item["origins"] = [{"actors": [{"type": "party", "actor-uuid": uid("party", who)}]}]
        if cfg["link"] == "finding":
            item["related-findings"] = [{"finding-uuid": uid("finding", cfg["control"])}]
        elif cfg["link"] == "observation":
            item["related-observations"] = [{"observation-uuid": uid("obs", cfg["control"])}]
        else:  # link by control through a POA&M-local finding
            fid = uid("poam-finding", key)
            findings.append(
                {
                    "uuid": fid,
                    "title": f"{display(cfg['control'])} weakness",
                    "description": cfg["title"],
                    "target": {
                        "type": "statement-id",
                        "target-id": f"{cfg['control']}_smt",
                        "status": {"state": "satisfied" if cfg["status"] == "closed" else "not-satisfied"},
                    },
                    "related-risks": [{"risk-uuid": risk_uuid}],
                }
            )
            item["related-findings"] = [{"finding-uuid": fid}]
        items.append(item)
    return {
        "plan-of-action-and-milestones": {
            "uuid": uid("poam"),
            "metadata": {
                "title": f"POA&M: {SYSTEM}",
                "last-modified": LAST_MODIFIED,
                "version": "2026.11",
                "oscal-version": OSCAL,
                "roles": ROLES,
                "parties": [party(k) for k in ("isso", "sysadmin", "dba")],
                "remarks": "SYNTHETIC sample for ato-readiness-checker. Not a real POA&M.",
            },
            "import-ssp": {"href": "ssp.json"},
            "system-id": {"identifier-type": "https://ietf.org/rfc/rfc4122", "id": SYSTEM_ID},
            "risks": risks,
            "findings": findings,
            "poam-items": items,
        }
    }


# --- flawed package -----------------------------------------------------------------------


def _req(doc: dict, cid: str) -> dict:
    reqs = doc["system-security-plan"]["control-implementation"]["implemented-requirements"]
    return next(r for r in reqs if r["control-id"] == cid)


def _item(doc: dict, key: str) -> dict:
    return next(i for i in doc["plan-of-action-and-milestones"]["poam-items"] if i["uuid"] == uid("item", key))


def _risk(doc: dict, key: str) -> dict:
    return next(r for r in doc["plan-of-action-and-milestones"]["risks"] if r["uuid"] == uid("risk", key))


def flawed(clean_ssp: dict, clean_ar: dict, clean_poam: dict) -> tuple[dict, dict, dict]:
    s, a, p = copy.deepcopy(clean_ssp), copy.deepcopy(clean_ar), copy.deepcopy(clean_poam)
    root = s["system-security-plan"]
    chars = root["system-characteristics"]
    reqs = root["control-implementation"]["implemented-requirements"]

    del chars["data-flow"]  # SSP-001
    chars["security-impact-level"]["security-objective-confidentiality"] = "fips-199-low"  # SSP-002
    root["metadata"]["responsible-parties"] = [  # SSP-003: no AO assigned
        rp for rp in root["metadata"]["responsible-parties"] if rp["role-id"] != "authorizing-official"
    ]
    chars["authorization-boundary"]["description"] = "TBD: boundary diagram to be inserted."  # SSP-004
    root["control-implementation"]["implemented-requirements"] = [  # CTRL-001: IA-2(1) missing
        r for r in reqs if r["control-id"] != "ia-2.1"
    ]
    au9 = _req(s, "au-9")  # CTRL-002: no narrative at all
    del au9["by-components"]
    cp9 = _req(s, "cp-9")  # CTRL-003: control says implemented, component says partial
    cp9["by-components"][0]["implementation-status"]["state"] = "partial"
    si2 = _req(s, "si-2")  # CTRL-004: SSP claims implemented, assessment says not satisfied
    si2["props"][0]["value"] = "implemented"
    for bc in si2["by-components"]:
        bc["implementation-status"]["state"] = "implemented"
    ac18 = _req(s, "ac-18")  # CTRL-006: not-applicable with no justification
    del ac18["remarks"]

    result = a["assessment-results"]["results"][0]
    result["start"], result["end"] = "2025-08-04T13:00:00+00:00", "2025-08-29T21:00:00+00:00"  # AR-003
    sel = result["reviewed-controls"]["control-selections"][0]
    sel["include-controls"] = [c for c in sel["include-controls"] if c["control-id"] != "sc-28"]  # AR-002
    result["findings"] = [f for f in result["findings"] if f["target"]["target-id"] != "sc-28_obj"]
    # TRC-001 (no POA&M item) and CTRL-004 (the SSP still says implemented)
    ia5 = next(f for f in result["findings"] if f["target"]["target-id"] == "ia-5_obj")
    ia5["target"]["status"]["state"] = "not-satisfied"
    ia5["description"] = "Service account passwords never expire."
    ia5["props"] = [{"name": "severity", "ns": FED_NS, "value": "moderate"}]
    obs = next(o for o in result["observations"] if o["uuid"] == uid("obs", "si-4"))
    obs["subjects"][0]["subject-uuid"] = uid("comp", "unlisted-siem-forwarder")  # REF-002

    pr = p["plan-of-action-and-milestones"]
    pr["metadata"]["oscal-version"] = "1.1.1"  # REF-005
    pr["system-id"]["id"] = uid("some-other-system")  # REF-003
    pr["poam-items"] = [i for i in pr["poam-items"] if i["uuid"] != uid("item", "cm8")]  # CTRL-005, TRC-001
    pr["risks"] = [r for r in pr["risks"] if r["uuid"] != uid("risk", "cm8")]
    _risk(p, "ac2")["deadline"] = "2026-10-01T23:59:59+00:00"  # POAM-004: High item overdue -> critical
    for t, day in zip(_risk(p, "ac2")["remediations"][0]["tasks"], ("2026-09-01", "2026-10-01"), strict=True):
        t["timing"]["on-date"]["date"] = f"{day}T00:00:00+00:00"
    del _risk(p, "ra5")["deadline"]  # POAM-001
    del _risk(p, "cm6")["remediations"][0]["tasks"]  # POAM-002
    si2_item = _item(p, "si2")  # POAM-003
    si2_item["props"] = [x for x in si2_item["props"] if x["name"] != "point-of-contact"]
    sc8_tasks = _risk(p, "sc8")["remediations"][0]["tasks"]  # REF-004: duplicate UUID
    sc8_tasks.append({**copy.deepcopy(sc8_tasks[0]), "title": "Verify TLS 1.0 is off"})

    orphan_risk = uid("risk", "orphan")  # TRC-002, POAM-005, POAM-006
    pr["risks"].append(
        {
            "uuid": orphan_risk,
            "title": "Legacy finding carried from a prior audit",
            "description": "Carried forward from the 2024 audit; no matching assessment finding.",
            "statement": "Weakness in PL-2 System Security and Privacy Plans.",
            "status": "open",
            "deadline": "2027-01-31T23:59:59+00:00",
            "remediations": [
                {
                    "uuid": uid("rem", "orphan"),
                    "lifecycle": "planned",
                    "title": "Remediation plan",
                    "description": "Update the plan.",
                    "tasks": [
                        {
                            "uuid": uid("task", "orphan", "0"),
                            "type": "milestone",
                            "title": "Update SSP narrative",
                            "timing": {"on-date": {"date": "2027-03-15T00:00:00+00:00"}},
                        }
                    ],
                }
            ],
        }
    )
    pr["poam-items"].append(
        {
            "uuid": uid("item", "orphan"),
            "title": "Legacy finding carried from a prior audit",
            "description": "No severity recorded; milestone falls after the due date.",
            "props": [_prop("control", "PL-2"), _prop("point-of-contact", PARTIES["isso"][0])],
            "related-risks": [{"risk-uuid": orphan_risk}, {"risk-uuid": uid("risk", "deleted-risk")}],  # REF-001
        }
    )
    return s, a, p


# --- write ----------------------------------------------------------------------------


def render(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def build() -> dict[Path, str]:
    clean_ssp, clean_ar, clean_poam = ssp(), assessment_results(), poam()
    bad_ssp, bad_ar, bad_poam = flawed(clean_ssp, clean_ar, clean_poam)
    files = {}
    for name, (s, a, p) in {"clean": (clean_ssp, clean_ar, clean_poam), "flawed": (bad_ssp, bad_ar, bad_poam)}.items():
        folder = SAMPLES / name
        files[folder / "ssp.json"] = render(s)
        files[folder / "assessment-results.json"] = render(a)
        files[folder / "poam.json"] = render(p)
        files[folder / "baseline-profile.json"] = render(baseline_profile())
    return files


AS_OF = "2026-11-17"
GENERATED_AT = "2026-11-17T12:00:00+00:00"


def build_outputs() -> dict[Path, str]:
    """Run the review on both packages and render every output format."""
    import os
    from datetime import date

    sys.path.insert(0, str(ROOT / "src"))
    from ato_readiness_checker.loader import load_package
    from ato_readiness_checker.reports import (
        brief_html,
        brief_markdown,
        report_html,
        report_json,
        report_markdown,
        review_to_oscal,
    )
    from ato_readiness_checker.review import run_review

    files = {}
    cwd = os.getcwd()
    os.chdir(ROOT)  # relative paths keep the outputs identical on every machine
    try:
        for name in ("clean", "flawed"):
            d = f"samples/{name}/"
            pkg = load_package(d + "ssp.json", [d + "assessment-results.json"], [d + "poam.json"])
            review = run_review(pkg, as_of=date.fromisoformat(AS_OF), generated_at=GENERATED_AT)
            out = SAMPLES / "outputs" / name
            files[out / "readiness-report.md"] = report_markdown(review)
            files[out / "readiness-report.html"] = report_html(review)
            files[out / "readiness-report.json"] = report_json(review)
            files[out / "ao-brief-draft.md"] = brief_markdown(review)
            files[out / "ao-brief-draft.html"] = brief_html(review)
            files[out / "readiness-review.oscal.json"] = render(review_to_oscal(review))
    finally:
        os.chdir(cwd)
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if committed samples differ from this script")
    args = ap.parse_args(argv)
    files = build()
    if args.check or all(p.is_file() and p.read_text(encoding="utf-8") == t for p, t in files.items()):
        files.update(build_outputs())
    else:
        # inputs changed: write them first so the outputs are built from the new inputs
        for path, text in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        files.update(build_outputs())
    if args.check:
        stale = [p for p, text in files.items() if not p.is_file() or p.read_text(encoding="utf-8") != text]
        for p in stale:
            print(f"out of date: {p.relative_to(ROOT)}", file=sys.stderr)
        if stale:
            print("run: python tools/make_samples.py", file=sys.stderr)
        return 1 if stale else 0
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
