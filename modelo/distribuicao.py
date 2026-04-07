"""Geracao da distribuicao de probabilidade por faixa de temperatura."""
from dataclasses import dataclass

import numpy as np
from scipy import stats

from coletores.base import Previsao
from modelo.pesos import media_ponderada
from modelo.confianca import calcular_confianca, calcular_desvio_modelo


@dataclass
class DistribuicaoFaixa:
    """Probabilidade calculada pra uma faixa de temperatura."""

    grau: int
    probabilidade: float
    media: float
    desvio_padrao: float
    confianca: str


def calcular_distribuicao(
    previsoes: list[Previsao],
    pesos: dict[str, float],
    horizonte: str,
    faixa_min: int = -10,
    faixa_max: int = 50,
    horas_desde_coleta: float = 3.0,
) -> list[DistribuicaoFaixa]:
    """Gera distribuicao de probabilidade por faixa de 1 grau.

    1. Calcula media ponderada das fontes
    2. Calcula desvio padrao baseado no horizonte e discordancia
    3. Gera curva normal e integra em cada faixa de 1C
    4. Retorna lista de DistribuicaoFaixa com probabilidades
    """
    media = media_ponderada(previsoes, pesos)
    desvio = calcular_desvio_modelo(previsoes, horizonte)
    confianca = calcular_confianca(previsoes, horas_desde_coleta)

    distribuicao_normal = stats.norm(loc=media, scale=desvio)

    faixas: list[DistribuicaoFaixa] = []

    for grau in range(faixa_min, faixa_max + 1):
        prob = float(distribuicao_normal.cdf(grau + 0.5) - distribuicao_normal.cdf(grau - 0.5))
        if prob >= 0.001:
            faixas.append(DistribuicaoFaixa(
                grau=grau,
                probabilidade=prob,
                media=media,
                desvio_padrao=desvio,
                confianca=confianca,
            ))

    soma = sum(f.probabilidade for f in faixas)
    if soma > 0:
        for f in faixas:
            f.probabilidade = f.probabilidade / soma

    return faixas
