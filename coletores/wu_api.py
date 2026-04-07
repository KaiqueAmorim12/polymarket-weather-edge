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
        """Busca todas as leituras de um dia LOCAL pra uma estacao.

        O WU API retorna dados em UTC. Pra fusos positivos (ex: Tokyo UTC+9),
        pedimos o dia anterior tambem pra cobrir a manha local.
        Pra fusos negativos (ex: NYC UTC-4), pedimos o dia seguinte tambem.
        Depois filtramos so as leituras do dia LOCAL correto.
        """
        unidade_param = "m" if unidade == "C" else "e"
        url = WU_BASE_URL.format(estacao=estacao)

        # Calcular range de datas UTC que cobre o dia local inteiro
        dt_alvo = datetime.strptime(data_alvo, "%Y-%m-%d").date()
        if fuso_offset > 0:
            # Fuso positivo: manha local = dia anterior UTC
            data_inicio = (dt_alvo - timedelta(days=1)).strftime("%Y%m%d")
        else:
            data_inicio = dt_alvo.strftime("%Y%m%d")

        if fuso_offset < 0:
            # Fuso negativo: noite local = dia seguinte UTC
            data_fim = (dt_alvo + timedelta(days=1)).strftime("%Y%m%d")
        else:
            data_fim = dt_alvo.strftime("%Y%m%d")

        params = {
            "apiKey": WU_API_KEY,
            "units": unidade_param,
            "startDate": data_inicio,
            "endDate": data_fim,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resposta = await client.get(url, params=params)
                resposta.raise_for_status()
                dados = resposta.json()
                todas_leituras = self._parsear_resposta(dados, unidade, fuso_offset)

                # Filtrar so leituras do dia LOCAL correto
                leituras = [
                    l for l in todas_leituras
                    if self._data_local(l.timestamp, fuso_offset) == data_alvo
                ]

                logger.info(f"WU {estacao}: {len(leituras)} leituras locais para {data_alvo}")
                return leituras
        except Exception as e:
            logger.warning(f"Erro ao coletar WU {estacao}: {e}")
            return []

    def _data_local(self, timestamp: int, fuso_offset: float) -> str:
        """Retorna a data local (YYYY-MM-DD) de um timestamp UTC."""
        dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        dt_local = dt_utc + timedelta(hours=fuso_offset)
        return dt_local.strftime("%Y-%m-%d")

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

    async def coletar_previsao(
        self, latitude: float, longitude: float, unidade: str
    ) -> Optional[dict[str, Any]]:
        """Busca previsao de temperatura maxima do WU forecast.

        Retorna dict com 'data_local' e 'temp_max' pra cada dia disponivel,
        ou None se falhar. Retorna os 2 primeiros dias (hoje e amanha local).
        """
        unidade_param = "m" if unidade == "C" else "e"
        url = "https://api.weather.com/v3/wx/forecast/daily/5day"
        params = {
            "geocode": f"{latitude},{longitude}",
            "format": "json",
            "units": unidade_param,
            "language": "en-US",
            "apiKey": WU_API_KEY,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(url, params=params)
                r.raise_for_status()
                dados = r.json()
                maximas = dados.get("calendarDayTemperatureMax", [])
                datas_local = dados.get("validTimeLocal", [])
                resultado = []
                for i in range(min(2, len(maximas))):
                    if maximas[i] is not None:
                        data_str = datas_local[i][:10] if i < len(datas_local) else None
                        resultado.append({
                            "data_local": data_str,
                            "temp_max": float(maximas[i]),
                        })
                return resultado if resultado else None
        except Exception as e:
            logger.warning(f"Erro ao buscar previsao WU: {e}")
            return None

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
