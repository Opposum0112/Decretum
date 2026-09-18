from pathlib import Path
from sec_agent.validator import load_recipe, structural_validate
from sec_agent.compiler import compile_recipe

def test_openai_recipe_is_valid():
    recipe = load_recipe(Path("recipes/openai-hosted-malware-analysis.yaml"))
    assert structural_validate(recipe) == []

def test_host_mounts_rejected():
    recipe = load_recipe(Path("recipes/openai-hosted-malware-analysis.yaml"))
    recipe["environment"]["host_mounts"] = True
    assert any("host filesystem mounts" in e for e in structural_validate(recipe))

def test_privileged_execution_rejected():
    recipe = load_recipe(Path("recipes/openai-hosted-malware-analysis.yaml"))
    recipe["environment"]["privileged"] = True
    assert any("privileged" in e for e in structural_validate(recipe))

def test_compiler_produces_deterministic_contract():
    recipe = load_recipe(Path("recipes/openai-hosted-malware-analysis.yaml"))
    a = compile_recipe(recipe, Path("artifacts/test"))
    b = compile_recipe(recipe, Path("artifacts/test"))
    assert a.contract_id == b.contract_id
    assert a.contract["kind"] == "ResearchContract"
    assert "process.execute" in a.contract["capabilities"]["required"]


def test_codex_settings_are_compiled_and_cloud_is_denied():
    recipe = load_recipe(Path("recipes/openai-hosted-malware-analysis.yaml"))
    contract = compile_recipe(recipe, Path("artifacts/test-codex"))
    codex = contract.contract["environment"]["codex"]
    assert codex["sandbox_mode"] == "workspace-write"
    assert codex["approval_policy"] == "on-request"
    assert codex["network_access_enabled"] is False
    assert "cloud.sandbox" in contract.contract["capabilities"]["denied"]


def test_undeclared_skill_capability_is_rejected():
    recipe = load_recipe(Path("recipes/openai-hosted-malware-analysis.yaml"))
    recipe["skills"][0]["capabilities"][0] = "process.unknown"
    errors = structural_validate(recipe)
    assert any("undeclared capability" in e for e in errors)

def test_capability_tool_is_validated():
    recipe = load_recipe(Path("recipes/openai-hosted-malware-analysis.yaml"))
    recipe["capability_catalog"][0]["tools"] = ["not-a-tool"]
    errors = structural_validate(recipe)
    assert any("unsupported capability tool" in e for e in errors)

def test_capability_graph_is_normalized():
    recipe = load_recipe(Path("recipes/openai-hosted-malware-analysis.yaml"))
    contract = compile_recipe(recipe, Path("artifacts/test-graph"))
    graph = contract.contract["capability_graph"]
    assert graph[0]["skill"] == "malware.behavior-analysis"
    assert graph[0]["capabilities"] == ["process.observe", "network.capture"]



def test_declared_capability_requires_registered_provider(tmp_path):
    from sec_agent.validator import validate_capability_providers
    recipe = {"capability_catalog": [{"id": "custom.unavailable"}], "skills": [], "role_definition": {}, "environment": {}}
    registry = tmp_path / "providers.yaml"
    registry.write_text("""
apiVersion: decretum.dev/v1
kind: CapabilityProviderRegistry
version: "1.0"
providers:
  tcpdump:
    interface: {type: tool, executable: tcpdump}
    capabilities: [network.capture]
""", encoding="utf-8")
    errors = validate_capability_providers(recipe, registry)
    assert any("custom.unavailable" in error for error in errors)


def test_declared_capability_with_mcp_provider_is_valid(tmp_path):
    from sec_agent.validator import validate_capability_providers
    recipe = {"capability_catalog": [{"id": "network.capture"}], "skills": [], "role_definition": {}, "environment": {}}
    registry = tmp_path / "providers.yaml"
    registry.write_text("""
apiVersion: decretum.dev/v1
kind: CapabilityProviderRegistry
version: "1.0"
providers:
  pcap:
    interface: {type: mcp, server: pcap}
    capabilities: [network.capture]
""", encoding="utf-8")
    assert validate_capability_providers(recipe, registry) == []


def test_registry_declares_harnesses_integrations_and_models():
    from sec_agent.validator import registry_errors
    assert registry_errors() == []


def test_capability_resolver_reports_provider_candidates():
    from sec_agent.resolver import resolve_capabilities
    recipe = {"capability_catalog": [{"id": "network.capture"}], "skills": [], "role_definition": {}}
    result = resolve_capabilities(recipe)
    assert result["capabilities"][0]["capability"] == "network.capture"
    assert result["capabilities"][0]["providers"]
    assert {"codex", "goose", "google_adk", "open_code", "vercel_ai"} <= set(result["harnesses"])
