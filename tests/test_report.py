import os


def test_report_endpoint(client, excel_dir, pdf_path):
    """Testa a geração de relatório PDF da auditoria"""
    files = []
    opened_files = []

    try:
        # Adicionar todos os Excels
        excel_files = [f for f in os.listdir(excel_dir) if f.endswith('.xlsx')]
        for f in excel_files:
            fp = excel_dir / f
            opened = open(fp, 'rb')
            opened_files.append(opened)
            files.append(('files', (f, opened, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')))

        # Adicionar o PDF
        pdf_opened = open(pdf_path, 'rb')
        opened_files.append(pdf_opened)
        files.append(('files', (pdf_path.name, pdf_opened, 'application/pdf')))

        # Enviar request de upload para gerar uma run
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert 'run_id' in data
        run_id = data['run_id']

        # Testar GET sem filtros
        report_resp = client.get(f"/api/runs/{run_id}/report")
        assert report_resp.status_code == 200
        assert report_resp.headers["content-type"] == "application/pdf"
        assert "Content-Disposition" in report_resp.headers
        cd_header = report_resp.headers["Content-Disposition"]
        assert "attachment" in cd_header
        assert "filename=" in cd_header or "filename*=" in cd_header
        assert ".pdf" in cd_header
        assert len(report_resp.content) > 0
        assert b"SEV" in report_resp.content

        # Testar GET com filtros
        report_filtered_resp = client.get(f"/api/runs/{run_id}/report", params={
            "placa": "XYZ1234",
            "produto": "LITIO",
            "date_start": "2026-05-13",
            "date_end": "2026-06-02"
        })
        assert report_filtered_resp.status_code == 200
        assert report_filtered_resp.headers["content-type"] == "application/pdf"
        assert len(report_filtered_resp.content) > 0

        # Testar GET com run_id inexistente
        fake_run_id = "non-existent-uuid"
        report_fake_resp = client.get(f"/api/runs/{fake_run_id}/report")
        assert report_fake_resp.status_code == 404
        assert "error" in report_fake_resp.json()

    finally:
        for opened in opened_files:
            opened.close()
