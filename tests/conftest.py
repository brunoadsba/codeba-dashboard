from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.app import app


@pytest.fixture
def project_root() -> Path:
    """Retorna o caminho raiz do projeto (operacao/)."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def data_dir(project_root) -> Path:
    """Retorna o caminho da pasta data/."""
    return project_root / "data"


@pytest.fixture
def fixtures_dir(project_root) -> Path:
    """Retorna o caminho da pasta tests/fixtures/."""
    return project_root / "tests" / "fixtures"


@pytest.fixture
def excel_dir(data_dir, fixtures_dir) -> Path:
    """Retorna data/excel/, data/ ou tests/fixtures/ (nessa ordem de prioridade)."""
    # Garantir que fixtures existam
    from tests.fixtures.generate import ensure_fixtures
    ensure_fixtures()

    if (data_dir / "excel").exists():
        return data_dir / "excel"
    # Verificar se há .xlsx em data/
    if list(data_dir.glob("*.xlsx")):
        return data_dir
    return fixtures_dir


@pytest.fixture
def pdf_path(data_dir, fixtures_dir) -> Path:
    """Retorna o caminho do PDF, com fallback para fixtures."""
    from tests.fixtures.generate import ensure_fixtures
    ensure_fixtures()

    p = data_dir / "relatorios" / "13_05_2026_a_02_06_2026.pdf"
    if p.exists():
        return p
    pdfs = [f for f in data_dir.iterdir() if f.suffix.lower() == '.pdf']
    if pdfs:
        return pdfs[0]
    return fixtures_dir / "relatorio_test.pdf"


@pytest.fixture
def client():
    """TestClient com lifespan (init do SQLite)."""
    with TestClient(app) as c:
        yield c
