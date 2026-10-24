"""
Day 40 - Portfolio Statistics API

Endpoint:
    GET /api/v1/portfolio/stats

Returns P10, P25, P50, P75 and P90
statistics for the 10 core KPIs across
the N100 company universe.
"""

import math
import sqlite3
from collections import defaultdict

from fastapi import APIRouter

# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio"],
)


# ============================================================
# DATABASE
# ============================================================

DB_PATH = "database/n100.db"


def get_connection():
    """
    Create SQLite connection with Row factory.
    """

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# PERCENTILE HELPER
# ============================================================


def percentile(values, percentile):
    """
    Calculate a percentile using linear interpolation.
    """

    clean_values = [
        float(value)
        for value in values
        if value is not None
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    ]

    if not clean_values:
        return None

    clean_values.sort()

    if len(clean_values) == 1:
        return round(clean_values[0], 2)

    position = (len(clean_values) - 1) * percentile

    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return round(clean_values[lower], 2)

    weight = position - lower

    result = clean_values[lower] + weight * (clean_values[upper] - clean_values[lower])

    return round(result, 2)


# ============================================================
# YEAR PARSER
# ============================================================


def extract_year(year_value):
    """
    Extract a four-digit financial year from values
    such as 'Mar 2024'.
    """

    if year_value is None:
        return None

    text = str(year_value).strip()

    parts = text.split()

    for part in parts:
        if len(part) == 4 and part.isdigit():
            return int(part)

    return None


# ============================================================
# CAGR HELPER
# ============================================================


def calculate_cagr(start_value, end_value, years):
    """
    Calculate CAGR percentage.

    Returns None when CAGR cannot be calculated.
    """

    if start_value is None or end_value is None or years <= 0:
        return None

    try:
        start_value = float(start_value)
        end_value = float(end_value)

        if start_value <= 0:
            return None

        if end_value <= 0:
            return None

        result = ((end_value / start_value) ** (1 / years) - 1) * 100

        if not math.isfinite(result):
            return None

        return result

    except (TypeError, ValueError, ZeroDivisionError):
        return None


# ============================================================
# LATEST FINANCIAL RATIOS
# ============================================================


def get_latest_ratios(conn):
    """
    Return the latest historical ratio record
    for each company.
    """

    rows = conn.execute("""
        SELECT
            company_id,
            year,
            roe,
            roce,
            debt_to_equity,
            interest_coverage,
            asset_turnover,
            net_profit_margin,
            free_cash_flow
        FROM (
            SELECT
                r.*,
                ROW_NUMBER() OVER (
                    PARTITION BY company_id
                    ORDER BY
                        CAST(
                            substr(
                                year,
                                -4
                            ) AS INTEGER
                        ) DESC,
                        id DESC
                ) AS rn
            FROM historical_financial_ratios r
        )
        WHERE rn = 1
        """).fetchall()

    return rows


# ============================================================
# PROFIT & LOSS DATA
# ============================================================


def get_profit_loss(conn):
    """
    Return annual P&L records required for CAGR
    calculations.
    """

    rows = conn.execute("""
        SELECT
            company_id,
            year,
            sales,
            net_profit,
            eps
        FROM profitandloss
        WHERE year LIKE 'Mar %'
        ORDER BY
            company_id,
            CAST(
                substr(
                    year,
                    -4
                ) AS INTEGER
            )
        """).fetchall()

    return rows


# ============================================================
# BUILD CAGR DATA
# ============================================================


def build_cagr_data(rows):
    """
    Calculate 5-year Revenue, PAT and EPS CAGR
    for each company using the latest available
    five-year annual period.
    """

    company_data = defaultdict(list)

    for row in rows:

        year = extract_year(row["year"])

        if year is None:
            continue

        company_data[row["company_id"]].append(
            {
                "year": year,
                "sales": row["sales"],
                "net_profit": row["net_profit"],
                "eps": row["eps"],
            }
        )

    result = {}

    for company_id, records in company_data.items():

        records.sort(key=lambda item: item["year"])

        # ----------------------------------------------------
        # Search from the latest year backwards.
        # Prefer an exact 5-year period.
        # ----------------------------------------------------

        latest = records[-1]

        start_record = None

        target_year = latest["year"] - 5

        for record in records:

            if record["year"] == target_year:
                start_record = record
                break

        # ----------------------------------------------------
        # If exact 5-year record is unavailable,
        # do not invent a CAGR.
        # ----------------------------------------------------

        if start_record is None:

            result[company_id] = {
                "revenue_cagr": None,
                "pat_cagr": None,
                "eps_cagr": None,
            }

            continue

        result[company_id] = {
            "revenue_cagr": calculate_cagr(
                start_record["sales"],
                latest["sales"],
                5,
            ),
            "pat_cagr": calculate_cagr(
                start_record["net_profit"],
                latest["net_profit"],
                5,
            ),
            "eps_cagr": calculate_cagr(
                start_record["eps"],
                latest["eps"],
                5,
            ),
        }

    return result


