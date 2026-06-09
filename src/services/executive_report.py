import re
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Tuple
from src.services.post_processing import levenshtein_distance


def _format_date_to_local(date_str: str) -> str:
    """Converte data UTC ISO para o horário local de Salvador (UTC-3) formatado."""
    if not date_str:
        return "Data não disponível"
    try:
        dt_utc = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        tz_ba = timezone(timedelta(hours=-3))
        return dt_utc.astimezone(tz_ba).strftime("%d/%m/%Y às %H:%M:%S")
    except Exception:
        return date_str

def _extract_weights_from_detail(detail: str) -> Tuple[float, float]:
    """Extrai Peso Excel e Peso PDF a partir da string de Detalhe da divergência."""
    match = re.findall(r"Bruto (\d+(?:\.\d+)?)", detail)
    if len(match) >= 2:
        return float(match[0]), float(match[1])
    return 0.0, 0.0

def _format_kg(val: float) -> str:
    """Formata valor em kg para padrão brasileiro (ex: 45.000)."""
    try:
        return f"{int(val):,}".replace(",", ".")
    except Exception:
        return "0"

def _format_ton(val: float) -> str:
    """Formata valor em toneladas para padrão brasileiro (ex: 45,00 t)."""
    try:
        return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"

def generate_executive_report_html(payload: Dict[str, Any], file_names: List[str] = None) -> str:
    """
    Gera um documento HTML premium com o Relatório Executivo de Não Conformidade.
    Contém estilização dedicada para visualização em tela e regras de impressão (@media print) para A4.
    """
    if file_names is None:
        file_names = payload.get("file_names", [])

    run_id = payload.get("run_id", "Não informado")
    created_at = _format_date_to_local(payload.get("created_at", ""))
    resumo = payload.get("resumo", {})
    total_proc = resumo.get("total_processado", 0)
    total_ok = resumo.get("ok", 0)
    total_div = resumo.get("divergencias", 0)
    
    kpi_accuracy = (total_ok / total_proc * 100) if total_proc > 0 else 0.0

    # Calcular volume total auditado (em toneladas)
    # Procuramos nos registros OK e somamos os pesos líquidos
    total_toneladas_ok = 0.0
    for ok_item in payload.get("ok", []):
        peso_liq = ok_item.get("Peso Liquido") or (ok_item.get("Peso Bruto", 0) - ok_item.get("Tara", 0))
        total_toneladas_ok += (peso_liq / 1000.0)

    # Agrupar divergências por categoria de forma organizada e limpa
    divergencias_raw = payload.get("divergencias", [])
    grouped_divs = defaultdict(list)
    for div in divergencias_raw:
        status = div.get("Status", "Outros")
        grouped_divs[status].append(div)

    # Determinar classificação de conformidade
    if kpi_accuracy >= 98:
        classificacao = "EXCELENTE"
        classificacao_class = "status-green"
    elif kpi_accuracy >= 90:
        classificacao = "ATENÇÃO"
        classificacao_class = "status-yellow"
    else:
        classificacao = "CRÍTICO"
        classificacao_class = "status-red"

    # Determinar datas inicial/final da auditoria para o cabeçalho
    todas_datas = []
    for item in payload.get("ok", []) + payload.get("divergencias", []):
        d = item.get("Data")
        if d:
            todas_datas.append(d)
            
    periodo_label = "Não especificado"
    if todas_datas:
        def parse_date(d_str):
            try:
                return datetime.strptime(d_str, "%d/%m/%Y")
            except:
                return datetime.min
        datas_ordenadas = sorted(set(todas_datas), key=parse_date)
        if len(datas_ordenadas) == 1:
            periodo_label = datas_ordenadas[0]
        else:
            periodo_label = f"{datas_ordenadas[0]} a {datas_ordenadas[-1]}"

    # --- MONTAGEM DO HTML ---
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório Executivo de Não Conformidade — CODEBA</title>
    <style>
        :root {{
            --primary: #0F172A;
            --primary-light: #1E293B;
            --accent: #1D4ED8;
            --accent-light: #EFF6FF;
            --text-main: #334155;
            --text-dark: #0F172A;
            --border-color: #E2E8F0;
            --bg-light: #F8FAFC;
            --success: #15803D;
            --success-light: #DCFCE7;
            --warning: #B45309;
            --warning-light: #FEF3C7;
            --danger: #B91C1C;
            --danger-light: #FEE2E2;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: var(--text-main);
            background-color: #E2E8F0;
            line-height: 1.5;
            padding: 40px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        /* Container do Relatório (Simulação de A4 na tela) */
        .report-page {{
            background: #ffffff;
            width: 100%;
            max-width: 800px;
            min-height: 1120px;
            padding: 50px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
            border-radius: 8px;
            position: relative;
            display: flex;
            flex-direction: column;
        }}

        /* Barra flutuante de ações */
        .action-bar {{
            width: 100%;
            max-width: 800px;
            margin-bottom: 15px;
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 18px;
            background-color: var(--accent);
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.9em;
            cursor: pointer;
            text-decoration: none;
            transition: background 0.2s;
        }}

        .btn:hover {{
            background-color: #1e40af;
        }}

        .btn-secondary {{
            background-color: #64748B;
        }}

        .btn-secondary:hover {{
            background-color: #475569;
        }}

        /* Cabeçalho do Relatório */
        .header-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
            border-bottom: 2px solid var(--primary);
        }}

        .header-logo {{
            width: 160px;
            padding-bottom: 15px;
            vertical-align: middle;
        }}

        .header-titles {{
            padding-bottom: 15px;
            text-align: right;
            vertical-align: middle;
        }}

        .header-titles h1 {{
            font-size: 1.15em;
            font-weight: 800;
            color: var(--primary);
            letter-spacing: 0.5px;
            margin-bottom: 3px;
        }}

        .header-titles h2 {{
            font-size: 0.85em;
            font-weight: 600;
            color: #64748B;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}

        .header-titles h3 {{
            font-size: 1.1em;
            font-weight: 700;
            color: var(--accent);
        }}

        /* Metadados e Informações Gerais */
        .meta-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            background-color: var(--bg-light);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 15px 20px;
            margin-bottom: 30px;
            font-size: 0.88em;
        }}

        .meta-item strong {{
            color: var(--text-dark);
        }}

        /* Grid de KPIs */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 35px;
        }}

        .kpi-card {{
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 12px 15px;
            text-align: center;
            background-color: #ffffff;
        }}

        .kpi-card.highlight {{
            background-color: var(--accent-light);
            border-color: #BFDBFE;
        }}

        .kpi-value {{
            font-size: 1.4em;
            font-weight: 800;
            color: var(--text-dark);
            margin-bottom: 3px;
        }}

        .kpi-label {{
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
            color: #64748B;
            letter-spacing: 0.5px;
        }}

        .status-badge {{
            display: inline-block;
            padding: 4px 10px;
            font-size: 0.8em;
            font-weight: 700;
            border-radius: 20px;
            text-transform: uppercase;
        }}

        .status-green {{ background-color: var(--success-light); color: var(--success); }}
        .status-yellow {{ background-color: var(--warning-light); color: var(--warning); }}
        .status-red {{ background-color: var(--danger-light); color: var(--danger); }}

        /* Seções e Listas de Divergências */
        .section-title {{
            font-size: 1.1em;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 12px;
            border-left: 4px solid var(--accent);
            padding-left: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .description-block {{
            font-size: 0.9em;
            margin-bottom: 25px;
            color: #475569;
        }}

        .table-title {{
            font-size: 0.92em;
            font-weight: 700;
            color: var(--primary);
            margin: 20px 0 8px 0;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .executive-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.82em;
            margin-bottom: 30px;
            border: 1px solid var(--border-color);
        }}

        .executive-table th {{
            background-color: var(--bg-light);
            color: var(--text-dark);
            font-weight: 700;
            text-align: left;
            padding: 8px 12px;
            border-bottom: 2px solid var(--border-color);
        }}

        .executive-table td {{
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-color);
            vertical-align: middle;
        }}

        .executive-table tr:nth-child(even) {{
            background-color: #FAF8F6;
        }}

        .text-right {{ text-align: right !important; }}
        .text-center {{ text-align: center !important; }}
        
        .badge-table {{
            display: inline-block;
            padding: 2px 6px;
            font-size: 0.85em;
            font-weight: 600;
            border-radius: 4px;
        }}

        /* Parecer do Auditor */
        .parecer-box {{
            background-color: var(--bg-light);
            border: 1px solid var(--border-color);
            border-left: 4px solid var(--primary);
            border-radius: 4px;
            padding: 20px;
            margin-top: auto;
            margin-bottom: 40px;
            font-size: 0.88em;
        }}

        .parecer-box h4 {{
            font-size: 1em;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 8px;
            text-transform: uppercase;
        }}

        .parecer-box p {{
            margin-bottom: 10px;
        }}

        .parecer-box ul {{
            padding-left: 20px;
        }}

        .parecer-box li {{
            margin-bottom: 5px;
        }}

        /* Área de Assinatura */
        .signatures {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 50px;
            margin-top: 20px;
            padding-top: 30px;
            border-top: 1px solid var(--border-color);
        }}

        .signature-block {{
            text-align: center;
            font-size: 0.85em;
        }}

        .signature-line {{
            width: 80%;
            margin: 0 auto 8px auto;
            border-top: 1px solid #94A3B8;
        }}

        .signature-title {{
            color: #64748B;
            font-size: 0.9em;
            margin-top: 2px;
        }}

        /* Regras Específicas de Impressão */
        @media print {{
            body {{
                background-color: #ffffff;
                padding: 0;
            }}

            .report-page {{
                box-shadow: none;
                padding: 0;
                width: 100%;
                max-width: 100%;
                min-height: auto;
            }}

            .no-print {{
                display: none !important;
            }}

            .page-break {{
                page-break-before: always;
            }}

            @page {{
                size: A4;
                margin: 20mm;
            }}
        }}
    </style>
