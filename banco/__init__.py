"""Modulo banco — persistencia SQLite."""
from banco.modelos import criar_tabelas
from banco.repositorio import Repositorio

__all__ = ["criar_tabelas", "Repositorio"]
