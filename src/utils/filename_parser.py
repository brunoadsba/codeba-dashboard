import os

def extract_produto_from_filename(filename):
    base = os.path.basename(filename)
    name = base.rsplit('.', 1)[0] if '.' in base else base
    if " - " in name:
        return name.split(" - ")[0].strip()
    if "- " in name:
        return name.split("- ")[0].strip()
    return name.strip()


def extract_cliente_from_filename(filename):
    """Extrai o nome do cliente/fornecedor do nome do arquivo (parte após ' - ')."""
    base = os.path.basename(filename)
    name = base.rsplit('.', 1)[0] if '.' in base else base
    if " - " in name:
        return name.split(" - ", 1)[1].strip()
    if "- " in name:
        return name.split("- ", 1)[1].strip()
    return ""
