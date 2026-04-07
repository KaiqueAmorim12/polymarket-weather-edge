"""exportar_json.py — Exporta dados do banco pra JSON (usado pelo GitHub Actions)."""
import json
from datetime import date, timedelta
from pathlib import Path

from banco import criar_tabelas, Repositorio

RAIZ = Path(__file__).parent
CAMINHO_DB = RAIZ / "dados" / "weather_edge.db"
CAMINHO_RESULTADOS = RAIZ / "resultados"


def exportar() -> None:
    CAMINHO_RESULTADOS.mkdir(parents=True, exist_ok=True)
    criar_tabelas(str(CAMINHO_DB))
    repo = Repositorio(str(CAMINHO_DB))

    hoje = date.today()

    cidades_json = json.loads((RAIZ / "config" / "cidades.json").read_text(encoding="utf-8"))
    cidades = cidades_json["cidades"]

    resumo: dict = {
        "data": hoje.isoformat(),
        "cidades": {},
    }

    for cidade in cidades:
        nome = cidade["nome"]
        leituras = repo.buscar_leituras(nome, hoje.isoformat())
        if leituras:
            pico = max(leituras, key=lambda l: l["temperatura"])
            resumo["cidades"][nome] = {
                "leituras": len(leituras),
                "temp_atual": leituras[-1]["temperatura"],
                "pico": pico["temperatura"],
                "pico_hora": pico["hora_local"],
                "unidade": cidade["unidade"],
            }

    metricas = repo.calcular_metricas()
    resumo["metricas"] = metricas
    resumo["apostas_hoje"] = repo.buscar_apostas_do_dia(hoje.isoformat())

    caminho = CAMINHO_RESULTADOS / "resumo_diario.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2, default=str)

    print(f"Exportado: {len(resumo['cidades'])} cidades com dados")


if __name__ == "__main__":
    exportar()
