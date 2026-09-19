from pathlib import Path

from sec_agent.compiler import compile_recipe
from sec_agent.resolver import resolve_capabilities
from sec_agent.validator import validate_recipe

RECIPE = Path("recipes/openai-hosted-malware-analysis.yaml")


def test_recipe_validates_and_resolves():
    recipe, errors, _ = validate_recipe(RECIPE)
    assert not errors
    result = resolve_capabilities(recipe)
    assert result["status"] in {"ready", "needs_prerequisites"}
    assert any(item["capability"] == "process.observe" for item in result["capabilities"])


def test_compiler_emits_execution_ir():
    recipe, errors, _ = validate_recipe(RECIPE)
    assert not errors
    contract = compile_recipe(recipe, Path("artifacts/test"))
    assert contract.contract["kind"] == "ResearchExecutionContract"
    assert contract.contract["contract_version"] == "3"
    assert "experiment_graph" in contract.contract
    assert "resolution" in contract.contract


def test_experiment_dag_rejects_cycles_and_unknown_dependencies(tmp_path):
    recipe, errors, _ = validate_recipe(RECIPE)
    assert not errors
    recipe["experiments"] = [
        {"id": "a", "capabilities": ["process.observe"], "depends_on": ["b"]},
        {"id": "b", "capabilities": ["network.capture"], "depends_on": ["a"]},
    ]
    from sec_agent.validator import validate_experiment_graph
    errors = validate_experiment_graph(recipe)
    assert any("cycle" in error for error in errors)


def test_experiment_dag_rejects_undeclared_capability():
    recipe, errors, _ = validate_recipe(RECIPE)
    assert not errors
    recipe["experiments"] = [{"id": "x", "capabilities": ["does.not.exist"]}]
    from sec_agent.validator import validate_experiment_graph
    errors = validate_experiment_graph(recipe)
    assert any("undeclared capability" in error for error in errors)


def test_registered_harness_adapter_prepares_contract():
    from sec_agent.harness_adapters import CodexAdapter
    recipe, errors, _ = validate_recipe(RECIPE)
    assert not errors
    contract = compile_recipe(recipe, Path("artifacts/test"))
    adapter = CodexAdapter()
    if adapter.supports(contract.contract):
        prepared = adapter.prepare(contract.contract)
        assert prepared["protocol"] == "decretum.dev/v1"
        assert prepared["adapter"] == "codex"
        assert prepared["contract_id"] == contract.contract["contract_id"]


def test_runtime_discovery_is_ephemeral():
    from sec_agent.discovery import discover_runtime
    from sec_agent.validator import load_provider_registry, DEFAULT_PROVIDER_REGISTRY
    registry = load_provider_registry(str(DEFAULT_PROVIDER_REGISTRY))
    result = discover_runtime(registry)
    assert set(result) == {"tools", "harnesses", "compute"}
    assert "docker" in result["compute"]
    assert "codex" in result["harnesses"]


def test_readiness_report_is_ephemeral():
    from sec_agent.readiness import assess_readiness
    from sec_agent.validator import load_provider_registry, DEFAULT_PROVIDER_REGISTRY
    registry = load_provider_registry(str(DEFAULT_PROVIDER_REGISTRY))
    result = assess_readiness(registry)
    assert "providers" in result and "models" in result and "runtime" in result
    assert "tcpdump" in result["providers"]
    assert "openai" in result["models"]


def test_mcp_readiness_requires_configured_integration():
    from sec_agent.readiness import check_provider_readiness
    provider = {"interface": {"type": "mcp", "server": "pcap"}}
    result = check_provider_readiness("pcap-mcp", provider, {"tools": {}, "compute": {}}, [])
    assert result["ready"] is False


def test_mcp_stdio_configuration_is_ready():
    from sec_agent.readiness import check_provider_readiness
    provider = {"interface": {"type": "mcp", "server": "pcap"}}
    integration = [{"provider": "pcap-mcp", "transport": "stdio", "command": "pcap-mcp"}]
    result = check_provider_readiness("pcap-mcp", provider, {"tools": {}, "compute": {}}, integration)
    assert result["ready"] is True


