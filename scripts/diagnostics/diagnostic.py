import pandas as pd
import pdfplumber
import traceback
import os

print('='*60)
print('DIAGNOSTICO COMPLETO')
print('='*60)

# 1. Teste Excel
print('\n--- TESTE EXCEL ---')
xlsx_files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
print(f'Arquivos Excel encontrados: {xlsx_files}')

for xf in xlsx_files:
    print(f'\n>> {xf}')
    try:
        ef = pd.ExcelFile(xf)
        print(f'   Sheets: {ef.sheet_names}')
        for sn in ef.sheet_names[:2]:
            df = ef.parse(sn, skiprows=4)
            df = df.dropna(axis=1, how='all')
            print(f'   Sheet [{sn}]: {len(df)} rows, cols={list(df.columns)}')
            if len(df) > 0:
                print(f'   Amostra: {df.head(1).to_dict()}')
    except Exception as e:
        print(f'   ERRO: {e}')

# 2. Teste PDF
print('\n--- TESTE PDF ---')
pdf_files = [f for f in os.listdir('.') if f.endswith('.pdf')]
print(f'Arquivos PDF encontrados: {pdf_files}')

for pf in pdf_files:
    print(f'\n>> {pf}')
    try:
        with pdfplumber.open(pf) as pdf:
            print(f'   Paginas: {len(pdf.pages)}')
            for i, page in enumerate(pdf.pages[:3]):
                table = page.extract_table()
                if table:
                    print(f'   Pagina {i}: {len(table)} rows')
                    print(f'   Headers: {table[0]}')
                    if len(table) > 1:
                        print(f'   Row 1: {table[1]}')
                else:
                    print(f'   Pagina {i}: sem tabela')
    except Exception as e:
        print(f'   ERRO: {e}')

# 3. Teste processador completo
print('\n--- TESTE PROCESSADOR ---')
from processor import process_excel_file, process_pdf_file, calculate_kpis

all_dfs = []
for xf in xlsx_files:
    try:
        df = process_excel_file(xf)
        print(f'process_excel({xf}): {len(df)} rows, cols={list(df.columns)}')
        if not df.empty:
            all_dfs.append(df)
    except Exception as e:
        print(f'FALHA process_excel({xf}): {e}')
        traceback.print_exc()

for pf in pdf_files:
    try:
        df = process_pdf_file(pf)
        print(f'process_pdf({pf}): {len(df)} rows, cols={list(df.columns)}')
        if not df.empty:
            all_dfs.append(df)
    except Exception as e:
        print(f'FALHA process_pdf({pf}): {e}')
        traceback.print_exc()

print(f'\nTotal DataFrames validos: {len(all_dfs)}')

if all_dfs:
    final = pd.concat(all_dfs, ignore_index=True)
    col_data = 'Data'
    print(f'DataFrame final: {len(final)} rows, cols={list(final.columns)}')
    print(f'Tipos: {dict(final.dtypes)}')
    print(f'Amostra Data: {final[col_data].head(5).tolist()}')
    
    try:
        kpis = calculate_kpis(final)
        if kpis:
            print(f'\nKPIs calculados com sucesso!')
            print(f'Resumo: {kpis.get("resumo", {})}')
            print(f'Distribuicao: {kpis.get("distribuicao", {})}')
            ev = kpis.get('evolucao', {})
            print(f'Evolucao labels (primeiros 5): {ev.get("labels", [])[:5]}')
            print(f'Evolucao datasets: {len(ev.get("datasets", []))} series')
        else:
            print('KPIs retornou vazio!')
    except Exception as e:
        print(f'FALHA calculate_kpis: {e}')
        traceback.print_exc()
else:
    print('NENHUM DataFrame valido!')
