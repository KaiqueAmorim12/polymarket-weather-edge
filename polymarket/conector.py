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

    def _construir_slug(self, cidade: str, data_alvo: str) -> str:
        """Constroi o slug do evento de temperatura na Polymarket.

        Padrao: highest-temperature-in-{cidade}-on-{month}-{day}-{year}
        Ex: highest-temperature-in-london-on-april-8-2026
        """
        dt = datetime.strptime(data_alvo, "%Y-%m-%d")
        mes_ingles = dt.strftime("%B").lower()  # april, may, etc.
        cidade_slug = cidade.lower().replace(" ", "-")
        return f"highest-temperature-in-{cidade_slug}-on-{mes_ingles}-{dt.day}-{dt.year}"

    async def buscar_evento_por_slug(self, cidade: str, data_alvo: str) -> Optional[dict[str, Any]]:
        """Busca evento de temperatura via slug direto na Gamma API."""
        slug = self._construir_slug(cidade, data_alvo)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resposta = await client.get(f"{GAMMA_API_BASE}/events/slug/{slug}")
                if resposta.status_code == 200:
                    evento = resposta.json()
                    logger.info(f"Polymarket: encontrado '{evento.get('title', '')}' ({len(evento.get('markets', []))} faixas)")
                    return evento
                else:
                    logger.warning(f"Polymarket: evento nao encontrado para slug '{slug}' (status {resposta.status_code})")
                    return None
        except Exception as e:
            logger.warning(f"Erro ao buscar evento Polymarket ({slug}): {e}")
            return None

    async def buscar_odds(self, cidade: str, data_alvo: str) -> list[dict[str, Any]]:
        """Busca odds de todas as faixas de temperatura pra uma cidade/data."""
        evento = await self.buscar_evento_por_slug(cidade, data_alvo)
        if not evento:
            return []
        return self._parsear_evento(evento)

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
        """Extrai faixa de temperatura de uma pergunta de contrato.

        Lida com:
        - "20°C", "20°C or higher", "16°C or below"
        - "between 68-69°F" (faixas de range, ex: Miami)
        - Diferentes encodings do simbolo de grau
        """
        import re
        pergunta_norm = pergunta.replace("\u00b0", "°").replace("&#176;", "°")

        # Padrao 1: "between X-Y°F" (faixas de range)
        match_range = re.search(
            r"between\s+(\d+)\s*-\s*(\d+)\s*°\s*([CF])",
            pergunta_norm,
            re.IGNORECASE,
        )
        if match_range:
            return parsear_faixa_temperatura(
                f"between {match_range.group(1)}-{match_range.group(2)}°{match_range.group(3)}"
            )

        # Padrao 2: "20°C or higher", "16°C or below", "20°C"
        match = re.search(
            r"(\d+)\s*°\s*([CF])\s*(or\s+(?:higher|lower|above|below)|ou\s+(?:mais|menos))?",
            pergunta_norm,
            re.IGNORECASE,
        )
        if match:
            numero = match.group(1)
            unidade = match.group(2)
            modificador = (match.group(3) or "").strip()
            texto = f"{numero}°{unidade}"
            if modificador:
                texto += f" {modificador}"
            return parsear_faixa_temperatura(texto)

        # Fallback: qualquer numero seguido de C ou F
        match = re.search(r"(\d+)\s*[°º]\s*([CF])", pergunta_norm, re.IGNORECASE)
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
