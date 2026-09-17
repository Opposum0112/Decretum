from pathlib import Path
from sec_agent.validator import structural_validate, load_recipe


def test_supply_chain_recipe_structure():
    recipe = load_recipe(Path("recipes/supply_chain_audit.yaml"))
    assert structural_validate(recipe) == []


def test_host_mounts_rejected():
    recipe = load_recipe(Path("recipes/supply_chain_audit.yaml"))
    recipe["compute"]["allow_host_mounts"] = True
    assert any("host mounts" in e for e in structural_validate(recipe))
