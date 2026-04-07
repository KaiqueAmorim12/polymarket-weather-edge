"""Testes do modulo polymarket — conector e mapeador."""
import pytest

from polymarket.mapeador import parsear_faixa_temperatura, FaixaOdd


class TestMapeador:
    def test_parsear_faixa_exata(self) -> None:
        faixa = parsear_faixa_temperatura("20°C")
        assert faixa is not None
        assert faixa.grau == 20
        assert faixa.tipo == "exata"

    def test_parsear_faixa_ou_menos(self) -> None:
        faixa = parsear_faixa_temperatura("16°C ou menos")
        assert faixa is not None
        assert faixa.grau == 16
        assert faixa.tipo == "inferior"

    def test_parsear_faixa_or_below(self) -> None:
        faixa = parsear_faixa_temperatura("16°C or below")
        assert faixa is not None
        assert faixa.grau == 16
        assert faixa.tipo == "inferior"

    def test_parsear_faixa_ou_mais(self) -> None:
        faixa = parsear_faixa_temperatura("24°C or higher")
        assert faixa is not None
        assert faixa.grau == 24
        assert faixa.tipo == "superior"

    def test_parsear_faixa_fahrenheit(self) -> None:
        faixa = parsear_faixa_temperatura("70°F")
        assert faixa is not None
        assert faixa.grau == 21

    def test_parsear_faixa_invalida(self) -> None:
        faixa = parsear_faixa_temperatura("texto invalido")
        assert faixa is None


class TestConector:
    def test_parsear_evento_weather(self) -> None:
        from polymarket.conector import PolymarketConector

        evento_mock = {
            "id": "123",
            "title": "Highest temperature in London on April 7?",
            "slug": "highest-temperature-in-london-on-april-7-2026",
            "markets": [
                {
                    "id": "m1",
                    "question": "Will the highest temperature in London be 20°C on April 7?",
                    "outcomePrices": "[0.24, 0.79]",
                    "volume": "12672",
                    "outcomes": "[\"Yes\", \"No\"]",
                },
                {
                    "id": "m2",
                    "question": "Will the highest temperature in London be 21°C on April 7?",
                    "outcomePrices": "[0.05, 0.96]",
                    "volume": "17143",
                    "outcomes": "[\"Yes\", \"No\"]",
                },
            ],
        }

        conector = PolymarketConector()
        odds = conector._parsear_evento(evento_mock)

        assert len(odds) == 2
        assert odds[0]["faixa_grau"] == 20
        assert odds[0]["preco_compra"] == 0.24
        assert odds[1]["faixa_grau"] == 21
        assert odds[1]["preco_compra"] == 0.05
