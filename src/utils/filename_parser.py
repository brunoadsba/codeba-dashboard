import os
import re
from typing import Optional


PRODUTOS_CONHECIDOS = [
    "LITIO", "LÍTIO",
    "ÓXIDO DE MAGNÉSIO", "OXIDO DE MAGNESIO",
    "MANGANÊS", "MANGANES",
    "NÍQUEL", "NIQUEL", "ATLANTIC NICKEL",
    "MILHO",
]


def extract_produto_from_filename(filename: str) -> Optional[str]:
    base = os.path.basename(filename)
    name = base.rsplit('.', 1)[0] if '.' in base else base
    name_upper = name.upper().strip()

    # Busca por produtos conhecidos no nome do arquivo (case-insensitive)
    for produto in PRODUTOS_CONHECIDOS:
        if produto.upper() in name_upper:
            # Retorna o nome canônico (mantém acentos e formatação original)
            if produto in ("LÍTIO",):
                return "LITIO"
            if produto in ("ÓXIDO DE MAGNÉSIO", "OXIDO DE MAGNESIO"):
                return "ÓXIDO DE MAGNÉSIO"
            if produto in ("MANGANÊS", "MANGANES"):
                return "MANGANÊS"
            if produto in ("NÍQUEL", "NIQUEL", "ATLANTIC NICKEL"):
                return "NÍQUEL"
            return produto

    # Fallback: lógica antiga
    if " - " in name:
        return name.split(" - ")[0].strip()
    if "- " in name:
        return name.split("- ")[0].strip()
    return name.strip()

