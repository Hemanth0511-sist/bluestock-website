import sqlite3
import sys
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# DATABASE IMPORTS
# ============================================================

from src.dashboard.utils.db import (
    get_companies,
    get_market_cap,
    get_pl,
    get_rankings,
)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Screener | Nifty 100 Analytics",
    page_icon="🔎",
    layout="wide",
)


# ============================================================
# HEADER
# ============================================================

st.title("🔎 Nifty 100 Screener")

st.caption(
    "Filter Nifty 100 companies using financial quality, "
    "growth, valuation, dividend and debt metrics."
)

st.divider()


# ============================================================
# LOAD COMPANY DATA
# ============================================================

companies = get_companies()

if companies is None or companies.empty:
    st.error("No company data found in the database.")
    st.stop()

companies = companies.copy()


# ============================================================
# LOAD RANKINGS
# ============================================================

rankings = get_rankings()

if rankings is None:
    rankings = pd.DataFrame()


# ============================================================
# LOAD MARKET CAP / VALUATION DATA
# ============================================================

market_cap = get_market_cap()

if market_cap is None:
    market_cap = pd.DataFrame()


# ============================================================
# PREPARE LATEST MARKET DATA
# ============================================================

latest_market = pd.DataFrame()

if not market_cap.empty:

    latest_market = market_cap.copy()

    if "year" in latest_market.columns:

        latest_market["year"] = pd.to_numeric(
            latest_market["year"],
            errors="coerce",
        )

        latest_market = latest_market.sort_values(["company_id", "year"])

        latest_market = latest_market.groupby(
            "company_id",
            as_index=False,
        ).tail(1)


# ============================================================
# LOAD LATEST HISTORICAL RATIOS FOR ALL COMPANIES
# ============================================================
#
# IMPORTANT:
#
# The FastAPI screener uses the latest row from
# historical_financial_ratios for every company.
#
# The dashboard MUST use the same source and selection logic.
#
# The important SQL logic is:
#
#     PARTITION BY company_id
#     ORDER BY year DESC, id DESC
#
# This ensures that when duplicate rows exist for the same
# company/year, the row with the latest database id is used.
#
# DO NOT use get_ratios() here.
# get_ratios() reads financial_ratios and can produce a
# different set of companies from the FastAPI screener.
# ============================================================


def _load_latest_historical_ratios():
    """
    Load exactly one latest historical financial ratio
    row for every company.

    This mirrors the FastAPI screener's latest-row logic.
    """

    database_path = PROJECT_ROOT / "database" / "n100.db"

    if not database_path.exists():
        return pd.DataFrame()

    query = """
        SELECT
            id,
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
            free_cash_flow,
            cfo_quality,
            capex_intensity,
            icr_label,
            icr_warning,
            high_leverage
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
        ORDER BY company_id
    """

    connection = sqlite3.connect(str(database_path))

    try:
        return pd.read_sql_query(
            query,
            connection,
        )

    finally:
        connection.close()


ratios = _load_latest_historical_ratios()


if not ratios.empty:

    ratios = ratios.copy()

    ratios["company_id"] = ratios["company_id"].astype(str).str.strip()

else:

    ratios = pd.DataFrame()


# ============================================================
# PREPARE RATIO DATA
# ============================================================

if not ratios.empty:

    numeric_columns = [
        "revenue_growth",
        "profit_growth",
        "net_profit_margin",
        "operating_profit_margin",
        "roe",
        "roce",
        "debt_to_equity",
        "interest_coverage",
        "free_cash_flow",
        "cfo_quality",
        "capex_intensity",
    ]

    for column in numeric_columns:

        if column in ratios.columns:

            ratios[column] = pd.to_numeric(
                ratios[column],
                errors="coerce",
            )


# ============================================================
# BUILD BASE DATASET
# ============================================================

base = companies.copy()


# ============================================================
# NORMALIZE COMPANY IDENTIFIERS
# ============================================================

base["company_id"] = base["company_id"].astype(str).str.strip()


# ============================================================
# SELECT COMPANY COLUMNS
# ============================================================

