"""Local-only LinkML-aligned recipe validation."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml

ROLE_VALUES = {"threat_researcher", "supply_chain_auditor", "detection_engineer", "vulnerability_exploit_researcher", "malware_researcher", "threat_intelligence_researcher", "cloud_security_researcher", "forensics_researcher", "vulnerability_researcher", "security_architect"}
SKILL_KINDS = {"analysis", "investigation", "detection", "forensics", "threat_intelligence", "malware_analysis", "vulnerability_research", "cloud_security", "reverse_engineering", "network_analysis", "software_supply_chain", "reporting"}
SKILL_EXECUTION_MODES = {"codex_native", "shell", "mcp", "script", "analyst_review"}
TOOLS = {"sysdig", "falco", "tracee", "tetragon", "bpftrace", "bcc", "libbpf", "ebpf_exporter", "strace", "ltrace", "perf", "ftrace", "auditd", "auditbeat", "osquery", "procmon", "psutil", "tcpdump", "tshark", "dumpcap", "wireshark", "zeek", "suricata", "snort", "netsniff_ng", "conntrack", "nftables", "iptables", "ethtool", "ss", "ip", "dig", "resolvectl", "bpftool", "pahole", "opensnoop", "execsnoop", "tcpconnect", "tcplife", "filetop", "biolatency", "runqlat", "funccount", "openssl_trace", "volatility", "rekall", "yara", "clamav", "ghidra", "radare2", "binwalk", "strings", "readelf", "objdump", "lsof", "nsenter", "capsh", "unshare"}
CAPABILITY_KINDS = {"artifact", "filesystem", "process", "network", "identity", "cloud", "container", "instrumentation", "analysis", "reporting"}
CAPABILITY_RISKS = {"read", "observe", "collect", "execute", "write", "privileged", "network_access"}
BACKENDS = {"unix", "docker", "podman", "lima", "incus", "lxc", "kvm", "firecracker", "qemu"}

def load_recipe(path: Path) -> dict[str, Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError("Recipe root must be a YAML mapping")
    return value

def structural_validate(recipe: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"id","name","version","role","objective","environment","policy","evidence","completion"}
    errors.extend(f"missing required field: {key}" for key in sorted(required - recipe.keys()))
    if recipe.get("role") not in ROLE_VALUES: errors.append(f"invalid role: {recipe.get('role')!r}")

    role_definition = recipe.get("role_definition")
    if role_definition is not None:
        if not isinstance(role_definition, dict): errors.append("role_definition must be a mapping")
        elif role_definition.get("id") != recipe.get("role"): errors.append("role_definition.id must match recipe.role")

    capabilities = recipe.get("capability_catalog", recipe.get("capabilities", [])) or []
    if not isinstance(capabilities, list):
        errors.append("capability_catalog must be a list"); capabilities = []
    cap_by_id: dict[str, dict[str, Any]] = {}
    for cap in capabilities:
        if not isinstance(cap, dict): errors.append("each capability must be a mapping"); continue
        cid = cap.get("id")
        if not cid: errors.append("capability.id is required"); continue
        if cid in cap_by_id: errors.append(f"duplicate capability id: {cid!r}")
        cap_by_id[cid] = cap
        if cap.get("kind") not in CAPABILITY_KINDS: errors.append(f"invalid capability kind for {cid!r}: {cap.get('kind')!r}")
        if cap.get("risk") not in CAPABILITY_RISKS: errors.append(f"invalid capability risk for {cid!r}: {cap.get('risk')!r}")
        if not cap.get("name") or not cap.get("description"): errors.append(f"capability {cid!r} requires name and description")
        for tool in cap.get("tools", []) or []:
            if tool not in TOOLS: errors.append(f"unsupported capability tool {tool!r} in {cid!r}")

    skills = recipe.get("skills", []) or []
    if not isinstance(skills, list): errors.append("skills must be a list"); skills = []
    skill_ids = {s.get("id") for s in skills if isinstance(s, dict) and s.get("id")}
    if isinstance(role_definition, dict):
        for sid in role_definition.get("skills", []) or []:
            if sid not in skill_ids: errors.append(f"role_definition references undeclared skill {sid!r}")
        for cid in role_definition.get("default_capabilities", []) or []:
            if cid not in cap_by_id: errors.append(f"role_definition references undeclared capability {cid!r}")

    for skill in skills:
        if not isinstance(skill, dict): errors.append("each skill must be a mapping"); continue
        sid = skill.get("id")
        if not sid: errors.append("skill.id is required"); continue
        if not skill.get("name") or skill.get("kind") not in SKILL_KINDS or not skill.get("description"): errors.append(f"skill {sid!r} requires valid name, kind, and description")
        if skill.get("execution_mode", "codex_native") not in SKILL_EXECUTION_MODES: errors.append(f"invalid execution mode for skill {sid!r}")
        for cap in skill.get("capabilities", []) or []:
            if cap not in cap_by_id: errors.append(f"skill {sid!r} references undeclared capability {cap!r}")
        for tool in skill.get("tools", []) or []:
            if tool not in TOOLS: errors.append(f"unsupported skill tool {tool!r} in {sid!r}")

    environment = recipe.get("environment")
    if not isinstance(environment, dict): errors.append("environment must be a mapping"); return errors
    if environment.get("type", "local") != "local": errors.append("environment.type must be local; hosted sandbox execution is not supported")
    sandbox = environment.get("sandbox")
    if not isinstance(sandbox, dict):
        errors.append("environment.sandbox must be a mapping")
    else:
        backend = sandbox.get("backend")
        if backend not in BACKENDS: errors.append(f"unsupported sandbox backend: {backend!r}")
        if backend in {"docker","podman"} and not sandbox.get("image"): errors.append(f"{backend} sandbox requires environment.sandbox.image")
        if sandbox.get("inherit_host_environment", False): errors.append("host environment inheritance must remain disabled")
        if environment.get("host_mounts", False): errors.append("host filesystem mounts must remain disabled")
    if environment.get("privileged", False): errors.append("privileged execution is prohibited by default")

    policy = recipe.get("policy")
    if not isinstance(policy, dict): errors.append("policy must be a mapping")
    else:
        for key in ("allow","deny","approval_required"):
            if policy.get(key) is not None and not isinstance(policy[key], list): errors.append(f"policy.{key} must be a list")
    evidence = recipe.get("evidence")
    if not isinstance(evidence, dict): errors.append("evidence must be a mapping")
    elif not evidence.get("required"): errors.append("evidence.required must be non-empty")
    completion = recipe.get("completion")
    if not isinstance(completion, dict): errors.append("completion must be a mapping")
    elif completion.get("report_required", True) is not True: errors.append("completion.report_required must remain true")
    instrumentation = recipe.get("instrumentation", {}) or {}
    if not isinstance(instrumentation, dict): errors.append("instrumentation must be a mapping")
    else:
        for tool in instrumentation.get("tools", []) or []:
            if tool not in TOOLS: errors.append(f"unsupported instrumentation tool: {tool!r}")
    return errors

def preflight(recipe: dict[str, Any]) -> list[str]:
    sandbox = recipe.get("environment", {}).get("sandbox", {})
    backend = sandbox.get("backend")
    if backend == "docker": return ["Docker backend selected: local Docker daemon must be available"]
    if backend in {"podman","lima","incus","lxc","kvm","firecracker","qemu"}: return [f"{backend} backend selected: local provider must be installed and available"]
    if backend == "unix": return ["Unix-local backend selected: commands execute with host permissions; use only for trusted workloads or an externally isolated host"]
    return []

def validate_recipe(path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    recipe = load_recipe(path); errors = structural_validate(recipe)
    return recipe, errors, preflight(recipe) if not errors else []
