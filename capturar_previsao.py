"""capturar_previsao.py — Captura previsao de maxima as 6h local de cada cidade.

Uso:
    py capturar_previsao.py           # detecta hora UTC atual e processa cidades correspondentes
    py capturar_previsao.py --todas   # captura de TODAS as cidades (forcar)
"""
import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from banco import criar_tabelas, Repositorio
from coletores.wu_api import ColetorWU

RAIZ = Path(__file__).parent
CAMINHO_CIDADES = RAIZ / "config" / "cidades.json"
CAMINHO_LOG = RAIZ / "logs" / "weather_edge.log"

# Mapeamento: hora UTC -> lista de cidades que estao as 6h local
# Baseado em fuso_offset: 6h local = (6 - fuso_offset) % 24 UTC
GATILHOS_UTC = {
    18: ["Wellington"],
    21: ["Seoul", "Tokyo", "Busan"],
    22: ["Shanghai", "Hong Kong", "Beijing", "Chongqing", "Taipei", "Singapore", "Kuala Lumpur"],
    23: ["Jakarta"],
    1:  ["Lucknow"],  # UTC+5.5 -> 6-5.5=0.5 -> arredonda pra 1h UTC
    3:  ["Moscow", "Ankara", "Istanbul", "Tel Aviv", "Helsinki"],
    4:  ["Warsaw", "Paris", "Amsterdam", "Madrid", "Milan"],
    5:  ["London"],
    9:  ["Sao Paulo", "Buenos Aires"],
    10: ["Toronto", "NYC", "Miami"],
    11: ["Panama", "Chicago"],
    12: ["Mexico City", "Denver"],
    13: ["Seattle"],
}


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


def cidades_para_hora_utc(hora_utc: int) -> list[str]:
    """Retorna lista de nomes de cidades que estao as 6h local nesta hora UTC."""
    return GATILHOS_UTC.get(hora_utc, [])


async def capturar_previsao_cidades(nomes_cidades: list[str]) -> None:
    """Captura previsao de maxima pra lista de cidades."""
    logger = logging.getLogger(__name__)

    criar_tabelas()
    repo = Repositorio()
    todas_cidades = carregar_cidades()
    coletor = ColetorWU()

    for nome in nomes_cidades:
        cidade = next((c for c in todas_cidades if c["nome"] == nome), None)
        if not cidade:
            logger.warning(f"Cidade {nome} nao encontrada no config")
            continue

        previsoes = await coletor.coletar_previsao(
            latitude=cidade.get("latitude", 0),
            longitude=cidade.get("longitude", 0),
            unidade=cidade["unidade"],
        )

        if not previsoes:
            logger.warning(f"  {nome}: previsao nao disponivel")
            continue

        # Calcular data local atual da cidade
        agora_utc = datetime.now(timezone.utc)
        data_local = (agora_utc + timedelta(hours=cidade["fuso_offset"])).strftime("%Y-%m-%d")

        # Salvar SO a previsao do dia atual local (nao D+1)
        if not repo.buscar_previsao(nome, data_local):
            prev_hoje = next((p for p in previsoes if p["data_local"] == data_local), None)
            if prev_hoje:
                agora_str = agora_utc.isoformat()[:16]
                repo.salvar_previsao(nome, data_local, prev_hoje["temp_max"], cidade["unidade"], agora_str)
                logger.info(f"  {nome}: previsao {data_local} = {prev_hoje['temp_max']}{cidade['unidade']} (captura 6h local)")
            else:
                logger.warning(f"  {nome}: API nao retornou previsao pra {data_local}")


async def main_async(todas: bool = False) -> None:
    logger = logging.getLogger(__name__)

    if todas:
        logger.info("=== Captura de previsao: TODAS as cidades ===")
        todas_cidades = carregar_cidades()
        nomes = [c["nome"] for c in todas_cidades]
    else:
        hora_utc = datetime.now(timezone.utc).hour
        nomes = cidades_para_hora_utc(hora_utc)
        if not nomes:
            logger.info(f"Hora UTC {hora_utc:02d}:00 — nenhuma cidade com 6h local agora. Nada a fazer.")
            return
        logger.info(f"=== Captura de previsao: {hora_utc:02d}:00 UTC — {len(nomes)} cidades as 6h local ===")
        logger.info(f"Cidades: {', '.join(nomes)}")

    await capturar_previsao_cidades(nomes)
    logger.info("=== Captura de previsao concluida ===")


def main() -> None:
    configurar_logging()
    parser = argparse.ArgumentParser(description="WeatherEdge — Captura de previsao 6h local")
    parser.add_argument("--todas", action="store_true", help="Captura de TODAS as cidades")
    args = parser.parse_args()
    asyncio.run(main_async(todas=args.todas))


if __name__ == "__main__":
    main()
