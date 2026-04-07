"""CSS customizado do dashboard WeatherEdge v2 — preto, dourado, prata."""

CSS = """
<style>
    .stApp { background-color: #080b12; color: #e8edf5; }
    .stApp header { background-color: #080b12; }
    .stSidebar > div { background-color: #0d1117; }

    div[data-testid="stMetric"] {
        background: #151c27;
        border: 1px solid rgba(136,146,164,0.06);
        border-radius: 10px;
        padding: 16px;
        border-top: 2px solid;
        border-image: linear-gradient(90deg, #d4a017, #c0c0c0) 1;
    }
    div[data-testid="stMetric"] label { color: #8892a4 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #d4a017 !important; }

    .stDataFrame { background: #151c27; border-radius: 10px; }

    .stButton > button {
        background: linear-gradient(135deg, #d4a017, #c0c0c0);
        color: #080b12;
        border: none;
        border-radius: 6px;
        font-weight: 700;
        transition: 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 20px rgba(212, 160, 23, 0.3);
    }

    .stSelectbox > div > div {
        background: #151c27;
        border: 1px solid rgba(136,146,164,0.06);
        color: #e8edf5;
    }

    .stTabs [data-baseweb="tab"] { color: #8892a4; }
    .stTabs [aria-selected="true"] { color: #d4a017 !important; border-bottom-color: #d4a017 !important; }
</style>
"""
