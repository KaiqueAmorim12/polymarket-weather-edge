"""Coletor Weather Underground API — dados hora a hora de temperatura.

Usa a API interna do Weather Underground (api.weather.com) que retorna
observacoes historicas a cada 30 minutos pra qualquer estacao.
Essa eh a MESMA fonte que a Polymarket usa pra resolver os contratos.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

WU_API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
WU_BASE_URL = "https://api.weather.com/v1/location/{estacao}/observations/historical.json"


@dataclass
class LeituraHoraria:
    """Uma leitura de temperatura num momento especifico."""
    timestamp: int
    temperatura: float
    hora_utc: str
    hora_local: str
    unidade: str


class ColetorWU:
    """Coleta dados hora a hora do Weather Underground."""

    async def coletar_dia(
        self,
        estacao: str,
        data_alvo: str,
        unidade: str,
        fuso_offset: float,
    ) -> list[LeituraHoraria]:
        """Busca todas as leituras de um dia pra uma estacao."""
        data_formatada = data_alvo.replace("-", "")
        unidade_param = "m" if unidade == "C" else "e"

        url = WU_BASE_URL.format(estacao=estacao)
        params = {
            "apiKey": WU_API_KEY,
            "units": unidade_param,
            "startDate": data_formatada,
            "endDate": data_formatada,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resposta = await client.get(url, params=params)
                resposta.raise_for_status()
                dados = resposta.json()
                leituras = self._parsear_resposta(dados, unidade, fuso_offset)
                logger.info(f"WU {estacao}: {len(leituras)} leituras para {data_alvo}")
                return leituras
        except Exception as e:
            logger.warning(f"Erro ao coletar WU {estacao}: {e}")
            return []

    def _parsear_resposta(
        self,
        dados: dict[str, Any],
        unidade: str,
        fuso_offset: float,
    ) -> list[LeituraHoraria]:
        """Parseia resposta da API e retorna lista de leituras."""
        observacoes = dados.get("observations", [])
        leituras: list[LeituraHoraria] = []

        for obs in observacoes:
            ts = obs.get("valid_time_gmt", 0)
            temp = obs.get("temp")
            if temp is None:
                continue

            dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
            hora_utc = dt_utc.strftime("%H:%M")
            dt_local = dt_utc + timedelta(hours=fuso_offset)
            hora_local = dt_local.strftime("%H:%M")

            leituras.append(LeituraHoraria(
                timestamp=ts,
                temperatura=float(temp),
                hora_utc=hora_utc,
                hora_local=hora_local,
                unidade=unidade,
            ))

        return sorted(leituras, key=lambda l: l.timestamp)

    def _calcular_pico(self, leituras: list[LeituraHoraria]) -> dict[str, Any]:
        """Calcula temperatura pico e horario."""
        if not leituras:
            return {"temperatura": 0, "hora_local": "--", "hora_utc": "--"}
        pico = max(leituras, key=lambda l: l.temperatura)
        return {
            "temperatura": pico.temperatura,
            "hora_local": pico.hora_local,
            "hora_utc": pico.hora_utc,
            "unidade": pico.unidade,
        }

    def _calcular_status(self, leituras: list[LeituraHoraria]) -> str:
        """Calcula status atual: Subindo, Perto do pico, Pico atingido, Descendo."""
        if len(leituras) < 2:
            return "Sem dados"

        ultima = leituras[-1].temperatura
        penultima = leituras[-2].temperatura

        if len(leituras) >= 3:
            antepenultima = leituras[-3].temperatura
            if penultima > antepenultima and ultima < penultima:
                return "Pico atingido"
            if ultima < penultima and penultima < antepenultima:
                return "Descendo"

        if ultima > penultima:
            return "Subindo"
        elif ultima == penultima:
            return "Perto do pico"
        else:
            return "Descendo"
