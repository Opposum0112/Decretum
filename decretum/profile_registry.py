"""Load and validate execution configuration profiles.

Profiles are preferences/configuration only. They never create or redefine
canonical capabilities.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_PROFILE_REGISTRY = None
PROFILE_TYPES = {"infrastructure", "instrumentation", "harness"}


def load_profile_registry(path: Path | None = DEFAULT_PROFILE_REGISTRY, domain: str | None = None) -> dict[str, Any]:
    if path is None:\n        from .domain_packs import resource_for_domain\n        path = resource_for_domain(domain, "profiles") / "profile_registry.yaml"\n    if path.is_dir(): path = path / "profile_registry.yaml"\n    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError("profile registry must be a mapping")
    for section in PROFILE_TYPES:
        if not isinstance(value.get(section, {}), dict):
            raise ValueError(f"profile registry section {section!r} must be a mapping")
    return value


def get_profile(profile_type: str, profile_id: str, path: Path | None = DEFAULT_PROFILE_REGISTRY, domain: str | None = None) -> dict[str, Any]:
    if profile_type not in PROFILE_TYPES:
        raise ValueError(f"unsupported profile type: {profile_type}")
    registry = load_profile_registry(path, domain=domain)
    profile = (registry.get(profile_type) or {}).get(profile_id)
    if not isinstance(profile, dict):
        raise KeyError(f"{profile_type} profile {profile_id!r} is not registered")
    if profile.get("type", profile_type) != profile_type:
        raise ValueError(f"profile {profile_id!r} has type {profile.get('type')!r}, expected {profile_type!r}")
    return profile


def resolve_recipe_profiles(recipe: dict[str, Any], path: Path | None = DEFAULT_PROFILE_REGISTRY) -> dict[str, Any]:
    """Resolve profile references without changing the recipe's experiment semantics."""
    result: dict[str, Any] = {"references": {}, "profiles": {}}
    refs = {
        "infrastructure": recipe.get("infrastructure_profile"),
        "instrumentation": recipe.get("instrumentation_profile"),
        "harness": recipe.get("harness_profile"),
    }
    for profile_type, profile_id in refs.items():
        if not profile_id:
            continue
        result["references"][profile_type] = profile_id
        result["profiles"][profile_type] = get_profile(profile_type, profile_id, path, recipe.get("domain"))
    return result


def validate_recipe_profiles(recipe: dict[str, Any], path: Path | None = DEFAULT_PROFILE_REGISTRY) -> list[str]:
    errors: list[str] = []
    try:
        registry = load_profile_registry(path, domain=recipe.get("domain"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"profile registry unavailable: {exc}"]

    mappings = {
        "infrastructure_profile": "infrastructure",
        "instrumentation_profile": "instrumentation",
        "harness_profile": "harness",
    }
    for field, profile_type in mappings.items():
        value = recipe.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not value:
            errors.append(f"{field} must be a non-empty profile identifier")
            continue
        if value not in (registry.get(profile_type) or {}):
            errors.append(f"{field} {value!r} is not registered")
    # Prevent semantic/configuration leakage back into the recipe.
    if "compute" in recipe:
        errors.append("compute must be defined by infrastructure_profile, not inline in the recipe")
    if "instrumentation" in recipe:
        errors.append("instrumentation must be defined by instrumentation_profile, not inline in the recipe")
    return errors
