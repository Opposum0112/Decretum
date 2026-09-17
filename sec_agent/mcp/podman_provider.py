"""FastMCP rootless Podman provider with no host mounts."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP("decretum-podman")
_CONTAINER: str | None = None


def _run(argv: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=timeout)


@mcp.tool()
def provision_sandbox(base_image: str, cpus: int, memory: str, tools: list[str]) -> str:
    """Create a rootless container with no host filesystem mounts."""
    global _CONTAINER
    if shutil.which("podman") is None:
        raise RuntimeError("podman is required")
    if not base_image or cpus < 1:
        raise ValueError("invalid sandbox parameters")
    name = "decretum-research"
    _run(["podman", "rm", "-f", name], timeout=30) if subprocess.run(["podman", "container", "exists", name]).returncode == 0 else None
    _run(["podman", "run", "-d", "--name", name, "--cpus", str(cpus), "--memory", memory, "--network", "none", base_image, "sleep", "infinity"])
    _CONTAINER = name
    return name


@mcp.tool()
def execute_instrumented(command: str, trace_flags: list[str]) -> str:
    if _CONTAINER is None:
        raise RuntimeError("sandbox is not provisioned")
    return _run(["podman", "exec", _CONTAINER, "sh", "-lc", command]).stdout


@mcp.tool()
def capture_and_hash_evidence(remote_paths: list[str], local_dest: str, algorithm: str = "sha256") -> str:
    if algorithm != "sha256":
        raise ValueError("only sha256 is supported")
    if _CONTAINER is None:
        raise RuntimeError("sandbox is not provisioned")
    dest = Path(local_dest).resolve(); dest.mkdir(parents=True, exist_ok=True)
    for remote in remote_paths:
        target = dest / Path(remote).name
        result = subprocess.run(["podman", "cp", f"{_CONTAINER}:{remote}", str(target)], check=True, capture_output=True, text=True)
        if result.returncode != 0: raise RuntimeError(result.stderr)
    entries = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(dest)}" for p in sorted(dest.rglob("*")) if p.is_file() and p.name != "manifest.sha256"]
    manifest = dest / "manifest.sha256"; manifest.write_text("\n".join(entries) + "\n", encoding="utf-8")
    return str(manifest)


@mcp.tool()
def destroy_sandbox() -> str:
    global _CONTAINER
    if _CONTAINER is None: return "no sandbox"
    name = _CONTAINER
    try: _run(["podman", "rm", "-f", name])
    finally: _CONTAINER = None
    return name


if __name__ == "__main__": mcp.run()
