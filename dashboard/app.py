"""Dashboard WeatherEdge v2 — Monitor de Temperatura em Tempo Real."""
import sys
import json
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from banco import Repositorio, criar_tabelas
from dashboard.estilos import CSS

RAIZ = Path(__file__).parent.parent
CAMINHO_DB = RAIZ / "dados" / "weather_edge.db"
CAMINHO_CIDADES = RAIZ / "config" / "cidades.json"

st.set_page_config(page_title="WeatherEdge", page_icon="W", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


def carregar_cidades() -> list[dict]:
    with open(CAMINHO_CIDADES, encoding="utf-8") as f:
        return json.load(f)["cidades"]


def inicializar() -> Repositorio:
    CAMINHO_DB.parent.mkdir(parents=True, exist_ok=True)
    criar_tabelas(str(CAMINHO_DB))
    return Repositorio(str(CAMINHO_DB))


def tela_principal(repo: Repositorio, cidades: list[dict]) -> None:
    st.title("WeatherEdge")
    st.caption("Monitor de Temperatura em Tempo Real — Weather Underground + Polymarket")

    hoje = date.today().isoformat()

    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        regiao = st.selectbox("Regiao", ["Todas", "Asia", "Europa", "Americas", "Oceania"])
    with col_f2:
        ordenar = st.selectbox("Ordenar por", ["Horario BRT", "Temperatura", "Nome"])
    with col_f3:
        st.write("")
        st.write("")
        if st.button("Atualizar"):
            st.rerun()

    cidades_filtradas = cidades
    if regiao != "Todas":
        cidades_filtradas = [c for c in cidades if c["regiao"] == regiao]

    if ordenar == "Horario BRT":
        cidades_filtradas = sorted(cidades_filtradas, key=lambda c: c["fuso_offset"], reverse=True)
    elif ordenar == "Nome":
        cidades_filtradas = sorted(cidades_filtradas, key=lambda c: c["nome"])

    st.subheader("Cidades Monitoradas")

    for i in range(0, len(cidades_filtradas), 4):
        cols = st.columns(4)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(cidades_filtradas):
                break
            cidade = cidades_filtradas[idx]
            nome = cidade["nome"]
            unidade = cidade["unidade"]
            leituras = repo.buscar_leituras(nome, hoje)

            with col:
                with st.container(border=True):
                    if leituras:
                        temp_atual = leituras[-1]["temperatura"]
                        pico = max(leituras, key=lambda l: l["temperatura"])
                        if len(leituras) >= 2:
                            diff = leituras[-1]["temperatura"] - leituras[-2]["temperatura"]
                            seta = "^" if diff > 0 else "v" if diff < 0 else "="
                            status = "Subindo" if diff > 0 else "Descendo" if diff < 0 else "Estavel"
                        else:
                            seta = ""
                            status = ""

                        st.markdown(f"**{nome}** ({unidade})")
                        st.markdown(f"### {temp_atual} {seta}")
                        st.caption(f"Pico: {pico['temperatura']} as {pico['hora_local']} | {status}")

                        if st.button(f"Ver detalhes", key=f"det_{nome}"):
                            st.session_state["cidade_detalhe"] = nome
                            st.rerun()
                    else:
                        st.markdown(f"**{nome}** ({unidade})")
                        st.markdown("### --")
                        st.caption("Sem dados. Execute main.py")


# --- Main ---
repo = inicializar()
cidades = carregar_cidades()

pagina = st.sidebar.radio("Navegacao", ["Monitor", "Apostas"])

if pagina == "Apostas":
    from dashboard.pagina_apostas import mostrar_apostas
    mostrar_apostas(repo, cidades)
elif "cidade_detalhe" in st.session_state:
    from dashboard.pagina_cidade import mostrar_detalhe_cidade
    mostrar_detalhe_cidade(repo, cidades, st.session_state["cidade_detalhe"])
else:
    tela_principal(repo, cidades)
