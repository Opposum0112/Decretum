"""Compile explicit Markdown intent into a schema-valid ExecutionRecipe.

Markdown is an authoring frontend. The compiler does not infer new capabilities;
canonical capabilities and execution implementations are resolved later.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

ALIASES = {"domain": "domain", "objective": "objective", "capabilities": "capabilities", "inputs": "inputs", "outputs": "outputs", "profiles": "profiles", "policy": "policy", "evidence": "evidence", "completion": "completion", "role": "role", "experiments": "experiments"}

def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "decretum-spec"

def _parse_sections(text: str) -> dict[str, tuple[int, list[str]]]:
    result: dict[str, tuple[int, list[str]]] = {}
    current = None
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            current = ALIASES.get(line[3:].strip().lower())
            if current:
                result[current] = (number, [])
        elif current:
            result[current][1].append(line)
    return result

def _items(lines: list[str]) -> list[str]:
    values = []
    for line in lines:
        value = line.strip()
        if not value:
            continue
        value = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", value)
        values.append(value)
    return values

def _text(lines: list[str]) -> str:
    return "\n".join(_items(lines)).strip()

def _mapping(lines: list[str]) -> dict[str, str]:
    result = {}
    for value in _items(lines):
        if ":" in value:
            key, item = value.split(":", 1)
            result[_slug(key).replace("-", "_")] = item.strip().strip('"').strip("'")
    return result

def _experiments(lines: list[str]) -> list[dict[str, Any]]:
    result = []
    current = None
    for line in lines:
        if line.startswith("### "):
            if current:
                result.append(current)
            current = {"id": _slug(line[4:].strip())}
            continue
        if current is None:
            continue
        value = line.strip()
        if not value or ":" not in value:
            continue
        key, item = value.split(":", 1)
        key = _slug(key).replace("-", "_")
        item = item.strip()
        if key in {"capabilities", "depends_on", "inputs", "outputs"}:
            current[key] = [x.strip() for x in item.split(",") if x.strip()]
        else:
            current[key] = item
    if current:
        result.append(current)
    return result

def compile_spec(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    title = next((x[2:].strip() for x in text.splitlines() if x.startswith("# ")), None)
    if not title:
        raise ValueError("spec.md requires a level-1 title")
    sections = _parse_sections(text)
    objective = _text(sections.get("objective", (0, []))[1])
    if not objective:
        raise ValueError("spec.md requires an ## Objective section")
    recipe: dict[str, Any] = {
        "apiVersion": "decretum.dev/v1",
        "kind": "ExecutionRecipe",
        "domain": _text(sections.get("domain", (0, []))[1]) or "software_engineering",
        "id": _slug(title),
        "name": title,
        "version": "1.0",
        "objective": objective,
    }
    for key in ("capabilities", "inputs", "outputs"):
        values = _items(sections.get(key, (0, []))[1])
        if values:
            recipe[key] = values
    for key in ("profiles", "policy", "evidence", "completion"):
        values = _mapping(sections.get(key, (0, []))[1])
        if values:
            recipe[key] = values
    role = _text(sections.get("role", (0, []))[1])
    if role:
        recipe["role"] = role
    experiments = _experiments(sections.get("experiments", (0, []))[1])
    if experiments:
        recipe["experiments"] = experiments
    recipe["_artifact"] = "ExecutionRecipe"
    recipe["_schema"] = "schema/recipe.schema.yaml"
    recipe["_source_path"] = str(path)
    recipe["_spec_source"] = {"file": str(path), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "sections": {key: {"line": line} for key, (line, _) in sections.items()}}
    return recipe

def write_recipe(recipe: dict[str, Any], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(recipe, sort_keys=False), encoding="utf-8")
    return output
