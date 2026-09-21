# Domain Model

Decretum has a small domain-neutral core and extensible domain packs.

## Core

The core answers one question:

> Given structured intent and the available execution ecosystem, what deterministic execution contract can be produced?

| Concept | Meaning |
|---|---|
| Schema | Defines the semantic vocabulary |
| Capability | Atomic semantic requirement |
| Recipe | Declares the desired work |
| Profile | Reusable execution characteristics/preferences |
| Provider | Concrete capability implementation |
| Integration | Provider access surface |
| Harness | External execution/interaction runtime |
| Resolver | Deterministic binding |
| Compiler | Contract generation |
| Execution Contract | Portable handoff |
| Store | External persistent state |

## Domain packs

A domain pack is a collection of domain-specific semantics loaded by the same compiler model.

```
domains/
  security-research/
    schema/
    capabilities/
    profiles/
    recipes/

  software-engineering/
    schema/
    capabilities/
    profiles/
    recipes/
```

Each domain pack is independently versioned and installable. The core schema directory contains only domain-neutral artifact schemas; domain capability/provider/profile registries live inside their respective packs.

## Recipe vs profile

A recipe answers:

> What should be done?

A profile answers:

> What characteristics or preferences should constrain execution?

```yaml
recipe:
  capabilities:
    - network.capture
    - artifact.collect

profiles:
  infrastructure: isolated-linux-vm
  instrumentation: linux-network-observation
  harness: interactive-research
```

Changing Lima to Incus is a profile/provider decision, not a semantic recipe change.

## Provider vs capability

A capability is semantic:

```
network.capture
```

Providers are implementations:

```
tcpdump
tshark
pcap-mcp
zeek
```

Adding a provider should not require changing compiler semantics.

## Execution Contract

The contract is the stable boundary between Decretum and an external runtime. It should carry enough information for the runtime to understand requirements, resolved providers/integrations, profiles, policy, readiness and constraints.

It should not embed the runtime's implementation.

## Software engineering example

A future software-engineering domain pack could define:

```
source.read
source.modify
dependency.install
test.execute
artifact.build
container.build
```

and recipes such as:

```yaml
kind: ExecutionRecipe
domain: software_engineering
objective: Build and validate a Python service
capabilities:
  - source.read
  - source.modify
  - dependency.install
  - test.execute
  - container.build
profiles:
  language: python
  testing: pytest
  container: docker
```

These are illustrative domain-pack semantics. They should be promoted into a canonical registry before becoming executable recipes.

## Security research reference domain

The current canonical capabilities demonstrate the model with process observation, network capture, artifact collection, VM/container execution, kernel tracing, memory analysis, malware analysis and binary analysis.

They do not define Decretum's architectural scope.

## Runtime boundary

The harness/agent owns execution, interaction, orchestration, evidence/artifact collection, findings/reporting where applicable, and persistent session state.

Decretum owns semantics, validation, resolution, policy and compilation.

> **Define in Decretum. Execute in the harness. Remember in the store.**
