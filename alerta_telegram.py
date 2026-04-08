"""alerta_telegram.py — Envia alertas Telegram 1h antes do pico de temperatura."""
import asyncio
import json
import logging
from collections import Counter
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

TELEGRAM_TOKEN = "8694039991:AAHxcdfFgEPZbRugxzEQKrfUojoBwTJXv28"
TELEGRAM_CHAT_ID = "6406646436"

# Melhor modelo por cidade (baseado no teste de 7 dias)
MELHOR_MODELO: dict[str, str] = {
    "Wellington": "UKMO", "Seoul": "GEM", "Tokyo": "ECMWF", "Busan": "UKMO",
    "Shanghai": "ECMWF", "Hong Kong": "GFS", "Beijing": "UKMO", "Chongqing": "ECMWF",
    "Taipei": "ICON", "Singapore": "UKMO", "Kuala Lumpur": "GFS", "Jakarta": "UKMO",
    "Lucknow": "ECMWF", "Moscow": "ECMWF", "Ankara": "ICON", "Istanbul": "ICON",
    "Tel Aviv": "ICON", "Helsinki": "UKMO", "Warsaw": "ECMWF", "Paris": "ECMWF",
    "Amsterdam": "ICON", "Madrid": "GEM", "Milan": "ICON", "London": "ICON",
    "Sao Paulo": "UKMO", "Buenos Aires": "ICON", "Toronto": "ECMWF", "NYC": "ICON",
    "Panama": "UKMO", "Chicago": "GFS", "Mexico City": "UKMO", "Denver": "ICON",
    "Miami": "UKMO", "Seattle": "ECMWF",
}

# Confianca do melhor modelo (% de acerto em 7 dias)
CONFIANCA: dict[str, int] = {
    "Wellington": 57, "Seoul": 71, "Tokyo": 43, "Busan": 71,
    "Shanghai": 43, "Hong Kong": 14, "Beijing": 57, "Chongqing": 43,
    "Taipei": 29, "Singapore": 57, "Kuala Lumpur": 29, "Jakarta": 30,
    "Lucknow": 57, "Moscow": 29, "Ankara": 57, "Istanbul": 30,
    "Tel Aviv": 29, "Helsinki": 71, "Warsaw": 71, "Paris": 57,
    "Amsterdam": 71, "Madrid": 57, "Milan": 71, "London": 71,
    "Sao Paulo": 43, "Buenos Aires": 29, "Toronto": 71, "NYC": 43,
    "Panama": 43, "Chicago": 43, "Mexico City": 57, "Denver": 29,
    "Miami": 30, "Seattle": 14,
}

# Hora estimada de pico (hora local da cidade)
HORA_PICO_LOCAL = 14  # 14h local como estimativa padrao
HORA_ALERTA_LOCAL = HORA_PICO_LOCAL - 1  # alerta 1h antes = 13h local


def carregar_cidades() -> list[dict]:
    """Carrega lista de cidades do arquivo de configuracao."""
    with open(RAIZ / "config" / "cidades.json", encoding="utf-8") as f:
        return json.load(f)["cidades"]


