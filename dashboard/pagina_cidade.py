"""Pagina de detalhe da cidade — curva de temperatura + odds Polymarket."""
from datetime import date, timedelta

import streamlit as st

from banco import Repositorio
from dashboard.componentes import grafico_curva_temperatura, grafico_odds_barras


def mostrar_detalhe_cidade(repo: Repositorio, cidades: list[dict], nome_cidade: str) -> None:
    if st.button("Voltar ao Monitor"):
        del st.session_state["cidade_detalhe"]
        st.rerun()

    cidade = next((c for c in cidades if c["nome"] == nome_cidade), None)
    if not cidade:
        st.error(f"Cidade {nome_cidade} nao encontrada")
        return

    unidade = cidade["unidade"]
    hoje = date.today().isoformat()

    st.title(f"{nome_cidade}")
    st.caption(f"Estacao: {cidade['estacao_wu']} | Unidade: {unidade} | Fuso: UTC{cidade['fuso_offset']:+g}")

    leituras = repo.buscar_leituras(nome_cidade, hoje)

    col_curva, col_odds = st.columns([3, 2])

    with col_curva:
        st.subheader("Curva de Temperatura - Hoje")
        if leituras:
            horas = [l["hora_local"] for l in leituras]
            temps = [l["temperatura"] for l in leituras]
            pico = max(leituras, key=lambda l: l["temperatura"])

            fig = grafico_curva_temperatura(
                horas=horas, temperaturas=temps, unidade=unidade,
                pico_hora=pico["hora_local"], pico_temp=pico["temperatura"],
            )
            st.plotly_chart(fig, use_container_width=True)

            col_i1, col_i2, col_i3 = st.columns(3)
            with col_i1:
                st.metric("Temperatura Atual", f"{temps[-1]} {unidade}")
            with col_i2:
                st.metric("Pico do Dia", f"{pico['temperatura']} {unidade} ({pico['hora_local']})")
            with col_i3:
                if len(leituras) >= 2:
                    diff = leituras[-1]["temperatura"] - leituras[-2]["temperatura"]
                    status = "Subindo" if diff > 0 else "Descendo" if diff < 0 else "Estavel"
                else:
                    status = "Sem dados"
                st.metric("Status", status)
        else:
            st.info("Sem leituras para hoje. Execute main.py para coletar dados.")

    with col_odds:
        data_amanha = (date.today() + timedelta(days=1)).isoformat()
        st.subheader(f"Odds Polymarket - {data_amanha}")
        odds = repo.buscar_odds_mais_recentes(nome_cidade, data_amanha)

        if not odds:
            # Tentar odds de hoje
            odds = repo.buscar_odds_mais_recentes(nome_cidade, hoje)
            if odds:
                st.caption("(Odds de hoje)")

        if odds:
            faixas_lista = [o["faixa"] for o in odds]
            precos = [o["preco_compra"] for o in odds]
            fig_odds = grafico_odds_barras(faixas_lista, precos)
            st.plotly_chart(fig_odds, use_container_width=True)

            st.dataframe(
                [{"Faixa": o["faixa"], "Odd": f"{o['preco_compra']:.1%}", "Volume": f"${o['volume']:,.0f}"} for o in odds],
                use_container_width=True,
            )
        else:
            st.info("Sem odds disponiveis.")

    # Historico 7 dias
    st.subheader("Historico (ultimos 7 dias)")
    for delta in range(1, 8):
        dia = (date.today() - timedelta(days=delta)).isoformat()
        leituras_dia = repo.buscar_leituras(nome_cidade, dia)
        if leituras_dia:
            pico_dia = max(leituras_dia, key=lambda l: l["temperatura"])
            minima_dia = min(leituras_dia, key=lambda l: l["temperatura"])
            st.caption(
                f"{dia}: Max {pico_dia['temperatura']}{unidade} ({pico_dia['hora_local']}) | "
                f"Min {minima_dia['temperatura']}{unidade} ({minima_dia['hora_local']})"
            )
