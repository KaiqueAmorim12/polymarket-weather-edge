"""Simulador — calcula lucro/prejuizo pra diferentes estrategias de aposta."""


def simular_estrategia(
    faixas: list[int],
    precos: list[float],
    probabilidades: list[float],
    valor_total: float,
    estrategia: str = "espalhada",
) -> dict:
    """Simula uma estrategia de aposta e retorna metricas."""
    n = len(faixas)
    if n == 0:
        return {"custo_total": 0, "valor_esperado": 0}

    if estrategia == "concentrada":
        pesos = [1.0] + [0.0] * (n - 1)
    elif estrategia == "equilibrada" and n >= 3:
        pesos = [0.60, 0.25, 0.15] + [0.0] * (n - 3)
    elif estrategia == "equilibrada" and n == 2:
        pesos = [0.70, 0.30]
    else:
        pesos = [1.0 / n] * n

    resultado: dict = {
        "estrategia": estrategia,
        "custo_total": valor_total,
        "faixas": [],
    }

    valor_esperado = 0.0

    for i in range(n):
        valor_faixa = valor_total * pesos[i]
        preco = precos[i]
        prob = probabilidades[i]

        if preco <= 0 or valor_faixa <= 0:
            continue

        acoes = valor_faixa / preco
        retorno_bruto = acoes * 1.0
        lucro = retorno_bruto - valor_total

        resultado[f"lucro_se_acerta_{faixas[i]}"] = round(lucro, 2)
        resultado["faixas"].append({
            "grau": faixas[i],
            "valor_investido": round(valor_faixa, 2),
            "acoes": round(acoes, 1),
            "lucro_se_acerta": round(lucro, 2),
        })

        valor_esperado += prob * retorno_bruto

    resultado["valor_esperado"] = round(valor_esperado - valor_total, 2)
    resultado["pior_cenario"] = round(-valor_total, 2)

    return resultado
