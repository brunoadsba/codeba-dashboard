import pytest

from src.services.analytics import (
    build_volume_records,
    compute_period_bounds,
    net_weight_kg,
    normalize_product,
)


def test_normalize_product():
    assert normalize_product("LITIO (Deduzido)") == "LITIO"
    assert normalize_product("Não Identificado") == "Outros"
    assert normalize_product("Ambíguo (LITIO/MANGANES)") == "Outros"
    assert normalize_product("") == "Outros"
    assert normalize_product("ÓXIDO DE MAGNÉSIO") == "ÓXIDO DE MAGNÉSIO"


def test_net_weight_ok():
    item = {"Peso Liquido": 38300, "Peso Bruto": 59160, "Tara": 20860}
    assert net_weight_kg(item, is_ok=True) == 38300


def test_net_weight_divergencia():
    item = {"Peso Bruto": 50000, "Tara": 20000}
    assert net_weight_kg(item, is_ok=False) == 30000


def test_net_weight_missing():
    assert net_weight_kg({}, is_ok=True) is None


def test_build_volume_records():
    ok = [{
        "Placa": "ABC1D23",
        "Data": "05/06/2026",
        "Produto": "LITIO",
        "Peso Liquido": 38300,
        "Peso Bruto": 59160,
        "Tara": 20860,
    }]
    div = [{
        "Placa": "XYZ9W87",
        "Data": "06/06/2026",
        "Produto": "MANGANES",
        "Peso Bruto": 60000,
        "Tara": 22000,
    }]
    result = build_volume_records(ok, div)
    assert "records" in result
    assert len(result["records"]) == 2
    assert result["records"][0]["is_ok"] is True
    assert result["records"][0]["toneladas"] == pytest.approx(38.3)
    assert result["records"][1]["is_ok"] is False
    assert result["records"][1]["toneladas"] == pytest.approx(38.0)


def test_build_volume_records_skips_no_weight():
    ok = [{"Placa": "A", "Data": "01/01/2026", "Produto": "LITIO"}]
    result = build_volume_records(ok, [])
    assert result["records"] == []


def test_compute_period_bounds():
    ok = [{"Data": "06/06/2026"}, {"Data": "05/06/2026"}]
    start, end = compute_period_bounds(ok, [])
    assert start == "05/06/2026"
    assert end == "06/06/2026"