</head>
<body>

    <!-- Barra de Ações (Apenas em tela) -->
    <div class="action-bar no-print">
        <button class="btn btn-secondary" onclick="window.close()"><i class="ph ph-x"></i> Fechar Janela</button>
        <button class="btn" onclick="window.print()"><i class="ph ph-printer"></i> Imprimir / Salvar PDF</button>
    </div>

    <!-- Página do Relatório -->
    <div class="report-page">
        
        <!-- Tabela do Cabeçalho -->
        <table class="header-table">
            <tr>
                <td class="header-logo">
                    <img src="/static/Logo CODEBA.png" alt="CODEBA" style="height: 50px; display: block;">
                </td>
                <td class="header-titles">
                    <h1>COMPANHIA DOCAS DO ESTADO DA BAHIA</h1>
                    <h2>SUPERINTENDÊNCIA DE OPERAÇÕES PORTUÁRIAS — SUPORT</h2>
                    <h3>RELATÓRIO EXECUTIVO DE NÃO CONFORMIDADE</h3>
                </td>
            </tr>
        </table>

        <!-- Metadados -->
        <div class="meta-grid">
            <div class="meta-item"><strong>ID da Auditoria:</strong> <code>{run_id}</code></div>
            <div class="meta-item"><strong>Data de Emissão:</strong> {created_at}</div>
            <div class="meta-item"><strong>Período Auditado:</strong> {periodo_label}</div>
            <div class="meta-item"><strong>Arquivos da Execução:</strong> {', '.join(file_names) if file_names else 'N/A'}</div>
        </div>

        <h3 class="section-title">Resumo Operacional</h3>
        <p class="description-block">
            Este relatório descreve a conciliação física e documental entre os registros de pesagem digitados manualmente pelos operadores na balança manual (Excel) e os registros de transações automatizados extraídos do sistema OpenPort (PDF) na tela 7015 do Porto de Ilhéus.
        </p>

        <!-- KPIs -->
        <div class="kpi-grid">
            <div class="kpi-card highlight">
                <div class="kpi-value">{kpi_accuracy:.2f}%</div>
                <div class="kpi-label">Acurácia Documental</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">{_format_ton(total_toneladas_ok)} t</div>
                <div class="kpi-label">Volume Conciliado</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">{total_proc}</div>
                <div class="kpi-label">Total de Viagens</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">
                    <span class="status-badge {classificacao_class}">{classificacao}</span>
                </div>
                <div class="kpi-label">Classificação</div>
            </div>
        </div>

        <h3 class="section-title">Análise de Não Conformidades</h3>
        
        {"" if divergencias_raw else "<p class='description-block' style='font-style: italic;'>Nenhuma inconsistência foi identificada neste período. Todas as pesagens estão em conformidade.</p>"}
