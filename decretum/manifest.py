"""Create a complete immutable compilation manifest for replay."""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
from typing import Any

from .registry_snapshot import registry_digest, snapshot_registry
from .validator import DEFAULT_PROVIDER_REGISTRY, load_provider_registry


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_digest(manifest: dict[str, Any]) -> str:
    body = {k: v for k, v in manifest.items() if k != "digest"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def create_manifest(
    recipe_path: Path,
    schema_path: Path,
    registry_path: Path,
    artifact_dir: Path,
    compiler_version: str = "0.1",
) -> dict[str, Any]:
    snapshot = snapshot_registry(registry_path, artifact_dir)
    manifest = {
        "manifest_version": "1",
        "compiler_version": compiler_version,
        "recipe": {"path": str(recipe_path), "sha256": file_digest(recipe_path)},
        "schema": {"path": str(schema_path), "sha256": file_digest(schema_path)},
        "provider_registry": {"path": str(registry_path), "sha256": registry_digest(load_provider_registry(str(registry_path)))},
        "registry_snapshot": {"artifact": "provider-registry.snapshot.json", "sha256": file_digest(artifact_dir / "provider-registry.snapshot.json"), "digest": snapshot["digest"]},
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    manifest["digest"] = manifest_digest(manifest)
    (artifact_dir / "compilation-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
