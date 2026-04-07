"""Componentes reutilizaveis do dashboard v2."""
import plotly.graph_objects as go


def grafico_curva_temperatura(
    horas: list[str],
    temperaturas: list[float],
    unidade: str,
    pico_hora: str = "",
    pico_temp: float = 0,
) -> go.Figure:
    """Grafico da curva de temperatura do dia."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=horas, y=temperaturas,
        fill="tozeroy",
        fillcolor="rgba(212, 160, 23, 0.1)",
        line=dict(color="#d4a017", width=2),
        mode="lines+markers",
        marker=dict(size=4, color="#d4a017"),
        name="Temperatura",
        hovertemplate="%{x}<br>%{y}" + unidade + "<extra></extra>",
    ))

    if pico_hora and pico_temp:
        fig.add_trace(go.Scatter(
            x=[pico_hora], y=[pico_temp],
            mode="markers+text",
            marker=dict(size=12, color="#22c55e", symbol="star"),
            text=[f"PICO {pico_temp}{unidade}"],
            textposition="top center",
            textfont=dict(color="#22c55e", size=11),
            showlegend=False,
        ))

    if horas and temperaturas:
        fig.add_trace(go.Scatter(
            x=[horas[-1]], y=[temperaturas[-1]],
            mode="markers+text",
            marker=dict(size=10, color="#d4a017", symbol="diamond"),
            text=[f"AGORA {temperaturas[-1]}{unidade}"],
            textposition="bottom center",
            textfont=dict(color="#d4a017", size=10),
            showlegend=False,
        ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#151c27",
        plot_bgcolor="#0d1117",
        height=400,
        margin=dict(l=40, r=20, t=30, b=40),
        xaxis_title="Hora Local",
        yaxis_title=f"Temperatura ({unidade})",
        xaxis=dict(gridcolor="rgba(136,146,164,0.1)"),
        yaxis=dict(gridcolor="rgba(136,146,164,0.1)"),
    )
    return fig


def grafico_odds_barras(
    faixas: list[str],
    odds: list[float],
) -> go.Figure:
    """Grafico de barras horizontais das odds."""
    cores = ["#d4a017" if o == max(odds) else "#c0c0c0" for o in odds]

    fig = go.Figure(go.Bar(
        y=faixas,
        x=[o * 100 for o in odds],
        orientation="h",
        marker_color=cores,
        text=[f"{o:.0%}" for o in odds],
        textposition="outside",
        textfont=dict(color="#e8edf5"),
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#151c27",
        plot_bgcolor="#0d1117",
        height=400,
        margin=dict(l=80, r=40, t=30, b=40),
        xaxis_title="Probabilidade (%)",
        yaxis=dict(autorange="reversed"),
    )
    return fig
