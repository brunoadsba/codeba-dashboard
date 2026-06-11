import logging
import traceback
import pandas as pd

from src.utils.cleaners import clean_placa, safe_to_numeric
from src.utils.filename_parser import extract_produto_from_filename, extract_cliente_from_filename

logger = logging.getLogger(__name__)

def process_excel_file(file_path):
    try:
        logger.info(f"Processando Excel: {file_path}")
        all_data = []
        produto_from_file = extract_produto_from_filename(file_path)

        with pd.ExcelFile(file_path) as excel_file:
            for sheet_name in excel_file.sheet_names:
                try:
                    # Carregar cru sem pular linhas hardcoded
                    df_raw = excel_file.parse(sheet_name, header=None)
                    if df_raw.empty:
                        continue

                    # Header Hunting: Procurar dinamicamente nas primeiras 20 linhas
                    header_idx = None
                    for idx, row in df_raw.head(20).iterrows():
                        row_str = ' '.join(row.astype(str).str.upper())
                        if 'PLACA' in row_str and ('PESO' in row_str or 'DATA' in row_str):
                            header_idx = idx
                            break

                    if header_idx is None:
                        continue

                    df_data = df_raw.iloc[header_idx+1:].copy()
                    df_data.columns = df_raw.iloc[header_idx]
                    df_data = df_data.reset_index(drop=True)
                    df_data = df_data.dropna(axis=1, how='all')

                    # Mapeamento dinâmico de colunas
                    col_map = {}
                    for col in df_data.columns:
                        col_str = str(col).upper().strip()
                        if 'PLACA' in col_str and 'OBS' not in col_str:
                            col_map[col] = 'Placa'
                        elif 'DATA' in col_str:
                            col_map[col] = 'Data'
                        elif 'PESO' in col_str and 'BRUTO' in col_str:
                            col_map[col] = 'Peso Bruto'
                        elif 'TARA' in col_str:
                            col_map[col] = 'Tara'
                        elif 'PESO' in col_str and ('LIQUIDO' in col_str or 'LÍQUIDO' in col_str):
                            col_map[col] = 'Peso Liquido'

                    df_data = df_data.rename(columns=col_map)

                    keep_cols = [c for c in ['Placa', 'Data', 'Peso Bruto', 'Tara', 'Peso Liquido'] if c in df_data.columns]
                    if not keep_cols or 'Placa' not in keep_cols:
                        continue

                    df_data = df_data[keep_cols]

                    # Limpar Placa
                    df_data['Placa'] = df_data['Placa'].apply(clean_placa)
                    df_data = df_data[df_data['Placa'] != '']
                    # Filtrar linhas de resumo/totalizadores comuns em planilhas CODEBA
                    junk_placas = ['PLACA', 'TOTAL', 'SUBTOTAL', 'NAN', 'TOTALDESCARREGADO',
                                   'BRUTOACUMULADO', 'TARAACUMULADA', 'PESOACUMULADO',
                                   'TOTALCARREGADO', 'LIQUIDOACUMULADO']
                    df_data = df_data[~df_data['Placa'].isin(junk_placas)]

                    if df_data.empty:
                        continue

                    # Sanitização Numérica
                    for col in ['Peso Bruto', 'Tara', 'Peso Liquido']:
                        if col in df_data.columns:
                            df_data[col] = df_data[col].apply(safe_to_numeric)

                    # Data
                    if 'Data' in df_data.columns:
                        df_data['Data'] = pd.to_datetime(df_data['Data'], errors='coerce', dayfirst=True)

                    df_data['Produto'] = produto_from_file
                    df_data['Cliente'] = extract_cliente_from_filename(file_path)
                    df_data['Fonte'] = 'Excel'

                    all_data.append(df_data)
                except Exception as e:
                    logger.error(f"Erro na sheet {sheet_name}: {e}\n{traceback.format_exc()}")
                    continue

        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Erro Excel: {e}\n{traceback.format_exc()}")
        return pd.DataFrame()
