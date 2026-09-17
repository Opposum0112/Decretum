"""Offline forensic artifact inspection MCP service."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
import duckdb
from fastmcp import FastMCP

mcp = FastMCP("decretum-artifact-inspector")


def _safe_artifact(path: str) -> Path:
    p = Path(path).resolve()
    if not p.is_file(): raise FileNotFoundError(p)
    return p


@mcp.tool()
def query_pcap(pcap_path: str, display_filter: str = "") -> str:
    """Query a PCAP with tshark; display_filter is passed as a tshark display filter."""
    p = _safe_artifact(pcap_path)
    if shutil.which("tshark") is None: raise RuntimeError("tshark is required")
    argv = ["tshark", "-r", str(p), "-T", "fields", "-e", "frame.number", "-e", "ip.src", "-e", "ip.dst"]
    if display_filter: argv += ["-Y", display_filter]
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=120).stdout


@mcp.tool()
def query_syscalls(log_path: str, sql_query: str) -> str:
    """Query line-oriented syscall telemetry through DuckDB's read_csv_auto."""
    p = _safe_artifact(log_path)
    con = duckdb.connect(database=":memory:")
    try:
        # The caller supplies SELECT SQL; the file is exposed as table `events`.
        con.execute("CREATE VIEW events AS SELECT * FROM read_csv_auto(?, union_by_name=true)", [str(p)])
        if not re.match(r"^\s*(select|with)\b", sql_query, re.I): raise ValueError("only SELECT/WITH queries are allowed")
        rows = con.execute(sql_query).fetchall()
        return json.dumps(rows, default=str)
    finally: con.close()


@mcp.tool()
def dump_strings(binary_path: str, min_len: int = 4) -> str:
    """Extract printable ASCII strings without executing the artifact."""
    p = _safe_artifact(binary_path)
    if min_len < 1: raise ValueError("min_len must be positive")
    data = p.read_bytes()
    return "\n".join(m.decode("ascii", "ignore") for m in re.findall(rb"[ -~]{%d,}" % min_len, data))


@mcp.tool()
def generate_role_report(role: str, template: str, findings: dict[str, object] | None = None) -> str:
    """Render a deterministic Markdown role report from supplied offline findings."""
    allowed = {"threat_researcher", "supply_chain_auditor", "detection_engineer", "vulnerability_exploit_researcher"}
    if role not in allowed: raise ValueError("unsupported role")
    body = json.dumps(findings or {}, indent=2, sort_keys=True)
    return f"# {template}\n\n**Role:** `{role}`\n\n## Findings\n\n```json\n{body}\n```\n"


if __name__ == "__main__": mcp.run()
