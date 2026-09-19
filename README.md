# Decretum

> **Describe the security research you want to perform. Decretum figures out what is available, builds a safe execution plan, and produces a reproducible research contract.**

Decretum is a **harness-neutral security research compiler**.

It lets a researcher describe an investigation as a portable YAML recipe instead of tying the recipe to one command, one MCP server, one agent, or one machine.

Decretum then:

- validates the research recipe
- discovers available execution surfaces
- maps capabilities to providers
- checks provider, policy, and harness compatibility
- selects providers and fallbacks
- freezes the plan into an auditable contract
- records evidence and provenance
- supports verification and offline replay

**Decretum is not another agent runtime.** Codex, Goose, Google ADK, Pi, or another compatible harness can execute the contract.

---

## Why use Decretum?

Without Decretum, a research workflow often becomes:

```text
Research idea
   ↓
Custom script
   ↓
Hard-coded tool
   ↓
Hard-coded agent
   ↓
Machine-specific setup
   ↓
Difficult to reproduce
```

With Decretum:

```text
Research question
   ↓
Portable recipe
   ↓
Capabilities
   ↓
Available providers
   ↓
Compatible execution surface
   ↓
Selected provider + fallback
   ↓
Execution contract
   ↓
Evidence + provenance
   ↓
Reproducible research
```

The important idea is simple:

> **Recipes describe what the researcher needs. Providers describe how that capability can be delivered.**

---

# 1. Quick start

## Step 1 — Install

Requirements:

- Python 3.11+
- uv
- the tools/harnesses you want to use

```bash
git clone https://github.com/Opposum0112/Decretum.git
cd Decretum
uv sync
```

---

## Step 2 — See what your machine can provide

Before creating a recipe, discover the execution surfaces available on your host:

```bash
decretum capabilities discover
```

Decretum checks registered:

- CLI/tool providers
- API integrations
- MCP surfaces
- supported agent harnesses
- local availability
- provider ↔ harness compatibility

It creates:

```text
artifacts/capability-discovery/
├── capability-surface-manifest.json
└── capability-candidates.yaml
```

The candidate file is created only when review is required.

Example:

```text
network.capture

  tshark
    tool
      Codex
      Goose
      ADK
      READY

  tcpdump
    tool
      Codex
      Goose
      READY

  pcap-mcp
    MCP
      registered
      not locally verified
```

**Discovery does not modify the canonical schema.**

---

# 2. Write a research recipe

Suppose you want to investigate whether a suspicious program creates unexpected network activity.

You describe the investigation, not the specific packet-capture program.

```yaml
id: suspicious-network-investigation
name: Suspicious Network Investigation
version: "1.0"
role: malware_researcher

objective: >
  Determine whether the sample creates unexpected network activity.

environment:
  type: local
  sandbox:
    backend: docker
    image: security-research/sample-lab:latest
  orchestration:
    executor: codex
    mode: interactive

capability_catalog:
  - id: process.observe
    name: Observe Processes
    kind: process
    risk: observe
    description: Observe process activity.

  - id: network.capture
    name: Capture Network Traffic
    kind: network
    risk: collect
    description: Capture traffic produced by the experiment.

skills:
  - id: observe-runtime
    kind: investigation
    capabilities:
      - process.observe
      - network.capture

experiments:
  - id: observe-process
    objective: Observe process activity.
    capabilities: [process.observe]
    outputs: [process_activity]

  - id: capture-network
    objective: Capture network activity.
    capabilities: [network.capture]
    depends_on: [observe-process]
    outputs: [network_activity]

policy:
  deny: [privileged]
  approval_required: []

evidence:
  required: true

completion:
  report: true
```

Notice what the recipe **does not** say:

```text
Run tshark
Run tcpdump
Start a particular MCP server
Use a particular LLM
Use a particular agent runtime
```

It asks for:

```text
process.observe
network.capture
```

That is what makes the recipe portable.

---

# 3. Validate the recipe

Run:

```bash
decretum validate recipes/suspicious-network-investigation.yaml
```

Validation checks the recipe structure and required provider registrations.

Nothing is executed.

Think of this as:

> **"Is my research request well formed?"**

---

# 4. Resolve the recipe

Run:

