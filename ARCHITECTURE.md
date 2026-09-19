# Architecture Freeze

This document records the architectural boundary that future changes must preserve.

## Frozen rule

> **Decretum is a compiler/resolver, not a runtime.**

Decretum:

- defines and validates canonical capability semantics
- discovers execution surfaces
- resolves providers, integrations, profiles and harness compatibility
- applies policy
- compiles a portable ResearchExecutionContract
- records compile-time provenance and registry snapshots
- verifies contracts read-only

Decretum does **not**:

- start or operate an agent runtime
- provision research environments
- conduct researcher interaction
- execute experiments
- collect evidence
- develop findings
- generate reports
- own persistent research sessions
- own the research/evidence database

## Handoff

```
Recipe
  -> Decretum
  -> ResearchExecutionContract
  -> External Harness Runtime
  -> Research / Evidence Store
```

The contract is the interoperability boundary.

## Interactive loop

The runtime may request another experiment. If that request requires only capabilities already present in the contract, the runtime can continue according to its own execution model.

If the request requires a new capability, provider, integration, policy permission or changed execution requirement:

```
Harness Runtime
      |
      v
Experiment / capability request
      |
      v
Decretum
      |
      +-- validate
      +-- resolve
      +-- compile
      |
      v
New ResearchExecutionContract
      |
      v
Harness Runtime
```

The harness must not silently redefine Decretum's capability semantics.

## Research state

Evidence, findings, hypotheses, researcher interactions and reports belong to the runtime's research store.

Decretum may include evidence/report **requirements** in the contract, but it does not own the resulting state.

## Contribution guardrail

Any feature that executes research or owns the interactive research loop belongs outside the Decretum compiler core.

Contributors should extend:

- canonical capability semantics
- provider metadata
- integration metadata
- profiles
- discovery/readiness
- resolution
- policy
- contract format

Harness/runtime projects should implement:

- execution
- researcher UX
- evidence collection
- finding analysis
- reporting
- persistent research state

**This boundary is intentionally frozen.**