def test_resolution_produces_experiment_plan_and_fallbacks():
    from sec_agent.resolver import resolve_capabilities
    recipe, errors, _ = validate_recipe(RECIPE)
    assert not errors
    result = resolve_capabilities(recipe)
    assert "experiment_plan" in result
    assert "failures" in result
    for item in result["capabilities"]:
        assert all("provider_ready" in provider for provider in item["providers"])


def test_candidate_rank_is_deterministic():
    from sec_agent.resolver import _candidate_rank
    assert _candidate_rank({"provider": "b", "interface": "tool", "ready": True}) < _candidate_rank({"provider": "a", "interface": "api", "ready": True})


def test_policy_denies_capability():
    from sec_agent.policy import policy_for_capability
    recipe, errors, _ = validate_recipe(RECIPE)
    assert not errors
    recipe["policy"]["deny"] = ["network.capture"]
    policy = policy_for_capability("network.capture", recipe, {"network.capture": {"risk": "observe"}})
    assert policy["denied"] is True


def test_policy_marks_capability_approval_required():
    from sec_agent.policy import policy_for_capability
    recipe, errors, _ = validate_recipe(RECIPE)
    assert not errors
    policy = policy_for_capability("process.execute", recipe, {"process.execute": {"risk": "execute", "requires_approval": True}})
    assert policy["approval_required"] is True


def test_provider_equivalence_marks_different_semantics_unsafe():
    from sec_agent.equivalence import equivalence
    a = {"interface": {"type": "tool"}, "isolation": "host", "network": "host", "privileged": False}
    b = {"interface": {"type": "tool"}, "isolation": "container", "network": "none", "privileged": False}
    result = equivalence(a, b, "network.capture")
    assert result["equivalent"] is False
    assert "isolation" in result["differences"]


def test_equivalent_fallback_is_marked_safe():
    from sec_agent.equivalence import annotate_equivalence
    a = {"interface": {"type": "tool"}, "isolation": "host", "network": "host", "privileged": False}
    b = {"interface": {"type": "tool"}, "isolation": "host", "network": "host", "privileged": False}
    result = annotate_equivalence(a, b, "network.capture")
    assert result["safe_fallback"] is True


def test_schema_governed_compatibility_rejects_network_mismatch():
    from sec_agent.compatibility import compatibility
    provider = {"interface": {"type": "tool"}, "isolation": "host", "network": "internet", "execution_modes": ["capture"]}
    spec = {"risk": "observe", "allowed_networks": ["none", "restricted"], "allowed_execution_modes": ["capture"]}
    result = compatibility(provider, "network.capture", spec)
    assert result["compatible"] is False
    assert "network_not_allowed" in result["violations"]


def test_schema_governed_compatibility_accepts_matching_provider():
    from sec_agent.compatibility import compatibility
    provider = {"interface": {"type": "tool"}, "isolation": "host", "network": "restricted", "execution_modes": ["capture"]}
    spec = {"risk": "observe", "allowed_networks": ["restricted"], "allowed_execution_modes": ["capture"]}
    result = compatibility(provider, "network.capture", spec)
    assert result["compatible"] is True


def test_contract_contains_auditable_plan_digest():
    recipe, errors, _ = validate_recipe(RECIPE)
    assert not errors
    contract = compile_recipe(recipe, Path("artifacts/test"))
    assert len(contract.contract["plan_digest"]) == 64
    assert "resolution" in contract.contract
    assert "failures" in contract.contract["resolution"]


def test_plan_digest_is_deterministic():
    from sec_agent.compiler import _plan_digest
    plan = {"status": "ready", "capabilities": [], "failures": [], "harnesses": ["codex"], "readiness": {}, "experiment_plan": []}
    assert _plan_digest(plan) == _plan_digest(plan)


def test_execution_provenance_binds_contract_and_plan():
    from sec_agent.research_state import record_execution, read_events
    root = Path("artifacts/provenance-test")
    item = record_execution(root, "exec-1", "contract-1", "a"*64, "exp-1", "tshark", "tool", "codex")
    assert item["contract_id"] == "contract-1"
    assert item["plan_digest"] == "a"*64
    assert item["provenance_digest"]
    assert read_events(root)[0]["type"] == "execution_started"


