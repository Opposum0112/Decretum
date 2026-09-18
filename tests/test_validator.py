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
