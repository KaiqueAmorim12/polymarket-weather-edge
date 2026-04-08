"""coletar_modelos.py — Coleta previsoes de 6 modelos meteorologicos e salva no Supabase."""
import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx

RAIZ = Path(__file__).parent
SUPABASE_URL = "https://wzjdthcxlsopmqcwtvla.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind6amR0aGN4bHNvcG1xY3d0dmxhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzUzNjY2MywiZXhwIjoyMDczMTEyNjYzfQ.ZRXuEULiCpkIYDhspjYd1dadql4AwMnygGzr6D6Ts0Q"
HEADERS_SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

# 6 modelos disponiveis no Open-Meteo
MODELOS = [
    "ecmwf_ifs025",
    "gfs_seamless",
    "icon_seamless",
    "ukmo_seamless",
    "jma_seamless",
    "gem_seamless",
]


def carregar_cidades() -> list[dict]:
    """Carrega lista de cidades do arquivo de configuracao."""
    with open(RAIZ / "config" / "cidades.json", encoding="utf-8") as f:
        return json.load(f)["cidades"]


async def coletar_modelo(client: httpx.AsyncClient, cidade: dict, modelo: str, data_local: str) -> dict | None:
    """Busca previsao de um modelo para uma cidade. Retorna registro ou None se falhar."""
    try:
        r = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": cidade["latitude"],
                "longitude": cidade["longitude"],
                "daily": "temperature_2m_max",
                "models": modelo,
                "forecast_days": 2,
            },
        )
        if r.status_code != 200:
            return None

        data = r.json()
        datas = data.get("daily", {}).get("time", [])
        maxs = data.get("daily", {}).get("temperature_2m_max", [])

        for i, d in enumerate(datas):
            if d == data_local and i < len(maxs) and maxs[i] is not None:
                val: float = maxs[i]
                # Converter Celsius para Fahrenheit se necessario
                if cidade["unidade"] == "F":
                    val = val * 9 / 5 + 32
                # Normalizar nome do modelo: "ecmwf_ifs025" -> "ECMWF", "gfs_seamless" -> "GFS"
                nome_modelo = modelo.replace("_seamless", "").replace("_ifs025", "").upper()
                return {
                    "cidade": cidade["nome"],
                    "data_alvo": data_local,
                    "modelo": nome_modelo,
                    "temp_max_prevista": round(val, 1),
                    "unidade": cidade["unidade"],
                    "hora_captura": datetime.now(timezone.utc).isoformat()[:16],
                }
    except Exception as e:
        logging.getLogger(__name__).warning(f"  {cidade['nome']} {modelo}: {e}")
    return None


async def coletar() -> None:
    """Coleta previsoes de todos os modelos para todas as cidades e salva no Supabase."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger(__name__)

    cidades = carregar_cidades()
    agora = datetime.now(timezone.utc)

    logger.info(f"=== Coleta de 6 modelos — {len(cidades)} cidades ===")

    registros: list[dict] = []

    # Semaforo para limitar requisicoes paralelas e nao sobrecarregar a API
    semaforo = asyncio.Semaphore(10)

    async def coletar_com_semaforo(client: httpx.AsyncClient, cidade: dict, modelo: str, data_local: str) -> dict | None:
        async with semaforo:
            return await coletar_modelo(client, cidade, modelo, data_local)

    async with httpx.AsyncClient(timeout=15) as client:
        # Criar todas as tasks em paralelo (cidade x modelo)
        tasks = []
        for cidade in cidades:
            # Calcular data local da cidade usando o fuso_offset
            data_local = (agora + timedelta(hours=cidade["fuso_offset"])).strftime("%Y-%m-%d")
            for modelo in MODELOS:
                tasks.append(coletar_com_semaforo(client, cidade, modelo, data_local))

        resultados = await asyncio.gather(*tasks)
        registros = [r for r in resultados if r is not None]

    logger.info(f"Coletadas {len(registros)} previsoes de {len(cidades) * len(MODELOS)} tentativas")

    # Deletar previsoes anteriores do mesmo dia (pra atualizar com dados mais recentes)
    if registros:
        datas_cidades = set((r["cidade"], r["data_alvo"]) for r in registros)
        for cidade, data in datas_cidades:
            try:
                httpx.delete(
                    f"{SUPABASE_URL}/rest/v1/we_modelos?cidade=eq.{cidade}&data_alvo=eq.{data}",
                    headers=HEADERS_SB, timeout=10,
                )
            except:
                pass

        # Salvar novos registros
        try:
            r = httpx.post(
                f"{SUPABASE_URL}/rest/v1/we_modelos",
                headers=HEADERS_SB,
                json=registros,
                timeout=30,
            )
            if r.status_code in (200, 201):
                logger.info(f"Salvos {len(registros)} registros no Supabase (status {r.status_code})")
            else:
                logger.error(f"Erro ao salvar no Supabase: {r.status_code} — {r.text[:200]}")
        except Exception as e:
            logger.error(f"Falha na conexao com Supabase: {e}")
    else:
        logger.warning("Nenhum registro coletado para salvar.")

    logger.info("=== Coleta de modelos concluida ===")


if __name__ == "__main__":
    asyncio.run(coletar())
