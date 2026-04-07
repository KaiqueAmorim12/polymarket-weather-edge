"""exportar_json.py — Exporta resultados do banco SQLite pra JSON.

Usado pelo GitHub Actions pra persistir resultados no repo.
O Streamlit Cloud le esses JSONs pra mostrar o dashboard.
"""
import json
from datetime import date, timedelta
from pathlib import Path

from banco import criar_tabelas, Repositorio

RAIZ = Path(__file__).parent
CAMINHO_DB = RAIZ / "dados" / "weather_edge.db"
CAMINHO_RESULTADOS = RAIZ / "resultados"


def exportar() -> None:
    """Exporta analises e previsoes dos ultimos 7 dias pra JSON."""
    CAMINHO_RESULTADOS.mkdir(parents=True, exist_ok=True)
    criar_tabelas(str(CAMINHO_DB))
    repo = Repositorio(str(CAMINHO_DB))

    hoje = date.today()
    dados_exportados: dict = {
        "ultima_atualizacao": hoje.isoformat(),
        "analises_por_dia": {},
        "previsoes_por_dia": {},
        "resultados": {},
    }

    # Exportar ultimos 7 dias + proximos 2
    for delta in range(-7, 3):
        dia = (hoje + timedelta(days=delta)).isoformat()

        # Analises
        analises = repo.buscar_todas_analises_do_dia(dia)
        if analises:
            dados_exportados["analises_por_dia"][dia] = analises

        # Resultados reais
        cidades = [
            "London", "New York", "Hong Kong", "Istanbul", "Moscow",
            "Paris", "Seoul", "Tokyo", "Chicago", "Madrid",
        ]
        for cidade in cidades:
            resultado = repo.buscar_resultado(cidade, dia)
            if resultado:
                chave = f"{cidade}_{dia}"
                dados_exportados["resultados"][chave] = resultado

            # Previsoes
            previsoes = repo.buscar_previsoes(cidade, dia)
            if previsoes:
                chave = f"{cidade}_{dia}"
                dados_exportados["previsoes_por_dia"][chave] = previsoes

    # Performance geral
    performance = repo.buscar_performance()
    dados_exportados["performance"] = performance

    # Salvar JSON
    caminho_json = CAMINHO_RESULTADOS / "dados_dashboard.json"
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(dados_exportados, f, ensure_ascii=False, indent=2, default=str)

    # Salvar tambem o resumo de oportunidades do dia
    d1 = (hoje + timedelta(days=1)).isoformat()
    d2 = (hoje + timedelta(days=2)).isoformat()
    oportunidades = []
    for dia in [d1, d2]:
        analises = repo.buscar_todas_analises_do_dia(dia)
        recs = [a for a in analises if a.get("recomendacao") == "COMPRAR"]
        for r in recs:
            oportunidades.append(r)

    resumo = {
        "data_execucao": hoje.isoformat(),
        "d1": d1,
        "d2": d2,
        "total_oportunidades": len(oportunidades),
        "oportunidades": oportunidades,
    }

    caminho_resumo = CAMINHO_RESULTADOS / "oportunidades_hoje.json"
    with open(caminho_resumo, "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2, default=str)

    print(f"Exportado: {len(oportunidades)} oportunidades, {len(dados_exportados['analises_por_dia'])} dias de analises")


if __name__ == "__main__":
    exportar()
