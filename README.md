# Decretum

**Decretum is a local, interactive security-research workbench for Codex.**

Describe a security investigation in a small YAML recipe. Decretum validates the research boundary, creates a durable research contract, and lets Codex investigate interactively using the local workspace and approved tools.

The important part is the loop:

```text
Researcher
   ↓
Research recipe
   ↓
Decretum validates + compiles
   ↓
Codex investigates
   ↓
Evidence
   ↓
Interactive analysis
   ↓
Finding / hypothesis
   ↓
Researcher asks the next question
   ↓
New experiment when needed
   ↓
More evidence
   ↺
   ↓
Evidence-backed report
```

**There is no hosted/cloud sandbox provisioning in this branch.** Research execution stays local.

---

## What you can do

Use Decretum when you want to investigate something rather than simply run a fixed command.

Examples:

- analyze a suspicious file or program
- investigate process, filesystem, or network behavior
- perform detection-engineering experiments
- investigate a software supply-chain artifact
- compare observations with MITRE ATT&CK or other security frameworks
- correlate findings with threat-intelligence reports
- continue asking questions about evidence without restarting the research session
- ask Codex to propose another experiment when the current evidence is inconclusive

---

## 1. Install

Requirements:

- Python 3.11+
- Codex/OpenAI credentials
- Docker locally if you choose the Docker execution backend

Install:

```bash
git clone https://github.com/Opposum0112/Decretum.git
cd Decretum
uv sync
```

For Docker support:

```bash
uv sync --extra docker
```

Set credentials:

```bash
export OPENAI_API_KEY="..."
```

---

## 2. Create a research recipe

A recipe describes **what you want to investigate and what boundaries apply**.

Here is a deliberately small example:

```yaml
apiVersion: decretum.dev/v1
kind: ResearchExperiment

id: dns-behavior-001
name: Local DNS behavior investigation
version: "1.0"

role: threat_researcher

objective: >
  Determine whether the supplied program performs DNS activity
  and identify the observable behavior.

inputs:
  sample: ./samples/sample.bin

environment:
  type: local

  sandbox:
    backend: unix
    workspace_directory: .
    inherit_host_environment: false

  network:
    mode: none

  privileged: false

  codex:
    sandbox_mode: workspace-write
    approval_policy: on-request
    network_access_enabled: false
    web_search_mode: disabled
    persist_session: true

policy:
  allow:
    - artifact.read
    - artifact.collect
    - process.execute
    - process.observe
    - network.observe

  deny:
    - host.filesystem.write
    - host.mount
    - privileged.host_access
    - unrestricted.network
    - cloud.sandbox

  approval_required:
    - network.enable
    - new_capability

evidence:
  required:
    - process_activity
    - network_activity
    - dns_activity
    - indicators

completion:
  report_required: true
  conclusion_required: true

workload:
  command: ./samples/sample.bin
  timeout_seconds: 120

reports:
  - kind: markdown
    template: security-research
```

For untrusted workloads, use a stronger externally isolated environment or the local Docker backend rather than treating Unix-local execution as a strong security boundary.

---

## 3. Validate before running

```bash
decretum validate recipes/dns-behavior.yaml
```

You should see the recipe's validation and preflight checks.

Nothing is executed by validation.

---

## 4. Compile the research contract

```bash
decretum compile recipes/dns-behavior.yaml
```

Decretum creates a deterministic contract containing the:

- research objective
- inputs
- execution environment
- Codex settings
- capabilities
- policy
- evidence requirements
- completion criteria
- report requirements

The contract becomes the authoritative boundary for the investigation.

---

## 5. Start the investigation

```bash
decretum run recipes/dns-behavior.yaml --dry-run=false
```

Codex now investigates the local workspace.

It can:

1. inspect the supplied input
2. inspect available local evidence
3. form a hypothesis
4. perform an allowed experiment
5. collect evidence
6. analyze that evidence
7. determine what remains unknown
8. continue the investigation within the contract

The researcher does **not** have to provide every individual command in advance.

---

# 6. Interactively analyze the evidence

This is the core Decretum workflow.

Suppose Codex has collected:

```text
process trace
DNS observations
filesystem changes
execution logs
sample hash
```

Ask a follow-up question:

