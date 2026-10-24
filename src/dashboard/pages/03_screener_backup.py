import sys
from pathlib import Path

import pandas as pd
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
    get_historical_ratios,
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

        latest_market = latest_market.groupby("company_id", as_index=False).tail(1)


# ============================================================
# LOAD LATEST HISTORICAL RATIOS FOR ALL COMPANIES
# ============================================================
#
# IMPORTANT:
# The FastAPI screener reads historical_financial_ratios and
# explicitly selects the latest row for every company.
#
# The dashboard must use the SAME source and selection logic.
# Using get_ratios(ticker) here reads financial_ratios, which can
# contain a different/smaller set of current records. That was
# the reason the dashboard was returning only BEL and HAL while
# the API returned 52 companies for min_roe=15.
# ============================================================

ratio_frames = []

for ticker in companies["company_id"].dropna().unique():

    try:
        ratio_df = get_historical_ratios(ticker)

    except Exception:
        ratio_df = pd.DataFrame()

    if ratio_df is None or ratio_df.empty:
        continue

    ratio_df = ratio_df.copy()

    # Ensure year is sortable even when stored as:
    # Mar 2024, Mar 23, 2024, 2024, etc.
    if "year" in ratio_df.columns:

        ratio_df["_ratio_year"] = pd.to_numeric(
            ratio_df["year"].astype(str).str.extract(r"(\d{4})")[0],
            errors="coerce",
        )

        ratio_df = ratio_df.sort_values(
            ["_ratio_year", "year"],
            ascending=[True, True],
            na_position="first",
        )

        # Same company can have duplicate rows for a year.
        # Keep the final/latest database row.
        ratio_df = ratio_df.tail(1)

        ratio_df = ratio_df.drop(
            columns=["_ratio_year"],
            errors="ignore",
        )

    ratio_df["company_id"] = str(ticker).strip()

    ratio_frames.append(ratio_df)


if ratio_frames:

    ratios = pd.concat(
        ratio_frames,
        ignore_index=True,
    )

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

# Keep company identifiers consistent across all dashboard joins.
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
        # Normalize year
        # ----------------------------------------------------

        pl["_year"] = pd.to_numeric(
            pl["year"].astype(str).str.extract(r"(\d{4})")[0],
            errors="coerce",
        )

        # ----------------------------------------------------
        # Normalize financial columns
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
        # Latest available year
        # and five years earlier
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
        # Revenue CAGR
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
    tuple(companies["company_id"].dropna().unique())
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

# Each filter has an explicit enable/disable switch.
# This is important for API ↔ Dashboard integration:
# a disabled filter must not remove companies merely because
# the corresponding database value is NULL.


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
            min(100.0, preset_values["roe"]),
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
            min(10.0, preset_values["de"]),
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
            min(50000.0, preset_values["fcf"]),
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
            min(100.0, preset_values["revenue"]),
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
            min(100.0, preset_values["pat"]),
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
            min(100.0, preset_values["opm"]),
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
            min(1000.0, preset_values["pe"]),
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
            min(50.0, preset_values["pb"]),
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
            min(20.0, preset_values["dividend"]),
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
            min(100.0, preset_values["icr"]),
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

filtered = base.copy()


# ------------------------------------------------------------
# ROE
# ------------------------------------------------------------

if roe_enabled:
    filtered = filtered[filtered["roe"].notna() & (filtered["roe"] >= roe_min)]


# ------------------------------------------------------------
# D/E
# ------------------------------------------------------------

if de_enabled:
    filtered = filtered[
        filtered["debt_to_equity"].notna() & (filtered["debt_to_equity"] <= de_max)
    ]


# ------------------------------------------------------------
# FCF
# ------------------------------------------------------------

if fcf_enabled:
    filtered = filtered[
        filtered["free_cash_flow"].notna() & (filtered["free_cash_flow"] >= fcf_min)
    ]


# ------------------------------------------------------------
# REVENUE CAGR
# ------------------------------------------------------------

if revenue_cagr_enabled:
    filtered = filtered[
        filtered["revenue_cagr_5yr"].notna()
        & (filtered["revenue_cagr_5yr"] >= revenue_cagr_min)
    ]


# ------------------------------------------------------------
# PAT CAGR
# ------------------------------------------------------------

if pat_cagr_enabled:
    filtered = filtered[
        filtered["pat_cagr_5yr"].notna() & (filtered["pat_cagr_5yr"] >= pat_cagr_min)
    ]


# ------------------------------------------------------------
# OPM
# ------------------------------------------------------------

if opm_enabled:
    filtered = filtered[
        filtered["operating_profit_margin"].notna()
        & (filtered["operating_profit_margin"] >= opm_min)
    ]


# ------------------------------------------------------------
# P/E
# ------------------------------------------------------------

if pe_enabled:
    filtered = filtered[filtered["pe_ratio"].notna() & (filtered["pe_ratio"] <= pe_max)]


# ------------------------------------------------------------
# P/B
# ------------------------------------------------------------

if pb_enabled:
    filtered = filtered[filtered["pb_ratio"].notna() & (filtered["pb_ratio"] <= pb_max)]


# ------------------------------------------------------------
# DIVIDEND
# ------------------------------------------------------------

if dividend_enabled:
    filtered = filtered[
        filtered["dividend_yield_pct"].notna()
        & (filtered["dividend_yield_pct"] >= dividend_min)
    ]


# ------------------------------------------------------------
# ICR
# ------------------------------------------------------------

if icr_enabled:
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

results = filtered[display_columns].copy()


# ============================================================
# RENAME COLUMNS
# ============================================================

results = results.rename(
    columns={
        "company_id": "Company ID",
        "company_name": "Company Name",
        "broad_sector": "Sector",
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
            ["Composite Score", "Company ID"],
            ascending=[False, True],
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
