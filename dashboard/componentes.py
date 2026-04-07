"""Componentes reutilizaveis do dashboard Streamlit."""
import plotly.graph_objects as go


def grafico_distribuicao(
    faixas: list[int],
    prob_modelo: list[float],
    prob_mercado: list[float],
) -> go.Figure:
    """Grafico de barras comparando modelo vs mercado."""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=[f"{g}°C" for g in faixas],
        y=[p * 100 for p in prob_modelo],
        name="Modelo",
        marker_color="#2ecc71",
    ))

    fig.add_trace(go.Bar(
        x=[f"{g}°C" for g in faixas],
        y=[p * 100 for p in prob_mercado],
        name="Polymarket",
        marker_color="#3498db",
    ))

    fig.update_layout(
        barmode="group",
        yaxis_title="Probabilidade (%)",
        xaxis_title="Temperatura",
        template="plotly_dark",
        height=400,
    )

    return fig


def grafico_edge(
    faixas: list[int],
    edges: list[float],
) -> go.Figure:
    """Grafico de barras do edge por faixa (verde = positivo, vermelho = negativo)."""
    cores = ["#2ecc71" if e > 0 else "#e74c3c" for e in edges]

    fig = go.Figure(go.Bar(
        x=[f"{g}°C" for g in faixas],
        y=edges,
        marker_color=cores,
    ))

    fig.update_layout(
        yaxis_title="Edge (pontos)",
        xaxis_title="Temperatura",
        template="plotly_dark",
        height=300,
    )

    return fig


def estrelas_texto(n: int) -> str:
    """Converte numero de estrelas em texto visual."""
    return "+" * n + "-" * (5 - n)