# ============================================================
# ROOT / MODULE CHECK
# ============================================================


@router.get("")
def portfolio_root():
    """
    Check portfolio module availability.
    """

    return {
        "module": "portfolio",
        "status": "ready",
    }


# ============================================================
# PORTFOLIO STATISTICS
# ============================================================


@router.get("/stats")
def portfolio_stats():
    """
    Return P10, P25, P50, P75 and P90 statistics
    for the 10 core KPIs across all companies.
    """

    conn = get_connection()

    try:

        # ----------------------------------------------------
        # LOAD DATA
        # ----------------------------------------------------

        ratio_rows = get_latest_ratios(conn)

        pl_rows = get_profit_loss(conn)

        cagr_data = build_cagr_data(pl_rows)

        # ----------------------------------------------------
        # KPI COLLECTIONS
        # ----------------------------------------------------

        metrics = {
            "Asset Turnover": [],
            "Debt to Equity": [],
            "EPS CAGR": [],
            "Free Cash Flow": [],
            "Interest Coverage": [],
            "Net Profit Margin": [],
            "PAT CAGR": [],
            "ROCE": [],
            "ROE": [],
            "Revenue CAGR": [],
        }

        companies_with_data = set()

        # ----------------------------------------------------
        # ADD LATEST RATIO DATA
        # ----------------------------------------------------

        for row in ratio_rows:

            company_id = row["company_id"]

            companies_with_data.add(company_id)

            metrics["Asset Turnover"].append(row["asset_turnover"])

            metrics["Debt to Equity"].append(row["debt_to_equity"])

            metrics["Free Cash Flow"].append(row["free_cash_flow"])

            metrics["Interest Coverage"].append(row["interest_coverage"])

            metrics["Net Profit Margin"].append(row["net_profit_margin"])

            metrics["ROCE"].append(row["roce"])

            metrics["ROE"].append(row["roe"])

        # ----------------------------------------------------
        # ADD CAGR DATA
        # ----------------------------------------------------

        for company_id, values in cagr_data.items():

            if values["eps_cagr"] is not None:
                metrics["EPS CAGR"].append(values["eps_cagr"])

            if values["pat_cagr"] is not None:
                metrics["PAT CAGR"].append(values["pat_cagr"])

            if values["revenue_cagr"] is not None:
                metrics["Revenue CAGR"].append(values["revenue_cagr"])

        # ----------------------------------------------------
        # BUILD STATISTICS
        # ----------------------------------------------------

        statistics = {}

        for metric_name, values in metrics.items():

            clean_values = [
                float(value)
                for value in values
                if value is not None
                and isinstance(value, (int, float))
                and math.isfinite(float(value))
            ]

            statistics[metric_name] = {
                "count": len(clean_values),
                "p10": percentile(
                    clean_values,
                    0.10,
                ),
                "p25": percentile(
                    clean_values,
                    0.25,
                ),
                "p50": percentile(
                    clean_values,
                    0.50,
                ),
                "p75": percentile(
                    clean_values,
                    0.75,
                ),
                "p90": percentile(
                    clean_values,
                    0.90,
                ),
            }

        # ----------------------------------------------------
        # COMPANY COUNT
        # ----------------------------------------------------

        company_count = conn.execute("""
            SELECT COUNT(*)
            FROM companies
            """).fetchone()[0]

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {
            "company_count": company_count,
            "metric_count": len(metrics),
            "percentiles": [
                "P10",
                "P25",
                "P50",
                "P75",
                "P90",
            ],
            "statistics": statistics,
        }

    finally:
        conn.close()
