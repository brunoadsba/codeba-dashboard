"""
Persistência SQLite de auditorias processadas.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.services.analytics import compute_period_bounds

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_runs (
    id            TEXT PRIMARY KEY,
    created_at    TEXT NOT NULL,
    period_start  TEXT,
    period_end    TEXT,
    file_names    TEXT NOT NULL,
    resumo        TEXT NOT NULL,
    payload       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_runs_created_at ON audit_runs(created_at DESC);
"""


def init_db(db_path: str | Path) -> None:
    """Cria tabela se não existir."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(_SCHEMA)


def _ensure_db(db_path: str | Path) -> None:
    init_db(db_path)


def save_audit_run(
    db_path: str | Path,
    result: dict[str, Any],
    file_names: list[str],
    run_id: str | None = None,
) -> dict[str, str]:
    """
    Persiste resultado completo da auditoria.

    Returns:
        dict com run_id e created_at
    """
    _ensure_db(db_path)
    run_id = run_id or uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()
    ok_list = result.get("ok", [])
    div_list = result.get("divergencias", [])
    period_start, period_end = compute_period_bounds(ok_list, div_list)
    resumo = result.get("resumo", {})

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO audit_runs
                (id, created_at, period_start, period_end, file_names, resumo, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                created_at,
                period_start,
                period_end,
                json.dumps(file_names, ensure_ascii=False),
                json.dumps(resumo, ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
            ),
        )
    return {"run_id": run_id, "created_at": created_at}


def list_audit_runs(
    db_path: str | Path,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Lista runs com metadados leves."""
    _ensure_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute("SELECT COUNT(*) FROM audit_runs").fetchone()[0]
        rows = conn.execute(
            """
            SELECT id, created_at, period_start, period_end, file_names, resumo
            FROM audit_runs
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    runs = []
    for row in rows:
        runs.append({
            "id": row["id"],
            "created_at": row["created_at"],
            "period_start": row["period_start"],
            "period_end": row["period_end"],
            "file_names": json.loads(row["file_names"]),
            "resumo": json.loads(row["resumo"]),
        })
    return {"runs": runs, "total": total}


def get_audit_run(db_path: str | Path, run_id: str) -> dict[str, Any] | None:
    """Carrega payload completo de um run."""
    _ensure_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT payload, created_at FROM audit_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if not row:
        return None
    payload = json.loads(row["payload"])
    payload["run_id"] = run_id
    payload["created_at"] = row["created_at"]
    return payload


def delete_audit_run(db_path: str | Path, run_id: str) -> bool:
    """Remove um run. Retorna True se existia."""
    _ensure_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute("DELETE FROM audit_runs WHERE id = ?", (run_id,))
        return cur.rowcount > 0
