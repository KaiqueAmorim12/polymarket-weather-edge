"""Pagina de apostas — registro manual e historico de P&L."""
from datetime import date, datetime, timezone

import streamlit as st

from banco import Repositorio


def mostrar_apostas(repo: Repositorio, cidades: list[dict]) -> None:
    st.title("Minhas Apostas")

    # Formulario
    st.subheader("Registrar Nova Aposta")
    with st.form("form_aposta"):
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            tipo = st.selectbox("Tipo", ["YES", "NO"])
        with col2:
            nome_cidade = st.selectbox("Cidade", [c["nome"] for c in cidades])
        with col3:
            faixa = st.text_input("Faixa", placeholder="23C ou 78-79F")
        with col4:
            odd = st.number_input("Odd", min_value=0.01, max_value=0.99, value=0.24, step=0.01)
        with col5:
            valor = st.number_input("Valor ($)", min_value=0.10, max_value=1000.0, value=5.0, step=0.50)

        data_aposta = st.date_input("Data do contrato", value=date.today())
        submitted = st.form_submit_button("Registrar Aposta")

        if submitted and faixa:
            agora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            repo.registrar_aposta(
                cidade=nome_cidade, data_alvo=data_aposta.isoformat(),
                faixa=faixa, tipo=tipo, odd=odd, valor=valor, horario_registro=agora,
            )
            st.success(f"Aposta registrada: {tipo} {nome_cidade} {faixa} @ {odd:.2f} - ${valor:.2f}")

    # Metricas
    st.subheader("Performance")
    metricas = repo.calcular_metricas()
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Total Apostas", str(metricas["total_apostas"]))
    with col_m2:
        st.metric("Win Rate", f"{metricas['win_rate']:.0f}%")
    with col_m3:
        pnl = metricas["pnl_total"]
        st.metric("P&L Total", f"${pnl:+.2f}", delta=f"{pnl:+.2f}")
    with col_m4:
        st.metric("ROI", f"{metricas['roi']:+.1f}%")

    # Apostas de hoje
    hoje = date.today().isoformat()
    apostas_hoje = repo.buscar_apostas_do_dia(hoje)
    if apostas_hoje:
        st.subheader(f"Apostas de Hoje ({hoje})")
        for a in apostas_hoje:
            resultado = a["resultado"]
            icone = {"aguardando": "wait", "ganhou": "OK", "perdeu": "X"}.get(resultado, "?")
            pnl_str = f"${a['pnl']:+.2f}" if resultado != "aguardando" else "--"
            st.markdown(
                f"[{icone}] **{a['cidade']}** | {a['faixa']} | {a['tipo']} | "
                f"${a['valor']:.2f} @ {a['odd']:.2f} | {pnl_str}"
            )

    # Historico
    st.subheader("Historico Completo")
    historico = repo.buscar_historico_apostas()
    if historico:
        st.dataframe(
            [
                {
                    "Data": a["data_alvo"], "Cidade": a["cidade"], "Faixa": a["faixa"],
                    "Tipo": a["tipo"], "Valor": f"${a['valor']:.2f}", "Odd": f"{a['odd']:.2f}",
                    "Resultado": a["resultado"],
                    "P&L": f"${a['pnl']:+.2f}" if a["resultado"] != "aguardando" else "--",
                }
                for a in historico
            ],
            use_container_width=True,
        )
    else:
        st.info("Nenhuma aposta registrada ainda.")

    # Resolver apostas
    apostas_aguardando = [a for a in (historico or []) if a["resultado"] == "aguardando"]
    if apostas_aguardando:
        st.subheader("Resolver Apostas")
        st.caption("Marque como ganhou ou perdeu apos verificar o resultado no WU.")
        for a in apostas_aguardando:
            col_r1, col_r2, col_r3 = st.columns([3, 1, 1])
            with col_r1:
                st.write(f"{a['data_alvo']} | {a['cidade']} | {a['faixa']} | {a['tipo']} @ {a['odd']:.2f}")
            with col_r2:
                if st.button(f"Ganhou", key=f"g_{a['id']}"):
                    if a["tipo"] == "YES":
                        lucro = (1.0 / a["odd"] - 1) * a["valor"]
                    else:
                        lucro = (1.0 / (1 - a["odd"]) - 1) * a["valor"]
                    repo.resolver_aposta(a["id"], "ganhou", round(lucro, 2))
                    st.rerun()
            with col_r3:
                if st.button(f"Perdeu", key=f"p_{a['id']}"):
                    repo.resolver_aposta(a["id"], "perdeu", -a["valor"])
                    st.rerun()