```bash
decretum analyze dns-behavior-001 \
  "Analyze the process and DNS evidence. Does it support the hypothesis that the sample performs DNS-based command and control?"
```

Then ask another:

```bash
decretum analyze dns-behavior-001 \
  "Compare the DNS observations with the process timeline and identify inconsistencies."
```

Then:

```bash
decretum analyze dns-behavior-001 \
  "What evidence is still missing before we can reach a defensible conclusion?"
```

These are **continuations of the research**, not independent conversations.

The research session and Decretum ledger preserve the investigation state.

---

# 7. Let evidence drive the next experiment

Suppose the analysis concludes:

```text
The available evidence shows DNS activity, but it does not
establish whether the observed domain is part of the sample's
control channel.
```

The researcher can ask:

```bash
decretum analyze dns-behavior-001 \
  "Propose the safest next experiment that could distinguish
   ordinary DNS resolution from command-and-control behavior."
```

The resulting investigation can identify:

- the hypothesis being tested
- required capabilities
- required evidence
- the proposed experiment
- whether researcher approval is required

If the experiment requires a capability outside the existing contract, it must go through the Decretum policy/approval boundary rather than silently expanding access.

---

# 8. Persistent findings

Research findings are not intended to disappear when the Codex conversation ends.

A finding can retain:

```text
Finding
├── statement
├── status
├── evidence references
├── semantic tags
├── entities
├── techniques
├── tactics
├── controls
├── confidence
├── supporting references
└── provenance
```

For example:

```yaml
id: FIND-017

statement: >
  The sample performs DNS resolution before the observed
  outbound connection.

status: supported

semantic_tags:
  - dns
  - network-behavior
  - possible-c2

techniques:
  - ATT&CK:T1071.004

tactics:
  - command-and-control

evidence_ids:
  - EVID-021
  - EVID-022

confidence: high
```

These findings can become reusable knowledge for later investigations.

A later investigation can therefore ask:

```text
Have we previously observed behavior related to this
technique, artifact, domain, process, or indicator?
```

The goal is to build **research memory**, not merely conversation history.

---

# 9. Use security-framework and threat-intelligence references

Recipes can provide references that help establish the analytical context.

Supported reference categories include:

- security frameworks
- threat-intelligence reports
- threat-intelligence feeds
- vendor advisories
- vulnerability databases
- research papers
- incident reports
- malware reports
- detection content
- standards documents

Example:

```yaml
references:

  - id: ATTCK-T1071-004
    type: security_framework
    authority: mitre
    title: Application Layer Protocol: DNS
    uri: https://example.invalid/replace-with-authoritative-reference
    version: "current"
    citation: "ATT&CK T1071.004"

  - id: TI-REPORT-001
    type: threat_intelligence_report
    authority: researcher
    title: Related DNS behavior report
    uri: https://example.invalid/report
    citation: "Research report reference"
```

Use authoritative URLs and citations appropriate to your investigation. Decretum stores the reference metadata; Codex uses the references as analytical context.

---

# 10. Research state

A local investigation can accumulate state like:

```text
artifacts/
└── dns-behavior-001/
    ├── research-contract.json
    ├── research-session.sqlite3
    ├── research-ledger.jsonl
    ├── experiments/
    │   ├── 001/
    │   └── 002/
    ├── evidence/
    │   ├── process/
    │   ├── network/
    │   ├── filesystem/
    │   └── indicators/
    ├── hypotheses/
    └── report/
```

The ledger records the evolution of the investigation.

The session stores interactive conversation state.

The evidence directory stores the actual research artifacts.

The contract records what the investigation was authorized to do.

---

# 11. Inspect a research investigation

```bash
decretum inspect dns-behavior-001
```

This shows the locally persisted research state.

---

# 12. Generate the final report

The investigation should reach the report only after the required evidence has been examined.

The final report should be based on:

```text
Research objective
      +
Experiments performed
      +
Observed evidence
      +
Persistent findings
      +
Researcher decisions
      +
Security-framework references
      +
Threat-intelligence references
      ↓
Evidence-backed conclusion
      ↓
Research report
```

The important principle is:

> **The report is the result of the investigation, not the source of truth for the investigation.**

---

## How the pieces fit together