```bash
decretum resolve recipes/suspicious-network-investigation.yaml
```

The resolver checks:

```text
Recipe
  ↓
Required capabilities
  ↓
Registered providers
  ↓
Local readiness
  ↓
Execution surface
  ↓
Harness compatibility
  ↓
Policy compatibility
  ↓
Provider compatibility
```

For example:

```text
network.capture

  tshark
    provider: READY
    interface: tool
    harness: codex
    compatibility: PASS
    → SELECTED

  tcpdump
    provider: READY
    interface: tool
    harness: codex
    compatibility: PASS
    → FALLBACK

  pcap-mcp
    interface: mcp
    → NOT LOCALLY VERIFIED
```

Nothing is executed.

---

# 5. Compile the research contract

Run:

```bash
decretum compile recipes/suspicious-network-investigation.yaml
```

Decretum freezes the research plan into:

```text
artifacts/<research-id>/
├── research-contract.json
├── provider-registry.snapshot.json
└── compilation-manifest.json
```

The contract contains the resolved execution plan and records what Decretum intended to run.

The registry snapshot preserves the provider definitions used during compilation.

The compilation manifest records hashes of the important compilation inputs.

You can now review the plan **before execution**.

---

# 6. Execute with your chosen harness

When you are ready:

```bash
decretum run recipes/suspicious-network-investigation.yaml --dry-run=false
```

The execution harness performs the research within the compiled contract boundary.

Decretum does not try to replace the harness.

Conceptually:

```text
Decretum
   │
   │ execution contract
   ▼
Harness
   │
   ├── Codex
   ├── Goose
   ├── Google ADK
   ├── Pi
   └── other adapters
        │
        ▼
     Research
```

---

# 7. Collect and analyze evidence

After execution, continue the research session:

```bash
decretum analyze <research-id> "What evidence is still missing?"
```

Inspect generated research state:

```bash
decretum inspect <research-id>
```

A research artifact can contain:

```text
research-contract.json
research-session.sqlite3
research-ledger.jsonl
experiments/
evidence/
report/
```

---

# 8. Verify the research record

Verify the tamper-evident ledger:

```bash
decretum verify-ledger <research-id>
```

The ledger is hash chained so later changes can be detected.

This provides **tamper evidence**, not a claim of immutable storage or protection from a fully privileged attacker.

---

# 9. Replay the research plan

Run:

```bash
decretum replay artifacts/<research-id>/research-contract.json
```

Replay is read-only.

It does **not**:

- execute tools
- launch containers
- start VMs
- start MCP servers
- run agents

Instead it answers two different questions:

```text
Was the historical contract internally consistent?
                         +
Can the current environment reproduce the required surfaces?
```

---

# 10. Adding new capabilities

This is where Decretum becomes community extensible.

Suppose researchers need:

```text
cloud.audit.query
```

but that capability does not exist yet.

You can ask discovery to inspect a recipe containing it:

```bash
decretum capabilities discover --recipe recipes/cloud-investigation.yaml
```

Decretum can produce:

```text
CapabilityCandidate

cloud.audit.query
    status: review_required
    providers: none
```

It deliberately does **not** invent the security meaning of the capability.

The workflow is:

```text
DISCOVER
    ↓
PROPOSE
    ↓
DEFINE SEMANTICS
    ↓
VALIDATE
    ↓
APPROVE
    ↓
REGISTER PROVIDERS
    ↓
REGISTER INTEGRATIONS
    ↓
TEST
    ↓
COMPOSE INTO RECIPES
```

This distinction is important.

A locally installed executable is an **execution surface**.

It is not automatically a new security capability.

For example, discovering a binary named `cloud-audit-tool` does not prove what security semantics it provides.

A researcher must define the capability.

---

# 11. Capability vs provider vs integration vs harness

These four concepts should stay separate.

| Concept | Meaning | Example |
|---|---|---|
| Capability | What the researcher needs | `network.capture` |
| Provider | Concrete implementation | tshark |
| Integration | How the provider is reached | MCP/API/tool |
| Harness | Agent/orchestration runtime | Codex |

For example:

```text
network.capture
       │
       ├── tshark
       │     └── tool
       │
       ├── tcpdump
       │     └── tool
       │
       └── pcap-mcp
             └── MCP
```

