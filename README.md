# Decretum

**Decretum defines the security-research ontology and boundaries. Codex is the interactive researcher that selects, composes, orchestrates, and executes the declared skills.**

Decretum is a local, interactive security-research workbench for Codex. It defines the schema, validates the research recipe, compiles the authorized research contract, and preserves the evidence and findings produced during the investigation.

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

## What Decretum does

Think of Decretum as a **security-research contract compiler**.

You describe your investigation in YAML. Decretum checks it and turns it into a clear contract for Codex.

```text
Your question
     ↓
Simple YAML recipe
     ↓
Decretum validates it
     ↓
Decretum compiles a research contract
     ↓
Codex investigates interactively
     ↓
Evidence → Findings → Report
```

You do **not** need to define every command or every investigation step.

### The four things to remember

**1. Schema — what is possible**

The LinkML schema defines the security-research vocabulary: roles, skills, capabilities, tools, compute providers, evidence, policy, and references.

**2. Recipe — what this investigation allows**

Your recipe selects the parts you want for one investigation:

```yaml
role: threat_researcher
skills:
  - malware.behavior-analysis
capabilities:
  - process.observe
  - network.capture
environment:
  compute:
    provider: lima
```

**3. Contract — the boundary**

Decretum validates and compiles the recipe into a `ResearchContract`. The contract records the research objective, capabilities, tools, compute boundary, policy, and required evidence.

**4. Codex — the interactive researcher**

Codex uses the contract to select skills, combine them, choose instrumentation, run permitted experiments, inspect evidence, form hypotheses, and iterate with you.

> **Decretum defines the boundary. Codex explores inside the boundary.**

### Capabilities are tool-independent

You normally describe **what you need**, not a specific tool.

For example, `process.observe` can be implemented with Sysdig, Falco, Tracee, Tetragon, bpftrace, BCC, strace, auditd, or osquery.

`network.capture` can use tcpdump, tshark, dumpcap, Wireshark, Zeek, Suricata, or Snort.

Local compute can use Unix, Docker, Podman, Lima, Incus, LXC, KVM, Firecracker, or QEMU.

Decretum validates the declared boundary; Codex chooses an appropriate declared implementation.

## What you can do

Use Decretum for interactive security research such as:

- malware and suspicious-file analysis
- process and system behavior investigation
- network and DNS research
- detection-engineering experiments
- software supply-chain research
- vulnerability research
- forensic investigation
- threat-intelligence correlation
- security-framework mapping

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

## Architecture and boundaries

Decretum separates **what is allowed** from **how the investigation is performed**.

```text
                         DECRETUM
       ┌─────────────────────────────────────────┐
       │ Security-research ontology (LinkML)    │
       │ Role → Skill → Capability → Tool       │
       │ Evidence → Finding → Reference         │
       └───────────────────┬─────────────────────┘
                           │
                    Schema boundary
                           │
                           ▼
                 ┌───────────────────┐
                 │ Research Recipe   │
                 │ Objective / Input │
                 │ Role / Skills     │
                 │ Capabilities      │
                 │ Policy / Env     │
                 │ Evidence / Done  │
                 └─────────┬─────────┘
                           │
                  Execution boundary
                           │
                           ▼
                 Research Contract
                           │
                           ▼
                    ┌────────────┐
                    │   CODEX    │
                    │ Select     │
                    │ Compose    │
                    │ Orchestrate│
                    │ Execute    │
                    │ Analyze    │
                    └─────┬──────┘
                          │
                   Local Unix/Docker
                          │
                    Tools / MCP
                          │
                          ▼
             Evidence → Findings → Report
```

### Schema boundary — Decretum defines the vocabulary

The LinkML schema defines what a valid security investigation can express. It establishes the ontology for roles, skills, capabilities, tools, evidence, findings, references, and policy.

The schema is the **ontology and capability vocabulary boundary**. It does not orchestrate an investigation.

### Recipe boundary — the investigation authorization boundary

A recipe is an instance of that ontology for one concrete investigation. It answers: **What is this investigation authorized to do?**

The recipe specifies the objective, inputs, role, skills, capabilities, tools, environment, policy, evidence requirements, and completion criteria.

A capability can exist in the schema while a particular recipe chooses not to declare it, or requires researcher approval for it.

The recipe is therefore the **specific research authorization/execution boundary**.

### Compiler — freezes the boundary

Decretum validates the recipe and compiles it into a deterministic `ResearchContract`. The contract is the machine-readable snapshot of the effective role, skills, capabilities, tools, environment, policy, evidence requirements, completion criteria, and references.

