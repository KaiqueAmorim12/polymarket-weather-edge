"""Testes do modulo coletores — base e Open-Meteo."""
from datetime import datetime, timezone

import pytest

from coletores.base import Previsao, ResultadoColeta
from coletores.open_meteo import OpenMeteoColetor


class TestPrevisao:
    def test_criar_previsao(self) -> None:
        p = Previsao(
            fonte="ecmwf",
            temperatura_max=20.1,
            temperatura_min=9.0,
            coletado_em=datetime.now(timezone.utc),
        )
        assert p.fonte == "ecmwf"
        assert p.temperatura_max == 20.1

    def test_previsao_valida(self) -> None:
        p = Previsao(
            fonte="gfs",
            temperatura_max=20.0,
            temperatura_min=10.0,
            coletado_em=datetime.now(timezone.utc),
        )
        assert p.valida()

    def test_previsao_invalida_max_menor_que_min(self) -> None:
        p = Previsao(
            fonte="gfs",
            temperatura_max=5.0,
            temperatura_min=10.0,
            coletado_em=datetime.now(timezone.utc),
        )
        assert not p.valida()


class TestResultadoColeta:
    def test_resultado_com_previsoes(self) -> None:
        p1 = Previsao("ecmwf", 20.1, 9.0, datetime.now(timezone.utc))
        p2 = Previsao("gfs", 19.2, 8.1, datetime.now(timezone.utc))
        resultado = ResultadoColeta(
            cidade="London",
            data_alvo="2026-04-07",
            previsoes=[p1, p2],
            erros=[],
        )
        assert len(resultado.previsoes) == 2
        assert resultado.sucesso()

    def test_resultado_com_erros_parciais(self) -> None:
        p1 = Previsao("ecmwf", 20.1, 9.0, datetime.now(timezone.utc))
        resultado = ResultadoColeta(
            cidade="London",
            data_alvo="2026-04-07",
            previsoes=[p1],
            erros=["gfs: timeout"],
        )
        assert resultado.sucesso()

    def test_resultado_sem_previsoes(self) -> None:
        resultado = ResultadoColeta(
            cidade="London",
            data_alvo="2026-04-07",
            previsoes=[],
            erros=["tudo falhou"],
        )
        assert not resultado.sucesso()


class TestOpenMeteoColetor:
    def test_parsear_resposta(self) -> None:
        resposta_mock = {
            "daily": {
                "time": ["2026-04-07"],
                "temperature_2m_max": [20.1],
                "temperature_2m_min": [9.0],
            }
        }

        coletor = OpenMeteoColetor()
        previsoes = coletor._parsear_resposta(resposta_mock, "2026-04-07")
        assert len(previsoes) >= 1
        assert previsoes[0].temperatura_max == 20.1

    def test_parsear_resposta_multi_modelo(self) -> None:
        resposta_ecmwf = {
            "daily": {
                "time": ["2026-04-07"],
                "temperature_2m_max": [20.1],
                "temperature_2m_min": [9.0],
            }
        }
        resposta_gfs = {
            "daily": {
                "time": ["2026-04-07"],
                "temperature_2m_max": [19.2],
                "temperature_2m_min": [8.1],
            }
        }

        coletor = OpenMeteoColetor()
        prev_ecmwf = coletor._parsear_resposta(resposta_ecmwf, "2026-04-07", fonte="ecmwf")
        prev_gfs = coletor._parsear_resposta(resposta_gfs, "2026-04-07", fonte="gfs")

        assert prev_ecmwf[0].fonte == "ecmwf"
        assert prev_ecmwf[0].temperatura_max == 20.1
        assert prev_gfs[0].fonte == "gfs"
        assert prev_gfs[0].temperatura_max == 19.2
