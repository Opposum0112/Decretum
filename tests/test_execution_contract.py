from pathlib import Path

from sec_agent.compiler import compile_recipe
from sec_agent.validator import load_recipe, structural_validate, validate_recipe

RECIPE = Path("recipes/openai-hosted-malware-analysis.yaml")


def test_reference_recipe_validates():
    recipe, errors, findings = validate_recipe(RECIPE)
    assert not errors
    assert not findings
    assert structural_validate(recipe) == []


def test_compiler_emits_domain_neutral_execution_contract():
    recipe = load_recipe(RECIPE)
    contract = compile_recipe(recipe, Path("artifacts/test"))
    assert contract.contract["kind"] == "ExecutionContract"
    assert contract.contract["domain"] == "security_research"
    assert contract.contract["contract_version"] == "5"
    assert contract.contract["handoff"]["mode"] == "contract_only"
    assert contract.contract["handoff"]["decretum_stops_after_compilation"] is True


def test_compilation_is_deterministic():
    recipe = load_recipe(RECIPE)
    a = compile_recipe(recipe, Path("artifacts/test-a"))
    b = compile_recipe(recipe, Path("artifacts/test-b"))
    assert a.contract_id == b.contract_id
    assert a.contract["plan_digest"] == b.contract["plan_digest"]


def test_handoff_is_runtime_neutral():
    recipe = load_recipe(RECIPE)
    contract = compile_recipe(recipe, Path("artifacts/test-handoff"))
    envelope = {
        "protocol": "decretum.dev/v1",
        "type": "execution_handoff",
        "contract": contract.contract,
        "execution": "external_harness_runtime",
        "decretum_action": "none_after_handoff",
    }
    assert envelope["type"] == "execution_handoff"
    assert envelope["execution"] == "external_harness_runtime"
    assert envelope["decretum_action"] == "none_after_handoff"


def test_domain_neutral_recipe_shape_is_accepted():
    recipe = {
        "apiVersion": "decretum.dev/v1",
        "kind": "ExecutionRecipe",
        "domain": "software_engineering",
        "id": "software-task",
        "name": "Software Task",
        "version": "1.0",
        "objective": "Build and validate a service.",
        "capabilities": [],
    }
    assert structural_validate(recipe) == []
