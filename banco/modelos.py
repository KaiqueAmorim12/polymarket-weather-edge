"""Criacao das tabelas SQLite do WeatherEdge v2."""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS leituras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cidade TEXT NOT NULL,
    data_alvo TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    temperatura REAL NOT NULL,
    hora_utc TEXT NOT NULL,
    hora_local TEXT NOT NULL,
    unidade TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS odds_polymarket (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cidade TEXT NOT NULL,
    data_alvo TEXT NOT NULL,
    faixa TEXT NOT NULL,
    preco_compra REAL NOT NULL,
    volume REAL NOT NULL,
    coletado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS apostas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cidade TEXT NOT NULL,
    data_alvo TEXT NOT NULL,
    faixa TEXT NOT NULL,
    tipo TEXT NOT NULL,
    odd REAL NOT NULL,
    valor REAL NOT NULL,
    horario_registro TEXT NOT NULL,
    resultado TEXT NOT NULL DEFAULT 'aguardando',
    pnl REAL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_leituras_cidade_data ON leituras(cidade, data_alvo);
CREATE INDEX IF NOT EXISTS idx_odds_cidade_data ON odds_polymarket(cidade, data_alvo);
CREATE INDEX IF NOT EXISTS idx_apostas_data ON apostas(data_alvo);
"""


def criar_tabelas(caminho_db: str) -> None:
    Path(caminho_db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho_db)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
