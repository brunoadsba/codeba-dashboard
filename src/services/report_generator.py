import os
import io
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from src.config import STATIC_DIR

# ── Cores Institucionais ──────────────────────────────────────
CODEBA_NAVY      = colors.HexColor("#0B1D3A")   # Azul marinho institucional
CODEBA_BLUE      = colors.HexColor("#1E3A5F")   # Azul cabeçalho
SLATE_900        = colors.HexColor("#0F172A")
SLATE_700        = colors.HexColor("#334155")
SLATE_600        = colors.HexColor("#475569")
SLATE_500        = colors.HexColor("#64748B")
SLATE_300        = colors.HexColor("#CBD5E1")
SLATE_200        = colors.HexColor("#E2E8F0")
SLATE_100        = colors.HexColor("#F1F5F9")
SLATE_50         = colors.HexColor("#F8FAFC")

GREEN_700        = colors.HexColor("#15803D")
GREEN_100        = colors.HexColor("#DCFCE7")
GREEN_50         = colors.HexColor("#F0FDF4")

RED_700          = colors.HexColor("#B91C1C")
RED_100          = colors.HexColor("#FEE2E2")
RED_50           = colors.HexColor("#FEF2F2")

AMBER_700        = colors.HexColor("#B45309")
AMBER_100        = colors.HexColor("#FEF3C7")
AMBER_50         = colors.HexColor("#FFFBEB")

ORANGE_700       = colors.HexColor("#C2410C")
ORANGE_100       = colors.HexColor("#FFEDD5")
ORANGE_50        = colors.HexColor("#FFF7ED")

BLUE_700         = colors.HexColor("#1D4ED8")
BLUE_100         = colors.HexColor("#DBEAFE")
BLUE_50          = colors.HexColor("#EFF6FF")


def format_kg(val: Any) -> str:
    if val is None or pd.isna(val):
        return "—"
    try:
        return f"{int(float(val)):,}".replace(",", ".") + " kg"
    except Exception:
        return str(val)

def format_ton(val: Any) -> str:
    if val is None or pd.isna(val):
        return "0,00 t"
    try:
        return f"{float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " t"
    except Exception:
        return str(val)

def get_periodo_str(ok_list: list[dict], div_list: list[dict]) -> str:
    all_dates = []
    for item in ok_list + div_list:
        dt = item.get("Data")
        if dt:
            date_part = str(dt).split(" ")[0]
            all_dates.append(date_part)
            
    if not all_dates:
        return "—"
        
    def sort_key(d: str) -> tuple[int, int, int]:
        parts = d.split("/")
        if len(parts) == 3:
            try:
                return int(parts[2]), int(parts[1]), int(parts[0])
            except ValueError:
                pass
        return 0, 0, 0
        
    sorted_dates = sorted(list(set(all_dates)), key=sort_key)
    if len(sorted_dates) == 1:
        return sorted_dates[0]
    return f"{sorted_dates[0]} a {sorted_dates[-1]}"


# ── Cor de fundo por tipo de erro ─────────────────────────────
def _row_color_for_status(status: str) -> tuple[colors.HexColor, colors.HexColor]:
    """Retorna (cor_de_fundo, cor_de_texto) para o status de divergência."""
    s = (status or "").strip().lower()
    if "erro de placa" in s:
        return RED_50, RED_700
    elif "falta no excel" in s:
        return AMBER_50, AMBER_700
    elif "falta no pdf" in s:
        return ORANGE_50, ORANGE_700
    elif "diferença de peso" in s or "diferenca" in s:
        return BLUE_50, BLUE_700
    return colors.white, SLATE_700


