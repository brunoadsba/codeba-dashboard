import logging
import traceback

import pandas as pd
import pdfplumber

from src.utils.cleaners import clean_placa, safe_to_numeric

logger = logging.getLogger(__name__)


def _deduplicate_weighings(df):
    """
    Remove pesagens duplicadas do OpenPort.

    O sistema OpenPort pode gerar múltiplos registros para a mesma pesagem física,
    com pequenas variações de digitação na placa ou SEV. Duplicatas são identificadas
    por: mesma Data + mesmo Peso Bruto + mesma Tara (match exato).

    Mantém a primeira ocorrência e descarta as subsequentes.

    Returns:
        tuple: (DataFrame filtrado, quantidade de duplicatas removidas)
    """
    if df.empty or 'Data' not in df.columns or 'Peso Bruto' not in df.columns or 'Tara' not in df.columns:
        return df, 0

    before_count = len(df)

    # Identificar duplicatas por Data + Peso Bruto + Tara (match exato), mantendo a primeira
    duplicated_mask = df.duplicated(subset=['Data', 'Peso Bruto', 'Tara'], keep='first')

    # Logar cada duplicata descartada para rastreabilidade
    duplicated_rows = df[duplicated_mask]
    for _, row in duplicated_rows.iterrows():
        sev_info = f", SEV: {row['SEV']}" if 'SEV' in df.columns and pd.notna(row.get('SEV')) else ""
        logger.info(
            "Duplicata removida: Placa=%s, Data=%s, Bruto=%.2f, Tara=%.2f%s",
            row.get('Placa', '?'),
            row.get('Data', '?'),
            row.get('Peso Bruto', 0),
            row.get('Tara', 0),
            sev_info
        )

    df_clean = df[~duplicated_mask].copy()
    removed_count = before_count - len(df_clean)

    return df_clean, removed_count


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
        
        mapped_df = pd.DataFrame()
        for target, substring in [
            ('Placa', 'PLACA'),
            ('Data', 'DATA'),
            ('Peso Bruto', 'BRUTO'),
            ('Tara', 'TARA'),
            ('SEV', 'SEV'),
            ('Tipo Carga', 'TIPO CARGA')
        ]:
            found_col = None
            for col in df.columns:
                if col and substring in str(col).upper():
                    found_col = col
                    break
            if found_col is not None:
                mapped_df[target] = df[found_col]
        df = mapped_df

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

        # Desduplicação: remove pesagens duplicadas do OpenPort
        df, duplicatas_removidas = _deduplicate_weighings(df)
        if duplicatas_removidas > 0:
            logger.info(f"Desduplicação PDF: {duplicatas_removidas} registro(s) duplicado(s) removido(s).")

        df['Fonte'] = 'PDF'
        return df
    except Exception as e:
        logger.error(f"Erro PDF: {e}\n{traceback.format_exc()}")
        return pd.DataFrame()
