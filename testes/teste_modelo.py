"""Testes do modulo modelo — distribuicao, pesos e confianca."""
from datetime import datetime, timezone

import pytest

from coletores.base import Previsao
from modelo.distribuicao import calcular_distribuicao, DistribuicaoFaixa
from modelo.pesos import media_ponderada, PESOS_PADRAO
from modelo.confianca import calcular_confianca


def _criar_previsoes() -> list[Previsao]:
    """Helper — cria previsoes de exemplo (London 7 abr)."""
    agora = datetime.now(timezone.utc)
    return [
        Previsao("ecmwf", 20.1, 9.0, agora),
        Previsao("gfs", 19.2, 8.1, agora),
        Previsao("openweathermap", 19.5, 8.5, agora),
        Previsao("wunderground", 20.0, 8.0, agora),
        Previsao("accuweather", 19.0, 7.8, agora),
        Previsao("visual_crossing", 19.8, 8.3, agora),
    ]


class TestMediaPonderada:
    def test_media_com_todos_os_pesos(self) -> None:
        previsoes = _criar_previsoes()
        media = media_ponderada(previsoes, PESOS_PADRAO)
        assert 19.5 <= media <= 19.8

    def test_media_com_fonte_faltando(self) -> None:
        previsoes = _criar_previsoes()[:2]
        media = media_ponderada(previsoes, PESOS_PADRAO)
        assert 19.0 <= media <= 20.5

    def test_media_com_uma_fonte_so(self) -> None:
        previsoes = [Previsao("ecmwf", 20.1, 9.0, datetime.now(timezone.utc))]
        media = media_ponderada(previsoes, PESOS_PADRAO)
        assert media == 20.1


class TestConfianca:
    def test_confianca_alta_fontes_concordam(self) -> None:
        previsoes = _criar_previsoes()
        conf = calcular_confianca(previsoes, horas_desde_coleta=3.0)
        assert conf == "ALTA"

    def test_confianca_baixa_fontes_discordam(self) -> None:
        agora = datetime.now(timezone.utc)
        previsoes = [
            Previsao("ecmwf", 25.0, 15.0, agora),
            Previsao("gfs", 18.0, 8.0, agora),
        ]
        conf = calcular_confianca(previsoes, horas_desde_coleta=3.0)
        assert conf == "BAIXA"

    def test_confianca_media_dados_velhos(self) -> None:
        previsoes = _criar_previsoes()
        conf = calcular_confianca(previsoes, horas_desde_coleta=10.0)
        assert conf == "MEDIA"


class TestDistribuicao:
    def test_distribuicao_soma_100_porcento(self) -> None:
        previsoes = _criar_previsoes()
        dist = calcular_distribuicao(previsoes, PESOS_PADRAO, horizonte="D-1")
        soma = sum(f.probabilidade for f in dist)
        assert abs(soma - 1.0) < 0.01

    def test_distribuicao_faixa_mais_provavel(self) -> None:
        previsoes = _criar_previsoes()
        dist = calcular_distribuicao(previsoes, PESOS_PADRAO, horizonte="D-1")
        mais_provavel = max(dist, key=lambda f: f.probabilidade)
        assert mais_provavel.grau in [19, 20]

    def test_distribuicao_d2_mais_espalhada_que_d1(self) -> None:
        previsoes = _criar_previsoes()
        dist_d1 = calcular_distribuicao(previsoes, PESOS_PADRAO, horizonte="D-1")
        dist_d2 = calcular_distribuicao(previsoes, PESOS_PADRAO, horizonte="D-2")
        max_d1 = max(f.probabilidade for f in dist_d1)
        max_d2 = max(f.probabilidade for f in dist_d2)
        assert max_d2 < max_d1

    def test_distribuicao_retorna_faixas_com_metadados(self) -> None:
        previsoes = _criar_previsoes()
        dist = calcular_distribuicao(previsoes, PESOS_PADRAO, horizonte="D-1")
        assert len(dist) > 0
        assert all(isinstance(f, DistribuicaoFaixa) for f in dist)
        assert all(f.media > 0 for f in dist)
        assert all(f.desvio_padrao > 0 for f in dist)
        assert all(f.confianca in ["ALTA", "MEDIA", "BAIXA"] for f in dist)
