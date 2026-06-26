import hashlib
import json
import logging
import traceback
import uuid
from collections import defaultdict

import pandas as pd

from src.services.analytics import build_volume_records
from src.services.post_processing import detect_plate_typos, infer_product_from_history
from src.utils.cleaners import clean_placa

logger = logging.getLogger(__name__)


def _json_fallback(obj):
    """Converte tipos numpy/pandas para tipos nativos Python (serialização JSON)."""
    import numpy as np
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, pd.Series):
        return obj.tolist()
    return str(obj)


PRODUCT_TO_CLIENT = {
    'LITIO': 'AMG Brasil',
    'LÍTIO': 'AMG Brasil',
    'ÓXIDO DE MAGNÉSIO': 'RHI Magnesita',
    'OXIDO DE MAGNESIO': 'RHI Magnesita',
    'NÍQUEL': 'Atlantic Nickel',
    'NIQUEL': 'Atlantic Nickel',
    'ATLANTIC NICKEL': 'Atlantic Nickel',
    'NÍQUEL- ATLANTIC NICKEL': 'Atlantic Nickel',
    'MANGANÊS': 'Vale',
    'MANGANES': 'Vale',
    'MILHO': '—',
}


def get_cliente(produto: str) -> str:
    """Retorna o nome do cliente com base no produto."""
    if not produto:
        return ''
    prod_upper = str(produto).upper().strip()
    for key, val in PRODUCT_TO_CLIENT.items():
        if key in prod_upper or prod_upper in key:
            return val
    return ''


DEFAULT_PR_MAP = {
    'LITIO': '11049',
    'LÍTIO': '11049',
    'ÓXIDO DE MAGNÉSIO': '11050',
    'OXIDO DE MAGNESIO': '11050',
    'NÍQUEL': '11048',
    'NÍQUEL- ATLANTIC NICKEL': '11048',
    'ATLANTIC NICKEL': '11048',
    'NIQUEL': '11048',
    'MANGANÊS': '11047',
    'MANGANES': '11047',
    'MILHO': '11046'
}

def get_pr_and_motivacao(item, produto):
    # Determine PR
    pr = item.get('PR')
    if not pr:
        sev = item.get('SEV')
        if sev:
            pr = str(sev)
    if not pr and produto:
        prod_upper = str(produto).upper().strip()
        for key, val in DEFAULT_PR_MAP.items():
            if key in prod_upper:
                pr = val
                break
    if not pr:
        pr = '11050'

    # Determine Motivação
    motivacao = 'EGS'
    return pr, motivacao

def format_datetime_str(dt_val):
    if pd.isna(dt_val) or dt_val is None:
        return ""
    try:
        dt = pd.to_datetime(dt_val)
        # Se for exatamente meia-noite (sem hora gravada ou importado de forma simples)
        if dt.time() == pd.Timestamp('2020-01-01 00:00:00').time():
            return dt.strftime('%d/%m/%Y')
        else:
            return dt.strftime('%d/%m/%Y %H:%M')
    except Exception:
        return str(dt_val)

def clean_sev(sev_val):
    if not sev_val or str(sev_val).startswith('TEMP_SEV_') or str(sev_val).lower() == 'nan':
        return ""
    return str(sev_val).strip()

