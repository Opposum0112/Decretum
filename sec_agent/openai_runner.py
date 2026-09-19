"""DEPRECATED runtime adapter placeholder.

Decretum no longer executes Codex or any other harness. Harness execution belongs
to an external runtime project. This module remains only as a migration guard.
"""

from __future__ import annotations


def create_session(*args, **kwargs):
    raise RuntimeError(
        "Decretum is compiler-only. Pass the ResearchExecutionContract to an external " 
        "harness runtime; execution is intentionally not supported here."
    )


def save_session(*args, **kwargs):
    raise RuntimeError(
        "Decretum does not persist harness sessions. Use the external research store."
    )
