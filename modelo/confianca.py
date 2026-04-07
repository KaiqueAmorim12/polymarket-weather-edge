"""Calculo do score de confianca da previsao."""
import numpy as np

from coletores.base import Previsao


def calcular_confianca(
    previsoes: list[Previsao],
    horas_desde_coleta: float,
) -> str:
    """Calcula confianca baseado na concordancia entre fontes e frescor dos dados.

    ALTA:  fontes concordam (desvio <0.5C) e dados frescos (<6h)
    MEDIA: leve discordancia (desvio 0.5-1.5C) ou dados >6h
    BAIXA: grande discordancia (desvio >1.5C) ou poucas fontes (<2)
    """
    if len(previsoes) < 2:
        return "BAIXA"

    temps = [p.temperatura_max for p in previsoes]
    desvio = float(np.std(temps))

    if desvio > 1.5:
        return "BAIXA"
    if desvio > 0.5 or horas_desde_coleta > 6.0:
        return "MEDIA"
    return "ALTA"


def calcular_desvio_modelo(
    previsoes: list[Previsao],
    horizonte: str,
    desvio_base_d1: float = 0.5,
    desvio_base_d2: float = 1.2,
    divergencia_threshold: float = 2.0,
) -> float:
    """Calcula desvio padrao pra distribuicao normal."""
    desvio_base = desvio_base_d1 if horizonte == "D-1" else desvio_base_d2

    if len(previsoes) < 2:
        return desvio_base

    temps = [p.temperatura_max for p in previsoes]
    desvio_fontes = float(np.std(temps))

    if desvio_fontes > divergencia_threshold:
        return max(desvio_base, desvio_fontes)

    return max(desvio_base, (desvio_base + desvio_fontes) / 2)
