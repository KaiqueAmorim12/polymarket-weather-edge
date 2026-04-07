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

    # Log diario de auditoria — arquivo separado por dia pra conferir manualmente
    exportar_log_auditoria(repo, hoje, d1, d2, oportunidades)


def exportar_log_auditoria(
    repo: Repositorio,
    hoje: date,
    d1: str,
    d2: str,
    oportunidades: list[dict],
) -> None:
    """Cria log de auditoria legivel pra conferencia humana.

    Salva em resultados/logs/YYYY-MM-DD.md pra facil leitura no GitHub.
    """
    pasta_logs = CAMINHO_RESULTADOS / "logs"
    pasta_logs.mkdir(parents=True, exist_ok=True)

    linhas: list[str] = []
    linhas.append(f"# WeatherEdge — Log de Auditoria {hoje.isoformat()}")
    linhas.append(f"")
    linhas.append(f"**Execucao:** {hoje.isoformat()} 18:00 BRT")
    linhas.append(f"**D-1:** {d1} | **D-2:** {d2}")
    linhas.append(f"")

    # Secao 1: Recomendacoes do dia
    linhas.append(f"## Recomendacoes ({len(oportunidades)} oportunidades)")
    linhas.append(f"")
    if oportunidades:
        linhas.append(f"| Cidade | Data | Horizonte | Faixa | Modelo | Mercado | Edge | Estrelas |")
        linhas.append(f"|--------|------|-----------|-------|--------|---------|------|----------|")
        for o in oportunidades:
            linhas.append(
                f"| {o['cidade']} | {o['data_alvo']} | {o['horizonte']} | "
                f"{o['faixa_grau']}C | {o['prob_modelo']:.0%} | {o['prob_mercado']:.0%} | "
                f"+{o['edge']:.1f} | {o['estrelas']} |"
            )
    else:
        linhas.append("Nenhuma oportunidade encontrada.")
    linhas.append(f"")

    # Secao 2: Verificacao de resultados de ontem
    ontem = (hoje - timedelta(days=1)).isoformat()
    linhas.append(f"## Resultados de Ontem ({ontem})")
    linhas.append(f"")

    cidades = [
        "London", "New York", "Hong Kong", "Istanbul", "Moscow",
        "Paris", "Seoul", "Tokyo", "Chicago", "Madrid",
    ]

    tem_resultado = False
    for cidade in cidades:
        resultado = repo.buscar_resultado(cidade, ontem)
        if resultado:
            if not tem_resultado:
                linhas.append(f"| Cidade | Temp Real | Faixa Vencedora | Fonte |")
                linhas.append(f"|--------|----------|-----------------|-------|")
                tem_resultado = True
            linhas.append(
                f"| {resultado['cidade']} | {resultado['temperatura_real']}C | "
                f"{resultado['faixa_vencedora']}C | {resultado['fonte_resolucao']} |"
            )

    if not tem_resultado:
        linhas.append("Sem resultados verificados ainda (sistema comeca a verificar apos 1 dia rodando).")
    linhas.append(f"")

    # Secao 3: Comparacao recomendacao vs resultado (se disponivel)
    linhas.append(f"## Performance — Comparacao Recomendacao vs Resultado")
    linhas.append(f"")

    performance = repo.buscar_performance()
    perf_ontem = [p for p in performance if p["data_alvo"] == ontem]

    if perf_ontem:
        linhas.append(f"| Cidade | Horizonte | Acertou | Erro | Lucro Simulado |")
        linhas.append(f"|--------|-----------|---------|------|----------------|")
        for p in perf_ontem:
            acertou = "SIM" if p["acertou_faixa"] else "NAO"
            linhas.append(
                f"| {p['cidade']} | {p['horizonte']} | {acertou} | "
                f"{p['erro_graus']:.0f}C | ${p['lucro_simulado']:+.2f} |"
            )
    else:
        linhas.append("Sem dados de performance ainda. Amanha tera a primeira comparacao.")
    linhas.append(f"")

    # Secao 4: Previsoes brutas (pra auditoria)
    linhas.append(f"## Previsoes Brutas por Fonte (D-1: {d1})")
    linhas.append(f"")
    for cidade in cidades:
        previsoes = repo.buscar_previsoes(cidade, d1)
        previsoes_d1 = [p for p in previsoes if p["horizonte"] == "D-1"]
        if previsoes_d1:
            linhas.append(f"**{cidade}:**")
            for p in previsoes_d1:
                linhas.append(f"- {p['fonte']}: {p['temperatura_max']}C (coletado {p['coletado_em'][:16]})")
            linhas.append(f"")

    # Salvar
    caminho_log = pasta_logs / f"{hoje.isoformat()}.md"
    with open(caminho_log, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    print(f"Log de auditoria salvo em {caminho_log}")


if __name__ == "__main__":
    exportar()
