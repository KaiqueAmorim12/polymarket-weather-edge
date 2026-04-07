"""main.py — Orquestrador principal do WeatherEdge.

Executa o ciclo completo:
1. Coleta previsoes de multiplas fontes meteorologicas
2. Calcula distribuicao de probabilidade por faixa
3. Busca odds da Polymarket
4. Calcula edge e gera recomendacoes
5. Salva tudo no banco
"""
import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import os

from banco import criar_tabelas, Repositorio
from coletores import coletar_todas_fontes
from modelo import calcular_distribuicao, PESOS_PADRAO
from polymarket import PolymarketConector
from comparador import calcular_edge, gerar_recomendacoes, classificar_estrelas

RAIZ = Path(__file__).parent
CAMINHO_DB = RAIZ / "dados" / "weather_edge.db"
CAMINHO_CIDADES = RAIZ / "config" / "cidades.json"
CAMINHO_CONFIG = RAIZ / "config" / "config.json"
CAMINHO_LOG = RAIZ / "logs" / "weather_edge.log"


def configurar_logging() -> None:
    """Configura logging pra console e arquivo."""
    CAMINHO_LOG.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(str(CAMINHO_LOG), encoding="utf-8"),
        ],
    )


def carregar_cidades() -> list[dict[str, Any]]:
    """Carrega configuracao das 10 cidades."""
    with open(CAMINHO_CIDADES, encoding="utf-8") as f:
        dados = json.load(f)
    return dados["cidades"]