Codex operates from this compiled contract rather than inventing a new security boundary during execution.

### Codex — the interactive researcher and orchestrator

Codex owns the dynamic part of research. It can understand the objective, inspect evidence, select and compose declared skills, determine investigation order, form hypotheses, propose experiments, execute permitted operations, collect evidence, analyze results, and ask the researcher for clarification or approval.

Decretum does not dictate the investigation sequence.

> **Decretum constrains the research space; Codex explores that space.**

### Tools and MCP — instruments, not the policy authority

Tools and MCP servers provide concrete instrumentation and operations. They do not define research authorization by themselves. A tool is usable only when compatible with the effective recipe/contract boundary and policy.

### Research state — persistent knowledge boundary

Evidence, hypotheses, experiments, findings, references, and session state are persisted locally. The research ledger preserves the semantic history of the investigation separately from the Codex conversation.

### Boundary summary

| Boundary | Question | Owner |
|---|---|---|
| **Schema** | What concepts and capabilities exist? | Decretum / LinkML |
| **Recipe** | What is authorized for this investigation? | Researcher + Decretum policy |
| **Contract** | What exact boundary was compiled? | Decretum compiler |
| **Orchestration** | What should happen next? | Codex |
| **Execution** | How is an authorized operation performed? | Codex + local tools/MCP |
| **Evidence** | What was actually observed? | Research state |
| **Findings** | What has the evidence established? | Researcher/Codex with provenance |
| **Report** | How is the result communicated? | Research workflow |
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

## Local compute and security instrumentation

Decretum treats compute providers and security instrumentation as **capabilities available to the research contract**, not as a hidden runtime dependency.

### Local compute providers

The schema can describe local execution using providers such as:

- Unix/local host
- Docker
- Podman
- Lima
- Incus
- LXC
- KVM
- Firecracker
- QEMU

This allows a recipe to express the compute boundary separately from the research logic.

For example:

```yaml
environment:
  type: local
  compute:
    provider: lima
    instance: security-research-vm
    cpu: 4
    memory_mb: 8192
    architecture: x86_64
    ephemeral: true
  sandbox:
    backend: lima
    workspace_directory: /workspace
```

Decretum describes and validates the provider boundary. It does not silently install or manage a provider. The selected provider must already be available on the researcher's machine or be provisioned through an explicitly approved external workflow.

### Security instrumentation

The schema supports a broad instrumentation vocabulary spanning:

**Kernel / eBPF**

- Sysdig
- Falco
- Tracee
- Tetragon
- bpftrace
- BCC
- libbpf
- bpftool
- eBPF exporters
- opensnoop
- execsnoop
- tcpconnect
- tcplife
- filetop
- biolatency
- runqlat
- funccount

**System / process**

- strace
- ltrace
- perf
- ftrace
- auditd
- Auditbeat
- osquery
- procmon
- psutil
- lsof
- nsenter
- capsh
- unshare

**Network**

- tcpdump
- tshark
- dumpcap
- Wireshark
- Zeek
- Suricata
- Snort
- netsniff-ng
- conntrack
- nftables
- iptables
- ethtool
- ss
- ip
- dig
- resolvectl

**Binary / malware / memory analysis**

- Volatility
- Rekall
- YARA
- ClamAV
- Ghidra
- radare2
- binwalk
- strings
- readelf
- objdump

The important distinction is that these are **instrumentation capabilities in the ontology**. A particular recipe still determines which ones are actually authorized for a specific investigation.

For example:

```yaml
instrumentation:
  tools:
    - sysdig
    - falco
    - tcpdump
    - zeek
    - yara
  events:
    - process_exec
    - network_connect
    - dns_query
    - file_write
  probes:
    - process
    - network
    - filesystem
```

This lets the security-research community extend the instrumentation vocabulary without turning every new tool into a new Decretum runtime component.

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


## Contributing

Decretum is intended to grow as a **community-driven, public security-research project**. Contributions are welcome across the schema, research recipes, validation, documentation, testing, and research workflows.

### What you can contribute

#### 1. Research recipes

Recipes are one of the easiest ways to contribute a reusable security investigation.

Good recipe contributions should:

- have a clear research objective
- declare the appropriate role and skills
- use only required capabilities
- define the tools and environment explicitly
- define expected evidence
- define completion criteria
- include relevant security-framework or threat-intelligence references when appropriate
- avoid unnecessary privileges or network access
- be safe to run in the documented local execution model

