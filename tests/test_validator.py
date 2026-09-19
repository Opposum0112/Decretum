from pathlib import Path

from sec_agent.compiler import compile_recipe
from sec_agent.validator import (
    load_recipe,
    structural_validate,
    validate_capability_providers,
    registry_errors,
)

RECIPE = Path("recipes/openai-hosted-malware-analysis.yaml")


def test_recipe_is_valid():
    recipe = load_recipe(RECIPE)
    assert structural_validate(recipe) == []


def test_compiler_produces_deterministic_contract():
    recipe = load_recipe(RECIPE)
    a = compile_recipe(recipe, Path("artifacts/test"))
    b = compile_recipe(recipe, Path("artifacts/test"))
    assert a.contract_id == b.contract_id
    assert a.contract["kind"] == "ResearchExecutionContract"
    assert "process.execute" in a.contract["capabilities"]


def test_compiled_contract_is_harness_handoff_only():
    recipe = load_recipe(RECIPE)
    contract = compile_recipe(recipe, Path("artifacts/test-contract"))
    assert contract.contract["handoff"]["target"] == "external_harness_runtime"
    assert contract.contract["handoff"]["mode"] == "contract_only"
    assert contract.contract["handoff"]["decretum_stops_after_compilation"] is True
    assert "researcher_interaction" in contract.contract["handoff"]["runtime_owns"]
    assert "research_store_persistence" in contract.contract["handoff"]["runtime_owns"]
    assert "runtime_owns" in contract.contract["handoff"]
    assert "provision" not in contract.contract["research_loop"]


def test_noncanonical_capability_is_rejected():
    recipe = load_recipe(RECIPE)
    recipe["capabilities"].append("process.unknown")
    errors = structural_validate(recipe)
    assert any("non-canonical capability" in e for e in errors)


def test_inline_configuration_is_rejected():
    recipe = load_recipe(RECIPE)
    recipe["compute"] = {"required": ["compute.vm"]}
    errors = structural_validate(recipe)
    assert any("profiles" in e for e in errors)


def test_declared_capability_requires_registered_provider(tmp_path):
    recipe = {"capabilities": ["custom.unavailable"], "experiments": []}
    registry = tmp_path / "providers.yaml"
    registry.write_text("""
apiVersion: decretum.dev/v1
kind: CapabilityProviderRegistry
version: "1.0"
providers:
  tcpdump:
    interface: {type: tool, executable: tcpdump}
    capabilities: [network.capture]
harnesses: {}
integrations: {}
models: {}
""", encoding="utf-8")
    errors = validate_capability_providers(recipe, registry)
    assert any("custom.unavailable" in error for error in errors)


def test_canonical_capability_with_provider_is_valid(tmp_path):
    recipe = {"capabilities": ["network.capture"], "experiments": []}
    registry = tmp_path / "providers.yaml"
    registry.write_text("""
apiVersion: decretum.dev/v1
kind: CapabilityProviderRegistry
version: "1.0"
providers:
  pcap:
    interface: {type: mcp, server: pcap}
    capabilities: [network.capture]
harnesses: {}
integrations: {}
models: {}
""", encoding="utf-8")
    assert validate_capability_providers(recipe, registry) == []


def test_registry_declares_harnesses_integrations_and_models():
    assert registry_errors() == []


def test_recipe_uses_independent_profiles():
    recipe = load_recipe(Path("recipes/suspicious-network-investigation.yaml"))
    assert structural_validate(recipe) == []
    assert validate_capability_providers(recipe) == []
    assert recipe["infrastructure_profile"] == "isolated-linux-vm"
    assert recipe["instrumentation_profile"] == "linux-network-observation"
    assert recipe["harness_profile"] == "interactive-research"
    assert "compute" not in recipe
    assert "instrumentation" not in recipe


def test_contract_has_frozen_external_runtime_boundary():
    recipe = load_recipe(RECIPE)
    contract = compile_recipe(recipe, Path("artifacts/test-boundary"))
    handoff = contract.contract["handoff"]
    assert handoff["target"] == "external_harness_runtime"
    assert handoff["decretum_stops_after_compilation"] is True
    assert "evidence_collection" in handoff["runtime_owns"]
    assert "report_generation" in handoff["runtime_owns"]
    assert handoff["new_capability_or_requirement"] == "return_to_decretum_for_resolution_and_recompilation"


def test_harness_adapter_only_prepares_handoff():
    from sec_agent.harness_adapters import get_adapter
    recipe = load_recipe(RECIPE)
    contract = compile_recipe(recipe, Path("artifacts/test-adapter"))
    adapter = get_adapter(contract.contract["execution"]["harness"])
    envelope = adapter.prepare(contract.contract)
    assert envelope["type"] == "research_execution_handoff"
    assert envelope["execution"] == "external_harness_runtime"
    assert envelope["decretum_action"] == "none_after_handoff"
