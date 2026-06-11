"""Test reconcile_data with PDF grande AFTER the bidirectional fix"""
import sys, os
sys.path.append(r"C:\Users\bruno.santos\Downloads\Projetos\codeba\operacao")
os.chdir(r"C:\Users\bruno.santos\Downloads\Projetos\codeba\operacao")
import processor, pandas as pd, importlib
importlib.reload(processor)

excel_dir = "excel"
pdf_path = "Relatorios/01_01_2025 ate 02_06_2026.pdf"

all_excel = []
for f in sorted(os.listdir(excel_dir)):
    if not f.endswith('.xlsx'): continue
    df = processor.process_excel_file(os.path.join(excel_dir, f))
    if not df.empty:
        df['Produto'] = processor.extract_produto_from_filename(f)
        df['Cliente'] = processor.extract_cliente_from_filename(f)
        all_excel.append(df)
        print(f"{f}: {len(df)} registros")

df_excel = pd.concat(all_excel, ignore_index=True) if all_excel else pd.DataFrame()
df_pdf = processor.process_pdf_file(pdf_path)

print(f"\nTotal Excel: {len(df_excel)}")
print(f"Total PDF: {len(df_pdf)}")

result = processor.reconcile_data(df_excel, df_pdf)
print(f"\n=== RESULTADO APOS FIX ===")
print(f"OK: {result['resumo']['ok']}")
print(f"Divergencias: {result['resumo']['divergencias']}")
print(f"Total: {result['resumo']['total_processado']}")
print(f"Produtos: {result.get('produtos_detectados', [])}")

status_counts = {}
for d in result['divergencias']:
    s = d.get('Status', '?')
    status_counts[s] = status_counts.get(s, 0) + 1
print(f"\nDivergencias por tipo:")
for s, c in sorted(status_counts.items(), key=lambda x: -x[1]):
    print(f"  {s}: {c}")
