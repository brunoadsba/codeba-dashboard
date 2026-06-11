import pytest
from pathlib import Path
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
    """Retorna o caminho da pasta data/excel/."""
    return data_dir / "excel"


@pytest.fixture
def pdf_path(data_dir) -> Path:
    """Retorna o caminho do PDF utilizado nos testes."""
    return data_dir / "relatorios" / "13_05_2026_a_02_06_2026.pdf"


@pytest.fixture
def client():
    """TestClient com lifespan (init do SQLite)."""
    with TestClient(app) as c:
        yield c
