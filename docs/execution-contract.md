# Execution Contract

The **Execution Contract** is Decretum's interoperability boundary.

It is the deterministic artifact handed from Decretum to an external agent or harness runtime.

## Purpose

A contract records the execution decision made by the compiler from:

- structured intent
- canonical capabilities
- profiles and preferences
- provider and integration registries
- harness compatibility
- readiness
- policy
- compile-time provenance

The runtime consumes the contract. It does not redefine its semantics.

## Contract flow

    spec.md (optional)
                  |
                  v
              ExecutionRecipe
                  |
                  v
        Recipe + Profile + Registry State
                  |
                  v
              Decretum
                  |
          validate / resolve
                  |
                  v
        Deterministic Contract
                  |
                  v
          Agent / Harness
                  |
                  v
              Execution

## Required properties

A conforming contract should provide:

1. **Explicit intent** — what outcome is requested.
2. **Resolved capabilities** — semantic requirements are explicit.
3. **Recipe provenance** — the source Recipe and, when applicable, the originating `spec.md` digest are identifiable.
4. **Concrete execution surfaces** — provider, integration and harness choices are recorded.
5. **Readiness information** — unavailable prerequisites are visible.
6. **Policy information** — relevant constraints and approvals are preserved.
7. **Provenance** — registry and compilation inputs can be audited.
8. **Deterministic identity** — equivalent inputs and registry state produce the same contract identity.
9. **Runtime handoff** — the contract clearly states that execution belongs to an external runtime.

## Immutability boundary

The external runtime may adapt its internal implementation, but it must not silently change the contract's semantic requirements.

If execution needs a new capability, provider, integration, permission or changed requirement:

    Runtime
      -> requirement change
      -> Decretum
      -> validate / resolve / compile
      -> new Execution Contract

## What the contract is not

It is not:

- an agent prompt
- a workflow engine
- a VM definition
- a research database
- a findings/report database
- an execution log

Those concerns belong to the consuming runtime and its external stores.

## Versioning

Contracts carry an apiVersion, kind, and contract_version.

The canonical conceptual kind is:

    apiVersion: decretum.dev/v1
    kind: ExecutionContract

The current security reference implementation may expose compatibility metadata for the historical ResearchExecutionContract representation. New domain-neutral contracts should use ExecutionContract.
