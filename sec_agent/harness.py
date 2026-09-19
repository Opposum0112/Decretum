"""Contract handoff interfaces for external harness integrations.

These interfaces translate Decretum IR into a handoff envelope. They do not
execute agents, experiments or research sessions.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class HarnessAdapter(ABC):
    """Minimal handoff adapter implemented by an external-runtime integration."""

    id: str

    @abstractmethod
    def supports(self, contract: dict[str, Any]) -> bool:
        """Return whether the external runtime can consume the contract."""

    @abstractmethod
    def prepare(self, contract: dict[str, Any]) -> dict[str, Any]:
        """Translate the portable contract into a handoff envelope."""


class GenericHarnessAdapter(HarnessAdapter):
    id = "generic"

    def supports(self, contract: dict[str, Any]) -> bool:
        return (
            contract.get("kind") == "ResearchExecutionContract"
            and contract.get("handoff", {}).get("target") == "external_harness_runtime"
        )

    def prepare(self, contract: dict[str, Any]) -> dict[str, Any]:
        if not self.supports(contract):
            raise ValueError("contract is not a valid external-runtime handoff")
        return {
            "protocol": "decretum.dev/v1",
            "type": "research_execution_handoff",
            "adapter": self.id,
            "contract_id": contract["contract_id"],
            "contract": contract,
            "execution": "external_harness_runtime",
            "decretum_action": "none_after_handoff",
        }
