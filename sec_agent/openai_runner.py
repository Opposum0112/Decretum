"""Codex CLI executor for local Decretum research contracts.

Decretum owns the contract and policy. Codex owns interactive local execution.
No hosted/cloud sandbox is provisioned by this adapter.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any


SANDBOX_MODES = {"read-only", "workspace-write", "danger-full-access"}
APPROVAL_POLICIES = {"untrusted", "on-request", "never"}


def _instructions(contract: dict[str, Any]) -> str:
    return f"""You are the Codex execution agent for a Decretum security research project.

The Decretum ResearchContract below is authoritative. Follow its objective,
capabilities, evidence requirements, completion criteria, and policy.

Execution rules:
- Execute locally through the Codex runtime only.
- Do not provision or request a hosted/cloud sandbox.
- Do not silently widen filesystem, network, privilege, or tool access.
- Never bypass a denied capability.
- If a required capability is outside the contract, stop and request researcher
  approval or a contract amendment.
- Keep experiment artifacts and reports in the declared workspace.
- Prefer the safest useful experiment first.
- Capture evidence before drawing conclusions.

Research loop:
1. Inspect the contract and workspace.
2. Inspect available inputs and local research tools.
3. Form a hypothesis.
4. Run a bounded experiment.
5. Collect and preserve evidence.
6. Reassess the hypothesis.
7. Continue only within policy.
8. Produce the requested evidence-backed report.

ResearchContract:
{json.dumps(contract, indent=2, sort_keys=True)}
"""


def _codex_options(contract: dict[str, Any], workspace: Path) -> tuple[str, dict[str, Any], dict[str, Any]]:
    environment = contract["environment"]
    codex = environment.get("codex", {})
    sandbox_mode = codex.get("sandbox_mode", "workspace-write")
    approval_policy = codex.get("approval_policy", "on-request")
    if sandbox_mode not in SANDBOX_MODES:
        raise ValueError(f"Unsupported Codex sandbox_mode: {sandbox_mode}")
    if approval_policy not in APPROVAL_POLICIES:
        raise ValueError(f"Unsupported Codex approval_policy: {approval_policy}")

    thread_options = {
        "model": codex.get("model") or os.getenv("DECRETUM_MODEL", "gpt-5.6"),
        "model_reasoning_effort": codex.get("reasoning_effort", "medium"),
        "network_access_enabled": bool(codex.get("network_access_enabled", False)),
        "web_search_mode": codex.get("web_search_mode", "disabled"),
        "approval_policy": approval_policy,
    }
    turn_options = {
        "idle_timeout_seconds": int(codex.get("idle_timeout_seconds", 120)),
    }
    return sandbox_mode, thread_options, turn_options


async def _run(contract: dict[str, Any], workspace: Path, prompt: str, session_db: Path) -> Any:
    from agents import Agent, Runner, SQLiteSession
    from agents.extensions.experimental.codex import ThreadOptions, TurnOptions, codex_tool

    sandbox_mode, thread_options, turn_options = _codex_options(contract, workspace)
    environment = contract["environment"]
    codex = environment.get("codex", {})

    tool = codex_tool(
        name="codex_researcher",
        sandbox_mode=sandbox_mode,
        working_directory=str(workspace),
        skip_git_repo_check=bool(codex.get("skip_git_repo_check", False)),
        default_thread_options=ThreadOptions(**thread_options),
        default_turn_options=TurnOptions(**turn_options),
        persist_session=bool(codex.get("persist_session", True)),
    )

    agent = Agent(
        name="Decretum Codex Researcher",
        instructions=_instructions(contract),
        tools=[tool],
    )

    prompt = (
        prompt
        + "\\n\\nUse the codex_researcher tool for workspace/evidence inspection and "
        "experiments. Keep conclusions tied to observed evidence and do not "
        "execute through a hosted sandbox."
    )
    session = SQLiteSession(contract["research"]["id"], str(session_db))
    return await Runner.run(agent, prompt, session=session)


def create_session(
    contract: dict[str, Any],
    *,
    workspace: Path,
    model: str | None = None,
    prompt: str | None = None,
    session_db: Path | None = None,
) -> Any:
    """Run a complete local Codex research session."""
    if model:
        contract = json.loads(json.dumps(contract))
        contract.setdefault("environment", {}).setdefault("codex", {})["model"] = model
    if not (os.getenv("CODEX_API_KEY") or os.getenv("OPENAI_API_KEY")):
        raise RuntimeError("CODEX_API_KEY or OPENAI_API_KEY is required for Codex.")
    workspace = workspace.resolve()
    if not workspace.exists():
        raise FileNotFoundError(f"Codex workspace does not exist: {workspace}")
    db = (session_db or (workspace / ".decretum" / "research-session.sqlite3")).resolve()
    db.parent.mkdir(parents=True, exist_ok=True)
    return asyncio.run(_run(contract, workspace, prompt or "Begin the research and work until the current evidence is sufficient for the requested stage.", db))


def save_session(result: Any, artifact_dir: Path) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    data = result.model_dump() if hasattr(result, "model_dump") else {
        "final_output": getattr(result, "final_output", None),
        "last_agent": getattr(getattr(result, "last_agent", None), "name", None),
    }
    path = artifact_dir / "codex-run.json"
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
    return path
