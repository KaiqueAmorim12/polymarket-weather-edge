"""Criacao das tabelas SQLite do WeatherEdge."""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS previsoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cidade TEXT NOT NULL,
    data_alvo TEXT NOT NULL,
    horizonte TEXT NOT NULL,
    fonte TEXT NOT NULL,
    temperatura_max REAL NOT NULL,
    temperatura_min REAL NOT NULL,
    coletado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS distribuicoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cidade TEXT NOT NULL,
    data_alvo TEXT NOT NULL,
    horizonte TEXT NOT NULL,
    faixa_grau INTEGER NOT NULL,
    probabilidade REAL NOT NULL,
    media REAL NOT NULL,
    desvio_padrao REAL NOT NULL,
    confianca TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS odds_polymarket (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cidade TEXT NOT NULL,
    data_alvo TEXT NOT NULL,
    faixa_grau INTEGER NOT NULL,
    probabilidade_mercado REAL NOT NULL,
    preco_compra REAL NOT NULL,
    preco_venda REAL NOT NULL,
    volume REAL NOT NULL,
    coletado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cidade TEXT NOT NULL,
    data_alvo TEXT NOT NULL,
    horizonte TEXT NOT NULL,
    faixa_grau INTEGER NOT NULL,
    prob_modelo REAL NOT NULL,
    prob_mercado REAL NOT NULL,
    edge REAL NOT NULL,
    recomendacao TEXT NOT NULL,
    estrelas INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS resultados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cidade TEXT NOT NULL,
    data_alvo TEXT NOT NULL,
    temperatura_real REAL NOT NULL,
    faixa_vencedora INTEGER NOT NULL,
    fonte_resolucao TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cidade TEXT NOT NULL,
    data_alvo TEXT NOT NULL,
    horizonte TEXT NOT NULL,
    acertou_faixa INTEGER NOT NULL,
    erro_graus REAL NOT NULL,
    lucro_simulado REAL NOT NULL
);
"""


def criar_tabelas(caminho_db: str) -> None:
    """Cria todas as tabelas no banco SQLite."""
    Path(caminho_db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho_db)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
