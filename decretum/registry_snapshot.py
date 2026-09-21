"""Immutable registry snapshots used by execution contracts and replay."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .validator import load_provider_registry


def canonical_registry(registry: dict[str, Any]) -> bytes:
    return json.dumps(registry, sort_keys=True, separators=(",", ":")).encode()


def registry_digest(registry: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_registry(registry)).hexdigest()


def snapshot_registry(registry_path: Path, artifact_dir: Path) -> dict[str, Any]:
    registry = load_provider_registry(str(registry_path))
    digest = registry_digest(registry)
    snapshot = {
        "source": str(registry_path),
        "digest": digest,
        "registry": registry,
    }
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "provider-registry.snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return snapshot


def load_snapshot(path: Path) -> dict[str, Any]:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    actual = registry_digest(snapshot["registry"])
    if actual != snapshot.get("digest"):
        raise ValueError("provider registry snapshot digest mismatch")
    return snapshot
