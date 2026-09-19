from pathlib import Path

from sec_agent.compiler import compile_recipe
from sec_agent.resolver import resolve_capabilities
from sec_agent.validator import validate_recipe

RECIPE = Path("recipes/openai-hosted-malware-analysis.yaml")


def test_recipe_validates_and_resolves():
    recipe, errors, _ = validate_recipe(RECIPE)
    assert not errors
    result = resolve_capabilities(recipe)
    assert result["status"] in {"ready", "needs_prerequisites"}
    assert any(item["capability"] == "process.observe" for item in result["capabilities"])


def test_compiler_emits_execution_ir():
    recipe, errors, _ = validate_recipe(RECIPE)
    assert not errors
    contract = compile_recipe(recipe, Path("artifacts/test"))
    assert contract.contract["kind"] == "ResearchExecutionContract"
    assert contract.contract["contract_version"] == "2"
    assert "experiment_graph" in contract.contract
    assert "resolution" in contract.contract
    assert "capability_requirements" in contract.contract


def test_experiment_dag_rejects_cycles_and_unknown_dependencies(tmp_path):
    recipe, errors, _ = validate_recipe(RECIPE)
    assert not errors
    recipe["experiments"] = [
        {"id": "a", "capabilities": ["process.observe"], "depends_on": ["b"]},
        {"id": "b", "capabilities": ["network.capture"], "depends_on": ["a"]},
    ]
    from sec_agent.validator import validate_experiment_graph
    errors = validate_experiment_graph(recipe)
    assert any("cycle" in error for error in errors)


def test_experiment_dag_rejects_undeclared_capability():
    recipe, errors, _ = validate_recipe(RECIPE)
    assert not errors
    recipe["experiments"] = [{"id": "x", "capabilities": ["does.not.exist"]}]
    from sec_agent.validator import validate_experiment_graph
    errors = validate_experiment_graph(recipe)
    assert any("undeclared capability" in error for error in errors)
