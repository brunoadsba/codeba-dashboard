import os
import sys
from pathlib import Path
import requests

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = "http://127.0.0.1:8000"

def run_test_case(name, func, *args, **kwargs):
    print(f"Running {name:.<60}", end="", flush=True)
    try:
        func(*args, **kwargs)
        print(" [PASS]")
        return True
    except Exception as e:
        print(" [FAIL]")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_frontend():
    # 1. Testar home page
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert "CODEBA" in r.text
    assert "filter-produto" in r.text
    assert "compliance-panel" in r.text

    # 2. Testar JS estático
    r_js = requests.get(f"{BASE_URL}/static/js/app.js")
    assert r_js.status_code == 200
    assert "createProductBadge" in r_js.text

def test_flow_completo(excel_path, pdf_path):
    # 1. Upload dos arquivos
    with open(excel_path, 'rb') as f1, open(pdf_path, 'rb') as f2:
        files = [
            ('files', (excel_path.name, f1, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')),
            ('files', (pdf_path.name, f2, 'application/pdf'))
        ]
        r = requests.post(f"{BASE_URL}/api/upload", files=files)
    
    assert r.status_code == 200, f"Upload falhou: {r.status_code} - {r.text}"
    data = r.json()
    assert 'error' not in data, f"Erro no upload: {data.get('error')}"
    assert 'run_id' in data
    assert 'resumo' in data
    assert 'ok' in data
    assert 'divergencias' in data

    run_id = data['run_id']
    resumo = data['resumo']
    
    # 2. Listar Runs
    r_list = requests.get(f"{BASE_URL}/api/runs")
    assert r_list.status_code == 200
    runs = r_list.json().get('runs', [])
    assert any(run['id'] == run_id for run in runs), f"Run {run_id} não encontrada no histórico"

    # 3. Obter Detalhes da Run
    r_detail = requests.get(f"{BASE_URL}/api/runs/{run_id}")
    assert r_detail.status_code == 200
    detail_data = r_detail.json()
    assert detail_data['run_id'] == run_id
    assert detail_data['resumo']['total_processado'] == resumo['total_processado']

    # 4. Gerar Relatório PDF sem filtros
    r_report = requests.get(f"{BASE_URL}/api/runs/{run_id}/report")
    assert r_report.status_code == 200, f"Falha no relatório PDF: {r_report.status_code}"
    assert r_report.headers.get("content-type") == "application/pdf"
    assert "attachment; filename=" in r_report.headers.get("Content-Disposition", "")
    assert len(r_report.content) > 0

    # 5. Gerar Relatório PDF com filtros
    r_report_filtered = requests.get(f"{BASE_URL}/api/runs/{run_id}/report", params={
        "placa": "XYZ1234",
        "produto": "LITIO"
    })
    assert r_report_filtered.status_code == 200
    assert r_report_filtered.headers.get("content-type") == "application/pdf"
    assert len(r_report_filtered.content) > 0

    # 6. Excluir Run
    r_del = requests.get(f"{BASE_URL}/api/runs") # Verificando antes
    initial_count = len(r_del.json().get('runs', []))
    
    r_delete = requests.delete(f"{BASE_URL}/api/runs/{run_id}")
    assert r_delete.status_code == 200
    assert r_delete.json().get("deleted") is True

    # 7. Confirmar exclusão
    r_after_del = requests.get(f"{BASE_URL}/api/runs/{run_id}")
    assert r_after_del.status_code == 404

def main():
    print("==========================================================")
    print("CODEBA AUDITORIA - EXECUTANDO TESTES END-TO-END NO SERVIDOR")
    print("==========================================================")

    data_dir = project_root / "data"
    excel_path = data_dir / "LITIO - CBL.xlsx"
    
    # Encontrar PDF na pasta data/
    pdfs = [f for f in data_dir.iterdir() if f.suffix.lower() == '.pdf']
    if not pdfs:
        print("Erro: Nenhum arquivo PDF encontrado na pasta data/")
        sys.exit(1)
    pdf_path = pdfs[0]

    print(f"Endereço do Servidor: {BASE_URL}")
    print(f"Excel de Teste: {excel_path}")
    print(f"PDF de Teste: {pdf_path}")
    print("----------------------------------------------------------")

    success = True
    success &= run_test_case("Testar Frontend e Arquivos Estáticos", test_frontend)
    success &= run_test_case("Testar Fluxo Completo de Auditoria (E2E)", test_flow_completo, excel_path, pdf_path)

    print("----------------------------------------------------------")
    if success:
        print("TODOS OS TESTES E2E PASSARAM COM SUCESSO!")
        sys.exit(0)
    else:
        print("FALHA EM ALGUNS TESTES E2E!")
        sys.exit(1)


if __name__ == "__main__":
    main()
