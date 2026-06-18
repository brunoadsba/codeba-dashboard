import os


def test_upload_completo(client, excel_dir, pdf_path):
    """TESTE 1: Upload completo (todas as planilhas + PDF curto)"""
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

        # Enviar request
        response = client.post("/api/upload", files=files)

        assert response.status_code == 200
        data = response.json()

        assert 'error' not in data
        assert 'resumo' in data
        assert 'ok' in data
        assert 'divergencias' in data
        assert 'produtos_detectados' in data
        assert 'volume' in data
        assert 'records' in data['volume']
        assert 'run_id' in data
        assert 'created_at' in data

        if len(data['volume']['records']) > 0:
            rec = data['volume']['records'][0]
            assert 'toneladas' in rec
            assert 'produto' in rec
            assert 'data' in rec
            assert 'is_ok' in rec

        resumo = data['resumo']
        ok_list = data['ok']
        div_list = data['divergencias']
        produtos = data['produtos_detectados']

        assert resumo.get('ok', 0) > 0
        assert resumo.get('total_processado', 0) == len(ok_list) + len(div_list)
 
        assert len(produtos) >= 2
        assert any('LITIO' in p.upper() for p in produtos)

        # Validar registros OK
        if len(ok_list) > 0:
            sample = ok_list[0]
            required_fields = ['Placa', 'Data', 'Peso Bruto', 'Tara', 'Peso Liquido', 'Produto', 'SEV']
            for field in required_fields:
                assert field in sample

            for item in ok_list:
                expected_pl = item['Peso Bruto'] - item['Tara']
                assert abs(item.get('Peso Liquido', 0) - expected_pl) < 0.1
                assert item.get('Produto') != ""

        # Validar divergências
        if len(div_list) > 0:
            sample_div = div_list[0]
            div_fields = ['Placa', 'Data', 'Status', 'Detalhe', 'Produto']
            for field in div_fields:
                assert field in sample_div

        # Validar Erros de Placa
        typos = [d for d in div_list if d.get('Status') == 'Erro de Placa']
        for t in typos:
            assert 'Placa_Excel' in t
            assert 'Placa_PDF' in t
            assert t.get('Placa_Excel') != t.get('Placa_PDF')

        # Validar Dedução de Produto
        inferred = [d for d in div_list if '(Deduzido)' in d.get('Produto', '')]
        not_id = [d for d in div_list if d.get('Produto') == 'Não Identificado']
        for d in inferred + not_id:
            assert d.get('Status') == 'Falta no Excel'

        # Validar API de histórico
        run_id = data['run_id']
        list_resp = client.get("/api/runs")
        assert list_resp.status_code == 200
        listing = list_resp.json()
        assert listing['total'] >= 1
        assert any(r['id'] == run_id for r in listing['runs'])

        detail_resp = client.get(f"/api/runs/{run_id}")
        assert detail_resp.status_code == 200
        loaded = detail_resp.json()
        assert loaded['run_id'] == run_id
        assert loaded['resumo']['total_processado'] == resumo['total_processado']

    finally:
        for opened in opened_files:
            opened.close()


def test_upload_so_pdf(client, pdf_path):
    """TESTE 2: Upload só PDF (sem Excel)"""
    opened_files = []
    try:
        pdf_opened = open(pdf_path, 'rb')
        opened_files.append(pdf_opened)
        files = [('files', (pdf_path.name, pdf_opened, 'application/pdf'))]

        response = client.post("/api/upload", files=files)
        assert response.status_code == 200

        data = response.json()
        resumo = data.get('resumo', {})
        assert resumo.get('ok', 0) == 0
        assert resumo.get('divergencias', 0) > 0

        divs = data.get('divergencias', [])
        falta_excel = [d for d in divs if d.get('Status') == 'Falta no Excel']
        assert len(falta_excel) == len(divs)

    finally:
        for opened in opened_files:
            opened.close()


def test_frontend_acessivel(client):
    """TESTE 3: Frontend acessível"""
    response = client.get("/")
    assert response.status_code == 200
    assert 'CODEBA' in response.text
    assert 'filter-produto' in response.text
    assert 'product-conformity' in response.text
    assert 'compliance-panel' in response.text
    assert 'analytics-section' in response.text
    assert 'history-drawer' in response.text

    # Testar JS
    response_js = client.get("/static/js/app.js")
    assert response_js.status_code == 200
    assert 'createProductBadge' in response_js.text
    assert 'createPlateDiff' in response_js.text
    assert 'renderProductBars' in response_js.text

    response_analytics = client.get("/static/js/analytics.js")
    assert response_analytics.status_code == 200
    assert 'aggregateVolume' in response_analytics.text

    # Testar CSS
    response_css = client.get("/static/css/style.css")
    assert response_css.status_code == 200
    assert '.badge-produto' in response_css.text
    assert '.placa-diff' in response_css.text
    assert '.product-chip' in response_css.text
    assert '.compliance-panel' in response_css.text
