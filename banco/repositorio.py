"""Repositorio — CRUD para o banco SQLite do WeatherEdge."""
import sqlite3
from typing import Optional


class Repositorio:
    """Acesso ao banco de dados SQLite."""

    def __init__(self, caminho_db: str) -> None:
        self.caminho_db = caminho_db

    def _conectar(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.caminho_db)
        conn.row_factory = sqlite3.Row
        return conn

    # --- Previsoes ---

    def salvar_previsao(
        self,
        cidade: str,
        data_alvo: str,
        horizonte: str,
        fonte: str,
        temperatura_max: float,
        temperatura_min: float,
        coletado_em: str,
    ) -> None:
        conn = self._conectar()
        conn.execute(
            """INSERT INTO previsoes
               (cidade, data_alvo, horizonte, fonte, temperatura_max, temperatura_min, coletado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (cidade, data_alvo, horizonte, fonte, temperatura_max, temperatura_min, coletado_em),
        )
        conn.commit()
        conn.close()

    def buscar_previsoes(self, cidade: str, data_alvo: str) -> list[dict]:
        conn = self._conectar()
        cursor = conn.execute(
            "SELECT * FROM previsoes WHERE cidade = ? AND data_alvo = ? ORDER BY coletado_em DESC",
            (cidade, data_alvo),
        )
        resultado = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return resultado

    # --- Distribuicoes ---

    def salvar_distribuicao(
        self,
        cidade: str,
        data_alvo: str,
        horizonte: str,
        faixa_grau: int,
        probabilidade: float,
        media: float,
        desvio_padrao: float,
        confianca: str,
    ) -> None:
        conn = self._conectar()
        conn.execute(
            """INSERT INTO distribuicoes
               (cidade, data_alvo, horizonte, faixa_grau, probabilidade, media, desvio_padrao, confianca)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (cidade, data_alvo, horizonte, faixa_grau, probabilidade, media, desvio_padrao, confianca),
        )
        conn.commit()
        conn.close()

    def buscar_distribuicoes(self, cidade: str, data_alvo: str, horizonte: str) -> list[dict]:
        conn = self._conectar()
        cursor = conn.execute(
            """SELECT * FROM distribuicoes
               WHERE cidade = ? AND data_alvo = ? AND horizonte = ?
               ORDER BY faixa_grau""",
            (cidade, data_alvo, horizonte),
        )
        resultado = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return resultado

    # --- Odds Polymarket ---

    def salvar_odds(
        self,
        cidade: str,
        data_alvo: str,
        faixa_grau: int,
        probabilidade_mercado: float,
        preco_compra: float,
        preco_venda: float,
        volume: float,
        coletado_em: str,
    ) -> None:
        conn = self._conectar()
        conn.execute(
            """INSERT INTO odds_polymarket
               (cidade, data_alvo, faixa_grau, probabilidade_mercado, preco_compra, preco_venda, volume, coletado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (cidade, data_alvo, faixa_grau, probabilidade_mercado, preco_compra, preco_venda, volume, coletado_em),
        )
        conn.commit()
        conn.close()

    def buscar_odds(self, cidade: str, data_alvo: str) -> list[dict]:
        conn = self._conectar()
        cursor = conn.execute(
            """SELECT * FROM odds_polymarket
               WHERE cidade = ? AND data_alvo = ?
               ORDER BY faixa_grau""",
            (cidade, data_alvo),
        )
        resultado = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return resultado

    # --- Analises ---

    def salvar_analise(
        self,
        cidade: str,
        data_alvo: str,
        horizonte: str,
        faixa_grau: int,
        prob_modelo: float,
        prob_mercado: float,
        edge: float,
        recomendacao: str,
        estrelas: int,
    ) -> None:
        conn = self._conectar()
        conn.execute(
            """INSERT INTO analises
               (cidade, data_alvo, horizonte, faixa_grau, prob_modelo, prob_mercado, edge, recomendacao, estrelas)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cidade, data_alvo, horizonte, faixa_grau, prob_modelo, prob_mercado, edge, recomendacao, estrelas),
        )
        conn.commit()
        conn.close()

    def buscar_analises(self, cidade: str, data_alvo: str, horizonte: str) -> list[dict]:
        conn = self._conectar()
        cursor = conn.execute(
            """SELECT * FROM analises
               WHERE cidade = ? AND data_alvo = ? AND horizonte = ?
               ORDER BY edge DESC""",
            (cidade, data_alvo, horizonte),
        )
        resultado = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return resultado

    def buscar_todas_analises_do_dia(self, data_alvo: str) -> list[dict]:
        conn = self._conectar()
        cursor = conn.execute(
            "SELECT * FROM analises WHERE data_alvo = ? ORDER BY estrelas DESC, edge DESC",
            (data_alvo,),
        )
        resultado = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return resultado

    # --- Resultados ---

    def salvar_resultado(
        self,
        cidade: str,
        data_alvo: str,
        temperatura_real: float,
        faixa_vencedora: int,
        fonte_resolucao: str,
    ) -> None:
        conn = self._conectar()
        conn.execute(
            """INSERT INTO resultados
               (cidade, data_alvo, temperatura_real, faixa_vencedora, fonte_resolucao)
               VALUES (?, ?, ?, ?, ?)""",
            (cidade, data_alvo, temperatura_real, faixa_vencedora, fonte_resolucao),
        )
        conn.commit()
        conn.close()

    def buscar_resultado(self, cidade: str, data_alvo: str) -> Optional[dict]:
        conn = self._conectar()
        cursor = conn.execute(
            "SELECT * FROM resultados WHERE cidade = ? AND data_alvo = ?",
            (cidade, data_alvo),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # --- Performance ---

    def salvar_performance(
        self,
        cidade: str,
        data_alvo: str,
        horizonte: str,
        acertou_faixa: bool,
        erro_graus: float,
        lucro_simulado: float,
    ) -> None:
        conn = self._conectar()
        conn.execute(
            """INSERT INTO performance
               (cidade, data_alvo, horizonte, acertou_faixa, erro_graus, lucro_simulado)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (cidade, data_alvo, horizonte, int(acertou_faixa), erro_graus, lucro_simulado),
        )
        conn.commit()
        conn.close()

    def buscar_performance(self, cidade: Optional[str] = None, horizonte: Optional[str] = None) -> list[dict]:
        conn = self._conectar()
        query = "SELECT * FROM performance WHERE 1=1"
        params: list = []
        if cidade:
            query += " AND cidade = ?"
            params.append(cidade)
        if horizonte:
            query += " AND horizonte = ?"
            params.append(horizonte)
        query += " ORDER BY data_alvo DESC"
        cursor = conn.execute(query, params)
        resultado = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return resultado

    def limpar_previsoes_antigas(self, cidade: str, data_alvo: str) -> None:
        """Remove previsoes anteriores pra evitar duplicatas na re-coleta."""
        conn = self._conectar()
        conn.execute(
            "DELETE FROM previsoes WHERE cidade = ? AND data_alvo = ?",
            (cidade, data_alvo),
        )
        conn.commit()
        conn.close()

    def limpar_distribuicoes_antigas(self, cidade: str, data_alvo: str, horizonte: str) -> None:
        """Remove distribuicoes anteriores antes de recalcular."""
        conn = self._conectar()
        conn.execute(
            "DELETE FROM distribuicoes WHERE cidade = ? AND data_alvo = ? AND horizonte = ?",
            (cidade, data_alvo, horizonte),
        )
        conn.commit()
        conn.close()
