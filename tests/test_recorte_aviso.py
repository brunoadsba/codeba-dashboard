from datetime import datetime

import pandas as pd

from src.services.reconciliation import reconcile_data


def test_recorte_aviso_excel_fora_intersecao():
    """Excel com data fora do PDF deve gerar aviso com datas ignoradas."""
    df_ex = pd.DataFrame([
        {"Placa": "ABC1D23", "Data": datetime(2026, 6, 5), "Peso Bruto": 50000, "Tara": 20000, "Produto": "LITIO", "Cliente": "A"},
        {"Placa": "XYZ9W87", "Data": datetime(2026, 6, 15), "Peso Bruto": 60000, "Tara": 22000, "Produto": "LITIO", "Cliente": "A"},
    ])
    df_p = pd.DataFrame([
        {"Placa": "ABC1D23", "Data": datetime(2026, 6, 5), "Peso Bruto": 50000, "Tara": 20000, "SEV": "1"},
        {"Placa": "DEF4G56", "Data": datetime(2026, 6, 6), "Peso Bruto": 55000, "Tara": 21000, "SEV": "2"},
    ])

    result = reconcile_data(df_ex, df_p)

    assert "avisos" in result
    recorte = result["avisos"]["recorte_periodo"]
    assert recorte["excel_ignorados"]["total"] == 1
    assert "15/06/2026" in recorte["excel_ignorados"]["datas"]
    assert recorte["periodo_utilizado"]["inicio"] == "05/06/2026"
    assert recorte["periodo_utilizado"]["fim"] == "06/06/2026"

    datas_ok = {item["Data"] for item in result["ok"]}
    datas_div = {item["Data"] for item in result["divergencias"]}
    assert "15/06/2026" not in datas_ok
    assert "15/06/2026" not in datas_div


def test_sem_aviso_quando_periodos_coincidem():
    df_ex = pd.DataFrame([
        {"Placa": "ABC1D23", "Data": "05/06/2026", "Peso Bruto": 50000, "Tara": 20000, "Produto": "LITIO", "Cliente": "A"},
    ])
    df_p = pd.DataFrame([
        {"Placa": "ABC1D23", "Data": "05/06/2026", "Peso Bruto": 50000, "Tara": 20000, "SEV": "1"},
    ])

    result = reconcile_data(df_ex, df_p)
    assert "avisos" not in result
