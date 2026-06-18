import os
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent


def ensure_fixtures():
    xlsx_path = FIXTURES_DIR / "litio_test.xlsx"
    pdf_path = FIXTURES_DIR / "relatorio_test.pdf"

    if xlsx_path.exists() and pdf_path.exists():
        return

    from openpyxl import Workbook
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.lib import colors

    if not xlsx_path.exists():
        wb = Workbook()
        ws = wb.active
        ws.title = "Pesagens"
        ws.append(["PLACA", "DATA", "PESO BRUTO", "TARA"])
        ws.append(["ABC1D23", "01/06/2026", 59160, 20860])
        ws.append(["XYZ9W87", "02/06/2026", 60300, 21500])
        ws.append(["JKL4M56", "03/06/2026", 58000, 20000])
        ws.append(["PFI5E14", "03/06/2026", 62000, 22000])
        wb.save(xlsx_path)

    if not pdf_path.exists():
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
        elements = []
        headers = ["PLACA", "DATA", "PESO BRUTO", "TARA", "SEV"]
        data = [
            headers,
            ["ABC1D23", "01/06/2026", "59160", "20860", "123456"],
            ["XYZ9W87", "02/06/2026", "60300", "21500", "123457"],
            ["JKL4M56", "03/06/2026", "58000", "20000", "123458"],
            ["PFI5E14", "03/06/2026", "62000", "22000", "123459"],
        ]
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
        doc.build(elements)

    # Ensure files were created
    assert xlsx_path.exists(), f"Failed to create {xlsx_path}"
    assert pdf_path.exists(), f"Failed to create {pdf_path}"


if __name__ == "__main__":
    ensure_fixtures()
    print("Fixtures created successfully.")
