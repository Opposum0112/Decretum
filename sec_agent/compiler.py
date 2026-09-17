"""Compile recipes into immutable execution contracts and dispatch harnesses."""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ExecutionContract:
    contract_id: str
    recipe: dict[str, Any]
    artifact_dir: Path
    mcp_config: dict[str, Any]


def compile_recipe(recipe: dict[str, Any], artifact_dir: Path) -> ExecutionContract:
    """Create a deterministic, immutable execution contract from a validated recipe."""
    canonical = json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode()
    contract_id = hashlib.sha256(canonical).hexdigest()[:16]
    provider = recipe["compute"]["provider"]
    mcp_config = {
        "mcpServers": {
            "compute": {
                "command": "python",
                "args": ["-m", f"sec_agent.mcp.{provider}_provider"],
            },
            "artifact-inspector": {
                "command": "python",
                "args": ["-m", "sec_agent.mcp.artifact_inspector"],
            },
        }
    }
    return ExecutionContract(
        contract_id,
        json.loads(json.dumps(recipe)),
        artifact_dir,
        mcp_config,
    )


def dispatch(contract: ExecutionContract, *, dry_run: bool = True) -> int:
    """Dispatch a recipe without ever running its workload directly on the host.

    The compute provider owns sandbox provisioning and workload execution. Harnesses
    may orchestrate the run, but the final command must execute inside that sandbox.
    """
    recipe = contract.recipe
    provider = recipe["compute"]["provider"]
    command = recipe["workload"]["command"]
    timeout = recipe["workload"].get("timeout_seconds", 300)

    if dry_run:
        return 0

    # Keep this path provider-neutral. A provider module exposes the same MCP tool
    # contract; direct host subprocess execution is deliberately not supported.
    module = f"sec_agent.mcp.{provider}_provider"
    provision = [
        "python",
        "-m",
        module,
        "--provision",
        recipe["compute"]["base_image"],
        "--cpus",
        str(recipe["compute"]["cpus"]),
        "--memory",
        recipe["compute"]["memory"],
    ]
    execute = ["python", "-m", module, "--execute", command]
    destroy = ["python", "-m", module, "--destroy"]

    # Provider CLIs are intentionally invoked as separate lifecycle operations so
    # cleanup remains possible even when the workload exits non-zero or times out.
    try:
        subprocess.run(provision, check=True, timeout=120)
        result = subprocess.run(execute, check=False, timeout=timeout)
        return result.returncode
    except subprocess.TimeoutExpired:
        return 124
    finally:
        subprocess.run(destroy, check=False, timeout=60)
