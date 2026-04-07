"""agendar.py — Agendador que roda o ciclo WeatherEdge a cada 6h.

Uso:
    py agendar.py          # roda agendador em loop infinito
    py agendar.py --agora  # roda um ciclo imediato e sai
"""
import argparse
import asyncio
import logging
import time

import schedule

from main import configurar_logging, executar_ciclo_completo


def rodar_ciclo() -> None:
    """Wrapper sincrono que roda o ciclo async."""
    asyncio.run(executar_ciclo_completo())


def main() -> None:
    """Entry point do agendador."""
    configurar_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="WeatherEdge — Agendador")
    parser.add_argument("--agora", action="store_true", help="Roda um ciclo imediato e sai")
    args = parser.parse_args()

    if args.agora:
        logger.info("Rodando ciclo imediato...")
        rodar_ciclo()
        return

    schedule.every().day.at("00:00").do(rodar_ciclo)
    schedule.every().day.at("06:00").do(rodar_ciclo)
    schedule.every().day.at("12:00").do(rodar_ciclo)
    schedule.every().day.at("18:00").do(rodar_ciclo)

    logger.info("WeatherEdge agendador iniciado. Ciclos: 00:00, 06:00, 12:00, 18:00 UTC")
    logger.info("Rodando primeiro ciclo agora...")
    rodar_ciclo()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
