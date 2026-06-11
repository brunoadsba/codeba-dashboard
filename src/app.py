import logging
import os
import time
import uuid
import traceback
import gc
from contextlib import asynccontextmanager
from typing import List

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

from src.config import STATIC_DIR, UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE, HOST, PORT, DATABASE_PATH
from src.logging_config import setup_logging
from src.services.excel_parser import process_excel_file
from src.services.pdf_parser import process_pdf_file
from src.services.reconciliation import reconcile_data
from src.services.persistence import init_db, save_audit_run, list_audit_runs, get_audit_run, delete_audit_run
from src.utils.filename_parser import extract_produto_from_filename, extract_cliente_from_filename

# Inicializar logs
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(DATABASE_PATH)
    logger.info("Banco de dados inicializado: %s", DATABASE_PATH)
    yield


app = FastAPI(title="CODEBA Dashboard MVP", lifespan=lifespan)

# Criar pasta temp para uploads e static
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(STATIC_DIR / "css", exist_ok=True)
os.makedirs(STATIC_DIR / "js", exist_ok=True)
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# Mount pasta static
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_path = STATIC_DIR / "index.html"
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Erro: Arquivo static/index.html não encontrado.</h1>", status_code=404)


@app.get("/api/runs")
async def api_list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return list_audit_runs(DATABASE_PATH, limit=limit, offset=offset)


@app.get("/api/runs/{run_id}")
async def api_get_run(run_id: str):
    payload = get_audit_run(DATABASE_PATH, run_id)
    if not payload:
        return JSONResponse(status_code=404, content={"error": "Auditoria não encontrada."})
    return payload


@app.delete("/api/runs/{run_id}")
async def api_delete_run(run_id: str):
    if delete_audit_run(DATABASE_PATH, run_id):
        return {"deleted": True, "id": run_id}
    return JSONResponse(status_code=404, content={"error": "Auditoria não encontrada."})


@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    dfs_excel = []
    dfs_pdf = []
    saved_files = []
    original_names = []

    try:
        for file in files:
            # Validar extensão (allow-list)
            original_name = file.filename or "unknown"
            ext = os.path.splitext(original_name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                logger.warning(f"Extensão rejeitada: {ext} (arquivo: {original_name})")
                continue

            # Gerar nome seguro com UUID para evitar path traversal
            safe_name = f"{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(UPLOAD_DIR, safe_name)

            # Validar que o path resultante está dentro de UPLOAD_DIR
            resolved_path = os.path.realpath(file_path)
            resolved_upload_dir = os.path.realpath(UPLOAD_DIR) + os.sep
            if not resolved_path.startswith(resolved_upload_dir):
                logger.error(f"Tentativa de path traversal detectada: {original_name}")
                continue

            # Salvar arquivo com limite de tamanho
            try:
                content = await file.read()
                if len(content) > MAX_FILE_SIZE:
                    logger.warning(f"Arquivo muito grande: {original_name} ({len(content)} bytes)")
                    continue

                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                saved_files.append(file_path)
                original_names.append(original_name)
            except Exception as e:
                logger.error(f"Erro ao salvar {original_name}: {e}")
                continue

            # Processar
            logger.info(f"Processando arquivo: {original_name} (salvo como {safe_name})")

            if ext in {'.xlsx', '.xls'}:
                df = process_excel_file(file_path)
                # Preservar o nome original para extrair o produto e cliente
                if not df.empty:
                    df['Produto'] = extract_produto_from_filename(original_name)
                    df['Cliente'] = extract_cliente_from_filename(original_name)

                if not df.empty:
                    dfs_excel.append(df)
                    logger.info(f"  Excel processado: {len(df)} registros")
                else:
                    logger.warning(f"  Excel sem dados válidos: {original_name}")
            elif ext == '.pdf':
                df = process_pdf_file(file_path)
                if not df.empty:
                    dfs_pdf.append(df)
                    logger.info(f"  PDF processado: {len(df)} registros")
                else:
                    logger.warning(f"  PDF sem dados válidos: {original_name}")

        if not dfs_excel and not dfs_pdf:
            logger.warning("Nenhum dado válido encontrado nos arquivos enviados")
            return JSONResponse(
                status_code=200,
                content={"error": "Nenhum dado válido encontrado nos arquivos enviados."}
            )

        df_ex = pd.concat(dfs_excel, ignore_index=True) if dfs_excel else pd.DataFrame()
        df_p = pd.concat(dfs_pdf, ignore_index=True) if dfs_pdf else pd.DataFrame()

        result = reconcile_data(df_ex, df_p)

        if "error" in result:
            return JSONResponse(
                status_code=500,
                content={"error": result.get("error")}
            )

        meta = save_audit_run(DATABASE_PATH, result, original_names)
        result["run_id"] = meta["run_id"]
        result["created_at"] = meta["created_at"]

        logger.info("Auditoria calculada, persistida e retornada com sucesso (run_id=%s)", meta["run_id"])
        return result

    except Exception as e:
        logger.error(f"Erro inesperado no upload: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": "Erro interno ao processar os arquivos. Verifique o log."}
        )
    finally:
        # Liberar handles (openpyxl no Windows) antes de apagar temporários
        gc.collect()
        _cleanup_temp_files(saved_files)


def _cleanup_temp_files(file_paths):
    """Remove arquivos temporários com retry para locks do Windows."""
    for fp in file_paths:
        removed = False
        for attempt in range(5):
            try:
                if os.path.exists(fp):
                    os.remove(fp)
                removed = True
                break
            except PermissionError:
                wait = 0.5 * (attempt + 1)
                logger.warning(
                    "Arquivo bloqueado, tentativa %s/5 em %.1fs: %s",
                    attempt + 1, wait, fp,
                )
                time.sleep(wait)
            except OSError as e:
                if getattr(e, "winerror", None) == 32 and attempt < 4:
                    wait = 0.5 * (attempt + 1)
                    logger.warning(
                        "Arquivo em uso (WinError 32), tentativa %s/5 em %.1fs: %s",
                        attempt + 1, wait, fp,
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"Não foi possível remover {fp}: {e}")
                    break
            except Exception as e:
                logger.error(f"Erro ao remover {fp}: {e}")
                break
        if not removed and os.path.exists(fp):
            logger.error(
                "Arquivo temporário não removido após retries (será ignorado): %s", fp
            )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.app:app", host=HOST, port=PORT, reload=True)
