"""Pagina de historico e performance do modelo."""
import streamlit as st
import plotly.graph_objects as go

from banco import Repositorio


def tela_historico(repo: Repositorio) -> None:
    """Tela de performance — acuracia, ROI, erro por fonte."""
    st.subheader("Performance do Modelo")

    col_filtro1, col_filtro2 = st.columns(2)
    with col_filtro1:
        cidade_filtro = st.selectbox("Cidade", ["Todas"] + [
            "London", "New York", "Hong Kong", "Istanbul", "Moscow",
            "Paris", "Seoul", "Tokyo", "Chicago", "Madrid",
        ])
    with col_filtro2:
        horizonte_filtro = st.selectbox("Horizonte", ["Todos", "D-1", "D-2"])

    cidade_param = None if cidade_filtro == "Todas" else cidade_filtro
    horizonte_param = None if horizonte_filtro == "Todos" else horizonte_filtro

    performance = repo.buscar_performance(cidade=cidade_param, horizonte=horizonte_param)

    if not performance:
        st.info("Sem dados de performance ainda. O sistema precisa rodar por alguns dias.")
        return

    total = len(performance)
    acertos = sum(1 for p in performance if p["acertou_faixa"])
    acuracia = acertos / total if total > 0 else 0
    erro_medio = sum(abs(p["erro_graus"]) for p in performance) / total if total > 0 else 0
    lucro_total = sum(p["lucro_simulado"] for p in performance)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Acuracia (faixa exata)", f"{acuracia:.0%}")
    with col2:
        st.metric("Erro medio", f"{erro_medio:.1f}°C")
    with col3:
        st.metric("ROI simulado", f"${lucro_total:.2f}")
    with col4:
        st.metric("Total analises", str(total))

    if total > 5:
        datas = [p["data_alvo"] for p in performance]
        acertos_cumulativo = []
        acc = 0
        for i, p in enumerate(performance):
            acc += int(p["acertou_faixa"])
            acertos_cumulativo.append(acc / (i + 1))

        fig = go.Figure(go.Scatter(
            x=datas,
            y=[a * 100 for a in acertos_cumulativo],
            mode="lines+markers",
            name="Acuracia cumulativa",
            line=dict(color="#2ecc71"),
        ))
        fig.update_layout(
            yaxis_title="Acuracia (%)",
            template="plotly_dark",
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        [
            {
                "Data": p["data_alvo"],
                "Cidade": p["cidade"],
                "Horizonte": p["horizonte"],
                "Acertou": "SIM" if p["acertou_faixa"] else "NAO",
                "Erro": f"{p['erro_graus']:+.1f}°C",
                "Lucro sim.": f"${p['lucro_simulado']:+.2f}",
            }
            for p in performance
        ],
        use_container_width=True,
    )
