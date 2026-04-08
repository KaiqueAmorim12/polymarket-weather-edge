"""alerta_telegram.py — Envia alertas Telegram 1h antes do pico de temperatura."""
import asyncio
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta, date
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

# Hora estimada de pico (hora local da cidade)
HORA_PICO_LOCAL = 14  # 14h local como estimativa padrao
HORA_ALERTA_LOCAL = HORA_PICO_LOCAL - 1  # alerta 1h antes = 13h local

# Modelos disponiveis para avaliacao
MODELOS_NOMES = ["ECMWF", "GFS", "ICON", "UKMO", "JMA", "GEM"]


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


def calcular_melhor_modelo(nome_cidade: str) -> tuple[str, int, list[str]]:
    """Retorna (melhor_modelo, pct_acerto, top3) baseado nos ultimos 30 dias.

    Busca historico real do Supabase e calcula qual modelo acertou mais
    a temperatura maxima (comparando previsao arredondada com leitura real).
    """
    logger = logging.getLogger(__name__)
    data_inicio = (date.today() - timedelta(days=30)).isoformat()

    # Buscar previsoes dos modelos dos ultimos 30 dias
    modelos = buscar_supabase(
        "we_modelos",
        f"cidade=eq.{nome_cidade}&data_alvo=gte.{data_inicio}&order=hora_captura.desc",
    )

    # Buscar leituras reais dos ultimos 30 dias
    leituras = buscar_supabase(
        "we_leituras",
        f"cidade=eq.{nome_cidade}&data_alvo=gte.{data_inicio}&select=data_alvo,temperatura",
    )

    # Calcular maxima real por dia (pega o maior valor de temperatura no dia)
    max_por_dia: dict[str, float] = defaultdict(lambda: -999.0)
    for l in leituras:
        try:
            t = float(l.get("temperatura", 0))
            dia = l["data_alvo"]
            if t > max_por_dia[dia]:
                max_por_dia[dia] = t
        except (ValueError, KeyError):
            continue

    # Pegar apenas a coleta mais recente por combinacao dia+modelo
    vistos: set[str] = set()
    prev_por_dia: dict[str, dict[str, float]] = {}  # {dia: {modelo: temp_prevista}}
    for m in modelos:
        chave = f"{m['data_alvo']}_{m['modelo']}"
        if chave in vistos:
            continue
        vistos.add(chave)
        dia = m["data_alvo"]
        if dia not in prev_por_dia:
            prev_por_dia[dia] = {}
        try:
            prev_por_dia[dia][m["modelo"]] = float(m["temp_max_prevista"])
        except (ValueError, KeyError):
            continue

    # Contar acertos apenas em dias ja finalizados (antes de hoje)
    hoje = date.today().isoformat()
    acertos: dict[str, int] = {m: 0 for m in MODELOS_NOMES}
    totais: dict[str, int] = {m: 0 for m in MODELOS_NOMES}

    for dia, prevs in prev_por_dia.items():
        if dia >= hoje:
            continue  # dia ainda nao finalizou, nao conta
        real = max_por_dia.get(dia)
        if real is None or real == -999.0:
            continue  # sem leitura real para comparar
        real_arred = round(real)
        for modelo, temp in prevs.items():
            if modelo in totais:
                totais[modelo] += 1
                if round(temp) == real_arred:
                    acertos[modelo] += 1

    # Montar ranking: modelos com pelo menos 1 previsao, ordenados por acertos
    ranking = sorted(
        [m for m in MODELOS_NOMES if totais[m] > 0],
        key=lambda m: acertos[m],
        reverse=True,
    )

    # Fallback se nao houver dados suficientes
    if not ranking:
        logger.warning(f"  Sem dados historicos para {nome_cidade}, usando ICON como fallback")
        return "ICON", 0, ["ICON", "ECMWF", "GFS"]

    melhor = ranking[0]
    total_melhor = totais[melhor]
    pct = round(acertos[melhor] / total_melhor * 100) if total_melhor > 0 else 0

    top3 = ranking[:3]
    logger.info(f"  {nome_cidade}: melhor={melhor} ({pct}%), top3={top3}")

    return melhor, pct, top3


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

        # Calcular melhor modelo dinamicamente com base nos ultimos 30 dias
        melhor, conf, top3 = calcular_melhor_modelo(nome)

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

        # Formatar top3 dinamico
        top3_str = " | ".join(f"#{i+1} {m}" for i, m in enumerate(top3))

        texto = (
            f"<b>⏰ {nome} — pico em ~1h</b>\n"
            f"\n"
            f"Pico previsto: ~{HORA_PICO_LOCAL}:00 local / {hora_pico_brt:02d}:00 BRT\n"
            f"Temp atual: {temp_atual_str}\n"
            f"\n"
            f"<b>Melhor modelo (30d): {melhor} (acerto {conf}%)</b>\n"
            f"Ranking: {top3_str}\n"
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
