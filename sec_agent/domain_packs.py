"""Discover and validate installable Decretum domain packs."""
from __future__ import annotations
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any
import yaml

ENTRY_POINT_GROUP = "decretum.domain_packs"
REQUIRED_MANIFEST_FIELDS = {"apiVersion", "kind", "id", "name", "version", "domains"}

def discover_domain_packs() -> list[dict[str, Any]]:
    discovered = []
    for ep in sorted(entry_points(group=ENTRY_POINT_GROUP), key=lambda item: item.name):
        try:
            provider = ep.load()
            manifest = provider() if callable(provider) else provider
            if not isinstance(manifest, dict):
                raise ValueError("entry point must return a mapping")
            item = dict(manifest)
            item["entry_point"] = ep.name
            item["distribution"] = ep.dist.name if ep.dist else None
            item["distribution_version"] = ep.dist.version if ep.dist else None
            discovered.append(item)
        except Exception as exc:
            discovered.append({"entry_point": ep.name, "distribution": ep.dist.name if ep.dist else None, "error": str(exc)})
    return discovered

def validate_domain_pack_manifest(manifest: dict[str, Any]) -> list[str]:
    errors = [f"missing required field: {field}" for field in sorted(REQUIRED_MANIFEST_FIELDS - set(manifest))]
    if manifest.get("apiVersion") != "decretum.dev/v1": errors.append("apiVersion must be decretum.dev/v1")
    if manifest.get("kind") != "DomainPack": errors.append("kind must be DomainPack")
    if not isinstance(manifest.get("id"), str) or not manifest.get("id"): errors.append("id must be a non-empty string")
    if not isinstance(manifest.get("domains"), list) or not manifest.get("domains"): errors.append("domains must be a non-empty list")
    if "version" in manifest and not isinstance(manifest["version"], str): errors.append("version must be a string")
    return errors

def load_pack_manifest(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict): raise ValueError("domain pack manifest must be a mapping")
    return value

def validate_pack_directory(path: Path) -> list[str]:
    manifest_path = path / "domain-pack.yaml"
    if not manifest_path.is_file(): return [f"missing {manifest_path}"]
    try: manifest = load_pack_manifest(manifest_path)
    except (OSError, yaml.YAMLError, ValueError) as exc: return [f"invalid manifest: {exc}"]
    errors = validate_domain_pack_manifest(manifest)
    for relative in ("schema", "capabilities", "profiles", "recipes"):
        if not (path / relative).exists(): errors.append(f"domain pack should contain {relative}/")
    return errors

def installed_pack_summary() -> list[dict[str, Any]]:
    result = []
    for pack in discover_domain_packs():
        result.append({"id": pack.get("id"), "name": pack.get("name"), "version": pack.get("version"), "domains": pack.get("domains"), "distribution": pack.get("distribution"), "status": "error" if pack.get("error") else "ready", "error": pack.get("error")})
    return result
