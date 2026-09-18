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
    recipe["capabilities"][0]["tools"] = ["not-a-tool"]
    errors = structural_validate(recipe)
    assert any("unsupported capability tool" in e for e in errors)

def test_capability_graph_is_normalized():
    recipe = load_recipe(Path("recipes/openai-hosted-malware-analysis.yaml"))
    contract = compile_recipe(recipe, Path("artifacts/test-graph"))
    graph = contract.contract["capability_graph"]
    assert graph[0]["skill"] == "malware.behavior-analysis"
    assert graph[0]["capabilities"] == ["process.observe", "network.capture"]

