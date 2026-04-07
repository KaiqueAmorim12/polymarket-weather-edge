"""Testes do orquestrador v2."""
from datetime import date
import pytest
from main import calcular_data_hoje


class TestCalcularDataHoje:
    def test_retorna_data_iso(self) -> None:
        assert calcular_data_hoje(date(2026, 4, 7)) == "2026-04-07"

    def test_sem_argumento_usa_hoje(self) -> None:
        assert len(calcular_data_hoje()) == 10
