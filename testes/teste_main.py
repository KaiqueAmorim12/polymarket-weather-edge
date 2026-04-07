"""Testes do orquestrador principal."""
from datetime import date

import pytest

from main import calcular_datas_alvo


class TestCalcularDatasAlvo:
    def test_retorna_d1_e_d2(self) -> None:
        hoje = date(2026, 4, 6)
        d1, d2 = calcular_datas_alvo(hoje)
        assert d1 == "2026-04-07"
        assert d2 == "2026-04-08"

    def test_virada_de_mes(self) -> None:
        hoje = date(2026, 4, 30)
        d1, d2 = calcular_datas_alvo(hoje)
        assert d1 == "2026-05-01"
        assert d2 == "2026-05-02"