A recipe composes **capabilities**.

The resolver chooses an appropriate **provider**.

The execution system uses an **integration**.

The selected **harness** performs the orchestration.

---

# 12. Build reusable research recipes

Once a capability is registered, recipes can compose it.

For example:

```text
Malware investigation
        │
        ├── artifact.read
        ├── process.observe
        ├── network.capture
        ├── filesystem.observe
        └── memory.analyze
```

Another recipe could reuse the same capabilities:

```text
Incident investigation
        │
        ├── process.observe
        ├── network.capture
        └── artifact.collect
```

The same capability can therefore participate in many investigations.

That is the foundation for a reusable security-research ecosystem.

---

# 13. Community contributions

Decretum is designed for researchers, detection engineers, threat researchers, security engineers, tool authors, and agent developers to contribute independently.

You can contribute:

- new capabilities
- provider implementations
- MCP integrations
- API integrations
- harness adapters
- reusable recipes
- tests
- documentation
- research workflows

## Contribution types

| You want to add... | Contribute... |
|---|---|
| A new research action | Capability |
| Another implementation | Provider |
| A new way to access it | Integration |
| A reusable investigation | Recipe |
| Agent execution support | Harness adapter |
| Better confidence | Tests/evidence |
| Better usability | Documentation |

---

## A. Add a capability

Add a capability when the **research action itself is new**.

Example:

```yaml
id: cloud.audit.query
name: Query Cloud Audit Logs
kind: cloud
risk: read
description: Query cloud audit records for security investigation.
allowed_networks: [restricted, internet]
allowed_execution_modes: [observe, collect]
evidence_outputs: [audit_events]
```

The important part is the semantic contract.

It should describe:

- what the capability means
- what it produces
- its risk
- allowed execution conditions
- compatibility expectations

Avoid making the capability name a product name when the behavior is portable.

Prefer:

```text
cloud.audit.query
```

over:

```text
aws.cloudtrail.query
```

when the underlying research action is the same.

---

## B. Add a provider

A provider implements an existing capability.

For example:

```text
cloud.audit.query
│
├── AWS CloudTrail API
├── Azure Monitor API
├── GCP Audit Logs API
└── Cloud Audit MCP
```

The provider should declare:

- capabilities
- interface
- integration
- readiness requirements
- execution modes
- isolation
- network requirements
- evidence outputs

Do not redefine the capability merely to make one provider fit.

---

## C. Add an integration

An integration describes how Decretum reaches a provider.

Examples:

```text
MCP
API
local CLI
container API
VM API
```

This allows the same semantic capability to be delivered through different execution surfaces.

---

## D. Add a recipe

A good recipe answers:

1. **What are we investigating?**
2. **Which capabilities are required?**
3. **What experiments are performed?**
4. **What depends on what?**
5. **What evidence is required?**
6. **What is denied or requires approval?**
7. **When is the research complete?**

Prefer:

```text
capability
    ↓
experiment
    ↓
evidence
```

instead of:

```text
recipe
    ↓
hard-coded command
    ↓
one specific machine
```

---

# 14. Recommended contribution workflow

### For a new capability

```text
Research need
     ↓
Search existing capabilities
     │
     ├── Exists → reuse it
     │
     └── Missing
           ↓
      Define CapabilitySpec
           ↓
      Define semantics
           ↓
      Add provider(s)
           ↓
      Add integration(s)
           ↓
      Add compatibility/readiness tests
           ↓
      Add example recipe
           ↓
      Validate
           ↓
      Resolve
           ↓
      Compile
           ↓
      Run tests
           ↓
      Pull request
```

### For a new provider

```text
Existing capability
       ↓
Implement provider
       ↓
Register interface
       ↓
Register integration
       ↓
Define readiness
       ↓
Define compatibility
       ↓
Add tests
       ↓
Example recipe
       ↓
Pull request
```

### For a new recipe

```text
Research question
       ↓
Select existing capabilities
       ↓
Create experiment DAG
       ↓
Define evidence
       ↓
Define policy
       ↓
Validate
       ↓
Resolve
       ↓
Compile
       ↓
Test
       ↓
Pull request
```

