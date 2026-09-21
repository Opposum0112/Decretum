from pathlib import Path

from sec_agent.domain_packs import load_pack_manifest, validate_domain_pack_manifest, validate_pack_directory

PACK = Path("examples/domain-pack")

def test_domain_pack_manifest_is_valid():
    manifest = load_pack_manifest(PACK / "domain-pack.yaml")
    assert validate_domain_pack_manifest(manifest) == []

def test_domain_pack_layout_is_valid():
    assert validate_pack_directory(PACK) == []
