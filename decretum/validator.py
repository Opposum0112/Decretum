"""Local-only LinkML-aligned recipe validation."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from .capability_registry import canonical_capabilities
from .profile_registry import DEFAULT_PROFILE_REGISTRY, load_profile_registry, validate_recipe_profiles


PROVIDER_INTERFACE_TYPES = {"mcp", "api", "tool"}
HARNESS_OPERATIONS = {"provision", "implement_capabilities", "execute", "orchestrate", "collect_evidence", "researcher_interaction"}
DEFAULT_SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"
DEFAULT_PROVIDER_REGISTRY = None
RECIPE_SCHEMA = DEFAULT_SCHEMA_DIR / "recipe.schema.yaml"
SPECIFICATION_SCHEMA = DEFAULT_SCHEMA_DIR / "specification.schema.yaml"
CAPABILITY_IMPLEMENTATION_SCHEMA = DEFAULT_SCHEMA_DIR / "capability_implementation.schema.yaml"
EXECUTION_CONTRACT_SCHEMA = DEFAULT_SCHEMA_DIR / "execution_contract.schema.yaml"

@lru_cache(maxsize=8)
def load_provider_registry(path: str | Path | None, domain: str | None = None) -> dict[str, Any]:
    if path is None:\n        from .domain_packs import resource_for_domain\n        path = resource_for_domain(domain, "providers") / "provider_registry.yaml"\n    if Path(path).is_dir(): path = Path(path) / "provider_registry.yaml"\n    registry = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(registry, dict) or not isinstance(registry.get("providers"), dict):
        raise ValueError("provider registry must contain a providers mapping")
    return registry

def validate_provider_registry(registry: dict[str, Any], capability_registry_path: Path | None = None, domain: str | None = None) -> list[str]:
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
            if capability not in canonical_capabilities(capability_registry_path, domain):
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

def validate_capability_providers(recipe: dict[str, Any], registry_path: Path | None = DEFAULT_PROVIDER_REGISTRY, capability_registry_path: Path | None = None) -> list[str]:
    try:
        registry = load_provider_registry(registry_path, recipe.get("domain"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"provider registry unavailable: {exc}"]
    errors = registry_errors(registry_path, capability_registry_path=capability_registry_path, domain=recipe.get("domain"))
    required = required_capabilities(recipe, registry_path)
    index = provider_capability_index(registry)
    for capability in sorted(required):
        if capability and capability not in index:
            errors.append(f"capability {capability!r} has no registered provider (MCP/API/tool)")
    return errors

def registry_errors(registry_path: Path | None = DEFAULT_PROVIDER_REGISTRY, capability_registry_path: Path | None = None, domain: str | None = None) -> list[str]:
    try:
        registry = load_provider_registry(registry_path, domain)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"provider registry unavailable: {exc}"]
    errors = validate_provider_registry(registry, capability_registry_path, domain)
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

def validate_document_schema(document: dict[str, Any], schema_path: Path) -> list[str]:
    """Validate a Decretum artifact against its domain-neutral JSON Schema."""
    try:
        schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator(schema).check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda e: list(e.path))
        return [f"{schema_path.name}: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"{schema_path.name}: schema unavailable: {exc}"]

def validate_recipe_schema(recipe: dict[str, Any]) -> list[str]:
    return validate_document_schema(recipe, RECIPE_SCHEMA)

def validate_specification_schema(specification: dict[str, Any]) -> list[str]:
    return validate_document_schema(specification, SPECIFICATION_SCHEMA)

def validate_capability_implementation_schema(implementation: dict[str, Any]) -> list[str]:
    return validate_document_schema(implementation, CAPABILITY_IMPLEMENTATION_SCHEMA)

def validate_execution_contract_schema(contract: dict[str, Any]) -> list[str]:
    return validate_document_schema(contract, EXECUTION_CONTRACT_SCHEMA)

def load_recipe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Recipe root must be a YAML mapping")
    return value

def structural_validate(recipe: dict[str, Any], capability_registry_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    required = {"id", "name", "version", "objective"}
    errors.extend(f"missing required field: {key}" for key in sorted(required - recipe.keys()))
    role_definition = recipe.get("role_definition")
    if role_definition is not None and not isinstance(role_definition, dict):
        errors.append("role_definition must be a mapping")

    # Recipe capability_catalog is deprecated as a semantic definition.
    # References must resolve against the canonical registry.
    canonical = canonical_capabilities(capability_registry_path, recipe.get("domain"))
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

    return errors

def validate_experiment_graph(recipe: dict[str, Any], capability_registry_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    steps = recipe.get("experiments", []) or []
    if not isinstance(steps, list):
        return ["experiments must be a list"]
    declared = set(canonical_capabilities(capability_registry_path, recipe.get("domain")))
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

def preflight(recipe: dict[str, Any], profile_path: Path | None = DEFAULT_PROFILE_REGISTRY) -> list[str]:
    profile_errors = validate_recipe_profiles(recipe, profile_path)
    if profile_errors:
        return [f"PROFILE: {item}" for item in profile_errors]
    return []

def validate_recipe(path: Path, domain_pack_path: Path | None = None) -> tuple[dict[str, Any], list[str], list[str]]:
    recipe = load_recipe(path)
    provider_path = profile_path = capability_path = None
    if domain_pack_path:
        provider_path = domain_pack_path / "providers" / "provider_registry.yaml"
        profile_path = domain_pack_path / "profiles" / "profile_registry.yaml"
        capability_path = domain_pack_path / "capabilities" / "capability_registry.yaml"
    errors = validate_recipe_schema(recipe)
    errors.extend(structural_validate(recipe, capability_path))
    errors.extend(validate_experiment_graph(recipe, capability_path))
    if not errors:
        errors.extend(validate_capability_providers(recipe, provider_path, capability_path))
    return recipe, errors, preflight(recipe, profile_path) if not errors else []
