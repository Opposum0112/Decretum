# Decretum

> **Decretum defines the security-research ontology and boundaries. Codex is the interactive researcher that selects, composes, orchestrates, and executes the declared skills.**

Decretum is a **LinkML-based security-research contract compiler**. It turns a declarative research recipe into a validated contract that Codex can investigate within.

**Local-first:** this branch does not provision hosted or cloud sandboxes.

```mermaid
flowchart LR
    A[Researcher] --> B[YAML Recipe]
    B --> C[Validate + Compile]
    C --> D[Research Contract]
    D --> E[Codex]
    E --> F[Local Compute + Tools]
    F --> G[Evidence]
    G --> H[Findings]
    H --> E
```

## The mental model

| Layer | Purpose |
| --- | --- |
| **Schema** | Defines the security-research vocabulary and capabilities |
| **Recipe** | Defines the boundary and requirements for one investigation |
| **Contract** | Freezes the validated research boundary |
| **Codex** | Selects, composes, orchestrates, and executes skills interactively |
| **Tools / MCP** | Implement authorized capabilities |
| **Evidence** | Records what was observed |
| **Findings** | Records what the research established |

> **Schema = what is possible · Recipe = what this investigation allows · Contract = frozen boundary · Codex = researcher**

## Quick start

### 1. Install

Requirements: **Python 3.11+**, **uv**, and OpenAI/Codex credentials.

```bash
git clone https://github.com/Opposum0112/Decretum.git
cd Decretum
uv sync
export OPENAI_API_KEY="..."
```

### 2. Validate a recipe

Validation checks the recipe without executing the workload.

```bash
decretum validate recipes/openai-hosted-malware-analysis.yaml
```

### 3. Resolve capability readiness

Before execution, inspect which registered providers, integrations, harnesses, and models can satisfy the recipe:

```bash
decretum resolve recipes/openai-hosted-malware-analysis.yaml
```

The resolver does **not** execute the research. It answers:

```text
Capability
   ↓
Provider candidates (MCP / API / tool)
   ↓
Integration / transport
   ↓
Harness
   ↓
LLM reasoning
   ↓
Prerequisite readiness
```

For tool providers, Decretum checks whether the required executable is discoverable on the local host. API/MCP entries are reported as registered endpoints; connection/credential checks remain an execution-time concern.

### 4. Compile the contract

```bash
decretum compile recipes/openai-hosted-malware-analysis.yaml
```

The compiler produces a machine-readable `research-contract.json` for the research session.

### 5. Run the research

```bash
decretum run recipes/openai-hosted-malware-analysis.yaml --dry-run=false
```

Codex investigates interactively within the compiled contract. It can inspect evidence, select and compose declared skills, use permitted instrumentation, form hypotheses, request experiments, and iterate with the researcher.

### 6. Continue the same research session

```bash
decretum analyze <research-id> "What evidence is still missing?"
decretum analyze <research-id> "Compare the observed process and network activity."
```

### 7. Inspect persisted state

```bash
decretum inspect <research-id>
```

## How research works

```mermaid
flowchart TD
    Q[Research question] --> R[Research recipe]
    R --> V[LinkML validation]
    V --> C[Contract compilation]
    C --> X[Codex]
    X --> S[Select / compose skills]
    S --> T[Run authorized tools]
    T --> E[Collect evidence]
    E --> A[Analyze evidence]
    A --> F[Hypothesis / finding]
    F --> D{More evidence needed?}
    D -- Yes --> X
    D -- No --> P[Report]
```

Decretum constrains the research space; **Codex explores that space**. If a capability is outside the contract, it must follow the configured approval or contract-amendment path rather than silently expanding access.

## Capability-provider validation

Every capability is required to have at least one registered implementation before a recipe can compile. The provider registry is transport-neutral and supports three provider interfaces:

```text
Capability
   |
   +-- MCP provider
   +-- API provider
   +-- Tool / CLI provider
```

