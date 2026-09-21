"""Canonical capability registry and explicit promotion workflow.

Discovery may propose candidates, but only an explicit domain-authoring action can
promote a capability into the canonical recipe vocabulary.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import yaml

DEFAULT_CAPABILITY_REGISTRY = None
VALID_KINDS = {"artifact","filesystem","process","network","identity","cloud","container","instrumentation","analysis","reporting","compute"}
VALID_RISKS = {"read","observe","collect","execute","write","privileged","network_access"}
ID_RE = re.compile(r"^[a-z][a-z0-9_-]*(\.[a-z0-9_-]+)+$")


def load_capability_registry(path: Path | None = DEFAULT_CAPABILITY_REGISTRY, domain: str | None = None) -> dict[str, Any]:
    if path is None:\n        from .domain_packs import resource_for_domain\n        path = resource_for_domain(domain, "capabilities") / "capability_registry.yaml"\n    if path.is_dir(): path = path / "capability_registry.yaml"\n    if not path.exists():
        return {"apiVersion": "decretum.dev/v1", "kind": "CapabilityRegistry", "version": "1.0", "capabilities": {}}
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict) or not isinstance(value.get("capabilities"), dict):
        raise ValueError("capability registry must contain a capabilities mapping")
    return value


def validate_capability_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cid = spec.get("id")
    if not isinstance(cid, str) or not ID_RE.fullmatch(cid):
        errors.append("capability id must use dotted lowercase form such as cloud.audit.query")
    if spec.get("kind") not in VALID_KINDS:
        errors.append(f"invalid capability kind: {spec.get('kind')!r}")
    if spec.get("risk") not in VALID_RISKS:
        errors.append(f"invalid capability risk: {spec.get('risk')!r}")
    for field in ("name", "description"):
        if not isinstance(spec.get(field), str) or not spec[field].strip():
            errors.append(f"capability {field} is required")
    for field in ("allowed_isolations", "allowed_networks", "allowed_execution_modes", "evidence_outputs"):
        if field in spec and not isinstance(spec[field], list):
            errors.append(f"{field} must be a list")
    return errors


def canonical_capabilities(path: Path | None = DEFAULT_CAPABILITY_REGISTRY, domain: str | None = None) -> dict[str, dict[str, Any]]:
    return load_capability_registry(path, domain=domain).get("capabilities", {})


def promote_capability(spec: dict[str, Any], path: Path | None = DEFAULT_CAPABILITY_REGISTRY, domain: str | None = None) -> None:
    errors = validate_capability_spec(spec)
    if errors:
        raise ValueError("; ".join(errors))
    registry = load_capability_registry(path, domain=domain)
    capabilities = registry.setdefault("capabilities", {})
    existing = capabilities.get(spec["id"])
    if existing and existing != spec:
        raise ValueError(f"capability {spec['id']!r} already exists with different semantics")
    capabilities[spec["id"]] = spec
    registry["version"] = str(registry.get("version", "1.0"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")


def candidate(report_path: Path, capability_id: str) -> dict[str, Any] | None:
    payload = yaml.safe_load(report_path.read_text(encoding="utf-8")) or {}
    for item in payload.get("candidates", []) or []:
        if item.get("capability") == capability_id:
            return item
    return None
