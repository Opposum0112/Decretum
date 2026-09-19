# Decretum

> **Decretum defines what a security researcher needs. The execution ecosystem determines how it is fulfilled.**

Decretum is a **harness-neutral security research compiler and capability resolver**. It discovers execution surfaces, validates canonical capabilities, resolves providers/integrations/harness compatibility, and compiles a portable **Research Execution Contract**.

## 🚧 Frozen architecture rule

> **Decretum is not a runtime. Decretum is responsible for determining what can be executed and producing a portable execution contract. It does not execute research, manage researcher interaction, collect evidence, maintain findings, or generate reports.**

After compilation, **Decretum stops**.

The compiled contract is passed to an external harness runtime such as Codex, Goose, OpenCode, Google ADK, Vercel AI, or another compatible runtime.

The external runtime owns the interactive investigation and writes the resulting evidence, findings, and report to its research/evidence store.

If the investigation needs a **new capability or changed requirement**, the request returns to Decretum for resolution and a new contract.

---

# Architecture

```
                         RESEARCHER
                             |
                         Research Recipe
                             |
                             v
                 +-------------------------+
                 |        DECRETUM         |
                 |                         |
                 | Capability Registry     |
                 | Provider Registry       |
                 | Profiles                |
                 | Discovery               |
                 | Validation              |
                 | Policy                  |
                 | Resolver                |
                 | Compiler                |
                 +------------+------------+
                              |
                              | ResearchExecutionContract
                              v
                 +-------------------------+
                 |    HARNESS RUNTIME      |
                 |                         |
                 | Codex / Goose / etc.    |
                 |                         |
                 | Researcher interaction  |
                 | Provisioning             |
                 | Experiment execution    |
                 | Evidence collection     |
                 | Analysis                |
                 | Findings                |
                 | Report                  |
                 +------------+------------+
                              |
                              v
                 +-------------------------+
                 | RESEARCH / EVIDENCE     |
                 | STORE                   |
                 |                         |
                 | Sessions                |
                 | Experiments             |
                 | Evidence                |
                 | Findings                |
                 | Hypotheses              |
                 | Reports                 |
                 | Provenance              |
                 +-------------------------+
```

### The boundary

| Component | Owns |
|---|---|
| **Decretum** | What is required, what is available, resolution, policy, compilation |
| **Execution contract** | Portable handoff between Decretum and a runtime |
| **Harness runtime** | How research is executed and how the researcher interacts |
| **Research/evidence store** | Persistent investigation state and artifacts |

### Core vocabulary

```
Capability    = what is needed
Profile       = execution characteristics/preferences
Provider      = implementation
Integration   = access surface
Harness       = runtime that executes/orchestrates the contract
Contract      = compiled handoff
Evidence      = observed research artifacts
Finding       = evidence-backed conclusion
```

---

# Research workflow

A researcher should experience Decretum as a **research compiler**, not as another agent framework.

```
1. Define research objective
          |
2. Compose canonical capabilities
          |
3. Select infrastructure / instrumentation / harness profiles
          |
4. Validate recipe
          |
5. Discover available execution surfaces
          |
6. Resolve capability -> provider -> integration -> harness
          |
7. Review resolution
          |
8. Compile ResearchExecutionContract
          |
9. Pass contract to external harness runtime
          |
          +-------------------------------+
          |                               |
          v                               |
10. Harness conducts interactive          |
    investigation                         |
          |                               |
          +--> experiment                 |
          +--> collect evidence           |
          +--> analyze                    |
          +--> finding                    |
          +--> researcher interaction     |
          +--> report                     |
          |                               |
11. Persist evidence/findings/report <----+
          |
12. Need a new capability?
          |
          +--> return to Decretum
               resolve + compile again
```

**Decretum does not perform steps 9–11.**

---

# Quick start

```bash
git clone https://github.com/Opposum0112/Decretum.git
cd Decretum
uv sync
```

## Discover

```bash
decretum capabilities discover
```

Discovery checks registered tools, APIs, MCP surfaces, integrations, compute providers, and harness availability.

It can produce:

```
artifacts/capability-discovery/
├── capability-surface-manifest.json
└── capability-candidates.yaml
```

Discovery **never silently modifies canonical capability semantics**.

## Validate

```bash
decretum validate recipes/<recipe>.yaml
```

Nothing is executed.

