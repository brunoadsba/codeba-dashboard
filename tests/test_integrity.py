import pytest
import pandas as pd
from src.services.reconciliation import calculate_integrity_hash, reconcile_data

def test_integrity_hash_determinism():
    ok_list = [
        {
            "Placa": "ABC1234",
            "Data": "25/06/2026 08:00:00",
            "Peso Bruto": 45000.0,
            "Tara": 15000.0,
            "Peso Liquido": 30000.0,
            "Produto": "MILHO",
            "SEV": "10001",
            "Status": "OK"
        }
    ]
    divergencias = [
        {
            "Placa": "XYZ5678",
            "Data": "25/06/2026 09:00:00",
            "Peso Bruto": 42000.0,
            "Tara": 12000.0,
            "Peso Liquido": 30000.0,
            "Produto": "LÍTIO",
            "SEV": "10002",
            "Status": "Divergência de Peso"
        }
    ]
    notas_informativas = []

    # Calculate hash multiple times
    hash1 = calculate_integrity_hash(ok_list, divergencias, notas_informativas)
    hash2 = calculate_integrity_hash(ok_list, divergencias, notas_informativas)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex digest length

    # Different order of same elements must yield same hash due to internal sorting
    ok_list_reversed = list(reversed(ok_list))
    hash3 = calculate_integrity_hash(ok_list_reversed, divergencias, notas_informativas)
    assert hash1 == hash3

    # Mutating any field must change the hash
    ok_list_mutated = [dict(ok_list[0], **{"Peso Bruto": 45001.0})]
    hash_mutated = calculate_integrity_hash(ok_list_mutated, divergencias, notas_informativas)
    assert hash1 != hash_mutated


def test_reconciliation_discarded_records():
    # Excel with some invalid entries (empty placa, invalid date)
    df_excel = pd.DataFrame([
        # Valid row
        {"Linha": 1, "Aba": "Sheet1", "Placa": "ABC1234", "Data": "25/06/2026", "Peso Bruto": 45000.0, "Tara": 15000.0, "Produto": "MILHO"},
        # Invalid Placa (empty after clean)
        {"Linha": 2, "Aba": "Sheet1", "Placa": "   ", "Data": "25/06/2026", "Peso Bruto": 40000.0, "Tara": 12000.0, "Produto": "MILHO"},
        # Invalid Date
        {"Linha": 3, "Aba": "Sheet1", "Placa": "XYZ5678", "Data": "data_invalida", "Peso Bruto": 40000.0, "Tara": 12000.0, "Produto": "MILHO"},
    ])

    # PDF with some invalid entries
    df_pdf = pd.DataFrame([
        # Valid row
        {"SEV": "10001", "Placa": "ABC1234", "Data": "25/06/2026 08:00:00", "Peso Bruto": 45000.0, "Tara": 15000.0, "Tipo Carga": "MILHO"},
        # Invalid Placa
        {"SEV": "10002", "Placa": "", "Data": "25/06/2026 08:30:00", "Peso Bruto": 45000.0, "Tara": 15000.0, "Tipo Carga": "MILHO"},
        # Invalid Date
        {"SEV": "10003", "Placa": "XYZ5678", "Data": "99/99/9999", "Peso Bruto": 45000.0, "Tara": 15000.0, "Tipo Carga": "MILHO"},
    ])

    res = reconcile_data(df_excel, df_pdf)

    # Must contain discarded warnings
    assert "avisos" in res
    assert "registros_descartados" in res["avisos"]
    
    excel_discarded = res["avisos"]["registros_descartados"]["excel"]
    pdf_discarded = res["avisos"]["registros_descartados"]["pdf"]

    assert len(excel_discarded) == 2
    # Verify first invalid excel row (empty plate)
    assert excel_discarded[0]["Linha"] == 2
    assert "Placa" in excel_discarded[0]["Motivo"]

    # Verify second invalid excel row (invalid date)
    assert excel_discarded[1]["Linha"] == 3
    assert "Data" in excel_discarded[1]["Motivo"]

    assert len(pdf_discarded) == 2
    # Verify first invalid pdf row (empty plate)
    assert pdf_discarded[0]["SEV"] == "10002"
    assert "Placa" in pdf_discarded[0]["Motivo"]

    # Verify second invalid pdf row (invalid date)
    assert pdf_discarded[1]["SEV"] == "10003"
    assert "Data" in pdf_discarded[1]["Motivo"]
