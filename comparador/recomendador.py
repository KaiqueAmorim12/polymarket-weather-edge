"""Recomendador — classifica oportunidades e gera recomendacoes de aposta."""
from comparador.edge import AnaliseEdge

CRITERIOS = {
    "D-1": {"edge_min": 5, "confianca_min": "MEDIA", "retorno_min": 2.0, "liquidez_min": 1000},
    "D-2": {"edge_min": 8, "confianca_min": "ALTA", "retorno_min": 3.0, "liquidez_min": 1000},
}

NIVEL_CONFIANCA = {"BAIXA": 0, "MEDIA": 1, "ALTA": 2}


def classificar_estrelas(edge: float, confianca: str, retorno: float) -> int:
    """Classifica oportunidade de 1 a 5 estrelas."""
    nivel = NIVEL_CONFIANCA.get(confianca, 0)

    if edge >= 15 and nivel >= 2 and retorno >= 5.0:
        return 5
    if edge >= 10 and nivel >= 2:
        return 4
    if edge >= 7 and nivel >= 1:
        return 3
    if edge >= 5 and nivel >= 1:
        return 2
    return 1


def gerar_recomendacoes(
    analises: list[AnaliseEdge],
    horizonte: str,
) -> list[AnaliseEdge]:
    """Filtra analises que atendem os criterios do horizonte."""
    criterios = CRITERIOS.get(horizonte, CRITERIOS["D-1"])
    nivel_min = NIVEL_CONFIANCA.get(criterios["confianca_min"], 0)

    recomendadas = []
    for a in analises:
        nivel_a = NIVEL_CONFIANCA.get(a.confianca, 0)
        if (
            a.edge >= criterios["edge_min"]
            and nivel_a >= nivel_min
            and a.retorno >= criterios["retorno_min"]
            and a.volume >= criterios["liquidez_min"]
        ):
            recomendadas.append(a)

    return sorted(recomendadas, key=lambda a: a.edge, reverse=True)