class NumberedCanvas(canvas.Canvas):
    """
    Canvas customizado para desenhar o cabeçalho institucional, rodapés e
    fazer a numeração de páginas dinâmica (Página X de Y).
    """
    def __init__(self, *args, **kwargs):
        kwargs['pageCompression'] = 0
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, num_pages: int):
        self.saveState()
        page_w, page_h = A4  # 595.27 x 841.89

        # ── 1. Faixa azul institucional no topo ───────────────────
        bar_height = 68
        bar_y = page_h - bar_height
        self.setFillColor(CODEBA_NAVY)
        self.rect(0, bar_y, page_w, bar_height, stroke=0, fill=1)

        # ── 2. Logo CODEBA (dentro da faixa) ──────────────────────
        logo_path = STATIC_DIR / "Logo CODEBA.png"
        if logo_path.exists():
            logo_w = 120
            logo_h = 37
            logo_x = 36
            logo_y = bar_y + (bar_height - logo_h) / 2
            self.drawImage(str(logo_path), logo_x, logo_y, width=logo_w, height=logo_h, mask="auto")

        # ── 3. Título na faixa ────────────────────────────────────
        self.setFillColor(colors.white)
        self.setFont("Helvetica-Bold", 16)
        self.drawString(170, bar_y + 38, "Relatório de Não Conformidade")

        periodo_str = getattr(self, "_periodo_str", "—")
        self.setFillColor(colors.HexColor("#94A3B8"))  # Slate 400
        self.setFont("Helvetica", 9)
        self.drawString(170, bar_y + 22, f"Período Auditado: {periodo_str}")
        self.drawString(170, bar_y + 10, "Base de Dados: Relatório OpenPort (Tela 7714)")

        # ── 4. Linha de separação abaixo da faixa ─────────────────
        self.setStrokeColor(SLATE_200)
        self.setLineWidth(0.75)
        self.line(30, bar_y - 6, page_w - 30, bar_y - 6)

        # ── 5. Rodapé ────────────────────────────────────────────
        # Linha divisória do rodapé
        self.setStrokeColor(SLATE_200)
        self.setLineWidth(0.5)
        self.line(30, 42, page_w - 30, 42)

        emissao_str = getattr(self, "_emissao_str", "")
        self.setFont("Helvetica", 7.5)
        self.setFillColor(SLATE_500)
        self.drawString(30, 30, f"Data de Emissão: {emissao_str} (Horário de Ilhéus)")

        self.setFont("Helvetica", 7.5)
        self.setFillColor(SLATE_500)
        right_text = f"Gerado pelo Sistema de Auditoria CODEBA     ·     Página {self._pageNumber} de {num_pages}"
        self.drawRightString(page_w - 30, 30, right_text)

        self.restoreState()


def filter_records(ok_list: list[dict], div_list: list[dict], filters: dict) -> tuple[list[dict], list[dict]]:
    filtered_ok = ok_list.copy()
    filtered_div = div_list.copy()
    
    placa = filters.get("placa")
    if placa:
        placa_clean = placa.strip().replace("-", "").upper()
        
        def match_placa(item):
            # Matches standard Placa, Placa_Excel, or Placa_PDF
            p = str(item.get("Placa", "")).strip().replace("-", "").upper()
            pe = str(item.get("Placa_Excel", "")).strip().replace("-", "").upper()
            pp = str(item.get("Placa_PDF", "")).strip().replace("-", "").upper()
            return placa_clean in p or placa_clean in pe or placa_clean in pp
            
        filtered_ok = [i for i in filtered_ok if match_placa(i)]
        filtered_div = [i for i in filtered_div if match_placa(i)]
        
    produto = filters.get("produto")
    if produto:
        prod_clean = produto.strip().upper()
        
        def match_produto(item):
            p = str(item.get("Produto", "")).strip().upper()
            return prod_clean in p
            
        filtered_ok = [i for i in filtered_ok if match_produto(i)]
        filtered_div = [i for i in filtered_div if match_produto(i)]
        
    date_start = filters.get("date_start")
    date_end = filters.get("date_end")
    if date_start or date_end:
        start_dt = pd.to_datetime(date_start).date() if date_start else None
        end_dt = pd.to_datetime(date_end).date() if date_end else None
        
        def match_date(item):
            dt_str = item.get("Data", "")
            if not dt_str:
                return False
            try:
                # Dates are DD/MM/YYYY or DD/MM/YYYY HH:MM
                item_dt = pd.to_datetime(dt_str, dayfirst=True).date()
                if start_dt and item_dt < start_dt:
                    return False
                if end_dt and item_dt > end_dt:
                    return False
                return True
            except Exception:
                return False
                
        filtered_ok = [i for i in filtered_ok if match_date(i)]
        filtered_div = [i for i in filtered_div if match_date(i)]
        
    return filtered_ok, filtered_div


