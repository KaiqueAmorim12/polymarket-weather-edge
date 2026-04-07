"""Calculo de edge — diferenca entre probabilidade do modelo e odds do mercado."""
from dataclasses import dataclass
from typing import Any

from modelo.distribuicao import DistribuicaoFaixa


@dataclass
class AnaliseEdge:
    """Resultado da analise de edge pra uma faixa."""

    faixa_grau: int
    prob_modelo: float
    prob_mercado: float
    edge: float
    preco_compra: float
    volume: float
    confianca: str
    retorno: float


def calcular_edge(
    distribuicao: list[DistribuicaoFaixa],
    odds: list[dict[str, Any]],
) -> list[AnaliseEdge]:
    """Calcula edge pra cada faixa comparando modelo vs mercado."""
    dist_por_grau = {f.grau: f for f in distribuicao}

    analises: list[AnaliseEdge] = []

    for odd in odds:
        grau = odd["faixa_grau"]
        preco_compra = odd["preco_compra"]
        volume = odd.get("volume", 0)

        faixa_modelo = dist_por_grau.get(grau)
        prob_modelo = faixa_modelo.probabilidade if faixa_modelo else 0.0
        confianca = faixa_modelo.confianca if faixa_modelo else "BAIXA"

        edge = (prob_modelo - preco_compra) * 100
        retorno = (1.0 / preco_compra) if preco_compra > 0 else 0.0

        analises.append(AnaliseEdge(
            faixa_grau=grau,
            prob_modelo=prob_modelo,
            prob_mercado=preco_compra,
            edge=edge,
            preco_compra=preco_compra,
            volume=volume,
            confianca=confianca,
            retorno=retorno,
        ))

    return analises
