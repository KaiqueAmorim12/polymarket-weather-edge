"""Testes do coletor Weather Underground API."""
from datetime import datetime, timezone

import pytest

from coletores.wu_api import ColetorWU, LeituraHoraria


class TestLeituraHoraria:
    def test_criar_leitura(self) -> None:
        leitura = LeituraHoraria(
            timestamp=1775480400,
            temperatura=16.0,
            hora_utc="14:20",
            hora_local="15:20",
            unidade="C",
        )
        assert leitura.temperatura == 16.0
        assert leitura.unidade == "C"


class TestColetorWU:
    def test_parsear_resposta_celsius(self) -> None:
        resposta_mock = {
            "observations": [
                {"valid_time_gmt": 1775444400, "temp": 8},
                {"valid_time_gmt": 1775446200, "temp": 7},
                {"valid_time_gmt": 1775480400, "temp": 16},
                {"valid_time_gmt": 1775482200, "temp": 15},
            ]
        }
        coletor = ColetorWU()
        leituras = coletor._parsear_resposta(resposta_mock, unidade="C", fuso_offset=1)
        assert len(leituras) == 4
        assert leituras[0].temperatura == 8
        assert leituras[2].temperatura == 16

    def test_parsear_resposta_fahrenheit(self) -> None:
        resposta_mock = {
            "observations": [
                {"valid_time_gmt": 1775444400, "temp": 68},
                {"valid_time_gmt": 1775446200, "temp": 72},
                {"valid_time_gmt": 1775480400, "temp": 79},
            ]
        }
        coletor = ColetorWU()
        leituras = coletor._parsear_resposta(resposta_mock, unidade="F", fuso_offset=-4)
        assert len(leituras) == 3
        assert leituras[0].temperatura == 68
        assert leituras[2].temperatura == 79

    def test_calcular_pico(self) -> None:
        leituras = [
            LeituraHoraria(1, 10.0, "06:00", "07:00", "C"),
            LeituraHoraria(2, 15.0, "10:00", "11:00", "C"),
            LeituraHoraria(3, 20.0, "14:00", "15:00", "C"),
            LeituraHoraria(4, 18.0, "16:00", "17:00", "C"),
        ]
        coletor = ColetorWU()
        pico = coletor._calcular_pico(leituras)
        assert pico["temperatura"] == 20.0
        assert pico["hora_local"] == "15:00"

    def test_calcular_status(self) -> None:
        leituras = [
            LeituraHoraria(1, 10.0, "06:00", "07:00", "C"),
            LeituraHoraria(2, 15.0, "10:00", "11:00", "C"),
            LeituraHoraria(3, 16.0, "11:00", "12:00", "C"),
        ]
        coletor = ColetorWU()
        status = coletor._calcular_status(leituras)
        assert status == "Subindo"

    def test_resposta_vazia(self) -> None:
        coletor = ColetorWU()
        leituras = coletor._parsear_resposta({"observations": []}, "C", 0)
        assert leituras == []
