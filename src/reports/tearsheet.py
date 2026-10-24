"""
DAY 33 - COMPANY TEARSHEET PDF GENERATOR

Creates a 2-page company tearsheet using:
- SQLite database: database/n100.db
- output/pros_cons_generated.csv
- output/cashflow_intelligence.xlsx

Test companies:
TCS, HDFCBANK, RELIANCE, SUNPHARMA, TATASTEEL

Usage:
    python src/reports/tearsheet.py

The script is deliberately defensive about column names because the
project database contains scraped/normalized financial fields.
"""

from __future__ import annotations

import math
import re
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "database" / "n100.db"

OUTPUT_DIR = ROOT / "reports" / "tearsheets"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROS_CONS_PATH = ROOT / "output" / "pros_cons_generated.csv"
CASHFLOW_INTELLIGENCE_PATH = ROOT / "output" / "cashflow_intelligence.xlsx"

TEST_TICKERS = [
    "TCS",
    "HDFCBANK",
    "RELIANCE",
    "SUNPHARMA",
    "TATASTEEL",
]

NAVY = colors.HexColor("#12304A")
LIGHT_BLUE = colors.HexColor("#EAF2F8")
LIGHT_GREEN = colors.HexColor("#EAF7EE")
LIGHT_RED = colors.HexColor("#FDECEC")
GREEN = colors.HexColor("#198754")
RED = colors.HexColor("#C62828")
GRAY = colors.HexColor("#6B7280")
DARK = colors.HexColor("#172033")
WHITE = colors.white


# ============================================================
# HELPERS
# ============================================================


def clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default

    if isinstance(value, float) and math.isnan(value):
        return default

    text = str(value)
    text = text.replace("\\n", " ")
    text = re.sub(r"\s+", " ", text).strip()

    return text if text else default


def safe_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        value = float(value)
        if not np.isfinite(value):
            return None
        return value
    except (TypeError, ValueError):
        return None


def fmt_num(value: Any, decimals: int = 2, suffix: str = "") -> str:
    number = safe_float(value)

    if number is None:
        return "N/A"

    return f"{number:,.{decimals}f}{suffix}"


def fmt_pct(value: Any) -> str:
    number = safe_float(value)

    if number is None:
        return "N/A"

    return f"{number:.2f}%"


def sql_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [row[1] for row in rows]
    except sqlite3.Error:
        return []


