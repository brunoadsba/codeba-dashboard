import io
from datetime import datetime
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.config import STATIC_DIR

# ── Cores Institucionais ──────────────────────────────────────
CODEBA_NAVY      = colors.HexColor("#0B1D3A")   # Azul marinho institucional
ZEBRA_ODD        = colors.HexColor("#F8FAFC")   # Zebra odd row
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
AMBER_700        = colors.HexColor("#B45309")
AMBER_100        = colors.HexColor("#FEF3C7")

# ── Cores Badges (Status) ────────────────────────────────────
STATUS_ERRO_BG   = colors.HexColor("#FEF2F2")
STATUS_ERRO_FG   = colors.HexColor("#B91C1C")
STATUS_FALTA_EXCEL_BG  = colors.HexColor("#FFFBEB")
STATUS_FALTA_EXCEL_FG  = colors.HexColor("#B45309")
STATUS_FALTA_PDF_BG = colors.HexColor("#EFF6FF")
STATUS_FALTA_PDF_FG = colors.HexColor("#1D4ED8")

# ── Cores código/etiqueta ────────────────────────────────────
CODE_TAG_BG      = colors.HexColor("#F1F5F9")

# ── Cores pesos ──────────────────────────────────────────────
PESOS_LABEL      = colors.HexColor("#64748B")
PESOS_VALUE      = colors.HexColor("#0F172A")
PESOS_SEP        = colors.HexColor("#E5E7EB")


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
        has_div = getattr(self, "_has_divergencias", True)
        title_text = "Relatório de Não Conformidade" if has_div else "Relatório de Conformidade"
        self.setFillColor(colors.white)
        self.setFont("Helvetica-Bold", 16)
        self.drawString(170, bar_y + 38, title_text)

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

        integrity_hash = getattr(self, "_integrity_hash", "")
        if integrity_hash:
            self.setFont("Helvetica", 6.5)
            self.setFillColor(SLATE_500)
            self.drawString(30, 18, f"Hash de Integridade (SHA-256): {integrity_hash}")

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
    file_date = emissao_dt.strftime("%d-%m-%Y")
    filename = f"Relatório_Executivo {file_date}.pdf"

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
        fontSize=8,
        leading=11,
        textColor=colors.white,
        alignment=TA_CENTER
    )

    td_style_center = ParagraphStyle(
        "TableCellCenter",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=SLATE_700,
        alignment=TA_CENTER
    )

    td_style_green_center = ParagraphStyle(
        "TableCellGreenCenter",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=GREEN_700,
        alignment=TA_CENTER
    )

    td_style_left = ParagraphStyle(
        "TableCellLeft",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=SLATE_700,
        alignment=TA_LEFT
    )

    td_style_right = ParagraphStyle(
        "TableCellRight",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=SLATE_700,
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

    # Legenda de cores removida — a informação de status já está presente
    # nos badges da coluna "Status" de cada linha da tabela.

    if num_div > 0:
        # ── Contadores por Tipo de Erro ───────────────────────────
        error_counts = {}
        for item in filtered_div:
            s = item.get("Status", "")
            error_counts[s] = error_counts.get(s, 0) + 1

        count_label_style = ParagraphStyle(
            "CountLabel", fontName="Helvetica", fontSize=8,
            leading=10, textColor=SLATE_500, alignment=TA_CENTER
        )
        count_value_style = ParagraphStyle(
            "CountValue", fontName="Helvetica-Bold", fontSize=14,
            leading=18, textColor=SLATE_900, alignment=TA_CENTER
        )

        erro_placa_n = error_counts.get("Erro de Placa", 0)
        falta_excel_n = error_counts.get("Falta no Excel", 0)
        falta_pdf_n = error_counts.get("Falta no PDF", 0)

        counter_data = [
            [
                Paragraph("Erro de Placa", count_label_style),
                Paragraph("Falta no Excel", count_label_style),
                Paragraph("Falta no PDF", count_label_style),
                Paragraph("Total", count_label_style),
            ],
            [
                Paragraph(str(erro_placa_n), ParagraphStyle("CV1", parent=count_value_style, textColor=STATUS_ERRO_FG)),
                Paragraph(str(falta_excel_n), ParagraphStyle("CV2", parent=count_value_style, textColor=STATUS_FALTA_EXCEL_FG)),
                Paragraph(str(falta_pdf_n), ParagraphStyle("CV3", parent=count_value_style, textColor=STATUS_FALTA_PDF_FG)),
                Paragraph(str(num_div), count_value_style),
            ]
        ]

        counter_col_w = [535.3 / 4] * 4
        counter_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SLATE_50),
            ("BOX", (0, 0), (-1, -1), 0.5, SLATE_300),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, SLATE_200),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
            ("TOPPADDING", (0, 1), (-1, 1), 2),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ])

        counter_table = Table(counter_data, colWidths=counter_col_w, style=counter_style)
        story.append(counter_table)
        story.append(Spacer(1, 10))

    # ── Construir tabela de divergências (8 colunas) ─────────────
    # Larguras: total ~535pt (A4 - 60pt margens)
    # Pesos (kg) ampliado de 100 para 130pt para evitar quebra de valores
    div_col_widths = [26, 38, 52, 52, 60, 130, 56, 121]

    # Estilos
    item_style = ParagraphStyle("ItemNum", fontName="Helvetica", fontSize=8, leading=11,
                                textColor=SLATE_500, alignment=TA_CENTER)
    sev_style = ParagraphStyle("SevCell", fontName="Helvetica", fontSize=8, leading=11,
                               textColor=SLATE_700, alignment=TA_CENTER)
    placa_style = ParagraphStyle("PlacaVal", fontName="Helvetica-Bold", fontSize=8, leading=11,
                                 textColor=SLATE_900, alignment=TA_CENTER)
    data_date_style = ParagraphStyle("DataDate", fontName="Helvetica", fontSize=8, leading=11,
                                     textColor=SLATE_700, alignment=TA_CENTER)
    data_time_style = ParagraphStyle("DataTime", fontName="Helvetica", fontSize=7, leading=9,
                                     textColor=SLATE_500, alignment=TA_CENTER)
    prod_style = ParagraphStyle("ProdCell", fontName="Helvetica", fontSize=8, leading=11,
                                textColor=SLATE_700, alignment=TA_LEFT)
    det_diag_style = ParagraphStyle("DetDiag", fontName="Helvetica", fontSize=8, leading=11,
                                    textColor=SLATE_600, alignment=TA_LEFT)
    det_corr_style = ParagraphStyle("DetCorr", fontName="Helvetica", fontSize=7.5, leading=10,
                                    textColor=SLATE_500, alignment=TA_LEFT)

    # Estilo coluna pesos (label + valor por coluna)
    peso_col_style = ParagraphStyle("PesoCol", fontName="Helvetica", fontSize=7.5, leading=10,
                                    textColor=PESOS_LABEL, alignment=TA_CENTER)

    # Header
    div_table_data = [[
        Paragraph("Ítem", th_style),
        Paragraph("SEV", th_style),
        Paragraph("Placa", th_style),
        Paragraph("Data", th_style),
        Paragraph("Produto", th_style),
        Paragraph("Pesos (kg)", th_style),
        Paragraph("Status", th_style),
        Paragraph("Detalhe", th_style),
    ]]

    error_types_found = set()

    for idx, item in enumerate(filtered_div):
        status = item.get("Status", "")
        error_types_found.add(status)

        # Ítem
        item_cell = Paragraph(str(idx + 1).zfill(2), item_style)

        # SEV — tag estilizada
        sev_raw = item.get("SEV", "") or ""
        if sev_raw:
            sev_tag_style = ParagraphStyle(
                "SevTag", fontName="Helvetica", fontSize=7.5, leading=10,
                textColor=SLATE_700, alignment=TA_CENTER
            )
            sev_cell = Table(
                [[Paragraph(sev_raw, sev_tag_style)]],
                colWidths=[div_col_widths[1] - 4],
                style=[
                    ("BACKGROUND", (0, 0), (-1, -1), CODE_TAG_BG),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        else:
            sev_cell = Paragraph("\u2014", sev_style)

        # Placa — tag sem borda (fundo cinza sutil)
        placa_val = item.get("Placa", "—")
        placa_tag = Table(
            [[Paragraph(placa_val, placa_style)]],
            colWidths=[div_col_widths[2] - 4],
            style=[
                ("BACKGROUND", (0, 0), (-1, -1), CODE_TAG_BG),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )

        # Data — date + time em duas linhas
        dt_raw = item.get("Data", "—")
        if " " in dt_raw:
            date_part, time_part = dt_raw.split(" ", 1)
        else:
            date_part, time_part = dt_raw, ""
        date_parts = [[Paragraph(date_part, data_date_style)]]
        if time_part:
            date_parts.append([Paragraph(time_part, data_time_style)])
        data_table = Table(date_parts, colWidths=[div_col_widths[3] - 2],
                           style=[("TOPPADDING", (0, 0), (-1, -1), 1),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 1)])

        # Produto
        prod_raw = item.get("Produto", "") or ""
        prod_clean = prod_raw.replace(" (Deduzido)", "").strip()
        prod_cell = Paragraph(prod_clean, prod_style)

        # Pesos — grid 3 colunas: label + valor, separador vertical
        pb = item.get("Peso Bruto")
        tara = item.get("Tara")
        pl = item.get("Peso Liquido")
        if pl is None:
            pl = (pb or 0) - (tara or 0)

        def _peso_block(label: str, val) -> str:
            if val is None or pd.isna(val):
                val_str = "—"
            else:
                try:
                    val_str = f"{int(float(val)):,}".replace(",", ".")
                except Exception:
                    val_str = str(val)
            # Use non-breaking spaces (\xa0) to prevent word-wrap on the value
            val_str_nb = val_str.replace(" ", "\xa0")
            return (
                f'<font color="{PESOS_LABEL.hexval()}" size="7">{label}</font>'
                f'<br/>'
                f'<font color="{PESOS_VALUE.hexval()}" size="8"><b>{val_str_nb}</b></font>'
            )

        pesos_row = [
            Paragraph(_peso_block("BRUTO", pb), peso_col_style),
            Paragraph(_peso_block("TARA", tara), peso_col_style),
            Paragraph(_peso_block("LÍQ.", pl), peso_col_style),
        ]
        peso_sub_w = (div_col_widths[5] - 4) / 3
        pesos_table = Table(
            [pesos_row],
            colWidths=[peso_sub_w] * 3,
            style=[
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LINEAFTER", (0, 0), (0, -1), 0.5, PESOS_SEP),
                ("LINEAFTER", (1, 0), (1, -1), 0.5, PESOS_SEP),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 1),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1),
            ]
        )

        # Status — badge consistente
        s = (status or "").strip().lower()
        if "erro de placa" in s:
            badge_bg, badge_fg = STATUS_ERRO_BG, STATUS_ERRO_FG
        elif "falta no excel" in s:
            badge_bg, badge_fg = STATUS_FALTA_EXCEL_BG, STATUS_FALTA_EXCEL_FG
        elif "falta no pdf" in s:
            badge_bg, badge_fg = STATUS_FALTA_PDF_BG, STATUS_FALTA_PDF_FG
        else:
            badge_bg, badge_fg = STATUS_ERRO_BG, STATUS_ERRO_FG

        badge_style = ParagraphStyle("Badge", fontName="Helvetica-Bold", fontSize=7, leading=9,
                                     textColor=badge_fg, alignment=TA_CENTER)
        badge_table = Table(
            [[Paragraph(status, badge_style)]],
            colWidths=[div_col_widths[6] - 2],
            style=[
                ("BACKGROUND", (0, 0), (-1, -1), badge_bg),
                ("BOX", (0, 0), (-1, -1), 0.5, badge_fg),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )

        # Detalhe — 2 níveis com hierarquia
        placa_excel = item.get("Placa_Excel", "")
        placa_pdf = item.get("Placa_PDF", "")
        linha_erro = item.get("linha_erro_data", "")
        aba_erro = item.get("aba_erro_data", "")
        arquivo_erro = item.get("arquivo_erro_data", "")
        data_errada = item.get("data_errada_excel", "")

        if placa_excel and placa_pdf:
            diag = Paragraph("Placa digitada incorretamente.", det_diag_style)
            corr = Paragraph(
                f'<font color="#94A3B8">{placa_excel}</font>'
                f' <font color="#64748B">→</font> '
                f'<font face="Courier" color="#0F172A" backcolor="#F1F5F9">{placa_pdf}</font>',
                det_corr_style
            )
            detalhe_rows = [[diag], [corr]]
        elif linha_erro:
            diag = Paragraph("Registro no PDF sem correspondência na planilha.", det_diag_style)
            nota = (
                f"Linha {linha_erro}"
                + (f" (Aba '{aba_erro}')" if aba_erro else "")
                + (f" de {arquivo_erro}" if arquivo_erro else "")
                + (f" com data {data_errada}." if data_errada else ".")
            )
            nota_style = ParagraphStyle("DetNota", fontName="Helvetica", fontSize=7, leading=9,
                                        textColor=SLATE_500, alignment=TA_LEFT)
            detalhe_rows = [[diag], [Paragraph(nota, nota_style)]]
        else:
            diag = Paragraph(item.get("Detalhe", "") or "", det_diag_style)
            detalhe_rows = [[diag]]

        detalhe_inner = Table(detalhe_rows, colWidths=[div_col_widths[7] - 2],
                              style=[("TOPPADDING", (0, 0), (-1, -1), 1),
                                     ("BOTTOMPADDING", (0, 0), (-1, -1), 1)])

        row = [item_cell, sev_cell, placa_tag, data_table, prod_cell,
               pesos_table, badge_table, detalhe_inner]
        div_table_data.append(row)

    if num_div == 0:
        empty_p = Paragraph("—", td_style_center)
        div_table_data.append([empty_p for _ in range(8)])

    # Estilização da Tabela de Divergências
    div_t_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SLATE_900),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, SLATE_200),
        ("BOX", (0, 0), (-1, -1), 0.6, SLATE_300),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        # Zebra striping sutil
        *[("BACKGROUND", (0, i + 1), (-1, i + 1),
           ZEBRA_ODD if i % 2 == 1 else colors.white)
          for i in range(len(filtered_div))],
    ])

    if num_div == 0:
        div_t_style.add("BACKGROUND", (0, 1), (-1, 1), SLATE_50)

    div_table = Table(div_table_data, colWidths=div_col_widths, style=div_t_style, repeatRows=1)
    story.append(div_table)
    story.append(Spacer(1, 24))

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
    story.append(Spacer(1, 6))

    # ── Barra de Progresso Visual ──────────────────────────────
    bar_total_w = 535.3
    bar_fill_w = max(bar_total_w * (pct_sem_erro / 100.0), 1)
    bar_empty_w = bar_total_w - bar_fill_w

    bar_fill_color = status_color
    bar_bg_color = SLATE_100

    bar_label_style = ParagraphStyle(
        "BarLabel", fontName="Helvetica-Bold", fontSize=7,
        leading=9, textColor=colors.white, alignment=TA_CENTER
    )
    bar_data = [[Paragraph(f"{pct_str} Conformidade", bar_label_style), Paragraph("", bar_label_style)]]
    bar_table = Table(
        bar_data,
        colWidths=[bar_fill_w, bar_empty_w],
        rowHeights=[16],
        style=[
            ("BACKGROUND", (0, 0), (0, 0), bar_fill_color),
            ("BACKGROUND", (1, 0), (1, 0), bar_bg_color),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]
    )
    story.append(bar_table)
    story.append(Spacer(1, 24))

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
        action_num = 1
        if "Erro de Placa" in error_types_found:
            story.append(Paragraph(
                f"{action_num}. <b>Correção de Digitação de Placas:</b> Foram identificados erros na digitação "
                "de placas entre a planilha Excel e o relatório OpenPort. Orientar os balanceiros para "
                "reforçar a conferência visual da placa antes do registro, especialmente em situações de "
                "alto volume de operação.",
                bullet_style
            ))
            action_num += 1

        if "Falta no Excel" in error_types_found:
            story.append(Paragraph(
                f"{action_num}. <b>Registros Ausentes na Planilha:</b> Existem pesagens registradas no sistema OpenPort "
                "que não constam na planilha Excel. Verificar se houve omissão no preenchimento manual "
                "e orientar a equipe para que todas as pesagens sejam devidamente registradas.",
                bullet_style
            ))
            action_num += 1

        if "Falta no PDF" in error_types_found:
            story.append(Paragraph(
                f"{action_num}. <b>Registros Ausentes no OpenPort:</b> Existem registros na planilha Excel que não "
                "possuem correspondência no relatório OpenPort. Verificar se a balança estava operando "
                "corretamente nos períodos correspondentes e se o sistema registrou todas as pesagens.",
                bullet_style
            ))
            action_num += 1

        if "Diferença de Peso" in error_types_found:
            story.append(Paragraph(
                f"{action_num}. <b>Diferenças de Peso:</b> Foram constatadas divergências nos valores de peso bruto "
                "e/ou tara entre as fontes. Verificar a calibração das balanças e se os valores estão "
                "sendo transferidos corretamente para as planilhas.",
                bullet_style
            ))
            action_num += 1



    # ══════════════════════════════════════════════════════════════
    # SEÇÃO 4: Resumo por Produto
    # ══════════════════════════════════════════════════════════════
    story.append(Spacer(1, 24))
    # Os elementos desta seção são agrupados com KeepTogether para
    # evitar que a tabela de produtos seja separada do título em
    # páginas diferentes.
    sec4_elements = []
    sec4_elements.append(Paragraph("4. Resumo por Produto", title_style))
    sec4_elements.append(Paragraph(
        "Distribuição das viagens e divergências agrupadas por produto movimentado:",
        body_style
    ))
    sec4_elements.append(Spacer(1, 4))

    # Agrupar dados por produto
    prod_stats = {}
    for item in filtered_ok:
        prod = (item.get("Produto", "") or "").replace(" (Deduzido)", "").strip()
        if not prod or prod in ("Não Identificado", "") or prod.startswith("Ambíguo"):
            prod = "Não Identificado"
        if prod not in prod_stats:
            prod_stats[prod] = {"viagens": 0, "divergencias": 0}
        prod_stats[prod]["viagens"] += 1

    for item in filtered_div:
        prod = (item.get("Produto", "") or "").replace(" (Deduzido)", "").strip()
        if not prod or prod in ("Não Identificado", "") or prod.startswith("Ambíguo"):
            prod = "Não Identificado"
        if prod not in prod_stats:
            prod_stats[prod] = {"viagens": 0, "divergencias": 0}
        prod_stats[prod]["viagens"] += 1
        prod_stats[prod]["divergencias"] += 1

    if prod_stats:
        prod_th = ParagraphStyle("ProdTH", fontName="Helvetica-Bold", fontSize=8,
                                  leading=10, textColor=colors.white, alignment=TA_LEFT)
        prod_th_c = ParagraphStyle("ProdTHC", fontName="Helvetica-Bold", fontSize=8,
                                    leading=10, textColor=colors.white, alignment=TA_CENTER)
        prod_td = ParagraphStyle("ProdTD", fontName="Helvetica", fontSize=8,
                                  leading=11, textColor=SLATE_700, alignment=TA_LEFT)
        prod_td_c = ParagraphStyle("ProdTDC", fontName="Helvetica", fontSize=8,
                                    leading=11, textColor=SLATE_700, alignment=TA_CENTER)
        prod_td_g = ParagraphStyle("ProdTDG", fontName="Helvetica-Bold", fontSize=8,
                                    leading=11, textColor=GREEN_700, alignment=TA_CENTER)

        prod_table_data = [[
            Paragraph("Produto", prod_th),
            Paragraph("Viagens", prod_th_c),
            Paragraph("Divergências", prod_th_c),
            Paragraph("% Conformidade", prod_th_c),
        ]]

        for prod_name in sorted(prod_stats.keys()):
            stats = prod_stats[prod_name]
            total = stats["viagens"]
            divs = stats["divergencias"]
            pct = ((total - divs) / total * 100.0) if total > 0 else 0.0
            pct_formatted = f"{pct:.1f}%".replace(".", ",")
            pct_style = prod_td_g if pct >= 95.0 else prod_td_c

            prod_table_data.append([
                Paragraph(prod_name, prod_td),
                Paragraph(str(total), prod_td_c),
                Paragraph(str(divs), prod_td_c),
                Paragraph(pct_formatted, pct_style),
            ])

        prod_col_w = [200, 111.77, 111.77, 111.77]
        prod_t_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SLATE_900),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, SLATE_200),
            ("BOX", (0, 0), (-1, -1), 0.5, SLATE_300),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            *[("BACKGROUND", (0, i + 1), (-1, i + 1),
               ZEBRA_ODD if i % 2 == 1 else colors.white)
              for i in range(len(prod_stats))],
        ])

        prod_table = Table(prod_table_data, colWidths=prod_col_w, style=prod_t_style, repeatRows=1)
        sec4_elements.append(prod_table)

    # Agrupar toda a seção 4 com KeepTogether para não separar entre páginas
    story.append(KeepTogether(sec4_elements))

    # Campo de assinatura removido conforme solicitação.

    # Injetar variáveis de instância no canvasmaker personalizado
    integrity_hash = payload.get("integrity_hash", "")
    canvasmaker = make_canvas_maker(periodo_str, emissao_str, integrity_hash, has_divergencias=(num_div > 0))

    # Build PDF
    doc.build(story, canvasmaker=canvasmaker)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes, filename

def make_canvas_maker(periodo_str: str, emissao_str: str, integrity_hash: str, has_divergencias: bool = True):
    class CustomNumberedCanvas(NumberedCanvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._periodo_str = periodo_str
            self._emissao_str = emissao_str
            self._integrity_hash = integrity_hash
            self._has_divergencias = has_divergencias
    return CustomNumberedCanvas
