"""Shared data processing for both matplotlib and plotly plots."""

from __future__ import annotations

from collections import Counter

import pandas as pd

STOP_WORDS: set[str] = {
    "and", "of", "the", "for", "a", "toward", "with", "from",
    "on", "in", "to", "as", "by", "an", "its", "via", "based",
    "using", "at", "their", "are", "is", "be",
}


def extract_year_counts(df: pd.DataFrame) -> tuple[list[int], list[int]]:
    """Extract sorted (years, counts) from a DataFrame with a 'year' column."""
    year = pd.to_numeric(df["year"], errors="coerce").dropna().astype(int)
    year_unique, year_counts = zip(*sorted(zip(
        year.value_counts().index, year.value_counts().values,
    ))) if len(year) > 0 else ([], [])
    return list(year_unique), list(year_counts)


def extract_top_journals(df: pd.DataFrame, top_n: int = 10) -> tuple[list[str], list[int]]:
    """Extract (journal_names, counts) for top N journals."""
    journal = df["journal"].replace("No disponible", pd.NA).dropna()
    counts = journal.value_counts().head(top_n)
    return list(counts.index), list(counts.values)


def extract_top_keywords(data: list[dict], top_n: int = 10) -> tuple[list[str], list[int]]:
    """Extract (words, frequencies) from article titles."""
    all_words: list[str] = []
    for item in data:
        words = (item.get("title", "").lower()
                 .replace("/", " ").replace("(", " ").replace(")", " ").split())
        all_words.extend(words)

    keywords = [w for w in all_words if w not in STOP_WORDS and len(w) > 2]
    top = Counter(keywords).most_common(top_n)
    if not top:
        return [], []
    words, freqs = zip(*top)
    return list(words), list(freqs)


def extract_source_distribution(df: pd.DataFrame) -> tuple[list[str], list[int]]:
    """Extract (source_names, counts)."""
    counts = df["source"].value_counts()
    return list(counts.index), list(counts.values)


def extract_level_distribution(df: pd.DataFrame) -> tuple[list[str], list[int]]:
    """Extract (level_labels, counts)."""
    level_labels = {
        "L1": "L1 Blends", "L2": "L2 Aditivos",
        "L3": "L3 Empaques", "L4": "L4 Biodegradables",
    }
    counts = df["level"].value_counts()
    labels = [level_labels.get(lvl, lvl) for lvl in counts.index]
    return labels, list(counts.values)