def choose_column(
    columns: Iterable[str],
    candidates: Iterable[str],
) -> str | None:
    lookup = {str(c).lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    # Loose normalized comparison.
    def normalize(x: str) -> str:
        return re.sub(r"[^a-z0-9]", "", x.lower())

    normalized = {normalize(str(c)): c for c in columns}

    for candidate in candidates:
        key = normalize(candidate)
        if key in normalized:
            return normalized[key]

    return None


def year_value(value: Any) -> int | None:
    if value is None:
        return None

    match = re.search(r"(19|20)\d{2}", str(value))

    if not match:
        return None

    return int(match.group(0))


def sort_financial_year(df: pd.DataFrame, column: str = "year") -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return df.copy()

    result = df.copy()
    result["_year_num"] = result[column].apply(year_value)
    result = result.sort_values(
        ["_year_num", column],
        na_position="last",
    )
    return result.drop(columns=["_year_num"])


def get_year_label(value: Any) -> str:
    return clean_text(value, "N/A")


def make_chart_path(ticker: str, name: str) -> Path:
    safe_ticker = re.sub(r"[^A-Za-z0-9_-]", "_", ticker)
    return ROOT / "output" / f"_tearsheet_{safe_ticker}_{name}.png"


# ============================================================
# DATABASE LOADER
# ============================================================


class TearsheetData:
    def __init__(self) -> None:
        self.conn = sqlite3.connect(DB_PATH)

        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database not found: {DB_PATH}")

        self.companies = pd.read_sql_query(
            "SELECT * FROM companies",
            self.conn,
        )

        self.ratios = pd.read_sql_query(
            "SELECT * FROM historical_financial_ratios",
            self.conn,
        )

        self.pl = pd.read_sql_query(
            "SELECT * FROM profitandloss",
            self.conn,
        )

        self.bs = pd.read_sql_query(
            "SELECT * FROM balancesheet",
            self.conn,
        )

        self.cf = pd.read_sql_query(
            "SELECT * FROM cashflow",
            self.conn,
        )

        self.close()

        self.pros_cons = self._load_pros_cons()
        self.cashflow_intelligence = self._load_cashflow_intelligence()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def _load_pros_cons(self) -> pd.DataFrame:
        if not PROS_CONS_PATH.exists():
            return pd.DataFrame()

        try:
            return pd.read_csv(PROS_CONS_PATH)
        except Exception:
            return pd.DataFrame()

    def _load_cashflow_intelligence(self) -> pd.DataFrame:
        if not CASHFLOW_INTELLIGENCE_PATH.exists():
            return pd.DataFrame()

        try:
            return pd.read_excel(CASHFLOW_INTELLIGENCE_PATH)
        except Exception:
            return pd.DataFrame()

    def company(self, ticker: str) -> pd.Series | None:
        if self.companies.empty:
            return None

        id_col = choose_column(
            self.companies.columns,
            ["id", "company_id", "ticker"],
        )

        if id_col is None:
            return None

        mask = (
            self.companies[id_col].astype(str).str.strip().str.upper() == ticker.upper()
        )

        rows = self.companies.loc[mask]

        if rows.empty:
            return None

        return rows.iloc[0]

    def company_df(
        self,
        df: pd.DataFrame,
        ticker: str,
    ) -> pd.DataFrame:
        if df.empty:
            return df.copy()

        id_col = choose_column(
            df.columns,
            ["company_id", "id", "ticker"],
        )

        if id_col is None:
            return pd.DataFrame()

        result = df[
            df[id_col].astype(str).str.strip().str.upper() == ticker.upper()
        ].copy()

        year_col = choose_column(
            result.columns,
            ["year", "financial_year", "fy"],
        )

        if year_col:
            result = sort_financial_year(result, year_col)

        return result.reset_index(drop=True)

    def ratios_for(self, ticker: str) -> pd.DataFrame:
        return self.company_df(self.ratios, ticker)

    def pl_for(self, ticker: str) -> pd.DataFrame:
        return self.company_df(self.pl, ticker)

    def bs_for(self, ticker: str) -> pd.DataFrame:
        return self.company_df(self.bs, ticker)

    def cf_for(self, ticker: str) -> pd.DataFrame:
        return self.company_df(self.cf, ticker)

    def cashflow_row(self, ticker: str) -> pd.Series | None:
        if self.cashflow_intelligence.empty:
            return None

        id_col = choose_column(
            self.cashflow_intelligence.columns,
            ["company_id", "id", "ticker"],
        )

        if id_col is None:
            return None

        rows = self.cashflow_intelligence[
            self.cashflow_intelligence[id_col].astype(str).str.strip().str.upper()
            == ticker.upper()
        ]

        if rows.empty:
            return None

        return rows.iloc[0]

    def pros_cons_for(self, ticker: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        if self.pros_cons.empty:
            return pd.DataFrame(), pd.DataFrame()

        id_col = choose_column(
            self.pros_cons.columns,
            ["company_id", "id", "ticker"],
        )

        type_col = choose_column(
            self.pros_cons.columns,
            ["type"],
        )

        if id_col is None or type_col is None:
            return pd.DataFrame(), pd.DataFrame()

        rows = self.pros_cons[
            self.pros_cons[id_col].astype(str).str.strip().str.upper() == ticker.upper()
        ].copy()

        pros = rows[rows[type_col].astype(str).str.lower() == "pro"]

        cons = rows[rows[type_col].astype(str).str.lower() == "con"]

        return pros, cons


# ============================================================
# METRIC EXTRACTION
# ============================================================


def latest_value(
    df: pd.DataFrame,
    candidates: list[str],
) -> float | None:
    if df.empty:
        return None

    col = choose_column(df.columns, candidates)

    if col is None:
        return None

    for value in reversed(df[col].tolist()):
        number = safe_float(value)

        if number is not None:
            return number

    return None


def latest_text(
    df: pd.DataFrame,
    candidates: list[str],
) -> str:
    if df.empty:
        return "N/A"

    col = choose_column(df.columns, candidates)

    if col is None:
        return "N/A"

    for value in reversed(df[col].tolist()):
        text = clean_text(value)

        if text:
            return text

    return "N/A"


def five_year_cagr(
    df: pd.DataFrame,
    candidates: list[str],
) -> float | None:
    if df.empty:
        return None

    col = choose_column(df.columns, candidates)

    if col is None:
        return None

    values = pd.to_numeric(
        df[col],
        errors="coerce",
    )

    valid = values.dropna()

    if len(valid) < 6:
        return None

    start = safe_float(valid.iloc[-6])
    end = safe_float(valid.iloc[-1])

    if start is None or end is None:
        return None

    if start <= 0 or end <= 0:
        return None

    try:
        return ((end / start) ** (1 / 5) - 1) * 100
    except Exception:
        return None


def get_company_metrics(
    data: TearsheetData,
    ticker: str,
) -> dict[str, Any]:

    ratios = data.ratios_for(ticker)
    pl = data.pl_for(ticker)
    cf = data.cf_for(ticker)

    latest_ratio = ratios.iloc[-1] if not ratios.empty else None
    latest_pl = pl.iloc[-1] if not pl.empty else None
    latest_cf = cf.iloc[-1] if not cf.empty else None

    def row_value(row: pd.Series | None, candidates: list[str]):
        if row is None:
            return None

        col = choose_column(row.index, candidates)

        if col is None:
            return None

        return row.get(col)

    roe = row_value(latest_ratio, ["roe"])
    roce = row_value(latest_ratio, ["roce"])

    npm = row_value(
        latest_ratio,
        ["net_profit_margin", "npm"],
    )

    de = row_value(
        latest_ratio,
        ["debt_to_equity", "de"],
    )

    revenue_cagr = five_year_cagr(
        pl,
        ["sales", "revenue"],
    )

    fcf = row_value(
        latest_ratio,
        ["free_cash_flow", "fcf"],
    )

    if fcf is None:
        fcf = row_value(
            latest_cf,
            ["free_cash_flow"],
        )

    # If historical ratio ROE/ROCE are stored as decimals, convert
    # them to percentage form for display.
    roe_num = safe_float(roe)
    roce_num = safe_float(roce)
    npm_num = safe_float(npm)

    if roe_num is not None and abs(roe_num) <= 1.5:
        roe_num *= 100

    if roce_num is not None and abs(roce_num) <= 1.5:
        roce_num *= 100

    if npm_num is not None and abs(npm_num) <= 1.5:
        npm_num *= 100

    return {
        "roe": roe_num,
        "roce": roce_num,
        "npm": npm_num,
        "de": safe_float(de),
        "revenue_cagr_5yr": revenue_cagr,
        "fcf": safe_float(fcf),
    }


# ============================================================
# CHARTS
# ============================================================


def create_profit_revenue_chart(
    ticker: str,
    pl: pd.DataFrame,
) -> Path:

    path = make_chart_path(ticker, "profit_revenue")

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(10.5, 3.0),
        dpi=160,
    )

    if pl.empty:
        for ax in axes:
            ax.text(
                0.5,
                0.5,
                "Data unavailable",
                ha="center",
                va="center",
            )
            ax.axis("off")

        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    year_col = choose_column(
        pl.columns,
        ["year", "financial_year", "fy"],
    )

    sales_col = choose_column(
        pl.columns,
        ["sales", "revenue"],
    )

    profit_col = choose_column(
        pl.columns,
        ["net_profit", "profit_after_tax", "pat"],
    )

    years = (
        pl[year_col].astype(str).tolist()
        if year_col
        else [str(i + 1) for i in range(len(pl))]
    )

    sales = (
        pd.to_numeric(pl[sales_col], errors="coerce")
        if sales_col
        else pd.Series(dtype=float)
    )

    profit = (
        pd.to_numeric(pl[profit_col], errors="coerce")
        if profit_col
        else pd.Series(dtype=float)
    )

    x = np.arange(len(years))

    if sales_col:
        axes[0].bar(x, sales.fillna(0))
        axes[0].set_title("Revenue")
        axes[0].set_ylabel("Value")
    else:
        axes[0].text(0.5, 0.5, "Revenue unavailable", ha="center", va="center")
        axes[0].axis("off")

    if profit_col:
        axes[1].bar(x, profit.fillna(0))
        axes[1].set_title("Net Profit")
        axes[1].set_ylabel("Value")
    else:
        axes[1].text(0.5, 0.5, "Net Profit unavailable", ha="center", va="center")
        axes[1].axis("off")

    for ax in axes:
        if len(years) > 0:
            step = max(1, len(years) // 6)
            ax.set_xticks(x[::step])
            ax.set_xticklabels(
                years[::step],
                rotation=45,
                ha="right",
                fontsize=7,
            )
        ax.grid(axis="y", alpha=0.2)
        ax.tick_params(axis="both", labelsize=7)

    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)

    return path


def create_roe_roce_chart(
    ticker: str,
    ratios: pd.DataFrame,
) -> Path:

    path = make_chart_path(ticker, "roe_roce")

    fig, ax = plt.subplots(
        figsize=(10.5, 2.7),
        dpi=160,
    )

    if ratios.empty:
        ax.text(
            0.5,
            0.5,
            "ROE / ROCE data unavailable",
            ha="center",
            va="center",
        )
        ax.axis("off")
    else:
        year_col = choose_column(
            ratios.columns,
            ["year", "financial_year", "fy"],
        )

        roe_col = choose_column(
            ratios.columns,
            ["roe"],
        )

        roce_col = choose_column(
            ratios.columns,
            ["roce"],
        )

        years = (
            ratios[year_col].astype(str).tolist()
            if year_col
            else [str(i + 1) for i in range(len(ratios))]
        )

        x = np.arange(len(years))

        plotted = False

        if roe_col:
            roe = pd.to_numeric(
                ratios[roe_col],
                errors="coerce",
            )
            if roe.notna().any():
                if roe.abs().max() <= 1.5:
                    roe = roe * 100
                ax.plot(
                    x,
                    roe,
                    marker="o",
                    linewidth=1.8,
                    label="ROE",
                )
                plotted = True

        if roce_col:
            roce = pd.to_numeric(
                ratios[roce_col],
                errors="coerce",
            )
            if roce.notna().any():
                if roce.abs().max() <= 1.5:
                    roce = roce * 100
                ax.plot(
                    x,
                    roce,
                    marker="o",
                    linewidth=1.8,
                    label="ROCE",
                )
                plotted = True

        if plotted:
            step = max(1, len(years) // 8)
            ax.set_xticks(x[::step])
            ax.set_xticklabels(
                years[::step],
                rotation=45,
                ha="right",
                fontsize=7,
            )
            ax.set_ylabel("%")
            ax.set_title("ROE and ROCE — 10-Year Trend")
            ax.grid(alpha=0.2)
            ax.legend(
                loc="upper left",
                fontsize=7,
                frameon=False,
            )
        else:
            ax.text(
                0.5,
                0.5,
                "ROE / ROCE data unavailable",
                ha="center",
                va="center",
            )
            ax.axis("off")

    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)

    return path


def create_balance_chart(
    ticker: str,
    bs: pd.DataFrame,
) -> Path:

    path = make_chart_path(ticker, "balance_sheet")

    fig, ax = plt.subplots(
        figsize=(10.5, 2.8),
        dpi=160,
    )

    if bs.empty:
        ax.text(
            0.5,
            0.5,
            "Balance sheet data unavailable",
            ha="center",
            va="center",
        )
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    year_col = choose_column(
        bs.columns,
        ["year", "financial_year", "fy"],
    )

    equity_col = choose_column(
        bs.columns,
        [
            "shareholders_funds",
            "shareholder_funds",
            "equity",
            "net_worth",
            "networth",
        ],
    )

    borrowings_col = choose_column(
        bs.columns,
        [
            "borrowings",
            "total_borrowings",
            "debt",
            "borrowings_total",
        ],
    )

    liabilities_col = choose_column(
        bs.columns,
        [
            "total_liabilities",
            "liabilities",
            "total_liability",
        ],
    )

    years = (
        bs[year_col].astype(str).tolist()
        if year_col
        else [str(i + 1) for i in range(len(bs))]
    )

    equity = (
        pd.to_numeric(bs[equity_col], errors="coerce").fillna(0)
        if equity_col
        else pd.Series(0, index=bs.index)
    )

    borrowings = (
        pd.to_numeric(bs[borrowings_col], errors="coerce").fillna(0)
        if borrowings_col
        else pd.Series(0, index=bs.index)
    )

    if liabilities_col:
        liabilities = pd.to_numeric(
            bs[liabilities_col],
            errors="coerce",
        ).fillna(0)

        other = liabilities - equity - borrowings
        other = other.clip(lower=0)
    else:
        other = pd.Series(0, index=bs.index)

    x = np.arange(len(years))

    ax.bar(x, equity, label="Equity")
    ax.bar(
        x,
        borrowings,
        bottom=equity,
        label="Borrowings",
    )
    ax.bar(
        x,
        other,
        bottom=equity + borrowings,
        label="Other Liabilities",
    )

    step = max(1, len(years) // 8)

    ax.set_xticks(x[::step])
    ax.set_xticklabels(
        years[::step],
        rotation=45,
        ha="right",
        fontsize=7,
    )

    ax.set_title("Balance Sheet Composition")
    ax.tick_params(axis="y", labelsize=7)
    ax.legend(
        loc="upper left",
        fontsize=7,
        frameon=False,
        ncol=3,
    )
    ax.grid(axis="y", alpha=0.2)

    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)

    return path


# ============================================================
# REPORT STYLES
# ============================================================

styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "TearsheetTitle",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=16,
    leading=19,
    textColor=WHITE,
    alignment=TA_LEFT,
    spaceAfter=0,
)

