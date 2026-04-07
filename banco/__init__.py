"""Modulo banco — Supabase."""
from banco.repositorio import Repositorio


def criar_tabelas(caminho_db: str = "") -> None:
    """Noop — tabelas criadas no Supabase Dashboard."""
    pass


__all__ = ["criar_tabelas", "Repositorio"]