---

# 15. Before opening a PR

Run:

```bash
uv sync
uv run pytest
```

Then validate your example:

```bash
decretum capabilities discover
decretum validate recipes/<recipe>.yaml
decretum resolve recipes/<recipe>.yaml
decretum compile recipes/<recipe>.yaml
```

For a new capability, include:

- why an existing capability is insufficient
- semantic definition
- risk and execution constraints
- provider implementation(s)
- integration requirements
- compatibility/readiness tests
- example recipe

For a new recipe, include:

- research objective
- capabilities
- experiment dependencies
- evidence expectations
- policy boundaries
- example usage

Do not include:

- credentials
- API keys
- private customer data
- confidential reports
- sensitive research artifacts
- malware samples that should not be publicly distributed

---

# 16. Project structure

```text
Decretum/
│
├── schema/
│   ├── sec_research_metamodel.yaml
│   └── provider_registry.yaml
│
├── recipes/
│   └── reusable research recipes
│
├── sec_agent/
│   ├── validator.py
│   ├── capability_discovery.py
│   ├── resolver.py
│   ├── compatibility.py
│   ├── compiler.py
│   ├── research_state.py
│   └── replay.py
│
├── tests/
│
└── artifacts/
    └── generated research state
```

---

# 17. The complete researcher workflow

For a normal user, the whole project can be understood as:

```text
1. Discover
   ↓
2. Choose or create capabilities
   ↓
3. Write a recipe
   ↓
4. Validate
   ↓
5. Resolve
   ↓
6. Review the selected providers
   ↓
7. Compile
   ↓
8. Execute with your preferred harness
   ↓
9. Collect evidence
   ↓
10. Analyze findings
   ↓
11. Verify provenance
   ↓
12. Replay later
```

For contributors:

```text
Research problem
      ↓
Capability
      ↓
Provider
      ↓
Integration
      ↓
Execution surface
      ↓
Harness compatibility
      ↓
Recipe
      ↓
Reusable research workflow
```

---

# 18. Architecture at a glance

```text
                    RESEARCHER
                        │
                        ▼
                 Research Recipe
                        │
                        ▼
                  LinkML Schema
                        │
                        ▼
                 Capability Model
                        │
                        ▼
                Provider Registry
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
        Discovery              Integrations
             │                     │
             └──────────┬──────────┘
                        ▼
                  Host Readiness
                        │
                        ▼
                      Policy
                        │
                        ▼
                  Compatibility
                        │
                        ▼
                    Resolver
                        │
                        ▼
                  Execution Plan
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
        Plan Digest          Registry Snapshot
             │                     │
             └──────────┬──────────┘
                        ▼
              Compilation Manifest
                        │
                        ▼
            Research Execution Contract
                        │
                        ▼
                  Harness Adapter
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
           Codex      Goose       ADK
             │
             ▼
          Experiments
             │
             ▼
           Evidence
             │
             ▼
          Findings
             │
             ▼
      Hash-chained Ledger
             │
             ▼
       Offline Replay
```

---

# 19. Design principles

### Portable semantics

Capabilities describe research actions, not products.

### Harness neutrality

Decretum defines the contract; agent runtimes execute it.

### Discovery without ontology pollution

Host discovery can identify execution surfaces, but cannot silently invent canonical security semantics.

### Explicit approval

New capabilities become canonical through review rather than automatic mutation.

### Reproducibility

The execution plan, provider registry, compilation inputs, and provenance can be inspected later.

### Composability

Capabilities can be reused across many recipes and combined into larger investigations.

### Community extensibility

Researchers can contribute capabilities, providers, integrations, recipes, tests, and adapters independently.

---

## Status

Decretum is evolving toward a **community-extensible, harness-neutral security-research compiler**.

The core direction is:

```text
Portable security semantics
        +
Discoverable execution surfaces
        +
Composable research recipes
        +
Policy-aware provider resolution
        +
Harness-neutral execution contracts
        +
Persistent evidence and provenance
        =
Reproducible security research
```

The project deliberately does **not** try to replace agent runtimes such as Codex, Goose, Google ADK, or Pi.

**Decretum defines what the researcher wants done. The execution ecosystem determines how it is carried out.**