SUBTITLE_STYLE = ParagraphStyle(
    "TearsheetSubtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=8.5,
    leading=10,
    textColor=colors.HexColor("#E5EDF5"),
)

SECTION_STYLE = ParagraphStyle(
    "Section",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=10.5,
    leading=12,
    textColor=NAVY,
    spaceBefore=2,
    spaceAfter=5,
)

BODY_STYLE = ParagraphStyle(
    "Body",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=7.6,
    leading=9.5,
    textColor=DARK,
)

SMALL_STYLE = ParagraphStyle(
    "Small",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=6.8,
    leading=8,
    textColor=DARK,
)

PRO_STYLE = ParagraphStyle(
    "Pro",
    parent=BODY_STYLE,
    textColor=colors.HexColor("#14532D"),
)

CON_STYLE = ParagraphStyle(
    "Con",
    parent=BODY_STYLE,
    textColor=colors.HexColor("#7F1D1D"),
)

CENTER_SMALL = ParagraphStyle(
    "CenterSmall",
    parent=SMALL_STYLE,
    alignment=TA_CENTER,
)


# ============================================================
# PDF BUILDING
# ============================================================


def header_table(
    company_name: str,
    ticker: str,
    sector: str,
) -> Table:

    title = Paragraph(
        f"<b>{clean_text(company_name, ticker)}</b>",
        TITLE_STYLE,
    )

    subtitle = Paragraph(
        f"{ticker}  •  {clean_text(sector, 'Sector unavailable')}",
        SUBTITLE_STYLE,
    )

    table = Table(
        [[title], [subtitle]],
        colWidths=[174 * mm],
        rowHeights=[10 * mm, 6 * mm],
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 4),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
                ("TOPPADDING", (0, 1), (-1, 1), 0),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 3),
            ]
        )
    )

    return table


