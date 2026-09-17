"""Role-aware report rendering."""
from __future__ import annotations
import json

ROLE_OUTPUTS = {
    "supply_chain_auditor": ("CycloneDX SBOM", "risk report"),
    "detection_engineer": ("Sigma rules", "ATT&CK mapping"),
    "threat_researcher": ("STIX 2.1 bundle", "threat research report"),
    "vulnerability_exploit_researcher": ("RCA report", "crash analysis"),
}

def render(role: str, findings: dict[str, object]) -> str:
    if role not in ROLE_OUTPUTS: raise ValueError(f"unsupported role: {role}")
    primary, secondary = ROLE_OUTPUTS[role]
    return f"# Decretum {role}\n\nOutputs: **{primary}** and **{secondary}**.\n\n## Findings\n\n```json\n{json.dumps(findings, indent=2, sort_keys=True, default=str)}\n```\n"
