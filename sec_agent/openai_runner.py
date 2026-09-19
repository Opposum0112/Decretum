"""Compatibility guard for the retired in-repository Codex executor.

Decretum no longer executes Codex or any other harness. Harness execution belongs
to an external runtime project.
"""

from __future__ import annotations


def create_session(*args, **kwargs):
    raise RuntimeError(
        "Decretum is compiler-only. Pass the ResearchExecutionContract to an "
        "external harness runtime; execution is intentionally not supported here."
    )


def save_session(*args, **kwargs):
    raise RuntimeError(
        "Decretum does not persist harness sessions. Use the external research store."
    )
