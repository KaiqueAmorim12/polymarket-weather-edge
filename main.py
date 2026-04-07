"""main.py — Orquestrador WeatherEdge v2.

Ciclo simplificado:
1. Para cada cidade: busca leituras hora a hora do WU API
2. Para cada cidade: busca odds da Polymarket
3. Salva tudo no banco
"""
import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from banco import criar_tabelas, Repositorio
from coletores import ColetorWU
from polymarket import PolymarketConector

RAIZ = Path(__file__).parent
CAMINHO_DB = RAIZ / "dados" / "weather_edge.db"
CAMINHO_CIDADES = RAIZ / "config" / "cidades.json"
CAMINHO_LOG = RAIZ / "logs" / "weather_edge.log"


def configurar_logging() -> None:
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
    with open(CAMINHO_CIDADES, encoding="utf-8") as f:
        return json.load(f)["cidades"]


def calcular_data_hoje(hoje: date | None = None) -> str:
    if hoje is None:
        hoje = date.today()
    return hoje.isoformat()


async def coletar_cidade(
    cidade: dict[str, Any], data_alvo: str, repo: Repositorio,
) -> None:
    logger = logging.getLogger(__name__)
    nome = cidade["nome"]

    # 1. Leituras WU hora a hora
    coletor = ColetorWU()
    repo.limpar_leituras(nome, data_alvo)
    leituras = await coletor.coletar_dia(
        estacao=cidade["estacao_wu"],
        data_alvo=data_alvo,
        unidade=cidade["unidade"],
        fuso_offset=cidade["fuso_offset"],
    )

    for leitura in leituras:
        repo.salvar_leitura(
            cidade=nome, data_alvo=data_alvo, timestamp=leitura.timestamp,
            temperatura=leitura.temperatura, hora_utc=leitura.hora_utc,
            hora_local=leitura.hora_local, unidade=leitura.unidade,
        )

    if leituras:
        pico = coletor._calcular_pico(leituras)
        status = coletor._calcular_status(leituras)
        logger.info(
            f"  {nome}: {len(leituras)} leituras | "
            f"atual {leituras[-1].temperatura}{cidade['unidade']} | "
            f"pico {pico['temperatura']}{cidade['unidade']} as {pico['hora_local']} | {status}"
        )
    else:
        logger.warning(f"  {nome}: sem leituras")

    # 1.5 Capturar previsao de maxima (se ainda nao tem pra hoje)
    previsao_existente = repo.buscar_previsao(nome, data_alvo)
    if not previsao_existente:
        temp_prevista = await coletor.coletar_previsao(
            latitude=cidade.get("latitude", 0),
            longitude=cidade.get("longitude", 0),
            unidade=cidade["unidade"],
        )
        if temp_prevista is not None:
            agora = datetime.now(timezone.utc).isoformat()[:16]
            repo.salvar_previsao(nome, data_alvo, temp_prevista, cidade["unidade"], agora)
            logger.info(f"  {nome}: previsao maxima = {temp_prevista}{cidade['unidade']}")
        else:
            logger.debug(f"  {nome}: previsao nao disponivel")

    # 2. Odds Polymarket (dia atual e amanha)
    conector = PolymarketConector()
    for delta in [0, 1]:
        data_odds = (datetime.strptime(data_alvo, "%Y-%m-%d").date() + timedelta(days=delta)).isoformat()
        odds = await conector.buscar_odds(cidade["slug_poly"], data_odds)
        if odds:
            repo.limpar_odds(nome, data_odds)
            agora = datetime.now(timezone.utc).isoformat()
            for odd in odds:
                faixa_texto = str(odd.get("faixa_grau", ""))
                repo.salvar_odds(
                    cidade=nome, data_alvo=data_odds, faixa=faixa_texto,
                    preco_compra=odd["preco_compra"], volume=odd["volume"],
                    coletado_em=agora,
                )
            logger.info(f"  {nome}: {len(odds)} odds Polymarket pra {data_odds}")


async def executar_ciclo() -> None:
    logger = logging.getLogger(__name__)
    CAMINHO_DB.parent.mkdir(parents=True, exist_ok=True)
    criar_tabelas(str(CAMINHO_DB))
    repo = Repositorio(str(CAMINHO_DB))
    cidades = carregar_cidades()
    data_hoje = calcular_data_hoje()

    logger.info(f"=== WeatherEdge v2 — {datetime.now(timezone.utc).isoformat()} ===")
    logger.info(f"Data: {data_hoje} | Cidades: {len(cidades)}")

    for cidade in cidades:
        try:
            await coletar_cidade(cidade, data_hoje, repo)
        except Exception as e:
            logger.error(f"Erro em {cidade['nome']}: {e}")

    logger.info("=== Ciclo completo ===")


if __name__ == "__main__":
    configurar_logging()
    asyncio.run(executar_ciclo())
