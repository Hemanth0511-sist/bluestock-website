"""
normalizer.py

Utility functions for cleaning and standardizing
financial datasets before loading into SQLite.
"""

from typing import Optional


def normalize_year(year) -> Optional[int]:
    if year is None:
        return None

    text = str(year).strip().upper()
    text = text.replace("FY", "")

    if len(text) == 2 and text.isdigit():
        return 2000 + int(text)

    if text.isdigit():
        return int(text)

    return None


def normalize_ticker(ticker: str) -> str:
    if ticker is None:
        return ""

    return ticker.strip().upper()


def normalize_text(value: str) -> str:
    if value is None:
        return ""

    return " ".join(value.strip().split())