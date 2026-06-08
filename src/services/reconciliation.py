import logging
import traceback
import uuid
import pandas as pd
from collections import defaultdict

from src.utils.cleaners import clean_placa
from src.services.post_processing import detect_plate_typos, infer_product_from_history

logger = logging.getLogger(__name__)

def match_trips(ex_list, p_list):
    """
    Realiza o Match Bipartido Inteligente para lidar com múltiplas viagens da mesma placa no mesmo dia.
    Propaga Produto, Cliente e calcula Peso Líquido nos registros de saída.
    """
    ok_list = []
    divergencias = []
    matched_p = set()
    matched_ex = set()
    
    # 1. Match Exato (tolerância de 0.1kg para absorver dízimas da conversão float)
    for i, ex in enumerate(ex_list):
        best_p_idx = -1
        for j, p in enumerate(p_list):
            if j in matched_p:
                continue
            diff = abs(ex['Peso Bruto'] - p['Peso Bruto']) + abs(ex['Tara'] - p['Tara'])
            if diff < 0.1: 
                best_p_idx = j
                break
        if best_p_idx != -1:
            matched_ex.add(i)
            matched_p.add(best_p_idx)
            peso_liquido = ex['Peso Bruto'] - ex['Tara']
            ok_list.append({
                'Placa': ex['Placa'],
                'Data': ex['Data_Merge'],
                'Peso Bruto': ex['Peso Bruto'],
                'Tara': ex['Tara'],
                'Peso Liquido': peso_liquido,
                'Produto': ex.get('Produto', ''),
                'Cliente': ex.get('Cliente', ''),
                'Detalhe': 'Pesagem exata'
            })
            
    # 2. Match por Aproximação (Associa viagens com erro de digitação para apontar a diferença)
    for i, ex in enumerate(ex_list):
        if i in matched_ex: 
            continue
            
        best_p_idx = -1
        min_diff = float('inf')
        for j, p in enumerate(p_list):
            if j in matched_p: 
                continue
            diff = abs(ex['Peso Bruto'] - p['Peso Bruto']) + abs(ex['Tara'] - p['Tara'])
            if diff < min_diff:
                min_diff = diff
                best_p_idx = j
        
        prod_ex = ex.get('Produto', 'Desconhecido')
        cliente_ex = ex.get('Cliente', '')
        
        # Se houver um par disponível, nós vinculamos e apontamos a diferença exata.
        if best_p_idx != -1:
            p = p_list[best_p_idx]
            prod_p = p.get('Tipo Carga', 'Desconhecido')
            matched_ex.add(i)
            matched_p.add(best_p_idx)
            divergencias.append({
                'Placa': ex['Placa'],
                'Data': ex['Data_Merge'],
                'Status': 'Diferença de Peso',
                'Detalhe': f"[Planilha: {prod_ex}] Bruto {ex['Peso Bruto']} / Tara {ex['Tara']} != [PDF: {prod_p}] Bruto {p['Peso Bruto']} / Tara {p['Tara']}",
                'Produto': prod_ex,
                'Cliente': cliente_ex,
                'Peso Bruto': ex['Peso Bruto'],
                'Tara': ex['Tara']
            })
        else:
            # Se não sobrou nenhum PDF para fazer par
            divergencias.append({
                'Placa': ex['Placa'],
                'Data': ex['Data_Merge'],
                'Status': 'Falta no PDF',
                'Detalhe': f"[Planilha: {prod_ex}] Excel acusa Bruto {ex['Peso Bruto']}kg / Tara {ex['Tara']}kg, mas não há viagem correspondente no PDF.",
                'Produto': prod_ex,
                'Cliente': cliente_ex,
                'Peso Bruto': ex['Peso Bruto'],
                'Tara': ex['Tara']
            })
            
    # 3. O que sobrou no PDF sem registro no Excel
    for j, p in enumerate(p_list):
        if j not in matched_p:
            prod_p = p.get('Tipo Carga', 'Desconhecido')
            divergencias.append({
                'Placa': p['Placa'],
                'Data': p['Data_Merge'],
                'Status': 'Falta no Excel',
                'Detalhe': f"[PDF: {prod_p}] OpenPort acusa Bruto {p['Peso Bruto']}kg / Tara {p['Tara']}kg. Não há registro no Excel.",
                'Produto': '',
                'Cliente': '',
                'Peso Bruto': p['Peso Bruto'],
                'Tara': p['Tara']
            })
            
    return ok_list, divergencias


def _sort_br_dates(dates: list[str]) -> list[str]:
    """Ordena datas no formato DD/MM/YYYY."""

    def sort_key(d: str) -> tuple[int, int, int]:
        parts = d.split("/")
        if len(parts) == 3:
            return int(parts[2]), int(parts[1]), int(parts[0])
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