company_columns = [
    "company_id",
    "company_name",
    "broad_sector",
    "sub_sector",
]

company_columns = [column for column in company_columns if column in base.columns]

base = base[company_columns].drop_duplicates(subset=["company_id"])


# ============================================================
# MERGE RATIOS
# ============================================================

if not ratios.empty:

    base = base.merge(
        ratios,
        on="company_id",
        how="left",
    )


# ============================================================
# MERGE MARKET DATA
# ============================================================

if not latest_market.empty:

    market_columns = [
        "company_id",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
        "market_cap_crore",
    ]

    market_columns = [
        column for column in market_columns if column in latest_market.columns
    ]

    base = base.merge(
        latest_market[market_columns],
        on="company_id",
        how="left",
    )


# ============================================================
# MERGE RANKINGS
# ============================================================

if not rankings.empty:

    ranking_columns = [
        "company_id",
        "final_score",
        "quality_score",
        "growth_score",
        "value_score",
        "risk_score",
        "overall_rank",
        "recommendation",
    ]

    ranking_columns = [
        column for column in ranking_columns if column in rankings.columns
    ]

    if "company_id" in ranking_columns:

        ranking_data = rankings[ranking_columns].drop_duplicates(subset=["company_id"])

        ranking_data["company_id"] = ranking_data["company_id"].astype(str).str.strip()

        base = base.merge(
            ranking_data,
            on="company_id",
            how="left",
        )


# ============================================================
# CALCULATE 5-YEAR CAGR
# ============================================================


@st.cache_data(ttl=600)
def calculate_cagr_data(tickers):

    revenue_cagr = {}
    pat_cagr = {}

    for ticker in tickers:

        try:
            pl = get_pl(ticker)

        except Exception:
            continue

        if pl is None or pl.empty:
            continue

        pl = pl.copy()

        if "year" not in pl.columns:
            continue

        # ----------------------------------------------------
        # NORMALIZE YEAR
        # ----------------------------------------------------

        pl["_year"] = pd.to_numeric(
            pl["year"].astype(str).str.extract(r"(\d{4})")[0],
            errors="coerce",
        )

        # ----------------------------------------------------
        # NORMALIZE FINANCIAL COLUMNS
        # ----------------------------------------------------

        if "sales" in pl.columns:

            pl["sales"] = pd.to_numeric(
                pl["sales"],
                errors="coerce",
            )

        if "net_profit" in pl.columns:

            pl["net_profit"] = pd.to_numeric(
                pl["net_profit"],
                errors="coerce",
            )

        pl = pl.dropna(subset=["_year"]).sort_values("_year")

        if len(pl) < 6:
            continue

        # ----------------------------------------------------
        # LATEST AVAILABLE YEAR
        # AND FIVE YEARS EARLIER
        # ----------------------------------------------------

        latest_year = int(pl["_year"].max())

        start_year = latest_year - 5

        start_rows = pl[pl["_year"] == start_year]

        end_rows = pl[pl["_year"] == latest_year]

        if start_rows.empty or end_rows.empty:
            continue

        start_row = start_rows.iloc[-1]
        end_row = end_rows.iloc[-1]

        # ----------------------------------------------------
        # REVENUE CAGR
        # ----------------------------------------------------

        if (
            "sales" in pl.columns
            and pd.notna(start_row["sales"])
            and pd.notna(end_row["sales"])
            and start_row["sales"] > 0
            and end_row["sales"] > 0
        ):

            revenue_cagr[ticker] = (
                (end_row["sales"] / start_row["sales"]) ** (1 / 5) - 1
            ) * 100

        # ----------------------------------------------------
        # PAT CAGR
        # ----------------------------------------------------

        if (
            "net_profit" in pl.columns
            and pd.notna(start_row["net_profit"])
            and pd.notna(end_row["net_profit"])
            and start_row["net_profit"] > 0
            and end_row["net_profit"] > 0
        ):

            pat_cagr[ticker] = (
                (end_row["net_profit"] / start_row["net_profit"]) ** (1 / 5) - 1
            ) * 100

    return revenue_cagr, pat_cagr