def kpi_table(metrics: dict[str, Any]) -> Table:

    values = [
        ("ROE", fmt_pct(metrics["roe"])),
        ("ROCE", fmt_pct(metrics["roce"])),
        ("Net Profit Margin", fmt_pct(metrics["npm"])),
        ("D/E", fmt_num(metrics["de"])),
        ("Revenue CAGR 5Y", fmt_pct(metrics["revenue_cagr_5yr"])),
        ("FCF", fmt_num(metrics["fcf"])),
    ]

    rows = []

    for i in range(0, 6, 3):
        row = []

        for label, value in values[i : i + 3]:
            cell = Table(
                [
                    [
                        Paragraph(
                            f"<b>{label}</b>",
                            CENTER_SMALL,
                        )
                    ],
                    [
                        Paragraph(
                            f"<b>{value}</b>",
                            ParagraphStyle(
                                "KPIValue",
                                parent=CENTER_SMALL,
                                fontSize=11,
                                leading=13,
                                textColor=NAVY,
                            ),
                        )
                    ],
                ],
                colWidths=[54 * mm],
                rowHeights=[6 * mm, 10 * mm],
            )

            cell.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
                        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D7E5")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("TOPPADDING", (0, 0), (-1, -1), 1),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                    ]
                )
            )

            row.append(cell)

        rows.append(row)

    outer = Table(
        rows,
        colWidths=[56 * mm, 56 * mm, 56 * mm],
        rowHeights=[18 * mm, 18 * mm],
        hAlign="LEFT",
    )

    outer.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    return outer


