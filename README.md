# Decretum

> **Define the security research you need. Decretum discovers execution surfaces, resolves capabilities, and compiles a portable contract for a harness to execute.**

Decretum is a **harness-neutral security research compiler**.

Its core rule is:

> **LinkML defines what a researcher needs. Discovery determines what can provide it. The compiler turns the request into a contract. The harness determines how it is executed.**

Decretum is not another agent runtime. Codex, Goose, Google ADK, Pi, or another compatible harness can execute the contract.

## Architecture

```
                 RESEARCHER
                     |
                 Recipe
                     |
             Capability Schema
                     |
          +----------+----------+
          |                     |
      Registry              Discovery
          |                     |
          +----------+----------+
                     |
                  Resolver
                     |
                  Compiler
                     |
          Research Execution Contract
                     |
                Harness Adapter
                     |
       +-------------+-------------+
       |             |             |
   Provision      Execute      Orchestrate
       |             |             |
       +-------------+-------------+
                     |
          Evidence / Findings / Report
                     |
              Research Store
```

### The six core pieces

| Component | Responsibility |
|---|---|
| **Capability schema** | Canonical semantic boundary |
| **Provider registry** | Concrete implementations and execution surfaces |
| **Discovery** | Verifies what is available and proposes missing capabilities |
| **Resolver/compiler** | Resolves capabilities and creates the execution contract |
| **Harness adapter** | Provisions, implements, executes, orchestrates and interacts with the researcher |
| **Research store** | Persists contracts, evidence, findings, reports and provenance |

The important separation is:

```
Capability = what
Provider   = implementation
Integration = access surface
Harness    = execution/orchestration
```

---

# Quick start

## 1. Install

```bash
git clone https://github.com/Opposum0112/Decretum.git
cd Decretum
uv sync
```

## 2. Discover the host

```bash
decretum capabilities discover
```

Discovery checks registered tools, APIs, MCP surfaces, integrations and harness availability.

It produces:

```
artifacts/capability-discovery/
├── capability-surface-manifest.json
└── capability-candidates.yaml
```

Discovery **never silently changes the canonical capability vocabulary**.

---

# Write a recipe

Recipes should stay small. They describe the research objective and compose canonical capabilities into experiments.

For example:

```yaml
id: suspicious-network-investigation
name: Suspicious Network Investigation
version: "1.0"

objective: >
  Determine whether the sample creates unexpected network activity.

capabilities:
  - process.observe
  - network.capture
  - artifact.collect

experiments:
  - id: observe-process
    objective: Observe process execution.
    capabilities: [process.observe]

  - id: capture-network
    objective: Capture network activity.
    capabilities: [network.capture]
    depends_on: [observe-process]

  - id: preserve-results
    objective: Preserve research evidence.
    capabilities: [artifact.collect]
    depends_on: [capture-network]
```

A recipe does **not** need to describe:

- Lima/Docker/Podman lifecycle
- VM creation or teardown
- installation commands
- MCP server implementation
- a particular CLI
- a particular LLM
- a particular agent runtime

Those are execution concerns.

---

# Validate

```bash
decretum validate recipes/<recipe>.yaml
```

Validation checks:

- recipe structure
- canonical capability references
- experiment dependencies
- policy/evidence requirements
- registered provider coverage

Nothing is executed.

---

# Resolve

```bash
decretum resolve recipes/<recipe>.yaml
```

Resolution follows:

```
Recipe
  ↓
Required capabilities
  ↓
Provider registry
  ↓
Provider readiness
  ↓
Integration / execution surface
  ↓
Harness implementation compatibility
  ↓
Harness operations
  ├── provision       (when compute is required)
  ├── implement_capabilities
  ├── execute
  ├── orchestrate
  ├── collect_evidence
  └── researcher_interaction
  ↓
Policy / semantic compatibility
  ↓
Selected provider + harness path
```

A provider being installed is **not enough**. Resolution checks the complete execution path. For a VM capability, for example:

```
compute.vm
   ↓
Lima / Incus / QEMU
   ↓
integration or direct tool surface
   ↓
selected harness
   ↓
harness can provision + implement + execute
   ↓
host/provider readiness + policy
   ↓
READY
```

If the harness cannot perform a required operation, the path is not ready and the contract records the missing operation instead of pretending the capability is executable.

A capability may have multiple providers:

```
network.capture
   |
   +-- tshark       → tool
   +-- tcpdump      → tool
   +-- pcap-mcp     → MCP
```

The compiler does not contain branches such as:

```python
if provider == "lima":
    ...
```

Adding a provider is registry work, not compiler work.

---

# Compile the execution contract

```bash
decretum compile recipes/<recipe>.yaml
```

The result is an auditable contract:

```
artifacts/<research-id>/
├── research-contract.json
├── provider-registry.snapshot.json
└── compilation-manifest.json
```

The contract records:

- requested capabilities
- experiment graph
- selected/resolved execution surfaces
- harness
- policy and approvals
- evidence requirements
- research-loop intent
- registry snapshot
- compilation provenance

The contract deliberately does **not** turn every provider lifecycle operation into a LinkML primitive.

---

# What the harness does

The contract tells a harness what the researcher wants and what must be preserved.

The harness is responsible for operational execution:

```
Contract
   ↓
Harness
   ├── provision environment
   ├── implement/resolution capabilities
   ├── execute experiments
   ├── orchestrate dependencies
   ├── collect evidence
   ├── interact with researcher
   ├── develop findings
   └── produce report
```

This keeps Decretum neutral across Codex, Goose, ADK, Pi and future runtimes.

---

