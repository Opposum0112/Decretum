# Decretum — Introduction

## What Decretum is

Decretum is a **harness-neutral security research compiler**.

It translates research intent into a validated, portable execution contract.

> **Decretum defines what the researcher needs. The execution ecosystem determines how it is fulfilled.**

## What Decretum is not

Decretum is deliberately **not**:

- an agent runtime
- a researcher chat loop
- a VM/container runtime
- an evidence database
- a finding engine
- a report generator
- a replacement for Codex, Goose, OpenCode, ADK, or other harnesses

## The architecture

```
Research Recipe
      |
      v
    DECRETUM
      |
      +-- Capability semantics
      +-- Discovery
      +-- Profiles
      +-- Resolution
      +-- Policy
      +-- Compilation
      |
      v
Research Execution Contract
      |
      v
External Harness Runtime
      |
      +-- Interactive researcher
      +-- Experiments
      +-- Evidence
      +-- Findings
      +-- Report
      |
      v
Research / Evidence Store
```

### The important architecture rule

> **Decretum is responsible for determining what can be executed and producing a portable execution contract. It does not execute research, manage researcher interaction, collect evidence, maintain findings, or generate reports.**

After compilation, Decretum stops.

The contract is handed to a compatible harness runtime. The harness conducts the investigation and updates the research/evidence store.

If the researcher discovers that a new capability or changed requirement is needed, that request returns to Decretum. Decretum resolves it and produces a new contract.

## Why this boundary matters

This allows the same research definition to work with different execution ecosystems.

```
                SAME CONTRACT
                     |
        +------------+------------+
        |            |            |
      Codex        Goose       OpenCode
        |            |            |
        v            v            v
     Runtime      Runtime      Runtime
        |            |            |
     Research     Research     Research
```

Decretum remains stable while harnesses and research stores evolve independently.

## For researchers

1. Define the research objective.
2. Select canonical capabilities.
3. Select reusable profiles.
4. Validate and resolve.
5. Compile the contract.
6. Give the contract to your preferred harness runtime.
7. Conduct the interactive investigation there.
8. Preserve evidence and findings in the runtime's research store.
9. Return to Decretum only when the required capability/contract changes.

## For contributors

Contribute at the correct boundary:

- **Capability** → canonical semantic model
- **Provider** → implementation metadata
- **Integration** → access surface
- **Profile** → reusable execution preference
- **Discovery** → readiness/evidence
- **Compiler** → contract generation
- **Harness runtime** → execution and researcher interaction
- **Research store** → persistent evidence, findings and reports

See the README for the complete contribution workflow and frozen architectural invariants.
