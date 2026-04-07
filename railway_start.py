"""railway_start.py — Inicia Streamlit + coleta periodica na Railway.

Roda a coleta de dados em background (a cada 30min) enquanto
o Streamlit serve o dashboard na porta definida pela Railway.
"""
import asyncio
import logging
import os
import subprocess
import sys
import threading
import time

import schedule

from main import configurar_logging, executar_ciclo


def rodar_coleta() -> None:
    """Executa um ciclo de coleta."""
    try:
        asyncio.run(executar_ciclo())
    except Exception as e:
        logging.getLogger(__name__).error(f"Erro na coleta: {e}")


def loop_coleta() -> None:
    """Thread de coleta: roda imediato + a cada 30min."""
    logger = logging.getLogger(__name__)
    logger.info("Thread de coleta iniciada")

    # Primeira coleta imediata
    rodar_coleta()

    # Agendar a cada 30min
    schedule.every(30).minutes.do(rodar_coleta)

    while True:
        schedule.run_pending()
        time.sleep(30)


def main() -> None:
    configurar_logging()
    logger = logging.getLogger(__name__)

    # Iniciar coleta em background
    thread = threading.Thread(target=loop_coleta, daemon=True)
    thread.start()
    logger.info("Coleta periodica iniciada em background")

    # Iniciar Streamlit
    porta = os.environ.get("PORT", "8501")
    logger.info(f"Iniciando Streamlit na porta {porta}")

    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "dashboard/app.py",
        "--server.port", porta,
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ])


if __name__ == "__main__":
    main()
