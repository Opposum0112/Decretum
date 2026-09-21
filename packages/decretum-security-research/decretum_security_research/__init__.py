"""Security research domain pack for Decretum."""
from __future__ import annotations
from importlib.resources import files

_ROOT = files(__package__)

def domain_pack() -> dict:
    root = _ROOT
    return {
        "apiVersion": "decretum.dev/v1",
        "kind": "DomainPack",
        "id": "security-research",
        "name": "Decretum Security Research",
        "version": "0.1.0",
        "domains": ["security_research", "security-research"],
        "description": "Security research capabilities, providers, profiles and schemas.",
        "resources": {
            "schema": str(root / "schema"),
            "capabilities": str(root / "capabilities"),
            "providers": str(root / "providers"),
            "profiles": str(root / "profiles"),
            "recipes": str(root / "recipes"),
        },
    }
