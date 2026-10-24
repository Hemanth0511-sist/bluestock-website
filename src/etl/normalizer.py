"""
Utility functions for cleaning and standardizing
financial datasets before loading into SQLite.
"""

import re


def normalize_year(year) -> str | None:
    """
    Normalize financial year/date values to YYYY-MM.

    Supported formats:
        Mar-23       -> 2023-03
        Mar 23       -> 2023-03
        March-2023   -> 2023-03
        March 2023   -> 2023-03
        2023         -> 2023-03
        FY23         -> 2023-03
        FY2023       -> 2023-03
        Dec-22       -> 2022-12
        Dec 22       -> 2022-12
        December-22  -> 2022-12
        Jun-23       -> 2023-06
        2023-03      -> 2023-03

    Returns:
        YYYY-MM string for valid input.
        None for None.
        PARSE_ERROR for unsupported values.
    """

    if year is None:
        return None

    text = str(year).strip().upper()

    if not text:
        return "PARSE_ERROR"

    # Remove FY prefix
    if text.startswith("FY"):
        text = text[2:].strip()

        # FY23 / FY24 / FY99
        if re.fullmatch(r"\d{2}", text):
            return f"20{int(text):02d}-03"

        # FY2023 / FY2024
        if re.fullmatch(r"\d{4}", text):
            return f"{text}-03"

        return "PARSE_ERROR"

    # Already normalized YYYY-MM
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", text)
    if match:
        year_part = int(match.group(1))
        month_part = int(match.group(2))

        if 1 <= month_part <= 12:
            return f"{year_part:04d}-{month_part:02d}"

        return "PARSE_ERROR"

    # Plain year: YYYY -> YYYY-03
    if re.fullmatch(r"\d{4}", text):
        return f"{text}-03"

    # Month + year formats:
    # Mar-23, Mar 23, March-2023, March 2023
    match = re.fullmatch(r"([A-Z]+)[\s\-]+(\d{2}|\d{4})", text)

    if match:
        month_text = match.group(1)
        year_text = match.group(2)

        months = {
            "JAN": 1,
            "JANUARY": 1,
            "FEB": 2,
            "FEBRUARY": 2,
            "MAR": 3,
            "MARCH": 3,
            "APR": 4,
            "APRIL": 4,
            "MAY": 5,
            "JUN": 6,
            "JUNE": 6,
            "JUL": 7,
            "JULY": 7,
            "AUG": 8,
            "AUGUST": 8,
            "SEP": 9,
            "SEPT": 9,
            "SEPTEMBER": 9,
            "OCT": 10,
            "OCTOBER": 10,
            "NOV": 11,
            "NOVEMBER": 11,
            "DEC": 12,
            "DECEMBER": 12,
        }

        month = months.get(month_text)

        if month is None:
            return "PARSE_ERROR"

        if len(year_text) == 2:
            year_value = 2000 + int(year_text)
        else:
            year_value = int(year_text)

        return f"{year_value:04d}-{month:02d}"

    return "PARSE_ERROR"


def normalize_ticker(ticker: str) -> str:
    if ticker is None:
        return ""

    return ticker.strip().upper()


def normalize_text(value: str) -> str:
    if value is None:
        return ""

    return " ".join(value.strip().split())
