import pytest

from src.services.persistence import (
    delete_audit_run,
    get_audit_run,
    init_db,
    list_audit_runs,
    save_audit_run,
)


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    init_db(path)
    return path


def _sample_result():
    return {
        "resumo": {"total_processado": 2, "ok": 1, "divergencias": 1},
        "ok": [{
            "Placa": "ABC1D23",
            "Data": "05/06/2026",
            "Produto": "LITIO",
            "Peso Liquido": 38300,
            "Peso Bruto": 59160,
            "Tara": 20860,
            "Cliente": "Cliente A",
            "Detalhe": "Pesagem exata",
        }],
        "divergencias": [{
            "Placa": "XYZ9W87",
            "Data": "06/06/2026",
            "Produto": "MANGANES",
            "Status": "Falta no Excel",
            "Detalhe": "teste",
            "Peso Bruto": 60000,
            "Tara": 22000,
        }],
        "produtos_detectados": ["LITIO"],
        "clientes_por_produto": {"LITIO": ["Cliente A"]},
        "volume": {"records": [], "meta": {}},
    }


def test_save_and_load(db_path):
    result = _sample_result()
    meta = save_audit_run(db_path, result, ["litio.xlsx", "rel.pdf"], run_id="test-run-1")
    assert meta["run_id"] == "test-run-1"
    assert "created_at" in meta

    loaded = get_audit_run(db_path, "test-run-1")
    assert loaded is not None
    assert loaded["run_id"] == "test-run-1"
    assert len(loaded["ok"]) == 1
    assert loaded["resumo"]["total_processado"] == 2


def test_list_runs(db_path):
    result = _sample_result()
    save_audit_run(db_path, result, ["a.xlsx"], run_id="run-a")
    save_audit_run(db_path, result, ["b.pdf"], run_id="run-b")

    listing = list_audit_runs(db_path, limit=10)
    assert listing["total"] == 2
    assert len(listing["runs"]) == 2
    ids = {r["id"] for r in listing["runs"]}
    assert ids == {"run-a", "run-b"}


def test_delete_run(db_path):
    result = _sample_result()
    save_audit_run(db_path, result, ["a.xlsx"], run_id="to-delete")
    assert delete_audit_run(db_path, "to-delete") is True
    assert get_audit_run(db_path, "to-delete") is None
    assert delete_audit_run(db_path, "to-delete") is False


def test_init_db_creates_file(tmp_path):
    path = tmp_path / "nested" / "auditoria.db"
    init_db(path)
    assert path.exists()