def info_card(
    company: pd.Series,
) -> Table:

    columns = company.index

    name_col = choose_column(
        columns,
        ["company_name", "name"],
    )

    sector_col = choose_column(
        columns,
        ["sector", "broad_sector"],
    )

    sub_sector_col = choose_column(
        columns,
        ["sub_sector", "subsector", "industry"],
    )

    ticker_col = choose_column(
        columns,
        ["id", "company_id", "ticker"],
    )

    about_col = choose_column(
        columns,
        ["about_company", "about", "description"],
    )

    rows = [
        [
            Paragraph("<b>Company</b>", SMALL_STYLE),
            Paragraph(
                clean_text(
                    company.get(name_col) if name_col else None,
                    "N/A",
                ),
                SMALL_STYLE,
            ),
        ],
        [
            Paragraph("<b>NSE Ticker</b>", SMALL_STYLE),
            Paragraph(
                clean_text(
                    company.get(ticker_col) if ticker_col else None,
                    "N/A",
                ),
                SMALL_STYLE,
            ),
        ],
        [
            Paragraph("<b>Sector</b>", SMALL_STYLE),
            Paragraph(
                clean_text(
                    company.get(sector_col) if sector_col else None,
                    "N/A",
                ),
                SMALL_STYLE,
            ),
        ],
        [
            Paragraph("<b>Sub-sector</b>", SMALL_STYLE),
            Paragraph(
                clean_text(
                    company.get(sub_sector_col) if sub_sector_col else None,
                    "N/A",
                ),
                SMALL_STYLE,
            ),
        ],
        [
            Paragraph("<b>About</b>", SMALL_STYLE),
            Paragraph(
                clean_text(
                    company.get(about_col) if about_col else None,
                    "Description unavailable.",
                ),
                SMALL_STYLE,
            ),
        ],
    ]

    table = Table(
        rows,
        colWidths=[28 * mm, 146 * mm],
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F6F9")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D7DEE6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    return table


def pros_cons_table(
    pros: pd.DataFrame,
    cons: pd.DataFrame,
) -> Table:

    def extract_text(row: pd.Series) -> str:
        col = choose_column(
            row.index,
            ["text", "description", "reason"],
        )

        if col is None:
            return clean_text(row.to_dict())

        return clean_text(
            row.get(col),
            "Signal available.",
        )

    pro_items = [
        Paragraph(
            f"✓ {extract_text(row)}",
            PRO_STYLE,
        )
        for _, row in pros.head(6).iterrows()
    ]

    con_items = [
        Paragraph(
            f"✕ {extract_text(row)}",
            CON_STYLE,
        )
        for _, row in cons.head(6).iterrows()
    ]

    if not pro_items:
        pro_items = [Paragraph("✓ No generated pro available.", PRO_STYLE)]

    if not con_items:
        con_items = [Paragraph("✕ No generated con available.", CON_STYLE)]

    pro_cell = [
        Paragraph(
            "<b>PROS</b>",
            ParagraphStyle(
                "ProHead",
                parent=SMALL_STYLE,
                textColor=GREEN,
                fontName="Helvetica-Bold",
            ),
        ),
        Spacer(1, 2),
    ] + pro_items

    con_cell = [
        Paragraph(
            "<b>CONS</b>",
            ParagraphStyle(
                "ConHead",
                parent=SMALL_STYLE,
                textColor=RED,
                fontName="Helvetica-Bold",
            ),
        ),
        Spacer(1, 2),
    ] + con_items

    table = Table(
        [[pro_cell, con_cell]],
        colWidths=[87 * mm, 87 * mm],
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), LIGHT_GREEN),
                ("BACKGROUND", (1, 0), (1, 0), LIGHT_RED),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DCE3")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5DCE3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    return table


