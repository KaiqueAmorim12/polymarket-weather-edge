"""Modulo coletores — coleta previsoes de multiplas fontes meteorologicas."""
import logging
from typing import Optional

from coletores.base import Previsao, ResultadoColeta
from coletores.open_meteo import OpenMeteoColetor
from coletores.openweathermap import OpenWeatherMapColetor
from coletores.accuweather import AccuWeatherColetor
from coletores.visual_crossing import VisualCrossingColetor
from coletores.wunderground import WundergroundColetor

logger = logging.getLogger(__name__)

__all__ = [
    "Previsao",
    "ResultadoColeta",
    "coletar_todas_fontes",
]


async def coletar_todas_fontes(
    cidade: str,
    latitude: float,
    longitude: float,
    data_alvo: str,
    estacao_resolucao: str,
    chaves: dict[str, str],
) -> ResultadoColeta:
    """Coleta previsoes de todas as fontes disponiveis pra uma cidade/data."""
    previsoes: list[Previsao] = []
    erros: list[str] = []

    # 1. Open-Meteo (GFS + ECMWF) — sem chave
    try:
        coletor_om = OpenMeteoColetor()
        prev_om = await coletor_om.coletar(latitude, longitude, data_alvo)
        previsoes.extend(prev_om)
    except Exception as e:
        erros.append(f"open_meteo: {e}")

    # 2. OpenWeatherMap
    chave_owm = chaves.get("OPENWEATHERMAP_API_KEY", "")
    if chave_owm:
        try:
            coletor_owm = OpenWeatherMapColetor(api_key=chave_owm)
            prev = await coletor_owm.coletar(latitude, longitude, data_alvo)
            if prev:
                previsoes.append(prev)
        except Exception as e:
            erros.append(f"openweathermap: {e}")

    # 3. AccuWeather
    chave_aw = chaves.get("ACCUWEATHER_API_KEY", "")
    if chave_aw:
        try:
            coletor_aw = AccuWeatherColetor(api_key=chave_aw)
            prev = await coletor_aw.coletar(latitude, longitude, data_alvo)
            if prev:
                previsoes.append(prev)
        except Exception as e:
            erros.append(f"accuweather: {e}")

    # 4. Visual Crossing
    chave_vc = chaves.get("VISUAL_CROSSING_API_KEY", "")
    if chave_vc:
        try:
            coletor_vc = VisualCrossingColetor(api_key=chave_vc)
            prev = await coletor_vc.coletar(latitude, longitude, data_alvo)
            if prev:
                previsoes.append(prev)
        except Exception as e:
            erros.append(f"visual_crossing: {e}")

    # 5. Weather Underground (scraping)
    try:
        coletor_wu = WundergroundColetor()
        prev = await coletor_wu.coletar(estacao_resolucao, data_alvo)
        if prev:
            previsoes.append(prev)
    except Exception as e:
        erros.append(f"wunderground: {e}")

    logger.info(f"{cidade} ({data_alvo}): {len(previsoes)} previsoes, {len(erros)} erros")
    return ResultadoColeta(
        cidade=cidade,
        data_alvo=data_alvo,
        previsoes=previsoes,
        erros=erros,
    )
