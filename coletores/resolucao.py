"""Coletor de resolucao — busca temperatura REAL registrada no WU History.

A Polymarket resolve contratos usando:
https://www.wunderground.com/history/daily/{pais}/{cidade}/{estacao}/date/{YYYY-M-D}

Este modulo acessa essa pagina APOS o dia passar e extrai a temperatura
maxima real registrada, que eh o resultado oficial do contrato.
"""
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup

from banco import Repositorio

logger = logging.getLogger(__name__)

RAIZ = Path(__file__).parent.parent


class ColetorResolucao:
    """Busca temperatura real no WU History apos o dia passar."""

    def _formatar_url(self, url_template: str, data_alvo: str) -> str:
        """Formata URL substituindo {data} por YYYY-M-D (sem zeros a esquerda)."""
        dt = datetime.strptime(data_alvo, "%Y-%m-%d")
        data_formatada = f"{dt.year}-{dt.month}-{dt.day}"
        return url_template.replace("{data}", data_formatada)

    async def buscar_temperatura_real(
        self, url_template: str, data_alvo: str
    ) -> Optional[float]:
        """Busca temperatura maxima real registrada no WU History."""
        url = self._formatar_url(url_template, data_alvo)
        logger.info(f"Buscando resolucao em: {url}")

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resposta = await client.get(url, headers=headers)
                resposta.raise_for_status()

                return self._parsear_html_history(resposta.text)
        except Exception as e:
            logger.warning(f"Erro ao buscar resolucao ({url}): {e}")
            return None

    def _parsear_html_history(self, html: str) -> Optional[float]:
        """Parseia pagina de historico do WU e extrai temperatura maxima.

        Tenta multiplas estrategias pois o layout do WU muda.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Estrategia 1: buscar na tabela de observacoes do dia
            # WU costuma ter uma tabela com Max Temperature
            for td in soup.find_all(["td", "span", "div"]):
                texto = td.get_text(strip=True)
                if "max" in texto.lower() and ("°c" in texto.lower() or "°f" in texto.lower()):
                    temp = self._extrair_max_de_texto(texto)
                    if temp is not None:
                        return temp

            # Estrategia 2: buscar no texto completo da pagina
            texto_completo = soup.get_text()
            return self._extrair_max_de_texto(texto_completo)

        except Exception as e:
            logger.warning(f"Erro ao parsear HTML do WU History: {e}")
            return None

    def _extrair_max_de_texto(self, texto: str) -> Optional[float]:
        """Extrai temperatura maxima de um bloco de texto.

        Procura padrao: 'Max Temperature' seguido de um numero com °C ou °F.
        """
        # Procurar "Max Temperature" seguido de numero
        match = re.search(r"Max\s*Temperature\s*(\d+)\s*°([CF])", texto, re.IGNORECASE)
        if match:
            valor = float(match.group(1))
            unidade = match.group(2).upper()
            if unidade == "F":
                valor = round((valor - 32) * 5 / 9, 1)
            return valor

        return None

    async def verificar_resultados(self, repo: Repositorio) -> None:
        """Verifica resultados de ontem pra todas as cidades.

        Busca temperatura real no WU History, salva em 'resultados'
        e atualiza 'performance'.
        """
        from datetime import date, timedelta

        ontem = (date.today() - timedelta(days=1)).isoformat()

        with open(RAIZ / "config" / "cidades.json", encoding="utf-8") as f:
            cidades = json.load(f)["cidades"]

        for cidade in cidades:
            nome = cidade["nome"]
            url_template = cidade.get("url_history_wu", "")

            if not url_template:
                logger.warning(f"{nome}: sem URL de resolucao configurada")
                continue

            # Verificar se ja tem resultado
            resultado_existente = repo.buscar_resultado(nome, ontem)
            if resultado_existente:
                continue

            temp_real = await self.buscar_temperatura_real(url_template, ontem)
            if temp_real is None:
                logger.warning(f"{nome}: nao conseguiu buscar temperatura real de {ontem}")
                continue

            faixa_vencedora = round(temp_real)

            repo.salvar_resultado(
                cidade=nome,
                data_alvo=ontem,
                temperatura_real=temp_real,
                faixa_vencedora=faixa_vencedora,
                fonte_resolucao=f"wunderground_history",
            )
            logger.info(f"{nome} ({ontem}): temperatura real = {temp_real}°C (faixa {faixa_vencedora}°C)")

            # Atualizar performance pra cada horizonte
            for horizonte in ["D-1", "D-2"]:
                analises = repo.buscar_analises(nome, ontem, horizonte)
                if not analises:
                    continue

                # Encontrar a faixa que o modelo recomendou (maior edge)
                melhor = max(analises, key=lambda a: a["edge"])
                acertou = melhor["faixa_grau"] == faixa_vencedora
                erro = abs(melhor["faixa_grau"] - faixa_vencedora)

                # Calcular lucro simulado
                recomendadas = [a for a in analises if a["recomendacao"] == "COMPRAR"]
                lucro = 0.0
                for rec in recomendadas:
                    if rec["faixa_grau"] == faixa_vencedora:
                        lucro += (1.0 - rec["prob_mercado"])  # ganhou: recebe $1 - custo
                    else:
                        lucro -= rec["prob_mercado"]  # perdeu: perde o custo

                repo.salvar_performance(
                    cidade=nome,
                    data_alvo=ontem,
                    horizonte=horizonte,
                    acertou_faixa=acertou,
                    erro_graus=float(erro),
                    lucro_simulado=lucro,
                )
                status = "ACERTOU" if acertou else f"ERROU por {erro}°C"
                logger.info(f"  {nome} {horizonte}: {status} | lucro simulado: ${lucro:+.2f}")
