"""Repositorio — CRUD para o banco SQLite do WeatherEdge v2."""
import sqlite3
from typing import Optional


class Repositorio:
    def __init__(self, caminho_db: str) -> None:
        self.caminho_db = caminho_db

    def _conectar(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.caminho_db)
        conn.row_factory = sqlite3.Row
        return conn

    # --- Leituras ---

    def salvar_leitura(self, cidade: str, data_alvo: str, timestamp: int,
                       temperatura: float, hora_utc: str, hora_local: str, unidade: str) -> None:
        conn = self._conectar()
        conn.execute(
            "INSERT INTO leituras (cidade, data_alvo, timestamp, temperatura, hora_utc, hora_local, unidade) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cidade, data_alvo, timestamp, temperatura, hora_utc, hora_local, unidade),
        )
        conn.commit()
        conn.close()

    def buscar_leituras(self, cidade: str, data_alvo: str) -> list[dict]:
        conn = self._conectar()
        cursor = conn.execute(
            "SELECT * FROM leituras WHERE cidade = ? AND data_alvo = ? ORDER BY timestamp",
            (cidade, data_alvo),
        )
        resultado = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return resultado

    def limpar_leituras(self, cidade: str, data_alvo: str) -> None:
        conn = self._conectar()
        conn.execute("DELETE FROM leituras WHERE cidade = ? AND data_alvo = ?", (cidade, data_alvo))
        conn.commit()
        conn.close()

    # --- Odds ---

    def salvar_odds(self, cidade: str, data_alvo: str, faixa: str,
                    preco_compra: float, volume: float, coletado_em: str) -> None:
        conn = self._conectar()
        conn.execute(
            "INSERT INTO odds_polymarket (cidade, data_alvo, faixa, preco_compra, volume, coletado_em) VALUES (?, ?, ?, ?, ?, ?)",
            (cidade, data_alvo, faixa, preco_compra, volume, coletado_em),
        )
        conn.commit()
        conn.close()

    def buscar_odds(self, cidade: str, data_alvo: str) -> list[dict]:
        conn = self._conectar()
        cursor = conn.execute(
            "SELECT * FROM odds_polymarket WHERE cidade = ? AND data_alvo = ? ORDER BY coletado_em DESC",
            (cidade, data_alvo),
        )
        resultado = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return resultado

    def buscar_odds_mais_recentes(self, cidade: str, data_alvo: str) -> list[dict]:
        conn = self._conectar()
        cursor = conn.execute(
            """SELECT * FROM odds_polymarket
               WHERE cidade = ? AND data_alvo = ?
               AND coletado_em = (SELECT MAX(coletado_em) FROM odds_polymarket WHERE cidade = ? AND data_alvo = ?)
               ORDER BY preco_compra DESC""",
            (cidade, data_alvo, cidade, data_alvo),
        )
        resultado = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return resultado

    def limpar_odds(self, cidade: str, data_alvo: str) -> None:
        conn = self._conectar()
        conn.execute("DELETE FROM odds_polymarket WHERE cidade = ? AND data_alvo = ?", (cidade, data_alvo))
        conn.commit()
        conn.close()

    # --- Apostas ---

    def registrar_aposta(self, cidade: str, data_alvo: str, faixa: str,
                         tipo: str, odd: float, valor: float, horario_registro: str) -> None:
        conn = self._conectar()
        conn.execute(
            "INSERT INTO apostas (cidade, data_alvo, faixa, tipo, odd, valor, horario_registro) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cidade, data_alvo, faixa, tipo, odd, valor, horario_registro),
        )
        conn.commit()
        conn.close()

    def resolver_aposta(self, aposta_id: int, resultado: str, pnl: float) -> None:
        conn = self._conectar()
        conn.execute("UPDATE apostas SET resultado = ?, pnl = ? WHERE id = ?", (resultado, pnl, aposta_id))
        conn.commit()
        conn.close()

    def buscar_apostas_do_dia(self, data_alvo: str) -> list[dict]:
        conn = self._conectar()
        cursor = conn.execute(
            "SELECT * FROM apostas WHERE data_alvo = ? ORDER BY horario_registro DESC", (data_alvo,),
        )
        resultado = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return resultado

    def buscar_historico_apostas(self, limite: int = 100) -> list[dict]:
        conn = self._conectar()
        cursor = conn.execute(
            "SELECT * FROM apostas ORDER BY data_alvo DESC, horario_registro DESC LIMIT ?", (limite,),
        )
        resultado = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return resultado

    def calcular_metricas(self) -> dict:
        conn = self._conectar()
        cursor = conn.execute(
            """SELECT
                COUNT(*) as total_apostas,
                SUM(CASE WHEN resultado = 'ganhou' THEN 1 ELSE 0 END) as ganhou,
                SUM(CASE WHEN resultado = 'perdeu' THEN 1 ELSE 0 END) as perdeu,
                SUM(CASE WHEN resultado = 'aguardando' THEN 1 ELSE 0 END) as aguardando,
                COALESCE(SUM(pnl), 0) as pnl_total,
                COALESCE(SUM(valor), 0) as total_investido
            FROM apostas"""
        )
        row = dict(cursor.fetchone())
        conn.close()
        # Quando nao tem apostas, SUM retorna None — tratar como 0
        row["ganhou"] = row["ganhou"] or 0
        row["perdeu"] = row["perdeu"] or 0
        row["aguardando"] = row["aguardando"] or 0
        row["pnl_total"] = row["pnl_total"] or 0
        row["total_investido"] = row["total_investido"] or 0
        total_resolvidas = row["ganhou"] + row["perdeu"]
        row["win_rate"] = (row["ganhou"] / total_resolvidas * 100) if total_resolvidas > 0 else 0
        row["roi"] = (row["pnl_total"] / row["total_investido"] * 100) if row["total_investido"] > 0 else 0
        return row
