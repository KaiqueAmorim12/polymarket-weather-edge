"""Coletor AccuWeather — previsao diaria via API gratuita (50 req/dia)."""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from coletores.base import Previsao

logger = logging.getLogger(__name__)

BASE_URL = "https://dataservice.accuweather.com"


class AccuWeatherColetor:
    """Coleta previsoes via AccuWeather API (chave gratuita, 50 req/dia)."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._cache_location_key: dict[str, str] = {}

    async def coletar(
        self, latitude: float, longitude: float, data_alvo: str
    ) -> Optional[Previsao]:
        """Busca previsao pra uma coordenada/data."""
        try:
            location_key = await self._buscar_location_key(latitude, longitude)
            if not location_key:
                return None

            async with httpx.AsyncClient(timeout=30.0) as client:
                resposta = await client.get(
                    f"{BASE_URL}/forecasts/v1/daily/5day/{location_key}",
                    params={
                        "apikey": self.api_key,
                        "metric": True,
                    },
                )
                resposta.raise_for_status()
                forecasts = resposta.json().get("DailyForecasts", [])
                return self._parsear_resposta(forecasts, data_alvo)
        except Exception as e:
            logger.warning(f"Erro ao coletar AccuWeather: {e}")
            return None

    async def _buscar_location_key(self, latitude: float, longitude: float) -> Optional[str]:
        """Busca o location key do AccuWeather pra uma coordenada."""
        cache_key = f"{latitude},{longitude}"
        if cache_key in self._cache_location_key:
            return self._cache_location_key[cache_key]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resposta = await client.get(
                    f"{BASE_URL}/locations/v1/cities/geoposition/search",
                    params={
                        "apikey": self.api_key,
                        "q": f"{latitude},{longitude}",
                    },
                )
                resposta.raise_for_status()
                dados = resposta.json()
                key = dados.get("Key")
                if key:
                    self._cache_location_key[cache_key] = key
                return key
        except Exception as e:
            logger.warning(f"Erro ao buscar location key AccuWeather: {e}")
            return None

    def _parsear_resposta(
        self, forecasts: list[dict[str, Any]], data_alvo: str
    ) -> Optional[Previsao]:
        """Parseia resposta — encontra o dia alvo e pega max/min."""
        for forecast in forecasts:
            data_forecast = forecast.get("Date", "")[:10]
            if data_forecast == data_alvo:
                temp = forecast.get("Temperature", {})
                previsao = Previsao(
                    fonte="accuweather",
                    temperatura_max=temp["Maximum"]["Value"],
                    temperatura_min=temp["Minimum"]["Value"],
                    coletado_em=datetime.now(timezone.utc),
                )
                return previsao if previsao.valida() else None

        return None