| Component | Responsibility |
|---|---|
| **Researcher** | Defines questions, reviews evidence, redirects research, approves requested changes |
| **Decretum** | Validates recipes, compiles contracts, enforces declared boundaries, persists research state |
| **Codex** | Performs interactive reasoning and local research work |
| **Local workspace** | Holds experiments and evidence |
| **MCP/tools** | Provide specialized research capabilities |
| **Research ledger** | Preserves investigation history |
| **Semantic findings** | Preserve reusable research knowledge |
| **References** | Connect findings to frameworks and intelligence |
| **Report** | Communicates the evidence-backed result |

---

## Design philosophy

Decretum intentionally does **not** try to become another agent framework.

It provides the structure around an interactive security investigation:

1. **Declare** what you want to investigate.
2. **Validate** the research boundary.
3. **Compile** the contract.
4. **Investigate** with Codex.
5. **Collect** evidence.
6. **Analyze** evidence interactively.
7. **Record** findings and hypotheses.
8. **Ask** the researcher when direction or authorization is needed.
9. **Run** another local experiment when justified.
10. **Repeat** until the evidence is sufficient.
11. **Generate** the evidence-backed report.
12. **Preserve** the findings for future investigations.

The intended result is a **persistent, interactive security-research environment**, not a one-shot experiment runner.

## Local-first security boundary

This branch intentionally excludes hosted/cloud sandbox provisioning.

The execution model is:

```text
Decretum contract
       ↓
Codex
       ↓
Local Unix / Local Docker
       ↓
Local evidence
```

For hostile workloads, use appropriate authorization and containment controls. Unix-local execution is not a strong isolation boundary; use Docker or stronger external isolation when the workload requires it.

## Repository

```text
schema/
  sec_research_metamodel.yaml

recipes/
  *.yaml

sec_agent/
  validator.py
  compiler.py
  openai_runner.py
  research_state.py
  cli.py

tests/
  test_validator.py
```

## Current status

This branch implements the local Codex-oriented architecture with:

- declarative research recipes
- contract compilation
- local execution
- interactive Codex sessions
- persistent session state
- research ledger
- semantic findings
- hypothesis tracking
- experiment requests
- security-framework references
- threat-intelligence references
- evidence-oriented investigation flow

The remaining evolution is to make experiment lifecycle, evidence ingestion, semantic retrieval, researcher approvals, and report generation fully structured end-to-end rather than relying on free-form Codex output.


## Declaring capabilities

You can declare capabilities directly in a recipe or attach them to skills. For example:

```yaml
capabilities:
  - id: process.observe
    name: Observe processes
    kind: process
    risk: observe
    description: Inspect process execution and metadata
    requires_approval: false
    tools: [strace, tetragon]
    evidence_outputs: [process_events]

skills:
  - id: malware.behavior
    name: Malware behavior analysis
    kind: malware_analysis
    description: Analyze process, filesystem, and network behavior
    capabilities:
      - id: process.observe
        name: Observe processes
        kind: process
        risk: observe
        description: Inspect process execution and metadata
```

This makes the security boundary understandable to both humans and automation: **what the researcher wants, what the agent may do, which instruments may be used, and what evidence must come back**.

## Security framework and threat-intelligence references

Recipes can attach structured references to the investigation, including security frameworks, threat-intelligence reports and feeds, vendor advisories, vulnerability databases, research papers, incident reports, malware reports, detection content, and standards.

Use the reference fields to preserve the source identity, authority, title, URI/citation, version, access time, and notes. Findings can then retain links to the evidence and references that support them.

## What Codex does

Codex is the interactive research executor. It can:

1. Read the compiled contract and current research state.
2. Select or compose declared skills.
3. Inspect existing evidence.
4. Form or update hypotheses.
5. Propose and execute bounded experiments when permitted.
6. Collect and hash evidence.
7. Re-analyze accumulated evidence when the researcher asks a follow-up question.
8. Record findings and their evidence/reference relationships.
9. Continue the research loop until the declared completion criteria are satisfied.

Codex does **not** expand the contract silently. New privileges, capabilities, tools, or network access require the policy/approval path defined by the recipe.

## Local execution boundary

Decretum is intentionally local-first. The current execution boundary is Unix or Docker on the researcher's machine. It does not provision a hosted/cloud sandbox.

This is especially important for security research: the recipe describes the permitted boundary, the validator checks it, the compiler freezes it into a contract, and Codex operates inside that contract.