A recipe should be understandable to another researcher without requiring knowledge of Decretum's implementation.

Suggested structure:

```text
recipes/
└── <research-topic>.yaml
```

When adding a recipe, also add validation coverage where practical.

### 2. Schema contributions

The LinkML schema is the foundation of Decretum.

Schema changes should be treated as API/ontology changes because they can affect recipes, contracts, validators, and downstream research tooling.

When proposing a schema change:

1. Explain the security-research concept being added or changed.
2. Prefer reusable concepts over recipe-specific fields.
3. Keep Role → Skill → Capability → Tool → Evidence relationships explicit.
4. Consider backward compatibility with existing recipes.
5. Add or update validation tests.
6. Update the README or examples when the user-facing model changes.

Avoid adding concepts solely to support one implementation detail.

### 3. Testing

Every meaningful change should include appropriate tests.

Run the test suite from the repository root:

```bash
uv run pytest
```

For recipe or schema changes, verify at minimum:

```bash
decretum validate recipes/<your-recipe>.yaml
decretum compile recipes/<your-recipe>.yaml
```

For changes affecting the research contract, also inspect the generated contract and verify that the expected roles, skills, capabilities, policy, evidence requirements, and environment are preserved.

Contributors should add regression tests for bugs and boundary conditions rather than relying only on manual testing.

### 4. Documentation

Documentation contributions are especially valuable.

Examples include:

- new researcher workflows
- recipe authoring guides
- schema explanations
- capability examples
- security-boundary documentation
- troubleshooting
- threat-research methodology
- framework/reference integration examples

Prefer documentation that explains **how a researcher uses Decretum** rather than only describing implementation internals.

### 5. Bug reports

Please open an issue when you find a reproducible problem.

Include:

- what you were trying to do
- expected behavior
- actual behavior
- exact command used
- relevant recipe or a minimal reproduction
- validation/compiler output
- operating system and Python version
- Decretum commit or release version
- relevant logs or stack traces

For security-sensitive issues, **do not disclose exploit details or sensitive artifacts in a public issue**. Use the repository's designated private security-reporting mechanism when available.

### 6. Feature requests and design discussions

For larger changes, open a discussion or issue before implementing a substantial architectural change.

Useful proposals explain:

- the researcher problem
- the proposed behavior
- why the existing schema or workflow is insufficient
- affected schema concepts
- compatibility considerations
- security implications
- example YAML
- expected compiled contract

This helps the community review the research model before implementation details become difficult to change.

### 7. Pull requests

A good pull request should:

- describe the user/researcher problem being solved
- explain the architectural impact
- keep changes focused
- include tests
- update examples/documentation when appropriate
- avoid unrelated refactoring
- explain any schema or contract compatibility impact

For schema changes, include an example recipe demonstrating the new model.

For new recipes, include validation coverage and explain the intended research use case.

### Community principles

Decretum is designed to be **open, inspectable, reproducible, and researcher-controlled**.

Contributors are encouraged to:

- favor explicit security boundaries
- preserve evidence provenance
- make research workflows reproducible
- minimize privileges
- avoid hidden execution behavior
- distinguish observations from conclusions
- document assumptions and limitations
- keep the researcher in control of authorization decisions
- build reusable ontology and research knowledge rather than one-off automation

The goal is not simply to add more automation. The goal is to build a shared vocabulary and durable foundation for **interactive, evidence-driven security research**.

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
      - process.observe
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


## Reusable roles and skills

For larger research programs, roles and skills can be treated as reusable catalog entries instead of being invented for each experiment.

A role describes **who is performing the research** and its normal skill/capability boundary:

```yaml
role_definition:
  id: threat_researcher
  description: Security researcher investigating runtime behavior
  skills:
    - malware.behavior-analysis
  default_capabilities:
    - process.observe
    - network.capture
  allowed_tools:
    - strace
    - tetragon
    - tcpdump
    - tshark
```

The recipe can then contain a skill catalog and capability catalog. The compiler preserves these definitions and produces a normalized contract for Codex.

This gives organizations a reusable vocabulary:

- **Role** — research responsibility and baseline boundary.
- **Skill** — a composable research method.
- **Capability** — the specific operation a skill requires.
- **Tool** — an instrument that implements or supports the capability.
- **Evidence** — the observable output required from the activity.

Codex remains the orchestrator. The catalogs do not become an execution engine; they give Codex a validated vocabulary and security boundary to reason over.
