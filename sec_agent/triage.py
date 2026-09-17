"""Interactive offline triage REPL."""
from __future__ import annotations
from pathlib import Path
import cmd
import hashlib

class TriageShell(cmd.Cmd):
    intro = "Decretum offline triage. Commands: list, hash <file>, quit"
    prompt = "decretum> "
    def __init__(self, root: Path):
        super().__init__(); self.root = root.resolve()
    def do_list(self, _: str) -> None:
        for p in sorted(self.root.rglob("*")):
            if p.is_file(): print(p.relative_to(self.root))
    def do_hash(self, arg: str) -> None:
        p = (self.root / arg).resolve()
        if self.root not in p.parents or not p.is_file(): print("invalid artifact"); return
        print(hashlib.sha256(p.read_bytes()).hexdigest(), p.relative_to(self.root))
    def do_quit(self, _: str) -> bool: return True
    do_exit = do_quit

def run_triage(artifacts: Path) -> None:
    if not artifacts.is_dir(): raise FileNotFoundError(artifacts)
    TriageShell(artifacts).cmdloop()
