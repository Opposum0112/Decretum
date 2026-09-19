<p align="center">
  <img src="docs/assets/decretum-logo.svg" alt="Decretum" width="680">
</p>

<p align="center">
  <strong>Declarative intent → deterministic execution contract → agent / harness</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="Apache 2.0"></a>
  <a href="https://github.com/Opposum0112/Decretum/actions/workflows/tests.yml"><img src="https://github.com/Opposum0112/Decretum/actions/workflows/tests.yml/badge.svg?branch=capability-compiler-evolution" alt="Tests"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/YAML-schema-CCB6FF.svg" alt="YAML schemas">
  <img src="https://img.shields.io/badge/LinkML-aligned-6B4FBB.svg" alt="LinkML aligned">
</p>

# Decretum

> **Decretum turns structured intent into a deterministic execution contract for agents and harnesses.**

Decretum is a **domain-neutral Declarative Execution Compiler**. It combines schemas, recipes, profiles, provider/integration registries, discovery, validation, policy, and deterministic resolution to produce a portable **Execution Contract**.

Security research is Decretum's reference domain, not its architectural boundary. The same compiler model can describe software engineering, infrastructure automation, data engineering, incident response, scientific experiments, and other reproducible technical work.

## Architecture

> **Decretum is not a runtime. It defines what can be executed and produces a portable execution contract. It does not execute work, manage agent/researcher interaction, collect evidence, maintain findings, or generate reports.**

After compilation, **Decretum stops**. The contract is passed to an external harness or agent runtime.

If execution later needs a new capability or changed requirement, the request returns to Decretum for validation, resolution, and recompilation.

## The model

```
Schema       = what exists / semantic boundaries
Recipe       = what should be done
Profile      = execution characteristics and preferences
Registry     = available implementations
Resolver     = deterministic capability binding
Compiler     = portable contract generation
Harness      = actual execution and interaction
Store        = persistent execution/research memory
```

The important separation is:

```
                    DECRETUM
          Declarative Execution Compiler
                       |
       +---------------+---------------+
       |               |               |
    Schema           Recipe          Profile
   "what"           "do"            "how"
       |               |               |
       +---------------+---------------+
                       |
                    Resolver
                       |
     capability + provider + integration
       + harness + readiness + policy
                       |
                       v
               Execution Contract
                       |
                       v
              External Harness/Agent
                       |
          +------------+------------+
          |            |            |
       execute      interact      persist
          |            |            |
          +------------+------------+
                       |
                    Store
```

## Domain packs

The compiler core is domain-neutral. Domain-specific semantics live in registries and schemas rather than compiler branches.

Examples:

- **Security research** — malware, network, forensics, detection and cloud investigation
- **Software engineering** — source changes, dependencies, tests, builds and containers
- **Infrastructure** — VM, container, network and deployment requirements
- **Data engineering** — datasets, transforms, validation and artifacts
- **Scientific/technical experiments** — instruments, observations, analysis and evidence

A domain pack contributes capabilities, schemas, recipes, profiles and provider metadata. It does not change the core resolver/compiler semantics.

## Why structured contracts instead of broad markdown specifications?

Markdown is excellent for explanation. It is not a deterministic execution interface.

Decretum separates:

```
human intent
    |
    v
structured schema + recipe + profile
    |
    v
validated resolution
    |
    v
portable execution contract
    |
    v
agent / harness execution
```

This gives agents a machine-readable boundary while keeping implementation choices outside the recipe.

## Example: software engineering

A software task can use the same compiler:

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

completion:
  required:
    - tests_pass
    - artifact_built
    - container_built
```

The same intent can be compiled against another preference set:

```yaml
profiles:
  infrastructure: isolated-dev-vm
  testing: pytest
  container: podman
  agent: enterprise-coding-agent
```

The recipe describes **intent**. The profile expresses **preferences**. The provider registry determines **what is actually available**.

## Security research reference example

```yaml
id: suspicious-network-investigation
name: Suspicious Network Investigation
version: "1.0"
role: threat_researcher
objective: Determine whether the sample creates unexpected network activity.

capabilities:
  - process.observe
  - network.capture
  - artifact.collect

infrastructure_profile: isolated-linux-vm
instrumentation_profile: linux-network-observation
harness_profile: interactive-research
```

The recipe does not contain Lima/Docker lifecycle, MCP implementation, agent prompts, or runtime-specific code.

## End-to-end workflow

1. Define structured intent.
2. Reference canonical capabilities.
3. Select profiles/preferences.
4. Validate the recipe.
5. Discover available execution surfaces.
6. Resolve capability → provider → integration → harness.
7. Check readiness and policy.
8. Compile the Execution Contract.
9. Hand the contract to the external harness.
10. The harness executes, interacts, and persists its state.
11. If requirements change, return to Decretum and compile a new contract.

**Decretum does not perform steps 9–10.**

### Capability evolution

```
DISCOVER
   |
PROPOSE
   |
SEMANTIC REVIEW
   |
