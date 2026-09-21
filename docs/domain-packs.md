# Decretum Domain Packs

Domain Packs are installable Python packages that extend Decretum without adding domain-specific logic to the core compiler.

## What a pack can contain

A Domain Pack may contribute:

- domain schemas and LinkML models
- canonical capabilities
- provider/integration metadata
- reusable infrastructure, instrumentation and harness profiles
- example recipes and Markdown specifications
- documentation and tests

The core compiler remains domain-neutral.

## Package contract

A package advertises a Python entry point:

```toml
[project.entry-points."decretum.domain_packs"]
my-domain = "my_decretum_pack:domain_pack"
```

The entry point returns a `DomainPack` manifest:

```yaml
apiVersion: decretum.dev/v1
kind: DomainPack
id: my-domain
name: My Domain
version: 1.0.0
domains:
  - my_domain
```

A pack should keep its content under a predictable layout:

```
my_decretum_pack/
├── domain-pack.yaml
├── schema/
├── capabilities/
├── profiles/
├── recipes/
└── docs/
```

## Contributor workflow

1. Create a standalone Python package.
2. Add `domain-pack.yaml`.
3. Add schemas, capabilities, profiles and recipes.
4. Validate the pack:
   ```bash
   decretum spec validate-pack ./my-pack
   ```
5. Install the package into a Decretum environment.
6. Discover installed packs:
   ```bash
   decretum spec packs
   ```
7. Submit the pack or integration through the normal review process.

## Important boundary

Installing a Domain Pack does not automatically execute its recipes or silently mutate the core canonical vocabulary. Pack content must pass the normal validation and review boundaries.

This enables a package ecosystem where contributors can add domains such as security research, cloud operations, software engineering, DFIR, malware analysis, OT/ICS, or other research domains without forking Decretum's compiler.
