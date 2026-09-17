"""Conservative rule generation from observed syscall sequences."""
from __future__ import annotations
import re

def sigma_from_syscalls(sequence: list[str], title: str = "Observed syscall sequence") -> dict:
    """Generate a Sigma-like detection rule; input is treated as data, not executable code."""
    names = [x for x in sequence if re.fullmatch(r"[A-Za-z0-9_]+", x)]
    if not names: raise ValueError("sequence contains no valid syscall names")
    return {
        "title": title,
        "status": "experimental",
        "logsource": {"category": "process_creation"},
        "detection": {"selection": {"Syscall|contains": names}, "condition": "selection"},
        "level": "medium",
    }

def yara_strings(values: list[str]) -> str:
    safe = [v.replace('\\', '\\\\').replace('"', '\\"') for v in values if v]
    return "rule decretum_observation { strings: " + " ".join(f'$s{i} = "{v}" ascii' for i,v in enumerate(safe)) + " condition: any of them }"
