"""Tests for capability surface discovery."""
from pathlib import Path

from sec_agent.capability_discovery import discover_capability_surfaces


def test_discovery_finds_known_tool_provider(monkeypatch, tmp_path):
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        """apiVersion: decretum.dev/v1
kind: CapabilityProviderRegistry
providers:
  fake-capture:
    interface: {type: tool, executable: fake-tshark}
    capabilities: [network.capture]
integrations: {}
harnesses:
  fake:
    kind: agent
    supported_interfaces: [tool]
models: {}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr("sec_agent.capability_discovery.shutil.which", lambda name: "/usr/bin/fake" if name in {"fake-tshark", "fake"} else None)
    report = discover_capability_surfaces(registry)
    surface = report["surfaces"][0]
    assert surface["capability"] == "network.capture"
    assert surface["available"] is True
    assert surface["ready"] is True
    assert surface["harnesses"] == ["fake"]


def test_discovery_proposes_unknown_recipe_capability_without_mutating_registry(tmp_path):
    registry = tmp_path / "registry.yaml"
    original = """apiVersion: decretum.dev/v1
kind: CapabilityProviderRegistry
providers:
  fake:
    interface: {type: tool, executable: fake}
    capabilities: [artifact.read]
integrations: {}
harnesses: {}
models: {}
"""
    registry.write_text(original, encoding="utf-8")
    recipe = {
        "capability_catalog": [{"id": "cloud.audit.query"}],
        "experiments": [{"id": "query", "capabilities": ["cloud.audit.query"]}],
    }
    report = discover_capability_surfaces(registry, recipe)
    assert report["candidates"][0]["capability"] == "cloud.audit.query"
    assert report["candidates"][0]["status"] == "review_required"
    assert registry.read_text(encoding="utf-8") == original


def test_discovery_digest_is_deterministic(tmp_path):
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        """providers:
  fake:
    interface: {type: tool, executable: fake}
    capabilities: [artifact.read]
integrations: {}
harnesses: {}
models: {}
""",
        encoding="utf-8",
    )
    first = discover_capability_surfaces(registry)
    second = discover_capability_surfaces(registry)
    assert first["digest"] == second["digest"]