def capital_badge(label: str) -> Table:

    if not label or label == "N/A":
        label = "Unknown"

    badge = Table(
        [
            [
                Paragraph(
                    f"<b>CAPITAL ALLOCATION: {clean_text(label)}</b>",
                    ParagraphStyle(
                        "Badge",
                        parent=CENTER_SMALL,
                        fontSize=8,
                        textColor=WHITE,
                    ),
                )
            ]
        ],
        colWidths=[174 * mm],
        rowHeights=[9 * mm],
    )

    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    return badge


def latest_cashflow_table(
    cf: pd.DataFrame,
) -> Table:

    if cf.empty:
        return Table(
            [
                [
                    Paragraph(
                        "Cash-flow data unavailable.",
                        SMALL_STYLE,
                    )
                ]
            ],
            colWidths=[174 * mm],
        )

    row = cf.iloc[-1]

    year_col = choose_column(
        cf.columns,
        ["year", "financial_year", "fy"],
    )

    cfo_col = choose_column(
        cf.columns,
        ["operating_activity", "cfo"],
    )

    cfi_col = choose_column(
        cf.columns,
        ["investing_activity", "cfi"],
    )

    cff_col = choose_column(
        cf.columns,
        ["financing_activity", "cff"],
    )

    ncf_col = choose_column(
        cf.columns,
        ["net_cash_flow", "net_cash"],
    )

    values = [
        ("CFO", row.get(cfo_col) if cfo_col else None),
        ("CFI", row.get(cfi_col) if cfi_col else None),
        ("CFF", row.get(cff_col) if cff_col else None),
        ("Net Cash Flow", row.get(ncf_col) if ncf_col else None),
    ]

    title = (
        f"Latest Year: {clean_text(row.get(year_col), 'N/A')}"
        if year_col
        else "Latest Year"
    )

    rows = [
        [Paragraph(f"<b>{title}</b>", SMALL_STYLE), "", "", ""],
        [
            Paragraph("<b>CFO</b>", CENTER_SMALL),
            Paragraph("<b>CFI</b>", CENTER_SMALL),
            Paragraph("<b>CFF</b>", CENTER_SMALL),
            Paragraph("<b>Net Cash Flow</b>", CENTER_SMALL),
        ],
        [
            Paragraph(fmt_num(values[0][1]), CENTER_SMALL),
            Paragraph(fmt_num(values[1][1]), CENTER_SMALL),
            Paragraph(fmt_num(values[2][1]), CENTER_SMALL),
            Paragraph(fmt_num(values[3][1]), CENTER_SMALL),
        ],
    ]

    table = Table(
        rows,
        colWidths=[43.5 * mm] * 4,
    )

    table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F6F9")),
                ("BACKGROUND", (0, 1), (-1, 1), LIGHT_BLUE),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5DCE3")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    return table