APPROVE
   |
CANONICAL CAPABILITY
   |
PROVIDER IMPLEMENTATIONS
```

Discovery can propose a capability, but it cannot silently mutate canonical semantics.

## Quick start

```bash
git clone https://github.com/Opposum0112/Decretum.git
cd Decretum
uv sync
decretum capabilities discover
decretum validate recipes/<recipe>.yaml
decretum resolve recipes/<recipe>.yaml
decretum compile recipes/<recipe>.yaml
```

Nothing in Decretum's validate/resolve/compile path executes the work.

## Resolution chain

```
Capability
    |
Provider
    |
Integration
    |
Execution surface
    |
Harness compatibility
    |
Host/provider readiness
    |
Policy compatibility
    |
READY / BLOCKED
```

## Architecture boundary

Decretum deliberately does **not** become:

- an agent runtime
- a workflow engine
- a VM/container runtime
- an evidence database
- a finding engine
- a report generator
- a long-running researcher process
- a Codex/Goose/OpenCode replacement

Instead:

```
Decretum
  = declarative intent -> deterministic contract

Harness / Agent
  = interactive execution environment

Store
  = persistent execution or research memory
```

See [ARCHITECTURE.md](ARCHITECTURE.md), [docs/execution-contract.md](docs/execution-contract.md), and [docs/domain-model.md](docs/domain-model.md) for the detailed boundary.

## Documentation and project governance

- [Introduction](INTRO.md) — problem, positioning and workflow
- [Architecture](ARCHITECTURE.md) — system boundary and invariants
- [Execution Contract](docs/execution-contract.md) — interoperability specification
- [Domain model](docs/domain-model.md) — core concepts and domain packs
- [Contributing](CONTRIBUTING.md) — development and extension rules
- [Security](SECURITY.md) — vulnerability reporting
- [Changelog](CHANGELOG.md) — release history
- [License](LICENSE) — Apache 2.0

## Contribution guide

Contribute at the layer that owns the semantics:

- **Domain schema/capability** → stable meaning
- **Provider** → concrete implementation
- **Integration** → access surface
- **Profile** → reusable preference/constraint
- **Discovery** → availability evidence
- **Resolver/compiler** → generic binding and contract generation
- **Harness/runtime** → execution and interaction
- **Store** → persistent evidence, artifacts, findings or reports

Adding a provider should normally require registry work, not compiler branching.

For a new capability, explain its semantics and distinguish it from existing capabilities before requesting canonical approval.

## Project structure

```
Decretum/
├── schema/
│   ├── capability_registry.yaml
│   ├── provider_registry.yaml
│   ├── profile_registry.yaml
│   └── sec_research_metamodel.yaml   # reference security domain
├── recipes/
├── docs/
│   └── domain-model.md
├── sec_agent/
│   ├── capability_registry.py
│   ├── capability_discovery.py
│   ├── profile_registry.py
│   ├── resolver.py
│   ├── policy.py
│   ├── compiler.py
│   ├── harness.py
│   └── replay.py
└── tests/
```

## Architectural invariants

1. Decretum is a compiler/resolver, not a runtime.
2. Decretum stops after producing the execution contract.
3. The execution contract is the interoperability boundary.
4. Harnesses/agents own execution and interaction.
5. Persistent stores live outside Decretum.
6. New capability requirements return to Decretum for resolution and recompilation.
7. Canonical capability semantics are provider- and harness-independent.
8. Provider additions must not require compiler branching.
9. Discovery cannot silently mutate the canonical ontology.
10. Domain-specific behavior belongs in domain packs, not core compiler logic.
11. Replay/verification is read-only.
12. The compiler must remain deterministic for the same inputs and registry state.

> **Define in Decretum. Execute in the harness. Remember in the store.**

## Acknowledgements

Decretum is built on the work of the open-source community and the broader ecosystem of declarative schemas, interoperability tooling and agentic systems.

Special acknowledgement to the **LinkML community and contributors** for the schema and modeling ecosystem that informs Decretum's structured semantic approach.

Thank you to the maintainers, contributors and communities behind the open-source tools, standards and projects that make experimentation and interoperability possible.

## AI-assisted development and attribution

Decretum is developed with transparent AI assistance. **Vignesh Kumar** is the human project owner, architect, maintainer, and release authority. **ChatGPT (OpenAI)** is used as an AI engineering contributor for architecture exploration, implementation, refactoring, debugging, testing guidance, documentation, and repository maintenance.

AI assistance does not transfer project ownership or release authority to the AI system. Human review and acceptance remain part of the project workflow.

See [CONTRIBUTORS.md](CONTRIBUTORS.md) and [AI_ASSISTANCE.md](AI_ASSISTANCE.md) for the attribution policy and GitHub attribution details.

## Contact

For general project questions or bug reports, you may contact the maintainer at **maamtest18@gmail.com**. Please do not send passwords, API keys, credentials, private data, or undisclosed security vulnerabilities by email; use the security reporting process for vulnerabilities.

