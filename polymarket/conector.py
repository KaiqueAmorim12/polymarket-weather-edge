"""Conector Polymarket — busca contratos de clima e odds via Gamma API."""
import json
import logging
from datetime import datetime
from typing import Any, Optional

import httpx

from polymarket.mapeador import parsear_faixa_temperatura

logger = logging.getLogger(__name__)

GAMMA_API_BASE = "https://gamma-api.polymarket.com"


class PolymarketConector:
    """Busca contratos de temperatura e odds na Polymarket."""

    async def buscar_eventos_clima(self, cidade: str, data_alvo: str) -> list[dict[str, Any]]:
        """Busca eventos de temperatura pra uma cidade/data na Gamma API."""
        try:
            termos = f"highest temperature {cidade}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                resposta = await client.get(
                    f"{GAMMA_API_BASE}/events",
                    params={
                        "closed": False,
                        "limit": 20,
                        "title": termos,
                    },
                )
                resposta.raise_for_status()
                eventos = resposta.json()

                eventos_filtrados = []
                for evento in eventos:
                    titulo = evento.get("title", "").lower()
                    if self._data_no_titulo(data_alvo, titulo):
                        eventos_filtrados.append(evento)

                return eventos_filtrados
        except Exception as e:
            logger.warning(f"Erro ao buscar eventos Polymarket para {cidade} ({data_alvo}): {e}")
            return []

    async def buscar_odds(self, cidade: str, data_alvo: str) -> list[dict[str, Any]]:
        """Busca odds de todas as faixas de temperatura pra uma cidade/data."""
        eventos = await self.buscar_eventos_clima(cidade, data_alvo)

        todas_odds: list[dict[str, Any]] = []
        for evento in eventos:
            odds = self._parsear_evento(evento)
            todas_odds.extend(odds)

        return todas_odds

    def _parsear_evento(self, evento: dict[str, Any]) -> list[dict[str, Any]]:
        """Parseia evento da Gamma API e extrai odds por faixa."""
        mercados = evento.get("markets", [])
        odds: list[dict[str, Any]] = []

        for mercado in mercados:
            question = mercado.get("question", "")

            faixa = self._extrair_faixa_da_pergunta(question)
            if faixa is None:
                continue

            precos_str = mercado.get("outcomePrices", "[]")
            try:
                precos = json.loads(precos_str)
            except (json.JSONDecodeError, TypeError):
                precos = []

            preco_compra = float(precos[0]) if len(precos) > 0 else 0.0
            preco_venda = 1.0 - float(precos[1]) if len(precos) > 1 else 0.0

            volume_str = mercado.get("volume", "0")
            try:
                volume = float(volume_str)
            except (ValueError, TypeError):
                volume = 0.0

            odds.append({
                "faixa_grau": faixa.grau,
                "tipo_faixa": faixa.tipo,
                "probabilidade_mercado": preco_compra,
                "preco_compra": preco_compra,
                "preco_venda": preco_venda,
                "volume": volume,
                "market_id": mercado.get("id", ""),
            })

        return odds

    def _extrair_faixa_da_pergunta(self, pergunta: str) -> Optional[Any]:
        """Extrai faixa de temperatura de uma pergunta de contrato."""
        import re
        match = re.search(r"(\d+°[CF](?:\s+(?:or\s+(?:higher|lower|above|below)|ou\s+(?:mais|menos)))?)", pergunta)
        if match:
            return parsear_faixa_temperatura(match.group(1))

        match = re.search(r"(\d+)\s*°\s*([CF])", pergunta)
        if match:
            return parsear_faixa_temperatura(f"{match.group(1)}°{match.group(2)}")

        return None

    def _data_no_titulo(self, data_alvo: str, titulo: str) -> bool:
        """Verifica se a data alvo esta no titulo do evento."""
        try:
            dt = datetime.strptime(data_alvo, "%Y-%m-%d")
            formatos = [
                f"{dt.strftime('%B').lower()} {dt.day}",
                f"{dt.strftime('%B').lower()} {dt.day:02d}",
            ]
            return any(fmt in titulo for fmt in formatos)
        except ValueError:
            return False
