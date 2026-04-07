"""Mapeador — parseia faixas de temperatura dos contratos Polymarket."""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class FaixaOdd:
    """Uma faixa de temperatura parseada de um contrato Polymarket."""

    grau: int
    tipo: str  # "exata", "inferior" (ou menos), "superior" (ou mais)
    grau_min: int = 0  # pra faixas de range (ex: 68-69°F)
    grau_max: int = 0  # idem
    unidade: str = "C"  # "C" ou "F" — unidade ORIGINAL do contrato


def parsear_faixa_temperatura(texto: str) -> Optional[FaixaOdd]:
    """Parseia texto de faixa de temperatura do contrato Polymarket.

    Exemplos:
        "20°C"               -> FaixaOdd(grau=20, tipo="exata")
        "16°C ou menos"      -> FaixaOdd(grau=16, tipo="inferior")
        "24°C or higher"     -> FaixaOdd(grau=24, tipo="superior")
        "70°F"               -> FaixaOdd(grau=21, tipo="exata")  (convertido)
        "between 68-69°F"    -> FaixaOdd(grau=20, tipo="range", grau_min=20, grau_max=21)
        "67°F or below"      -> FaixaOdd(grau=19, tipo="inferior")
    """
    texto = texto.strip()
    texto_norm = texto.replace("\u00b0", "°").replace("&#176;", "°")

    eh_fahrenheit = "°F" in texto_norm or "°f" in texto_norm
    unidade = "F" if eh_fahrenheit else "C"

    texto_lower = texto_norm.lower()

    # Padrao 1: "between X-Y°F" (faixas de range, ex: Miami)
    match_range = re.search(r"between\s+(\d+)\s*-\s*(\d+)\s*°\s*([cf])", texto_lower)
    if match_range:
        val_min = int(match_range.group(1))
        val_max = int(match_range.group(2))
        grau_medio = round((val_min + val_max) / 2)
        if eh_fahrenheit:
            grau_medio = round(((val_min + val_max) / 2 - 32) * 5 / 9)
            val_min_c = round((val_min - 32) * 5 / 9)
            val_max_c = round((val_max - 32) * 5 / 9)
        else:
            val_min_c = val_min
            val_max_c = val_max
        return FaixaOdd(
            grau=grau_medio,
            tipo="range",
            grau_min=val_min_c,
            grau_max=val_max_c,
            unidade=unidade,
        )

    # Padrao 2: numero simples
    match = re.search(r"(-?\d+)", texto_norm)
    if not match:
        return None

    valor = int(match.group(1))

    if eh_fahrenheit:
        valor = round((valor - 32) * 5 / 9)

    if "ou menos" in texto_lower or "or below" in texto_lower or "or lower" in texto_lower:
        return FaixaOdd(grau=valor, tipo="inferior", unidade=unidade)
    elif "ou mais" in texto_lower or "or higher" in texto_lower or "or above" in texto_lower:
        return FaixaOdd(grau=valor, tipo="superior", unidade=unidade)
    else:
        return FaixaOdd(grau=valor, tipo="exata", unidade=unidade)