def generate_pdf_report(payload: dict[str, Any], filters: dict[str, Any]) -> tuple[bytes, str]:
    """
    Gera o PDF do relatório de não conformidades com base nos filtros fornecidos.
    
    Returns:
        tuple contendo (bytes_do_pdf, nome_do_arquivo)
    """
    ok_list = payload.get("ok", [])
    div_list = payload.get("divergencias", [])
    
    # Filtrar dados de acordo com a seleção ativa
    filtered_ok, filtered_div = filter_records(ok_list, div_list, filters)
    
    # Calcular metadados do período com base no dataset completo ou filtrado?
    # O período do cabeçalho representa as datas dos arquivos analisados
    periodo_str = get_periodo_str(filtered_ok, filtered_div)
    
    # Timestamp de emissão (Bahia/Ilhéus - local do servidor)
    emissao_dt = datetime.now()
    emissao_str = emissao_dt.strftime("%d/%m/%Y %H:%M:%S")
    file_timestamp = emissao_dt.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"relatorio_executivo_auditoria_{file_timestamp}.pdf"
    
    # Preparar buffer
    buffer = io.BytesIO()
    
    # Configurar Template de Documento A4
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=95,   # Espaço para a faixa institucional
        bottomMargin=58
    )
    
    styles = getSampleStyleSheet()
    
    # ── Estilos de Parágrafos ─────────────────────────────────
    title_style = ParagraphStyle(
        "ReportSectionTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=CODEBA_NAVY,
        spaceBefore=16,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        "ReportBodyText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=SLATE_700,
        spaceAfter=10
    )
    
    bullet_style = ParagraphStyle(
        "ReportBullet",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=SLATE_700,
        leftIndent=20,
        firstLineIndent=-10,
        spaceAfter=4
    )
    
    # Estilos de células de tabela
    th_style = ParagraphStyle(
        "TableHeader",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER
    )
    
    td_style_center = ParagraphStyle(
        "TableCellCenter",
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=SLATE_700,
        alignment=TA_CENTER
    )
    
    td_style_green_center = ParagraphStyle(
        "TableCellGreenCenter",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=GREEN_700,
        alignment=TA_CENTER
    )
    
    td_style_left = ParagraphStyle(
        "TableCellLeft",
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=SLATE_700,
        alignment=TA_LEFT
    )
    
    td_style_right = ParagraphStyle(
        "TableCellRight",
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=SLATE_700,
        alignment=TA_RIGHT
    )
    
    td_style_bold_right = ParagraphStyle(
        "TableCellBoldRight",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=SLATE_900,
        alignment=TA_RIGHT
    )
    
    td_style_footer = ParagraphStyle(
        "TableFooter",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=SLATE_600,
        alignment=TA_RIGHT
    )

    # Status badge style
    def _status_para_style(status_color: colors.HexColor):
        return ParagraphStyle(
            f"StatusBadge_{id(status_color)}",
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=status_color,
            alignment=TA_CENTER
        )
    
    story = []
    
    # ══════════════════════════════════════════════════════════════
    # SEÇÃO 1: Inconsistências Encontradas
    # ══════════════════════════════════════════════════════════════
    story.append(Paragraph("1. Inconsistências Encontradas", title_style))
    
    num_div = len(filtered_div)
    if num_div > 0:
        intro_txt = (
            f"Foram identificadas <b>{num_div} divergência{'s' if num_div != 1 else ''}</b> "
            "no cruzamento dos dados operacionais deste período. "
            "A tabela abaixo apresenta o detalhamento de cada ocorrência:"
        )
    else:
        intro_txt = (
            "Nenhuma divergência foi identificada no cruzamento dos dados deste período. "
            "Todos os registros da planilha coincidem com os do relatório OpenPort."
        )
    story.append(Paragraph(intro_txt, body_style))
    story.append(Spacer(1, 4))
    
    # Construir tabela de divergências
    # Larguras das colunas: total ~535pt
    div_col_widths = [80, 60, 60, 75, 75, 70, 40, 75.3]
    
    div_table_data = [
        [
            Paragraph("Data / Horário", th_style),
            Paragraph("Placa Digitada<br/>(Excel)", th_style),
            Paragraph("Placa Correta<br/>(OpenPort)", th_style),
            Paragraph("Tipo do Erro", th_style),
            Paragraph("Produto", th_style),
            Paragraph("Cliente", th_style),
            Paragraph("PR", th_style),
            Paragraph("Peso Bruto", th_style)
        ]
    ]
    
    # Rastrear tipos de erro para o Plano de Ação
    error_types_found = set()
    
    for item in filtered_div:
        status = item.get("Status", "")
        error_types_found.add(status)
        
        placa_excel = "—"
        placa_pdf = "—"
        
        if status == "Erro de Placa":
            placa_excel = item.get("Placa_Excel", "")
            placa_pdf = item.get("Placa_PDF", "")
        elif status == "Falta no Excel":
            placa_pdf = item.get("Placa", "")
        elif status == "Falta no PDF":
            placa_excel = item.get("Placa", "")
        else:
            placa_excel = item.get("Placa", "")
            placa_pdf = item.get("Placa", "")
            
        prod = item.get("Produto", "") or ""
        prod_clean = prod.replace(" (Deduzido)", "").upper()
        
        cliente = item.get("Cliente", "") or ""
        pr = item.get("PR", "11050")
        peso_bruto = format_kg(item.get("Peso Bruto"))
        
        dt_str = item.get("Data", "—")
        if dt_str and dt_str != "—" and ":" not in dt_str:
            dt_str = f"{dt_str} (Excel)"

        # Cor do badge de status
        _, status_color = _row_color_for_status(status)
        status_style = _status_para_style(status_color)
        
        row = [
            Paragraph(dt_str, td_style_center),
            Paragraph(placa_excel, td_style_center),
            Paragraph(placa_pdf, td_style_green_center if placa_pdf != "—" else td_style_center),
            Paragraph(status, status_style),
            Paragraph(prod_clean, td_style_left),
            Paragraph(cliente, td_style_left),
            Paragraph(pr, td_style_center),
            Paragraph(peso_bruto, td_style_right)
        ]
        div_table_data.append(row)
        
    if num_div == 0:
        row_empty = [
            Paragraph("—", td_style_center),
            Paragraph("—", td_style_center),
            Paragraph("—", td_style_center),
            Paragraph("—", td_style_center),
            Paragraph("Nenhuma divergência encontrada", td_style_left),
            Paragraph("—", td_style_center),
            Paragraph("—", td_style_center),
            Paragraph("—", td_style_center)
        ]
        div_table_data.append(row_empty)
        
    # Estilização da Tabela de Divergências
    div_t_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CODEBA_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, SLATE_200),
        ("BOX", (0, 0), (-1, -1), 0.6, SLATE_300),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ])
    
    # Aplicar cores de fundo por tipo de erro
    for i, item in enumerate(filtered_div):
        row_idx = i + 1  # +1 pois header é 0
        bg_color, _ = _row_color_for_status(item.get("Status", ""))
        div_t_style.add("BACKGROUND", (0, row_idx), (-1, row_idx), bg_color)
    
    # Se não teve divergências, fundo branco na linha vazia
    if num_div == 0:
        div_t_style.add("BACKGROUND", (0, 1), (-1, 1), SLATE_50)
        
    div_table = Table(div_table_data, colWidths=div_col_widths, style=div_t_style, repeatRows=1)
    story.append(div_table)
    story.append(Spacer(1, 18))
    
    # ══════════════════════════════════════════════════════════════
    # SEÇÃO 2: Resumo Operacional (caixa estilizada)
    # ══════════════════════════════════════════════════════════════
    story.append(Paragraph("2. Resumo Operacional", title_style))
    story.append(Paragraph(
        "Indicadores consolidados da operação no período auditado:",
        body_style
    ))
    story.append(Spacer(1, 4))
    
    # Calcular KPIs
    total_viagens = len(filtered_ok) + len(filtered_div)
    ok_count = len(filtered_ok)
    pct_sem_erro = (ok_count / total_viagens * 100.0) if total_viagens > 0 else 0.0
    
    # Volume total
    tot_vol_kg = 0
    for item in filtered_ok:
        tot_vol_kg += item.get("Peso Liquido", 0) or (item.get("Peso Bruto", 0) - item.get("Tara", 0))
    for item in filtered_div:
        tot_vol_kg += item.get("Peso Bruto", 0) - item.get("Tara", 0)
    tot_vol_t = tot_vol_kg / 1000.0
    
    # Status geral
    if pct_sem_erro == 100.0:
        status_geral = "Excelente"
        status_color = GREEN_700
        status_bg = GREEN_100
    elif pct_sem_erro >= 95.0:
        status_geral = "Bom"
        status_color = GREEN_700
        status_bg = GREEN_50
    elif pct_sem_erro >= 80.0:
        status_geral = "Atenção"
        status_color = AMBER_700
        status_bg = AMBER_100
    else:
        status_geral = "Crítico"
        status_color = RED_700
        status_bg = RED_100

    # Estilos para a caixa de KPIs
    kpi_label = ParagraphStyle(
        "KpiLabel", fontName="Helvetica", fontSize=9, leading=12, textColor=SLATE_500, alignment=TA_LEFT
    )
    kpi_value = ParagraphStyle(
        "KpiValue", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=SLATE_900, alignment=TA_LEFT
    )
    kpi_status_style = ParagraphStyle(
        "KpiStatus", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=status_color, alignment=TA_LEFT
    )
    
    pct_str = f"{pct_sem_erro:.1f}%".replace(".", ",")
    
    kpi_data = [
        [
            Paragraph("Volume Movimentado", kpi_label),
            Paragraph("Total de Viagens", kpi_label),
            Paragraph("Viagens sem Erro", kpi_label),
            Paragraph("Divergências", kpi_label),
            Paragraph("Status Geral", kpi_label),
        ],
        [
            Paragraph(format_ton(tot_vol_t), kpi_value),
            Paragraph(str(total_viagens), kpi_value),
            Paragraph(f"{ok_count} ({pct_str})", kpi_value),
            Paragraph(str(num_div), kpi_value),
            Paragraph(status_geral, kpi_status_style),
        ]
    ]
    
    kpi_col_w = [535.3 / 5] * 5
    kpi_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SLATE_50),
        ("BOX", (0, 0), (-1, -1), 0.6, SLATE_300),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, SLATE_200),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        # Fundo colorido na célula de status
        ("BACKGROUND", (-1, 1), (-1, 1), status_bg),
    ])
    
    kpi_table = Table(kpi_data, colWidths=kpi_col_w, style=kpi_style)
    story.append(kpi_table)
    story.append(Spacer(1, 18))
    
    # ══════════════════════════════════════════════════════════════
    # SEÇÃO 3: Plano de Ação (dinâmico)
    # ══════════════════════════════════════════════════════════════
    story.append(Paragraph("3. Plano de Ação", title_style))
    
    if num_div == 0:
        story.append(Paragraph(
            "Não foram identificadas divergências neste período. Nenhuma ação corretiva é necessária. "
            "Recomenda-se manter os procedimentos atuais e continuar o acompanhamento de rotina.",
            body_style
        ))
    else:
        story.append(Paragraph(
            "Com base nas inconsistências observadas, seguem as recomendações práticas para "
            "resolução e alinhamento com a equipe:",
            body_style
        ))
        story.append(Spacer(1, 4))
        
        # Recomendações condicionais baseadas nos tipos de erro encontrados
        if "Erro de Placa" in error_types_found:
            story.append(Paragraph(
                "• <b>Correção de Digitação de Placas:</b> Foram identificados erros na digitação "
                "de placas entre a planilha Excel e o relatório OpenPort. Orientar os balanceiros para "
                "reforçar a conferência visual da placa antes do registro, especialmente em situações de "
                "alto volume de operação.",
                bullet_style
            ))
            
        if "Falta no Excel" in error_types_found:
            story.append(Paragraph(
                "• <b>Registros Ausentes na Planilha:</b> Existem pesagens registradas no sistema OpenPort "
                "que não constam na planilha Excel. Verificar se houve omissão no preenchimento manual "
                "e orientar a equipe para que todas as pesagens sejam devidamente registradas.",
                bullet_style
            ))
            
        if "Falta no PDF" in error_types_found:
            story.append(Paragraph(
                "• <b>Registros Ausentes no OpenPort:</b> Existem registros na planilha Excel que não "
                "possuem correspondência no relatório OpenPort. Verificar se a balança estava operando "
                "corretamente nos períodos correspondentes e se o sistema registrou todas as pesagens.",
                bullet_style
            ))
            
        if "Diferença de Peso" in error_types_found:
            story.append(Paragraph(
                "• <b>Diferenças de Peso:</b> Foram constatadas divergências nos valores de peso bruto "
                "e/ou tara entre as fontes. Verificar a calibração das balanças e se os valores estão "
                "sendo transferidos corretamente para as planilhas.",
                bullet_style
            ))
        
        # Recomendação geral sempre presente
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "• <b>Acompanhamento Contínuo:</b> Recomenda-se a emissão periódica deste relatório para "
            "monitoramento da evolução dos indicadores e garantia da qualidade dos dados operacionais.",
            bullet_style
        ))
    
    # Injetar variáveis de instância no canvasmaker personalizado
    canvasmaker = make_canvas_maker(periodo_str, emissao_str)
    
    # Build PDF
    doc.build(story, canvasmaker=canvasmaker)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes, filename

def make_canvas_maker(periodo_str: str, emissao_str: str):
    class CustomNumberedCanvas(NumberedCanvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._periodo_str = periodo_str
            self._emissao_str = emissao_str
    return CustomNumberedCanvas
