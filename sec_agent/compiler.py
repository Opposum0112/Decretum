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
    canonical = json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode()
    contract_id = hashlib.sha256(canonical).hexdigest()[:16]
    provider = recipe["compute"]["provider"]
    mcp_config = {
        "mcpServers": {
            "compute": {"command": "python", "args": ["-m", f"sec_agent.mcp.{provider}_provider"]},
            "artifact-inspector": {"command": "python", "args": ["-m", "sec_agent.mcp.artifact_inspector"]},
        }
    }
    return ExecutionContract(contract_id, json.loads(json.dumps(recipe)), artifact_dir, mcp_config)


def dispatch(contract: ExecutionContract, *, dry_run: bool = True) -> int:
    harness = contract.recipe["harness"]
    command = contract.recipe["workload"]["command"]
    if dry_run or harness == "headless":
        return 0 if dry_run else subprocess.run(["sh", "-lc", command], check=False).returncode
    if harness == "goose":
        argv = ["goose", "run", "--", command]
    elif harness == "pi":
        argv = ["pi", "run", command]
    else:
        raise ValueError(f"unsupported harness: {harness}")
    return subprocess.run(argv, check=False).returncode
