"""
Testes unitários para a função _deduplicate_weighings do pdf_parser.
"""
import pandas as pd
import pytest

from src.services.pdf_parser import _deduplicate_weighings


class TestDeduplicateWeighings:
    """Testes para a desduplicação de pesagens do OpenPort."""

    def test_no_duplicates_returns_unchanged(self):
        """DataFrame sem duplicatas deve retornar inalterado."""
        df = pd.DataFrame({
            'Placa': ['ABC1234', 'XYZ5678'],
            'Data': pd.to_datetime(['2026-06-01', '2026-06-01']),
            'Peso Bruto': [45000.0, 38000.0],
            'Tara': [15000.0, 14000.0],
        })
        result, removed = _deduplicate_weighings(df)
        assert removed == 0
        assert len(result) == 2

    def test_exact_duplicate_keeps_first(self):
        """Duas linhas idênticas em Placa/Data/Peso Bruto/Tara — mantém a primeira."""
        df = pd.DataFrame({
            'Placa': ['RDP6D75', 'RDP6D75'],
            'Data': pd.to_datetime(['2026-06-01', '2026-06-01']),
            'Peso Bruto': [45000.0, 45000.0],
            'Tara': [15000.0, 15000.0],
        })
        result, removed = _deduplicate_weighings(df)
        assert removed == 1
        assert len(result) == 1
        assert result.iloc[0]['Placa'] == 'RDP6D75'

    def test_different_weights_keeps_both(self):
        """Duas linhas com mesma Data mas pesos diferentes — mantém ambas."""
        df = pd.DataFrame({
            'Placa': ['ABC1234', 'ABC1234'],
            'Data': pd.to_datetime(['2026-06-01', '2026-06-01']),
            'Peso Bruto': [45000.0, 46000.0],
            'Tara': [15000.0, 15000.0],
        })
        result, removed = _deduplicate_weighings(df)
        assert removed == 0
        assert len(result) == 2

    def test_different_dates_keeps_both(self):
        """Mesmos pesos em datas diferentes — mantém ambas (viagens distintas)."""
        df = pd.DataFrame({
            'Placa': ['ABC1234', 'ABC1234'],
            'Data': pd.to_datetime(['2026-06-01', '2026-06-02']),
            'Peso Bruto': [45000.0, 45000.0],
            'Tara': [15000.0, 15000.0],
        })
        result, removed = _deduplicate_weighings(df)
        assert removed == 0
        assert len(result) == 2

    def test_empty_dataframe_returns_empty(self):
        """DataFrame vazio deve retornar vazio sem erro."""
        df = pd.DataFrame()
        result, removed = _deduplicate_weighings(df)
        assert removed == 0
        assert len(result) == 0

    def test_missing_columns_returns_unchanged(self):
        """DataFrame sem colunas necessárias retorna inalterado."""
        df = pd.DataFrame({'Placa': ['ABC1234'], 'Outro': [123]})
        result, removed = _deduplicate_weighings(df)
        assert removed == 0
        assert len(result) == 1

    def test_multiple_duplicates_same_group(self):
        """Três registros idênticos em Placa/Data/Peso — mantém apenas o primeiro."""
        df = pd.DataFrame({
            'Placa': ['AAA1111', 'AAA1111', 'AAA1111'],
            'Data': pd.to_datetime(['2026-06-05'] * 3),
            'Peso Bruto': [50000.0, 50000.0, 50000.0],
            'Tara': [16000.0, 16000.0, 16000.0],
        })
        result, removed = _deduplicate_weighings(df)
        assert removed == 2
        assert len(result) == 1
        assert result.iloc[0]['Placa'] == 'AAA1111'

    def test_sev_column_logged_when_present(self):
        """Se a coluna SEV existir, a função não deve falhar.
        Duas linhas com mesma Placa/Data/Pesos e mesmo SEV — remove duplicata."""
        df = pd.DataFrame({
            'Placa': ['RDP6D75', 'RDP6D75'],
            'Data': pd.to_datetime(['2026-06-01', '2026-06-01']),
            'Peso Bruto': [45000.0, 45000.0],
            'Tara': [15000.0, 15000.0],
            'SEV': ['44354', '44354'],
        })
        result, removed = _deduplicate_weighings(df)
        assert removed == 1
        assert len(result) == 1

    def test_mixed_duplicates_and_unique(self):
        """Mistura de registros únicos e duplicados — remove apenas os duplicados."""
        df = pd.DataFrame({
            'Placa': ['AAA1111', 'AAA1111', 'BBB2222', 'CCC3333'],
            'Data': pd.to_datetime(['2026-06-01', '2026-06-01', '2026-06-01', '2026-06-02']),
            'Peso Bruto': [45000.0, 45000.0, 38000.0, 45000.0],
            'Tara': [15000.0, 15000.0, 14000.0, 15000.0],
        })
        result, removed = _deduplicate_weighings(df)
        assert removed == 1
        assert len(result) == 3
        # O primeiro AAA1111 é mantido, o segundo AAA1111 (mesma placa/data/peso) é removido
        # BBB2222 tem peso diferente, mantido
        assert 'BBB2222' in result['Placa'].values
        # CCC3333 tem data diferente, mantido
        assert 'CCC3333' in result['Placa'].values


from src.services.pdf_parser import _remove_incomplete_weighings

class TestRemoveIncompleteWeighings:
    """Testes para a remoção de pesagens incompletas (Tara = 0) do OpenPort."""

    def test_incomplete_weighing_removed(self):
        """Pesagem com Tara=0 e outra com Tara>0 no mesmo dia/placa com diferença < 200 kg -> remove a com Tara=0."""
        df = pd.DataFrame({
            'Placa': ['RDP6D75', 'RDP6D75'],
            'Data': pd.to_datetime(['2026-06-01 10:00:00', '2026-06-01 18:00:00']),
            'Peso Bruto': [58060.0, 58100.0],
            'Tara': [20400.0, 0.0],
            'SEV': ['664119', '664153']
        })
        result, removed = _remove_incomplete_weighings(df)
        assert removed == 1
        assert len(result) == 1
        assert result.iloc[0]['SEV'] == '664119'
        assert result.iloc[0]['Tara'] == 20400.0

    def test_incomplete_weighing_kept_no_complete(self):
        """Pesagem com Tara=0 mas sem correspondente completa no mesmo dia -> mantida."""
        df = pd.DataFrame({
            'Placa': ['RDP6D75'],
            'Data': pd.to_datetime(['2026-06-01 18:00:00']),
            'Peso Bruto': [58100.0],
            'Tara': [0.0],
            'SEV': ['664153']
        })
        result, removed = _remove_incomplete_weighings(df)
        assert removed == 0
        assert len(result) == 1

    def test_incomplete_weighing_kept_weight_diff_large(self):
        """Pesagem com Tara=0, tem correspondente no dia mas diferença de peso bruto > 200 kg -> mantida."""
        df = pd.DataFrame({
            'Placa': ['RDP6D75', 'RDP6D75'],
            'Data': pd.to_datetime(['2026-06-01 10:00:00', '2026-06-01 18:00:00']),
            'Peso Bruto': [58000.0, 58300.0],  # 300 kg diff
            'Tara': [20400.0, 0.0],
            'SEV': ['664119', '664153']
        })
        result, removed = _remove_incomplete_weighings(df)
        assert removed == 0
        assert len(result) == 2

    def test_incomplete_weighing_kept_different_day(self):
        """Pesagem com Tara=0, tem correspondente completa mas em dia diferente -> mantida."""
        df = pd.DataFrame({
            'Placa': ['RDP6D75', 'RDP6D75'],
            'Data': pd.to_datetime(['2026-06-01 10:00:00', '2026-06-02 18:00:00']),
            'Peso Bruto': [58060.0, 58100.0],
            'Tara': [20400.0, 0.0],
            'SEV': ['664119', '664153']
        })
        result, removed = _remove_incomplete_weighings(df)
        assert removed == 0
        assert len(result) == 2
