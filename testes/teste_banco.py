"""Testes do modulo banco — schema e repositorio."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from banco.modelos import criar_tabelas
from banco.repositorio import Repositorio


@pytest.fixture
def db_temp(tmp_path: Path) -> Path:
    """Cria banco temporario pra testes."""
    caminho = tmp_path / "teste.db"
    criar_tabelas(str(caminho))
    return caminho


@pytest.fixture
def repo(db_temp: Path) -> Repositorio:
    """Repositorio conectado ao banco temporario."""
    return Repositorio(str(db_temp))


class TestCriarTabelas:
    def test_cria_todas_as_tabelas(self, db_temp: Path) -> None:
        conn = sqlite3.connect(str(db_temp))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        tabelas = [row[0] for row in cursor.fetchall()]
        conn.close()

        esperadas = [
            "analises",
            "distribuicoes",
            "odds_polymarket",
            "performance",
            "previsoes",
            "resultados",
        ]
        assert tabelas == esperadas


class TestRepositorioPrevisoes:
    def test_salvar_e_buscar_previsao(self, repo: Repositorio) -> None:
        agora = datetime.now(timezone.utc).isoformat()
        repo.salvar_previsao(
            cidade="London",
            data_alvo="2026-04-07",
            horizonte="D-1",
            fonte="ecmwf",
            temperatura_max=20.1,
            temperatura_min=9.0,
            coletado_em=agora,
        )

        previsoes = repo.buscar_previsoes("London", "2026-04-07")
        assert len(previsoes) == 1
        assert previsoes[0]["fonte"] == "ecmwf"
        assert previsoes[0]["temperatura_max"] == 20.1

    def test_buscar_previsoes_vazias(self, repo: Repositorio) -> None:
        previsoes = repo.buscar_previsoes("London", "2026-04-07")
        assert previsoes == []


class TestRepositorioDistribuicoes:
    def test_salvar_e_buscar_distribuicao(self, repo: Repositorio) -> None:
        repo.salvar_distribuicao(
            cidade="London",
            data_alvo="2026-04-07",
            horizonte="D-1",
            faixa_grau=20,
            probabilidade=0.33,
            media=19.6,
            desvio_padrao=0.42,
            confianca="ALTA",
        )

        dist = repo.buscar_distribuicoes("London", "2026-04-07", "D-1")
        assert len(dist) == 1
        assert dist[0]["faixa_grau"] == 20
        assert dist[0]["probabilidade"] == 0.33


class TestRepositorioOdds:
    def test_salvar_e_buscar_odds(self, repo: Repositorio) -> None:
        agora = datetime.now(timezone.utc).isoformat()
        repo.salvar_odds(
            cidade="London",
            data_alvo="2026-04-07",
            faixa_grau=20,
            probabilidade_mercado=0.22,
            preco_compra=0.24,
            preco_venda=0.19,
            volume=12672.0,
            coletado_em=agora,
        )

        odds = repo.buscar_odds("London", "2026-04-07")
        assert len(odds) == 1
        assert odds[0]["preco_compra"] == 0.24


class TestRepositorioAnalises:
    def test_salvar_e_buscar_analise(self, repo: Repositorio) -> None:
        repo.salvar_analise(
            cidade="London",
            data_alvo="2026-04-07",
            horizonte="D-1",
            faixa_grau=20,
            prob_modelo=0.33,
            prob_mercado=0.22,
            edge=11.0,
            recomendacao="COMPRAR",
            estrelas=4,
        )

        analises = repo.buscar_analises("London", "2026-04-07", "D-1")
        assert len(analises) == 1
        assert analises[0]["edge"] == 11.0
        assert analises[0]["estrelas"] == 4


class TestRepositorioResultados:
    def test_salvar_e_buscar_resultado(self, repo: Repositorio) -> None:
        repo.salvar_resultado(
            cidade="London",
            data_alvo="2026-04-07",
            temperatura_real=20.0,
            faixa_vencedora=20,
            fonte_resolucao="wunderground_EGLC",
        )

        resultado = repo.buscar_resultado("London", "2026-04-07")
        assert resultado is not None
        assert resultado["temperatura_real"] == 20.0
        assert resultado["faixa_vencedora"] == 20
