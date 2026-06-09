import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.services.report_generator import (
    _format_date_to_local,
    _extract_weights_from_detail,
    _calculate_plate_similarity,
    generate_markdown_report,
    generate_pdf_report,
)
from src.services.persistence import save_audit_run, init_db

def test_format_date_to_local():
    # Caso 8601 com 'Z'
    assert "09/06/2026 15:00:00" in _format_date_to_local("2026-06-09T18:00:00Z")
    # Caso 8601 com offset '+00:00'
    assert "09/06/2026 15:00:00" in _format_date_to_local("2026-06-09T18:00:00+00:00")
    # Caso com frações de segundo e offset
    assert "09/06/2026 15:00:00" in _format_date_to_local("2026-06-09T18:00:00.123456+00:00")
    # String não formatável retorna a própria string
    assert _format_date_to_local("Texto Invalido") == "Texto Invalido"
    assert _format_date_to_local("") == "Data não disponível"

def test_extract_weights_from_detail():
    # Com ponto flutuante
    detail = "[Planilha: LÍTIO] Bruto 42100.0 / Tara 16000.0 != [PDF: LÍTIO] Bruto 42500.0 / Tara 16000.0"
    w1, w2 = _extract_weights_from_detail(detail)
    assert w1 == 42100.0
    assert w2 == 42500.0

    # Com valores inteiros
    detail_int = "[Planilha: LÍTIO] Bruto 42100 / Tara 16000 != [PDF: LÍTIO] Bruto 42500 / Tara 16000"
    w1, w2 = _extract_weights_from_detail(detail_int)
    assert w1 == 42100.0
    assert w2 == 42500.0

    # Caso com formatos inválidos ou ausentes
    assert _extract_weights_from_detail("Sem pesos aqui") == (0.0, 0.0)

def test_calculate_plate_similarity():
    assert "85.7%" in _calculate_plate_similarity("PFI5E14", "PFI5E17")
    assert "100.0%" in _calculate_plate_similarity("ABC1234", "ABC1234")
    assert _calculate_plate_similarity("", "ABC1234") == "N/A"

def test_generate_markdown_report():
    payload = {
        "run_id": "test-run-xyz",
        "created_at": "2026-06-09T18:00:00Z",
        "resumo": {
            "total_processado": 4,
            "ok": 2,
            "divergencias": 2
        },
        "divergencias": [
            {
                "Placa": "ABC1234",
                "Data": "05/06/2026",
                "Status": "Diferença de Peso",
                "Detalhe": "[Planilha: LÍTIO] Bruto 42100.0 / Tara 16000.0 != [PDF: LÍTIO] Bruto 42500.0 / Tara 16000.0",
                "Produto": "LÍTIO",
                "Cliente": "CLIENTE A",
                "Peso Bruto": 42100.0,
                "Tara": 16000.0,
                "SEV": "789012"
            },
            {
                "Placa": "PFI5E14",
                "Placa_Excel": "PFI5E14",
                "Placa_PDF": "PFI5E17",
                "Data": "05/06/2026",
                "Status": "Erro de Placa",
                "Detalhe": "Placa similar com pesos idênticos.",
                "Produto": "LÍTIO",
                "Cliente": "CLIENTE A",
                "Peso Bruto": 38300.0,
                "Tara": 15200.0,
                "SEV": "123456"
            }
        ]
    }
    
    report = generate_markdown_report(payload, ["teste.xlsx", "teste.pdf"])
    
    assert "# 📊 Relatório de Auditoria de Pesagens Portuárias (CODEBA)" in report
    assert "test-run-xyz" in report
    assert "teste.xlsx, teste.pdf" in report
    assert "🎯 KPI de Acurácia:** **50.00%**" in report
    assert "Diferença de Peso:** 1 ocorrência(s)" in report
    assert "Erro de Placa:** 1 ocorrência(s)" in report
    assert "### ⚠️ Status: Diferença de Peso" in report
    assert "Peso Excel (42100.0kg) vs Peso PDF (42500.0kg)" in report
    assert "Diferença:** **400.00kg**" in report

def test_api_report_endpoint(client, tmp_path):
    # Inicializar o banco de dados temporário e injetar para teste
    db = tmp_path / "test_report.db"
    init_db(db)
    
    # Criar uma auditoria de exemplo
    result = {
        "resumo": {"total_processado": 1, "ok": 1, "divergencias": 0},
        "ok": [{
            "Placa": "ABC1234",
            "Data": "05/06/2026",
            "Produto": "LÍTIO",
            "Peso Liquido": 30000.0,
            "Peso Bruto": 45000.0,
            "Tara": 15000.0,
            "Cliente": "CLIENTE A",
            "SEV": "123456",
            "Detalhe": "Pesagem exata"
        }],
        "divergencias": [],
        "produtos_detectados": ["LÍTIO"],
        "clientes_por_produto": {"LÍTIO": ["CLIENTE A"]},
        "volume": {"records": [], "meta": {}}
    }
    
    # Usar patch no DATABASE_PATH do app.py para apontar para o nosso db temporário
    with patch("src.app.DATABASE_PATH", str(db)):
        save_audit_run(db, result, ["test1.xlsx", "test2.pdf"], run_id="my-test-run")
        
        # Testar requisição 200
        response = client.get("/api/runs/my-test-run/report")
        assert response.status_code == 200
        assert "application/pdf" in response.headers["content-type"]
        assert "attachment; filename=relatorio_executivo_auditoria_my-test-run.pdf" in response.headers["content-disposition"]
        content = response.content
        assert content.startswith(b"%PDF")
        
        # Testar requisição 404
        response_404 = client.get("/api/runs/non-existent-run/report")
        assert response_404.status_code == 404
