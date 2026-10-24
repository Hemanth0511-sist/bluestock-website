"""
Documents API router.

Endpoint:
    GET /api/v1/companies/{ticker}/documents

Returns annual report links for a company and
whether each URL is considered valid.
"""

import sqlite3

import requests
from fastapi import APIRouter, HTTPException

# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/companies",
    tags=["Documents"],
)


# ============================================================
# DATABASE
# ============================================================

DB_PATH = "database/n100.db"


def get_connection():
    """Create a SQLite connection with row access by column name."""

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# URL VALIDATION
# ============================================================


def check_url(url):
    """
    Check whether an annual-report URL is reachable.

    404 is considered invalid.

    Common successful responses such as 200, 301, 302
    and 403 are considered valid because some financial
    websites restrict HEAD requests.
    """

    if not url:
        return False

    url = str(url).strip()

    if not url:
        return False

    if not url.lower().startswith(("http://", "https://")):
        return False

    try:

        response = requests.head(
            url,
            timeout=8,
            allow_redirects=True,
        )

        # ----------------------------------------------------
        # Definitely unavailable
        # ----------------------------------------------------

        if response.status_code == 404:
            return False

        # ----------------------------------------------------
        # Common valid responses
        # ----------------------------------------------------

        if response.status_code in (
            200,
            301,
            302,
            403,
        ):
            return True

        # ----------------------------------------------------
        # Some servers don't support HEAD correctly.
        # Try GET.
        # ----------------------------------------------------

        response = requests.get(
            url,
            timeout=8,
            stream=True,
            allow_redirects=True,
        )

        return response.status_code != 404

    except requests.RequestException:
        # ----------------------------------------------------
        # Network restrictions / SSL / remote server problems
        # should not incorrectly mark an existing URL invalid.
        # ----------------------------------------------------

        return True


# ============================================================
# DOCUMENT TABLE READER
# ============================================================


def load_documents(conn, ticker):
    """
    Load annual-report records for a company.

    The documents table may contain generic column names
    because the original Excel import preserved the first
    row as the actual header. Therefore this function first
    inspects the table structure and then safely reads the
    available columns.
    """

    # --------------------------------------------------------
    # Get actual SQLite column names
    # --------------------------------------------------------

    table_info = conn.execute("PRAGMA table_info(documents)").fetchall()

    if not table_info:
        return []

    columns = [row["name"] for row in table_info]

    # --------------------------------------------------------
    # Normalize names
    # --------------------------------------------------------

    normalized = {str(column).strip().lower(): column for column in columns}

    # --------------------------------------------------------
    # Locate company column
    # --------------------------------------------------------

    company_column = None

    for candidate in (
        "company_id",
        "company",
        "ticker",
        "symbol",
    ):

        if candidate in normalized:
            company_column = normalized[candidate]
            break

    # --------------------------------------------------------
    # Locate year column
    # --------------------------------------------------------

    year_column = None

    for candidate in (
        "year",
        "financial_year",
    ):

        if candidate in normalized:
            year_column = normalized[candidate]
            break

    # --------------------------------------------------------
    # Locate annual report column
    # --------------------------------------------------------

    report_column = None

    for candidate in (
        "annual_report",
        "annualreport",
        "report",
        "report_url",
        "url",
    ):

        if candidate in normalized:
            report_column = normalized[candidate]
            break

    # --------------------------------------------------------
    # If the imported table has generic column names,
    # use the known four-column structure:
    #
    # id, company_id, year, annual_report
    # --------------------------------------------------------

    if company_column is None or year_column is None or report_column is None:

        if len(columns) >= 4:

            company_column = columns[1]
            year_column = columns[2]
            report_column = columns[3]

        else:
            return []

    # --------------------------------------------------------
    # Quote identifiers safely
    # --------------------------------------------------------

    def quote_identifier(identifier):
        return (
            '"'
            + str(identifier).replace(
                '"',
                '""',
            )
            + '"'
        )

    company_sql = quote_identifier(company_column)

    year_sql = quote_identifier(year_column)

    report_sql = quote_identifier(report_column)

    # --------------------------------------------------------
    # Query
    # --------------------------------------------------------

    query = f"""
        SELECT
            {company_sql} AS company_id,
            {year_sql} AS year,
            {report_sql} AS annual_report
        FROM documents
        WHERE UPPER(TRIM(CAST(
            {company_sql} AS TEXT
        ))) = ?
        ORDER BY
            {year_sql} DESC
    """

    rows = conn.execute(
        query,
        (ticker.upper(),),
    ).fetchall()

    return rows


# ============================================================
# ENDPOINT
# ============================================================


@router.get("/{ticker}/documents")
def get_company_documents(ticker: str):
    """
    Return annual report links for a company.
    """

    ticker = ticker.strip().upper()

    if not ticker:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    conn = get_connection()

    try:

        # ----------------------------------------------------
        # First verify company exists.
        # ----------------------------------------------------

        company = conn.execute(
            """
            SELECT
                id,
                company_name
            FROM companies
            WHERE UPPER(TRIM(id)) = ?
            """,
            (ticker,),
        ).fetchone()

        if company is None:

            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker}' not found",
            )

        # ----------------------------------------------------
        # Load documents
        # ----------------------------------------------------

        rows = load_documents(
            conn,
            ticker,
        )

        documents = []

        for row in rows:

            report_url = row["annual_report"]

            if report_url is not None:
                report_url = str(report_url).strip()

            if report_url in (
                "",
                "None",
                "nan",
                "NaN",
            ):
                report_url = None

            documents.append(
                {
                    "year": row["year"],
                    "annual_report": report_url,
                    "is_url_valid": check_url(report_url),
                }
            )

        # ----------------------------------------------------
        # Return response
        # ----------------------------------------------------

        return {
            "ticker": ticker,
            "company_name": company["company_name"],
            "count": len(documents),
            "documents": documents,
        }

    finally:
        conn.close()
