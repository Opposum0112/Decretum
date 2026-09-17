"""FastMCP Lima provider with no-host-mount policy."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP("decretum-lima")
_INSTANCE: str | None = None


def _run(argv: list[str], timeout: int = 120) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=timeout).stdout


@mcp.tool()
def provision_sandbox(base_image: str, cpus: int, memory: str, tools: list[str]) -> str:
    """Create an isolated Lima instance. Host mounts are intentionally disabled."""
    global _INSTANCE
    if shutil.which("limactl") is None:
        raise RuntimeError("limactl is required")
    if not base_image or cpus < 1:
        raise ValueError("invalid sandbox parameters")
    name = "decretum-research"
    config = f"images:\n- location: {base_image}\ncpus: {cpus}\nmemory: {memory}\nmounts: []\n" 
    config_path = Path(".decretum-lima.yaml")
    config_path.write_text(config, encoding="utf-8")
    _run(["limactl", "create", "--name", name, str(config_path)])
    _run(["limactl", "start", name])
    _INSTANCE = name
    return name


@mcp.tool()
def execute_instrumented(command: str, trace_flags: list[str]) -> str:
    """Execute a command inside the current isolated Lima instance."""
    if _INSTANCE is None:
        raise RuntimeError("sandbox is not provisioned")
    return _run(["limactl", "shell", _INSTANCE, "--", "sh", "-lc", command])


@mcp.tool()
def capture_and_hash_evidence(remote_paths: list[str], local_dest: str, algorithm: str = "sha256") -> str:
    """Copy declared evidence and emit a deterministic SHA-256 manifest."""
    if algorithm != "sha256":
        raise ValueError("only sha256 is supported")
    if _INSTANCE is None:
        raise RuntimeError("sandbox is not provisioned")
    dest = Path(local_dest).resolve(); dest.mkdir(parents=True, exist_ok=True)
    for remote in remote_paths:
        _run(["limactl", "shell", _INSTANCE, "--", "sh", "-lc", f"cat -- {remote}"], timeout=120)
        output = subprocess.run(["limactl", "shell", _INSTANCE, "--", "cat", remote], check=True, capture_output=True).stdout
        target = dest / Path(remote).name
        target.write_bytes(output)
    entries = []
    for path in sorted(dest.rglob("*")):
        if path.is_file() and path.name != "manifest.sha256":
            entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(dest)}")
    manifest = dest / "manifest.sha256"; manifest.write_text("\n".join(entries) + "\n", encoding="utf-8")
    return str(manifest)


@mcp.tool()
def destroy_sandbox() -> str:
    """Stop and delete the current Lima instance."""
    global _INSTANCE
    if _INSTANCE is None:
        return "no sandbox"
    name = _INSTANCE
    try:
        _run(["limactl", "delete", "--force", name])
    finally:
        _INSTANCE = None
    return name


if __name__ == "__main__":
    mcp.run()
