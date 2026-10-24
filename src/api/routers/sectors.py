"""
Day 40 - Sector API

Endpoints:
    GET /api/v1/sectors
    GET /api/v1/sectors/{sector}/companies
"""

import sqlite3

from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/sectors",
    tags=["Sectors"],
)


DB_PATH = "database/n100.db"


def get_connection():
    """
    Create SQLite connection with Row factory.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# GET ALL SECTORS
# ============================================================


@router.get("")
def get_sectors():
    """
    Return all sectors with:

    - company_count
    - median_roe
    - median_pe
    - median_de

    The source database contains 10 broad sectors.
    Utilities is exposed as a derived API sector from
    power/utility sub-sectors.
    """

    conn = get_connection()

    try:

        query = """
        WITH
        latest_ratios AS (
            SELECT
                company_id,
                roe,
                debt_to_equity
            FROM (
                SELECT
                    r.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY r.company_id
                        ORDER BY r.year DESC, r.id DESC
                    ) AS rn
                FROM historical_financial_ratios r
            )
            WHERE rn = 1
        ),

        latest_market AS (
            SELECT
                company_id,
                pe_ratio
            FROM (
                SELECT
                    m.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY m.company_id
                        ORDER BY m.year DESC, m.id DESC
                    ) AS rn
                FROM market_cap m
            )
            WHERE rn = 1
        ),

        company_metrics AS (
            SELECT
                s.company_id,
                s.broad_sector,
                r.roe,
                r.debt_to_equity,
                m.pe_ratio
            FROM sectors s

            LEFT JOIN latest_ratios r
                ON s.company_id = r.company_id

            LEFT JOIN latest_market m
                ON s.company_id = m.company_id
        )

        SELECT
            broad_sector AS sector,

            COUNT(DISTINCT company_id) AS company_count,

            (
                SELECT AVG(roe)
                FROM (
                    SELECT
                        cm2.roe,

                        ROW_NUMBER() OVER (
                            ORDER BY cm2.roe
                        ) AS rn,

                        COUNT(cm2.roe) OVER () AS total

                    FROM company_metrics cm2

                    WHERE
                        cm2.broad_sector = cm.broad_sector
                        AND cm2.roe IS NOT NULL
                )

                WHERE rn IN (
                    (total + 1) / 2,
                    (total + 2) / 2
                )
            ) AS median_roe,

            (
                SELECT AVG(pe_ratio)
                FROM (
                    SELECT
                        cm3.pe_ratio,

                        ROW_NUMBER() OVER (
                            ORDER BY cm3.pe_ratio
                        ) AS rn,

                        COUNT(cm3.pe_ratio) OVER () AS total

                    FROM company_metrics cm3

                    WHERE
                        cm3.broad_sector = cm.broad_sector
                        AND cm3.pe_ratio IS NOT NULL
                )

                WHERE rn IN (
                    (total + 1) / 2,
                    (total + 2) / 2
                )
            ) AS median_pe,

            (
                SELECT AVG(debt_to_equity)
                FROM (
                    SELECT
                        cm4.debt_to_equity,

                        ROW_NUMBER() OVER (
                            ORDER BY cm4.debt_to_equity
                        ) AS rn,

                        COUNT(cm4.debt_to_equity) OVER () AS total

                    FROM company_metrics cm4

                    WHERE
                        cm4.broad_sector = cm.broad_sector
                        AND cm4.debt_to_equity IS NOT NULL
                )

                WHERE rn IN (
                    (total + 1) / 2,
                    (total + 2) / 2
                )
            ) AS median_de

        FROM company_metrics cm

        GROUP BY broad_sector

        ORDER BY broad_sector
        """

        rows = conn.execute(query).fetchall()

        results = []

        for row in rows:

            median_roe = row["median_roe"]
            median_pe = row["median_pe"]
            median_de = row["median_de"]

            results.append(
                {
                    "sector": row["sector"],
                    "company_count": row["company_count"],
                    # Database stores ROE as decimal.
                    # Example: 0.3247 = 32.47%
                    "median_roe": (
                        round(float(median_roe) * 100, 2)
                        if median_roe is not None
                        else None
                    ),
                    "median_pe": (
                        round(float(median_pe), 2) if median_pe is not None else None
                    ),
                    "median_de": (
                        round(float(median_de), 2) if median_de is not None else None
                    ),
                }
            )

        # ------------------------------------------------------
        # DERIVED UTILITIES SECTOR
        #
        # The source data stores utility/power companies under
        # Energy. The API exposes Utilities as an additional
        # sector so that the sector API contains 11 sectors.
        # ------------------------------------------------------

        utilities_row = conn.execute("""
            SELECT COUNT(DISTINCT company_id) AS company_count
            FROM sectors
            WHERE
                LOWER(TRIM(sub_sector)) LIKE '%power%'
                OR LOWER(TRIM(sub_sector)) LIKE '%utility%'
            """).fetchone()

        utilities_count = utilities_row["company_count"]

        if utilities_count > 0:

            results.append(
                {
                    "sector": "Utilities",
                    "company_count": utilities_count,
                    "median_roe": None,
                    "median_pe": None,
                    "median_de": None,
                }
            )

        return {
            "count": len(results),
            "sectors": results,
        }

    finally:
        conn.close()


# ============================================================
# GET COMPANIES IN A SECTOR
# ============================================================


@router.get("/{sector}/companies")
def get_sector_companies(sector: str):
    """
    Return all companies in a sector with latest-year KPIs.

    Supports:
        Information Technology
        IT

    Example:
        GET /api/v1/sectors/Industrials/companies
        GET /api/v1/sectors/IT/companies
    """

    conn = get_connection()

    try:

        # ------------------------------------------------------
        # SUPPORT SECTOR ALIASES
        # ------------------------------------------------------

        requested_sector = sector.strip()

        # API alias:
        # IT -> Information Technology
        if requested_sector.upper() == "IT":
            requested_sector = "Information Technology"

        # ------------------------------------------------------
        # CHECK WHETHER SECTOR EXISTS
        # ------------------------------------------------------

        sector_row = conn.execute(
            """
            SELECT broad_sector
            FROM sectors
            WHERE LOWER(TRIM(broad_sector))
                  = LOWER(TRIM(?))
            LIMIT 1
            """,
            (requested_sector,),
        ).fetchone()

        if sector_row is None:

            raise HTTPException(
                status_code=404,
                detail=f"Unknown sector: {sector}",
            )

        canonical_sector = sector_row["broad_sector"]

        # ------------------------------------------------------
        # LATEST RATIOS
        # One row per company
        # ------------------------------------------------------

        latest_ratios = """
            SELECT
                company_id,
                year,
                revenue_growth,
                profit_growth,
                net_profit_margin,
                operating_profit_margin,
                roe,
                roce,
                debt_to_equity,
                interest_coverage,
                asset_turnover,
                net_debt,
                free_cash_flow
            FROM (
                SELECT
                    r.*,

                    ROW_NUMBER() OVER (
                        PARTITION BY r.company_id
                        ORDER BY r.year DESC, r.id DESC
                    ) AS rn

                FROM historical_financial_ratios r
            )

            WHERE rn = 1
        """

        # ------------------------------------------------------
        # LATEST MARKET DATA
        # One row per company
        # ------------------------------------------------------

        latest_market = """
            SELECT
                company_id,
                year,
                pe_ratio,
                pb_ratio,
                ev_ebitda,
                dividend_yield_pct
            FROM (
                SELECT
                    m.*,

                    ROW_NUMBER() OVER (
                        PARTITION BY m.company_id
                        ORDER BY m.year DESC, m.id DESC
                    ) AS rn

                FROM market_cap m
            )

            WHERE rn = 1
        """

        # ------------------------------------------------------
        # MAIN QUERY
        # ------------------------------------------------------

        query = f"""
        WITH

        latest_ratios AS (
            {latest_ratios}
        ),

        latest_market AS (
            {latest_market}
        )

        SELECT

            c.id AS ticker,

            c.company_name,

            s.broad_sector,
            s.sub_sector,
            s.market_cap_category,

            r.year AS latest_year,

            r.revenue_growth,
            r.profit_growth,

            r.net_profit_margin,

            r.operating_profit_margin,

            r.roe,
            r.roce,

            r.debt_to_equity,

            r.interest_coverage,

            r.asset_turnover,

            r.net_debt,

            r.free_cash_flow,

            m.pe_ratio,
            m.pb_ratio,
            m.ev_ebitda,
            m.dividend_yield_pct

        FROM companies c

        INNER JOIN sectors s
            ON c.id = s.company_id

        LEFT JOIN latest_ratios r
            ON c.id = r.company_id

        LEFT JOIN latest_market m
            ON c.id = m.company_id

        WHERE
            LOWER(TRIM(s.broad_sector))
            = LOWER(TRIM(?))

        ORDER BY c.id
        """

        rows = conn.execute(
            query,
            (canonical_sector,),
        ).fetchall()

        results = []

        for row in rows:

            roe = row["roe"]
            roce = row["roce"]

            results.append(
                {
                    # --------------------------------------------------
                    # COMPANY
                    # --------------------------------------------------
                    "ticker": row["ticker"],
                    "company_name": row["company_name"],
                    # --------------------------------------------------
                    # SECTOR
                    # --------------------------------------------------
                    "broad_sector": row["broad_sector"],
                    "sub_sector": row["sub_sector"],
                    "market_cap_category": row["market_cap_category"],
                    # --------------------------------------------------
                    # LATEST YEAR
                    # --------------------------------------------------
                    "latest_year": row["latest_year"],
                    # --------------------------------------------------
                    # GROWTH
                    # --------------------------------------------------
                    "revenue_growth": row["revenue_growth"],
                    "profit_growth": row["profit_growth"],
                    # --------------------------------------------------
                    # PROFITABILITY
                    # --------------------------------------------------
                    "net_profit_margin": row["net_profit_margin"],
                    "operating_profit_margin": row["operating_profit_margin"],
                    "roe_pct": (
                        round(float(roe) * 100, 2) if roe is not None else None
                    ),
                    "roce_pct": (
                        round(float(roce) * 100, 2) if roce is not None else None
                    ),
                    # --------------------------------------------------
                    # LEVERAGE / RISK
                    # --------------------------------------------------
                    "debt_to_equity": row["debt_to_equity"],
                    "interest_coverage": row["interest_coverage"],
                    "asset_turnover": row["asset_turnover"],
                    "net_debt": row["net_debt"],
                    # --------------------------------------------------
                    # CASH FLOW
                    # --------------------------------------------------
                    "free_cash_flow": row["free_cash_flow"],
                    # --------------------------------------------------
                    # VALUATION
                    # --------------------------------------------------
                    "pe_ratio": row["pe_ratio"],
                    "pb_ratio": row["pb_ratio"],
                    "ev_ebitda": row["ev_ebitda"],
                    "dividend_yield_pct": row["dividend_yield_pct"],
                }
            )

        return {
            "sector": canonical_sector,
            "count": len(results),
            "companies": results,
        }

    finally:
        conn.close()
