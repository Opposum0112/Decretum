# Decretum — Introduction

## What Decretum is

Decretum is a **domain-neutral Declarative Execution Compiler for Agents and Harnesses**.

It translates structured intent into a validated, portable execution contract.

> **Decretum defines what needs to happen. The execution ecosystem determines how it is fulfilled.**

Security research is the reference domain today, but it is not the architectural boundary.

## What problem does Decretum solve?

Open knowledge frameworks, specifications, ontologies, and Markdown-based instructions are good at describing **what something means** or **what should be done**. Agent runtimes are good at reasoning and carrying out work. The gap is the deterministic execution structure between them.

Without that layer, an agent may have to infer:

- which capabilities are actually required
- which providers implement those capabilities
- which integration exposes each provider
- which harness can execute them
- whether prerequisites are available
- which policies and constraints apply
- what execution contract should be handed to the runtime

Decretum provides that missing compilation layer:

```
Knowledge / Specification
          |
          v
   Structured Intent
          |
          v
       DECRETUM
          |
   schema + recipe + profile
          |
      resolution
          |
 capability + provider + integration
       + harness + readiness + policy
          |
          v
 Deterministic Execution Contract
          |
          v
    Agent / Harness Runtime
          |
          v
 Interactive Execution
```

This creates a deliberate separation:

- **Knowledge/specification frameworks** define meaning and intent.
- **Decretum** determines how that intent can be deterministically fulfilled in the available execution ecosystem.
- **Agents/harnesses** perform reasoning, interaction, adaptation, and execution.
- **External stores** retain evidence, artifacts, findings, or other persistent state.

Decretum therefore does **not** attempt to make the agent's reasoning deterministic. It makes the **execution substrate and handoff deterministic**.

> **Decretum bridges declarative specifications and agentic execution by compiling structured intent into deterministic, capability-resolved execution contracts.**

This allows the same semantic intent to be executed through different providers, integrations, profiles, and agent runtimes without embedding those implementation choices into the specification itself.


## The core abstraction

```
Schema   -> what exists / semantic boundary
Recipe   -> what should be done
Profile  -> how / constraints / preferences
Registry -> what implementations are available
Resolver -> deterministic binding
Compiler -> Execution Contract
Harness  -> actual execution and interaction
Store    -> persistent state
```

This lets the same compiler model support security research, software engineering, infrastructure, data engineering, incident response, scientific experiments, and other reproducible technical workflows.

## The important architecture rule

> **Decretum is responsible for determining what can be executed and producing a portable execution contract. It does not execute work, manage researcher/agent interaction, collect evidence, maintain findings, or generate reports.**

After compilation, Decretum stops.

```
Structured Intent
      |
      v
   DECRETUM
      |
      +-- schema/capabilities
      +-- profiles
      +-- provider registry
      +-- discovery
      +-- validation
      +-- resolution
      +-- policy
      +-- compilation
      |
      v
Execution Contract
      |
      v
External Harness / Agent Runtime
      |
      +-- execution
      +-- interaction
      +-- orchestration
      +-- evidence/artifacts
      +-- findings/reports where applicable
      |
      v
External Store
```

If execution requires a new capability or changed requirement, the request returns to Decretum for resolution and a new contract.

## Domain packs

Domain semantics should be implemented as **domain packs** rather than hard-coded into the compiler.

A domain pack may contribute:

- canonical capabilities
- domain schemas
- recipes
- profiles
- provider registrations
- validation rules appropriate to that domain

The core resolver/compiler should not contain branches such as "if security" or "if software engineering".

## Example: software engineering

```yaml
apiVersion: decretum.dev/v1
kind: ExecutionRecipe
domain: software_engineering
id: build-user-service
name: Build User Service
version: "1.0"
objective: Build and validate a Python service.

capabilities:
  - source.read
  - source.modify
  - dependency.install
  - test.execute
  - artifact.build
  - container.build

profiles:
  infrastructure: local-dev
  language: python
  testing: pytest
  container: docker
  agent: coding-agent
```

Another organization can keep the same intent while changing preferences:

```yaml
profiles:
  infrastructure: isolated-dev-vm
  testing: pytest
  container: podman
  agent: enterprise-coding-agent
```

The recipe remains semantic; profiles and registries determine the concrete execution contract.

## Security research reference workflow

1. Define the research objective.
2. Select canonical capabilities.
3. Select infrastructure/instrumentation/harness profiles.
4. Validate the recipe.
5. Discover execution surfaces.
6. Resolve capability → provider → integration → harness.
7. Check readiness and policy.
8. Compile the contract.
9. Hand the contract to the external harness.
10. The harness conducts the investigation and persists results in its own store.
11. Return to Decretum if requirements change.

Decretum performs steps 1–8 only.

## Why structured contracts?

Markdown remains useful for humans, documentation and rationale. It is not sufficient as the deterministic execution boundary.

Decretum makes the execution interface explicit:

```
human intent
    |
structured schema + recipe + profile
    |
validated resolution
    |
Execution Contract
    |
agent / harness
```

## What Decretum is not

- an agent runtime
- a workflow engine
- a VM/container runtime
- an evidence database
- a finding engine
- a report generator
- a replacement for Codex, Goose, OpenCode, ADK or other harnesses

## For contributors

Extend the layer that owns the concern:

- **Capability/schema** → semantic meaning
- **Provider** → implementation
- **Integration** → access surface
- **Profile** → reusable constraints/preferences
- **Discovery** → availability evidence
- **Resolver/compiler** → generic deterministic binding
- **Harness** → execution and interaction
- **Store** → persistent state

For new capabilities, start with semantics rather than a provider-specific tool name. Discovery may propose candidates, but canonical ontology changes require explicit promotion.

See [ARCHITECTURE.md](ARCHITECTURE.md), [README.md](README.md), and [docs/domain-model.md](docs/domain-model.md).
