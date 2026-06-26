"""Testes para detecção de erros de digitação de data no Excel.

Cenário RPJ0I50: O balanceiro digitou 18-mar ao invés de 18-jun na planilha.
O sistema deve detectar que a placa+pesos existem nos registros descartados
e enriquecer a divergência com os metadados de rastreamento.
"""

from datetime import datetime

import pandas as pd

from src.services.reconciliation import reconcile_data


def _make_excel_df(rows):
    """Helper: cria DataFrame Excel com colunas padrão."""
    return pd.DataFrame(rows)


def _make_pdf_df(rows):
    """Helper: cria DataFrame PDF com colunas padrão."""
    return pd.DataFrame(rows)


def test_detect_date_typo_basic():
    """Registro Excel com data errada (março vs junho) deve ser detectado
    como possível erro de digitação quando a placa e pesos batem."""

    # Excel: 2 registros — um com data correta (18/jun), outro com data errada (18/mar)
    df_ex = _make_excel_df([
        {
            "Placa": "ABC1D23", "Data": datetime(2026, 6, 18, 11, 5),
            "Peso Bruto": 50000, "Tara": 20000, "Produto": "NÍQUEL",
            "Linha": 5, "Aba": "Plan1", "Arquivo": "NÍQUEL- ATLANTIC NICKEL.xlsx",
        },
        {
            "Placa": "RPJ0I50", "Data": datetime(2026, 3, 18, 17, 38),  # ← DATA ERRADA
            "Peso Bruto": 45000, "Tara": 18000, "Produto": "NÍQUEL",
            "Linha": 10, "Aba": "Plan5", "Arquivo": "NÍQUEL- ATLANTIC NICKEL.xlsx",
        },
    ])

    # PDF: 2 registros no dia 18/jun
    df_p = _make_pdf_df([
        {
            "Placa": "ABC1D23", "Data": datetime(2026, 6, 18, 11, 5),
            "Peso Bruto": 50000, "Tara": 20000, "SEV": "11048",
        },
        {
            "Placa": "RPJ0I50", "Data": datetime(2026, 6, 18, 17, 38),
            "Peso Bruto": 45000, "Tara": 18000, "SEV": "11049",
        },
    ])

    result = reconcile_data(df_ex, df_p)

    assert "error" not in result, f"Erro inesperado: {result.get('error')}"

    # Deve haver 1 OK (ABC1D23) e 1 divergência (RPJ0I50)
    assert result["resumo"]["ok"] >= 1
    assert result["resumo"]["divergencias"] >= 1

    # Encontrar a divergência do RPJ0I50
    div_rpj = [d for d in result["divergencias"] if d.get("Placa") == "RPJ0I50"]
    assert len(div_rpj) == 1, f"Esperava 1 divergência para RPJ0I50, encontrou {len(div_rpj)}"

    d = div_rpj[0]
    # Deve ter os metadados de erro de data
    assert d.get("linha_erro_data") == 10, f"Linha errada: {d.get('linha_erro_data')}"
    assert d.get("aba_erro_data") == "Plan5", f"Aba errada: {d.get('aba_erro_data')}"
    assert d.get("arquivo_erro_data") == "NÍQUEL- ATLANTIC NICKEL.xlsx"
    assert "18/03/2026" in d.get("data_errada_excel", ""), f"Data errada não encontrada: {d.get('data_errada_excel')}"
    assert "Erro de Data" in d.get("Detalhe", "") or "erro de digitação" in d.get("Detalhe", "").lower(), \
        f"Detalhe não menciona erro: {d.get('Detalhe')}"