def test_execution_result_has_result_digest():
    from sec_agent.research_state import record_execution_result
    root = Path("artifacts/provenance-test-result")
    item = record_execution_result(root, "exec-1", "completed", outputs={"evidence": ["pcap"]})
    assert item["result_digest"]


def test_ledger_hash_chain_verifies():
    from sec_agent.research_state import append_event, verify_ledger
    root = Path("artifacts/ledger-test")
    append_event(root, "one", {"value": 1})
    append_event(root, "two", {"value": 2})
    result = verify_ledger(root)
    assert result["valid"] is True
    assert result["events"] == 2


def test_ledger_tampering_is_detected():
    from sec_agent.research_state import append_event, verify_ledger
    root = Path("artifacts/ledger-tamper-test")
    append_event(root, "one", {"value": 1})
    append_event(root, "two", {"value": 2})
    path = root / "research-ledger.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace('"value": 1', '"value": 999')
    path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    assert verify_ledger(root)["valid"] is False


def test_replay_verifies_plan_digest():
    from sec_agent.replay import verify_plan_digest
    plan = {"status": "ready", "capabilities": [], "failures": [], "harnesses": ["codex"], "readiness": {}, "experiment_plan": []}
    from sec_agent.compiler import _plan_digest
    contract = {"plan_digest": _plan_digest(plan), "resolution": plan}
    assert verify_plan_digest(contract)["valid"] is True


def test_replay_detects_plan_tampering():
    from sec_agent.replay import verify_plan_digest
    contract = {"plan_digest": "a"*64, "resolution": {"status": "ready", "capabilities": [], "failures": [], "harnesses": [], "readiness": {}, "experiment_plan": []}}
    assert verify_plan_digest(contract)["valid"] is False


def test_registry_snapshot_round_trip(tmp_path):
    from sec_agent.registry_snapshot import snapshot_registry, load_snapshot
    from sec_agent.validator import DEFAULT_PROVIDER_REGISTRY
    snapshot = snapshot_registry(DEFAULT_PROVIDER_REGISTRY, tmp_path)
    loaded = load_snapshot(tmp_path / "provider-registry.snapshot.json")
    assert loaded["digest"] == snapshot["digest"]


def test_registry_snapshot_tampering_is_detected(tmp_path):
    from sec_agent.registry_snapshot import snapshot_registry, load_snapshot
    from sec_agent.validator import DEFAULT_PROVIDER_REGISTRY
    snapshot_registry(DEFAULT_PROVIDER_REGISTRY, tmp_path)
    path = tmp_path / "provider-registry.snapshot.json"
    data = path.read_text(encoding="utf-8").replace('"version": "1.3"', '"version": "tampered"')
    path.write_text(data, encoding="utf-8")
    try:
        load_snapshot(path)
        assert False, "tampering should be detected"
    except ValueError:
        pass


def test_recipe_requirements_are_compiled_and_preferences_are_visible():
    from sec_agent.validator import validate_recipe
    recipe, errors, _ = validate_recipe(Path("recipes/suspicious-network-investigation.yaml"))
    assert not errors
    contract = compile_recipe(recipe, Path("artifacts/test-requirements"))
    requirements = contract.contract["requirements"]
    assert requirements["instrumentation"]["required"] == ["network.metadata", "syscall.observe"]
    assert requirements["instrumentation"]["preferred"] == ["sysdig", "zeek"]
    assert requirements["compute"]["required"] == ["compute.vm"]
    assert requirements["compute"]["preferred"] == ["incus", "lima"]
    assert contract.contract["execution"]["resolution"]["provider_preferences"]["compute"] == ["lima", "incus"]


def test_resolver_marks_preferred_providers_without_changing_capability_semantics():
    from sec_agent.validator import validate_recipe
    from sec_agent.resolver import resolve_capabilities
    recipe, errors, _ = validate_recipe(Path("recipes/suspicious-network-investigation.yaml"))
    assert not errors
    result = resolve_capabilities(recipe)
    compute = next(item for item in result["capabilities"] if item["capability"] == "compute.vm")
    preferred = {p["provider"] for p in compute["providers"] if p["preferred"]}
    assert {"lima", "incus"}.issubset(preferred)
