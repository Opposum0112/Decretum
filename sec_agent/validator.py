"""Local-only LinkML-aligned recipe validation."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .capability_registry import canonical_capabilities
from .profile_registry import DEFAULT_PROFILE_REGISTRY, load_profile_registry, validate_recipe_profiles

ROLE_VALUES = {"threat_researcher", "supply_chain_auditor", "detection_engineer", "vulnerability_exploit_researcher", "malware_researcher", "threat_intelligence_researcher", "cloud_security_researcher", "forensics_researcher", "vulnerability_researcher", "security_architect"}
SKILL_KINDS = {"analysis", "investigation", "detection", "forensics", "threat_intelligence", "malware_analysis", "vulnerability_research", "cloud_security", "reverse_engineering", "network_analysis", "software_supply_chain", "reporting"}
SKILL_EXECUTION_MODES = {"codex_native", "shell", "mcp", "script", "analyst_review"}
TOOLS = {"sysdig", "falco", "tracee", "tetragon", "bpftrace", "bcc", "libbpf", "ebpf_exporter", "strace", "ltrace", "perf", "ftrace", "auditd", "auditbeat", "osquery", "procmon", "psutil", "tcpdump", "tshark", "dumpcap", "wireshark", "zeek", "suricata", "snort", "netsniff_ng", "conntrack", "nftables", "iptables", "ethtool", "ss", "ip", "dig", "resolvectl", "bpftool", "pahole", "opensnoop", "execsnoop", "tcpconnect", "tcplife", "filetop", "biolatency", "runqlat", "funccount", "openssl_trace", "volatility", "rekall", "yara", "clamav", "ghidra", "radare2", "binwalk", "strings", "readelf", "objdump", "lsof", "nsenter", "capsh", "unshare"}
CAPABILITY_KINDS = {"artifact", "filesystem", "process", "network", "identity", "cloud", "container", "instrumentation", "analysis", "reporting", "compute"}
CAPABILITY_RISKS = {"read", "observe", "collect", "execute", "write", "privileged", "network_access"}

PROVIDER_INTERFACE_TYPES = {"mcp", "api", "tool"}
HARNESS_OPERATIONS = {"provision", "implement_capabilities", "execute", "orchestrate", "collect_evidence", "researcher_interaction"}
DEFAULT_PROVIDER_REGISTRY = Path(__file__).resolve().parents[1] / "schema" / "provider_registry.yaml"

@lru_cache(maxsize=8)
def load_provider_registry(path: str) -> dict[str, Any]:
    registry = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(registry, dict) or not isinstance(registry.get("providers"), dict):
        raise ValueError("provider registry must contain a providers mapping")
    return registry

def validate_provider_registry(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for provider_id, provider in (registry.get("providers") or {}).items():
        if not isinstance(provider, dict):
            errors.append(f"provider {provider_id!r} must be a mapping")
            continue
        interface = provider.get("interface")
        if not isinstance(interface, dict):
            errors.append(f"provider {provider_id!r} requires interface")
        elif interface.get("type") not in PROVIDER_INTERFACE_TYPES:
            errors.append(f"provider {provider_id!r} has invalid interface type {interface.get('type')!r}")
        capabilities = provider.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            errors.append(f"provider {provider_id!r} requires non-empty capabilities")
        for capability in capabilities or []:
            if capability not in canonical_capabilities():
                errors.append(f"provider {provider_id!r} advertises non-canonical capability {capability!r}")
    return errors

def provider_capability_index(registry: dict[str, Any]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for provider_id, provider in (registry.get("providers") or {}).items():
        for capability in provider.get("capabilities", []) or []:
            index.setdefault(capability, []).append(provider_id)
    return index

def required_capabilities(recipe: dict[str, Any], registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> set[str]:
    required = set(recipe.get("capabilities", []) or [])
    for step in recipe.get("experiments", []) or []:
        required.update(step.get("capabilities", []) or [])
        if step.get("capability"):
            required.add(step["capability"])
    for skill in recipe.get("skills", []) or []:
        if isinstance(skill, dict):
            required.update(skill.get("capabilities", []) or [])
    role = recipe.get("role_definition") or {}
    if isinstance(role, dict):
        required.update(role.get("default_capabilities", []) or [])
    if (recipe.get("workload") or {}).get("command"):
        required.add("process.execute")
    return required

def validate_capability_providers(recipe: dict[str, Any], registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> list[str]:
    try:
        registry = load_provider_registry(str(registry_path))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"provider registry unavailable: {exc}"]
    errors = registry_errors(registry_path)
    required = required_capabilities(recipe, registry_path)
    index = provider_capability_index(registry)
    for capability in sorted(required):
        if capability and capability not in index:
            errors.append(f"capability {capability!r} has no registered provider (MCP/API/tool)")
    return errors

def registry_errors(registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> list[str]:
    try:
        registry = load_provider_registry(str(registry_path))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"provider registry unavailable: {exc}"]
    errors = validate_provider_registry(registry)
    providers = registry.get("providers", {}) or {}
    for integration_id, integration in (registry.get("integrations", {}) or {}).items():
        if not isinstance(integration, dict):
            errors.append(f"integration {integration_id!r} must be a mapping")
            continue
        if integration.get("type") not in PROVIDER_INTERFACE_TYPES:
            errors.append(f"integration {integration_id!r} has invalid interface type")
        if integration.get("provider") not in providers:
            errors.append(f"integration {integration_id!r} references unknown provider {integration.get('provider')!r}")
    for harness_id, harness in (registry.get("harnesses", {}) or {}).items():
        if not isinstance(harness, dict):
            errors.append(f"harness {harness_id!r} must be a mapping")
            continue
        if harness.get("kind") != "agent":
            errors.append(f"harness {harness_id!r} must have kind 'agent'")
        for interface in harness.get("supported_interfaces", []) or []:
            if interface not in PROVIDER_INTERFACE_TYPES:
                errors.append(f"harness {harness_id!r} has invalid interface {interface!r}")
        operations = harness.get("operations", [])
        if not isinstance(operations, list) or not operations:
            errors.append(f"harness {harness_id!r} requires non-empty operations")
        else:
            for operation in operations:
                if operation not in HARNESS_OPERATIONS:
                    errors.append(f"harness {harness_id!r} has invalid operation {operation!r}")
    for model_id, model in (registry.get("models", {}) or {}).items():
        if not isinstance(model, dict) or model.get("kind") != "llm":
            errors.append(f"model {model_id!r} must have kind 'llm'")
    return errors

def load_recipe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Recipe root must be a YAML mapping")
    return value

def structural_validate(recipe: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    domain = recipe.get("domain", "security_research")
    required = {"id", "name", "version", "objective"}
    if domain == "security_research":
        required.update({"role", "policy", "evidence", "completion"})
    errors.extend(f"missing required field: {key}" for key in sorted(required - recipe.keys()))
    if recipe.get("role") not in ROLE_VALUES:
        errors.append(f"invalid role: {recipe.get('role')!r}")

    role_definition = recipe.get("role_definition")
    if role_definition is not None and not isinstance(role_definition, dict):
        errors.append("role_definition must be a mapping")

    # Recipe capability_catalog is deprecated as a semantic definition.
    # References must resolve against the canonical registry.
    canonical = canonical_capabilities()
    catalog = recipe.get("capability_catalog")
    if catalog is not None:
        if not isinstance(catalog, list):
            errors.append("capability_catalog must be a list")
        else:
            for item in catalog:
                if not isinstance(item, dict) or not item.get("id"):
                    errors.append("capability_catalog entries must contain id")
                elif item["id"] not in canonical:
                    errors.append(f"capability_catalog references non-canonical capability {item['id']!r}; promote it first")

    for capability in required_capabilities(recipe):
        if capability not in canonical:
            errors.append(f"recipe references non-canonical capability {capability!r}; promote it first")

    skills = recipe.get("skills", []) or []
    if not isinstance(skills, list):
        errors.append("skills must be a list")
        skills = []

    if "compute" in recipe or "instrumentation" in recipe:
        errors.append("inline compute/instrumentation configuration is deprecated; use profiles")

    policy = recipe.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be a mapping")
    else:
        for key in ("allow", "deny", "approval_required"):
            if policy.get(key) is not None and not isinstance(policy[key], list):
                errors.append(f"policy.{key} must be a list")
    evidence = recipe.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("evidence must be a mapping")
    elif not evidence.get("required"):
        errors.append("evidence.required must be non-empty")
    completion = recipe.get("completion")
    if not isinstance(completion, dict):
        errors.append("completion must be a mapping")
    elif completion.get("report_required", True) is not True:
        errors.append("completion.report_required must remain true")

    return errors

def validate_experiment_graph(recipe: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    steps = recipe.get("experiments", []) or []
    if not isinstance(steps, list):
        return ["experiments must be a list"]
    declared = set(canonical_capabilities())
    step_ids = {x.get("id") for x in steps if isinstance(x, dict) and x.get("id")}
    graph: dict[str, list[str]] = {}
    for step in steps:
        if not isinstance(step, dict):
            errors.append("each experiment step must be a mapping")
            continue
        sid = step.get("id")
        if not sid:
            errors.append("experiment.id is required")
            continue
        graph[sid] = step.get("depends_on", []) or []
        for dep in graph[sid]:
            if dep == sid:
                errors.append(f"experiment {sid!r}: cannot depend on itself")
            elif dep not in step_ids:
                errors.append(f"experiment {sid!r}: unknown dependency {dep!r}")
        capabilities = list(step.get("capabilities", []) or [])
        if step.get("capability"):
            capabilities.append(step["capability"])
        for capability in capabilities:
            if capability not in declared:
                errors.append(f"experiment {sid!r}: non-canonical capability {capability!r}")
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting:
            errors.append(f"experiment graph contains a cycle at {node!r}")
            return
        if node in visited:
            return
        visiting.add(node)
        for dep in graph.get(node, []):
            if dep in graph:
                visit(dep)
        visiting.remove(node)
        visited.add(node)
    for node in graph:
        visit(node)
    return errors

def preflight(recipe: dict[str, Any]) -> list[str]:
    profile_errors = validate_recipe_profiles(recipe, DEFAULT_PROFILE_REGISTRY)
    if profile_errors:
        return [f"PROFILE: {item}" for item in profile_errors]
    return []

def validate_recipe(path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    recipe = load_recipe(path)
    errors = structural_validate(recipe)
    errors.extend(validate_experiment_graph(recipe))
    if not errors:
        errors.extend(validate_capability_providers(recipe))
    return recipe, errors, preflight(recipe) if not errors else []
