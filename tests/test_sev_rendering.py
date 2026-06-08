import pandas as pd
from src.services.reconciliation import reconcile_data

def test_sev_propagation_in_reconciliation():
    # Arrange: Excel sheet data (no SEV field)
    df_ex = pd.DataFrame([
        {
            "Placa": "ABC1D23",
            "Data": "2026-06-05",
            "Peso Bruto": 50000.0,
            "Tara": 20000.0,
            "Produto": "LITIO",
            "Cliente": "CLIENTE A"
        },
        {
            "Placa": "XYZ9W87",
            "Data": "2026-06-05",
            "Peso Bruto": 60000.0,
            "Tara": 22000.0,
            "Produto": "MILHO",
            "Cliente": "CLIENTE B"
        }
    ])

    # Arrange: PDF parsed data (with SEV field)
    df_pdf = pd.DataFrame([
        {
            "Placa": "ABC1D23",
            "Data": "2026-06-05",
            "Peso Bruto": 50000.0,
            "Tara": 20000.0,
            "SEV": "663928",
            "Tipo Carga": "LITIO"
        },
        {
            # A discrepancy in weights to trigger divergencias with SEV
            "Placa": "XYZ9W87",
            "Data": "2026-06-05",
            "Peso Bruto": 59900.0,  # 100kg difference
            "Tara": 22000.0,
            "SEV": "663929",
            "Tipo Carga": "MILHO"
        }
    ])

    # Act
    result = reconcile_data(df_ex, df_pdf)

    # Assert: Verify that the OK match has the correct SEV
    ok_list = result.get("ok", [])
    assert len(ok_list) == 1
    assert ok_list[0]["Placa"] == "ABC1D23"
    assert ok_list[0]["SEV"] == "663928"

    # Assert: Verify that the Divergence match has the correct SEV
    div_list = result.get("divergencias", [])
    # We should have two here because of the mismatch (one Falta no PDF and one Falta no Excel)
    # Since weights don't match, match_trips matches XYZ9W87 by approximation as "Diferença de Peso"
    assert len(div_list) == 1
    assert div_list[0]["Placa"] == "XYZ9W87"
    assert div_list[0]["SEV"] == "663929"
    assert "Diferença de Peso" in div_list[0]["Status"]

def test_sev_propagation_in_plate_typo():
    # Arrange: Excel sheet data (no SEV field)
    df_ex = pd.DataFrame([
        {
            "Placa": "ABC1D23",  # Typo in Excel: ABC1D23 instead of ABC1D24
            "Data": "2026-06-05",
            "Peso Bruto": 50000.0,
            "Tara": 20000.0,
            "Produto": "LITIO",
            "Cliente": "CLIENTE A"
        }
    ])

    # Arrange: PDF parsed data (with SEV field)
    df_pdf = pd.DataFrame([
        {
            "Placa": "ABC1D24",
            "Data": "2026-06-05",
            "Peso Bruto": 50000.0,
            "Tara": 20000.0,
            "SEV": "663930",
            "Tipo Carga": "LITIO"
        }
    ])

    # Act
    result = reconcile_data(df_ex, df_pdf)

    # Assert
    div_list = result.get("divergencias", [])
    assert len(div_list) == 1
    assert div_list[0]["Status"] == "Erro de Placa"
    assert div_list[0]["SEV"] == "663930"
