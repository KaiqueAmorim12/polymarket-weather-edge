"""agendar.py — Agendador WeatherEdge v2.

Uso:
    py agendar.py          # roda agendador a cada 30min
    py agendar.py --agora  # roda um ciclo imediato e sai
"""
import argparse
import asyncio
import logging
import time

import schedule

from main import configurar_logging, executar_ciclo


def rodar_ciclo() -> None:
    asyncio.run(executar_ciclo())


def main() -> None:
    configurar_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="WeatherEdge v2 — Agendador")
    parser.add_argument("--agora", action="store_true", help="Roda um ciclo imediato e sai")
    args = parser.parse_args()

    if args.agora:
        logger.info("Rodando ciclo imediato...")
        rodar_ciclo()
        return

    schedule.every(30).minutes.do(rodar_ciclo)

    logger.info("WeatherEdge v2 agendador iniciado. Ciclos a cada 30 minutos.")
    logger.info("Rodando primeiro ciclo agora...")
    rodar_ciclo()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
