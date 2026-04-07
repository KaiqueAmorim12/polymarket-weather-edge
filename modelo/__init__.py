"""Modulo modelo — calculo de probabilidades por faixa de temperatura."""
from modelo.distribuicao import calcular_distribuicao, DistribuicaoFaixa
from modelo.pesos import media_ponderada, PESOS_PADRAO
from modelo.confianca import calcular_confianca

__all__ = [
    "calcular_distribuicao",
    "DistribuicaoFaixa",
    "media_ponderada",
    "PESOS_PADRAO",
    "calcular_confianca",
]
