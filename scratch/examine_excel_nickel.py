import pandas as pd

file_path = r"c:\Users\bruno.santos\Downloads\Projetos\codeba\operacao\data\excel\NÍQUEL- ATLANTIC NICKEL.xlsx"
print(f"Lendo {file_path}...")

with pd.ExcelFile(file_path) as xls:
    for sheet in xls.sheet_names:
        df = xls.parse(sheet, header=None)
        print(f"\nSheet: {sheet}")
        
        # Procurar por cabeçalho
        header_idx = None
        for idx, row in df.head(50).iterrows():
            row_str = ' '.join(str(val).upper() for val in row.values)
            if 'PLACA' in row_str and ('PESO' in row_str or 'DATA' in row_str):
                header_idx = idx
                print(f"  Cabeçalho achado na linha {idx}")
                break
                
        if header_idx is not None:
            df_data = df.iloc[header_idx+1:].copy()
            df_data.columns = df.iloc[header_idx]
            
            # Limpar nomes de colunas
            df_data.columns = [str(c).strip() for c in df_data.columns]
            
            # Procurar por RPJ0I50 ou RPJ0150
            placa_cols = [c for c in df_data.columns if 'PLACA' in c.upper()]
            if placa_cols:
                placa_col = placa_cols[0]
                matches = df_data[df_data[placa_col].astype(str).str.contains("RPJ", na=False)]
                if not matches.empty:
                    print(f"  Encontrei {len(matches)} linhas com RPJ:")
                    for idx_m, row_m in matches.iterrows():
                        print(f"    Linha {idx_m}: {row_m.dropna().to_dict()}")
                else:
                    print("  Nenhuma linha com RPJ encontrada nesta sheet.")
            else:
                print("  Coluna Placa não encontrada.")
