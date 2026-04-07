"""Coletor OpenWeatherMap — previsao 5 dias via API gratuita."""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from coletores.base import Previsao

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"


class OpenWeatherMapColetor:
    """Coleta previsoes via OpenWeatherMap API (chave gratuita, 1000 req/dia)."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def coletar(
        self, latitude: float, longitude: float, data_alvo: str
    ) -> Optional[Previsao]:
        """Busca previsao pra uma coordenada/data."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resposta = await client.get(
                    BASE_URL,
                    params={
                        "lat": latitude,
                        "lon": longitude,
                        "appid": self.api_key,
                        "units": "metric",
                    },
                )
                resposta.raise_for_status()
                return self._parsear_resposta(resposta.json(), data_alvo)
        except Exception as e:
            logger.warning(f"Erro ao coletar OpenWeatherMap: {e}")
            return None

    def _parsear_resposta(
        self, dados: dict[str, Any], data_alvo: str
    ) -> Optional[Previsao]:
        """Parseia resposta — filtra entradas do dia alvo e pega max/min."""
        entradas = dados.get("list", [])

        temps_max: list[float] = []
        temps_min: list[float] = []

        for entrada in entradas:
            dt = datetime.fromtimestamp(entrada["dt"], tz=timezone.utc)
            if dt.strftime("%Y-%m-%d") == data_alvo:
                temps_max.append(entrada["main"]["temp_max"])
                temps_min.append(entrada["main"]["temp_min"])

        if not temps_max:
            return None

        previsao = Previsao(
            fonte="openweathermap",
            temperatura_max=max(temps_max),
            temperatura_min=min(temps_min),
            coletado_em=datetime.now(timezone.utc),
        )
        return previsao if previsao.valida() else None
