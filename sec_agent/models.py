"""Pydantic v2 runtime representation of the core recipe contract."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Role = Literal["threat_researcher", "supply_chain_auditor", "detection_engineer", "vulnerability_exploit_researcher"]
Provider = Literal["lima", "podman", "docker"]
Harness = Literal["goose", "pi", "headless"]
Tool = Literal["tetragon", "bpftrace", "strace", "tcpdump", "tshark"]

class ComputeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Provider
    base_image: str
    cpus: int = Field(ge=1)
    memory: str
    network: str | None = None
    allow_host_mounts: Literal[False] = False

class InstrumentationSpec(BaseModel):
    tools: list[Tool] = Field(default_factory=list)
    trace_flags: list[str] = Field(default_factory=list)

class EvidenceSpec(BaseModel):
    artifact_paths: list[str] = Field(min_length=1)
    hash_algorithm: Literal["sha256"] = "sha256"
    manifest: bool = True

class WorkloadSpec(BaseModel):
    command: str
    timeout_seconds: int = Field(default=300, ge=1)

class ReportSpec(BaseModel):
    kind: str
    template: str

class ResearchRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    version: str
    role: Role
    objective: str
    harness: Harness
    compute: ComputeSpec
    instrumentation: InstrumentationSpec | None = None
    evidence: EvidenceSpec
    references: list[str] = Field(default_factory=list)
    workload: WorkloadSpec
    reports: list[ReportSpec] = Field(default_factory=list)
