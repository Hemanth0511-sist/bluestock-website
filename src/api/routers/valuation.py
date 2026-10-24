"""
Day 40 - Market Cap / Valuation API

Endpoint:
    GET /api/v1/market-cap/{ticker}

Returns historical valuation multiples:
    - P/E
    - P/B
    - EV/EBITDA
    - Dividend Yield

Historical period:
    2019 to 2024
"""

import sqlite3

from fastapi import APIRouter, HTTPException, Query

# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/market-cap",
    tags=["Market Cap / Valuation"],
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
# ROOT
# ============================================================


@router.get("")
def market_cap_root():
    """
    Check whether the market-cap module is available.
    """

    return {
        "module": "market-cap",
        "status": "ready",
    }


# ============================================================
# HISTORICAL VALUATION
# ============================================================


@router.get("/{ticker}")
def get_market_cap_history(
    ticker: str,
    from_year: int = Query(
        default=2019,
        ge=2019,
        le=2024,
        description="Starting year",
    ),
    to_year: int = Query(
        default=2024,
        ge=2019,
        le=2024,
        description="Ending year",
    ),
):
    """
    Return historical valuation multiples for a company.

    Includes:
        - P/E
        - P/B
        - EV/EBITDA
        - Dividend Yield

    Historical range:
        2019 - 2024
    """

    # --------------------------------------------------------
    # VALIDATE YEAR RANGE
    # --------------------------------------------------------

    if from_year > to_year:
        raise HTTPException(
            status_code=400,
            detail="from_year cannot be greater than to_year",
        )

    # --------------------------------------------------------
    # NORMALIZE TICKER
    # --------------------------------------------------------

    normalized_ticker = ticker.strip().upper()

    if not normalized_ticker:
        raise HTTPException(
            status_code=400,
            detail="ticker cannot be empty",
        )

    conn = get_connection()

    try:

        # ----------------------------------------------------
        # CHECK COMPANY EXISTS
        # ----------------------------------------------------

        company = conn.execute(
            """
            SELECT
                id,
                company_name
            FROM companies
            WHERE UPPER(TRIM(id)) =
                  UPPER(TRIM(?))
            LIMIT 1
            """,
            (normalized_ticker,),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=(f"Company '{normalized_ticker}' not found"),
            )

        canonical_ticker = company["id"]

        # ----------------------------------------------------
        # GET MARKET CAP HISTORY
        # ----------------------------------------------------

        rows = conn.execute(
            """
            SELECT
                company_id,
                year,
                market_cap_crore,
                enterprise_value_crore,
                pe_ratio,
                pb_ratio,
                ev_ebitda,
                dividend_yield_pct
            FROM market_cap
            WHERE UPPER(TRIM(company_id)) =
                  UPPER(TRIM(?))
              AND year BETWEEN ? AND ?
            ORDER BY year
            """,
            (
                canonical_ticker,
                from_year,
                to_year,
            ),
        ).fetchall()

        # ----------------------------------------------------
        # COMPANY EXISTS BUT NO VALUATION DATA
        # ----------------------------------------------------

        if not rows:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No market-cap valuation data found "
                    f"for company '{canonical_ticker}' "
                    f"between {from_year} and {to_year}"
                ),
            )

        # ----------------------------------------------------
        # BUILD HISTORY
        # ----------------------------------------------------

        history = []

        for row in rows:

            history.append(
                {
                    "year": row["year"],
                    "pe_ratio": row["pe_ratio"],
                    "pb_ratio": row["pb_ratio"],
                    "ev_ebitda": row["ev_ebitda"],
                    "dividend_yield_pct": row["dividend_yield_pct"],
                }
            )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {
            "ticker": canonical_ticker,
            "company_name": company["company_name"],
            "from_year": from_year,
            "to_year": to_year,
            "count": len(history),
            "history": history,
        }

    finally:
        conn.close()
