import sys
import os
import shutil
import tempfile
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from src.services.post_processing import detect_plate_typos
from src.services.pdf_parser import process_pdf_file


def test_detect_plate_typos_with_mixed_dates():
    print("Running test_detect_plate_typos_with_mixed_dates...", end="")
    # fp['Data'] comes from Excel (date only)
    # fe['Data'] comes from PDF (date and time)
    divergencias = [
        {
            'Placa': 'RCU3J44',
            'Data': '13/05/2026',
            'Status': 'Falta no PDF',
            'Peso Bruto': 77600.0,
            'Tara': 28260.0,
            'Produto': 'ÓXIDO DE MAGNÉSIO',
            'Cliente': 'MAGNESITA'
        },
        {
            'Placa': 'RCU3J45',
            'Data': '13/05/2026 14:30',
            'Status': 'Falta no Excel',
            'Peso Bruto': 77600.0,
            'Tara': 28260.0,
            'SEV': '663928'
        }
    ]
    
    res = detect_plate_typos(divergencias)
    
    # It should have matched them into an 'Erro de Placa'
    assert len(res) == 1
    assert res[0]['Status'] == 'Erro de Placa'
    assert res[0]['Placa_Excel'] == 'RCU3J44'
    assert res[0]['Placa_PDF'] == 'RCU3J45'
    # It should carry the full PDF datetime (with hour)
    assert res[0]['Data'] == '13/05/2026 14:30'
    print(" [OK]")


def test_detect_plate_typos_with_missing_letter():
    print("Running test_detect_plate_typos_with_missing_letter...", end="")
    # RP5E21 has length 6 (typo), RPO5E21 has length 7 (correct)
    divergencias = [
        {
            'Placa': 'RP5E21',
            'Data': '02/06/2026',
            'Status': 'Falta no PDF',
            'Peso Bruto': 59120.0,
            'Tara': 19840.0,
            'Produto': 'ÓXIDO DE MAGNÉSIO',
            'Cliente': 'MAGNESITA'
        },
        {
            'Placa': 'RPO5E21',
            'Data': '02/06/2026 15:45',
            'Status': 'Falta no Excel',
            'Peso Bruto': 59120.0,
            'Tara': 19840.0,
            'SEV': '663920'
        }
    ]
    
    res = detect_plate_typos(divergencias)
    
    # It should match because Levenshtein distance is 1 (insertion of 'O')
    assert len(res) == 1
    assert res[0]['Status'] == 'Erro de Placa'
    assert res[0]['Placa_Excel'] == 'RP5E21'
    assert res[0]['Placa_PDF'] == 'RPO5E21'
    assert res[0]['Data'] == '02/06/2026 15:45'
    print(" [OK]")


def test_pdf_parser_handles_7015_and_7714():
    print("Running test_pdf_parser_handles_7015...", end="")
    pdf_path = project_root / "data" / "Relatório de Pesquisa - 7015.pdf"
    if pdf_path.exists():
        df = process_pdf_file(str(pdf_path))
        assert not df.empty
        assert 'Placa' in df.columns
        assert 'Data' in df.columns
        assert 'Peso Bruto' in df.columns
        assert 'Tara' in df.columns
        assert 'SEV' in df.columns
        print(" [OK]")
    else:
        print(" [SKIPPED (PDF missing)]")


def main():
    print("==========================================================")
    print("CODEBA AUDITORIA - STANDALONE UNIT TESTS")
    print("==========================================================")
    
    success = True
    try:
        test_detect_plate_typos_with_mixed_dates()
    except Exception as e:
        print(" [FAIL]")
        import traceback
        traceback.print_exc()
        success = False

    try:
        test_detect_plate_typos_with_missing_letter()
    except Exception as e:
        print(" [FAIL]")
        import traceback
        traceback.print_exc()
        success = False

    try:
        test_pdf_parser_handles_7015_and_7714()
    except Exception as e:
        print(" [FAIL]")
        import traceback
        traceback.print_exc()
        success = False

    print("----------------------------------------------------------")
    if success:
        print("ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == '__main__':
    main()