revenue_cagr_dict, pat_cagr_dict = calculate_cagr_data(
    tuple(companies["company_id"].dropna().astype(str).str.strip().unique())
)


base["revenue_cagr_5yr"] = base["company_id"].map(revenue_cagr_dict)

base["pat_cagr_5yr"] = base["company_id"].map(pat_cagr_dict)


# ============================================================
# CREATE FCF YIELD
# ============================================================

if "free_cash_flow" in base.columns and "market_cap_crore" in base.columns:

    base["fcf_yield_pct"] = (
        pd.to_numeric(
            base["free_cash_flow"],
            errors="coerce",
        )
        / pd.to_numeric(
            base["market_cap_crore"],
            errors="coerce",
        )
        * 100
    )

else:

    base["fcf_yield_pct"] = pd.NA


# ============================================================
# ENSURE REQUIRED NUMERIC COLUMNS
# ============================================================

required_numeric = [
    "roe",
    "debt_to_equity",
    "free_cash_flow",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
    "interest_coverage",
    "final_score",
]

for column in required_numeric:

    if column not in base.columns:
        base[column] = pd.NA

    base[column] = pd.to_numeric(
        base[column],
        errors="coerce",
    )


# ============================================================
# PRESETS
# ============================================================

PRESETS = {
    "Quality": {
        "roe": 15.0,
        "de": 2.0,
        "fcf": -50000.0,
        "revenue": -50.0,
        "pat": -100.0,
        "opm": 10.0,
        "pe": 1000.0,
        "pb": 50.0,
        "dividend": 0.0,
        "icr": 2.0,
    },
    "Value": {
        "roe": 10.0,
        "de": 3.0,
        "fcf": -50000.0,
        "revenue": -50.0,
        "pat": -100.0,
        "opm": -50.0,
        "pe": 20.0,
        "pb": 4.0,
        "dividend": 0.0,
        "icr": -10.0,
    },
    "Growth": {
        "roe": 12.0,
        "de": 2.5,
        "fcf": -50000.0,
        "revenue": 12.0,
        "pat": 12.0,
        "opm": 8.0,
        "pe": 1000.0,
        "pb": 50.0,
        "dividend": 0.0,
        "icr": 1.5,
    },
    "Dividend": {
        "roe": 8.0,
        "de": 3.0,
        "fcf": -50000.0,
        "revenue": -50.0,
        "pat": -100.0,
        "opm": -50.0,
        "pe": 1000.0,
        "pb": 50.0,
        "dividend": 2.0,
        "icr": -10.0,
    },
    "Debt-Free": {
        "roe": 8.0,
        "de": 0.3,
        "fcf": -50000.0,
        "revenue": -50.0,
        "pat": -100.0,
        "opm": -50.0,
        "pe": 1000.0,
        "pb": 50.0,
        "dividend": 0.0,
        "icr": 3.0,
    },
    "Turnaround": {
        "roe": -50.0,
        "de": 4.0,
        "fcf": -50000.0,
        "revenue": 0.0,
        "pat": 0.0,
        "opm": 0.0,
        "pe": 1000.0,
        "pb": 50.0,
        "dividend": 0.0,
        "icr": 1.0,
    },
}


# ============================================================
# SESSION STATE FOR PRESETS
# ============================================================

if "screener_preset" not in st.session_state:
    st.session_state.screener_preset = None

if "preset_values" not in st.session_state:
    st.session_state.preset_values = None


# ============================================================
# PRESET BUTTONS
# ============================================================

st.sidebar.header("🎯 Presets")

preset_columns = st.sidebar.columns(2)

preset_names = list(PRESETS.keys())

for index, preset_name in enumerate(preset_names):

    with preset_columns[index % 2]:

        if st.button(
            preset_name,
            key=f"preset_{preset_name}",
            width="stretch",
        ):

            st.session_state.screener_preset = preset_name

            st.session_state.preset_values = PRESETS[preset_name].copy()

            st.rerun()


# ============================================================
# DEFAULT FILTER VALUES
# ============================================================

