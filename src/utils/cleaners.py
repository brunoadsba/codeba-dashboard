import pandas as pd
import re

def clean_placa(placa):
    """Remove traços, espaços e mantém apenas letras e números maiúsculos."""
    if pd.isna(placa):
        return ''
    return re.sub(r'[^A-Z0-9]', '', str(placa).upper())


def safe_to_numeric(val):
    """
    Converte com segurança valores numéricos que podem vir como float nativo ou string formatada (BR).
    Ex: 1234.56 (float) -> 1234.56
        '1.234,56' (str) -> 1234.56
        '1234,56' (str) -> 1234.56
        '1234.56' (str) -> 1234.56
    """
    if pd.isna(val) or val == '':
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    val_str = str(val).strip()
    
    # Se tem vírgula, assume-se formato BR (vírgula é decimal). Remove pontos de milhar.
    if ',' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    else:
        # Se não tem vírgula, mas tem ponto, verificamos se é decimal ou milhar
        if val_str.count('.') > 1:
            # Múltiplos pontos = milhares (ex: 1.000.000). Removemos.
            val_str = val_str.replace('.', '')
        elif val_str.count('.') == 1:
            # Se tem exatamente um ponto e 3 casas após ele, assumir que é milhar (ex: '57.840')
            parts = val_str.split('.')
            if len(parts[1]) == 3:
                val_str = val_str.replace('.', '')
            
    try:
        return float(val_str)
    except Exception:
        return 0.0
