"""
DAY 35 - PORTFOLIO SUMMARY PDF

Generates one page per company, ordered alphabetically by ticker.

Output:
    reports/portfolio/portfolio_summary.pdf

Each page contains:
- Company name, ticker, sector
- Top 6 KPIs
- Trend arrows comparing latest available year with previous year
  (↑ improved, ↓ declined, → flat within 2%)
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "database" / "n100.db"
OUTPUT_DIR = ROOT / "reports" / "portfolio"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "portfolio_summary.pdf"

NAVY = colors.HexColor("#12304A")
BLUE = colors.HexColor("#EAF2F8")
LIGHT = colors.HexColor("#F5F7FA")
GREEN = colors.HexColor("#16803C")
RED = colors.HexColor("#B42318")
GRAY = colors.HexColor("#667085")
DARK = colors.HexColor("#172033")
WHITE = colors.white
BORDER = colors.HexColor("#D5DCE3")


def clean_text(value: Any, default: str = "N/A") -> str:
    if value is None:
        return default
    text = str(value).replace("\\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text or text.lower() in {"nan", "none"}:
        return default
    return text


def safe_float(value: Any) -> float | None:
    try:
        x = float(value)
        return x if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def fmt(value: Any, suffix: str = "") -> str:
    x = safe_float(value)
    return "N/A" if x is None else f"{x:.2f}{suffix}"


def choose(columns, candidates):
    lookup = {str(c).lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    normalized = {re.sub(r"[^a-z0-9]", "", str(c).lower()): c for c in columns}

    for candidate in candidates:
        key = re.sub(r"[^a-z0-9]", "", str(candidate).lower())
        if key in normalized:
            return normalized[key]

    return None


def year_num(value: Any) -> int:
    match = re.search(r"(19|20)\d{2}", str(value))
    return int(match.group()) if match else -1


def load_data():
    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query("SELECT * FROM companies", conn)

    sectors = pd.read_sql_query("SELECT * FROM sectors", conn)

    ratios = pd.read_sql_query("SELECT * FROM historical_financial_ratios", conn)

    pl = pd.read_sql_query("SELECT * FROM profitandloss", conn)

    cashflow = pd.read_sql_query("SELECT * FROM cashflow", conn)

    conn.close()

    return companies, sectors, ratios, pl, cashflow


def normalize_ids(df: pd.DataFrame, candidates=("company_id", "id", "ticker")):
    if df.empty:
        return df.copy(), None

    col = choose(df.columns, list(candidates))
    result = df.copy()

    if col is not None:
        result["company_id"] = result[col].astype(str).str.strip().str.upper()

    return result, col


def sort_by_year(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    year_col = choose(df.columns, ["year", "financial_year", "fy"])

    result = df.copy()

    if year_col:
        result["_year_num"] = result[year_col].apply(year_num)
        result = result.sort_values(["company_id", "_year_num"])

    return result


def get_sector_map(sectors: pd.DataFrame) -> dict[str, str]:
    sectors, _ = normalize_ids(sectors)

    if "company_id" not in sectors.columns:
        return {}

    sector_col = choose(
        sectors.columns, ["broad_sector", "sector", "broad_sector_name"]
    )

    if sector_col is None:
        return {}

    result = {}

    for _, row in sectors.iterrows():
        ticker = clean_text(row.get("company_id"), "").upper()
        sector = clean_text(row.get(sector_col), "Unknown")

        if ticker:
            result[ticker] = sector

    return result


def latest_two(df: pd.DataFrame, company_id: str) -> pd.DataFrame:
    if df.empty or "company_id" not in df.columns:
        return pd.DataFrame()

    result = df[
        df["company_id"].astype(str).str.strip().str.upper() == company_id
    ].copy()

    result = sort_by_year(result)

    if "_year_num" in result.columns:
        result = result.drop_duplicates(subset=["_year_num"], keep="last")

    return result.tail(2).reset_index(drop=True)


def latest_row(df: pd.DataFrame, company_id: str) -> pd.Series | None:
    rows = latest_two(df, company_id)

    if rows.empty:
        return None

    return rows.iloc[-1]


def previous_row(df: pd.DataFrame, company_id: str) -> pd.Series | None:
    rows = latest_two(df, company_id)

    if len(rows) < 2:
        return None

    return rows.iloc[-2]


def get_metric(row: pd.Series | None, candidates) -> float | None:
    if row is None:
        return None

    col = choose(row.index, candidates)

    if col is None:
        return None

    return safe_float(row.get(col))


def direction(
    latest: float | None,
    previous: float | None,
    lower_is_better: bool = False,
) -> str:
    """
    Flat means within 2% relative change.
    For values around zero, use absolute tolerance of 0.02.
    """

    if latest is None or previous is None:
        return "→"

    if abs(previous) > 1e-12:
        change = (latest - previous) / abs(previous)
    else:
        change = latest - previous

    if abs(change) <= 0.02:
        return "→"

    if lower_is_better:
        return "↑" if change < 0 else "↓"

    return "↑" if change > 0 else "↓"


def arrow_style(arrow: str) -> ParagraphStyle:
    if arrow == "↑":
        color = GREEN
    elif arrow == "↓":
        color = RED
    else:
        color = GRAY

    return ParagraphStyle(
        f"Arrow_{arrow}",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=15,
        alignment=TA_CENTER,
        textColor=color,
    )


styles = getSampleStyleSheet()

TITLE = ParagraphStyle(
    "PortfolioTitle",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=21,
    textColor=WHITE,
    alignment=TA_LEFT,
)

SUBTITLE = ParagraphStyle(
    "PortfolioSubtitle",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    textColor=GRAY,
)

SECTION = ParagraphStyle(
    "PortfolioSection",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
    textColor=NAVY,
)

BODY = ParagraphStyle(
    "PortfolioBody",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    textColor=DARK,
)

SMALL = ParagraphStyle(
    "PortfolioSmall",
    parent=BODY,
    fontSize=7,
    leading=8.5,
)

KPI_VALUE = ParagraphStyle(
    "KPIValue",
    parent=BODY,
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
    alignment=TA_CENTER,
    textColor=NAVY,
)

KPI_LABEL = ParagraphStyle(
    "KPILabel",
    parent=BODY,
    fontSize=7,
    leading=8,
    alignment=TA_CENTER,
    textColor=GRAY,
)


def build_kpi_table(ratio_latest, ratio_previous, pl_latest, pl_previous, cash_latest):
    metrics = [
        (
            "ROE",
            get_metric(ratio_latest, ["roe"]),
            get_metric(ratio_previous, ["roe"]),
            "%",
            False,
        ),
        (
            "ROCE",
            get_metric(ratio_latest, ["roce"]),
            get_metric(ratio_previous, ["roce"]),
            "%",
            False,
        ),
        (
            "Net Profit Margin",
            get_metric(ratio_latest, ["net_profit_margin", "npm"]),
            get_metric(ratio_previous, ["net_profit_margin", "npm"]),
            "%",
            False,
        ),
        (
            "D/E",
            get_metric(ratio_latest, ["debt_to_equity", "de"]),
            get_metric(ratio_previous, ["debt_to_equity", "de"]),
            "x",
            True,
        ),
        (
            "Revenue",
            get_metric(pl_latest, ["sales", "revenue"]),
            get_metric(pl_previous, ["sales", "revenue"]),
            "",
            False,
        ),
        (
            "FCF",
            get_metric(ratio_latest, ["free_cash_flow"]),
            get_metric(ratio_previous, ["free_cash_flow"]),
            "",
            False,
        ),
    ]

    cells = []

    for label, latest, previous, suffix, lower_is_better in metrics:
        arrow = direction(latest, previous, lower_is_better)
        cells.append(
            [
                Paragraph(clean_text(label), KPI_LABEL),
                Paragraph(fmt(latest, suffix), KPI_VALUE),
                Paragraph(arrow, arrow_style(arrow)),
            ]
        )

    # Two rows x three KPI tiles.
    table_rows = []

    for start in (0, 3):
        tile_row = []
        for cell in cells[start : start + 3]:
            tile = Table(
                [[cell[0]], [cell[1]], [cell[2]]],
                colWidths=[55 * mm],
                rowHeights=[7 * mm, 9 * mm, 7 * mm],
            )
            tile.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            tile_row.append(tile)

        table_rows.append(tile_row)

    outer = Table(
        table_rows,
        colWidths=[59 * mm, 59 * mm, 59 * mm],
        rowHeights=[25 * mm, 25 * mm],
        hAlign="LEFT",
    )

    outer.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    return outer


def build_company_page(
    ticker: str,
    company_name: str,
    sector: str,
    ratio_latest,
    ratio_previous,
    pl_latest,
    pl_previous,
    cash_latest,
):
    story = []

    header = Table(
        [
            [
                Paragraph(
                    f"{clean_text(company_name)} ({clean_text(ticker)})",
                    TITLE,
                )
            ]
        ],
        colWidths=[178 * mm],
        rowHeights=[18 * mm],
    )

    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(header)
    story.append(Spacer(1, 4))

    story.append(
        Paragraph(
            f"<b>Sector:</b> {clean_text(sector)}",
            BODY,
        )
    )

    latest_year = None
    year_col = choose(
        ratio_latest.index if ratio_latest is not None else [],
        ["year", "financial_year", "fy"],
    )

    if ratio_latest is not None and year_col:
        latest_year = clean_text(ratio_latest.get(year_col))

    if latest_year:
        story.append(
            Paragraph(
                f"<b>Latest available year:</b> {latest_year}",
                SUBTITLE,
            )
        )

    story.append(Spacer(1, 7))
    story.append(Paragraph("Top 6 KPIs", SECTION))
    story.append(Spacer(1, 3))

    story.append(
        build_kpi_table(
            ratio_latest,
            ratio_previous,
            pl_latest,
            pl_previous,
            cash_latest,
        )
    )

    story.append(Spacer(1, 8))
    story.append(Paragraph("Trend Legend", SECTION))
    story.append(
        Paragraph(
            "<b>↑</b> improved &nbsp;&nbsp; "
            "<b>↓</b> declined &nbsp;&nbsp; "
            "<b>→</b> flat within 2% of previous value",
            SMALL,
        )
    )

    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Trend arrows compare the latest two available observations. "
            "If historical data is insufficient, the metric is shown as N/A "
            "and the trend is neutral.",
            SMALL,
        )
    )

    return story


def main():
    print("=" * 70)
    print("DAY 35 - PORTFOLIO SUMMARY PDF")
    print("=" * 70)

    print("\nLoading database data...")

    companies, sectors, ratios, pl, cashflow = load_data()

    companies, company_id_col = normalize_ids(companies)
    ratios, _ = normalize_ids(ratios)
    pl, _ = normalize_ids(pl)
    cashflow, _ = normalize_ids(cashflow)

    sector_map = get_sector_map(sectors)

    print(f"Companies loaded : {len(companies)}")
    print(f"Historical ratios: {len(ratios)}")
    print(f"P&L rows         : {len(pl)}")
    print(f"Cashflow rows    : {len(cashflow)}")
    print(f"Sectors loaded   : {len(sectors)}")

    if "company_id" not in companies.columns:
        raise RuntimeError(
            "companies table does not contain a usable company ID column."
        )

    companies = (
        companies.dropna(subset=["company_id"])
        .drop_duplicates("company_id")
        .sort_values("company_id")
    )

    print("\nGenerating portfolio summary...")

    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Nifty 100 Portfolio Summary",
        author="N100 Financial Intelligence Platform",
    )

    story = []
    generated = 0
    failures = []

    name_col = choose(companies.columns, ["company_name", "name", "company"])

    for index, (_, company) in enumerate(companies.iterrows(), start=1):
        ticker = clean_text(company.get("company_id"), "").upper()

        if not ticker:
            failures.append("UNKNOWN")
            continue

        company_name = clean_text(company.get(name_col)) if name_col else ticker

        try:
            r_latest = latest_row(ratios, ticker)
            r_previous = previous_row(ratios, ticker)

            p_latest = latest_row(pl, ticker)
            p_previous = previous_row(pl, ticker)

            c_latest = latest_row(cashflow, ticker)

            sector = sector_map.get(ticker, "Unknown")

            story.extend(
                build_company_page(
                    ticker=ticker,
                    company_name=company_name,
                    sector=sector,
                    ratio_latest=r_latest,
                    ratio_previous=r_previous,
                    pl_latest=p_latest,
                    pl_previous=p_previous,
                    cash_latest=c_latest,
                )
            )

            generated += 1

            if index < len(companies):
                story.append(PageBreak())

            if index % 10 == 0 or index == len(companies):
                print(f"Processed {index}/{len(companies)} companies")

        except Exception as exc:
            failures.append(f"{ticker}: {exc}")

    if generated == 0:
        raise RuntimeError("No portfolio pages were generated.")

    doc.build(story)

    size_kb = OUTPUT_PATH.stat().st_size / 1024

    print("\n" + "-" * 70)
    print("DAY 35 VALIDATION")
    print("-" * 70)
    print(f"Companies expected : {len(companies)}")
    print(f"Pages generated    : {generated}")
    print(f"Generation failures: {len(failures)}")
    print(f"PDF size           : {size_kb:.1f} KB")

    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"  {failure}")

    print("\nOutput:")
    print(OUTPUT_PATH)

    if generated == len(companies) and not failures:
        print("\n✓ All company portfolio pages generated successfully.")
    else:
        raise RuntimeError(
            "Portfolio PDF validation failed. " "Check the failure list above."
        )

    print("\n" + "=" * 70)
    print("DAY 35 PORTFOLIO SUMMARY COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
