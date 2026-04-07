"""Testes do banco v2 — leituras hora a hora e apostas."""
import sqlite3
from pathlib import Path

import pytest

from banco.modelos import criar_tabelas
from banco.repositorio import Repositorio


@pytest.fixture
def db_temp(tmp_path: Path) -> Path:
    caminho = tmp_path / "teste.db"
    criar_tabelas(str(caminho))
    return caminho


@pytest.fixture
def repo(db_temp: Path) -> Repositorio:
    return Repositorio(str(db_temp))


class TestCriarTabelas:
    def test_cria_tabelas_v2(self, db_temp: Path) -> None:
        conn = sqlite3.connect(str(db_temp))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        tabelas = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert "leituras" in tabelas
        assert "apostas" in tabelas
        assert "odds_polymarket" in tabelas


class TestLeituras:
    def test_salvar_e_buscar_leituras(self, repo: Repositorio) -> None:
        repo.salvar_leitura(
            cidade="London", data_alvo="2026-04-07", timestamp=1775480400,
            temperatura=16.0, hora_utc="14:20", hora_local="15:20", unidade="C",
        )
        leituras = repo.buscar_leituras("London", "2026-04-07")
        assert len(leituras) == 1
        assert leituras[0]["temperatura"] == 16.0
        assert leituras[0]["hora_local"] == "15:20"

    def test_limpar_leituras(self, repo: Repositorio) -> None:
        repo.salvar_leitura("London", "2026-04-07", 1, 10.0, "06:00", "07:00", "C")
        repo.salvar_leitura("London", "2026-04-07", 2, 15.0, "10:00", "11:00", "C")
        repo.limpar_leituras("London", "2026-04-07")
        assert repo.buscar_leituras("London", "2026-04-07") == []


class TestApostas:
    def test_registrar_aposta(self, repo: Repositorio) -> None:
        repo.registrar_aposta(
            cidade="London", data_alvo="2026-04-07", faixa="23°C",
            tipo="YES", odd=0.24, valor=5.0, horario_registro="2026-04-07 14:20",
        )
        apostas = repo.buscar_apostas_do_dia("2026-04-07")
        assert len(apostas) == 1
        assert apostas[0]["cidade"] == "London"
        assert apostas[0]["resultado"] == "aguardando"

    def test_resolver_aposta(self, repo: Repositorio) -> None:
        repo.registrar_aposta("London", "2026-04-07", "23°C", "YES", 0.24, 5.0, "14:20")
        apostas = repo.buscar_apostas_do_dia("2026-04-07")
        repo.resolver_aposta(apostas[0]["id"], resultado="ganhou", pnl=3.83)
        apostas = repo.buscar_apostas_do_dia("2026-04-07")
        assert apostas[0]["resultado"] == "ganhou"
        assert apostas[0]["pnl"] == 3.83

    def test_calcular_metricas(self, repo: Repositorio) -> None:
        repo.registrar_aposta("London", "2026-04-06", "20°C", "YES", 0.30, 5.0, "14:00")
        repo.registrar_aposta("Moscow", "2026-04-06", "4°C", "YES", 0.40, 3.0, "10:00")
        apostas = repo.buscar_historico_apostas()
        repo.resolver_aposta(apostas[0]["id"], resultado="ganhou", pnl=3.50)
        repo.resolver_aposta(apostas[1]["id"], resultado="perdeu", pnl=-3.00)
        metricas = repo.calcular_metricas()
        assert metricas["total_apostas"] == 2
        assert metricas["ganhou"] == 1
        assert metricas["win_rate"] == 50.0
        assert metricas["pnl_total"] == 0.50
