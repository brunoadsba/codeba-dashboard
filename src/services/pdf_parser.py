import logging
import traceback
import pandas as pd
import pdfplumber

from src.utils.cleaners import clean_placa, safe_to_numeric

logger = logging.getLogger(__name__)

def process_pdf_file(file_path):
    try:
        all_data = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                table = page.extract_table()
                if not table or len(table) < 2:
                    continue
                
                # Header Hunting dinâmico nas primeiras 10 linhas
                header_idx = None
                for idx, row in enumerate(table[:10]):
                    if not row:
                        continue
                    # Ignora linhas com poucas células preenchidas (ex: cabeçalhos corporativos ou filtros)
                    non_empty_cells = sum(1 for cell in row if cell and str(cell).strip() != '')
                    if non_empty_cells < 4:
                        continue
                        
                    row_str = ' '.join([str(cell).upper() for cell in row if cell])
                    # Procura por Placa e outras chaves comuns
                    if 'PLACA' in row_str and ('PESO' in row_str or 'DATA' in row_str or 'SEV' in row_str):
                        header_idx = idx
                        break
                
                if header_idx is None:
                    logger.warning(f"Cabeçalho de pesagem não encontrado no PDF (Pág {page_num})")
                    continue
                
                headers = table[header_idx]
                unique_headers = []
                for i, h in enumerate(headers):
                    h_str = str(h).strip() if h else f"Unnamed_{i}"
                    count = unique_headers.count(h_str)
                    if count > 0:
                        h_str = f"{h_str}_{count}"
                    unique_headers.append(h_str)
                    
                df = pd.DataFrame(table[header_idx + 1:], columns=unique_headers)
                all_data.append(df)
                
        if not all_data:
            return pd.DataFrame()
            
        df = pd.concat(all_data, ignore_index=True)
        
        col_map = {}
        for col in df.columns:
            if not col: continue
            col_str = str(col).upper()
            if 'PLACA' in col_str: col_map[col] = 'Placa'
            elif 'DATA' in col_str: col_map[col] = 'Data'
            elif 'BRUTO' in col_str: col_map[col] = 'Peso Bruto'
            elif 'TARA' in col_str: col_map[col] = 'Tara'
            elif 'SEV' in col_str: col_map[col] = 'SEV'
            elif 'TIPO CARGA' in col_str: col_map[col] = 'Tipo Carga'
            
        df = df.rename(columns=col_map)
        useful_cols = [c for c in ['Placa', 'Data', 'Peso Bruto', 'Tara', 'SEV', 'Tipo Carga'] if c in df.columns]
        df = df[useful_cols].copy()
        
        if 'Placa' in df.columns:
            df['Placa'] = df['Placa'].apply(clean_placa)
            df = df[df['Placa'] != '']
            df = df[~df['Placa'].isin(['PLACA', 'NAN'])]
            
        # Sanitização Numérica do PDF
        for col in ['Peso Bruto', 'Tara']:
            if col in df.columns:
                df[col] = df[col].apply(safe_to_numeric)
                
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)
            
        df['Fonte'] = 'PDF'
        return df
    except Exception as e:
        logger.error(f"Erro PDF: {e}\n{traceback.format_exc()}")
        return pd.DataFrame()