# ============================================================
# SINGLE TEARSHEET
# ============================================================


def build_tearsheet(
    data: TearsheetData,
    ticker: str,
    output_path: Path | None = None,
) -> Path | None:

    company = data.company(ticker)

    if company is None:
        print(f"{ticker}: company not found")
        return None

    company_name_col = choose_column(
        company.index,
        ["company_name", "name"],
    )

    sector_col = choose_column(
        company.index,
        ["sector", "broad_sector"],
    )

    company_name = clean_text(
        company.get(company_name_col) if company_name_col else None,
        ticker,
    )

    sector = clean_text(
        company.get(sector_col) if sector_col else None,
        "N/A",
    )

    ratios = data.ratios_for(ticker)
    pl = data.pl_for(ticker)
    bs = data.bs_for(ticker)
    cf = data.cf_for(ticker)

    metrics = get_company_metrics(
        data,
        ticker,
    )

    pros, cons = data.pros_cons_for(ticker)

    cfi = data.cashflow_row(ticker)

    capital_label = "Unknown"

    if cfi is not None:
        capital_col = choose_column(
            cfi.index,
            [
                "capital_allocation_label",
                "capital_allocation_pattern",
            ],
        )

        if capital_col:
            capital_label = clean_text(
                cfi.get(capital_col),
                "Unknown",
            )

    if output_path is None:
        output_path = OUTPUT_DIR / f"{ticker}_tearsheet.pdf"

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    revenue_profit_chart = create_profit_revenue_chart(
        ticker,
        pl,
    )

    roe_roce_chart = create_roe_roce_chart(
        ticker,
        ratios,
    )

    balance_chart = create_balance_chart(
        ticker,
        bs,
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"{company_name} ({ticker}) Tearsheet",
        author="Nifty 100 Financial Intelligence Platform",
        allowSplitting=1,
    )

    story = []

    # --------------------------------------------------------
    # PAGE 1
    # --------------------------------------------------------

    story.append(
        header_table(
            company_name,
            ticker,
            sector,
        )
    )

    story.append(Spacer(1, 4))

    story.append(info_card(company))

    story.append(Spacer(1, 4))

    story.append(
        Paragraph(
            "Key Financial Indicators",
            SECTION_STYLE,
        )
    )

    story.append(kpi_table(metrics))

    story.append(Spacer(1, 4))

    story.append(
        Paragraph(
            "Revenue and Net Profit — 10-Year Trend",
            SECTION_STYLE,
        )
    )

    story.append(
        Image(
            str(revenue_profit_chart),
            width=174 * mm,
            height=50 * mm,
        )
    )

    story.append(Spacer(1, 2))

    story.append(
        Paragraph(
            "Return Efficiency Trend",
            SECTION_STYLE,
        )
    )

    story.append(
        Image(
            str(roe_roce_chart),
            width=174 * mm,
            height=45 * mm,
        )
    )

    story.append(PageBreak())

    # --------------------------------------------------------
    # PAGE 2
    # --------------------------------------------------------

    story.append(
        header_table(
            company_name,
            ticker,
            sector,
        )
    )

    story.append(Spacer(1, 5))

    story.append(
        Paragraph(
            "Balance Sheet Composition",
            SECTION_STYLE,
        )
    )

    story.append(
        Image(
            str(balance_chart),
            width=174 * mm,
            height=48 * mm,
        )
    )

    story.append(Spacer(1, 3))

    story.append(
        Paragraph(
            "Latest-Year Cash Flow",
            SECTION_STYLE,
        )
    )

    story.append(latest_cashflow_table(cf))

    story.append(Spacer(1, 5))

    story.append(
        pros_cons_table(
            pros,
            cons,
        )
    )

    story.append(Spacer(1, 5))

    story.append(capital_badge(capital_label))

    doc.build(story)

    # Clean temporary chart files after PDF creation.
    for chart_path in [
        revenue_profit_chart,
        roe_roce_chart,
        balance_chart,
    ]:
        try:
            chart_path.unlink(missing_ok=True)
        except Exception:
            pass

    return output_path


