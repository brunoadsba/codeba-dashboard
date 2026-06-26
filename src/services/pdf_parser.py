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

    # Identificar duplicatas por Placa + Data + Peso Bruto + Tara (match exato), mantendo a primeira
    # NOTA: SEV NÃO entra na chave porque o mesmo romaneio pode ter múltiplas pesagens
    # e a mesma pesagem física pode ter SEVs diferentes (duplicata espúria do OpenPort)
    subset_cols = ['Placa', 'Data', 'Peso Bruto', 'Tara']
    duplicated_mask = df.duplicated(subset=subset_cols, keep='first')

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


def _remove_incomplete_weighings(df):
    """
    Remove pesagens incompletas do OpenPort (Tara = 0) que possuem uma pesagem
    completa correspondente no mesmo dia para a mesma placa.

    Regra: Se a mesma placa no mesmo dia tem um registro com Tara > 0 e outro com Tara == 0
    onde |Bruto_parcial - Bruto_completo| < 200 kg, o registro Tara == 0 é classificado
    como pesagem incompleta e descartado.
    """
    if df.empty or 'Placa' not in df.columns or 'Data' not in df.columns or 'Peso Bruto' not in df.columns or 'Tara' not in df.columns:
        return df, 0

    before_count = len(df)

    # Criar DataFrame temporário apenas com linhas válidas para Placa e Data
    df_valid = df.dropna(subset=['Placa', 'Data']).copy()
    if df_valid.empty:
        return df, 0

    temp_dates = df_valid['Data'].dt.date
    to_remove = set()

    grouped = df_valid.groupby(['Placa', temp_dates])

    for (placa, data_dia), group in grouped:
        if pd.isna(data_dia) or not placa:
            continue

        parciais = group[group['Tara'] == 0]
        completas = group[group['Tara'] > 0]

        if parciais.empty or completas.empty:
            continue

        for p_idx, p_row in parciais.iterrows():
            p_bruto = p_row['Peso Bruto']
            # Procurar se há alguma pesagem completa correspondente
            for c_idx, c_row in completas.iterrows():
                c_bruto = c_row['Peso Bruto']
                if abs(p_bruto - c_bruto) < 200:
                    to_remove.add(p_idx)
                    sev_info = f", SEV: {p_row['SEV']}" if 'SEV' in df.columns and pd.notna(p_row.get('SEV')) else ""
                    logger.info(
                        "Pesagem incompleta removida (Tara=0 com completa correspondente): "
                        "Placa=%s, Data=%s, Bruto=%.2f%s",
                        placa,
                        p_row['Data'],
                        p_bruto,
                        sev_info
                    )
                    break  # Encontrou correspondente, para de procurar para este parcial

    df_clean = df.drop(index=list(to_remove)).copy()
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
        
        logger.debug("Colunas originais do PDF: %s", list(df.columns))

        mapped_df = pd.DataFrame()
        for target, substrings in [
            ('Placa', ['PLACA']),
            ('Data', ['DATA']),
            ('Peso Bruto', ['BRUTO']),
            ('Tara', ['TARA']),
            ('SEV', ['SEV']),
            ('Tipo Carga', ['TIPO CARGA', 'TIPO DE MERCADORIA', 'MERCADORIA', 'CARGA', 'PRODUTO', 'MERCADO']),
        ]:
            found_col = None
            for col in df.columns:
                if col:
                    col_upper = str(col).upper().replace('\n', ' ').replace('\r', ' ')
                    for substring in substrings:
                        if substring in col_upper:
                            found_col = col
                            break
                if found_col:
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
            datas_antes = df['Data'].notna().sum()
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)
            datas_rejeitadas = datas_antes - df['Data'].notna().sum()
            if datas_rejeitadas > 0:
                logger.warning("PDF: %d data(s) inválida(s) ignorada(s)", datas_rejeitadas)

        # Desduplicação: remove pesagens duplicadas do OpenPort
        df, duplicatas_removidas = _deduplicate_weighings(df)
        if duplicatas_removidas > 0:
            logger.info(f"Desduplicação PDF: {duplicatas_removidas} registro(s) duplicado(s) removido(s).")

        # Filtragem de pesagens incompletas (Tara = 0 com completa correspondente)
        df, incompletas_removidas = _remove_incomplete_weighings(df)
        if incompletas_removidas > 0:
            logger.info(f"Pesagens incompletas PDF: {incompletas_removidas} registro(s) incompletos removido(s).")

        logger.info("PDF: %d registro(s) extraído(s) (%d duplicatas removidas, %d incompletas removidas)", 
                    len(df), duplicatas_removidas, incompletas_removidas)
        df['Fonte'] = 'PDF'
        return df
    except Exception as e:
        logger.error(f"Erro PDF: {e}\n{traceback.format_exc()}")
        return pd.DataFrame()