preset_values = st.session_state.preset_values


if preset_values is None:

    preset_values = {
        "roe": 0.0,
        "de": 10.0,
        "fcf": -50000.0,
        "revenue": -50.0,
        "pat": -100.0,
        "opm": -50.0,
        "pe": 1000.0,
        "pb": 50.0,
        "dividend": 0.0,
        "icr": -10.0,
    }


# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.divider()

st.sidebar.header("⚙️ Screener Filters")


# ============================================================
# ROE
# ============================================================

roe_enabled = st.sidebar.checkbox(
    "Enable ROE Filter",
    value=True,
)

roe_min = st.sidebar.slider(
    "ROE Minimum (%)",
    min_value=-50.0,
    max_value=100.0,
    value=float(
        max(
            -50.0,
            min(
                100.0,
                preset_values["roe"],
            ),
        )
    ),
    step=1.0,
    disabled=not roe_enabled,
)


# ============================================================
# D/E
# ============================================================

de_enabled = st.sidebar.checkbox(
    "Enable D/E Filter",
    value=False,
)

de_max = st.sidebar.slider(
    "D/E Maximum",
    min_value=0.0,
    max_value=10.0,
    value=float(
        max(
            0.0,
            min(
                10.0,
                preset_values["de"],
            ),
        )
    ),
    step=0.1,
    disabled=not de_enabled,
)


# ============================================================
# FCF
# ============================================================

fcf_enabled = st.sidebar.checkbox(
    "Enable FCF Filter",
    value=False,
)

fcf_min = st.sidebar.slider(
    "FCF Minimum",
    min_value=-50000.0,
    max_value=50000.0,
    value=float(
        max(
            -50000.0,
            min(
                50000.0,
                preset_values["fcf"],
            ),
        )
    ),
    step=500.0,
    disabled=not fcf_enabled,
)


# ============================================================
# REVENUE CAGR
# ============================================================

revenue_cagr_enabled = st.sidebar.checkbox(
    "Enable Revenue CAGR Filter",
    value=False,
)

revenue_cagr_min = st.sidebar.slider(
    "Revenue CAGR 5yr Minimum (%)",
    min_value=-50.0,
    max_value=100.0,
    value=float(
        max(
            -50.0,
            min(
                100.0,
                preset_values["revenue"],
            ),
        )
    ),
    step=1.0,
    disabled=not revenue_cagr_enabled,
)


# ============================================================
# PAT CAGR
# ============================================================

pat_cagr_enabled = st.sidebar.checkbox(
    "Enable PAT CAGR Filter",
    value=False,
)

pat_cagr_min = st.sidebar.slider(
    "PAT CAGR 5yr Minimum (%)",
    min_value=-100.0,
    max_value=100.0,
    value=float(
        max(
            -100.0,
            min(
                100.0,
                preset_values["pat"],
            ),
        )
    ),
    step=1.0,
    disabled=not pat_cagr_enabled,
)


# ============================================================
# OPM
# ============================================================

opm_enabled = st.sidebar.checkbox(
    "Enable OPM Filter",
    value=False,
)

opm_min = st.sidebar.slider(
    "OPM Minimum (%)",
    min_value=-50.0,
    max_value=100.0,
    value=float(
        max(
            -50.0,
            min(
                100.0,
                preset_values["opm"],
            ),
        )
    ),
    step=1.0,
    disabled=not opm_enabled,
)


# ============================================================
# P/E
# ============================================================

pe_enabled = st.sidebar.checkbox(
    "Enable P/E Filter",
    value=False,
)

pe_max = st.sidebar.slider(
    "P/E Maximum",
    min_value=1.0,
    max_value=1000.0,
    value=float(
        max(
            1.0,
            min(
                1000.0,
                preset_values["pe"],
            ),
        )
    ),
    step=1.0,
    disabled=not pe_enabled,
)


# ============================================================
# P/B
# ============================================================

pb_enabled = st.sidebar.checkbox(
    "Enable P/B Filter",
    value=False,
)

