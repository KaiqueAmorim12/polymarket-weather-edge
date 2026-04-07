"""Repositorio — CRUD via Supabase REST API."""
import os
from typing import Optional

import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://wzjdthcxlsopmqcwtvla.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind6amR0aGN4bHNvcG1xY3d0dmxhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzUzNjY2MywiZXhwIjoyMDczMTEyNjYzfQ.ZRXuEULiCpkIYDhspjYd1dadql4AwMnygGzr6D6Ts0Q")


class Repositorio:
    """Acesso ao Supabase via REST API."""

    def __init__(self, caminho_db: str = "") -> None:
        """caminho_db ignorado — mantido pra compatibilidade."""
        self.base_url = f"{SUPABASE_URL}/rest/v1"
        self.headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _get(self, tabela: str, params: str = "") -> list[dict]:
        r = httpx.get(f"{self.base_url}/{tabela}?{params}", headers=self.headers, timeout=15)
        r.raise_for_status()
        return r.json()

    def _post(self, tabela: str, dados: dict | list[dict]) -> None:
        r = httpx.post(f"{self.base_url}/{tabela}", headers=self.headers, json=dados, timeout=15)
        r.raise_for_status()

    def _delete(self, tabela: str, params: str) -> None:
        r = httpx.delete(f"{self.base_url}/{tabela}?{params}", headers=self.headers, timeout=15)
        r.raise_for_status()

    def _patch(self, tabela: str, params: str, dados: dict) -> None:
        r = httpx.patch(f"{self.base_url}/{tabela}?{params}", headers=self.headers, json=dados, timeout=15)
        r.raise_for_status()

    # --- Leituras ---

    def salvar_leitura(self, cidade: str, data_alvo: str, timestamp: int,
                       temperatura: float, hora_utc: str, hora_local: str, unidade: str) -> None:
        self._post("we_leituras", {
            "cidade": cidade, "data_alvo": data_alvo, "timestamp_wu": timestamp,
            "temperatura": temperatura, "hora_utc": hora_utc, "hora_local": hora_local, "unidade": unidade,
        })

    def buscar_leituras(self, cidade: str, data_alvo: str) -> list[dict]:
        return self._get("we_leituras", f"cidade=eq.{cidade}&data_alvo=eq.{data_alvo}&order=timestamp_wu")

    def limpar_leituras(self, cidade: str, data_alvo: str) -> None:
        self._delete("we_leituras", f"cidade=eq.{cidade}&data_alvo=eq.{data_alvo}")

    # --- Odds ---

    def salvar_odds(self, cidade: str, data_alvo: str, faixa: str,
                    preco_compra: float, volume: float, coletado_em: str) -> None:
        self._post("we_odds", {
            "cidade": cidade, "data_alvo": data_alvo, "faixa": faixa,
            "preco_compra": preco_compra, "volume": volume, "coletado_em": coletado_em,
        })

    def buscar_odds(self, cidade: str, data_alvo: str) -> list[dict]:
        return self._get("we_odds", f"cidade=eq.{cidade}&data_alvo=eq.{data_alvo}&order=coletado_em.desc")

    def buscar_odds_mais_recentes(self, cidade: str, data_alvo: str) -> list[dict]:
        todas = self._get("we_odds", f"cidade=eq.{cidade}&data_alvo=eq.{data_alvo}&order=coletado_em.desc")
        if not todas:
            return []
        mais_recente = todas[0]["coletado_em"]
        return [o for o in todas if o["coletado_em"] == mais_recente]

    def limpar_odds(self, cidade: str, data_alvo: str) -> None:
        self._delete("we_odds", f"cidade=eq.{cidade}&data_alvo=eq.{data_alvo}")

    # --- Apostas ---

    def registrar_aposta(self, cidade: str, data_alvo: str, faixa: str,
                         tipo: str, odd: float, valor: float, horario_registro: str) -> None:
        self._post("we_apostas", {
            "cidade": cidade, "data_alvo": data_alvo, "faixa": faixa,
            "tipo": tipo, "odd": odd, "valor": valor, "horario_registro": horario_registro,
        })

    def resolver_aposta(self, aposta_id: int, resultado: str, pnl: float) -> None:
        self._patch("we_apostas", f"id=eq.{aposta_id}", {"resultado": resultado, "pnl": pnl})

    def buscar_apostas_do_dia(self, data_alvo: str) -> list[dict]:
        return self._get("we_apostas", f"data_alvo=eq.{data_alvo}&order=horario_registro.desc")

    def buscar_historico_apostas(self, limite: int = 100) -> list[dict]:
        return self._get("we_apostas", f"order=data_alvo.desc,horario_registro.desc&limit={limite}")

    def calcular_metricas(self) -> dict:
        apostas = self._get("we_apostas", "select=resultado,pnl,valor")
        total = len(apostas)
        ganhou = sum(1 for a in apostas if a["resultado"] == "ganhou")
        perdeu = sum(1 for a in apostas if a["resultado"] == "perdeu")
        aguardando = sum(1 for a in apostas if a["resultado"] == "aguardando")
        pnl_total = sum(a.get("pnl", 0) or 0 for a in apostas)
        total_investido = sum(a.get("valor", 0) or 0 for a in apostas)
        total_resolvidas = ganhou + perdeu
        win_rate = (ganhou / total_resolvidas * 100) if total_resolvidas > 0 else 0
        roi = (pnl_total / total_investido * 100) if total_investido > 0 else 0
        return {
            "total_apostas": total, "ganhou": ganhou, "perdeu": perdeu,
            "aguardando": aguardando, "pnl_total": pnl_total,
            "total_investido": total_investido, "win_rate": win_rate, "roi": roi,
        }
