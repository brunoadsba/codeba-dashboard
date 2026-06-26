from datetime import datetime
import pandas as pd
from src.services.reconciliation import reconcile_data


def test_viagens_ok_no_dia_injected_on_divergence():
    """Se uma placa tem viagem OK e outra divergente no dia, deve injetar viagens_ok_no_dia."""
    # Excel possui apenas a primeira viagem da placa ABC1D23
    df_ex = pd.DataFrame([
        {
            "Placa": "ABC1D23",
            "Data": datetime(2026, 6, 18, 11, 0),
            "Peso Bruto": 50000,
            "Tara": 20000,
            "Produto": "NIQUEL",
            "Cliente": "Atlantic Nickel",
        }
    ])
    
    # PDF possui duas viagens da placa ABC1D23 no mesmo dia (18/06/2026)
    df_p = pd.DataFrame([
        {
            "Placa": "ABC1D23",
            "Data": datetime(2026, 6, 18, 11, 0),
            "Peso Bruto": 50000,
            "Tara": 20000,
            "SEV": "664201",
        },
        {
            "Placa": "ABC1D23",
            "Data": datetime(2026, 6, 18, 17, 30),
            "Peso Bruto": 52000,
            "Tara": 20500,
            "SEV": "664223",
        }
    ])

    result = reconcile_data(df_ex, df_p)

    # Deve conter 1 viagem OK
    assert len(result["ok"]) == 1
    assert result["ok"][0]["Placa"] == "ABC1D23"
    assert result["ok"][0]["SEV"] == "664201"

    # Deve conter 1 divergência
    assert len(result["divergencias"]) == 1
    div_item = result["divergencias"][0]
    assert div_item["Placa"] == "ABC1D23"
    assert div_item["SEV"] == "664223"
    assert div_item["Status"] == "Falta no Excel"
    
    # Nova chave viagens_ok_no_dia deve ser 1
    assert div_item.get("viagens_ok_no_dia") == 1


def test_viagens_ok_no_dia_not_injected_when_no_ok_trips():
    """Se uma placa tem apenas divergências no dia e nenhuma viagem OK, viagens_ok_no_dia não deve estar presente."""
    df_ex = pd.DataFrame([]) # Excel vazio
    df_p = pd.DataFrame([
        {
            "Placa": "ABC1D23",
            "Data": datetime(2026, 6, 18, 17, 30),
            "Peso Bruto": 52000,
            "Tara": 20500,
            "SEV": "664223",
        }
    ])

    result = reconcile_data(df_ex, df_p)

    assert len(result["ok"]) == 0
    assert len(result["divergencias"]) == 1
    div_item = result["divergencias"][0]
    
    # Como não há viagens OK, a chave viagens_ok_no_dia não deve ser inserida
    assert "viagens_ok_no_dia" not in div_item