pb_max = st.sidebar.slider(
    "P/B Maximum",
    min_value=0.0,
    max_value=50.0,
    value=float(
        max(
            0.0,
            min(
                50.0,
                preset_values["pb"],
            ),
        )
    ),
    step=0.5,
    disabled=not pb_enabled,
)


# ============================================================
# DIVIDEND YIELD
# ============================================================

dividend_enabled = st.sidebar.checkbox(
    "Enable Dividend Filter",
    value=False,
)

dividend_min = st.sidebar.slider(
    "Dividend Yield Minimum (%)",
    min_value=0.0,
    max_value=20.0,
    value=float(
        max(
            0.0,
            min(
                20.0,
                preset_values["dividend"],
            ),
        )
    ),
    step=0.5,
    disabled=not dividend_enabled,
)


# ============================================================
# ICR
# ============================================================

icr_enabled = st.sidebar.checkbox(
    "Enable ICR Filter",
    value=False,
)

icr_min = st.sidebar.slider(
    "ICR Minimum",
    min_value=-10.0,
    max_value=100.0,
    value=float(
        max(
            -10.0,
            min(
                100.0,
                preset_values["icr"],
            ),
        )
    ),
    step=1.0,
    disabled=not icr_enabled,
)


# ============================================================
# SHOW ACTIVE PRESET
# ============================================================

if st.session_state.screener_preset:

    st.sidebar.success(f"Preset: {st.session_state.screener_preset}")


# ============================================================
# APPLY FILTERS
# ============================================================
#
# IMPORTANT:
# The FastAPI screener is the single source of truth.
#
# Previously this page independently filtered the local
# historical_financial_ratios table. That produced only
# BEL/HAL for ROE >= 15 while the API correctly returned
# 52 companies.
#
# The dashboard now sends the enabled API-supported filters
# to the same /api/v1/screener endpoint used by the
# integration test. This prevents the dashboard and API from
# using different screening logic/data-selection rules.
# ============================================================

API_BASE_URL = "http://127.0.0.1:8000/api/v1"


