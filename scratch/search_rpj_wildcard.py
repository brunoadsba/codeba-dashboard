import os
import pandas as pd
import glob

downloads_dir = r"c:\Users\bruno.santos\Downloads"
print(f"Buscando RPJ em planilhas de {downloads_dir}...")

excel_files = glob.glob(os.path.join(downloads_dir, "**/*.xlsx"), recursive=True)
excel_files += glob.glob(os.path.join(downloads_dir, "**/*.xls"), recursive=True)

print(f"Total de planilhas encontradas: {len(excel_files)}")

for file in excel_files:
    filename = os.path.basename(file)
    try:
        with pd.ExcelFile(file) as xls:
            for sheet in xls.sheet_names:
                df = xls.parse(sheet, header=None)
                for r_idx, row in df.iterrows():
                    row_str = " ".join(str(val) for val in row.values)
                    if "RPJ" in row_str.upper():
                        print(f"\nAchei no arquivo: {file}")
                        print(f"  Sheet '{sheet}', linha {r_idx}:")
                        print(f"  {row.dropna().to_dict()}")
    except Exception as e:
        pass
