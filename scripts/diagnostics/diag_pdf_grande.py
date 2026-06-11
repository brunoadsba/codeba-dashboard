"""Diagnóstico: PDF grande (01/01/2025 a 02/06/2026) vs 6 Excels"""
import sys, os
sys.path.append(r"C:\Users\bruno.santos\Downloads\Projetos\codeba\operacao")
os.chdir(r"C:\Users\bruno.santos\Downloads\Projetos\codeba\operacao")
import processor
import pandas as pd

pdf_path = r"Relatorios\01_01_2025 ate 02_06_2026.pdf"
excel_dir = r"excel"

# 1) Analisar o PDF
print("=" * 60)
print("ANALISE DO PDF")
print("=" * 60)
df_pdf = processor.process_pdf_file(pdf_path)
print(f"Total linhas PDF: {len(df_pdf)}")
print(f"Colunas PDF: {list(df_pdf.columns)}")

if 'Data' in df_pdf.columns:
    datas_pdf = df_pdf['Data'].dropna().unique()
    print(f"Datas unicas no PDF: {len(datas_pdf)}")
    
    # Parse dates
    parsed = []
    for d in datas_pdf:
        try:
            parts = str(d).split('/')
            if len(parts) == 3:
                parsed.append(pd.Timestamp(int(parts[2]), int(parts[1]), int(parts[0])))
        except:
            pass
    
    if parsed:
        parsed.sort()
        print(f"Periodo PDF: {parsed[0].strftime('%d/%m/%Y')} a {parsed[-1].strftime('%d/%m/%Y')}")
        print(f"Total dias: {(parsed[-1] - parsed[0]).days}")
        
        # Distribuicao por mes
        meses = {}
        for p in parsed:
            k = p.strftime('%Y-%m')
            meses[k] = meses.get(k, 0) + 1
        print(f"\nDatas por mes/ano:")
        for m in sorted(meses.keys()):
            print(f"  {m}: {meses[m]} datas")

# Contagem de placas
if 'Placa' in df_pdf.columns:
    placas_pdf = df_pdf['Placa'].dropna().unique()
    print(f"\nPlacas unicas no PDF: {len(placas_pdf)}")

# 2) Analisar cada Excel
print("\n" + "=" * 60)
print("ANALISE DOS EXCELS")
print("=" * 60)

all_excel = []
for f in sorted(os.listdir(excel_dir)):
    if not f.endswith('.xlsx'):
        continue
    fp = os.path.join(excel_dir, f)
    df = processor.process_excel_file(fp)
    if df.empty:
        print(f"\n{f}: VAZIO!")
        continue
    
    produto = processor.extract_produto_from_filename(f)
    cliente = processor.extract_cliente_from_filename(f)
    df['Produto'] = produto
    df['Cliente'] = cliente
    
    print(f"\n{f}")
    print(f"  Produto: {produto} | Cliente: {cliente}")
    print(f"  Registros: {len(df)}")
    print(f"  Colunas: {list(df.columns)}")
    
    if 'Data' in df.columns:
        datas = df['Data'].dropna().unique()
        parsed_excel = []
        for d in datas:
            try:
                parts = str(d).split('/')
                if len(parts) == 3:
                    parsed_excel.append(pd.Timestamp(int(parts[2]), int(parts[1]), int(parts[0])))
            except:
                pass
        if parsed_excel:
            parsed_excel.sort()
            print(f"  Periodo: {parsed_excel[0].strftime('%d/%m/%Y')} a {parsed_excel[-1].strftime('%d/%m/%Y')}")
        
    if 'Placa' in df.columns:
        print(f"  Placas unicas: {len(df['Placa'].dropna().unique())}")
    
    all_excel.append(df)

df_excel = pd.concat(all_excel, ignore_index=True) if all_excel else pd.DataFrame()
print(f"\nTotal registros Excel (todos): {len(df_excel)}")

# 3) Verificar interseção de datas
print("\n" + "=" * 60)
print("INTERSECAO DE PERIODOS")
print("=" * 60)

if 'Data' in df_excel.columns and 'Data' in df_pdf.columns:
    excel_dates = set(df_excel['Data'].dropna().unique())
    pdf_dates = set(df_pdf['Data'].dropna().unique())
    common = excel_dates & pdf_dates
    only_pdf = pdf_dates - excel_dates
    only_excel = excel_dates - pdf_dates
    
    print(f"Datas no Excel: {len(excel_dates)}")
    print(f"Datas no PDF: {len(pdf_dates)}")
    print(f"Datas em AMBOS: {len(common)}")
    print(f"Datas so no PDF: {len(only_pdf)}")
    print(f"Datas so no Excel: {len(only_excel)}")
    
    # Contar registros PDF em datas sem Excel
    pdf_sem_excel = df_pdf[df_pdf['Data'].isin(only_pdf)]
    print(f"\nRegistros PDF em datas sem Excel: {len(pdf_sem_excel)} de {len(df_pdf)}")
    print(f"Registros PDF em datas COM Excel: {len(df_pdf) - len(pdf_sem_excel)}")

# 4) Teste rapido de reconciliacao
print("\n" + "=" * 60)
print("TESTE DE RECONCILIACAO")
print("=" * 60)
result = processor.reconcile_data(df_excel, df_pdf)
print(f"OK: {result['resumo']['ok']}")
print(f"Divergencias: {result['resumo']['divergencias']}")
print(f"Total: {result['resumo']['total_processado']}")
print(f"Produtos: {result.get('produtos_detectados', [])}")

# Breakdown de divergencias por status
status_counts = {}
for d in result['divergencias']:
    s = d.get('Status', '?')
    status_counts[s] = status_counts.get(s, 0) + 1
print(f"\nDivergencias por tipo:")
for s, c in sorted(status_counts.items(), key=lambda x: -x[1]):
    print(f"  {s}: {c}")

# Breakdown por produto
prod_counts = {}
for d in result['divergencias']:
    p = d.get('Produto', 'VAZIO')
    prod_counts[p] = prod_counts.get(p, 0) + 1
print(f"\nDivergencias por produto (top 10):")
for p, c in sorted(prod_counts.items(), key=lambda x: -x[1])[:10]:
    print(f"  {p}: {c}")
