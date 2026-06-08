import os
import pandas as pd
import json

directory = r"C:\Users\bruno.santos\Downloads\Projetos\codeba\operacao"
results = {}

print("Iniciando análise dos arquivos...")

for file in os.listdir(directory):
    if file.endswith(".xlsx") or file.endswith(".xls"):
        file_path = os.path.join(directory, file)
        print(f"Analisando {file}...")
        try:
            excel_file = pd.ExcelFile(file_path)
            file_info = {"sheets": {}}
            for sheet in excel_file.sheet_names:
                df = excel_file.parse(sheet, nrows=5)
                cols = {col: str(df[col].dtype) for col in df.columns}
                # Convert samples to string to avoid serialization issues
                sample = df.head(2).astype(str).to_dict(orient="records")
                file_info["sheets"][sheet] = {"columns": cols, "sample": sample}
            results[file] = file_info
        except Exception as e:
            results[file] = {"error": str(e)}
            print(f"Erro em {file}: {e}")

output_path = os.path.join(directory, "analysis_results.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, ensure_ascii=False)

print(f"Análise concluída. Resultados salvos em {output_path}")
