"""
N100 Financial Intelligence Platform
Day 39 - Company Data API

Company-related REST API endpoints.
"""

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from src.api.database import get_db_connection

# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

TEARSHEET_DIR = BASE_DIR / "reports" / "tearsheets"


# ============================================================
# CONSTANTS
# ============================================================

COMPANY_COLUMNS = [
    "id",
    "company_logo",
    "company_name",
    "chart_link",
    "about_company",
    "website",
    "nse_profile",
    "bse_profile",
    "face_value",
    "book_value",
    "roce_percentage",
    "roe_percentage",
]


# ============================================================
# DATABASE HELPERS
# ============================================================


def fetch_all(query: str, params: tuple = ()):
    """
    Execute a SELECT query and return rows as dictionaries.
    """

    conn = get_db_connection()

    try:
        rows = conn.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def fetch_one(query: str, params: tuple = ()):
    """
    Execute a SELECT query and return one row as dictionary.
    """

    conn = get_db_connection()

    try:
        row = conn.execute(query, params).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        conn.close()


# ============================================================
# YEAR HELPERS
# ============================================================

MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def normalize_year(value) -> str | None:
    """
    Convert database year formats into YYYY-MM.

    Examples:

        Mar-13  -> 2013-03
        Mar-22  -> 2022-03
        Dec 2012 -> 2012-12
        2022-03 -> 2022-03

    Returns None when the value cannot be interpreted.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    # --------------------------------------------------------
    # Already YYYY-MM
    # --------------------------------------------------------

    match = re.fullmatch(r"(\d{4})-(\d{1,2})", text)

    if match:
        year = int(match.group(1))
        month = int(match.group(2))

        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"

    # --------------------------------------------------------
    # YYYY/MM
    # --------------------------------------------------------

    match = re.fullmatch(r"(\d{4})/(\d{1,2})", text)

    if match:
        year = int(match.group(1))
        month = int(match.group(2))

        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"

    # --------------------------------------------------------
    # Month-Year formats
    #
    # Mar-22
    # Mar 22
    # March-2022
    # March 2022
    # --------------------------------------------------------

    match = re.fullmatch(
        r"([A-Za-z]+)[\s\-]+(\d{2}|\d{4})",
        text,
    )

    if match:
        month_text = match.group(1).upper()[:3]
        year_text = match.group(2)

        month = MONTHS.get(month_text)

        if month is None:
            return None

        year = int(year_text)

        if len(year_text) == 2:
            if year >= 50:
                year += 1900
            else:
                year += 2000

        return f"{year:04d}-{month:02d}"

    # --------------------------------------------------------
    # Formats such as "10 Mar 2022"
    # --------------------------------------------------------

    match = re.fullmatch(
        r"\d{1,2}[\s\-]+([A-Za-z]+)[\s\-]+(\d{4})",
        text,
    )

    if match:
        month_text = match.group(1).upper()[:3]
        year = int(match.group(2))

        month = MONTHS.get(month_text)

        if month is not None:
            return f"{year:04d}-{month:02d}"

    return None


def validate_year_parameter(value: str | None, name: str):
    """
    Validate API year parameter.

    Required format:
        YYYY-MM
    """

    if value is None:
        return None

    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise HTTPException(
            status_code=422,
            detail=(f"{name} must use YYYY-MM format. " f"Example: 2022-03"),
        )

    return value


def filter_by_year_range(
    rows,
    from_year: str | None = None,
    to_year: str | None = None,
):
    """
    Filter database records using normalized YYYY-MM dates.
    """

    from_year = validate_year_parameter(from_year, "from_year")
    to_year = validate_year_parameter(to_year, "to_year")

    if from_year and to_year and from_year > to_year:
        raise HTTPException(
            status_code=422,
            detail="from_year cannot be later than to_year",
        )

    filtered = []

    for row in rows:
        normalized = normalize_year(row.get("year"))

        if normalized is None:
            continue

        if from_year and normalized < from_year:
            continue

        if to_year and normalized > to_year:
            continue

        item = dict(row)

        # Preserve original database year but expose
        # normalized API year as well.
        item["year"] = normalized

        filtered.append(item)

    filtered.sort(key=lambda x: x.get("year") or "")

    return filtered


# ============================================================
# COMPANY LOOKUP
# ============================================================


def get_company(ticker: str):
    """
    Find a company using its ticker.
    """

    return fetch_one(
        """
        SELECT *
        FROM companies
        WHERE UPPER(TRIM(id)) = UPPER(TRIM(?))
        LIMIT 1
        """,
        (ticker,),
    )


def require_company(ticker: str):
    """
    Return company or raise HTTP 404.
    """

    company = get_company(ticker)

    if company is None:
        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found",
        )

    return company


# ============================================================
# SECTOR LOOKUP
# ============================================================


def get_sector_data(ticker: str):
    """
    Return sector information for a company.
    """

    row = fetch_one(
        """
        SELECT
            company_id,
            broad_sector,
            sub_sector,
            index_weight_pct,
            market_cap_category
        FROM sectors
        WHERE UPPER(TRIM(company_id)) = UPPER(TRIM(?))
        ORDER BY id DESC
        LIMIT 1
        """,
        (ticker,),
    )

    return row


# ============================================================
# LATEST RATIO
# ============================================================


def get_latest_ratio(ticker: str):
    """
    Return the latest financial ratio row.
    """

    rows = fetch_all(
        """
        SELECT *
        FROM financial_ratios
        WHERE UPPER(TRIM(company_id)) = UPPER(TRIM(?))
        """,
        (ticker,),
    )

    if not rows:
        return None

    rows_with_dates = []

    for row in rows:
        normalized = normalize_year(row.get("year"))

        if normalized is not None:
            item = dict(row)
            item["_normalized_year"] = normalized
            rows_with_dates.append(item)

    if not rows_with_dates:
        return rows[-1]

    rows_with_dates.sort(key=lambda x: x["_normalized_year"])

    latest = rows_with_dates[-1]

    latest.pop("_normalized_year", None)

    return latest


# ============================================================
# GET ALL COMPANIES
# ============================================================


@router.get("")
def list_companies(
    sector: str | None = Query(
        default=None,
        description="Filter by broad sector",
    ),
    market_cap_category: str | None = Query(
        default=None,
        description="Filter by market cap category",
    ),
    search: str | None = Query(
        default=None,
        description="Partial ticker or company-name search",
    ),
):
    """
    Return all companies with basic classification
    and headline return metrics.
    """

    query = """
        SELECT
            c.id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            c.roe_percentage AS roe_pct,
            c.roce_percentage AS roce_pct,
            s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s
            ON UPPER(TRIM(c.id)) = UPPER(TRIM(s.company_id))
        WHERE 1 = 1
    """

    params = []

    # --------------------------------------------------------
    # Sector filter
    # --------------------------------------------------------

    if sector:
        query += """
            AND LOWER(TRIM(s.broad_sector)) =
                LOWER(TRIM(?))
        """

        params.append(sector)

    # --------------------------------------------------------
    # Market cap filter
    # --------------------------------------------------------

    if market_cap_category:
        query += """
            AND LOWER(TRIM(s.market_cap_category)) =
                LOWER(TRIM(?))
        """

        params.append(market_cap_category)

    # --------------------------------------------------------
    # Search filter
    # --------------------------------------------------------

    if search:
        query += """
            AND (
                LOWER(c.id) LIKE LOWER(?)
                OR LOWER(c.company_name) LIKE LOWER(?)
            )
        """

        search_value = f"%{search}%"

        params.extend(
            [
                search_value,
                search_value,
            ]
        )

    query += """
        ORDER BY c.id
    """

    rows = fetch_all(
        query,
        tuple(params),
    )

    return {
        "count": len(rows),
        "companies": rows,
    }


# ============================================================
# FULL COMPANY PROFILE
# ============================================================


@router.get("/{ticker}")
def company_profile(ticker: str):
    """
    Return complete company profile, sector data
    and latest financial KPIs.
    """

    company = require_company(ticker)

    sector = get_sector_data(ticker)

    latest_ratio = get_latest_ratio(ticker)

    return {
        "company": company,
        "sector": sector,
        "latest_kpis": latest_ratio,
    }


# ============================================================
# PEER COMPARISON
# ============================================================


@router.get("/{ticker}/peers/compare")
def company_peer_comparison(ticker: str):
    """
    Compare a company against its peer group.

    Returns:
        - selected company
        - peer group
        - benchmark company
        - peer-group average
        - comparison metrics
    """

    # --------------------------------------------------------
    # CHECK COMPANY
    # --------------------------------------------------------

    company = require_company(ticker)

    canonical_ticker = str(company["id"]).strip()

    # --------------------------------------------------------
    # FIND PEER GROUP
    # --------------------------------------------------------

    peer_group_row = fetch_one(
        """
        SELECT
            peer_group_name,
            is_benchmark
        FROM peer_groups
        WHERE UPPER(TRIM(company_id)) =
              UPPER(TRIM(?))
        LIMIT 1
        """,
        (canonical_ticker,),
    )

    if peer_group_row is None:
        raise HTTPException(
            status_code=404,
            detail=(f"No peer group found for company " f"'{canonical_ticker}'"),
        )

    peer_group = peer_group_row["peer_group_name"]

    # --------------------------------------------------------
    # GET ALL COMPANIES IN PEER GROUP
    # --------------------------------------------------------

    peer_companies = fetch_all(
        """
        SELECT
            company_id,
            is_benchmark
        FROM peer_groups
        WHERE LOWER(TRIM(peer_group_name)) =
              LOWER(TRIM(?))
        ORDER BY
            is_benchmark DESC,
            company_id
        """,
        (peer_group,),
    )

    if not peer_companies:
        raise HTTPException(
            status_code=404,
            detail=f"No companies found in peer group: {peer_group}",
        )

    # --------------------------------------------------------
    # CHECK SELECTED COMPANY IS IN PEER GROUP
    # --------------------------------------------------------

    selected_peer = None

    for peer in peer_companies:
        if str(peer["company_id"]).strip().upper() == canonical_ticker.upper():
            selected_peer = peer
            break

    if selected_peer is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Company '{canonical_ticker}' "
                f"is not mapped to peer group '{peer_group}'"
            ),
        )

    # --------------------------------------------------------
    # GET PEER PERCENTILE DATA
    # --------------------------------------------------------

    percentile_rows = fetch_all(
        """
        SELECT
            company_id,
            metric,
            value,
            percentile_rank,
            year
        FROM peer_percentiles
        WHERE LOWER(TRIM(peer_group_name)) =
              LOWER(TRIM(?))
        ORDER BY
            company_id,
            metric,
            year DESC
        """,
        (peer_group,),
    )

    if not percentile_rows:
        raise HTTPException(
            status_code=404,
            detail=(f"No peer metric data found " f"for peer group '{peer_group}'"),
        )

    # --------------------------------------------------------
    # BUILD LATEST METRIC LOOKUP
    # --------------------------------------------------------

    metric_lookup = {}

    for row in percentile_rows:

        company_id = str(row["company_id"]).strip()
        metric = row["metric"]

        if metric is None:
            continue

        if company_id not in metric_lookup:
            metric_lookup[company_id] = {}

        # Keep the latest available row for each metric.
        if metric not in metric_lookup[company_id]:
            metric_lookup[company_id][metric] = {
                "value": row["value"],
                "percentile_rank": row["percentile_rank"],
                "year": row["year"],
            }

    # --------------------------------------------------------
    # FIND BENCHMARK
    # --------------------------------------------------------

    benchmark_company = None

    for peer in peer_companies:
        if bool(peer["is_benchmark"]):
            benchmark_company = str(peer["company_id"]).strip()
            break

    # --------------------------------------------------------
    # GET ALL AVAILABLE METRICS
    # --------------------------------------------------------

    metric_names = sorted(
        {row["metric"] for row in percentile_rows if row["metric"] is not None}
    )

    # --------------------------------------------------------
    # CALCULATE PEER AVERAGES
    # --------------------------------------------------------

    peer_averages = {}

    for metric in metric_names:

        values = []

        for peer in peer_companies:

            company_id = str(peer["company_id"]).strip()

            metric_data = metric_lookup.get(company_id, {}).get(metric)

            if not metric_data:
                continue

            value = metric_data.get("value")

            if value is None:
                continue

            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue

        if values:
            peer_averages[metric] = round(
                sum(values) / len(values),
                2,
            )
        else:
            peer_averages[metric] = None

    # --------------------------------------------------------
    # SELECTED COMPANY METRICS
    # --------------------------------------------------------

    selected_metrics = metric_lookup.get(
        canonical_ticker,
        {},
    )

    # Case-insensitive fallback
    if not selected_metrics:

        for company_id, metrics in metric_lookup.items():

            if company_id.upper() == canonical_ticker.upper():
                selected_metrics = metrics
                break

    # --------------------------------------------------------
    # BENCHMARK METRICS
    # --------------------------------------------------------

    benchmark_metrics = {}

    if benchmark_company:

        benchmark_metrics = metric_lookup.get(
            benchmark_company,
            {},
        )

        if not benchmark_metrics:

            for company_id, metrics in metric_lookup.items():

                if company_id.upper() == benchmark_company.upper():
                    benchmark_metrics = metrics
                    break

    # --------------------------------------------------------
    # BUILD COMPARISON RESPONSE
    # --------------------------------------------------------

    comparison = {}

    for metric in metric_names:

        selected_data = selected_metrics.get(metric)
        benchmark_data = benchmark_metrics.get(metric)

        comparison[metric] = {
            "selected_company": (selected_data["value"] if selected_data else None),
            "peer_average": peer_averages.get(metric),
            "benchmark": (benchmark_data["value"] if benchmark_data else None),
            "selected_percentile": (
                selected_data["percentile_rank"] if selected_data else None
            ),
            "year": (selected_data["year"] if selected_data else None),
        }

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "company": canonical_ticker,
        "company_name": company.get("company_name"),
        "peer_group": peer_group,
        "peer_count": len(peer_companies),
        "benchmark_company": benchmark_company,
        "metrics": metric_names,
        "comparison": comparison,
    }


# ============================================================
# PROFIT & LOSS
# ============================================================


@router.get("/{ticker}/pl")
def company_profit_loss(
    ticker: str,
    from_year: str | None = Query(
        default=None,
        description="Start year in YYYY-MM format",
    ),
    to_year: str | None = Query(
        default=None,
        description="End year in YYYY-MM format",
    ),
):
    """
    Return P&L history for a company.
    """

    require_company(ticker)

    rows = fetch_all(
        """
        SELECT *
        FROM profitandloss
        WHERE UPPER(TRIM(company_id)) =
              UPPER(TRIM(?))
        """,
        (ticker,),
    )

    history = filter_by_year_range(
        rows,
        from_year,
        to_year,
    )

    return {
        "company_id": ticker.upper(),
        "count": len(history),
        "history": history,
    }


# ============================================================
# BALANCE SHEET
# ============================================================


@router.get("/{ticker}/bs")
def company_balance_sheet(
    ticker: str,
    from_year: str | None = Query(
        default=None,
        description="Start year in YYYY-MM format",
    ),
    to_year: str | None = Query(
        default=None,
        description="End year in YYYY-MM format",
    ),
):
    """
    Return balance sheet history for a company.
    """

    require_company(ticker)

    rows = fetch_all(
        """
        SELECT *
        FROM balancesheet
        WHERE UPPER(TRIM(company_id)) =
              UPPER(TRIM(?))
        """,
        (ticker,),
    )

    history = filter_by_year_range(
        rows,
        from_year,
        to_year,
    )

    return {
        "company_id": ticker.upper(),
        "count": len(history),
        "history": history,
    }


# ============================================================
# CASH FLOW
# ============================================================


@router.get("/{ticker}/cashflow")
def company_cashflow(
    ticker: str,
    from_year: str | None = Query(
        default=None,
        description="Start year in YYYY-MM format",
    ),
    to_year: str | None = Query(
        default=None,
        description="End year in YYYY-MM format",
    ),
):
    """
    Return cash flow history for a company.
    """

    require_company(ticker)

    rows = fetch_all(
        """
        SELECT *
        FROM cashflow
        WHERE UPPER(TRIM(company_id)) =
              UPPER(TRIM(?))
        """,
        (ticker,),
    )

    history = filter_by_year_range(
        rows,
        from_year,
        to_year,
    )

    return {
        "company_id": ticker.upper(),
        "count": len(history),
        "history": history,
    }


# ============================================================
# FINANCIAL RATIOS
# ============================================================


@router.get("/{ticker}/ratios")
def company_ratios(
    ticker: str,
    year: str | None = Query(
        default=None,
        description="Return one year using YYYY-MM format",
    ),
):
    """
    Return all computed financial KPIs for a company.

    If year is supplied, only that year is returned.
    """

    require_company(ticker)

    year = validate_year_parameter(
        year,
        "year",
    )

    rows = fetch_all(
        """
        SELECT *
        FROM financial_ratios
        WHERE UPPER(TRIM(company_id)) =
              UPPER(TRIM(?))
        """,
        (ticker,),
    )

    normalized_rows = []

    for row in rows:

        normalized = normalize_year(row.get("year"))

        if normalized is None:
            continue

        item = dict(row)

        item["year"] = normalized

        normalized_rows.append(item)

    normalized_rows.sort(key=lambda x: x.get("year") or "")

    if year is not None:

        normalized_rows = [row for row in normalized_rows if row["year"] == year]

    return {
        "company_id": ticker.upper(),
        "count": len(normalized_rows),
        "ratios": normalized_rows,
    }


# ============================================================
# TEARSHEET PDF
# ============================================================


@router.get("/{ticker}/tearsheet")
def company_tearsheet(ticker: str):
    """
    Download the pre-generated company tearsheet PDF.
    """

    require_company(ticker)

    # --------------------------------------------------------
    # Use the canonical ticker stored in the database.
    # --------------------------------------------------------

    company = get_company(ticker)

    canonical_ticker = str(company["id"]).strip()

    pdf_path = TEARSHEET_DIR / f"{canonical_ticker}_tearsheet.pdf"

    if not pdf_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(f"Tearsheet PDF not found for " f"company '{canonical_ticker}'"),
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )
