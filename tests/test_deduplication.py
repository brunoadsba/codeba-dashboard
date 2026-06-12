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
        """Duas linhas com mesma Data/Peso Bruto/Tara mas placas diferentes — mantém a primeira."""
        df = pd.DataFrame({
            'Placa': ['RDP6D75', 'RDP6075'],
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
        """Três registros idênticos em Data/Peso — mantém apenas o primeiro."""
        df = pd.DataFrame({
            'Placa': ['AAA1111', 'BBB2222', 'CCC3333'],
            'Data': pd.to_datetime(['2026-06-05'] * 3),
            'Peso Bruto': [50000.0, 50000.0, 50000.0],
            'Tara': [16000.0, 16000.0, 16000.0],
        })
        result, removed = _deduplicate_weighings(df)
        assert removed == 2
        assert len(result) == 1
        assert result.iloc[0]['Placa'] == 'AAA1111'

    def test_sev_column_logged_when_present(self):
        """Se a coluna SEV existir, a função não deve falhar."""
        df = pd.DataFrame({
            'Placa': ['RDP6D75', 'RDP6075'],
            'Data': pd.to_datetime(['2026-06-01', '2026-06-01']),
            'Peso Bruto': [45000.0, 45000.0],
            'Tara': [15000.0, 15000.0],
            'SEV': ['44354', '44358'],
        })
        result, removed = _deduplicate_weighings(df)
        assert removed == 1
        assert len(result) == 1

    def test_mixed_duplicates_and_unique(self):
        """Mistura de registros únicos e duplicados — remove apenas os duplicados."""
        df = pd.DataFrame({
            'Placa': ['AAA1111', 'AAA1112', 'BBB2222', 'CCC3333'],
            'Data': pd.to_datetime(['2026-06-01', '2026-06-01', '2026-06-01', '2026-06-02']),
            'Peso Bruto': [45000.0, 45000.0, 38000.0, 45000.0],
            'Tara': [15000.0, 15000.0, 14000.0, 15000.0],
        })
        result, removed = _deduplicate_weighings(df)
        assert removed == 1
        assert len(result) == 3
        # O primeiro AAA1111 é mantido, o AAA1112 (mesmo peso/data) é removido
        assert result.iloc[0]['Placa'] == 'AAA1111'
        # BBB2222 tem peso diferente, mantido
        assert 'BBB2222' in result['Placa'].values
        # CCC3333 tem data diferente, mantido
        assert 'CCC3333' in result['Placa'].values
