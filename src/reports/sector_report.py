"""
DAY 34 - sector REPORT GENERATOR

Generates one PDF for each sector using data from database/n100.db.

Usage:
    python src/reports/sector_report.py
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "database" / "n100.db"
OUTPUT_DIR = ROOT / "reports" / "sector"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#12304A")
LIGHT_BLUE = colors.HexColor("#EAF2F8")
GRAY = colors.HexColor("#6B7280")
DARK = colors.HexColor("#172033")
WHITE = colors.white


def clean_text(value: Any, default: str = "N/A") -> str:
    if value is None:
        return default
    text = re.sub(r"\s+", " ", str(value).replace("\\n", " ")).strip()
    return text if text else default


def safe_float(value: Any) -> float | None:
    try:
        value = float(value)
        if np.isfinite(value):
            return value
    except (TypeError, ValueError):
        pass
    return None


def fmt(value: Any, suffix: str = "") -> str:
    x = safe_float(value)
    return "N/A" if x is None else f"{x:.2f}{suffix}"


def choose(columns, candidates):
    lookup = {str(c).lower(): c for c in columns}
    for c in candidates:
        if c.lower() in lookup:
            return lookup[c.lower()]

    def norm(x):
        return re.sub(r"[^a-z0-9]", "", str(x).lower())

    normalized = {norm(c): c for c in columns}
    for c in candidates:
        if norm(c) in normalized:
            return normalized[norm(c)]

    return None


def year_num(value):
    match = re.search(r"(19|20)\d{2}", str(value))
    return int(match.group()) if match else -1


styles = getSampleStyleSheet()

TITLE = ParagraphStyle(
    "sectorTitle",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=17,
    leading=20,
    textColor=WHITE,
    alignment=TA_CENTER,
)

SECTION = ParagraphStyle(
    "sectorSection",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
    textColor=NAVY,
)

BODY = ParagraphStyle(
    "sectorBody",
    parent=styles["BodyText"],
    fontSize=7.2,
    leading=9,
    textColor=DARK,
)

SMALL = ParagraphStyle(
    "sectorSmall",
    parent=BODY,
    fontSize=6.5,
    leading=8,
)


def load_data():
    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query("SELECT * FROM companies", conn)

    sectors = pd.read_sql_query("SELECT * FROM sectors", conn)

    ratios = pd.read_sql_query("SELECT * FROM historical_financial_ratios", conn)

    pl = pd.read_sql_query("SELECT * FROM profitandloss", conn)

    market = pd.read_sql_query("SELECT * FROM market_cap", conn)

    conn.close()

    return companies, sectors, ratios, pl, market


def normalize_company_sector(companies, sectors):
    company_id = choose(
        companies.columns,
        ["id", "company_id", "ticker"],
    )

    sector_id = choose(
        sectors.columns,
        ["company_id", "id", "ticker"],
    )

    sector_col = choose(
        sectors.columns,
        [
            "broad_sector",
            "sector",
            "sector_name",
            "industry",
        ],
    )

    if company_id is None:
        raise RuntimeError("companies table has no company ID column.")

    result = companies.copy()

    result["company_id"] = result[company_id].astype(str).str.strip().str.upper()

    if sector_col is not None and sector_id is not None:
        sector_map = sectors[[sector_id, sector_col]].copy()

        sector_map["company_id"] = (
            sector_map[sector_id].astype(str).str.strip().str.upper()
        )

        sector_map["sector_name"] = sector_map[sector_col].astype(str).str.strip()

        sector_map = sector_map[["company_id", "sector_name"]].drop_duplicates(
            "company_id"
        )

        result = result.merge(
            sector_map,
            on="company_id",
            how="left",
        )

    else:
        direct_sector = choose(
            result.columns,
            ["broad_sector", "sector", "sector_name"],
        )

        if direct_sector:
            result["sector_name"] = result[direct_sector].astype(str).str.strip()
        else:
            result["sector_name"] = "Unknown"

    result["sector_name"] = (
        result["sector_name"]
        .replace({"nan": "Unknown", "None": "Unknown"})
        .fillna("Unknown")
    )

    return result


def latest_ratios(ratios):
    if ratios.empty:
        return ratios

    id_col = choose(
        ratios.columns,
        ["company_id", "id", "ticker"],
    )
    year_col = choose(
        ratios.columns,
        ["year", "financial_year", "fy"],
    )

    if id_col is None:
        return pd.DataFrame()

    result = ratios.copy()

    result["company_id"] = result[id_col].astype(str).str.strip().str.upper()

    if year_col:
        result["_year"] = result[year_col].apply(year_num)
        result = (
            result.sort_values("_year").groupby("company_id", as_index=False).tail(1)
        )
        result = result.drop(columns=["_year"])

    return result


def latest_market(market):
    if market.empty:
        return market

    id_col = choose(
        market.columns,
        ["company_id", "id", "ticker"],
    )
    year_col = choose(
        market.columns,
        ["year", "financial_year", "fy"],
    )

    if id_col is None:
        return pd.DataFrame()

    result = market.copy()

    result["company_id"] = result[id_col].astype(str).str.strip().str.upper()

    if year_col:
        result["_year"] = result[year_col].apply(year_num)
        result = (
            result.sort_values("_year").groupby("company_id", as_index=False).tail(1)
        )
        result = result.drop(columns=["_year"])

    return result


def five_year_revenue_cagr(pl, company_id):
    if pl.empty:
        return None

    id_col = choose(
        pl.columns,
        ["company_id", "id", "ticker"],
    )
    year_col = choose(
        pl.columns,
        ["year", "financial_year", "fy"],
    )
    sales_col = choose(
        pl.columns,
        ["sales", "revenue"],
    )

    if not all([id_col, sales_col]):
        return None

    df = pl[pl[id_col].astype(str).str.strip().str.upper() == company_id].copy()

    if year_col:
        df["_year"] = df[year_col].apply(year_num)
        df = df.sort_values("_year")

    values = pd.to_numeric(
        df[sales_col],
        errors="coerce",
    ).dropna()

    if len(values) < 6:
        return None

    start = safe_float(values.iloc[-6])
    end = safe_float(values.iloc[-1])

    if start is None or end is None or start <= 0 or end <= 0:
        return None

    return ((end / start) ** (1 / 5) - 1) * 100


def build_sector_dataset(companies, sectors, ratios, pl, market):
    master = normalize_company_sector(companies, sectors)

    latest_r = latest_ratios(ratios)
    latest_m = latest_market(market)

    rid = choose(latest_r.columns, ["company_id"])
    mid = choose(latest_m.columns, ["company_id"])

    if rid:
        latest_r["company_id"] = latest_r[rid].astype(str).str.strip().str.upper()

    if mid:
        latest_m["company_id"] = latest_m[mid].astype(str).str.strip().str.upper()

    data = master[["company_id", "sector_name"]].drop_duplicates("company_id")

    if rid:
        data = data.merge(
            latest_r,
            on="company_id",
            how="left",
            suffixes=("", "_ratio"),
        )

    if mid:
        data = data.merge(
            latest_m,
            on="company_id",
            how="left",
            suffixes=("", "_market"),
        )

    # Revenue and 5Y CAGR are included for useful sector context.
    cagr_map = {cid: five_year_revenue_cagr(pl, cid) for cid in data["company_id"]}
    data["revenue_cagr_5yr"] = data["company_id"].map(cagr_map)

    return data, master


def median_metric(df, candidates):
    col = choose(df.columns, candidates)
    if col is None:
        return None
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    return values.median() if not values.empty else None


def sector_summary_rows(sector_df):
    return [
        [
            Paragraph("<b>Metric</b>", SMALL),
            Paragraph("<b>sector Median</b>", SMALL),
        ],
        [
            Paragraph("ROE", SMALL),
            Paragraph(fmt(median_metric(sector_df, ["roe"]), "%"), SMALL),
        ],
        [
            Paragraph("ROCE", SMALL),
            Paragraph(fmt(median_metric(sector_df, ["roce"]), "%"), SMALL),
        ],
        [
            Paragraph("P/E", SMALL),
            Paragraph(fmt(median_metric(sector_df, ["pe_ratio", "pe"])), SMALL),
        ],
        [
            Paragraph("P/B", SMALL),
            Paragraph(fmt(median_metric(sector_df, ["pb_ratio", "pb"])), SMALL),
        ],
        [
            Paragraph("EV/EBITDA", SMALL),
            Paragraph(fmt(median_metric(sector_df, ["ev_ebitda"])), SMALL),
        ],
        [
            Paragraph("Revenue CAGR 5Y", SMALL),
            Paragraph(fmt(median_metric(sector_df, ["revenue_cagr_5yr"]), "%"), SMALL),
        ],
    ]


def build_sector_pdf(sector_name, sector_df, master, output_path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=f"{sector_name} - Nifty 100 sector Report",
    )

    story = []

    header = Table(
        [
            [
                Paragraph(
                    f"{clean_text(sector_name, 'Unknown sector')} — sector Report",
                    TITLE,
                )
            ]
        ],
        colWidths=[277 * mm],
        rowHeights=[15 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.append(header)
    story.append(Spacer(1, 5))

    story.append(
        Paragraph(
            f"<b>Companies in sector: {len(sector_df)}</b>",
            SECTION,
        )
    )
    story.append(Spacer(1, 3))

    summary = Table(
        sector_summary_rows(sector_df),
        colWidths=[48 * mm, 45 * mm],
    )
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D5DCE3")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    story.append(summary)
    story.append(Spacer(1, 6))

    story.append(
        Paragraph(
            "Company Comparison — Latest Available Data",
            SECTION,
        )
    )

    name_col = choose(
        master.columns,
        ["company_name", "name"],
    )

    rows = [
        [
            Paragraph("<b>Ticker</b>", SMALL),
            Paragraph("<b>Company</b>", SMALL),
            Paragraph("<b>ROE</b>", SMALL),
            Paragraph("<b>ROCE</b>", SMALL),
            Paragraph("<b>P/E</b>", SMALL),
            Paragraph("<b>P/B</b>", SMALL),
            Paragraph("<b>EV/EBITDA</b>", SMALL),
            Paragraph("<b>Revenue CAGR 5Y</b>", SMALL),
        ]
    ]

    for _, row in sector_df.sort_values("company_id").iterrows():
        rows.append(
            [
                Paragraph(clean_text(row.get("company_id")), SMALL),
                Paragraph(
                    clean_text(row.get(name_col)) if name_col else "N/A",
                    SMALL,
                ),
                Paragraph(fmt(row.get(choose(row.index, ["roe"])), "%"), SMALL),
                Paragraph(fmt(row.get(choose(row.index, ["roce"])), "%"), SMALL),
                Paragraph(fmt(row.get(choose(row.index, ["pe_ratio", "pe"]))), SMALL),
                Paragraph(fmt(row.get(choose(row.index, ["pb_ratio", "pb"]))), SMALL),
                Paragraph(fmt(row.get(choose(row.index, ["ev_ebitda"]))), SMALL),
                Paragraph(fmt(row.get("revenue_cagr_5yr"), "%"), SMALL),
            ]
        )

    company_table = Table(
        rows,
        repeatRows=1,
        colWidths=[
            25 * mm,
            70 * mm,
            25 * mm,
            25 * mm,
            25 * mm,
            25 * mm,
            30 * mm,
            35 * mm,
        ],
    )

    company_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D5DCE3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )

    story.append(company_table)

    doc.build(story)


def main():
    print("=" * 70)
    print("DAY 34 - sector REPORT GENERATION")
    print("=" * 70)

    companies, sectors, ratios, pl, market = load_data()

    print(f"Companies loaded : {len(companies)}")
    print(f"sector rows      : {len(sectors)}")
    print(f"Ratio rows       : {len(ratios)}")
    print(f"P&L rows         : {len(pl)}")
    print(f"Market rows      : {len(market)}")

    data, master = build_sector_dataset(
        companies,
        sectors,
        ratios,
        pl,
        market,
    )

    sector_names = sorted(
        data["sector_name"].astype(str).str.strip().replace({"": "Unknown"}).unique()
    )

    print(f"\nsectors found: {len(sector_names)}")

    generated = 0

    for sector in sector_names:
        sector_df = data[data["sector_name"].astype(str).str.strip() == sector].copy()

        filename = re.sub(r"[^A-Za-z0-9_-]+", "_", sector).strip("_") or "Unknown"

        output_path = OUTPUT_DIR / f"{filename}_report.pdf"

        build_sector_pdf(
            sector,
            sector_df,
            master,
            output_path,
        )

        generated += 1

        print(f"{sector}: {len(sector_df)} companies -> " f"{output_path.name}")

    print("\n" + "-" * 70)
    print("sector REPORT VALIDATION")
    print("-" * 70)
    print(f"sector PDFs generated : {generated}")
    print(f"Output directory      : {OUTPUT_DIR}")

    print("\n" + "=" * 70)
    print("SECTOR REPORT GENERATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
