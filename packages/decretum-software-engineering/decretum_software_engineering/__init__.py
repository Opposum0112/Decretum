"""Software engineering domain pack for Decretum."""
from importlib.resources import files
_ROOT = files(__package__)
def domain_pack() -> dict:
    return {
        "apiVersion": "decretum.dev/v1",
        "kind": "DomainPack",
        "id": "software-engineering",
        "name": "Decretum Software Engineering",
        "version": "0.1.0",
        "domains": ["software_engineering", "software-engineering"],
        "resources": {
            "capabilities": str(_ROOT / "capabilities"),
            "providers": str(_ROOT / "providers"),
            "profiles": str(_ROOT / "profiles"),
            "schema": str(_ROOT / "schema"),
            "recipes": str(_ROOT / "recipes"),
        },
    }
