"""SQLite-backed knowledge graph primitives."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path

class GraphStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY, kind TEXT, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS mappings (finding_id TEXT, framework TEXT, reference TEXT)")
    def _connect(self) -> sqlite3.Connection: return sqlite3.connect(self.path)
    def put_finding(self, finding_id: str, kind: str, payload: dict) -> None:
        with self._connect() as db: db.execute("INSERT OR REPLACE INTO findings VALUES (?,?,?)", (finding_id, kind, json.dumps(payload, sort_keys=True)))
    def map_reference(self, finding_id: str, framework: str, reference: str) -> None:
        with self._connect() as db: db.execute("INSERT INTO mappings VALUES (?,?,?)", (finding_id, framework, reference))
    def get(self, finding_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT kind,payload FROM findings WHERE id=?", (finding_id,)).fetchone()
        return None if row is None else {"kind": row[0], "payload": json.loads(row[1])}
