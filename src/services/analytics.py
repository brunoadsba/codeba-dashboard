"""
Agregação analítica de volume (toneladas) para o dashboard CODEBA.
"""

from __future__ import annotations

from typing import Any


def normalize_product(prod: str) -> str:
    """Normaliza nome de produto para agrupamento."""
    if not prod:
        return "Outros"
    clean = prod.replace(" (Deduzido)", "").strip()
    if not clean or clean == "Não Identificado" or clean.startswith("Ambíguo"):
        return "Outros"
    return clean


def net_weight_kg(item: dict[str, Any], is_ok: bool) -> float | None:
    """Retorna peso líquido em kg ou None se indisponível."""
    if is_ok:
        pl = item.get("Peso Liquido")
        if pl is not None:
            try:
                return float(pl)
            except (TypeError, ValueError):
                pass
    bruto = item.get("Peso Bruto")
    tara = item.get("Tara")
    if bruto is not None and tara is not None:
        try:
            return float(bruto) - float(tara)
        except (TypeError, ValueError):
            pass
    return None


def build_volume_records(ok_list: list[dict], divergencias: list[dict]) -> dict[str, Any]:
    """
    Gera registros granulares de volume para filtragem dinâmica no frontend.

    Cada registro representa uma viagem com peso calculável.
    """
    records: list[dict[str, Any]] = []

    for item in ok_list:
        weight = net_weight_kg(item, is_ok=True)
        if weight is None or weight <= 0:
            continue
        records.append({
            "data": item.get("Data", ""),
            "produto": normalize_product(item.get("Produto", "")),
            "toneladas": round(weight / 1000, 3),
            "viagens": 1,
            "is_ok": True,
            "placa": item.get("Placa", ""),
        })

    for item in divergencias:
        weight = net_weight_kg(item, is_ok=False)
        if weight is None or weight <= 0:
            continue
        records.append({
            "data": item.get("Data", ""),
            "produto": normalize_product(item.get("Produto", "")),
            "toneladas": round(weight / 1000, 3),
            "viagens": 1,
            "is_ok": False,
            "placa": item.get("Placa", ""),
        })

    return {
        "records": records,
        "meta": {
            "unidade": "toneladas",
            "fonte_peso": "Peso Liquido / Bruto-Tara",
        },
    }


def compute_period_bounds(ok_list: list[dict], divergencias: list[dict]) -> tuple[str | None, str | None]:
    """Retorna (period_start, period_end) em DD/MM/YYYY."""
    dates: list[str] = []
    for item in ok_list + divergencias:
        d = item.get("Data")
        if d:
            dates.append(d)
    if not dates:
        return None, None

    def parse_key(d: str) -> tuple[int, int, int]:
        date_part = d.split(" ")[0]
        parts = date_part.split("/")
        if len(parts) == 3:
            try:
                return int(parts[2]), int(parts[1]), int(parts[0])
            except ValueError:
                pass
        return 0, 0, 0

    dates.sort(key=parse_key)
    return dates[0], dates[-1]
