"""Mapeador — parseia faixas de temperatura dos contratos Polymarket."""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class FaixaOdd:
    """Uma faixa de temperatura parseada de um contrato Polymarket."""

    grau: int
    tipo: str  # "exata", "inferior" (ou menos), "superior" (ou mais)


def parsear_faixa_temperatura(texto: str) -> Optional[FaixaOdd]:
    """Parseia texto de faixa de temperatura do contrato Polymarket.

    Exemplos:
        "20°C"           -> FaixaOdd(grau=20, tipo="exata")
        "16°C ou menos"  -> FaixaOdd(grau=16, tipo="inferior")
        "16°C or below"  -> FaixaOdd(grau=16, tipo="inferior")
        "24°C or higher" -> FaixaOdd(grau=24, tipo="superior")
        "70°F"           -> FaixaOdd(grau=21, tipo="exata")  (convertido)
    """
    texto = texto.strip()

    eh_fahrenheit = "°F" in texto or "°f" in texto

    match = re.search(r"(-?\d+)", texto)
    if not match:
        return None

    valor = int(match.group(1))

    if eh_fahrenheit:
        valor = round((valor - 32) * 5 / 9)

    texto_lower = texto.lower()
    if "ou menos" in texto_lower or "or below" in texto_lower or "or lower" in texto_lower:
        return FaixaOdd(grau=valor, tipo="inferior")
    elif "ou mais" in texto_lower or "or higher" in texto_lower or "or above" in texto_lower:
        return FaixaOdd(grau=valor, tipo="superior")
    else:
        return FaixaOdd(grau=valor, tipo="exata")
