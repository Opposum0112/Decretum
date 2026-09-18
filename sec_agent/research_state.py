"""Structured durable research state for interactive evidence-driven investigations."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def append_event(root: Path, event_type: str, payload: dict[str, Any]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "research-ledger.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp": _now(), "type": event_type, "payload": payload}, sort_keys=True, default=str) + "\n")
    return path

def record_evidence(root: Path, evidence_id: str, kind: str, path: str | None = None, experiment_id: str | None = None, description: str = "") -> dict[str, Any]:
    item = {"id": evidence_id, "kind": kind, "path": path, "experiment_id": experiment_id, "description": description, "collected_at": _now()}
    if path and Path(path).is_file():
        item["sha256"] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    append_event(root, "evidence_recorded", item)
    return item

def record_hypothesis(root: Path, hypothesis_id: str, statement: str, status: str = "proposed", based_on: list[str] | None = None) -> dict[str, Any]:
    item = {"id": hypothesis_id, "statement": statement, "status": status, "based_on": based_on or []}
    append_event(root, "hypothesis_recorded", item)
    return item

def record_finding(root: Path, finding_id: str, statement: str, evidence_ids: list[str] | None = None, confidence: str | None = None) -> dict[str, Any]:
    item = {"id": finding_id, "statement": statement, "evidence_ids": evidence_ids or [], "confidence": confidence}
    append_event(root, "finding_recorded", item)
    return item

def request_experiment(root: Path, request_id: str, objective: str, hypothesis_id: str | None = None, requested_capabilities: list[str] | None = None, evidence_required: list[str] | None = None, approval_required: bool = True) -> dict[str, Any]:
    item = {"id": request_id, "hypothesis_id": hypothesis_id, "objective": objective, "requested_capabilities": requested_capabilities or [], "evidence_required": evidence_required or [], "approval_required": approval_required, "status": "proposed"}
    append_event(root, "experiment_requested", item)
    return item

def read_events(root: Path) -> list[dict[str, Any]]:
    path = root / "research-ledger.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def evidence_context(root: Path, limit: int = 60) -> str:
    events = read_events(root)
    return json.dumps(events[-limit:], indent=2, sort_keys=True) if events else "No structured research state has been recorded yet."
