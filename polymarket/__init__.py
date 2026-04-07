"""Modulo polymarket — conector e mapeador de odds."""
from polymarket.conector import PolymarketConector
from polymarket.mapeador import parsear_faixa_temperatura, FaixaOdd

__all__ = ["PolymarketConector", "parsear_faixa_temperatura", "FaixaOdd"]