"""

    has_page_break = False

    # 1. Tabela: Diferenças de Peso
    divs_peso = grouped_divs.get("Diferença de Peso", [])
    if divs_peso:
        html += f"""
        <div class="table-title">⚠️ Divergências de Carga (Peso Divergente) — {len(divs_peso)} ocorrência(s)</div>
        <table class="executive-table">
            <thead>
                <tr>
                    <th>Placa</th>
                    <th class="text-center">SEV</th>
                    <th class="text-center">Data</th>
                    <th>Produto</th>
                    <th class="text-right">Peso Excel (kg)</th>
                    <th class="text-right">Peso PDF (kg)</th>
                    <th class="text-right">Desvio (kg)</th>
                    <th class="text-right">Variação (%)</th>
                </tr>
            </thead>
            <tbody>
        """
        for item in divs_peso:
            placa = item.get("Placa", "N/A")
            sev = item.get("SEV", "N/A")
            data = item.get("Data", "N/A")
            produto = item.get("Produto", "N/A")
            detalhe = item.get("Detalhe", "")
            
            ex_bruto, pdf_bruto = _extract_weights_from_detail(detalhe)
            diff_abs = abs(pdf_bruto - ex_bruto)
            diff_pct = (diff_abs / ex_bruto * 100) if ex_bruto > 0 else 0.0

            html += f"""
                <tr>
                    <td><strong>{placa}</strong></td>
                    <td class="text-center">{sev if (sev and not sev.startswith('TEMP_SEV_')) else '—'}</td>
                    <td class="text-center">{data}</td>
                    <td>{produto}</td>
                    <td class="text-right">{_format_kg(ex_bruto)}</td>
                    <td class="text-right">{_format_kg(pdf_bruto)}</td>
                    <td class="text-right" style="color: var(--danger); font-weight: 600;">{_format_kg(diff_abs)}</td>
                    <td class="text-right" style="color: var(--danger); font-weight: 600;">{diff_pct:.2f}%</td>
                </tr>
            """
        html += """
            </tbody>
        </table>
        """
        has_page_break = True

    # 2. Tabela: Falta no Excel (Viagem Omitida no Controle Manual)
    divs_falta_excel = grouped_divs.get("Falta no Excel", [])
    if divs_falta_excel:
        # Se já colocamos uma tabela grande, colocamos quebra de página se for imprimir mais de uma
        class_page_break = "class='page-break'" if has_page_break else ""
        html += f"""
        <div {class_page_break} style="margin-top: 25px;"></div>
        <div class="table-title">⚠️ Omissões no Controle Manual (Balança Manual) — {len(divs_falta_excel)} ocorrência(s)</div>
        <p class="description-block" style="margin-bottom: 10px;">
            Pesagens registradas no sistema automático OpenPort, mas ausentes na planilha manual do balanceiro.
        </p>
        <table class="executive-table">
            <thead>
                <tr>
                    <th>Placa</th>
                    <th class="text-center">SEV</th>
                    <th class="text-center">Data</th>
                    <th>Produto (Deduzido)</th>
                    <th class="text-right">Peso Bruto (kg)</th>
                    <th class="text-right">Tara (kg)</th>
                </tr>
            </thead>
            <tbody>
        """
        for item in divs_falta_excel:
            placa = item.get("Placa", "N/A")
            sev = item.get("SEV", "N/A")
            data = item.get("Data", "N/A")
            produto = item.get("Produto", "Não Identificado")
            bruto = item.get("Peso Bruto", 0)
            tara = item.get("Tara", 0)

            html += f"""
                <tr>
                    <td><strong>{placa}</strong></td>
                    <td class="text-center">{sev if (sev and not sev.startswith('TEMP_SEV_')) else '—'}</td>
                    <td class="text-center">{data}</td>
                    <td><span class="badge-table status-yellow">{produto}</span></td>
                    <td class="text-right">{_format_kg(bruto)}</td>
                    <td class="text-right">{_format_kg(tara)}</td>
                </tr>
            """
        html += """
            </tbody>
        </table>
        """
        has_page_break = True

    # 3. Tabela: Falta no PDF (Omissões na Automação OpenPort / Erro de Lançamento)
    divs_falta_pdf = grouped_divs.get("Falta no PDF", [])
    if divs_falta_pdf:
        class_page_break = "class='page-break'" if has_page_break else ""
        html += f"""
        <div {class_page_break} style="margin-top: 25px;"></div>
        <div class="table-title">⚠️ Omissões na Automação OpenPort (Balança Automática) — {len(divs_falta_pdf)} ocorrência(s)</div>
        <p class="description-block" style="margin-bottom: 10px;">
            Viagens registradas pelos balanceiros na planilha Excel que não constam no sistema automático OpenPort.
        </p>
        <table class="executive-table">
            <thead>
                <tr>
                    <th>Placa</th>
                    <th class="text-center">Data</th>
                    <th>Produto / Cliente</th>
                    <th class="text-right">Peso Informado (kg)</th>
                    <th class="text-right">Tara Informada (kg)</th>
                </tr>
            </thead>
            <tbody>
        """
        for item in divs_falta_pdf:
            placa = item.get("Placa", "N/A")
            data = item.get("Data", "N/A")
            produto = item.get("Produto", "N/A")
            cliente = item.get("Cliente", "N/A")
            bruto = item.get("Peso Bruto", 0)
            tara = item.get("Tara", 0)

            html += f"""
                <tr>
                    <td><strong>{placa}</strong></td>
                    <td class="text-center">{data}</td>
                    <td>{produto} / {cliente}</td>
                    <td class="text-right">{_format_kg(bruto)}</td>
                    <td class="text-right">{_format_kg(tara)}</td>
                </tr>
            """
        html += """
            </tbody>
        </table>
        """
        has_page_break = True

    # 4. Tabela: Erros de Digitação de Placa (Typos já identificados e sugeridos para correção)
    divs_placa = grouped_divs.get("Erro de Placa", [])
    if divs_placa:
        class_page_break = "class='page-break'" if has_page_break else ""
        html += f"""
        <div {class_page_break} style="margin-top: 25px;"></div>
        <div class="table-title">⚠️ Inconsistências de Identificação (Placa Digitada Incorretamente) — {len(divs_placa)} ocorrência(s)</div>
        <p class="description-block" style="margin-bottom: 10px;">
            Pares onde os pesos e datas coincidem perfeitamente, mas houve erro de digitação de placa pelo balanceiro.
        </p>
        <table class="executive-table">
            <thead>
                <tr>
                    <th>Placa Digitada (Excel)</th>
                    <th>Placa Correta (PDF)</th>
                    <th class="text-center">SEV</th>
                    <th class="text-center">Data</th>
                    <th class="text-right">Peso Bruto (kg)</th>
                    <th>Divergência de Caracteres</th>
                </tr>
            </thead>
            <tbody>
        """
        for item in divs_placa:
            p_excel = item.get("Placa_Excel", "N/A")
            p_pdf = item.get("Placa_PDF", "N/A")
            sev = item.get("SEV", "N/A")
            data = item.get("Data", "N/A")
            bruto = item.get("Peso Bruto", 0)
            
            # Calcular distância de Levenshtein para identificar diferenças
            dist = levenshtein_distance(p_excel, p_pdf)
            diff_label = "Diferença de 1 caractere" if dist == 1 else f"Diferença de {dist} caracteres"

            html += f"""
                <tr>
                    <td><span style="color: var(--danger); font-weight: 700;">{p_excel}</span></td>
                    <td><span style="color: var(--success); font-weight: 700;">{p_pdf}</span></td>
                    <td class="text-center">{sev if (sev and not sev.startswith('TEMP_SEV_')) else '—'}</td>
                    <td class="text-center">{data}</td>
                    <td class="text-right">{_format_kg(bruto)}</td>
                    <td>{diff_label}</td>
                </tr>
            """
        html += """
            </tbody>
        </table>
        """

    # --- PARECER TÉCNICO E ASSINATURA ---
    # Garantir que a caixa de parecer e assinaturas caibam juntas ou quebrem de página se necessário
    html += f"""
        <div class="parecer-box">
            <h4>Parecer de Auditoria & Recomendações de Controle</h4>
            <p>Com base nos dados analisados, apresenta-se o seguinte parecer executivo:</p>
            <ul>
                <li><strong>Acurácia Documental:</strong> O índice de conformidade documental de {kpi_accuracy:.2f}% reflete uma classificação <strong>{classificacao}</strong> de conformidade.</li>
                {"<li><strong>Medida Corretiva de Placa:</strong> É recomendado atualizar no sistema as placas identificadas com erros de digitação, restabelecendo a consistência cadastral.</li>" if divs_placa else ""}
                {"<li><strong>Medida de Investigação de Desvio de Peso:</strong> As divergências de peso brutas listadas devem ser confrontadas com os tickets físicos da balança. Havendo discrepância sistemática, recomenda-se abertura de chamado técnico para calibração da balança física.</li>" if divs_peso else ""}
                {"<li><strong>Medida Administrativa de Omissão:</strong> Viagens omitidas em planilha manual devem ser justificadas pelo operador da balança para evitar perda de integridade dos relatórios diários de pesagem.</li>" if divs_falta_excel else ""}
            </ul>
        </div>

        <!-- Assinaturas -->
        <div class="signatures">
            <div class="signature-block">
                <div class="signature-line"></div>
                <strong>Auditor de Pesagens</strong>
                <div class="signature-title">Auditoria e Controle Interno — CODEBA</div>
            </div>
            <div class="signature-block">
                <div class="signature-line"></div>
                <strong>Diretoria de Operações</strong>
                <div class="signature-title">Superintendência Portuária — SUPORT</div>
            </div>
        </div>

    </div>
    
    <!-- Script de Icons -->
    <script src="https://unpkg.com/@phosphor-icons/web"></script>
</body>
</html>
"""
    return html
