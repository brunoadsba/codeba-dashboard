import os
from typing import Optional


def extract_produto_from_filename(filename: str) -> Optional[str]:
    base = os.path.basename(filename)
    name = base.rsplit('.', 1)[0] if '.' in base else base
    if " - " in name:
        return name.split(" - ")[0].strip()
    if "- " in name:
        return name.split("- ")[0].strip()
    return name.strip()

