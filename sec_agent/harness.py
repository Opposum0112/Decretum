"""Harness-neutral execution contract adapter interfaces.

Decretum does not implement agent runtimes. Adapters translate the portable
ResearchExecutionContract into the native contract expected by a harness.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class HarnessAdapter(ABC):
    """Minimal contract implemented by an execution-harness integration."""

    id: str

    @abstractmethod
    def supports(self, contract: dict[str, Any]) -> bool:
        """Return whether this adapter can execute the contract."""

    @abstractmethod
    def prepare(self, contract: dict[str, Any]) -> dict[str, Any]:
        """Translate Decretum IR into the harness-native execution request."""


class GenericHarnessAdapter(HarnessAdapter):
    """Reference adapter useful for integrations and contract testing."""

    id = "generic"

    def supports(self, contract: dict[str, Any]) -> bool:
        resolution = contract.get("resolution", {})
        return bool(resolution.get("bindings"))

    def prepare(self, contract: dict[str, Any]) -> dict[str, Any]:
        if not self.supports(contract):
            raise ValueError("contract has no compatible resolved execution bindings")
        return {
            "contract_id": contract["contract_id"],
            "research": contract["research"],
            "environment": contract["environment"],
            "experiment_graph": contract["experiment_graph"],
            "bindings": contract["resolution"]["bindings"],
            "policy": contract["policy"],
        }
