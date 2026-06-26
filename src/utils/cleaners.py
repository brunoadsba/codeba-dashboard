import re
import unicodedata
from typing import Any

import pandas as pd


def clean_placa(placa: Any) -> str:
    if pd.isna(placa):
        return ''
    normalized = unicodedata.normalize('NFKD', str(placa))
    ascii_str = normalized.encode('ASCII', 'ignore').decode('ASCII')
    return re.sub(r'[^A-Z0-9]', '', ascii_str.upper())


def safe_to_numeric(val: Any) -> float:
    """
    Converte um valor de entrada de forma segura para float.
    
    LIMITAÇÕES E PREMISSAS:
    - Se houver vírgula, assume padrão brasileiro (ex: "54.160,00" -> "54160.00").
    - Se não houver vírgula mas houver mais de um ponto (ex: "54.160.00"), remove os pontos.
    - Se houver exatamente um ponto e este for seguido por exatamente 3 dígitos (ex: "57.840"),
      a heurística assume que o ponto é um separador de milhar e o remove (ex: 57840.0).
      * Risco: Valores decimais legítimos com 3 casas (como "1.500" representando 1,5 toneladas)
        serão incorretamente normalizados para 1500.0. Como o dashboard opera com pesos de balança 
        na escala de milhares de kg (de 10.000 a 80.000), o impacto é mitigado na prática.
    """
    if pd.isna(val) or val == '':
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    val_str = str(val).strip()

    if ',' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    else:
        if val_str.count('.') > 1:
            val_str = val_str.replace('.', '')
        elif val_str.count('.') == 1:
            parts = val_str.split('.')
            if len(parts[1]) == 3:
                val_str = val_str.replace('.', '')

    try:
        return float(val_str)
    except Exception:
        return 0.0
