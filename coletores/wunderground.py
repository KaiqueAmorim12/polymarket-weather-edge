"""Coletor Weather Underground — scraping da previsao (fonte de resolucao Polymarket)."""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from coletores.base import Previsao

logger = logging.getLogger(__name__)

BASE_URL = "https://www.wunderground.com/forecast"


class WundergroundColetor:
    """Coleta previsoes via scraping do Weather Underground.

    IMPORTANTE: Esta eh a fonte de resolucao da Polymarket.
    O que o Weather Underground registrar eh o resultado oficial.
    """

    async def coletar(
        self, estacao: str, data_alvo: str
    ) -> Optional[Previsao]:
        """Busca previsao via scraping da pagina de forecast."""
        if estacao == "a_mapear":
            logger.warning("Estacao nao mapeada, pulando Weather Underground")
            return None

        try:
            url = f"{BASE_URL}/{estacao}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resposta = await client.get(url, headers=headers)
                resposta.raise_for_status()

                return self._parsear_html(resposta.text, data_alvo)
        except Exception as e:
            logger.warning(f"Erro ao coletar Weather Underground ({estacao}): {e}")
            return None

    def _parsear_html(self, html: str, data_alvo: str) -> Optional[Previsao]:
        """Parseia HTML da pagina de forecast do Weather Underground.

        NOTA: A estrutura HTML do WU muda com frequencia.
        Se o scraping quebrar, ajustar os seletores aqui.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            scripts = soup.find_all("script")
            for script in scripts:
                texto = script.string or ""
                if "temperature" in texto.lower() and "forecast" in texto.lower():
                    pass

            temp_elements = soup.select(".forecast-day .temp")
            if temp_elements:
                for elem in temp_elements:
                    hi = elem.select_one(".hi")
                    lo = elem.select_one(".lo")
                    if hi and lo:
                        return self._parsear_temperatura_de_texto(
                            hi.get_text(strip=True),
                            lo.get_text(strip=True),
                        )

            logger.warning("Nao conseguiu parsear HTML do Weather Underground")
            return None
        except Exception as e:
            logger.warning(f"Erro ao parsear HTML do WU: {e}")
            return None

    def _parsear_temperatura_de_texto(
        self, max_texto: str, min_texto: str
    ) -> Optional[Previsao]:
        """Converte textos de temperatura em Previsao."""
        try:
            temp_max = float(max_texto.replace("°", "").strip())
            temp_min = float(min_texto.replace("°", "").strip())

            previsao = Previsao(
                fonte="wunderground",
                temperatura_max=temp_max,
                temperatura_min=temp_min,
                coletado_em=datetime.now(timezone.utc),
            )
            return previsao if previsao.valida() else None
        except ValueError:
            return None
