import pandas as pd
import pdfplumber

def sum_excel(file_path):
    print(f"\n--- Reading {file_path} ---")
    try:
        # Read without header
        df = pd.read_excel(file_path, header=None)
        
        # Find weight column index and the row it's on
        weight_col_idx = -1
        header_row_idx = -1
        target_cols = ['peso liquido', 'peso líquido', 'peso (kg)', 'peso bruto', 'quantidade', 'volume']
        
        for r_idx, row in df.iterrows():
            for c_idx, val in enumerate(row):
                if isinstance(val, str) and val.strip().lower() in target_cols:
                    weight_col_idx = c_idx
                    header_row_idx = r_idx
                    print(f"Found header '{val}' at row {r_idx}, col {c_idx}")
                    break
            if weight_col_idx != -1:
                break
                
        if weight_col_idx != -1:
            # Get all values below the header in that column
            weight_series = df.iloc[header_row_idx + 1:, weight_col_idx]
            
            # Clean up the string values (remove dots for thousands, replace comma with dot)
            if weight_series.dtype == object:
                weight_series = weight_series.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            
            weight_series = pd.to_numeric(weight_series, errors='coerce')
            total = weight_series.sum()
            print(f"Total for {file_path}: {total}")
            return total
        else:
            print("Could not identify the weight column. Please check the Excel file.")
            return 0
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

def sum_pdf(file_path):
    print(f"\n--- Reading {file_path} ---")
    total_net_weight = 0
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                table = page.extract_table()
                if not table:
                    continue
                
                # Find the header row in the table
                header_row_idx = -1
                bruto_idx = -1
                tara_idx = -1
                
                for r_idx, row in enumerate(table):
                    row_lower = [str(cell).strip().lower() if cell else "" for cell in row]
                    if 'peso bruto' in row_lower and 'peso tara' in row_lower:
                        header_row_idx = r_idx
                        bruto_idx = row_lower.index('peso bruto')
                        tara_idx = row_lower.index('peso tara')
                        break
                        
                if header_row_idx == -1:
                    print(f"Page {i+1}: Could not find Peso Bruto or Peso Tara headers.")
                    continue
                
                page_total = 0
                for row in table[header_row_idx + 1:]:
                    if bruto_idx < len(row) and tara_idx < len(row):
                        bruto = row[bruto_idx]
                        tara = row[tara_idx]
                        
                        if bruto and tara:
                            # Clean up numbers (e.g. 60520,00 -> 60520.00)
                            try:
                                bruto_val = float(bruto.replace('.', '').replace(',', '.'))
                                tara_val = float(tara.replace('.', '').replace(',', '.'))
                                net = bruto_val - tara_val
                                page_total += net
                            except ValueError:
                                pass # skip non-numeric rows
                        
                print(f"Page {i+1} total net weight: {page_total}")
                total_net_weight += page_total
                
        print(f"Total net weight for PDF: {total_net_weight}")
        return total_net_weight
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

if __name__ == "__main__":
    file1 = r"y:\Nazaro\codeba-dashboard-main\data\ÓXIDO DE MAGNÉSIO - MAGNESITA.xlsx"
    file2 = r"y:\Nazaro\codeba-dashboard-main\data\LITIO - CBL.xlsx"
    file3 = r"y:\Nazaro\codeba-dashboard-main\data\Relatório de Pesquisa - 7015.pdf"
    
    total1 = sum_excel(file1)
    total2 = sum_excel(file2)
    total3 = sum_pdf(file3)
    
    print(f"\n=================================")
    print(f"MAGNESITA Total: {total1:,.2f}")
    print(f"LITIO Total:     {total2:,.2f}")
    print(f"PDF 7015 Total:  {total3:,.2f}")
    print(f"GRAND TOTAL:     {(total1 + total2 + total3):,.2f}")
    print(f"EXPECTED:        2,654,720.00")
    print(f"DIFFERENCE:      {((total1 + total2 + total3) - 2654720):,.2f}")
    print(f"=================================")
