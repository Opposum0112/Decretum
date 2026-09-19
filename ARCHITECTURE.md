# Architecture Freeze

This document records the architectural boundary that future changes must preserve.

## Frozen rule

> **Decretum is a domain-neutral declarative execution compiler/resolver, not a runtime.**

Decretum:

- defines and validates canonical capability semantics
- loads domain schemas and registries
- discovers execution surfaces
- resolves providers, integrations, profiles and harness compatibility
- applies policy
- compiles a portable Execution Contract
- records compile-time provenance and registry snapshots
- verifies contracts read-only

Decretum does **not**:

- start or operate an agent runtime
- provision environments itself
- conduct researcher/agent interaction
- execute experiments or software tasks
- collect evidence as runtime state
- develop findings
- generate reports
- own persistent sessions or stores

## Domain neutrality

Security research is the current reference domain, not the compiler's architectural boundary.

The core compiler must not contain domain-specific execution branches. Domain-specific semantics belong in domain packs:

```
Core
  schema loading
  capability registry
  provider registry
  profiles
  discovery
  validation
  resolver
  policy
  compiler
       |
       +---- Security research pack
       +---- Software engineering pack
       +---- Infrastructure pack
       +---- Data/experiment pack
       +---- Future packs
```

A domain pack can add semantics without turning the core into a domain-specific workflow engine.

## Structured intent model

```
Schema
  |
  +--> defines semantic vocabulary

Recipe
  |
  +--> declares desired outcome/capabilities

Profile
  |
  +--> declares characteristics and preferences

Registry
  |
  +--> declares concrete providers/integrations/harness surfaces

Resolver
  |
  +--> binds intent to available execution surfaces

Compiler
  |
  +--> emits portable Execution Contract
```

The same recipe can be compiled against different profiles and provider availability without changing its semantic intent.

## Handoff

```
Recipe
  -> Decretum
  -> Execution Contract
  -> External Harness / Agent Runtime
  -> External Store
```

The contract is the interoperability boundary.

## Iterative execution loop

If the runtime can satisfy the next action with capabilities already present, it remains within its own execution model.

If it needs a new capability, provider, integration, policy permission or changed execution requirement:

```
Harness / Agent
      |
      v
Requirement change
      |
      v
Decretum
      |
      +-- validate
      +-- resolve
      +-- compile
      |
      v
New Execution Contract
      |
      v
Harness / Agent
```

The runtime must not silently redefine Decretum's capability semantics.

## Contract naming

The canonical conceptual contract is **Execution Contract**.

The current security-domain implementation may retain `ResearchExecutionContract` as a compatibility representation while the contract format evolves. New domain-neutral implementations should use a domain-neutral kind and carry explicit domain/intent metadata rather than encoding the domain into the compiler boundary.

## Contribution guardrail

Features that execute work or own an interactive loop belong outside the Decretum compiler core.

Contributors should extend:

- schemas and domain packs
- canonical capabilities
- provider/integration metadata
- profiles
- discovery/readiness
- resolution
- policy
- contract format

Harness/runtime projects should implement:

- execution
- researcher/agent UX
- orchestration
- evidence collection
- finding analysis
- reporting
- persistent state

**This boundary is intentionally frozen.**
