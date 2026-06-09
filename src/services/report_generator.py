import re
import difflib
import os
import io
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import Image
from src.services.post_processing import levenshtein_distance


def _format_date_to_local(date_str: str) -> str:
    """Converte data UTC ISO para o horário local de Ilhéus (UTC-3)."""
    if not date_str:
        return "Data não disponível"
    try:
        # datetime.fromisoformat é muito robusto para parsing de ISO 8601
        dt_utc = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        tz_ba = timezone(timedelta(hours=-3))
        return dt_utc.astimezone(tz_ba).strftime("%d/%m/%Y %H:%M:%S (Horário de Ilhéus)")
    except Exception:
        return date_str

def _extract_weights_from_detail(detail: str) -> Tuple[float, float]:
    """Extrai o Peso Bruto do Excel e do PDF usando Regex a partir do campo Detalhe."""
    # Exemplo: "[Planilha: LÍTIO] Bruto 42100.0 / Tara 16000.0 != [PDF: LÍTIO] Bruto 42500.0 ..."
    match = re.findall(r"Bruto (\d+(?:\.\d+)?)", detail)
    if len(match) >= 2:
        return float(match[0]), float(match[1])
    return 0.0, 0.0

def _calculate_plate_similarity(plate1: str, plate2: str) -> str:
    """Calcula a similaridade entre duas placas e destaca as diferenças."""
    if not plate1 or not plate2:
        return "N/A"
    matcher = difflib.SequenceMatcher(None, plate1, plate2)
    ratio = matcher.ratio() * 100
    return f"{ratio:.1f}% de similaridade"

def generate_markdown_report(payload: Dict[str, Any], file_names: List[str] = None) -> str:
    """
    Gera um relatório técnico em Markdown com base no payload da auditoria.
    """
    if file_names is None:
        file_names = payload.get("file_names", [])

    # Extração segura de dados
    run_id = payload.get("run_id", "ID não informado")
    created_at = _format_date_to_local(payload.get("created_at", ""))
    resumo = payload.get("resumo", {})
    total_proc = resumo.get("total_processado", 0)
    total_ok = resumo.get("ok", 0)
    total_div = resumo.get("divergencias", 0)
    
    # KPI de Acurácia
    kpi_accuracy = (total_ok / total_proc * 100) if total_proc > 0 else 0.0
    
    # Agrupamento de Divergências
    divergencias_raw = payload.get("divergencias", [])
    grouped_divs = defaultdict(list)
    for div in divergencias_raw:
        status = div.get("Status", "Status Desconhecido")
        grouped_divs[status].append(div)

    # --- INÍCIO DA CONSTRUÇÃO DO MARKDOWN ---
    md = []
    md.append("# 📊 Relatório de Auditoria de Pesagens Portuárias (CODEBA)\n")
    
    md.append("## 📌 Metadados da Execução")
    md.append(f"- **ID da Execução:** `{run_id}`")
    md.append(f"- **Data de Geração:** {created_at}")
    md.append(f"- **Arquivos Analisados:** {', '.join(file_names) if file_names else 'Não especificados'}")
    md.append("")
    
    md.append("## 📈 Resumo Executivo")
    md.append(f"- **Total de Registros Processados:** {total_proc}")
    md.append(f"- **Registros Corretos (OK):** {total_ok}")
    md.append(f"- **Registros com Divergência:** {total_div}")
    md.append(f"- **🎯 KPI de Acurácia:** **{kpi_accuracy:.2f}%**\n")
    
    if grouped_divs:
        md.append("### Contagem de Divergências por Tipo:")
        for status, items in grouped_divs.items():
            md.append(f"- **{status}:** {len(items)} ocorrência(s)")
        md.append("\n---\n")
    
    md.append("## 🛠️ Diagnóstico Técnico de Divergências\n")
    
    if not grouped_divs:
        md.append("> ✅ *Nenhuma divergência encontrada nesta execução.*")
        return "\n".join(md)

    # Ordenação dos tipos de divergência para consistência
    ordered_statuses = sorted(list(grouped_divs.keys()))

    for status in ordered_statuses:
        items = grouped_divs[status]
        md.append(f"### ⚠️ Status: {status} ({len(items)} caso(s))")
        
        for idx, item in enumerate(items, 1):
            placa = item.get("Placa", "N/A")
            data = item.get("Data", "N/A")
            produto = item.get("Produto", "N/A")
            cliente = item.get("Cliente", "N/A")
            sev = item.get("SEV", "N/A")
            detalhe = item.get("Detalhe", "Sem detalhes adicionais.")
            
            md.append(f"#### {idx}. Placa: `{placa}` | Data: {data}")
            md.append(f"- **Produto/Cliente:** {produto} / {cliente}")
            if sev and sev != "N/A":
                md.append(f"- **SEV:** {sev}")
            md.append(f"- **Detalhe Bruto:** *{detalhe}*")
            
            # --- Lógica Específica por Status ---
            if status == "Diferença de Peso":
                excel_bruto, pdf_bruto = _extract_weights_from_detail(detalhe)
                if excel_bruto and pdf_bruto:
                    diff_abs = abs(pdf_bruto - excel_bruto)
                    diff_pct = (diff_abs / excel_bruto * 100) if excel_bruto > 0 else 0.0
                    md.append(f"- **Análise Numérica:** Peso Excel ({excel_bruto}kg) vs Peso PDF ({pdf_bruto}kg)")
                    md.append(f"- **Diferença:** **{diff_abs:.2f}kg** ({diff_pct:.2f}%)")
                md.append("- **Ação Recomendada:** Verificar possibilidade de erro de digitação manual da tara ou do peso bruto na planilha.")

            elif status == "Falta no PDF":
                md.append("- **Ação Recomendada:** Alerta Crítico! A pesagem foi registrada no Excel pelo balanceiro, mas não constou na automação do OpenPort. Investigar possível falha no sistema de captura automática da balança ou registro indevido (fantasma) na planilha.")

            elif status == "Falta no Excel":
                deduzido = "Deduzido" in produto
                md.append(f"- **Contexto do Sistema:** Produto classificado como '{'Deduzido' if deduzido else 'Não Identificado'}'.")
                md.append("- **Ação Recomendada:** Caminhão passou na balança automática (PDF), mas foi omitido no controle manual. O balanceiro deve justificar a omissão na planilha. Verificar se a carga seguiu para o pátio sem autorização.")

            elif status == "Erro de Placa":
                placa_excel = item.get("Placa_Excel", placa)
                placa_pdf = item.get("Placa_PDF", "N/A")
                sim_ratio = _calculate_plate_similarity(placa_excel, placa_pdf)
                md.append(f"- **Análise de Caracteres:** Excel (`{placa_excel}`) vs PDF (`{placa_pdf}`) -> {sim_ratio}")
                md.append("- **Ação Recomendada:** Forte indício de erro de digitação manual do balanceiro, visto que os pesos são idênticos. Atualizar o registro do Excel para coincidir com o OCR/PDF.")

            md.append("") # Espaçamento entre os itens
            
    return "\n".join(md)


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


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor('#64748B'))
        
        # Desenha linha e texto de cabeçalho (apenas nas páginas > 1)
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor('#E2E8F0'))
            self.setLineWidth(0.5)
            self.line(30, 810, 565, 810)
            self.drawString(30, 815, "Relatório de Não Conformidade — CODEBA")
        
        # Desenha linha e numeração no rodapé (em todas as páginas)
        self.setStrokeColor(colors.HexColor('#E2E8F0'))
        self.setLineWidth(0.5)
        self.line(30, 45, 565, 45)
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(565, 32, page_text)
        self.drawString(30, 32, "Companhia Docas do Estado da Bahia")
        self.restoreState()


