from pathlib import Path

from decretum.spec_compiler import compile_spec

SPEC = Path("examples/spec.md")

def test_markdown_spec_compiles_to_recipe():
    recipe = compile_spec(SPEC)
    assert recipe["kind"] == "ExecutionRecipe"
    assert recipe["domain"] == "software_engineering"
    assert recipe["name"] == "Build a User Service"
    assert recipe["capabilities"] == ["source.read", "source.modify", "test.execute"]
    assert recipe["experiments"][0]["id"] == "implement-service"
    assert recipe["_spec_source"]["sha256"]

def test_spec_compilation_is_deterministic():
    assert compile_spec(SPEC) == compile_spec(SPEC)