def reconcile_data(df_excel, df_pdf, filter_date=None):
    try:
        if df_excel.empty and df_pdf.empty:
            return {"resumo": {"total_processado": 0, "ok": 0, "divergencias": 0}, "divergencias": [], "ok": []}

        # Preparar Excel
        if not df_excel.empty:
            df_ex = df_excel.copy()
            df_ex['Placa'] = df_ex['Placa'].apply(clean_placa)
            df_ex['Data_Merge'] = pd.to_datetime(df_ex['Data'], errors='coerce').dt.strftime('%d/%m/%Y')
            df_ex = df_ex.dropna(subset=['Data_Merge', 'Placa'])
        else:
            df_ex = pd.DataFrame(columns=['Placa', 'Data_Merge', 'Peso Bruto', 'Tara', 'Produto', 'Cliente'])

        # Preparar PDF
        if not df_pdf.empty:
            df_p = df_pdf.copy()
            df_p['Placa'] = df_p['Placa'].apply(clean_placa)
            df_p['Data_Merge'] = pd.to_datetime(df_p['Data'], errors='coerce').dt.strftime('%d/%m/%Y')
            df_p = df_p.dropna(subset=['Data_Merge', 'Placa'])
            
            # Agrupar por SEV mantendo a maior pesagem e o tipo de carga
            if 'SEV' in df_p.columns:
                df_p['SEV'] = df_p['SEV'].fillna('').astype(str).str.strip()
                # Tratar SEVs vazios ou nan para evitar que se agrupem incorretamente
                sev_mask = (df_p['SEV'] == '') | (df_p['SEV'].str.lower() == 'nan')
                if sev_mask.any():
                    df_p.loc[sev_mask, 'SEV'] = [f"TEMP_SEV_{uuid.uuid4().hex}" for _ in range(sev_mask.sum())]
                
                # Ordenar por Peso Bruto decrescente para priorizar a pesagem carregada no topo do grupo
                df_p = df_p.sort_values(by='Peso Bruto', ascending=False)
                
                agg_dict = {
                    'Placa': 'first',
                    'Data_Merge': 'first',
                    'Data': 'first',
                    'Peso Bruto': 'max',
                    'Tara': 'max'
                }
                if 'Tipo Carga' in df_p.columns:
                    # 'first' pegará o Tipo Carga do registro com maior Peso Bruto (carregado)
                    agg_dict['Tipo Carga'] = 'first'
                df_p = df_p.groupby('SEV', as_index=False).agg(agg_dict)
        else:
            df_p = pd.DataFrame(columns=['Placa', 'Data_Merge', 'Peso Bruto', 'Tara', 'Data', 'Tipo Carga'])

        # Filtro de Data (UI) ou Recorte de Período Automático (Inteligência Bidirecional)
        recorte_aviso = None
        if filter_date:
            df_ex = df_ex[df_ex['Data_Merge'] == filter_date]
            df_p = df_p[df_p['Data_Merge'] == filter_date]
        else:
            if not df_p.empty and not df_ex.empty:
                pdf_dates = pd.to_datetime(df_p['Data_Merge'], format='%d/%m/%Y', errors='coerce').dropna()
                ex_dates_parsed = pd.to_datetime(df_ex['Data_Merge'], format='%d/%m/%Y', errors='coerce')
                ex_dates_valid = ex_dates_parsed.dropna()

                if not pdf_dates.empty and not ex_dates_valid.empty:
                    # Interseção de períodos: usar o range onde AMBOS têm dados
                    overall_min = max(pdf_dates.min(), ex_dates_valid.min())
                    overall_max = min(pdf_dates.max(), ex_dates_valid.max())

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
                                "Recorte de período: Excel %d ignorados (%s), PDF %d ignorados (%s). "
                                "Período utilizado: %s a %s",
                                excel_ignorados["total"],
                                ", ".join(excel_ignorados["datas"]) or "—",
                                pdf_ignorados["total"],
                                ", ".join(pdf_ignorados["datas"]) or "—",
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
        
        for k in all_keys:
            o, d = match_trips(ex_grouped[k], p_grouped[k])
            ok_list.extend(o)
            divergencias.extend(d)

        # Pós-processamento: Detecção de erros de digitação de placa
        divergencias = detect_plate_typos(divergencias)
        
        # Pós-processamento: Dedução de produto por histórico de placas
        divergencias = infer_product_from_history(ok_list, divergencias)

        total_viagens = len(ok_list) + len(divergencias)

        # Ordenação Cronológica Real
        def sort_key(item):
            try:
                return pd.to_datetime(item['Data'], format='%d/%m/%Y')
            except Exception:
                return pd.Timestamp.min

        divergencias.sort(key=sort_key)
        ok_list.sort(key=sort_key)

        # Coletar metadados de produtos e clientes para o frontend
        all_produtos = set()
        clientes_por_produto = {}
        for item in ok_list + divergencias:
            prod = item.get('Produto', '')
            cliente = item.get('Cliente', '')
            # Limpar sufixos de dedução para agrupamento
            prod_clean = prod.replace(' (Deduzido)', '') if prod else ''
            if prod_clean and prod_clean not in ('Não Identificado', '') and not prod_clean.startswith('Ambíguo'):
                all_produtos.add(prod_clean)
                if cliente:
                    if prod_clean not in clientes_por_produto:
                        clientes_por_produto[prod_clean] = set()
                    clientes_por_produto[prod_clean].add(cliente)
        
        # Converter sets para listas para serialização JSON
        clientes_dict = {k: sorted(list(v)) for k, v in clientes_por_produto.items()}

        from src.services.analytics import build_volume_records

        result = {
            "resumo": {
                "total_processado": total_viagens,
                "ok": len(ok_list),
                "divergencias": len(divergencias)
            },
            "divergencias": divergencias,
            "ok": ok_list,
            "produtos_detectados": sorted(list(all_produtos)),
            "clientes_por_produto": clientes_dict,
            "volume": build_volume_records(ok_list, divergencias),
        }
        if recorte_aviso:
            result["avisos"] = {"recorte_periodo": recorte_aviso}
        return result
    except Exception as e:
        logger.error(f"Erro ao conciliar dados: {e}\n{traceback.format_exc()}")
        return {"error": str(e)}
