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
def excel_dir(data_dir) -> Path:
    """Retorna o caminho da pasta data/excel/ com fallback para data/."""
    p = data_dir / "excel"
    return p if p.exists() else data_dir


@pytest.fixture
def pdf_path(data_dir) -> Path:
    """Retorna o caminho do PDF utilizado nos testes, com fallback para o primeiro PDF encontrado em data/."""
    p = data_dir / "relatorios" / "13_05_2026_a_02_06_2026.pdf"
    if p.exists():
        return p
    # Fallback para o primeiro PDF em data/
    pdfs = [f for f in data_dir.iterdir() if f.suffix.lower() == '.pdf']
    if pdfs:
        return pdfs[0]
    return p


@pytest.fixture
def client():
    """TestClient com lifespan (init do SQLite)."""
    with TestClient(app) as c:
        yield c

