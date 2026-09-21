# Contributing to Decretum

Thank you for helping improve Decretum.

## Architecture

Decretum is a **domain-neutral declarative execution compiler**. It validates intent, resolves execution capabilities and produces an Execution Contract. It does not execute work or become an agent runtime.

Before contributing, read:

- [Introduction](INTRO.md)
- [Architecture](ARCHITECTURE.md)
- [Domain model](docs/domain-model.md)
- [Execution Contract](docs/execution-contract.md)

## Where changes belong

| Concern | Contribution |
|---|---|
| Semantic vocabulary | Schema / domain pack |
| Capability | Canonical capability definition |
| Provider | Concrete implementation metadata |
| Integration | Access surface |
| Profile | Reusable constraints/preferences |
| Discovery | Availability evidence |
| Resolver/compiler | Generic deterministic binding |
| Harness adapter | Contract handoff only |
| Runtime/store | External project |

**Do not add provider-specific or domain-specific branches to the core compiler.**

## Adding a capability

1. Describe the semantic need.
2. Check whether an existing capability already covers it.
3. Add or update the domain schema/capability definition.
4. Run discovery where appropriate.
5. Review the capability semantics explicitly.
6. Register provider implementations separately.
7. Add tests and documentation.
8. Update examples only after the capability is canonical.

Discovery may propose candidates; it must not silently change canonical semantics.

## Development

Requirements:

- Python 3.11+
- uv

    uv sync --group dev
    uv run pytest
    uv run ruff check .

Before opening a pull request:

- keep tests passing
- keep public documentation aligned with the implementation
- avoid generated artifacts in Git
- preserve deterministic compilation
- keep the runtime boundary intact

## Pull requests

Use a focused title and explain:

- what changed
- why it belongs in Decretum
- architectural impact
- tests performed
- documentation impact

Small, composable changes are easier to review.


## Contributing a Domain Pack

Domain-specific functionality should normally be contributed as an installable Domain Pack rather than by adding domain-specific conditionals to the Decretum core. A pack can contain schemas, capabilities, profiles, provider/integration metadata, recipes, examples and documentation. See [Domain Packs](docs/domain-packs.md). Validate locally with `decretum spec validate-pack ./my-pack` before opening a pull request.
