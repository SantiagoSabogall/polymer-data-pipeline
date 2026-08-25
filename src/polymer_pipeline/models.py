"""Definiciones de tipos compartidas para el pipeline."""

from __future__ import annotations

from typing import TypedDict


class Article(TypedDict, total=False):
    """Representa un artículo normalizado en el pipeline."""
    title: str
    author: str
    journal: str
    year: str
    doi: str
    source: str
    abstract: str
    pdf_url: str
    level: str
