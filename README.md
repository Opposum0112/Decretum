# Decretum

**Decretum is a declarative local security-research contract compiler.**

You describe **what you want to investigate** in YAML. Decretum validates the recipe, compiles a deterministic research contract, and gives that contract to the **OpenAI Agents SDK** for model reasoning while experiments execute in a **local sandbox**.

There is **no cloud/hosted sandbox provisioning in this branch**.

## Architecture

```text
Researcher
   |
   v
YAML Research Recipe
   |
   v
LinkML-aligned validation
   |
   v
Decretum ResearchContract
   |
   v
OpenAI Agents SDK
   |
   +--> Local Unix sandbox
   |
   +--> Local Docker sandbox
   |
   +--> MCP / approved local tools
   |
   v
observe -> hypothesize -> experiment -> evidence -> report
```

The OpenAI API provides model reasoning. The local Agents SDK runtime owns sandbox execution. Commands and research artifacts do not need to be moved to a provider-managed execution environment.

## Local sandbox options

| Backend | Execution location | Isolation |
|---|---|---|
| `unix` | Local machine | Process-local SDK boundary; **not a strong security boundary on Linux** |
| `docker` | Local Docker daemon | Container boundary; preferred for untrusted workloads |

Cloud/hosted sandbox backends are intentionally not part of the Decretum contract model.

### Unix local

Use for trusted experiments or a machine that is already externally isolated.

```yaml
environment:
  type: local
  sandbox:
    backend: unix
    inherit_host_environment: false
  network:
    mode: none
```

On Linux, Unix-local execution must not be treated as equivalent to a VM or container security boundary.

### Docker local

Use a local Docker daemon when stronger workload isolation is required.

```yaml
environment:
  type: local
  sandbox:
    backend: docker
    image: python:3.14-slim
    inherit_host_environment: false
  network:
    mode: none
```

Inputs are staged into the sandbox through the Agents SDK manifest rather than by mounting the host filesystem into the research container.

## Quick start

Requires Python 3.11+, a local Docker installation for Docker experiments, and an OpenAI API key for model reasoning.

```bash
uv sync
export OPENAI_API_KEY="..."
```

For Docker support:

```bash
uv sync --extra docker
```

Validate:

```bash
decretum validate recipes/openai-hosted-malware-analysis.yaml
```

Compile without execution:

```bash
decretum compile recipes/openai-hosted-malware-analysis.yaml
```

Run the local experiment:

```bash
decretum run recipes/openai-hosted-malware-analysis.yaml --dry-run=false
```

Choose a model:

```bash
decretum run recipes/openai-hosted-malware-analysis.yaml --dry-run=false --model gpt-5.6
```

The CLI remains dry-run by default.

## Research contract

A recipe declares:

- research objective and role
- inputs and artifacts
- local sandbox backend
- network mode
- capabilities and policy
- evidence requirements
- completion criteria
- report formats

The agent is free to choose the investigation strategy, but it cannot silently change the declared execution boundary.

If it discovers that another capability is required, it must stop or request researcher approval/contract amendment rather than provisioning a cloud sandbox or bypassing policy.

## Example workflow

```text
Researcher
   |
   | "Investigate this sample"
   v
Decretum
   |
   | validate + compile
   v
OpenAI Agents SDK
   |
   | local Docker sandbox
   v
Codex/agent reasoning
   |
   +-- inspect input
   +-- run experiment
   +-- observe process/network activity
   +-- collect evidence
   +-- form next hypothesis
   |
   +-- needs new capability?
          |
          v
      Researcher approval
          |
          v
      amended contract
   |
   v
Evidence-backed report
```

## Safety model

Decretum rejects privileged execution and host filesystem mounts by default. Recipes can explicitly deny capabilities such as:

```yaml
policy:
  deny:
    - host.filesystem.write
    - host.mount
    - privileged.host_access
    - unrestricted.network
    - cloud.sandbox
```

The compiler never executes the workload. Execution is performed by the selected local Agents SDK sandbox.

For malware, exploit, or other hostile workload research, use Docker or a stronger externally isolated environment and apply appropriate authorization and containment controls. Unix-local execution should be reserved for trusted workloads.

## Repository layout

```text
schema/
  sec_research_metamodel.yaml

recipes/
  openai-hosted-malware-analysis.yaml   # legacy filename; recipe is local Docker

sec_agent/
  validator.py
  compiler.py
  openai_runner.py
  cli.py

tests/
  test_validator.py
```

## Design principles

1. **Local-first** — experiment execution stays on the researcher's machine.
2. **No cloud sandbox provisioning** — hosted execution is outside this architecture.
3. **Declarative over procedural** — recipes describe intent and boundaries.
4. **Contract over runtime** — Decretum owns the research contract; Agents SDK owns execution.
5. **Capability over tool** — capabilities remain abstract from concrete instruments.
6. **Human-in-the-loop** — researchers can approve capability changes.
7. **Reproducibility** — contracts and run metadata are persisted locally.
8. **Minimal runtime** — Decretum does not maintain its own sandbox, harness, or agent orchestration engine.

## Status

This branch is the **local-provider OpenAI Agents refactor**. The previous hosted-session implementation and custom Lima/Podman/Docker provider runtime are intentionally removed from the architecture.

The OpenAI Agents SDK is the execution adapter; Decretum remains the declarative security-research contract and control boundary.
