"""Check actual date format samples from PDF and Excel"""
import sys, os
sys.path.append(r"C:\Users\bruno.santos\Downloads\Projetos\codeba\operacao")
os.chdir(r"C:\Users\bruno.santos\Downloads\Projetos\codeba\operacao")
import processor

pdf = processor.process_pdf_file(r"Relatorios\01_01_2025 ate 02_06_2026.pdf")
excel = processor.process_excel_file(r"excel\LITIO - CBL.xlsx")

print("PDF - 5 primeiras datas:")
for d in pdf['Data'].head(10):
    print(f"  '{d}' (type: {type(d).__name__})")

print("\nExcel - 5 primeiras datas:")
for d in excel['Data'].head(10):
    print(f"  '{d}' (type: {type(d).__name__})")

# Check for MILHO (missing Data column)
milho = processor.process_excel_file(r"excel\MILHO - FFF TRADING.xlsx")
print(f"\nMILHO colunas: {list(milho.columns)}")
print(f"MILHO 3 primeiras linhas:")
print(milho.head(3).to_string())

# Check IBAR
ibar = processor.process_excel_file(r"excel\ÓXIDO DE MAGNÉSIO - IBAR NORDESTE.xlsx")
print(f"\nIBAR colunas: {list(ibar.columns)}")
print(f"IBAR 3 primeiras linhas:")
print(ibar.head(3).to_string())
