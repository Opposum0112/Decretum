# Decretum

**Decretum is a declarative security-research contract compiler.**

You describe **what you want to investigate** in a small YAML recipe. Decretum validates that recipe against a LinkML metamodel, compiles it into a machine-readable research contract, and hands that contract to the **OpenAI Agents API / Codex** for interactive investigation.

Decretum intentionally does **not** try to be another agent runtime, workflow engine, sandbox manager, or harness dispatcher.

## What Decretum does

1. **Researcher writes a recipe** — objective, inputs, environment, policy, evidence and completion criteria.
2. **LinkML validates the shape** — required fields and allowed values are checked.
3. **Decretum compiles the recipe** — producing a deterministic ResearchContract.
4. **OpenAI runs the research session** — the agent decides how to investigate using the permitted environment, tools and MCP capabilities.
5. **Researcher stays in the loop** — the agent can explain findings and request clarification or an explicit contract change when it needs something outside the contract.
6. **Evidence and report become research artifacts** — the compiled contract remains the local source of truth for what was authorized.

### The boundary

| Component | Responsibility |
|---|---|
| **Researcher** | Defines the research question, inputs and acceptable boundaries |
| **Decretum** | Validates and compiles the declarative research contract |
| **OpenAI Agents API / Codex** | Plans and performs the investigation interactively |
| **Sandbox / environment** | Provides the execution boundary |
| **MCP / tools** | Provide specialized research instruments |
| **Evidence store** | Records what actually happened |

> **Decretum defines what is allowed and what must be proven. Codex determines how to investigate.**

## Quick start

### 1. Install

Requires Python 3.11+ and an OpenAI API key.

    uv sync
    export OPENAI_API_KEY="..."

### 2. Validate a recipe

    decretum validate recipes/openai-hosted-malware-analysis.yaml

### 3. Compile without executing anything

    decretum compile recipes/openai-hosted-malware-analysis.yaml

This writes:

    artifacts/malware-analysis-001/research-contract.json

### 4. Start an OpenAI research session

The CLI is deliberately dry-run by default:

    decretum run recipes/openai-hosted-malware-analysis.yaml

To create the OpenAI session:

    decretum run recipes/openai-hosted-malware-analysis.yaml --dry-run=false

Optionally choose the model:

    decretum run recipes/openai-hosted-malware-analysis.yaml --dry-run=false --model gpt-5.6

The session metadata is persisted under the research artifact directory.

> **Note:** OpenAI API/session capabilities evolve. The adapter in sec_agent/openai_runner.py is intentionally isolated so the declarative schema and compiler do not depend on a particular SDK session implementation.

## Writing a recipe

A recipe should answer five questions:

- **What are we trying to learn?**
- **What inputs should the agent investigate?**
- **Where may it execute?**
- **What capabilities are allowed or denied?**
- **What evidence and completion conditions are required?**

Example:

    apiVersion: decretum.dev/v1
    kind: ResearchExperiment
    id: weblogic-deserialization
    name: WebLogic deserialization investigation
    version: "1.0"
    role: vulnerability_exploit_researcher

    objective: >
      Determine whether the supplied WebLogic workload exhibits
      Java deserialization behavior and produce evidence-backed findings.

    inputs:
      workload: ./samples/weblogic.tar.gz

    environment:
      type: openai_hosted
      network:
        mode: none
      privileged: false
      host_mounts: false
      programmatic_tool_calling: true

    policy:
      allow:
        - artifact.read
        - artifact.collect
        - process.execute
        - process.observe
        - network.observe
      deny:
        - host.filesystem.write
        - host.mount
        - privileged.host_access
        - unrestricted.network
      approval_required:
        - network.enable
        - new_capability

    evidence:
      required:
        - process_activity
        - network_activity
        - filesystem_changes
        - exploit_indicators

    completion:
      report_required: true
      conclusion_required: true

Notice that the recipe does **not** prescribe a long sequence of agent steps. It states the research intent, boundaries and proof requirements. The agent can choose experiments within those boundaries.

## Capability model

Capabilities are intentionally abstract.

- network.capture describes the research capability.
- tcpdump, eBPF, a provider-native capture facility or another approved instrument can implement it.
- The agent must not silently substitute a capability that is absent from the contract.

Decretum derives an initial capability envelope from the recipe and preserves explicit policy.

    {
      "capabilities": {
        "required": ["artifact.read", "artifact.collect", "process.execute", "process.observe"],
        "optional": [],
        "denied": ["host.filesystem.write", "host.mount", "privileged.host_access", "unrestricted.network"]
      }
    }

A future environment/provider adapter can advertise which concrete implementations satisfy these capabilities. That resolution is deliberately outside the core recipe compiler.

## Interactive research workflow

    Researcher
       |
       | YAML recipe
       v
    Decretum / LinkML
       |
       | validated ResearchContract
       v
    OpenAI Agents API / Codex
       |
       +--> sandbox
       +--> MCP
       +--> approved tools
       |
       v
    observe -> hypothesize -> experiment -> collect evidence
       |
       +---- need clarification/approval? ----> Researcher
       |
       v
    completion criteria satisfied
       |
       v
    evidence-backed report

A research session can therefore look like:

    Researcher: Investigate this sample.

    Codex: I observed process X and indicator Y.
           I need network capture to test hypothesis Z.

    Researcher: Continue.

    Codex: Runs the permitted experiment, compares evidence,
           explains the result, and updates the research conclusion.

    Codex: The required evidence is complete. Here is the report.

## Repository layout

    schema/
      sec_research_metamodel.yaml    # LinkML source of truth

    recipes/
      openai-hosted-malware-analysis.yaml

    sec_agent/
      validator.py                    # Recipe validation
      compiler.py                     # Recipe -> ResearchContract
      openai_runner.py                # OpenAI session adapter
      cli.py                          # End-user CLI

    tests/
      test_validator.py

## Research artifacts

Each run can preserve:

    artifacts/<research-id>/
      research-contract.json
      openai-session.json
      evidence/
      report/

The **research contract** is the durable local record of the requested research semantics. The OpenAI session is the live execution context.

## Safety model

Decretum treats the YAML contract as a policy boundary:

- privileged execution is rejected by default;
- host filesystem mounts are rejected;
- denied capabilities are explicit;
- new capabilities can require researcher approval;
- the compiler never executes a workload;
- the default CLI mode creates no OpenAI session;
- execution belongs to the configured agent environment, not the Decretum host process.

For real malware or exploit research, use an appropriately isolated environment and follow your organization's authorization and containment requirements.

## Development

    uv sync
    uv run pytest
    uv run decretum validate recipes/openai-hosted-malware-analysis.yaml
    uv run decretum compile recipes/openai-hosted-malware-analysis.yaml

## Design principles

1. **Declarative over procedural** — recipes describe research intent, not agent choreography.
2. **Contract over runtime** — Decretum owns the research contract; the agent runtime owns execution.
3. **Capability over tool** — contracts request capabilities rather than hard-coding implementation details.
4. **Human-in-the-loop** — researchers can clarify, approve and redirect the investigation.
5. **Reproducibility** — compiled contracts are deterministic and persisted as research artifacts.
6. **Provider isolation** — OpenAI-specific session logic is an adapter, not part of the domain model.

## Status

This branch is the **OpenAI API refactor** of Decretum. The former Lima/Podman/Docker provider and Goose/Pi/headless dispatcher code is intentionally removed from the core architecture. Those concerns can be implemented as future environment/tool adapters without reintroducing a custom Decretum runtime.