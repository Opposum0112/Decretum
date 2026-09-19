"""Compile Decretum research recipes into portable machine-readable contracts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .resolver import resolve_capabilities
from .validator import (
    DEFAULT_PROVIDER_REGISTRY,
    required_capabilities,
)

@dataclass(frozen=True, slots=True)
class ExecutionContract:
    contract_id: str
    contract: dict[str, Any]
    artifact_dir: Path


def _required_capabilities(recipe: dict[str, Any], registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> dict[str, list[str]]:\n    """Return the canonical capability closure from the validator."""\n    required = required_capabilities(recipe, registry_path)\n    denied = set((recipe.get("policy", {}) or {}).get("deny", []) or [])\n    return {"required": sorted(required), "denied": sorted(denied)}\n