The validator checks the declared capability catalog, skill and role capability references, and compute requirements against `schema/provider_registry.yaml`. A missing provider is a **compile-time error**, not a runtime warning. The registry also records available **integrations**, **agent harnesses**, and **LLM model families**. The resolver then reports candidate execution paths and local readiness without choosing an implementation permanently.

This keeps the boundaries explicit:

- **Schema** = capability boundary.
- **Recipe** = execution boundary.
- **Provider** = implementation mechanism.
- **Compiled contract** = frozen machine-readable research boundary.

Adding a new capability therefore follows:

```text
1. Add capability to the LinkML model
2. Register one or more MCP/API/tool providers
3. Register integrations that expose those providers when needed
4. Register compatible autonomous harnesses and model families
5. Validate and resolve readiness
6. Compile the research recipe
7. Hand the frozen contract to the autonomous agent
```

## Capability model

Capabilities are tool-independent. A recipe declares capabilities; concrete tools implement them.

```text
Role
  ↓
Skill
  ↓
Capability
  ↓
Tool / MCP
  ↓
Evidence
  ↓
Finding
```

Examples:

| Capability | Example implementations |
| --- | --- |
| `process.observe` | Sysdig, Falco, Tracee, Tetragon, bpftrace, BCC, strace, auditd |
| `network.capture` | tcpdump, tshark, Wireshark, Zeek, Suricata, Snort |
| `binary.analyze` | Ghidra, radare2, binwalk, readelf, objdump |
| `memory.analyze` | Volatility, Rekall |

Supported local compute vocabulary includes:

`Unix` · `Docker` · `Podman` · `Lima` · `Incus` · `LXC` · `KVM` · `Firecracker` · `QEMU`

## Autonomous research and learning

Decretum is the contract and capability boundary; the autonomous agent/harness is the researcher. A researcher can compose validated capabilities into comprehensive recipes and iterate through hypotheses, experiments, evidence, analysis, and findings. Required reports are preserved with the research state.

The capability catalog is intentionally extensible: new tools, APIs, MCP servers, integrations, harnesses, and model families can be registered without changing the meaning of an existing capability. This allows an implementation to evolve while recipes remain reusable.

## Capability evolution

A capability is added to Decretum through a governed lifecycle. Researchers do **not** need to bind a capability directly to one tool. The capability describes the stable research action; providers and integrations supply interchangeable implementations.

```mermaid
flowchart TD
    A[New research need] --> B[Define CapabilitySpec in LinkML schema]
    B --> C[Schema validation]
    C -->|Invalid| B
    C -->|Valid| D[Register MCP / API / Tool providers]
    D --> E[Register integrations]
    E --> F[Identify compatible harnesses]
    F --> G[Identify compatible LLM families]
    G --> H[Capability Resolver]
    H --> I{Readiness}
    I -->|Unavailable| D
    I -->|Ready| J[Capability becomes recipe-usable]
    J --> K[Compose Research Recipe]
    K --> L[Validate recipe]
    L --> M[Compile frozen ResearchContract]
    M --> N[Autonomous agent / harness]
    N --> O[Execute research]
    O --> P[Evidence]
    P --> Q[Finding + Report]
    Q --> R[Persistent Research Store]
    R --> S[Future research]
```

### Adding a capability

For example, a researcher needs cloud audit-log querying:

```yaml
capability_catalog:
  - id: cloud.audit.query
    name: Cloud Audit Query
    kind: cloud
    risk: read
    description: Query cloud audit records for security investigation
```

The implementation is then registered independently:

```text
cloud.audit.query
├── AWS CloudTrail API
├── Azure Monitor API
├── GCP Audit Logs API
└── Cloud Audit MCP
```

The resolver checks which registered implementations are usable in the current environment. A capability can have multiple providers:

```text
cloud.audit.query
├── cloudtrail-api     API    READY
├── azure-monitor      API    READY
├── gcp-audit-api      API    UNAVAILABLE
└── cloud-audit-mcp    MCP    READY
```

The capability is therefore the reusable semantic contract; the provider is an implementation choice. Adding another provider later does not require rewriting existing recipes.

### Capability evolution rules

