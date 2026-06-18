import re
from typing import Any

import pandas as pd


def clean_placa(placa: Any) -> str:
    if pd.isna(placa):
        return ''
    return re.sub(r'[^A-Z0-9]', '', str(placa).upper())


def safe_to_numeric(val: Any) -> float:
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