async def enviar_telegram(texto: str) -> bool:
    """Envia mensagem para o Telegram. Retorna True se bem-sucedido."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": texto,
                "parse_mode": "HTML",
            })
            return r.status_code == 200
    except Exception as e:
        logging.getLogger(__name__).warning(f"Erro ao enviar Telegram: {e}")
        return False


def buscar_supabase(endpoint: str, params: str = "") -> list[dict]:
    """Busca dados no Supabase via REST API sincrona."""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    if params:
        url += f"?{params}"
    try:
        r = httpx.get(url, headers=HEADERS_SB, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Erro ao buscar {endpoint}: {e}")
    return []


async def verificar_alertas() -> None:
    """Verifica quais cidades estao ~1h antes do pico e envia alertas Telegram."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger(__name__)

    cidades = carregar_cidades()
    agora_utc = datetime.now(timezone.utc)

    logger.info(f"=== Verificando alertas — {agora_utc.isoformat()[:16]} UTC ===")

    alertas_enviados = 0

    for c in cidades:
        nome: str = c["nome"]
        fuso: float = c["fuso_offset"]
        unidade: str = c["unidade"]

        # Calcular hora e minuto local atual da cidade
        agora_local = agora_utc + timedelta(hours=fuso)
        hora_local = agora_local.hour
        minuto_local = agora_local.minute

        # Verificar se e hora de alerta (13h local, entre :00 e :30)
        # Isso evita alertas duplicados se o script rodar multiplas vezes na mesma hora
        if hora_local != HORA_ALERTA_LOCAL:
            continue
        if minuto_local > 30:
            continue

        data_local = agora_local.strftime("%Y-%m-%d")

        # Buscar previsoes dos modelos para hoje nessa cidade
        modelos_previsao = buscar_supabase(
            "we_modelos",
            f"cidade=eq.{nome}&data_alvo=eq.{data_local}&order=criado_em.desc",
        )

        # Buscar temperatura atual (ultima leitura)
        leituras = buscar_supabase(
            "we_leituras",
            f"cidade=eq.{nome}&data_alvo=eq.{data_local}&order=timestamp_wu.desc&limit=1",
        )
        temp_atual = leituras[0]["temperatura"] if leituras else None

        # Buscar odds Polymarket do dia
        odds = buscar_supabase(
            "we_odds",
            f"cidade=eq.{nome}&data_alvo=eq.{data_local}&order=coletado_em.desc&limit=20",
        )

        # Determinar melhor modelo e confianca
        melhor = MELHOR_MODELO.get(nome, "ICON")
        conf = CONFIANCA.get(nome, 30)

        # Previsao do melhor modelo
        prev_melhor = next((m for m in modelos_previsao if m["modelo"] == melhor), None)
        prev_temp = f"{float(prev_melhor['temp_max_prevista']):.0f}" if prev_melhor else "?"

        # Calcular consenso: arredondar cada modelo e ver qual temp aparece mais
        previsoes_unicas: dict[str, int] = {}
        for m in modelos_previsao:
            previsoes_unicas[m["modelo"]] = round(float(m["temp_max_prevista"]))

        if previsoes_unicas:
            contagem: Counter = Counter(previsoes_unicas.values())
            faixa_consenso, qtd_consenso = contagem.most_common(1)[0]
            total_modelos = len(previsoes_unicas)
        else:
            faixa_consenso = "?"
            qtd_consenso = 0
            total_modelos = 0

        # Buscar odd da faixa prevista pelo melhor modelo
        odd_str = ""
        if odds and prev_melhor:
            faixa_busca = str(round(float(prev_melhor["temp_max_prevista"])))
            odd_match = next((o for o in odds if faixa_busca in str(o.get("faixa", ""))), None)
            if odd_match:
                odd_str = f"\nOdd Polymarket {faixa_busca}°{unidade}: {float(odd_match['preco_compra']) * 100:.1f}%"

        # Listar todos os modelos com destaque pro melhor
        modelos_str = ""
        for m in modelos_previsao:
            marca = " &lt;&lt;&lt;" if m["modelo"] == melhor else ""
            modelos_str += f"\n  {m['modelo']}: {float(m['temp_max_prevista']):.0f}°{unidade}{marca}"

        # Calcular hora do pico em BRT (UTC-3)
        hora_pico_utc = HORA_PICO_LOCAL - fuso
        hora_pico_brt = int(((hora_pico_utc - 3) % 24 + 24) % 24)

        # Formatar temperatura atual
        temp_atual_str = f"{float(temp_atual):.0f}°{unidade}" if temp_atual is not None else "—"

        texto = (
            f"<b>⏰ {nome} — pico em ~1h</b>\n"
            f"\n"
            f"Pico previsto: ~{HORA_PICO_LOCAL}:00 local / {hora_pico_brt:02d}:00 BRT\n"
            f"Temp atual: {temp_atual_str}\n"
            f"\n"
            f"<b>Melhor modelo: {melhor} (confianca {conf}%)</b>\n"
            f"Previsao: {prev_temp}°{unidade}\n"
            f"Consenso: {faixa_consenso}°{unidade} ({qtd_consenso}/{total_modelos} modelos)\n"
            f"{modelos_str}\n"
            f"{odd_str}"
        )

        enviado = await enviar_telegram(texto)
        if enviado:
            alertas_enviados += 1
            logger.info(f"  Alerta enviado: {nome}")
        else:
            logger.warning(f"  Falha ao enviar alerta: {nome}")

    logger.info(f"=== {alertas_enviados} alertas enviados ===")


if __name__ == "__main__":
    asyncio.run(verificar_alertas())
