"""Run a selected MCP service: python -m sec_agent.mcp.__main__ <lima|podman|artifacts>."""
from __future__ import annotations
import sys

def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "artifacts"
    if target == "lima":
        from .lima_provider import mcp
    elif target == "podman":
        from .podman_provider import mcp
    elif target in {"artifacts", "artifact-inspector"}:
        from .artifact_inspector import mcp
    else:
        raise SystemExit(f"unknown MCP service: {target}")
    mcp.run()

if __name__ == "__main__": main()
