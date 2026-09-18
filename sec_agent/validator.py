"""LinkML-aligned recipe validation and capability preflight."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml

ROLE_VALUES = {"threat_researcher","supply_chain_auditor","detection_engineer","vulnerability_exploit_researcher"}
TOOLS = {"tetragon","bpftrace","strace","tcpdump","tshark"}

def load_recipe(path: Path) -> dict[str, Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError("Recipe root must be a YAML mapping")
    return value

def structural_validate(recipe: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"id","name","version","role","objective","environment","policy","evidence","completion"}
    errors.extend(f"missing required field: {key}" for key in sorted(required - recipe.keys()))
    if recipe.get("role") not in ROLE_VALUES: errors.append(f"invalid role: {recipe.get('role')!r}")
    environment = recipe.get("environment")
    if not isinstance(environment, dict): errors.append("environment must be a mapping")
    else:
        if environment.get("type","openai_hosted") not in {"openai_hosted","self_hosted"}: errors.append("environment.type must be openai_hosted or self_hosted")
        if environment.get("privileged",False): errors.append("privileged execution is prohibited by default")
        if environment.get("host_mounts",False): errors.append("host filesystem mounts are prohibited")
    policy = recipe.get("policy")
    if not isinstance(policy, dict): errors.append("policy must be a mapping")
    else:
        for key in ("allow","deny"):
            if policy.get(key) is not None and not isinstance(policy[key],list): errors.append(f"policy.{key} must be a list")
    evidence = recipe.get("evidence")
    if not isinstance(evidence,dict): errors.append("evidence must be a mapping")
    elif not evidence.get("required"): errors.append("evidence.required must be non-empty")
    completion = recipe.get("completion")
    if not isinstance(completion,dict): errors.append("completion must be a mapping")
    elif completion.get("report_required",True) is not True: errors.append("completion.report_required must remain true")
    instrumentation = recipe.get("instrumentation",{})
    if instrumentation is not None and not isinstance(instrumentation,dict): errors.append("instrumentation must be a mapping")
    elif isinstance(instrumentation,dict):
        for tool in instrumentation.get("tools",[]) or []:
            if tool not in TOOLS: errors.append(f"unsupported instrumentation tool: {tool!r}")
    return errors

def preflight(recipe: dict[str, Any]) -> list[str]:
    if recipe.get("environment",{}).get("type","openai_hosted") == "openai_hosted": return []
    return ["self_hosted environment requires a configured Codex executor"]

def validate_recipe(path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    recipe = load_recipe(path)
    errors = structural_validate(recipe)
    return recipe, errors, preflight(recipe) if not errors else []
