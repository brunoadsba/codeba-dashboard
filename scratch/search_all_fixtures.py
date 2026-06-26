import os
import pandas as pd
import glob

excel_dir = r"c:\Users\bruno.santos\Downloads\Projetos\codeba\operacao\data\excel"
print(f"Buscando em: {excel_dir}")

files = glob.glob(os.path.join(excel_dir, "*.xlsx"))
files += glob.glob(os.path.join(excel_dir, "*.xls"))

for file in files:
    print(f"\nArquivo: {os.path.basename(file)}")
    try:
        with pd.ExcelFile(file) as xls:
            for sheet in xls.sheet_names:
                df = xls.parse(sheet, header=None)
                
                # Procurar por cabeçalho nas primeiras 50 linhas
                header_idx = None
                for idx, row in df.head(50).iterrows():
                    row_str = ' '.join(str(val).upper() for val in row.values)
                    if 'PLACA' in row_str and ('PESO' in row_str or 'DATA' in row_str):
                        header_idx = idx
                        break
                
                if header_idx is not None:
                    df_data = df.iloc[header_idx+1:].copy()
                    df_data.columns = df.iloc[header_idx]
                    df_data.columns = [str(c).strip() for c in df_data.columns]
                    
                    placa_cols = [c for c in df_data.columns if 'PLACA' in c.upper()]
                    if placa_cols:
                        placa_col = placa_cols[0]
                        matches = df_data[df_data[placa_col].astype(str).str.contains("RPJ", na=False)]
                        if not matches.empty:
                            print(f"  Sheet: {sheet} - Encontrei {len(matches)} linhas com RPJ:")
                            for idx_m, row_m in matches.iterrows():
                                print(f"    Linha {idx_m}: {row_m.dropna().to_dict()}")
    except Exception as e:
        print(f"  Erro ao ler: {e}")
