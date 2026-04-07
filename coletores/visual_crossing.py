"""Coletor Visual Crossing — previsao diaria via API gratuita."""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from coletores.base import Previsao

logger = logging.getLogger(__name__)

BASE_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"


class VisualCrossingColetor:
    """Coleta previsoes via Visual Crossing API (chave gratuita, 1000 req/dia)."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def coletar(
        self, latitude: float, longitude: float, data_alvo: str
    ) -> Optional[Previsao]:
        """Busca previsao pra uma coordenada/data."""
        try:
            url = f"{BASE_URL}/{latitude},{longitude}/{data_alvo}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resposta = await client.get(
                    url,
                    params={
                        "key": self.api_key,
                        "unitGroup": "metric",
                        "include": "days",
                    },
                )
                resposta.raise_for_status()
                return self._parsear_resposta(resposta.json(), data_alvo)
        except Exception as e:
            logger.warning(f"Erro ao coletar Visual Crossing: {e}")
            return None

    def _parsear_resposta(
        self, dados: dict[str, Any], data_alvo: str
    ) -> Optional[Previsao]:
        """Parseia resposta — pega tempmax/tempmin do dia."""
        dias = dados.get("days", [])

        for dia in dias:
            if dia.get("datetime") == data_alvo:
                previsao = Previsao(
                    fonte="visual_crossing",
                    temperatura_max=dia["tempmax"],
                    temperatura_min=dia["tempmin"],
                    coletado_em=datetime.now(timezone.utc),
                )
                return previsao if previsao.valida() else None

        return None
