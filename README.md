# Decretum

> **Define a security experiment once. Decretum validates it, finds usable implementations, freezes the plan, and lets your chosen agent harness execute it.**

Decretum is a **local-first security-research compiler**. You write a YAML research recipe; Decretum turns it into a validated, auditable execution contract that compatible harnesses such as Codex, Goose, ADK, or Pi can execute.

Decretum is **not another agent runtime**. It provides the research language, capability model, provider resolution, policy boundaries, reproducibility, and provenance.

## Start here

```text
1. Write or choose a recipe
        ↓
2. Validate it
        ↓
3. Resolve capabilities and prerequisites
        ↓
4. Compile and review the contract
        ↓
5. Run with a supported harness
        ↓
6. Collect evidence and findings
        ↓
7. Replay or verify provenance later
```

### Example: investigate suspicious network activity

Imagine you want to determine whether a suspicious program creates unexpected network connections. The recipe describes the research need rather than hard-coding one capture utility:

```yaml
id: suspicious-network-investigation
name: Suspicious Network Investigation
version: "1.0"
role: malware_researcher

objective: Determine whether the sample creates unexpected network activity.

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
    capabilities: [process.observe, network.capture]

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

Decretum may resolve the network capability like this:

```text
network.capture
  ├── tshark      READY → selected
  ├── tcpdump     READY → safe fallback
  └── pcap-mcp    NOT READY
```

The recipe stays portable because the researcher asked for `network.capture`, not specifically for tshark.

## Run an experiment

### 1. Install

Requirements: Python 3.11+, uv, and credentials/configuration required by the selected harness and model.

```bash
git clone https://github.com/Opposum0112/Decretum.git
cd Decretum
uv sync
```

### 2. Validate

```bash
decretum validate recipes/<recipe>.yaml
```

Checks the recipe without executing anything.

### 3. Resolve

```bash
decretum resolve recipes/<recipe>.yaml
```

Resolution tells you which capabilities are required, which providers implement them, which prerequisites are ready, which harnesses are compatible, and which fallbacks are safe. **Nothing is executed.**

### 4. Compile

```bash
decretum compile recipes/<recipe>.yaml
```

Creates:

```text
artifacts/<research-id>/
├── research-contract.json
├── provider-registry.snapshot.json
└── compilation-manifest.json
```

Review `execution_plan`, `approval_plan`, `resolution`, `plan_digest`, and the compilation manifest before execution.

### 5. Run

```bash
decretum run recipes/<recipe>.yaml --dry-run=false
```

The selected harness executes within the compiled research boundary.

### 6. Continue and inspect

```bash
decretum analyze <research-id> "What evidence is still missing?"
decretum inspect <research-id>
```

### 7. Verify and replay

```bash
decretum verify-ledger <research-id>
decretum replay artifacts/<research-id>/research-contract.json
```

Replay is read-only. It does not launch tools, containers, VMs, MCP servers, or agents.

## Discover execution surfaces

You can now ask Decretum what is actually available on the current host before writing or compiling a recipe:

```bash
decretum capabilities discover
```

For a recipe, include its requested capabilities and get candidate definitions for anything that is not yet registered:

```bash
decretum capabilities discover --recipe recipes/<recipe>.yaml
```

Discovery writes:

```text
artifacts/capability-discovery/
├── capability-surface-manifest.json
└── capability-candidates.yaml   # only when review is required
```

A discovered surface records:

```text
capability
    ↓
provider
    ↓
interface: tool | api | mcp
    ↓
local availability
    ↓
compatible installed harnesses
    ↓
ready execution surface
```

For example:

```text
network.capture
├── tshark
│   └── tool → Codex/Goose/ADK → READY
├── tcpdump
│   └── tool → Codex/Goose/ADK → READY
└── pcap-mcp
    └── MCP → registered, but not locally verified
```

### Discovery does not silently change the ontology

This is an important boundary:

```text
DISCOVER
   ↓
PROPOSE
   ↓
VALIDATE
   ↓
APPROVE
   ↓
REGISTER
   ↓
COMPOSE INTO RECIPES
```

Decretum can discover that a new execution surface exists, but it does not infer security semantics from an executable name and does not automatically edit the canonical LinkML schema.

If a recipe references an unknown capability, discovery creates a reviewable CapabilityCandidate. A researcher can then define its semantics, register providers/integrations, add tests, and make it available for future recipe composition.

This keeps the ontology portable while allowing host-specific execution surfaces to evolve quickly.

## How the system decides what can run

```text
Recipe
  ↓
Schema validation
  ↓
Capability requirements
  ↓
Provider registry
  ↓
Discovery + readiness
  ↓
Policy
  ↓
Schema compatibility
  ↓
Provider selection + safe fallbacks
  ↓
Experiment execution plan
  ↓
Frozen execution contract
```

## Architecture

```text
Researcher
    │
    ▼
Research Recipe ──────────────┐
    │                         │
    ▼                         │
LinkML Schema                 │
    │                         │
    ▼                         ▼
