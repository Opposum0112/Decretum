"""FastMCP Docker compute provider with an explicit no-host-mount policy."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import uuid
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP("decretum-docker")
_CONTAINER: str | None = None


def _run(argv: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=timeout)


def _require_docker() -> None:
    if shutil.which("docker") is None:
        raise RuntimeError("docker is required")


def _safe_remote(path: str) -> str:
    p = Path(path)
    if not path or not p.is_absolute() or ".." in p.parts:
        raise ValueError(f"remote artifact path must be absolute and traversal-free: {path!r}")
    return path


@mcp.tool()
def provision_sandbox(base_image: str, cpus: int, memory: str, tools: list[str]) -> str:
    """Create an isolated Docker container with no host filesystem mounts."""
    global _CONTAINER
    _require_docker()
    if not base_image or cpus < 1 or not memory:
        raise ValueError("invalid sandbox parameters")
    name = f"decretum-research-{uuid.uuid4().hex[:12]}"
    # --mount type=tmpfs gives the guest ephemeral writable storage without exposing the host.
    _run([
        "docker", "run", "-d", "--name", name,
        "--cpus", str(cpus), "--memory", memory,
        "--network", "none", "--read-only",
        "--mount", "type=tmpfs,destination=/tmp",
        "--mount", "type=tmpfs,destination=/run",
        "--security-opt", "no-new-privileges:true",
        "--cap-drop", "ALL", base_image, "sleep", "infinity",
    ])
    _CONTAINER = name
    return name


@mcp.tool()
def execute_instrumented(command: str, trace_flags: list[str]) -> str:
    if _CONTAINER is None:
        raise RuntimeError("sandbox is not provisioned")
    return _run(["docker", "exec", _CONTAINER, "sh", "-lc", command]).stdout


@mcp.tool()
def capture_and_hash_evidence(remote_paths: list[str], local_dest: str, algorithm: str = "sha256") -> str:
    if algorithm != "sha256":
        raise ValueError("only sha256 is supported")
    if _CONTAINER is None:
        raise RuntimeError("sandbox is not provisioned")
    dest = Path(local_dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    for remote in remote_paths:
        remote = _safe_remote(remote)
        target = dest / Path(remote).name
        _run(["docker", "cp", f"{_CONTAINER}:{remote}", str(target)])
    entries = [
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(dest)}"
        for p in sorted(dest.rglob("*"))
        if p.is_file() and p.name != "manifest.sha256"
    ]
    manifest = dest / "manifest.sha256"
    manifest.write_text("\n".join(entries) + "\n", encoding="utf-8")
    return str(manifest)


@mcp.tool()
def destroy_sandbox() -> str:
    global _CONTAINER
    if _CONTAINER is None:
        return "no sandbox"
    name = _CONTAINER
    try:
        _run(["docker", "rm", "-f", name], timeout=30)
    finally:
        _CONTAINER = None
    return name


if __name__ == "__main__":
    mcp.run()
