"""Contract handoff interfaces for external harness runtimes.

Adapters prepare a portable handoff envelope. They never execute work.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class HarnessAdapter(ABC):
    """Minimal adapter boundary for an external runtime."""

    id: str

    @abstractmethod
    def supports(self, contract: dict[str, Any]) -> bool:
        """Return whether the runtime can consume the contract."""

    @abstractmethod
    def prepare(self, contract: dict[str, Any]) -> dict[str, Any]:
        """Prepare a handoff envelope without executing the contract."""


class GenericHarnessAdapter(HarnessAdapter):
    id = "generic"

    def supports(self, contract: dict[str, Any]) -> bool:
        return (
            contract.get("kind") in {"ExecutionContract"}
            and contract.get("handoff", {}).get("target") == "external_harness_runtime"
        )

    def prepare(self, contract: dict[str, Any]) -> dict[str, Any]:
        if not self.supports(contract):
            raise ValueError("contract is not a valid external-runtime handoff")
        return {
            "protocol": "decretum.dev/v1",
            "type": "execution_handoff",
            "adapter": self.id,
            "contract_id": contract["contract_id"],
            "contract": contract,
            "execution": "external_harness_runtime",
            "decretum_action": "none_after_handoff",
        }
