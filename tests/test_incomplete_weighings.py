import pandas as pd
from src.services.reconciliation import reconcile_data

def test_reconciliation_reclassifies_incomplete_weighing():
    # Excel has one complete weighing
    df_ex = pd.DataFrame({
        'Placa': ['QTU3F78'],
        'Data': pd.to_datetime(['2026-06-17 10:42:00']),
        'Peso Bruto': [58060.0],
        'Tara': [20400.0],
        'Produto': ['LÍTIO']
    })

    # PDF has one complete weighing and one incomplete weighing (Tara = 0)
    df_pdf = pd.DataFrame({
        'Placa': ['QTU3F78', 'QTU3F78'],
        'Data': pd.to_datetime(['2026-06-17 10:42:00', '2026-06-17 17:55:00']),
        'Peso Bruto': [58060.0, 58100.0],
        'Tara': [20400.0, 0.0],
        'SEV': ['664119', '664153'],
        'Tipo Carga': ['LÍTIO', 'LÍTIO']
    })

    result = reconcile_data(df_ex, df_pdf)

    # The first complete weighing should match and be in ok_list
    assert len(result['ok']) == 1
    assert result['ok'][0]['SEV'] == '664119'

    # The second incomplete weighing should be separated into notas_informativas
    assert len(result['divergencias']) == 0
    assert len(result['notas_informativas']) == 1
    
    incompleta = result['notas_informativas'][0]
    assert incompleta['SEV'] == '664153'
    assert incompleta['Status'] == 'Pesagem Incompleta'
    assert incompleta['Tara'] == 0

    # Resumo count checks
    assert result['resumo']['ok'] == 1
    assert result['resumo']['divergencias'] == 0
    assert result['resumo']['incompletas'] == 1
    assert result['resumo']['total_processado'] == 2


def test_reconciliation_keeps_incomplete_weighing_as_divergence_when_no_ok_trip():
    # Excel has no weighings for this plate
    df_ex = pd.DataFrame(columns=['Placa', 'Data', 'Peso Bruto', 'Tara', 'Produto'])

    # PDF has only an incomplete weighing
    df_pdf = pd.DataFrame({
        'Placa': ['QTU3F78'],
        'Data': pd.to_datetime(['2026-06-17 17:55:00']),
        'Peso Bruto': [58100.0],
        'Tara': [0.0],
        'SEV': ['664153'],
        'Tipo Carga': ['LÍTIO']
    })

    result = reconcile_data(df_ex, df_pdf)

    # Should remain in divergencias because there is no OK voyage in the day
    assert len(result['ok']) == 0
    assert len(result['divergencias']) == 1
    assert len(result['notas_informativas']) == 0
    
    div = result['divergencias'][0]
    assert div['SEV'] == '664153'
    assert div['Status'] == 'Falta no Excel'