def _request_api_screener(
    min_roe=None,
    max_de=None,
    min_fcf=None,
    min_rev_cagr_5yr=None,
    min_pat_cagr_5yr=None,
    max_pe=None,
):
    """
    Call the FastAPI screener using the exact parameter names
    supported by the screener API.

    Returns a DataFrame. An empty DataFrame means the request
    failed or the API returned no results.
    """

    params = {}

    if min_roe is not None:
        params["min_roe"] = min_roe

    if max_de is not None:
        params["max_de"] = max_de

    if min_fcf is not None:
        params["min_fcf"] = min_fcf

    if min_rev_cagr_5yr is not None:
        params["min_rev_cagr_5yr"] = min_rev_cagr_5yr

    if min_pat_cagr_5yr is not None:
        params["min_pat_cagr_5yr"] = min_pat_cagr_5yr

    if max_pe is not None:
        params["max_pe"] = max_pe

    try:
        response = requests.get(
            f"{API_BASE_URL}/screener",
            params=params,
            timeout=10,
        )
    except requests.RequestException as exc:
        st.error(
            "Unable to connect to the FastAPI screener. "
            f"Make sure the API is running at {API_BASE_URL}.\n\n"
            f"Error: {exc}"
        )
        return pd.DataFrame()

    if response.status_code != 200:
        st.error(
            "FastAPI screener returned an error.\n\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text}"
        )
        return pd.DataFrame()

    try:
        payload = response.json()
    except ValueError:
        st.error("FastAPI screener returned invalid JSON.")
        return pd.DataFrame()

    if isinstance(payload, dict):
        rows = payload.get("results", [])
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []

    if not isinstance(rows, list):
        rows = []

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def _normalise_api_results(api_df):
    """
    Normalize the API response so the dashboard table has
    stable column names.

    The integration test accepts both ticker and company_id,
    but using 'Company ID' in the displayed table keeps the
    dashboard consistent with the existing UI.
    """

    if api_df is None or api_df.empty:
        return pd.DataFrame()

    result = api_df.copy()

    # --------------------------------------------------------
    # Normalize company identifier
    # --------------------------------------------------------

    if "company_id" not in result.columns:
        if "ticker" in result.columns:
            result["company_id"] = result["ticker"]
        elif "Ticker" in result.columns:
            result["company_id"] = result["Ticker"]

    if "company_name" not in result.columns:
        if "name" in result.columns:
            result["company_name"] = result["name"]
        elif "Company Name" in result.columns:
            result["company_name"] = result["Company Name"]

    if "broad_sector" not in result.columns:
        if "sector" in result.columns:
            result["broad_sector"] = result["sector"]
        elif "Sector" in result.columns:
            result["broad_sector"] = result["Sector"]

    # --------------------------------------------------------
    # Normalize common API metric names
    # --------------------------------------------------------

    aliases = {
        "roe": ["ROE", "roe_pct", "roe_percent"],
        "debt_to_equity": ["de", "d_e", "debt_equity"],
        "free_cash_flow": ["fcf"],
        "revenue_cagr_5yr": [
            "rev_cagr_5yr",
            "revenue_cagr",
        ],
        "pat_cagr_5yr": [
            "profit_cagr_5yr",
            "pat_cagr",
        ],
        "operating_profit_margin": [
            "opm",
            "opm_pct",
        ],
        "pe_ratio": ["pe", "p_e"],
        "pb_ratio": ["pb", "p_b"],
        "dividend_yield_pct": [
            "dividend_yield",
            "dividend_yield_percent",
        ],
        "interest_coverage": [
            "icr",
            "interest_coverage_ratio",
        ],
        "final_score": [
            "composite_score",
            "score",
        ],
    }

    for target, candidates in aliases.items():
        if target in result.columns:
            continue

        for candidate in candidates:
            if candidate in result.columns:
                result[target] = result[candidate]
                break

    # --------------------------------------------------------
    # Normalize numeric values
    # --------------------------------------------------------

    numeric_columns = [
        "roe",
        "debt_to_equity",
        "free_cash_flow",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "operating_profit_margin",
        "pe_ratio",
        "pb_ratio",
        "dividend_yield_pct",
        "interest_coverage",
        "final_score",
    ]

    for column in numeric_columns:
        if column in result.columns:
            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            )

    if "company_id" in result.columns:
        result["company_id"] = result["company_id"].astype(str).str.strip()

    return result


# ------------------------------------------------------------
# Build the API query from the enabled dashboard filters.
#
# For the integration test:
#
#     ROE enabled = True
#     ROE minimum = 15
#     every other filter = disabled
#
# Therefore the request is exactly:
#
#     /screener?min_roe=15
#
# which must return the same 52 companies as the API test.
# ------------------------------------------------------------

api_min_roe = roe_min if roe_enabled else None
api_max_de = de_max if de_enabled else None
api_min_fcf = fcf_min if fcf_enabled else None
api_min_rev_cagr = revenue_cagr_min if revenue_cagr_enabled else None
api_min_pat_cagr = pat_cagr_min if pat_cagr_enabled else None
api_max_pe = pe_max if pe_enabled else None


api_results = _request_api_screener(
    min_roe=api_min_roe,
    max_de=api_max_de,
    min_fcf=api_min_fcf,
    min_rev_cagr_5yr=api_min_rev_cagr,
    min_pat_cagr_5yr=api_min_pat_cagr,
    max_pe=api_max_pe,
)


filtered = _normalise_api_results(api_results)


# ------------------------------------------------------------
# Apply only filters that are NOT represented by the API
# query above.
#
# The API currently exposes ROE, D/E, FCF, Revenue CAGR,
# PAT CAGR and P/E. OPM, P/B, Dividend Yield and ICR are
# retained as dashboard-side filters when explicitly enabled.
#
# This does NOT affect the integration test because those
# filters are disabled there.
# ------------------------------------------------------------