def _safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def match_trips(ex_list, p_list):
    """
    Realiza o Match Bipartido Inteligente para lidar com múltiplas viagens da mesma placa no mesmo dia.
    Propaga Produto, Cliente e calcula Peso Líquido nos registros de saída.
    """
    ok_list = []
    divergencias = []
    matched_p = set()
    matched_ex = set()

    TOLERANCIA_EXATA_KG = 50       # Variação normal de balança (caminhão)
    TOLERANCIA_MAXIMA_KG = 5000    # Acima disso, não força pareamento

    # 1. Match Exato (absorve pequenas variações de pesagem)
    for i, ex in enumerate(ex_list):
        best_p_idx = -1
        for j, p in enumerate(p_list):
            if j in matched_p:
                continue
            diff = abs(_safe_float(ex.get('Peso Bruto')) - _safe_float(p.get('Peso Bruto'))) + abs(_safe_float(ex.get('Tara')) - _safe_float(p.get('Tara')))
            if diff < TOLERANCIA_EXATA_KG:
                best_p_idx = j
                break
        if best_p_idx != -1:
            p = p_list[best_p_idx]
            matched_ex.add(i)
            matched_p.add(best_p_idx)
            peso_liquido = _safe_float(ex.get('Peso Bruto')) - _safe_float(ex.get('Tara'))
            pr, motiv = get_pr_and_motivacao(p if p else ex, ex.get('Produto'))
            ok_list.append({
                'Placa': ex.get('Placa', ''),
                'Data': format_datetime_str(p.get('Data') or ex.get('Data')),
                'Peso Bruto': _safe_float(ex.get('Peso Bruto')),
                'Tara': _safe_float(ex.get('Tara')),
                'Peso Liquido': peso_liquido,
                'Produto': ex.get('Produto', ''),
                'Cliente': get_cliente(ex.get('Produto')),
                'Motivacao': motiv,
                'SEV': clean_sev(p.get('SEV')) if p else '',
                'Detalhe': 'Pesagem exata',
                'Linha': ex.get('Linha'),
                'Aba': ex.get('Aba'),
                'Arquivo': ex.get('Arquivo')
            })

    # 2. Match por Aproximação (Associa viagens com erro de digitação para apontar a diferença)
    for i, ex in enumerate(ex_list):
        if i in matched_ex:
            continue

        best_p_idx = -1
        min_diff = float('inf')
        best_pl_diff = float('inf')
        for j, p in enumerate(p_list):
            if j in matched_p:
                continue
            diff = abs(_safe_float(ex.get('Peso Bruto')) - _safe_float(p.get('Peso Bruto'))) + abs(_safe_float(ex.get('Tara')) - _safe_float(p.get('Tara')))
            # Usar Peso Liquido como desempate quando Bruto+Tara forem equivalentes
            ex_pl = _safe_float(ex.get('Peso Liquido'))
            p_pl = _safe_float(p.get('Peso Liquido'))
            pl_diff = abs(ex_pl - p_pl)
            if diff < min_diff or (diff == min_diff and pl_diff < best_pl_diff):
                min_diff = diff
                best_pl_diff = pl_diff
                best_p_idx = j

        prod_ex = ex.get('Produto', 'Desconhecido')

        # Se a diferença exceder a tolerância máxima, não força o pareamento
        if best_p_idx != -1 and min_diff > TOLERANCIA_MAXIMA_KG:
            best_p_idx = -1

        # Se houver um par disponível dentro da tolerância, vinculamos e apontamos a diferença exata.
        if best_p_idx != -1:
            p = p_list[best_p_idx]
            prod_p = str(p.get('Tipo Carga', '') or '').strip().upper()
            if prod_p in ('NÃO', 'NAO', 'N', '', 'DESCONHECIDO', 'NAN'):
                prod_p = ''
            matched_ex.add(i)
            matched_p.add(best_p_idx)
            pr, motiv = get_pr_and_motivacao(p, prod_ex)
            if prod_p:
                detalhe = f"Bruto/Tara não conferem entre planilha ({prod_ex}) e PDF ({prod_p})."
            else:
                detalhe = f"Bruto/Tara não conferem (planilha: {prod_ex})."
            divergencias.append({
                'Placa': ex.get('Placa', ''),
                'Data': format_datetime_str(p.get('Data') or ex.get('Data')),
                'Status': 'Diferença de Peso',
                'Detalhe': detalhe,
                'Produto': prod_ex,
                'Cliente': get_cliente(prod_ex),
                'Peso Bruto': _safe_float(ex.get('Peso Bruto')),
                'Tara': _safe_float(ex.get('Tara')),
                'Peso Liquido': _safe_float(ex.get('Peso Bruto')) - _safe_float(ex.get('Tara')),
                'Motivacao': motiv,
                'SEV': clean_sev(p.get('SEV')),
                'Linha': ex.get('Linha'),
                'Aba': ex.get('Aba'),
                'Arquivo': ex.get('Arquivo')
            })
        else:
            # Se não sobrou nenhum PDF para fazer par
            pr, motiv = get_pr_and_motivacao(ex, prod_ex)
            divergencias.append({
                'Placa': ex.get('Placa', ''),
                'Data': format_datetime_str(ex.get('Data')),
                'Status': 'Falta no PDF',
                'Detalhe': f"Registro na planilha ({prod_ex}) sem correspondência no PDF.",
                'Produto': prod_ex,
                'Cliente': get_cliente(prod_ex),
                'Peso Bruto': _safe_float(ex.get('Peso Bruto')),
                'Tara': _safe_float(ex.get('Tara')),
                'Peso Liquido': _safe_float(ex.get('Peso Bruto')) - _safe_float(ex.get('Tara')),
                'Motivacao': motiv,
                'SEV': '',
                'Linha': ex.get('Linha'),
                'Aba': ex.get('Aba'),
                'Arquivo': ex.get('Arquivo')
            })

    # 3. O que sobrou no PDF sem registro no Excel
    for j, p in enumerate(p_list):
        if j not in matched_p:
            pr, motiv = get_pr_and_motivacao(p, '')
            divergencias.append({
                'Placa': p.get('Placa', ''),
                'Data': format_datetime_str(p.get('Data')),
                'Status': 'Falta no Excel',
                'Detalhe': 'Registro no PDF sem correspondência na planilha.',
                'Produto': '',
                'Cliente': '',
                'Peso Bruto': _safe_float(p.get('Peso Bruto')),
                'Tara': _safe_float(p.get('Tara')),
                'Peso Liquido': _safe_float(p.get('Peso Bruto')) - _safe_float(p.get('Tara')),
                'Motivacao': motiv,
                'SEV': clean_sev(p.get('SEV'))
            })

    return ok_list, divergencias


