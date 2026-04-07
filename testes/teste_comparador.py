"""Testes do modulo comparador — edge, recomendador e simulador."""
import pytest

from modelo.distribuicao import DistribuicaoFaixa
from comparador.edge import calcular_edge, AnaliseEdge
from comparador.recomendador import classificar_estrelas, gerar_recomendacoes
from comparador.simulador import simular_estrategia


def _criar_distribuicao() -> list[DistribuicaoFaixa]:
    return [
        DistribuicaoFaixa(grau=17, probabilidade=0.02, media=19.6, desvio_padrao=0.5, confianca="ALTA"),
        DistribuicaoFaixa(grau=18, probabilidade=0.12, media=19.6, desvio_padrao=0.5, confianca="ALTA"),
        DistribuicaoFaixa(grau=19, probabilidade=0.28, media=19.6, desvio_padrao=0.5, confianca="ALTA"),
        DistribuicaoFaixa(grau=20, probabilidade=0.33, media=19.6, desvio_padrao=0.5, confianca="ALTA"),
        DistribuicaoFaixa(grau=21, probabilidade=0.18, media=19.6, desvio_padrao=0.5, confianca="ALTA"),
        DistribuicaoFaixa(grau=22, probabilidade=0.07, media=19.6, desvio_padrao=0.5, confianca="ALTA"),
    ]


def _criar_odds() -> list[dict]:
    return [
        {"faixa_grau": 17, "preco_compra": 0.112, "volume": 19538},
        {"faixa_grau": 18, "preco_compra": 0.40, "volume": 15386},
        {"faixa_grau": 19, "preco_compra": 0.25, "volume": 13182},
        {"faixa_grau": 20, "preco_compra": 0.24, "volume": 12672},
        {"faixa_grau": 21, "preco_compra": 0.05, "volume": 17143},
        {"faixa_grau": 22, "preco_compra": 0.011, "volume": 10257},
    ]


class TestCalcularEdge:
    def test_calcula_edge_corretamente(self) -> None:
        dist = _criar_distribuicao()
        odds = _criar_odds()
        analises = calcular_edge(dist, odds)

        a20 = next(a for a in analises if a.faixa_grau == 20)
        assert abs(a20.edge - 9.0) < 1.0

        a18 = next(a for a in analises if a.faixa_grau == 18)
        assert a18.edge < 0

    def test_edge_positivo_e_negativo(self) -> None:
        dist = _criar_distribuicao()
        odds = _criar_odds()
        analises = calcular_edge(dist, odds)

        tem_positivo = any(a.edge > 0 for a in analises)
        tem_negativo = any(a.edge < 0 for a in analises)
        assert tem_positivo
        assert tem_negativo


class TestClassificarEstrelas:
    def test_5_estrelas(self) -> None:
        estrelas = classificar_estrelas(edge=16.0, confianca="ALTA", retorno=6.0)
        assert estrelas == 5

    def test_4_estrelas(self) -> None:
        estrelas = classificar_estrelas(edge=11.0, confianca="ALTA", retorno=4.0)
        assert estrelas == 4

    def test_1_estrela_edge_baixo(self) -> None:
        estrelas = classificar_estrelas(edge=3.0, confianca="ALTA", retorno=2.0)
        assert estrelas == 1

    def test_1_estrela_confianca_baixa(self) -> None:
        estrelas = classificar_estrelas(edge=15.0, confianca="BAIXA", retorno=5.0)
        assert estrelas <= 2


class TestRecomendacoes:
    def test_gera_recomendacoes_d1(self) -> None:
        dist = _criar_distribuicao()
        odds = _criar_odds()
        analises = calcular_edge(dist, odds)
        recs = gerar_recomendacoes(analises, horizonte="D-1")

        assert len(recs) > 0
        assert all(r.edge >= 5 for r in recs)

    def test_d2_exige_mais_edge(self) -> None:
        dist = _criar_distribuicao()
        odds = _criar_odds()
        analises = calcular_edge(dist, odds)
        recs_d1 = gerar_recomendacoes(analises, horizonte="D-1")
        recs_d2 = gerar_recomendacoes(analises, horizonte="D-2")

        assert len(recs_d2) <= len(recs_d1)


class TestSimulador:
    def test_simular_concentrada(self) -> None:
        resultado = simular_estrategia(
            faixas=[20],
            precos=[0.24],
            probabilidades=[0.33],
            valor_total=10.0,
            estrategia="concentrada",
        )
        assert resultado["custo_total"] == 10.0
        assert resultado["lucro_se_acerta_20"] > 0
        assert resultado["valor_esperado"] > 0

    def test_simular_espalhada(self) -> None:
        resultado = simular_estrategia(
            faixas=[19, 20, 21],
            precos=[0.25, 0.24, 0.05],
            probabilidades=[0.28, 0.33, 0.18],
            valor_total=10.0,
            estrategia="espalhada",
        )
        assert resultado["custo_total"] <= 10.0
        assert "lucro_se_acerta_19" in resultado
        assert "lucro_se_acerta_20" in resultado
        assert "lucro_se_acerta_21" in resultado