def generate_pdf_report(payload: Dict[str, Any], file_names: List[str] = None) -> bytes:
    """
    Gera um relatório de conciliação de pesagens em PDF usando ReportLab.
    O formato segue estritamente as especificações do usuário:
    - Tom informal e direto
    - Sem cabeçalhos burocráticos
    - Tabela contendo apenas: Data | Placa Digitada | Placa Correta | Peso Bruto
    - Resumo operacional e plano de ação estruturados conforme a ordem definida
    - Sem assinaturas ou pareceres burocráticos
    """
    if file_names is None:
        file_names = payload.get("file_names", [])

    created_at = _format_date_to_local(payload.get("created_at", ""))
    resumo = payload.get("resumo", {})
    total_proc = resumo.get("total_processado", 0)
    total_ok = resumo.get("ok", 0)
    total_div = resumo.get("divergencias", 0)
    
    kpi_accuracy = (total_ok / total_proc * 100) if total_proc > 0 else 0.0
    
    # Calcular volume total auditado (em toneladas)
    total_toneladas_ok = 0.0
    for ok_item in payload.get("ok", []):
        peso_liq = ok_item.get("Peso Liquido") or (ok_item.get("Peso Bruto", 0) - ok_item.get("Tara", 0))
        total_toneladas_ok += (peso_liq / 1000.0)

    # Divergências
    divergencias_raw = payload.get("divergencias", [])
    
    # Determinar classificação de conformidade
    if kpi_accuracy >= 98:
        classificacao = "Excelente"
    elif kpi_accuracy >= 90:
        classificacao = "Atenção"
    else:
        classificacao = "Crítico"
        
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

    buffer = io.BytesIO()
    
    # Margins: 30pt. Printable width = 595.27 - 60 = 535.27 pt.
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=45,
        bottomMargin=55
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=12,
        fontName='Helvetica',
        textColor=colors.HexColor('#64748B'),
        spaceAfter=15
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=12,
        leading=15,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=18,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )
    
    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )
    
    # Cell Styles
    cell_header = ParagraphStyle(
        'CellHeader',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        fontName='Helvetica-Bold',
        textColor=colors.whitesmoke
    )
    
    cell_text = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#334155')
    )
    
    cell_text_bold = ParagraphStyle(
        'CellTextBold',
        parent=cell_text,
        fontName='Helvetica-Bold'
    )

    cell_text_red = ParagraphStyle(
        'CellTextRed',
        parent=cell_text,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#EF4444')
    )
    
    from src.config import STATIC_DIR
    logo_path = os.path.join(STATIC_DIR, "Logo CODEBA.png")
    logo_img = Image(logo_path, width=110, height=34)
    
    # Header Table
    header_data = [
        [logo_img, [
            Paragraph("Relatório de Não Conformidade", title_style),
            Paragraph(f"Período Auditado: {periodo_label}", subtitle_style)
        ]]
    ]
    header_table = Table(header_data, colWidths=[130, 405.27])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
    ]))
    
    story = [
        header_table,
        Spacer(1, 10),
        Paragraph("1. Inconsistências Encontradas", section_title_style)
    ]
    
    # Descrever falhas de forma clara e objetiva (informal)
    if total_div > 0:
        desc_texto = f"Identificamos {total_div} divergências na digitação das placas e registros operacionais no cruzamento dos dados deste período. Segue a tabela abaixo:"
        story.append(Paragraph(desc_texto, body_style))
        story.append(Spacer(1, 4))
        
        # Tabela de Inconsistências
        table_headers = [
            Paragraph("Data", cell_header),
            Paragraph("Placa Digitada (Excel)", cell_header),
            Paragraph("Placa Correta (OpenPort)", cell_header),
            Paragraph("Peso Bruto", cell_header)
        ]
        
        table_data = [table_headers]
        
        for item in divergencias_raw:
            data = item.get("Data", "—")
            status = item.get("Status", "")
            
            if status == "Erro de Placa":
                placa_digitada = item.get("Placa_Excel", "—")
                placa_correta = item.get("Placa_PDF", "—")
                peso = _format_kg(item.get("Peso Bruto", 0)) + " kg"
            elif status == "Diferença de Peso":
                placa_digitada = item.get("Placa", "—")
                placa_correta = item.get("Placa", "—") + " (Peso Divergente)"
                ex_bruto, pdf_bruto = _extract_weights_from_detail(item.get("Detalhe", ""))
                peso = f"{_format_kg(ex_bruto)} kg (manual) / {_format_kg(pdf_bruto)} kg (auto)"
            elif status == "Falta no PDF":
                placa_digitada = item.get("Placa", "—")
                placa_correta = "Sem registro na balança automática"
                peso = _format_kg(item.get("Peso Bruto", 0)) + " kg"
            elif status == "Falta no Excel":
                placa_digitada = "Sem lançamento na planilha"
                placa_correta = item.get("Placa", "—")
                peso = _format_kg(item.get("Peso Bruto", 0)) + " kg"
            else:
                placa_digitada = item.get("Placa", "—")
                placa_correta = "—"
                peso = _format_kg(item.get("Peso Bruto", 0)) + " kg"
                
            table_data.append([
                Paragraph(data, cell_text),
                Paragraph(placa_digitada, cell_text_red),
                Paragraph(placa_correta, cell_text_bold if status == "Erro de Placa" else cell_text),
                Paragraph(peso, cell_text)
            ])
            
        t_inc = Table(table_data, colWidths=[65, 130, 160, 180.27])
        t_inc.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#475569')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ]))
        story.append(t_inc)
    else:
        story.append(Paragraph("Verificamos todos os registros de pesagem para o período e não encontramos nenhuma inconsistência. A operação está em total conformidade.", body_style))
        
    story.append(Spacer(1, 10))
    story.append(Paragraph("2. Resumo Operacional", section_title_style))
    story.append(Paragraph("Abaixo está o resumo dos dados de movimentação do período. Os índices servem de referência para o acompanhamento contínuo da qualidade dos dados:", body_style))
    
    # Bullet points formatados
    story.append(Paragraph(f"• <b>Volume Movimentado:</b> {_format_ton(total_toneladas_ok)} t", bullet_style))
    story.append(Paragraph(f"• <b>Total de Viagens:</b> {total_proc}", bullet_style))
    story.append(Paragraph(f"• <b>Viagens sem Erro:</b> {kpi_accuracy:.2f}%", bullet_style))
    story.append(Paragraph(f"• <b>Status Geral:</b> {classificacao}", bullet_style))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph("3. Plano de Ação", section_title_style))
    story.append(Paragraph("Com base nas inconsistências observadas, segue recomendação prática para a resolução e alinhamento com a equipe:", body_style))
    
    story.append(Paragraph("• <b>Alinhamento com a Equipe:</b> Orientar os balanceiros para reforçar a atenção na digitação das placas e evitar omissões nas planilhas manuais.", bullet_style))
    
    # Data de emissão no final do documento
    emission_date_style = ParagraphStyle(
        'EmissionDate',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        fontName='Helvetica',
        textColor=colors.HexColor('#64748B'),
        spaceBefore=15,
        spaceAfter=5
    )
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Data de Emissão: {created_at}", emission_date_style))
    
    doc.build(story, canvasmaker=NumberedCanvas)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