## Resolve

```bash
decretum resolve recipes/<recipe>.yaml
```

Resolution validates the complete path:

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

## Compile

```bash
decretum compile recipes/<recipe>.yaml
```

Output:

```
artifacts/<research-id>/
├── research-contract.json
├── provider-registry.snapshot.json
└── compilation-manifest.json
```

## Inspect the handoff

```bash
decretum handoff artifacts/<research-id>/research-contract.json
```

This prints the portable handoff envelope. **It does not execute anything.**

---

# Example recipe

Keep recipes semantic and small:

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

infrastructure_profile: isolated-linux-vm
instrumentation_profile: linux-network-observation
harness_profile: interactive-research

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

The recipe does **not** contain Lima/Docker lifecycle, installation commands, MCP implementation, agent prompts, or runtime-specific execution code.

---

# What the compiled contract means

The contract is the boundary between Decretum and the execution ecosystem.

Conceptually:

```json
{
  "kind": "ResearchExecutionContract",
  "contract_version": "5",

  "capabilities": [
    "process.observe",
    "network.capture",
    "artifact.collect"
  ],

  "execution": {
    "harness": "codex",
    "resolution": "..."
  },

  "handoff": {
    "target": "external_harness_runtime",
    "mode": "contract_only",
    "decretum_stops_after_compilation": true
  }
}
```

The runtime may consume the contract in its own native format, but it must preserve the contract's semantic requirements and policy.

---

# Interactive investigation belongs to the harness

The external harness runtime can conduct a loop such as:

```
Compiled Contract
      |
      v
Harness Runtime
      |
      +--> Researcher asks question
      |
      +--> Form hypothesis
      |
      +--> Run experiment
      |
      +--> Collect evidence
      |
      +--> Analyze evidence
      |
      +--> Record finding
      |
      +--> Generate report
      |
      +--> Ask researcher for next direction
      |
      +--> Request another experiment
                 |
                 v
          New capability?
             /      \
           no       yes
           |         |
       continue   return to
                  Decretum
```

A runtime can therefore remain stateful and interactive without making Decretum stateful.

---

# Evidence, findings and research knowledge

The research/evidence store belongs to the **harness/runtime ecosystem**.

A runtime may persist:

```
research/
├── sessions/
├── experiments/
├── hypotheses/
├── evidence/
├── findings/
├── reports/
├── interactions/
└── provenance/
```

Evidence should retain provenance such as:

```json
{
  "id": "ev-001",
  "kind": "network.pcap",
  "experiment_id": "capture-network",
  "sha256": "...",
  "provider": "tcpdump"
}
```

Findings should reference the evidence that supports them:

```json
{
  "id": "finding-001",
  "statement": "Observed external DNS communication.",
  "status": "supported",
  "evidence_ids": ["ev-001"],
  "confidence": "high"
}
```

This lets the runtime build a persistent research knowledge graph without turning Decretum into a database or investigation engine.

---

# Capability lifecycle

New capabilities follow an explicit promotion path:

```
DISCOVER
   |
PROPOSE
   |
SEMANTIC REVIEW
   |
RESEARCHER APPROVAL
   |
CANONICAL CAPABILITY
   |
PROVIDER IMPLEMENTATIONS
```

Discovery can report:

```yaml
capability: cloud.audit.query
status: review_required
source:
  provider: example-provider
```

It must **not** silently add the capability to the canonical registry.

After review:

```bash
decretum capabilities approve cloud.audit.query \
  --kind cloud \
  --risk read \
  --name "Query Cloud Audit Logs" \
  --description "Query cloud audit records for security investigation."
```

Providers can then implement the canonical capability.

---

# Adding a provider

Provider metadata describes implementation and access:

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

Provider metadata does **not** redefine capability semantics.

A new provider should normally be registry work, not compiler branching.

---

# Profiles

Profiles separate execution preferences from semantic capabilities.

```yaml
infrastructure_profile: isolated-linux-vm
instrumentation_profile: linux-network-observation
harness_profile: interactive-research
```

Examples:

- Infrastructure: Lima / Incus / QEMU, VM size, OS, isolation
- Instrumentation: Sysdig / Zeek / tcpdump
- Harness: Codex / Goose / OpenCode / ADK / Vercel AI

The same research recipe can therefore be compiled against different execution environments without changing its research semantics.