1. **Define** the capability in the research schema.
2. **Validate** its identity, kind, risk and description.
3. **Implement** it through one or more MCP/API/tool providers.
4. **Register** integrations that expose those providers.
5. **Register or verify** compatible autonomous harnesses and LLM families.
6. **Resolve** provider candidates and local prerequisites.
7. **Use** the capability in recipes only after validation.
8. **Compile** recipes into frozen contracts.
9. **Execute** through the selected autonomous researcher.
10. **Persist** evidence, findings and reports so later research can build on the result.

This means the capability catalog can continuously grow while existing recipes remain stable:

```text
Stable capability semantics
          │
          ├── provider A
          ├── provider B
          ├── integration C
          └── integration D
                 ↓
        interchangeable execution
```

## Persistent research state

Each research ID keeps durable local artifacts such as:

```text
artifacts/<research-id>/
├── research-contract.json
├── research-session.sqlite3
├── research-ledger.jsonl
├── experiments/
├── evidence/
└── report/
```

The research ledger preserves evidence, hypotheses, findings, references, semantic tags, techniques, confidence, and provenance so follow-up analysis can continue from the existing research state.

## Architecture

```mermaid
flowchart TB
    subgraph EV[Capability Evolution]
      N[New research need] --> SC[LinkML CapabilitySpec]
      SC --> SV[Schema validation]
      SV --> PR[Provider registry]
      PR --> IR[Integration registry]
      IR --> HR[Harness registry]
      HR --> MR[Model registry]
      MR --> CR[Capability Resolver]
    end

    CR --> RR{READY?}
    RR -->|No| PR
    RR -->|Yes| RC[Research Recipe]
    RC --> RV[Recipe Validator]
    RV --> CC[Contract Compiler]
    CC --> CT[Frozen ResearchContract]
    CT --> AH[Autonomous Harness]
    AH --> EX[Research / Experiments]
    EX --> EV2[Evidence]
    EV2 --> FS[Findings + Report]
    FS --> PS[Persistent Research Store]
    PS --> AH
    PS --> CR
```

### Clear boundaries

- **Schema** defines reusable concepts, roles, skills, capabilities, evidence, and references.
- **Recipe** declares what one investigation is allowed to use.
- **Compiler** validates and freezes that declaration as a research contract.
- **Codex** decides how to investigate inside the contract.
- **Local compute and tools** perform the authorized work.
- **Research state** preserves the evidence and findings for continued investigation.

## References

Recipes can associate research with security frameworks, threat-intelligence sources, vendor advisories, vulnerability databases, research papers, incident reports, detection content, and standards.

Example:

```yaml
references:
  - id: ATTCK-T1071-004
    type: security_framework
    authority: mitre
    title: Application Layer Protocol: DNS
    citation: "ATT&CK T1071.004"
```

## Safety

Decretum is local-first. Unix execution uses host permissions and should not be treated as strong isolation. Use an appropriately isolated local environment for hostile workloads.

Recipes can explicitly deny privileged access, host filesystem writes, mounts, unrestricted network access, and cloud sandboxing.

## Contributing

Contributions are welcome in:

- **Recipes** — reusable security investigations under `recipes/`.
- **Schema** — roles, skills, capabilities, evidence, boundaries, and references.
- **Instrumentation** — mappings between capabilities and security tools.
- **Tests and documentation** — regression coverage and researcher guidance.

Before submitting recipe or schema changes:

```bash
decretum validate recipes/<topic>.yaml
decretum compile recipes/<topic>.yaml
uv run pytest
```

For bugs, include the command, minimal recipe, expected and actual behavior, error output, OS, Python version, and Decretum version or commit. Do not publish credentials or sensitive research artifacts in public issues.

## Repository layout

```text
schema/       LinkML ontology
recipes/      Research recipes
sec_agent/    Validator, compiler, Codex integration, research state
tests/        Regression tests
```

## Project status

The `refactor/openai-api` branch provides declarative research recipes, LinkML validation, deterministic contract compilation, reusable roles/skills/capabilities, local compute and instrumentation vocabulary, Codex research sessions, durable evidence and finding state, hypotheses, experiment requests, and security/threat-intelligence references.