if not filtered.empty:

    if opm_enabled and "operating_profit_margin" in filtered.columns:
        filtered = filtered[
            filtered["operating_profit_margin"].notna()
            & (filtered["operating_profit_margin"] >= opm_min)
        ]

    if pb_enabled and "pb_ratio" in filtered.columns:
        filtered = filtered[
            filtered["pb_ratio"].notna() & (filtered["pb_ratio"] <= pb_max)
        ]

    if dividend_enabled and "dividend_yield_pct" in filtered.columns:
        filtered = filtered[
            filtered["dividend_yield_pct"].notna()
            & (filtered["dividend_yield_pct"] >= dividend_min)
        ]

    if icr_enabled and "interest_coverage" in filtered.columns:
        filtered = filtered[
            filtered["interest_coverage"].notna()
            & (filtered["interest_coverage"] >= icr_min)
        ]


# ============================================================
# RESULT COUNT
# ============================================================

st.subheader(f"📊 {len(filtered)} companies match your filters")


# ============================================================
# PREPARE RESULT TABLE
# ============================================================

display_columns = [
    "company_id",
    "company_name",
    "broad_sector",
    "final_score",
    "roe",
    "debt_to_equity",
    "free_cash_flow",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
    "interest_coverage",
]

display_columns = [column for column in display_columns if column in filtered.columns]

if display_columns:
    results = filtered[display_columns].copy()
else:
    # Keep all API columns if the API response contains a
    # different set of fields.
    results = filtered.copy()


# ============================================================
# RENAME COLUMNS
# ============================================================

results = results.rename(
    columns={
        "company_id": "Company ID",
        "ticker": "Ticker",
        "company_name": "Company Name",
        "name": "Company Name",
        "broad_sector": "Sector",
        "sector": "Sector",
        "final_score": "Composite Score",
        "roe": "ROE (%)",
        "debt_to_equity": "D/E",
        "free_cash_flow": "FCF",
        "revenue_cagr_5yr": "Revenue CAGR 5yr (%)",
        "pat_cagr_5yr": "PAT CAGR 5yr (%)",
        "operating_profit_margin": "OPM (%)",
        "pe_ratio": "P/E",
        "pb_ratio": "P/B",
        "dividend_yield_pct": "Dividend Yield (%)",
        "interest_coverage": "ICR",
    }
)

# If the API only supplied ticker, ensure the displayed
# table still has the Company ID column expected by the
# integration test.
if "Company ID" not in results.columns and "Ticker" in results.columns:
    results.insert(
        0,
        "Company ID",
        results["Ticker"],
    )


# ============================================================
# SORT BY COMPOSITE SCORE
# ============================================================

if "Composite Score" in results.columns:

    results = results.sort_values(
        "Composite Score",
        ascending=False,
        na_position="last",
    )

    if "Company ID" in results.columns:

        results = results.sort_values(
            [
                "Composite Score",
                "Company ID",
            ],
            ascending=[
                False,
                True,
            ],
            na_position="last",
        )


# ============================================================
# DISPLAY TABLE
# ============================================================

if results.empty:

    st.warning(
        "No companies match the current filters. " "Try relaxing one or more filters."
    )

else:

    st.dataframe(
        results,
        width="stretch",
        hide_index=True,
        height=550,
    )


# ============================================================
# CSV DOWNLOAD
# ============================================================

st.divider()

csv_data = results.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download Screener Results CSV",
    data=csv_data,
    file_name="nifty100_screener_results.csv",
    mime="text/csv",
    width="stretch",
)


# ============================================================
# DATA INFORMATION
# ============================================================

st.divider()

info1, info2, info3 = st.columns(3)


with info1:

    st.metric(
        "Total Universe",
        f"{len(base):,}",
    )


with info2:

    st.metric(
        "Matching Companies",
        f"{len(results):,}",
    )


with info3:

    if len(base) > 0:

        percentage = len(results) / len(base) * 100

        st.metric(
            "Match Percentage",
            f"{percentage:.1f}%",
        )

    else:

        st.metric(
            "Match Percentage",
            "0.0%",
        )


# ============================================================
# FOOTER
# ============================================================

st.caption("Nifty 100 Financial Intelligence Platform • " "Screener")
