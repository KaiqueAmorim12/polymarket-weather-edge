"""Tipos base para coletores meteorologicos."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Previsao:
    """Uma previsao de temperatura de uma fonte especifica."""

    fonte: str
    temperatura_max: float
    temperatura_min: float
    coletado_em: datetime

    def valida(self) -> bool:
        """Previsao eh valida se max >= min e valores razoaveis (-60 a 60 C)."""
        return (
            self.temperatura_max >= self.temperatura_min
            and -60 <= self.temperatura_min <= 60
            and -60 <= self.temperatura_max <= 60
        )


@dataclass
class ResultadoColeta:
    """Resultado de uma rodada de coleta pra uma cidade/dia."""

    cidade: str
    data_alvo: str
    previsoes: list[Previsao] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)

    def sucesso(self) -> bool:
        """Coleta eh sucesso se tem pelo menos 1 previsao valida."""
        return len(self.previsoes) > 0
