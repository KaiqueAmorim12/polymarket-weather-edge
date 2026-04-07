"""Dashboard WeatherEdge — tela principal Streamlit."""
import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from banco import Repositorio, criar_tabelas
from dashboard.componentes import estrelas_texto, grafico_distribuicao, grafico_edge

RAIZ = Path(__file__).parent.parent
CAMINHO_DB = RAIZ / "dados" / "weather_edge.db"

st.set_page_config(
    page_title="WeatherEdge",
    page_icon="W",
    layout="wide",
)


def inicializar_banco() -> Repositorio:
    """Inicializa banco se nao existir e retorna repositorio."""
    CAMINHO_DB.parent.mkdir(parents=True, exist_ok=True)
    criar_tabelas(str(CAMINHO_DB))
    return Repositorio(str(CAMINHO_DB))


def tela_principal(repo: Repositorio) -> None:
    """Tela principal — visao geral do dia."""
    st.title("WeatherEdge")
    st.caption("Sistema de Value Betting em Contratos de Clima da Polymarket")

    hoje = date.today()
    d1 = (hoje + timedelta(days=1)).isoformat()
    d2 = (hoje + timedelta(days=2)).isoformat()

    st.markdown(f"**D-1:** {d1} | **D-2:** {d2}")

    st.subheader("Oportunidades Encontradas")

    analises_d1 = repo.buscar_todas_analises_do_dia(d1)
    analises_d2 = repo.buscar_todas_analises_do_dia(d2)
    todas = analises_d1 + analises_d2

    recomendadas = [a for a in todas if a["recomendacao"] == "COMPRAR"]

    if not recomendadas:
        st.info("Nenhuma oportunidade encontrada. Execute main.py para coletar dados.")
    else:
        for rec in recomendadas:
            col1, col2, col3, col4, col5 = st.columns([1, 2, 1, 1, 1])
            with col1:
                st.write(estrelas_texto(rec["estrelas"]))
            with col2:
                st.write(f"**{rec['cidade']}** ({rec['data_alvo']})")
            with col3:
                horizonte = rec.get("horizonte", "D-1")
                st.write(f"`{horizonte}`")
            with col4:
                st.write(f"**{rec['faixa_grau']}°C** a {rec['prob_mercado']:.0%}")
            with col5:
                st.write(f"Edge **+{rec['edge']:.1f}** pts")

    st.subheader("Todas as Cidades")

    tab_d1, tab_d2 = st.tabs(["D-1 (Amanha)", "D-2 (Depois de amanha)"])

    for tab, analises, label in [(tab_d1, analises_d1, d1), (tab_d2, analises_d2, d2)]:
        with tab:
            if not analises:
                st.info(f"Sem dados para {label}. Execute main.py.")
                continue

            cidades_vistas: set[str] = set()
            for a in analises:
                cidade = a["cidade"]
                if cidade in cidades_vistas:
                    continue
                cidades_vistas.add(cidade)

                analises_cidade = [x for x in analises if x["cidade"] == cidade]
                melhor = max(analises_cidade, key=lambda x: x["edge"])

                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                with col1:
                    if st.button(f"Ver {cidade}", key=f"btn_{cidade}_{label}"):
                        st.session_state["cidade_detalhe"] = cidade
                        st.session_state["data_detalhe"] = label
                        st.rerun()
                with col2:
                    st.write(f"{melhor['faixa_grau']}°C")
                with col3:
                    cor = "+" if melhor["edge"] > 5 else "~" if melhor["edge"] > 0 else "-"
                    st.write(f"{cor} {melhor['edge']:+.1f}")
                with col4:
                    st.write(estrelas_texto(melhor["estrelas"]))
                with col5:
                    st.write(melhor["recomendacao"])


def tela_detalhe_cidade(repo: Repositorio, cidade: str, data_alvo: str) -> None:
    """Tela de detalhe — distribuicao e edge pra uma cidade."""
    st.subheader(f"{cidade} — {data_alvo}")

    if st.button("Voltar"):
        del st.session_state["cidade_detalhe"]
        st.rerun()

    for horizonte in ["D-1", "D-2"]:
        st.markdown(f"### {horizonte}")

        distribuicoes = repo.buscar_distribuicoes(cidade, data_alvo, horizonte)
        odds = repo.buscar_odds(cidade, data_alvo)
        analises = repo.buscar_analises(cidade, data_alvo, horizonte)

        if not distribuicoes:
            st.info(f"Sem dados {horizonte}")
            continue

        faixas_modelo = {d["faixa_grau"]: d["probabilidade"] for d in distribuicoes}
        faixas_mercado = {o["faixa_grau"]: o["preco_compra"] for o in odds}
        faixas_edge = {a["faixa_grau"]: a["edge"] for a in analises}

        todas_faixas = sorted(set(list(faixas_modelo.keys()) + list(faixas_mercado.keys())))

        prob_modelo = [faixas_modelo.get(f, 0) for f in todas_faixas]
        prob_mercado = [faixas_mercado.get(f, 0) for f in todas_faixas]
        edges = [faixas_edge.get(f, 0) for f in todas_faixas]

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(
                grafico_distribuicao(todas_faixas, prob_modelo, prob_mercado),
                use_container_width=True,
            )
        with col2:
            st.plotly_chart(
                grafico_edge(todas_faixas, edges),
                use_container_width=True,
            )

        if analises:
            st.dataframe(
                [
                    {
                        "Faixa": f"{a['faixa_grau']}°C",
                        "Modelo": f"{a['prob_modelo']:.0%}",
                        "Mercado": f"{a['prob_mercado']:.0%}",
                        "Edge": f"{a['edge']:+.1f}",
                        "Estrelas": estrelas_texto(a["estrelas"]),
                        "Rec": a["recomendacao"],
                    }
                    for a in analises
                ],
                use_container_width=True,
            )

        previsoes = repo.buscar_previsoes(cidade, data_alvo)
        previsoes_horizonte = [p for p in previsoes if p["horizonte"] == horizonte]
        if previsoes_horizonte:
            with st.expander("Fontes consultadas"):
                for p in previsoes_horizonte:
                    st.write(f"**{p['fonte']}**: {p['temperatura_max']}°C (coletado {p['coletado_em'][:16]})")


# --- Main ---

repo = inicializar_banco()

pagina = st.sidebar.radio("Navegacao", ["Oportunidades", "Historico"])

if pagina == "Historico":
    from dashboard.pagina_historico import tela_historico
    tela_historico(repo)
elif "cidade_detalhe" in st.session_state:
    tela_detalhe_cidade(
        repo,
        st.session_state["cidade_detalhe"],
        st.session_state.get("data_detalhe", ""),
    )
else:
    tela_principal(repo)