def carregar_config() -> dict[str, Any]:
    """Carrega configuracao geral."""
    with open(CAMINHO_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def carregar_chaves() -> dict[str, str]:
    """Carrega chaves de API do .env."""
    load_dotenv(RAIZ / ".env")
    return {
        "OPENWEATHERMAP_API_KEY": os.getenv("OPENWEATHERMAP_API_KEY", ""),
        "ACCUWEATHER_API_KEY": os.getenv("ACCUWEATHER_API_KEY", ""),
        "VISUAL_CROSSING_API_KEY": os.getenv("VISUAL_CROSSING_API_KEY", ""),
    }


def calcular_datas_alvo(hoje: date | None = None) -> tuple[str, str]:
    """Calcula datas D-1 (amanha) e D-2 (depois de amanha)."""
    if hoje is None:
        hoje = date.today()
    d1 = (hoje + timedelta(days=1)).isoformat()
    d2 = (hoje + timedelta(days=2)).isoformat()
    return d1, d2


async def executar_ciclo_cidade(
    cidade: dict[str, Any],
    data_alvo: str,
    horizonte: str,
    chaves: dict[str, str],
    config: dict[str, Any],
    repo: Repositorio,
) -> None:
    """Executa ciclo completo pra uma cidade/data/horizonte."""
    logger = logging.getLogger(__name__)
    nome = cidade["nome"]
    logger.info(f"--- {nome} | {data_alvo} | {horizonte} ---")

    # 1. Coletar previsoes
    repo.limpar_previsoes_antigas(nome, data_alvo)
    resultado_coleta = await coletar_todas_fontes(
        cidade=nome,
        latitude=cidade["latitude"],
        longitude=cidade["longitude"],
        data_alvo=data_alvo,
        estacao_resolucao=cidade["estacao_resolucao"],
        chaves=chaves,
    )

    if not resultado_coleta.sucesso():
        logger.warning(f"{nome}: coleta falhou — {resultado_coleta.erros}")
        return

    for prev in resultado_coleta.previsoes:
        repo.salvar_previsao(
            cidade=nome,
            data_alvo=data_alvo,
            horizonte=horizonte,
            fonte=prev.fonte,
            temperatura_max=prev.temperatura_max,
            temperatura_min=prev.temperatura_min,
            coletado_em=prev.coletado_em.isoformat(),
        )

    # 2. Calcular distribuicao
    pesos = config.get("modelo", {}).get("pesos_fontes", PESOS_PADRAO)
    repo.limpar_distribuicoes_antigas(nome, data_alvo, horizonte)
    distribuicao = calcular_distribuicao(
        previsoes=resultado_coleta.previsoes,
        pesos=pesos,
        horizonte=horizonte,
    )

    for faixa in distribuicao:
        repo.salvar_distribuicao(
            cidade=nome,
            data_alvo=data_alvo,
            horizonte=horizonte,
            faixa_grau=faixa.grau,
            probabilidade=faixa.probabilidade,
            media=faixa.media,
            desvio_padrao=faixa.desvio_padrao,
            confianca=faixa.confianca,
        )

    # 3. Buscar odds da Polymarket
    conector = PolymarketConector()
    nome_poly = cidade.get("nome_polymarket", nome)
    odds = await conector.buscar_odds(nome_poly, data_alvo)

    if not odds:
        logger.warning(f"{nome}: nenhuma odd encontrada na Polymarket")
        return

    agora = datetime.now(timezone.utc).isoformat()
    for odd in odds:
        repo.salvar_odds(
            cidade=nome,
            data_alvo=data_alvo,
            faixa_grau=odd["faixa_grau"],
            probabilidade_mercado=odd["probabilidade_mercado"],
            preco_compra=odd["preco_compra"],
            preco_venda=odd["preco_venda"],
            volume=odd["volume"],
            coletado_em=agora,
        )

    # 4. Calcular edge
    analises = calcular_edge(distribuicao, odds)
    recomendacoes = gerar_recomendacoes(analises, horizonte)

    for a in analises:
        estrelas = classificar_estrelas(a.edge, a.confianca, a.retorno)
        recomendacao = "COMPRAR" if a in recomendacoes else "NAO"
        repo.salvar_analise(
            cidade=nome,
            data_alvo=data_alvo,
            horizonte=horizonte,
            faixa_grau=a.faixa_grau,
            prob_modelo=a.prob_modelo,
            prob_mercado=a.prob_mercado,
            edge=a.edge,
            recomendacao=recomendacao,
            estrelas=estrelas,
        )

    for r in recomendacoes:
        estrelas = classificar_estrelas(r.edge, r.confianca, r.retorno)
        simbolo = "+" * estrelas + "-" * (5 - estrelas)
        logger.info(
            f"  [{simbolo}] {nome} {data_alvo} {horizonte} | "
            f"{r.faixa_grau}C | edge +{r.edge:.1f} pts | "
            f"modelo {r.prob_modelo:.0%} vs mercado {r.prob_mercado:.0%} | "
            f"retorno {r.retorno:.1f}x"
        )

    if not recomendacoes:
        logger.info(f"  {nome}: sem oportunidades com edge suficiente")


async def executar_ciclo_completo() -> None:
    """Executa ciclo completo pra todas as cidades, D-1 e D-2."""
    logger = logging.getLogger(__name__)

    CAMINHO_DB.parent.mkdir(parents=True, exist_ok=True)
    criar_tabelas(str(CAMINHO_DB))
    repo = Repositorio(str(CAMINHO_DB))
    cidades = carregar_cidades()
    config = carregar_config()
    chaves = carregar_chaves()

    d1, d2 = calcular_datas_alvo()
    logger.info(f"=== WeatherEdge — Ciclo {datetime.now(timezone.utc).isoformat()} ===")
    logger.info(f"D-1: {d1} | D-2: {d2}")

    for cidade in cidades:
        for data_alvo, horizonte in [(d1, "D-1"), (d2, "D-2")]:
            try:
                await executar_ciclo_cidade(
                    cidade=cidade,
                    data_alvo=data_alvo,
                    horizonte=horizonte,
                    chaves=chaves,
                    config=config,
                    repo=repo,
                )
            except Exception as e:
                logger.error(f"Erro em {cidade['nome']} ({data_alvo} {horizonte}): {e}")

    logger.info("=== Ciclo completo ===")


if __name__ == "__main__":
    configurar_logging()
    asyncio.run(executar_ciclo_completo())