# Persistent research knowledge

Execution results belong in the research store rather than in the recipe schema.

The persistent record can contain:

```
research-contract.json
research-session.sqlite3
research-ledger.jsonl
experiments/
evidence/
findings/
report/
```

The ledger is hash chained for tamper evidence.

```bash
decretum verify-ledger <research-id>
```

Replay is read-only:

```bash
decretum replay artifacts/<research-id>/research-contract.json
```

Replay does not execute tools, containers, VMs, MCP servers or agents.

---

## Recipe-level instrumentation and compute

Recipes can now express both **what must be available** and **which implementation providers are preferred**, without encoding provider lifecycle or provisioning logic.

```yaml
instrumentation:
  required:
    - syscall.observe
    - network.metadata
  preferred:
    - sysdig
    - zeek

compute:
  required:
    - compute.vm
  preferred:
    - lima
    - incus
```

The semantics are deliberately small:

- `required` lists capability IDs.
- `preferred` lists provider IDs from `schema/provider_registry.yaml`.
- Validation checks that preferred providers are registered and advertise a relevant required capability.
- Resolution records the preferences and marks matching providers as preferred.
- Experiment bindings prefer those providers when they are ready and policy-compatible.
- Provisioning, instrumentation activation, VM lifecycle, and teardown remain harness/runtime responsibilities.

See `recipes/suspicious-network-investigation.yaml` for a complete example.

# Adding a capability

Capability discovery follows:

```
DISCOVER
   ↓
PROPOSE
   ↓
SEMANTIC VALIDATION
   ↓
RESEARCHER APPROVAL
   ↓
CANONICAL CAPABILITY REGISTRY
```

For example, discovery may encounter:

```
cloud.audit.query
status: review_required
providers: none
```

That does not automatically make it canonical.

The researcher defines its semantics:

```yaml
id: cloud.audit.query
name: Query Cloud Audit Logs
kind: cloud
risk: read
description: Query cloud audit records for security investigation.
```

Then explicitly approve it:

```bash
decretum capabilities approve cloud.audit.query \
  --kind cloud \
  --risk read \
  --name "Query Cloud Audit Logs" \
  --description "Query cloud audit records for security investigation."
```

Only after approval should providers declare that they implement it.

---

# Adding a provider

Providers are implementation metadata:

```yaml
providers:
  tshark:
    interface:
      type: tool
      executable: tshark
    capabilities:
      - network.capture

  pcap-mcp:
    interface:
      type: mcp
      server: pcap
    capabilities:
      - network.capture

  lima:
    interface:
      type: api
      endpoint: local:lima
    capabilities:
      - compute.vm
      - compute.snapshot
```

A provider entry answers:

> **How can this capability currently be implemented?**

It does not redefine the semantic meaning of the capability.

Compute providers such as Lima, Docker, Podman, Incus, QEMU and Firecracker are therefore just execution surfaces. Their provisioning and lifecycle remain harness/runtime implementation concerns.

---

# Capability vs provider vs integration vs harness

| Concept | Question | Example |
|---|---|---|
| Capability | What do I need? | `network.capture` |
| Provider | What implements it? | `tshark` |
| Integration | How do I reach it? | `tool`, `MCP`, `API` |
| Harness | Who executes/orchestrates? | Codex |

This separation is the main extensibility boundary.

---

# Research workflow

For researchers:

```
1. Discover execution surfaces
2. Reuse or propose capabilities
3. Write a small recipe
4. Validate
5. Resolve
6. Review the resolution
7. Compile
8. Execute through a harness
9. Collect evidence
10. Develop findings
11. Produce report
12. Persist provenance
13. Replay later
```

For contributors:

```
Research need
     ↓
Capability semantics
     ↓
Canonical approval
     ↓
Provider implementation
     ↓
Integration
     ↓
Discovery/readiness
     ↓
Recipe
     ↓
Tests
```

---

# Project structure

```
Decretum/
├── schema/
│   ├── sec_research_metamodel.yaml
│   ├── capability_registry.yaml
│   ├── provider_registry.yaml
│   └── provider_registry.schema.yaml
├── recipes/
├── sec_agent/
│   ├── capability_registry.py
│   ├── capability_discovery.py
│   ├── resolver.py
│   ├── compatibility.py
│   ├── compiler.py
│   ├── research_state.py
│   └── replay.py
└── tests/
```

---

# Design principles

### 1. Capability semantics are canonical

The LinkML capability boundary defines stable research meaning.

### 2. Discovery is evidence, not ontology

Discovery can prove that an execution surface exists. It cannot silently invent a new security capability.

### 3. Recipes are compositions

Recipes should describe experiments using capabilities, not encode provider lifecycle.

### 4. Providers are open-world

A new provider should be addable through registry data without changing compiler logic.

### 5. Harnesses own execution

Provisioning, implementation, orchestration, interactive research and ephemeral lifecycle belong to the execution environment.

### 6. Research state is persistent

Evidence, findings, reports and provenance belong in the research store, not in a growing collection of execution primitives.

### 7. Reproducibility remains first-class

Contracts, registry snapshots, manifests, evidence and ledger history make a research session inspectable and replayable.

---

# Status

Decretum is evolving toward a **simple, community-extensible, harness-neutral security research compiler**.

The core model is:

```
Canonical capabilities
        +
Discoverable execution surfaces
        +
Small research recipes
        +
Capability resolution
        +
Harness-neutral execution contracts
        +
Persistent research knowledge
        =
Reproducible security research
```

> **Decretum defines what the researcher needs. The execution ecosystem determines how it is fulfilled.**
