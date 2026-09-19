"""Tamper-evident execution provenance and durable research state."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(canonical).hexdigest()


def _event_digest(event: dict[str, Any]) -> str:
    return _digest(event)


def append_event(root: Path, event_type: str, payload: dict[str, Any]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "research-ledger.jsonl"
    previous_hash = ""
    if path.exists():
        try:
            previous = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
            previous_hash = previous.get("event_hash", "")
        except (json.JSONDecodeError, IndexError):
            previous_hash = ""

    event = {
        "timestamp": _now(),
        "type": event_type,
        "payload": payload,
        "previous_event_hash": previous_hash,
    }
    event["event_hash"] = _event_digest(event)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
    return path


def verify_ledger(root: Path) -> dict[str, Any]:
    path = root / "research-ledger.jsonl"
    if not path.exists():
        return {"valid": True, "events": 0, "errors": []}

    previous_hash = ""
    errors = []
    events = 0
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        events += 1
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append({"line": number, "reason": f"invalid_json: {exc}"})
            continue
        if event.get("previous_event_hash", "") != previous_hash:
            errors.append({"line": number, "reason": "previous_event_hash_mismatch"})
        stored = event.pop("event_hash", None)
        if stored != _event_digest(event):
            errors.append({"line": number, "reason": "event_hash_mismatch"})
        event["event_hash"] = stored
        previous_hash = stored or ""
    return {"valid": not errors, "events": events, "errors": errors, "head": previous_hash}


def record_execution(
    root: Path, execution_id: str, contract_id: str, plan_digest: str,
    experiment_id: str, provider: str, interface: str, harness: str,
    status: str = "started", inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = {
        "id": execution_id, "contract_id": contract_id, "plan_digest": plan_digest,
        "experiment_id": experiment_id, "provider": provider, "interface": interface,
        "harness": harness, "status": status, "inputs": inputs or {}, "started_at": _now(),
    }
    item["provenance_digest"] = _digest(item)
    append_event(root, "execution_started", item)
    return item


def record_execution_result(
    root: Path, execution_id: str, status: str,
    outputs: dict[str, Any] | None = None, error: str | None = None,
) -> dict[str, Any]:
    item = {
        "execution_id": execution_id, "status": status, "outputs": outputs or {},
        "error": error, "completed_at": _now(),
    }
    item["result_digest"] = _digest(item)
    append_event(root, "execution_completed", item)
    return item


def record_evidence(
    root: Path, evidence_id: str, kind: str, path: str | None = None,
    experiment_id: str | None = None, execution_id: str | None = None,
    description: str = "",
) -> dict[str, Any]:
    item = {
        "id": evidence_id, "kind": kind, "path": path, "experiment_id": experiment_id,
        "execution_id": execution_id, "description": description, "collected_at": _now(),
    }
    if path and Path(path).is_file():
        item["sha256"] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    append_event(root, "evidence_recorded", item)
    return item


def record_hypothesis(root: Path, hypothesis_id: str, statement: str, status: str = "proposed", based_on: list[str] | None = None) -> dict[str, Any]:
    item = {"id": hypothesis_id, "statement": statement, "status": status, "based_on": based_on or []}
    append_event(root, "hypothesis_recorded", item)
    return item


def record_finding(root: Path, finding_id: str, statement: str, evidence_ids: list[str] | None = None, confidence: str | None = None, semantic_tags: list[str] | None = None, techniques: list[str] | None = None, tactics: list[str] | None = None, controls: list[str] | None = None, references: list[str] | None = None, status: str = "observed") -> dict[str, Any]:
    item = {"id": finding_id, "statement": statement, "evidence_ids": evidence_ids or [], "confidence": confidence, "semantic_tags": semantic_tags or [], "techniques": techniques or [], "tactics": tactics or [], "controls": controls or [], "references": references or [], "status": status, "created_at": _now()}
    append_event(root, "finding_recorded", item)
    return item


def request_experiment(root: Path, request_id: str, objective: str, hypothesis_id: str | None = None, requested_capabilities: list[str] | None = None, evidence_required: list[str] | None = None, approval_required: bool = True) -> dict[str, Any]:
    item = {"id": request_id, "hypothesis_id": hypothesis_id, "objective": objective, "requested_capabilities": requested_capabilities or [], "evidence_required": evidence_required or [], "approval_required": approval_required, "status": "proposed"}
    append_event(root, "experiment_requested", item)
    return item


def record_reference(root: Path, reference: dict[str, Any]) -> dict[str, Any]:
    append_event(root, "research_reference_recorded", reference)
    return reference


def read_events(root: Path) -> list[dict[str, Any]]:
    path = root / "research-ledger.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evidence_context(root: Path, limit: int = 60) -> str:
    events = read_events(root)
    return json.dumps(events[-limit:], indent=2, sort_keys=True) if events else "No structured research state has been recorded yet."