def test_no_false_positive_when_plate_not_in_discarded():
    """Não deve criar alerta de erro de data se a placa do PDF não estiver
    nos registros descartados."""

    df_ex = _make_excel_df([
        {
            "Placa": "ABC1D23", "Data": datetime(2026, 6, 18),
            "Peso Bruto": 50000, "Tara": 20000, "Produto": "LITIO",
            "Linha": 3, "Aba": "Plan1", "Arquivo": "LITIO.xlsx",
        },
        # Registro com data fora do período (será descartado) — placa diferente
        {
            "Placa": "QQQ9Q99", "Data": datetime(2026, 3, 18),
            "Peso Bruto": 60000, "Tara": 22000, "Produto": "LITIO",
            "Linha": 7, "Aba": "Plan1", "Arquivo": "LITIO.xlsx",
        },
    ])

    df_p = _make_pdf_df([
        {
            "Placa": "ABC1D23", "Data": datetime(2026, 6, 18),
            "Peso Bruto": 50000, "Tara": 20000, "SEV": "1",
        },
        {
            "Placa": "ZZZ0Z00", "Data": datetime(2026, 6, 18),
            "Peso Bruto": 55000, "Tara": 21000, "SEV": "2",
        },
    ])

    result = reconcile_data(df_ex, df_p)
    assert "error" not in result

    for d in result["divergencias"]:
        assert d.get("linha_erro_data") is None, \
            f"Falso positivo de erro de data detectado para {d.get('Placa')}"


def test_no_alert_when_weights_differ_too_much():
    """Mesma placa nos descartados, mas pesos muito diferentes → não deve
    gerar alerta de erro de data."""

    df_ex = _make_excel_df([
        {
            "Placa": "ABC1D23", "Data": datetime(2026, 6, 18),
            "Peso Bruto": 50000, "Tara": 20000, "Produto": "LITIO",
            "Linha": 3, "Aba": "Plan1", "Arquivo": "LITIO.xlsx",
        },
        {
            "Placa": "RPJ0I50", "Data": datetime(2026, 3, 18),  # data errada
            "Peso Bruto": 99000, "Tara": 50000, "Produto": "LITIO",  # pesos MUITO diferentes
            "Linha": 10, "Aba": "Plan5", "Arquivo": "LITIO.xlsx",
        },
    ])

    df_p = _make_pdf_df([
        {
            "Placa": "ABC1D23", "Data": datetime(2026, 6, 18),
            "Peso Bruto": 50000, "Tara": 20000, "SEV": "1",
        },
        {
            "Placa": "RPJ0I50", "Data": datetime(2026, 6, 18),
            "Peso Bruto": 45000, "Tara": 18000, "SEV": "2",
        },
    ])

    result = reconcile_data(df_ex, df_p)
    assert "error" not in result

    div_rpj = [d for d in result["divergencias"] if d.get("Placa") == "RPJ0I50"]
    for d in div_rpj:
        assert d.get("linha_erro_data") is None, \
            "Não deveria gerar alerta quando pesos diferem muito"


def test_date_typo_within_weight_tolerance():
    """Placa e pesos com pequena variação (< 100 kg) devem ser detectados."""

    df_ex = _make_excel_df([
        {
            "Placa": "ABC1D23", "Data": datetime(2026, 6, 18),
            "Peso Bruto": 50000, "Tara": 20000, "Produto": "LITIO",
            "Linha": 3, "Aba": "Plan1", "Arquivo": "TEST.xlsx",
        },
        {
            "Placa": "RPJ0I50", "Data": datetime(2026, 3, 18),  # data errada
            "Peso Bruto": 45020, "Tara": 18010, "Produto": "LITIO",  # +30 total
            "Linha": 10, "Aba": "Plan5", "Arquivo": "TEST.xlsx",
        },
    ])

    df_p = _make_pdf_df([
        {
            "Placa": "ABC1D23", "Data": datetime(2026, 6, 18),
            "Peso Bruto": 50000, "Tara": 20000, "SEV": "1",
        },
        {
            "Placa": "RPJ0I50", "Data": datetime(2026, 6, 18),
            "Peso Bruto": 45000, "Tara": 18000, "SEV": "2",
        },
    ])

    result = reconcile_data(df_ex, df_p)
    assert "error" not in result

    div_rpj = [d for d in result["divergencias"] if d.get("Placa") == "RPJ0I50"]
    assert len(div_rpj) == 1
    assert div_rpj[0].get("linha_erro_data") == 10, \
        "Deveria detectar erro de data com variação de peso dentro da tolerância"
