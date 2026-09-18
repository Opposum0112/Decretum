"""Compile a validated Decretum recipe into an agent-executable research contract."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

INSTRUMENTATION_CAPABILITIES = {
    "sysdig": {"process.observe","filesystem.observe","network.observe","syscall.observe","container.observe"},
    "falco": {"process.observe","filesystem.observe","network.observe","syscall.observe","container.observe","detection.observe"},
    "tracee": {"process.observe","filesystem.observe","network.observe","syscall.observe","container.observe","kernel.trace"},
    "tetragon": {"process.observe","network.observe","filesystem.observe","syscall.observe","container.observe","kernel.trace"},
    "bpftrace": {"process.observe","filesystem.observe","network.observe","syscall.observe","kernel.trace"},
    "bcc": {"process.observe","filesystem.observe","network.observe","syscall.observe","kernel.trace"},
    "strace": {"process.observe","syscall.observe"},
    "ltrace": {"process.observe","library.observe"},
    "perf": {"process.observe","kernel.trace","performance.observe"},
    "ftrace": {"kernel.trace","syscall.observe"},
    "auditd": {"process.observe","filesystem.observe","identity.observe","syscall.observe"},
    "auditbeat": {"process.observe","filesystem.observe","network.observe","identity.observe"},
    "osquery": {"process.observe","filesystem.observe","network.observe","identity.observe","configuration.observe"},
    "tcpdump": {"network.observe","network.capture"},
    "tshark": {"network.observe","network.capture","protocol.analyze"},
    "dumpcap": {"network.capture"},
    "wireshark": {"network.observe","network.capture","protocol.analyze"},
    "zeek": {"network.observe","network.capture","protocol.analyze","network.metadata"},
    "suricata": {"network.observe","network.capture","network.detection"},
    "snort": {"network.observe","network.capture","network.detection"},
    "conntrack": {"network.observe","network.connection_state"},
    "nftables": {"network.observe","network.policy"},
    "iptables": {"network.observe","network.policy"},
    "ss": {"network.observe","network.connection_state"},
    "dig": {"network.observe","dns.observe"},
    "resolvectl": {"network.observe","dns.observe"},
    "bpftool": {"kernel.inspect","kernel.trace"},
    "opensnoop": {"filesystem.observe","process.observe"},
    "execsnoop": {"process.observe","syscall.observe"},
    "tcpconnect": {"network.observe","process.observe"},
    "tcplife": {"network.observe","process.observe"},
    "filetop": {"filesystem.observe","performance.observe"},
    "biolatency": {"filesystem.observe","performance.observe"},
    "runqlat": {"process.observe","performance.observe"},
    "funccount": {"kernel.trace","performance.observe"},
    "volatility": {"memory.acquire","memory.analyze"},
    "rekall": {"memory.acquire","memory.analyze"},
    "yara": {"artifact.scan","malware.analyze"},
    "clamav": {"artifact.scan","malware.analyze"},
    "ghidra": {"binary.analyze","reverse_engineer"},
    "radare2": {"binary.analyze","reverse_engineer"},
    "binwalk": {"artifact.analyze","binary.analyze"},
    "strings": {"binary.inspect","artifact.analyze"},
    "readelf": {"binary.inspect","binary.analyze"},
    "objdump": {"binary.inspect","binary.analyze"},
    "lsof": {"process.observe","filesystem.observe","network.observe"},
    "nsenter": {"namespace.observe","process.observe"},
    "capsh": {"identity.observe","capability.observe"},
    "unshare": {"namespace.observe"},
}
COMPUTE_CAPABILITIES = {
    "unix":{"compute.local","workspace.execute"},"local_unix":{"compute.local","workspace.execute"},
    "docker":{"compute.container","workspace.execute","compute.snapshot"},"podman":{"compute.container","workspace.execute","compute.snapshot"},
    "lima":{"compute.vm","workspace.execute","compute.snapshot"},"incus":{"compute.container","compute.vm","workspace.execute","compute.snapshot"},
    "lxc":{"compute.container","workspace.execute","compute.snapshot"},"kvm":{"compute.vm","workspace.execute","compute.snapshot"},
    "firecracker":{"compute.microvm","workspace.execute","compute.snapshot"},"qemu":{"compute.vm","workspace.execute","compute.snapshot"},
}

@dataclass(frozen=True, slots=True)
class ExecutionContract:
    contract_id: str
    contract: dict[str, Any]
    artifact_dir: Path

def _capabilities(recipe: dict[str, Any]) -> dict[str, list[str]]:
    required = {"artifact.read", "artifact.collect"}
    workload = recipe.get("workload", {}) or {}
    if workload.get("command"):
        required.add("process.execute")
    instrumentation = recipe.get("instrumentation", {}) or {}
    for tool in instrumentation.get("tools", []) or []:
        required.update(INSTRUMENTATION_CAPABILITIES.get(tool, set()))
    for skill in recipe.get("skills", []) or []:
        required.update(skill.get("capabilities", []) or [])
    role = recipe.get("role_definition", {}) or {}
    required.update(role.get("default_capabilities", []) or [])
    environment = recipe.get("environment", {}) or {}
    compute = environment.get("compute", {}) or {}
    sandbox = environment.get("sandbox", {}) or {}
    provider = compute.get("provider") or sandbox.get("backend")
    required.update(COMPUTE_CAPABILITIES.get(provider, set()))
    denied = set((recipe.get("policy", {}) or {}).get("deny", []) or [])
    return {"required": sorted(required), "denied": sorted(denied)}

def compile_recipe(recipe: dict[str, Any], artifact_dir: Path) -> ExecutionContract:
    role_definition = recipe.get("role_definition", {}) or {}
    skills = recipe.get("skills", []) or []
    body = {
        "apiVersion":"decretum.dev/v1","kind":"ResearchContract",
        "research":{"id":recipe["id"],"name":recipe["name"],"version":recipe["version"],"role":recipe["role"],"objective":recipe["objective"],"references":recipe.get("references",[])},
        "inputs":recipe.get("inputs",{}),"environment":recipe["environment"],
        "roles":[{"id":recipe["role"],"definition":role_definition,"skills":role_definition.get("skills",[s.get("id") for s in skills]),"default_capabilities":role_definition.get("default_capabilities",[]),"allowed_tools":role_definition.get("allowed_tools",[])}],
        "skills":skills,"skill_catalog":recipe.get("skill_catalog",[]),"capability_catalog":recipe.get("capability_catalog",[]),
        "provider_registry": "schema/provider_registry.yaml",
        "provider_interfaces": ["mcp", "api", "tool"],
        "capability_graph":[{"skill":s.get("id"),"capabilities":s.get("capabilities",[]) or [],"tools":s.get("tools",[]) or [],"evidence_inputs":s.get("evidence_inputs",[]) or [],"evidence_outputs":s.get("evidence_outputs",[]) or []} for s in skills],
        "orchestration":recipe["environment"].get("orchestration",{"executor":"codex","mode":"interactive"}),
        "capabilities":_capabilities(recipe),"policy":recipe["policy"],"evidence":recipe["evidence"],"completion":recipe["completion"],
        "workload":recipe.get("workload",{}),"reports":recipe.get("reports",[])
    }
    canonical = json.dumps(body,sort_keys=True,separators=(",",":")).encode()
    contract_id = hashlib.sha256(canonical).hexdigest()[:16]
    return ExecutionContract(contract_id,{**body,"contract_id":contract_id},artifact_dir)

def write_contract(contract: ExecutionContract) -> Path:
    contract.artifact_dir.mkdir(parents=True,exist_ok=True)
    path=contract.artifact_dir/"research-contract.json"
    path.write_text(json.dumps(contract.contract,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return path