# ============================================================
# VALIDATION
# ============================================================


def validate_pdf(path: Path) -> dict[str, Any]:

    result = {
        "exists": path.exists(),
        "size_kb": 0.0,
        "valid_size": False,
    }

    if path.exists():
        size = path.stat().st_size
        result["size_kb"] = size / 1024
        result["valid_size"] = size > 30 * 1024

    return result


def main() -> None:

    print("=" * 70)
    print("DAY 33 - PDF TEARSHEET TEMPLATE")
    print("=" * 70)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    print("\nLoading database data...")

    data = TearsheetData()

    print(f"Companies loaded : {len(data.companies)}")
    print(f"Historical ratios: {len(data.ratios)}")
    print(f"P&L rows         : {len(data.pl)}")
    print(f"Balance rows     : {len(data.bs)}")
    print(f"Cashflow rows    : {len(data.cf)}")
    print(f"Pros/cons rows   : {len(data.pros_cons)}")

    print("\n" + "-" * 70)
    print("TEST TEARSHEETS")
    print("-" * 70)

    results = []

    for ticker in TEST_TICKERS:

        print(f"\nGenerating {ticker}...")

        path = build_tearsheet(
            data,
            ticker,
            OUTPUT_DIR / f"{ticker}_tearsheet.pdf",
        )

        if path is None:
            results.append(
                {
                    "ticker": ticker,
                    "status": "FAILED",
                    "size_kb": 0,
                }
            )
            continue

        validation = validate_pdf(path)

        status = "PASS" if validation["exists"] else "FAILED"

        print(f"{ticker}: {status} | " f"{validation['size_kb']:.1f} KB | " f"{path}")

        results.append(
            {
                "ticker": ticker,
                "status": status,
                "size_kb": validation["size_kb"],
            }
        )

    results_df = pd.DataFrame(results)

    print("\n" + "-" * 70)
    print("DAY 33 VALIDATION")
    print("-" * 70)

    print(f"Test companies : {len(TEST_TICKERS)}")
    print(f"PDFs generated : " f"{(results_df['status'] == 'PASS').sum()}")

    print("\nTest results:")
    print(results_df.to_string(index=False))

    if len(results_df) == len(TEST_TICKERS) and (results_df["status"] == "PASS").all():
        print("\n✓ All 5 test tearsheets generated successfully.")
    else:
        print("\n⚠ Some test tearsheets failed.")

    print("\nOutput directory:")
    print(OUTPUT_DIR)

    print("\n" + "=" * 70)
    print("DAY 33 TEARSHEET TEMPLATE COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
