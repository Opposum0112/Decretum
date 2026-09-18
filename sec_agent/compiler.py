"""Compile a validated Decretum recipe into an agent-executable research contract."""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True, slots=True)
class ExecutionContract:
    contract_id: str
    contract: dict[str, Any]
    artifact_dir: Path

def _capabilities(recipe: dict[str, Any]) -> dict[str, list[str]]:
    result: set[str] = {"artifact.read", "artifact.collect"}
    evidence = recipe.get("evidence", {})
    workload = recipe.get("workload", {})
    instrumentation = recipe.get("instrumentation", {})
    if workload.get("command"):
        result.add("process.execute")
    for tool in instrumentation.get("tools", []) or []:
        if tool in {"strace", "tetragon", "bpftrace"}:
            result.add("process.observe")
        if tool in {"tcpdump", "tshark"}:
            result.update({"network.observe", "network.capture"})
    for artifact in evidence.get("required", []) or []:
        text = str(artifact).lower()
        if any(x in text for x in ("pcap", "network", "dns")):
            result.add("network.observe")
        if any(x in text for x in ("proc", "process", "syscall")):
            result.add("process.observe")
        if any(x in text for x in ("file", "diff", "filesystem")):
            result.add("filesystem.observe")
    return {"required": sorted(result), "optional": [], "denied": [
        "host.filesystem.write", "host.mount", "privileged.host_access", "unrestricted.network", "cloud.sandbox"
    ]}

def compile_recipe(recipe: dict[str, Any], artifact_dir: Path) -> ExecutionContract:
    capabilities = _capabilities(recipe)
    body = {
        "apiVersion": "decretum.dev/v1", "kind": "ResearchContract",
        "research": {"id": recipe["id"], "name": recipe["name"], "version": recipe["version"],
                     "role": recipe["role"], "objective": recipe["objective"],
                     "references": recipe.get("references", [])},
        "inputs": recipe.get("inputs", {}),
        "environment": recipe["environment"],
        "roles": [{"id": recipe["role"], "skills": [s.get("id") for s in recipe.get("skills", []) or []]}],
        "skills": recipe.get("skills", []),
        "capabilities": recipe.get("capabilities", []) or [cap for skill in (recipe.get("skills", []) or []) for cap in (skill.get("capabilities", []) or [])],
        "orchestration": recipe["environment"].get("orchestration", {"executor": "codex", "mode": "interactive"}),
        "capabilities": capabilities,
        "policy": recipe["policy"], "evidence": recipe["evidence"],
        "completion": recipe["completion"], "workload": recipe.get("workload", {}),
        "reports": recipe.get("reports", [])
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    contract_id = hashlib.sha256(canonical).hexdigest()[:16]
    return ExecutionContract(contract_id, {**body, "contract_id": contract_id}, artifact_dir)

def write_contract(contract: ExecutionContract) -> Path:
    contract.artifact_dir.mkdir(parents=True, exist_ok=True)
    path = contract.artifact_dir / "research-contract.json"
    path.write_text(json.dumps(contract.contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
