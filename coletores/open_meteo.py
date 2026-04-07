"""Coletor Open-Meteo — acesso a modelos GFS e ECMWF sem chave de API."""
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from coletores.base import Previsao

logger = logging.getLogger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoColetor:
    """Coleta previsoes dos modelos GFS e ECMWF via Open-Meteo."""

    async def coletar(
        self, latitude: float, longitude: float, data_alvo: str
    ) -> list[Previsao]:
        """Busca previsoes GFS e ECMWF pra uma coordenada/data."""
        previsoes: list[Previsao] = []

        modelos = [
            ("ecmwf_ifs025", "ecmwf"),
            ("gfs_seamless", "gfs"),
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            for modelo_api, nome_fonte in modelos:
                try:
                    resposta = await client.get(
                        BASE_URL,
                        params={
                            "latitude": latitude,
                            "longitude": longitude,
                            "daily": "temperature_2m_max,temperature_2m_min",
                            "models": modelo_api,
                            "start_date": data_alvo,
                            "end_date": data_alvo,
                            "timezone": "auto",
                        },
                    )
                    resposta.raise_for_status()
                    dados = resposta.json()
                    parsed = self._parsear_resposta(dados, data_alvo, fonte=nome_fonte)
                    previsoes.extend(parsed)
                    logger.info(f"Open-Meteo {nome_fonte}: {parsed[0].temperatura_max}C para {data_alvo}")
                except Exception as e:
                    logger.warning(f"Erro ao coletar Open-Meteo {nome_fonte}: {e}")

        return previsoes

    def _parsear_resposta(
        self,
        dados: dict[str, Any],
        data_alvo: str,
        fonte: str = "open_meteo",
    ) -> list[Previsao]:
        """Parseia a resposta JSON do Open-Meteo."""
        daily = dados.get("daily", {})
        datas = daily.get("time", [])
        maximas = daily.get("temperature_2m_max", [])
        minimas = daily.get("temperature_2m_min", [])

        previsoes: list[Previsao] = []
        for i, data in enumerate(datas):
            if data == data_alvo and i < len(maximas) and i < len(minimas):
                prev = Previsao(
                    fonte=fonte,
                    temperatura_max=maximas[i],
                    temperatura_min=minimas[i],
                    coletado_em=datetime.now(timezone.utc),
                )
                if prev.valida():
                    previsoes.append(prev)

        return previsoes
