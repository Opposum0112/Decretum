from pathlib import Path

from sec_agent.compiler import compile_recipe
from sec_agent.validator import (
    load_recipe,
    structural_validate,
    validate_capability_providers,
    registry_errors,
)

RECIPE = Path("recipes/openai-hosted-malware-analysis.yaml")


def test_openai_recipe_is_valid():
    recipe = load_recipe(RECIPE)
    assert structural_validate(recipe) == []


def test_host_mounts_rejected():
    recipe = load_recipe(RECIPE)
    recipe["environment"]["host_mounts"] = True
    assert any("host filesystem mounts" in e for e in structural_validate(recipe))


def test_privileged_execution_rejected():
    recipe = load_recipe(RECIPE)
    recipe["environment"]["privileged"] = True
    assert any("privileged" in e for e in structural_validate(recipe))


def test_compiler_produces_deterministic_contract():
    recipe = load_recipe(RECIPE)
    a = compile_recipe(recipe, Path("artifacts/test"))
    b = compile_recipe(recipe, Path("artifacts/test"))
    assert a.contract_id == b.contract_id
    assert a.contract["kind"] == "ResearchExecutionContract"
    assert "process.execute" in a.contract["capabilities"]


def test_compiled_contract_keeps_harness_execution_boundary():
    recipe = load_recipe(RECIPE)
    contract = compile_recipe(recipe, Path("artifacts/test-contract"))
    assert contract.contract["execution"]["harness"] == "codex"
    assert contract.contract["research_loop"]["interactive"] is True
    assert "provision" in contract.contract["research_loop"]["harness_responsible_for"]
    assert "implement_capabilities" in contract.contract["research_loop"]["harness_responsible_for"]


def test_undeclared_skill_capability_is_rejected():
    recipe = load_recipe(RECIPE)
    recipe["skills"][0]["capabilities"][0] = "process.unknown"
    errors = structural_validate(recipe)
    assert any("unknown capability" in e for e in errors)


def test_capability_tool_is_validated():
    recipe = load_recipe(RECIPE)
    recipe["capability_catalog"][0]["tools"] = ["not-a-tool"]
    errors = structural_validate(recipe)
    assert any("unsupported capability tool" in e for e in errors)


def test_declared_capability_requires_registered_provider(tmp_path):
    recipe = {
        "capability_catalog": [{"id": "custom.unavailable"}],
        "skills": [],
        "role_definition": {},
        "environment": {},
    }
    registry = tmp_path / "providers.yaml"
    registry.write_text(
        """
apiVersion: decretum.dev/v1
kind: CapabilityProviderRegistry
version: "1.0"
providers:
  tcpdump:
    interface: {type: tool, executable: tcpdump}
    capabilities: [network.capture]
""",
        encoding="utf-8",
    )
    errors = validate_capability_providers(recipe, registry)
    assert any("custom.unavailable" in error for error in errors)


def test_declared_capability_with_mcp_provider_is_valid(tmp_path):
    recipe = {
        "capability_catalog": [{"id": "network.capture"}],
        "skills": [],
        "role_definition": {},
        "environment": {},
    }
    registry = tmp_path / "providers.yaml"
    registry.write_text(
        """
apiVersion: decretum.dev/v1
kind: CapabilityProviderRegistry
version: "1.0"
providers:
  pcap:
    interface: {type: mcp, server: pcap}
    capabilities: [network.capture]
""",
        encoding="utf-8",
    )
    assert validate_capability_providers(recipe, registry) == []


def test_registry_declares_harnesses_integrations_and_models():
    assert registry_errors() == []


def test_provider_is_open_world():
    recipe = {
        "capability_catalog": [{"id": "compute.custom"}],
        "skills": [],
        "role_definition": {},
        "environment": {},
    }
    registry = Path("schema/provider_registry.yaml")
    assert isinstance(validate_capability_providers(recipe, registry), list)
