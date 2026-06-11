"""
Configuração centralizada do projeto CODEBA.

Todas as constantes e settings ficam aqui, lidas de variáveis de ambiente
com fallback para valores padrão seguros.
"""

import os
from pathlib import Path

# ── Diretórios base ──────────────────────────────────────────
# Raiz do projeto = operacao/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

STATIC_DIR = PROJECT_ROOT / "static"
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", str(PROJECT_ROOT / "temp_uploads"))
LOG_DIR = os.environ.get("LOG_DIR", str(PROJECT_ROOT / "logs"))
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(PROJECT_ROOT / "data" / "auditoria.db"))

# ── Servidor ─────────────────────────────────────────────────
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# ── Upload: Segurança ───────────────────────────────────────
# Extensões permitidas (allow-list)
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".pdf"}

# Limite de tamanho: 50 MB (configurável via env)
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE_MB", "50")) * 1024 * 1024

# TODO(security): Em produção, configurar CSRF tokens, Content Security Policy
# headers, autenticação e rate limiting.
