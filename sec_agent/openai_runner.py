"""OpenAI Agents SDK adapter with local-only sandbox execution."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any


def _instructions(contract: dict[str, Any]) -> str:
    return """You are the execution agent for a Decretum security research project.

Treat the ResearchContract below as authoritative. Decretum defines the research
goal, inputs, capabilities, evidence requirements, completion criteria and policy.
You decide how to investigate. Never invent capabilities or bypass denied policy.

Execution boundary:
- All experiment commands MUST execute in the selected local sandbox.
- Never request, create, or use a hosted/cloud sandbox.
- Never move a workload to provider-managed execution.
- If the local backend cannot satisfy a requirement, stop and request a contract
  change or researcher approval.

Research loop:
1. Understand the objective and inputs.
2. Inspect the local sandbox and staged inputs.
3. Form and test hypotheses with permitted capabilities.
4. Capture required evidence.
5. Ask for clarification/approval when policy requires it.
6. Run additional experiments only inside the declared local sandbox.
7. Produce the evidence-backed report when completion criteria are satisfied.

ResearchContract:
""" + json.dumps(contract, indent=2, sort_keys=True)


def _sample_entries(contract: dict[str, Any], recipe_dir: Path) -> dict[str, Any]:
    from agents.sandbox.entries import LocalDir, LocalFile

    entries: dict[str, Any] = {}
    inputs = contract.get("inputs", {})
    if not isinstance(inputs, dict):
        return entries

    values = []
    for key in ("sample", "workload", "artifact"):
        if inputs.get(key):
            values.append(inputs[key])
    values.extend(inputs.get("artifacts", []) or [])

    for value in values:
        source = (recipe_dir / str(value)).resolve()
        if source.is_file():
            entries[f"input/{source.name}"] = LocalFile(src=source)
        elif source.is_dir():
            entries[f"input/{source.name}"] = LocalDir(src=source)
        else:
            raise FileNotFoundError(f"Research input does not exist: {source}")
    return entries


def _build_sandbox(contract: dict[str, Any], recipe_dir: Path) -> Any:
    from agents.sandbox import Manifest, SandboxRunConfig
    from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient

    environment = contract["environment"]
    sandbox = environment["sandbox"]
    backend = sandbox["backend"]
    manifest = Manifest(entries=_sample_entries(contract, recipe_dir))

    if backend == "unix":
        client = UnixLocalSandboxClient(inherit_host_environment=False)
        options = None
    elif backend == "docker":
        try:
            from agents.sandbox.sandboxes.docker import (
                DockerSandboxClient,
                DockerSandboxClientOptions,
            )
            import docker
        except ImportError as exc:
            raise RuntimeError(
                "Docker backend requires the Agents SDK Docker extra and a local Docker daemon."
            ) from exc
        client = DockerSandboxClient(docker.from_env())
        network_mode = environment.get("network", {}).get("mode", "none")
        options = DockerSandboxClientOptions(
            image=sandbox["image"],
            network_mode=network_mode,
        )
    else:
        raise ValueError(f"Unsupported local sandbox backend: {backend}")

    return SandboxRunConfig(client=client, options=options, manifest=manifest)


async def _run(contract: dict[str, Any], recipe_dir: Path, model: str) -> Any:
    from agents import Runner, SandboxAgent
    from agents.run import RunConfig

    sandbox_config = _build_sandbox(contract, recipe_dir)
    client = sandbox_config.client
    agent = SandboxAgent(
        name=f"Decretum researcher: {contract['research']['id']}",
        model=model,
        instructions=_instructions(contract),
    )
    try:
        return await Runner.run(
            agent,
            "Begin the research inside the local sandbox. Inspect staged inputs, "
            "verify capabilities, and perform the safest useful experiment. "
            "Do not execute outside the sandbox.",
            run_config=RunConfig(sandbox=sandbox_config),
        )
    finally:
        close = getattr(client, "aclose", None)
        if close:
            await close()


def create_session(
    contract: dict[str, Any],
    *,
    recipe_dir: Path,
    model: str | None = None,
) -> Any:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for model reasoning.")
    return asyncio.run(_run(contract, recipe_dir, model or os.getenv("DECRETUM_MODEL", "gpt-5.6")))


def save_session(result: Any, artifact_dir: Path) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    data = result.model_dump() if hasattr(result, "model_dump") else {
        "final_output": getattr(result, "final_output", None),
        "last_agent": getattr(getattr(result, "last_agent", None), "name", None),
    }
    path = artifact_dir / "openai-run.json"
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
    return path