def _sort_br_dates(dates: list[str]) -> list[str]:
    """Ordena datas no formato DD/MM/YYYY."""

    def sort_key(d: str) -> tuple[int, int, int]:
        date_part = d.split(" ")[0]
        parts = date_part.split("/")
        if len(parts) == 3:
            try:
                return int(parts[2]), int(parts[1]), int(parts[0])
            except ValueError:
                pass
        return 0, 0, 0

    return sorted(set(dates), key=sort_key)


def _summarize_discarded(df_discarded: pd.DataFrame) -> dict:
    """Resume registros descartados no recorte de período."""
    if df_discarded.empty:
        return {"total": 0, "datas": []}
    return {
        "total": int(len(df_discarded)),
        "datas": _sort_br_dates(df_discarded["Data_Merge"].tolist()),
    }


def calculate_integrity_hash(ok_list: list, divergencias: list, notas_informativas: list) -> str:
    """
    Calcula um hash SHA-256 determinístico dos dados reconciliados para garantir a imutabilidade.
    """
    # Extrair apenas campos estruturais e de pesos que garantem a conformidade
    def sanitize_item(d, item_type):
        return {
            "type": item_type,
            "Placa": str(d.get("Placa", "")).strip().upper(),
            "Data": str(d.get("Data", "")).strip(),
            "Peso Bruto": float(d.get("Peso Bruto") or 0),
            "Tara": float(d.get("Tara") or 0),
            "Peso Liquido": float(d.get("Peso Liquido") or 0),
            "Produto": str(d.get("Produto", "")).strip().upper(),
            "SEV": str(d.get("SEV", "")).strip().upper(),
            "Status": str(d.get("Status", "OK")).strip().upper(),
        }

    sanitized_ok = [sanitize_item(x, "OK") for x in ok_list]
    sanitized_div = [sanitize_item(x, "DIV") for x in divergencias]
    sanitized_info = [sanitize_item(x, "INFO") for x in notas_informativas]

    # Ordenação canônica determinística
    def sort_key(x):
        return (x["Placa"], x["Data"], x["Peso Bruto"], x["Tara"], x["SEV"])

    sanitized_ok.sort(key=sort_key)
    sanitized_div.sort(key=sort_key)
    sanitized_info.sort(key=sort_key)

    payload_structure = {
        "ok": sanitized_ok,
        "divergencias": sanitized_div,
        "notas_informativas": sanitized_info
    }

    payload_json = json.dumps(payload_structure, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload_json.encode('utf-8')).hexdigest()


