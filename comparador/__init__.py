"""Modulo comparador — analise de edge, recomendacoes e simulacao."""
from comparador.edge import calcular_edge, AnaliseEdge
from comparador.recomendador import classificar_estrelas, gerar_recomendacoes
from comparador.simulador import simular_estrategia

__all__ = [
    "calcular_edge",
    "AnaliseEdge",
    "classificar_estrelas",
    "gerar_recomendacoes",
    "simular_estrategia",
]
