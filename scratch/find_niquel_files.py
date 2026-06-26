import os
import glob

search_root = r"c:\Users\bruno.santos"
print(f"Buscando arquivos de planilhas em {search_root}...")

# Pastas de interesse
folders = [
    os.path.join(search_root, "Desktop"),
    os.path.join(search_root, "Documents"),
    os.path.join(search_root, "Downloads"),
    os.path.join(search_root, "OneDrive")
]

all_files = []
for folder in folders:
    if os.path.exists(folder):
        print(f"  Varrendo: {folder}")
        all_files += glob.glob(os.path.join(folder, "**/*.xlsx"), recursive=True)
        all_files += glob.glob(os.path.join(folder, "**/*.xls"), recursive=True)

print(f"Total de planilhas encontradas nas pastas do usuário: {len(all_files)}")

niquel_files = []
for f in all_files:
    filename = os.path.basename(f)
    if "NÍQUEL" in filename.upper() or "NIQUEL" in filename.upper() or "CBL" in filename.upper() or "IBAR" in filename.upper() or "MAGNESITA" in filename.upper():
        niquel_files.append(f)
        print(f"Encontrado: {f} (Tamanho: {os.path.getsize(f)} bytes)")

# Se achar arquivos, vamos rodar a busca por RPJ neles
import pandas as pd
for file in niquel_files:
    print(f"\nExplicando RPJ no arquivo: {file}")
    try:
        with pd.ExcelFile(file) as xls:
            for sheet in xls.sheet_names:
                df = xls.parse(sheet, header=None)
                for r_idx, row in df.iterrows():
                    row_str = " ".join(str(val) for val in row.values)
                    if "RPJ" in row_str.upper():
                        print(f"  Sheet '{sheet}', linha {r_idx}:")
                        print(f"  {row.dropna().to_dict()}")
    except Exception as e:
        print(f"  Erro ao ler: {e}")
