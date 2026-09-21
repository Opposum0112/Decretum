# Markdown Spec Compiler

Decretum accepts a human-friendly `spec.md` as an authoring format and compiles it into a structured `ExecutionRecipe`.

```
spec.md
  ↓
Spec Compiler
  ↓
ExecutionRecipe
  ↓
Schema validation
  ↓
Capability resolution
  ↓
Recipe
  ↓
Execution Contract
```

The Markdown frontend is deterministic and does not call an LLM. It only extracts explicit sections and never silently invents executable capabilities.

## Supported sections

- `Domain`
- `Objective`
- `Capabilities`
- `Inputs`
- `Outputs`
- `Profiles`
- `Policy`
- `Evidence`
- `Completion`
- `Role`
- `Experiments`

Capabilities remain references to Decretum's canonical capability registry.

## CLI

```bash
decretum spec compile spec.md --output recipe.yaml
decretum validate recipe.yaml
decretum resolve recipe.yaml
decretum compile recipe.yaml
```

The resulting Execution Contract is the handoff boundary to the external harness. A new capability or changed requirement returns to Decretum for recompilation.