---

# Why the runtime boundary matters

This architecture deliberately avoids making Decretum:

- an agent framework
- a workflow engine
- a VM/container orchestrator
- an evidence database
- a finding engine
- a report generator
- a long-running researcher process
- a Codex/Goose/OpenCode replacement

Instead:

```
Decretum
  = research intent compiler

Harness
  = interactive research execution environment

Research Store
  = persistent research memory
```

This makes the system composable with existing and future agent runtimes.

---

# Contribution guide

Community contributions should follow the capability boundary.

## 1. Add a research capability

Start with the research question:

> What security-research capability is actually missing?

Then define stable semantics.

Do not start by adding a provider-specific name.

## 2. Propose the capability

Use discovery evidence or a capability proposal.

Explain:

- what the capability means
- why it is distinct from existing capabilities
- required risk level
- expected evidence outputs
- isolation/network requirements
- execution constraints

## 3. Get canonical approval

A capability becomes canonical only after explicit review.

This prevents every new tool from expanding the ontology.

## 4. Add an implementation

Add provider metadata describing how the canonical capability is implemented.

Examples:

```
network.capture
  ├── tcpdump
  ├── tshark
  └── pcap-mcp
```

No compiler branch should be necessary.

## 5. Add or update integration metadata

Describe the access surface:

```
tool
MCP
API
local executable
```

## 6. Add discovery/readiness checks

A provider should only be considered usable when its execution surface is actually available.

## 7. Add tests

Contributors should test:

- schema semantics
- provider registration
- discovery
- readiness
- capability resolution
- policy compatibility
- deterministic contract compilation
- contract handoff boundary

## 8. Keep runtime-specific work outside Decretum

If your contribution implements:

- Codex execution
- Goose execution
- OpenCode execution
- researcher UI
- experiment orchestration
- evidence database
- finding analysis
- report generation

it belongs in a harness/runtime or research-store project, not in the Decretum compiler core.

---

# Community contribution path

```
Researcher
   |
   v
Research need
   |
   v
Capability proposal
   |
   v
Semantic review
   |
   v
Canonical capability
   |
   +-------------------+
   |                   |
   v                   v
Provider             Profile
implementation       preference
   |                   |
   +---------+---------+
             |
             v
        Discovery
             |
             v
          Resolver
             |
             v
          Compiler
             |
             v
      Execution Contract
             |
             v
     External Harness
```

The community can therefore extend Decretum at several independent layers without coupling everything to one agent runtime.

---

# Project structure

```
Decretum/
├── schema/
│   ├── sec_research_metamodel.yaml
│   ├── capability_registry.yaml
│   ├── provider_registry.yaml
│   ├── profile_registry.yaml
│   └── provider_registry.schema.yaml
├── recipes/
├── sec_agent/
│   ├── capability_registry.py
│   ├── capability_discovery.py
│   ├── profile_registry.py
│   ├── resolver.py
│   ├── compatibility.py
│   ├── policy.py
│   ├── compiler.py
│   ├── manifest.py
│   ├── registry_snapshot.py
│   └── replay.py
└── tests/
```

---

# Frozen architectural invariants

These rules are intentionally frozen:

1. **Decretum is a compiler/resolver, not a runtime.**
2. **Decretum stops after producing the execution contract.**
3. **Harness runtimes own interactive researcher investigation.**
4. **Harness runtimes own provisioning, execution and orchestration.**
5. **Research/evidence stores live outside Decretum.**
6. **Findings and reports are produced and persisted by the runtime ecosystem.**
7. **New capability requirements return to Decretum for resolution and recompilation.**
8. **Canonical capability semantics are independent of providers and harnesses.**
9. **Provider additions must not require compiler branching.**
10. **The execution contract is the stable interoperability boundary.**
11. **Discovery can propose capabilities but cannot silently mutate the canonical ontology.**
12. **Replay/verification in Decretum is read-only and never executes research.**

> **Define in Decretum. Investigate in the harness. Remember in the research store.**

---

# Status

Decretum is intentionally focused on one job:

```
Research Intent
      +
Canonical Capabilities
      +
Discoverable Execution Surfaces
      +
Resolution
      +
Policy
      |
      v
Portable Research Execution Contract
```

The execution ecosystem then takes over.

That separation is the foundation for a community-extensible, harness-neutral security research ecosystem.