def reconcile_data(df_excel, df_pdf, filter_date=None, produtos_enviados=None):
    try:
        if df_excel.empty and df_pdf.empty:
            return {"resumo": {"total_processado": 0, "ok": 0, "divergencias": 0}, "divergencias": [], "ok": []}

        logger.info("Iniciando conciliação: Excel=%d registros, PDF=%d registros", len(df_excel), len(df_pdf))

        # Preparar Excel
        discarded_excel = []
        if not df_excel.empty:
            df_ex = df_excel.copy()
            df_ex['Placa'] = df_ex['Placa'].apply(clean_placa)
            df_ex['Data_Merge'] = pd.to_datetime(df_ex['Data'], errors='coerce', dayfirst=True).dt.strftime('%d/%m/%Y')
            
            # Capturar descartados por data ou placa vazia antes de dropar
            invalid_mask = df_ex['Data_Merge'].isna() | (df_ex['Placa'] == '') | df_ex['Placa'].isna()
            df_invalid = df_excel[invalid_mask]
            for idx, row in df_invalid.iterrows():
                linha_excel = int(row.get('Linha', idx + 1))
                aba_excel = str(row.get('Aba', 'Principal'))
                placa_original = str(row.get('Placa', ''))
                data_original = str(row.get('Data', ''))
                motivo = []
                if pd.isna(row.get('Data')) or str(row.get('Data')).strip() == '' or pd.isna(df_ex.loc[idx, 'Data_Merge']):
                    motivo.append("Data inválida ou ausente")
                if clean_placa(placa_original) == '':
                    motivo.append("Placa vazia ou inválida")
                
                discarded_excel.append({
                    "Aba": aba_excel,
                    "Linha": linha_excel,
                    "Placa": placa_original,
                    "Data": data_original,
                    "Produto": str(row.get('Produto', 'N/A')),
                    "Motivo": " e ".join(motivo) or "Dados incompletos"
                })

            antes = len(df_ex)
            df_ex = df_ex.dropna(subset=['Data_Merge', 'Placa'])
            if antes - len(df_ex) > 0:
                logger.warning("Excel: %d registro(s) descartado(s) por placa ou data inválida", antes - len(df_ex))
            
            # Normalizar Toneladas para Kilos
            for col in ['Peso Bruto', 'Tara']:
                if col in df_ex.columns:
                    cond = df_ex[col].apply(lambda x: isinstance(x, (int, float)) and 0 < x < 200)
                    if cond.any():
                        count_norm = cond.sum()
                        placas_affected = df_ex.loc[cond, 'Placa'].tolist()[:5]
                        logger.info("Excel: Normalizando %d valor(es) em '%s' de toneladas para kg (ex: placas %s)", count_norm, col, placas_affected)
                    df_ex[col] = df_ex[col].apply(lambda x: x * 1000 if isinstance(x, (int, float)) and 0 < x < 200 else x)
        else:
            df_ex = pd.DataFrame(columns=['Placa', 'Data_Merge', 'Peso Bruto', 'Tara', 'Produto'])

        # Preparar PDF
        discarded_pdf = []
        if not df_pdf.empty:
            df_p = df_pdf.copy()
            df_p['Placa'] = df_p['Placa'].apply(clean_placa)
            df_p['Data_Merge'] = pd.to_datetime(df_p['Data'], errors='coerce', dayfirst=True).dt.strftime('%d/%m/%Y')
            
            # Capturar descartados por data ou placa vazia antes de dropar
            invalid_mask = df_p['Data_Merge'].isna() | (df_p['Placa'] == '') | df_p['Placa'].isna()
            df_invalid = df_pdf[invalid_mask]
            for idx, row in df_invalid.iterrows():
                placa_original = str(row.get('Placa', ''))
                data_original = str(row.get('Data', ''))
                sev_original = str(row.get('SEV', 'N/A'))
                motivo = []
                if pd.isna(row.get('Data')) or str(row.get('Data')).strip() == '' or pd.isna(df_p.loc[idx, 'Data_Merge']):
                    motivo.append("Data inválida ou ausente")
                if clean_placa(placa_original) == '':
                    motivo.append("Placa vazia ou inválida")
                
                discarded_pdf.append({
                    "SEV": sev_original,
                    "Placa": placa_original,
                    "Data": data_original,
                    "Motivo": " e ".join(motivo) or "Dados incompletos"
                })

            antes_p = len(df_p)
            df_p = df_p.dropna(subset=['Data_Merge', 'Placa'])
            if antes_p - len(df_p) > 0:
                logger.warning("PDF: %d registro(s) descartado(s) por placa ou data inválida", antes_p - len(df_p))
            
            # Normalizar Toneladas para Kilos
            for col in ['Peso Bruto', 'Tara']:
                if col in df_p.columns:
                    cond = df_p[col].apply(lambda x: isinstance(x, (int, float)) and 0 < x < 200)
                    if cond.any():
                        count_norm = cond.sum()
                        placas_affected = df_p.loc[cond, 'Placa'].tolist()[:5]
                        logger.info("PDF: Normalizando %d valor(es) em '%s' de toneladas para kg (ex: placas %s)", count_norm, col, placas_affected)
                    df_p[col] = df_p[col].apply(lambda x: x * 1000 if isinstance(x, (int, float)) and 0 < x < 200 else x)

            # SEV: limpar e preencher vazios com temporários (para rastreabilidade).
            # Cada linha do PDF é tratada como registro individual — SEM agrupamento.
            if 'SEV' in df_p.columns:
                df_p['SEV'] = df_p['SEV'].fillna('').astype(str).str.strip()
                sev_empty = (df_p['SEV'] == '') | (df_p['SEV'].str.lower() == 'nan')
                if sev_empty.any():
                    df_p.loc[sev_empty, 'SEV'] = [f"TEMP_SEV_{uuid.uuid4().hex}" for _ in range(sev_empty.sum())]
                    logger.info("SEVs vazios: %d preenchidos com temporários", sev_empty.sum())

                # Diagnóstico: logar SEVs com 3+ registros (possível anomalia no OpenPort)
                sev_counts = df_p['SEV'].value_counts()
                multi = sev_counts[sev_counts > 2]
                if not multi.empty:
                    logger.warning("SEVs com 3+ registros (possível anomalia): %s", dict(multi))

                logger.info("PDF: %d registros individuais (SEV como campo informativo)",
                            len(df_p))
        else:
            df_p = pd.DataFrame(columns=['Placa', 'Data_Merge', 'Peso Bruto', 'Tara', 'Data', 'Tipo Carga'])

        logger.info("Após preparo: Excel=%d registros, PDF=%d registros",
                     len(df_ex) if not df_ex.empty else 0,
                     len(df_p) if not df_p.empty else 0)

        # Filtro de Data (UI) ou Recorte de Período Automático (ancorado no PDF)
        recorte_aviso = None
        df_ex_discarded = pd.DataFrame()  # Registros Excel descartados pelo recorte de período
        if filter_date:
            df_ex = df_ex[df_ex['Data_Merge'] == filter_date]
            df_p = df_p[df_p['Data_Merge'] == filter_date]
        else:
            if not df_p.empty and not df_ex.empty:
                pdf_dates = pd.to_datetime(df_p['Data_Merge'], format='%d/%m/%Y', errors='coerce').dropna()
                ex_dates_parsed = pd.to_datetime(df_ex['Data_Merge'], format='%d/%m/%Y', errors='coerce')
                ex_dates_valid = ex_dates_parsed.dropna()

                if not pdf_dates.empty and not ex_dates_valid.empty:
                    # Recorte ancorado no PDF (fonte primária): preservar TODO o range do PDF,
                    # cortar apenas o Excel para o período onde o PDF tem dados
                    overall_min = pdf_dates.min()
                    overall_max = pdf_dates.max()

                    if overall_min <= overall_max:
                        ex_in_range = (ex_dates_parsed >= overall_min) & (ex_dates_parsed <= overall_max)
                        pdf_dates_full = pd.to_datetime(df_p['Data_Merge'], format='%d/%m/%Y', errors='coerce')
                        pdf_in_range = (pdf_dates_full >= overall_min) & (pdf_dates_full <= overall_max)

                        df_ex_discarded = df_ex[~ex_in_range]
                        df_p_discarded = df_p[~pdf_in_range]

                        excel_ignorados = _summarize_discarded(df_ex_discarded)
                        pdf_ignorados = _summarize_discarded(df_p_discarded)

                        if excel_ignorados["total"] > 0 or pdf_ignorados["total"] > 0:
                            recorte_aviso = {
                                "periodo_utilizado": {
                                    "inicio": overall_min.strftime('%d/%m/%Y'),
                                    "fim": overall_max.strftime('%d/%m/%Y'),
                                },
                                "excel_ignorados": excel_ignorados,
                                "pdf_ignorados": pdf_ignorados,
                            }
                            logger.info(
                                "Recorte ancorado no PDF: Excel %d ignorados (%s). "
                                "Período do PDF: %s a %s",
                                excel_ignorados["total"],
                                ", ".join(excel_ignorados["datas"]) or "—",
                                recorte_aviso["periodo_utilizado"]["inicio"],
                                recorte_aviso["periodo_utilizado"]["fim"],
                            )

                        df_ex = df_ex[ex_in_range]
                        df_p = df_p[pdf_in_range]

        # Motor de Conciliação
        divergencias = []
        ok_list = []

        ex_records = df_ex.to_dict('records')
        p_records = df_p.to_dict('records')

        ex_grouped = defaultdict(list)
        for r in ex_records:
            ex_grouped[f"{r['Placa']}_{r['Data_Merge']}"].append(r)

        p_grouped = defaultdict(list)
        for r in p_records:
            p_grouped[f"{r['Placa']}_{r['Data_Merge']}"].append(r)

        all_keys = set(ex_grouped.keys()).union(set(p_grouped.keys()))

        # Identificar placas do PDF que ficarão sem par (diagnóstico)
        pdf_only_keys = set(p_grouped.keys()) - set(ex_grouped.keys())
        if pdf_only_keys:
            logger.warning("Placas do PDF sem correspondência no Excel (%d): %s",
                           len(pdf_only_keys), sorted(pdf_only_keys))

        for k in all_keys:
            o, d = match_trips(ex_grouped[k], p_grouped[k])
            ok_list.extend(o)
            divergencias.extend(d)

        # Pós-processamento: Detecção de erros de digitação de placa
        divergencias = detect_plate_typos(divergencias)

        # Pós-processamento: Dedução de produto por histórico de placas
        divergencias = infer_product_from_history(ok_list, divergencias)

        # Filtro por Produto (pós-matching): excluir divergências "Falta no Excel"
        # cuja placa NÃO existe em nenhum Excel enviado (outro produto)
        produtos_invalidos = []
        if produtos_enviados and not df_ex.empty:
            placas_excel = set(df_ex['Placa'].dropna().astype(str).str.strip().str.upper())
            novas_divs = []
            for d in divergencias:
                placa_div = d.get('Placa', '').strip().upper()
                if d.get('Status') == 'Falta no Excel' and placa_div not in placas_excel:
                    produtos_invalidos.append(d)
                else:
                    novas_divs.append(d)
            if produtos_invalidos:
                logger.info(
                    "Filtro por produto: %d divergência(s) removida(s) "
                    "(placa não encontrada em nenhum Excel enviado). "
                    "Produtos: %s",
                    len(produtos_invalidos), list(produtos_enviados),
                )
            divergencias = novas_divs

        # Pós-processamento: Detecção de Erros de Data no Excel
        # Para cada divergência "Falta no Excel", buscar nos registros descartados
        # pelo recorte de período um registro com mesma placa e pesos compatíveis.
        # Se encontrado, é provável erro de digitação de data na planilha.
        if not df_ex_discarded.empty:
            TOLERANCIA_DATA_KG = 100  # tolerância de peso para match secundário
            discarded_records = df_ex_discarded.to_dict('records')
            for d in divergencias:
                if d.get('Status') != 'Falta no Excel':
                    continue
                placa_div = str(d.get('Placa', '')).strip().upper()
                bruto_div = d.get('Peso Bruto', 0) or 0
                tara_div = d.get('Tara', 0) or 0

                for disc in discarded_records:
                    placa_disc = str(disc.get('Placa', '')).strip().upper()
                    if placa_disc != placa_div:
                        continue
                    bruto_disc = disc.get('Peso Bruto', 0) or 0
                    tara_disc = disc.get('Tara', 0) or 0
                    diff = abs(bruto_div - bruto_disc) + abs(tara_div - tara_disc)
                    if diff <= TOLERANCIA_DATA_KG:
                        # Encontrou correspondência — erro de digitação de data
                        data_errada = disc.get('Data_Merge', '')
                        if not data_errada:
                            try:
                                data_errada = pd.to_datetime(disc.get('Data'), dayfirst=True).strftime('%d/%m/%Y')
                            except Exception:
                                data_errada = str(disc.get('Data', '?'))
                        d['linha_erro_data'] = disc.get('Linha')
                        d['aba_erro_data'] = disc.get('Aba', '')
                        d['arquivo_erro_data'] = disc.get('Arquivo', '')
                        d['data_errada_excel'] = data_errada
                        d['Detalhe'] = (
                            f"Registro no PDF sem correspondência na planilha. "
                            f"⚠️ Possível erro de digitação: encontrado registro com mesma placa e pesos "
                            f"na Linha {disc.get('Linha')} (Aba '{disc.get('Aba', '?')}') do arquivo "
                            f"'{disc.get('Arquivo', '?')}', porém com data {data_errada}."
                        )
                        logger.warning(
                            "Erro de data detectado: Placa %s — Excel Linha %s (Aba '%s', Arquivo '%s') "
                            "data errada %s vs PDF %s",
                            placa_div, disc.get('Linha'), disc.get('Aba'),
                            disc.get('Arquivo'), data_errada, d.get('Data', '?'),
                        )
                        break  # Encontrou o match, não precisa continuar

        # Pós-processamento: Pesagens Incompletas (Tara = 0 com viagem OK no dia)
        notas_informativas = []
        restantes_divergencias = []

        for d in divergencias:
            tara_val = d.get('Tara')
            is_tara_zero = False
            try:
                if tara_val is not None and float(tara_val) == 0:
                    is_tara_zero = True
            except (ValueError, TypeError):
                pass

            if d.get('Status') == 'Falta no Excel' and is_tara_zero:
                placa_div = d.get('Placa')
                data_str = d.get('Data', '')
                data_dia_div = data_str.split(' ')[0] if data_str else ''

                tem_viagem_ok = False
                if placa_div and data_dia_div:
                    for ok in ok_list:
                        ok_placa = ok.get('Placa')
                        ok_data = ok.get('Data', '')
                        ok_data_dia = ok_data.split(' ')[0] if ok_data else ''
                        if ok_placa == placa_div and ok_data_dia == data_dia_div:
                            tem_viagem_ok = True
                            break

                if tem_viagem_ok:
                    d['Status'] = 'Pesagem Incompleta'
                    d['Detalhe'] = 'Pesagem incompleta registrada no OpenPort (Tara=0), com viagem correspondente concluída no dia.'
                    notas_informativas.append(d)
                else:
                    restantes_divergencias.append(d)
            else:
                restantes_divergencias.append(d)

        divergencias = restantes_divergencias

        total_viagens = len(ok_list) + len(divergencias) + len(notas_informativas)

        logger.info("Conciliação finalizada: %d OK, %d divergências, %d pesagens incompletas (total %d viagens)",
                     len(ok_list), len(divergencias), len(notas_informativas), total_viagens)

        # Ordenação Cronológica Real
        def sort_key(item):
            try:
                return pd.to_datetime(item['Data'], dayfirst=True)
            except Exception:
                return pd.Timestamp.min

        divergencias.sort(key=sort_key)
        ok_list.sort(key=sort_key)
        notas_informativas.sort(key=sort_key)

        # Preencher Cliente para divergências que tiveram produto deduzido e injetar viagens OK do dia
        for d in divergencias + notas_informativas:
            if not d.get('Cliente') and d.get('Produto'):
                d['Cliente'] = get_cliente(d['Produto'])
            
            placa_div = d.get('Placa')
            data_str = d.get('Data', '')
            data_dia_div = data_str.split(' ')[0] if data_str else ''
            if placa_div and data_dia_div:
                viagens_ok = sum(1 for ok in ok_list if ok.get('Placa') == placa_div and ok.get('Data', '').split(' ')[0] == data_dia_div)
                if viagens_ok > 0:
                    d['viagens_ok_no_dia'] = viagens_ok

        # Numerar Ítem sequencial (ordem cronológica)
        for i, d in enumerate(divergencias, 1):
            d['Ítem'] = i
        for i, o in enumerate(ok_list, 1):
            o['Ítem'] = i
        for i, n in enumerate(notas_informativas, 1):
            n['Ítem'] = i

        # Coletar metadados de produtos para o frontend
        all_produtos = set()
        for item in ok_list + divergencias + notas_informativas:
            prod = item.get('Produto', '')
            # Limpar sufixos de dedução para agrupamento
            prod_clean = prod.replace(' (Deduzido)', '') if prod else ''
            if prod_clean and prod_clean not in ('Não Identificado', '') and not prod_clean.startswith('Ambíguo'):
                all_produtos.add(prod_clean)

        result = {
            "resumo": {
                "total_processado": total_viagens,
                "ok": len(ok_list),
                "divergencias": len(divergencias),
                "incompletas": len(notas_informativas)
            },
            "divergencias": divergencias,
            "ok": ok_list,
            "notas_informativas": notas_informativas,
            "produtos_detectados": sorted(list(all_produtos)),
            "volume": build_volume_records(ok_list, divergencias),
        }
        avisos = {}
        if recorte_aviso:
            avisos["recorte_periodo"] = recorte_aviso
        if produtos_invalidos:
            infos = []
            for d in produtos_invalidos:
                data_raw = d.get('Data', '')
                try:
                    dm = pd.to_datetime(data_raw, dayfirst=True).strftime('%d/%m/%Y')
                except Exception:
                    dm = data_raw.split(' ')[0] if ' ' in str(data_raw) else str(data_raw)
                infos.append({"Placa": d.get("Placa", ""), "Data_Merge": dm})
            avisos["produtos_nao_enviados"] = {
                "excluidos": len(produtos_invalidos),
                "detalhes": _summarize_discarded(pd.DataFrame(infos)),
                "produtos_recebidos": [str(p) for p in (produtos_enviados or [])],
            }
        
        # Adicionar avisos de registros descartados por data ou placa corrompida
        if discarded_excel or discarded_pdf:
            avisos["registros_descartados"] = {
                "excel": discarded_excel,
                "pdf": discarded_pdf
            }

        if avisos:
            result["avisos"] = avisos

        # Garantir serialização JSON (converter numpy types)
        result = json.loads(json.dumps(result, default=_json_fallback))

        # Calcular hash de integridade determinístico nos dados já serializados
        hash_val = calculate_integrity_hash(
            result.get("ok", []),
            result.get("divergencias", []),
            result.get("notas_informativas", [])
        )
        result["integrity_hash"] = hash_val

        return result
    except Exception as e:
        logger.error(f"Erro ao conciliar dados: {e}\n{traceback.format_exc()}")
        return {"error": str(e)}
