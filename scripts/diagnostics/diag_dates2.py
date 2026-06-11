import processor, pandas as pd
pdf = processor.process_pdf_file('Relatorios/01_01_2025 ate 02_06_2026.pdf')
ex = processor.process_excel_file('excel/LITIO - CBL.xlsx')

p = pdf.copy()
p['DM'] = pd.to_datetime(p['Data'], errors='coerce').dt.strftime('%d/%m/%Y')

e = ex.copy()
e['DM'] = pd.to_datetime(e['Data'], errors='coerce').dt.strftime('%d/%m/%Y')

pd_set = set(p['DM'].dropna())
ed_set = set(e['DM'].dropna())
common = pd_set & ed_set

print(f"PDF datas formatadas: {len(pd_set)} unicas")
print(f"Excel datas formatadas: {len(ed_set)} unicas")
print(f"Em AMBOS: {len(common)}")
print(f"PDF amostra: {sorted(list(pd_set))[:5]}")
print(f"Excel amostra: {sorted(list(ed_set))[:5]}")
print(f"Comuns: {sorted(list(common))[:10]}")
