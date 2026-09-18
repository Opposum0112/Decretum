"""OpenAI Agents API adapter for compiled Decretum research contracts."""
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any

def _instructions(contract: dict[str, Any]) -> str:
    return """You are the execution agent for a Decretum security research project.
Treat the ResearchContract below as authoritative. Decretum defines the research
goal, inputs, capabilities, evidence requirements, completion criteria and policy.
You decide how to investigate. Never invent capabilities or bypass denied policy.
If a capability is unavailable or a new capability is required, explain it and
request a contract change or researcher approval.

ResearchContract:
""" + json.dumps(contract, indent=2, sort_keys=True) + """

Research loop:
1. Understand the objective and inputs.
2. Form and test hypotheses with permitted sandbox, MCP and tool capabilities.
3. Capture the required evidence.
4. Interact with the researcher when clarification or approval is required.
5. Run additional experiments when justified and still inside policy.
6. Produce the evidence-backed report when completion criteria are satisfied.
"""

def create_session(contract: dict[str, Any], *, model: str | None = None, stream: bool = True) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the OpenAI SDK with `uv sync`.") from exc
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for `decretum run`.")
    client = OpenAI()
    environment = contract["environment"]
    env_type = environment.get("type", "openai_hosted")
    env = {"type": "openai_hosted", "network": environment.get("network", {"mode": "none"})} if env_type == "openai_hosted" else {
        "type": "self_hosted", "workspace_directory": environment.get("workspace_directory", "/workspace")
    }
    tools: list[dict[str, Any]] = []
    if environment.get("web_search"): tools.append({"type": "web_search"})
    if environment.get("programmatic_tool_calling"): tools.append({"type": "programmatic_tool_calling"})
    for server in environment.get("mcp", []) or []:
        tools.append({"type": "mcp", "server_label": server["label"], "transport": server["transport"]})
    kwargs = {
        "agent": {
            "model": model or os.getenv("DECRETUM_MODEL", "gpt-5.6"),
            "instructions": _instructions(contract),
            "tools": tools,
        },
        "environment": env,
        "input": "Begin the research. Inspect the contract, assess available capabilities, and start with the safest useful experiment.",
        "metadata": {"decretum_contract_id": contract["contract_id"], "decretum_research_id": contract["research"]["id"]},
        "stream": stream,
    }
    return client.beta.agents.sessions.create(**kwargs)

def save_session(session: Any, artifact_dir: Path) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    data = session.model_dump() if hasattr(session, "model_dump") else session
    path = artifact_dir / "openai-session.json"
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
    return path
