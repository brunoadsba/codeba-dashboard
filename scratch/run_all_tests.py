import sys
import os
import shutil
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

# Adicionar a raiz do projeto ao path para poder importar src e tests
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.app import app
from tests.test_analytics import (
    test_normalize_product,
    test_net_weight_ok,
    test_net_weight_divergencia,
    test_net_weight_missing,
    test_build_volume_records,
    test_build_volume_records_skips_no_weight,
    test_compute_period_bounds,
)
from tests.test_persistence import (
    test_save_and_load,
    test_list_runs,
    test_delete_run,
    test_init_db_creates_file,
)
from tests.test_recorte_aviso import (
    test_recorte_aviso_excel_fora_intersecao,
    test_sem_aviso_quando_periodos_coincidem,
)
from tests.test_e2e import (
    test_upload_completo,
    test_upload_so_pdf,
    test_frontend_acessivel,
)
from tests.test_report import test_report_endpoint


class TempPath:
    def __init__(self, path):
        self.path = Path(path)

    def __truediv__(self, other):
        return self.path / other

    def exists(self):
        return self.path.exists()


def run_test_case(name, func, *args, **kwargs):
    print(f"Running {name:.<60}", end="", flush=True)
    try:
        func(*args, **kwargs)
        print(" [OK]")
        return True
    except Exception as e:
        print(" [FAIL]")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("==========================================================")
    print("CODEBA AUDITORIA - RUNNING ALL UNIT & E2E TESTS (STANDALONE)")
    print("==========================================================")

    # 1. Configurar fixtures
    data_dir = project_root / "data"
    excel_dir = data_dir / "excel" if (data_dir / "excel").exists() else data_dir
    
    pdf_path = data_dir / "relatorios" / "13_05_2026_a_02_06_2026.pdf"
    if not pdf_path.exists():
        pdfs = [f for f in data_dir.iterdir() if f.suffix.lower() == '.pdf']
        if pdfs:
            pdf_path = pdfs[0]
        else:
            print(f"ERROR: No PDF file found in {data_dir}")
            sys.exit(1)

    print(f"Excel directory: {excel_dir}")
    print(f"PDF path: {pdf_path}")
    print("----------------------------------------------------------")

    success = True

    # 2. Executar testes de Analytics
    success &= run_test_case("test_normalize_product", test_normalize_product)
    success &= run_test_case("test_net_weight_ok", test_net_weight_ok)
    success &= run_test_case("test_net_weight_divergencia", test_net_weight_divergencia)
    success &= run_test_case("test_net_weight_missing", test_net_weight_missing)
    success &= run_test_case("test_build_volume_records", test_build_volume_records)
    success &= run_test_case("test_build_volume_records_skips_no_weight", test_build_volume_records_skips_no_weight)
    success &= run_test_case("test_compute_period_bounds", test_compute_period_bounds)

    # 3. Executar testes de Recorte Aviso
    success &= run_test_case("test_recorte_aviso_excel_fora_intersecao", test_recorte_aviso_excel_fora_intersecao)
    success &= run_test_case("test_sem_aviso_quando_periodos_coincidem", test_sem_aviso_quando_periodos_coincidem)

    # 4. Executar testes de Persistencia (com DB temporário)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        from src.services.persistence import init_db as init_db_real
        db_path_1 = Path(tmpdir) / "test_1.db"
        db_path_2 = Path(tmpdir) / "test_2.db"
        db_path_3 = Path(tmpdir) / "test_3.db"
        
        init_db_real(db_path_1)
        init_db_real(db_path_2)
        init_db_real(db_path_3)
        
        success &= run_test_case("test_save_and_load", test_save_and_load, db_path_1)
        success &= run_test_case("test_list_runs", test_list_runs, db_path_2)
        success &= run_test_case("test_delete_run", test_delete_run, db_path_3)
        
        import gc
        gc.collect()

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        success &= run_test_case("test_init_db_creates_file", test_init_db_creates_file, TempPath(tmpdir))
        gc.collect()

    # 5. Executar testes E2E e do Report Endpoint
    with TestClient(app) as client:
        success &= run_test_case("test_upload_completo (E2E)", test_upload_completo, client, excel_dir, pdf_path)
        success &= run_test_case("test_upload_so_pdf (E2E)", test_upload_so_pdf, client, pdf_path)
        success &= run_test_case("test_frontend_acessivel", test_frontend_acessivel, client)
        success &= run_test_case("test_report_endpoint", test_report_endpoint, client, excel_dir, pdf_path)

    print("----------------------------------------------------------")
    if success:
        print("ALL TESTS PASSED SUCCESSFULLY! [OK]")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED! [FAIL]")
        sys.exit(1)


if __name__ == "__main__":
    main()
