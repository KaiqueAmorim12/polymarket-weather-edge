"""Calculo de media ponderada das fontes meteorologicas."""
from coletores.base import Previsao

PESOS_PADRAO: dict[str, float] = {
    "ecmwf": 0.30,
    "gfs": 0.25,
    "wunderground": 0.20,
    "openweathermap": 0.10,
    "accuweather": 0.10,
    "visual_crossing": 0.05,
}


def media_ponderada(
    previsoes: list[Previsao],
    pesos: dict[str, float],
) -> float:
    """Calcula media ponderada das temperaturas maximas.

    Se uma fonte esta faltando, redistribui os pesos proporcionalmente.
    """
    soma_ponderada = 0.0
    soma_pesos = 0.0

    for prev in previsoes:
        peso = pesos.get(prev.fonte, 0.05)
        soma_ponderada += prev.temperatura_max * peso
        soma_pesos += peso

    if soma_pesos == 0:
        return sum(p.temperatura_max for p in previsoes) / len(previsoes)

    return soma_ponderada / soma_pesos
