import sqlite3

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/screener", tags=["Screener"])

DB_PATH = "database/n100.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("")
def screen_companies(
    min_roe: float | None = None,
    max_de: float | None = None,
    min_fcf: float | None = None,
    sector: str | None = None,
    min_rev_cagr_5yr: float | None = None,
    min_pat_cagr_5yr: float | None = None,
    max_pe: float | None = None,
):
    """
    Screen all companies using latest financial KPIs.

    Returns ranked company list with:
    - ROE
    - ROCE
    - Debt to Equity
    - Free Cash Flow
    - Revenue Growth
    - Profit Growth
    - Revenue CAGR
    - PAT CAGR
    - Profitability metrics
    - Valuation metrics
    - Ranking information

    Invalid filter values return HTTP 400.
    """

    # =========================================================
    # VALIDATION
    # =========================================================

    if min_roe is not None and min_roe < -100:
        raise HTTPException(status_code=400, detail="min_roe cannot be below -100")

    if max_de is not None and max_de < 0:
        raise HTTPException(status_code=400, detail="max_de cannot be negative")

    if min_fcf is not None and min_fcf < 0:
        raise HTTPException(status_code=400, detail="min_fcf cannot be negative")

    if min_rev_cagr_5yr is not None and min_rev_cagr_5yr < -100:
        raise HTTPException(
            status_code=400, detail="min_rev_cagr_5yr cannot be below -100"
        )

    if min_pat_cagr_5yr is not None and min_pat_cagr_5yr < -100:
        raise HTTPException(
            status_code=400, detail="min_pat_cagr_5yr cannot be below -100"
        )

    if max_pe is not None and max_pe < 0:
        raise HTTPException(status_code=400, detail="max_pe cannot be negative")

    conn = get_connection()

    try:

        # =====================================================
        # SQL
        # =====================================================

        query = """
        WITH latest_ratios AS (
            SELECT *
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

        latest_profit_loss AS (
            SELECT *
            FROM (
                SELECT
                    p.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY p.company_id
                        ORDER BY
                            CAST(substr(p.year, 1, 4) AS INTEGER) DESC,
                            p.rowid DESC
                    ) AS rn
                FROM profitandloss p
            )
            WHERE rn = 1
        ),

        old_profit_loss AS (
            SELECT *
            FROM (
                SELECT
                    p.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY p.company_id
                        ORDER BY
                            CAST(substr(p.year, 1, 4) AS INTEGER) ASC,
                            p.rowid ASC
                    ) AS rn
                FROM profitandloss p
                WHERE CAST(substr(p.year, 1, 4) AS INTEGER) >= (
                    SELECT
                        MAX(
                            CAST(substr(p2.year, 1, 4) AS INTEGER)
                        ) - 5
                    FROM profitandloss p2
                    WHERE p2.company_id = p.company_id
                )
                AND CAST(substr(p.year, 1, 4) AS INTEGER) < (
                    SELECT
                        MAX(
                            CAST(substr(p3.year, 1, 4) AS INTEGER)
                        )
                    FROM profitandloss p3
                    WHERE p3.company_id = p.company_id
                )
            )
            WHERE rn = 1
        ),

        latest_market AS (
            SELECT *
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
        )

        SELECT
            c.id AS ticker,
            c.company_name,

            s.broad_sector,
            s.sub_sector,
            s.market_cap_category,

            r.year AS latest_year,

            r.roe,
            r.roce,
            r.debt_to_equity,
            r.free_cash_flow,

            r.revenue_growth,
            r.profit_growth,

            r.net_profit_margin,
            r.operating_profit_margin,
            r.interest_coverage,
            r.net_debt,

            m.pe_ratio,
            m.pb_ratio,
            m.ev_ebitda,
            m.dividend_yield_pct,

            cr.final_score,
            cr.overall_rank,
            cr.recommendation,

            lp.sales AS latest_sales,
            op.sales AS old_sales,

            lp.net_profit AS latest_net_profit,
            op.net_profit AS old_net_profit

        FROM companies c

        LEFT JOIN sectors s
            ON c.id = s.company_id

        LEFT JOIN latest_ratios r
            ON c.id = r.company_id

        LEFT JOIN latest_market m
            ON c.id = m.company_id

        LEFT JOIN company_rankings cr
            ON c.id = cr.company_id

        LEFT JOIN latest_profit_loss lp
            ON c.id = lp.company_id

        LEFT JOIN old_profit_loss op
            ON c.id = op.company_id

        WHERE 1 = 1
        """

        params = []

        # =====================================================
        # FILTERS
        # =====================================================

        if sector:
            query += """
                AND LOWER(TRIM(s.broad_sector)) = LOWER(TRIM(?))
            """
            params.append(sector)

        if min_roe is not None:
            query += """
                AND r.roe IS NOT NULL
                AND r.roe >= ?
            """
            params.append(min_roe / 100.0)

        if max_de is not None:
            query += """
                AND r.debt_to_equity IS NOT NULL
                AND r.debt_to_equity <= ?
            """
            params.append(max_de)

        if min_fcf is not None:
            query += """
                AND r.free_cash_flow IS NOT NULL
                AND r.free_cash_flow >= ?
            """
            params.append(min_fcf)

        if max_pe is not None:
            query += """
                AND m.pe_ratio IS NOT NULL
                AND m.pe_ratio <= ?
            """
            params.append(max_pe)

        # -----------------------------------------------------
        # Revenue CAGR filter
        # -----------------------------------------------------

        if min_rev_cagr_5yr is not None:
            query += """
                AND lp.sales IS NOT NULL
                AND op.sales IS NOT NULL
                AND op.sales > 0
                AND lp.sales > 0
                AND (
                    (
                        POWER(
                            CAST(lp.sales AS REAL)
                            / op.sales,
                            1.0 / 5.0
                        ) - 1
                    ) * 100
                ) >= ?
            """
            params.append(min_rev_cagr_5yr)

        # -----------------------------------------------------
        # PAT CAGR filter
        # -----------------------------------------------------

        if min_pat_cagr_5yr is not None:
            query += """
                AND lp.net_profit IS NOT NULL
                AND op.net_profit IS NOT NULL
                AND op.net_profit > 0
                AND lp.net_profit > 0
                AND (
                    (
                        POWER(
                            CAST(lp.net_profit AS REAL)
                            / op.net_profit,
                            1.0 / 5.0
                        ) - 1
                    ) * 100
                ) >= ?
            """
            params.append(min_pat_cagr_5yr)

        # =====================================================
        # RANKING
        # =====================================================

        query += """
            ORDER BY
                COALESCE(cr.final_score, 0) DESC,
                COALESCE(cr.overall_rank, 9999) ASC,
                c.id ASC
        """

        rows = conn.execute(query, params).fetchall()

        results = []

        # =====================================================
        # RESULT BUILDING
        # =====================================================

        for row in rows:

            revenue_cagr = None

            if (
                row["latest_sales"] is not None
                and row["old_sales"] is not None
                and row["old_sales"] > 0
                and row["latest_sales"] > 0
            ):
                revenue_cagr = (
                    ((float(row["latest_sales"]) / float(row["old_sales"])) ** (1 / 5))
                    - 1
                ) * 100

            pat_cagr = None

            if (
                row["latest_net_profit"] is not None
                and row["old_net_profit"] is not None
                and row["old_net_profit"] > 0
                and row["latest_net_profit"] > 0
            ):
                pat_cagr = (
                    (
                        (float(row["latest_net_profit"]) / float(row["old_net_profit"]))
                        ** (1 / 5)
                    )
                    - 1
                ) * 100

            results.append(
                {
                    "ticker": row["ticker"],
                    "company_name": row["company_name"],
                    "broad_sector": row["broad_sector"],
                    "sub_sector": row["sub_sector"],
                    "market_cap_category": row["market_cap_category"],
                    "latest_year": row["latest_year"],
                    "roe_pct": (row["roe"] * 100 if row["roe"] is not None else None),
                    "roce_pct": (
                        row["roce"] * 100 if row["roce"] is not None else None
                    ),
                    "debt_to_equity": row["debt_to_equity"],
                    "free_cash_flow": row["free_cash_flow"],
                    "revenue_growth": row["revenue_growth"],
                    "profit_growth": row["profit_growth"],
                    "revenue_cagr_5yr": revenue_cagr,
                    "pat_cagr_5yr": pat_cagr,
                    "net_profit_margin": row["net_profit_margin"],
                    "operating_profit_margin": row["operating_profit_margin"],
                    "interest_coverage": row["interest_coverage"],
                    "net_debt": row["net_debt"],
                    "pe_ratio": row["pe_ratio"],
                    "pb_ratio": row["pb_ratio"],
                    "ev_ebitda": row["ev_ebitda"],
                    "dividend_yield_pct": row["dividend_yield_pct"],
                    "final_score": row["final_score"],
                    "overall_rank": row["overall_rank"],
                    "recommendation": row["recommendation"],
                }
            )

        # =====================================================
        # RESPONSE
        # =====================================================

        return {
            "count": len(results),
            "filters": {
                "min_roe": min_roe,
                "max_de": max_de,
                "min_fcf": min_fcf,
                "sector": sector,
                "min_rev_cagr_5yr": min_rev_cagr_5yr,
                "min_pat_cagr_5yr": min_pat_cagr_5yr,
                "max_pe": max_pe,
            },
            "results": results,
        }

    finally:
        conn.close()
