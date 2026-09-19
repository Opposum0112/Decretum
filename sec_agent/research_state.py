"""Compatibility boundary for legacy runtime-state imports.

Decretum does not own persistent research state. External harness runtimes and
their research stores own sessions, evidence, findings and reports.
"""

from __future__ import annotations


def _removed(*args, **kwargs):
    raise RuntimeError(
        "Research sessions, evidence, findings and reports are outside Decretum. "
        "Use the external harness research store."
    )


append_event = _removed
record_execution = _removed
record_execution_result = _removed
record_evidence = _removed
record_hypothesis = _removed
record_finding = _removed
request_experiment = _removed
record_reference = _removed
read_events = _removed
evidence_context = _removed


def verify_ledger(root):
    """Legacy compatibility shim; verification belongs to the external store."""
    return {
        "valid": False,
        "events": 0,
        "errors": ["research ledger is owned by the external runtime"],
    }