Capability Model         Experiment DAG
    │                         │
    └──────────┬──────────────┘
               ▼
       Provider Registry
               │
       ┌───────┴────────┐
       ▼                ▼
  Discovery        Integrations
       │                │
       └───────┬────────┘
               ▼
           Readiness
               ▼
             Policy
               ▼
         Compatibility
               ▼
       Provider Resolver
               ▼
        Execution Plan
          │         │
          ▼         ▼
    Plan Digest  Registry Snapshot
          │         │
          └────┬────┘
               ▼
      Compilation Manifest
               ▼
   ResearchExecutionContract
               ▼
        Harness Adapter
          │     │     │
        Codex  Goose  ADK
               │
               ▼
          Experiments
               ▼
            Evidence
               ▼
            Findings
               ▼
      Hash-chained Ledger
               ▼
        Offline Replay
```

### Component responsibilities

| Component | Responsibility |
|---|---|
| Schema | Stable research semantics |
| Recipe | One investigation and its experiment graph |
| Registry | Capability implementations, integrations, harnesses and models |
| Discovery / readiness | What is usable on this host |
| Policy | What the research permits |
| Compatibility | Whether a provider satisfies capability semantics |
| Resolver | Selects providers and safe fallbacks |
| Compiler | Freezes an auditable execution contract |
| Harness adapter | Translates the contract for an execution harness |
| Research state | Evidence, hypotheses, findings and provenance |
| Replay | Historical integrity and current reproducibility checks |

## Persistent artifacts

```text
artifacts/<research-id>/
├── research-contract.json
├── compilation-manifest.json
├── provider-registry.snapshot.json
├── research-session.sqlite3
├── research-ledger.jsonl
├── experiments/
├── evidence/
└── report/
```

The compilation manifest records hashes for the recipe, schema and provider registry plus compiler/runtime information. The registry snapshot preserves the exact provider metadata used during compilation.

## Safety

Decretum is local-first and does not claim Unix execution is a strong security boundary. Use an appropriately isolated environment for hostile workloads.

Recipes should explicitly constrain privileged execution, filesystem writes, host mounts, network access, cloud/API access, and approval requirements.

## Community contributions

Decretum is designed so researchers can contribute **capabilities, providers, integrations, and reusable recipes independently**.

### What should you contribute?

| Contribution | Where | Purpose |
|---|---|---|
| Capability | `schema/` | Defines a stable research action |
| Provider | `schema/provider_registry.yaml` | Implements a capability through MCP, API, or tool/CLI |
| Integration | provider registry | Describes how the provider is reached |
| Recipe | `recipes/` | Reusable investigation composed from capabilities |
| Tests/docs | `tests/`, README/docs | Makes behavior reproducible for other researchers |

### Add a new capability

Add a capability when the community needs a **new research action**, not simply another implementation.

Example:

```yaml
- id: cloud.audit.query
  name: Query Cloud Audit Logs
  kind: cloud
  risk: read
  description: Query cloud audit records for security investigation.
  allowed_networks: [restricted, internet]
  allowed_execution_modes: [observe, collect]
  evidence_outputs: [audit_events]
```

Then register implementations independently:

```text
cloud.audit.query
├── AWS CloudTrail API
├── Azure Monitor API
├── GCP Audit Logs API
└── Cloud Audit MCP
```

Do not make a product name the capability unless the product-specific behavior is itself the research action. Prefer `cloud.audit.query` over `aws.cloudtrail.query` when the semantic action is portable.

### Add a provider

Register the provider against an existing capability. Declare its interface, integration, readiness requirements, and execution semantics. Do not change the capability meaning merely to accommodate one tool.

### Add a recipe

A recipe should explain:

1. the research question
2. required capabilities
3. experiment steps and dependencies
4. expected evidence
5. denied capabilities and approval boundaries
6. completion criteria

Prefer:

```text
capability → experiment → evidence
```

over a recipe tied to one hard-coded command. Let the resolver select the implementation.

### Contribution workflow

```text
Research need
    ↓
Does the capability already exist?
    ├── Yes → reuse it
    └── No  → propose CapabilitySpec
                 ↓
            Add provider(s)
                 ↓
            Add integration if needed
                 ↓
            Add compatibility/readiness tests
                 ↓
            Add example recipe
                 ↓
          Validate + resolve + compile
                 ↓
                Tests
                 ↓
             Pull request
```

Before opening a PR:

```bash
uv sync
uv run pytest
decretum validate recipes/<recipe>.yaml
decretum resolve recipes/<recipe>.yaml
decretum compile recipes/<recipe>.yaml
```

For a new capability, include why an existing capability is insufficient, the semantic definition, providers, compatibility/readiness expectations, tests, and at least one example recipe.

For a new recipe, include the objective, capability requirements, experiment graph, evidence expectations, policy boundaries, and example usage.

Never include credentials, private customer data, malware samples, or sensitive research artifacts in a public contribution.

## Repository layout

```text
schema/       LinkML research model and provider registry
recipes/      Reusable security-research experiments
sec_agent/    Validation, resolution, compilation, replay and research state
tests/        Regression tests
```

## Status

Decretum is evolving toward a **harness-neutral security-research compiler** with declarative recipes, LinkML-governed capabilities, provider resolution, policy-aware planning, deterministic contracts, immutable compilation inputs, execution provenance, tamper-evident research state, and offline replay.

The project deliberately does **not** try to replace agent runtimes such as Codex, Goose or ADK. It defines the research contract they execute.
