"""Testes do coletor de resolucao — busca temperatura real no WU History."""
import pytest

from coletores.resolucao import ColetorResolucao


class TestColetorResolucao:
    def test_formatar_url(self) -> None:
        coletor = ColetorResolucao()
        url_template = "https://www.wunderground.com/history/daily/gb/london/EGLC/date/{data}"
        url = coletor._formatar_url(url_template, "2026-04-07")
        assert url == "https://www.wunderground.com/history/daily/gb/london/EGLC/date/2026-4-7"

    def test_formatar_url_sem_zero(self) -> None:
        coletor = ColetorResolucao()
        url_template = "https://www.wunderground.com/history/daily/gb/london/EGLC/date/{data}"
        url = coletor._formatar_url(url_template, "2026-12-15")
        assert url == "https://www.wunderground.com/history/daily/gb/london/EGLC/date/2026-12-15"

    def test_parsear_temperatura_de_html(self) -> None:
        """Testa parsing de temperatura maxima de HTML simplificado."""
        coletor = ColetorResolucao()
        # WU History mostra temperatura maxima em tabela de observacoes
        # Esse teste valida o metodo de fallback por texto
        temp = coletor._extrair_max_de_texto("Max Temperature\n20 °C")
        assert temp == 20.0

    def test_parsear_temperatura_fahrenheit(self) -> None:
        coletor = ColetorResolucao()
        temp = coletor._extrair_max_de_texto("Max Temperature\n68 °F")
        # 68F = 20C
        assert temp == 20.0

    def test_parsear_temperatura_none_se_invalido(self) -> None:
        coletor = ColetorResolucao()
        temp = coletor._extrair_max_de_texto("nenhuma temperatura aqui")
        assert temp is None
