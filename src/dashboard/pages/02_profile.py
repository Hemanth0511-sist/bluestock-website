# ============================================================
# N100 FINANCIAL INTELLIGENCE PLATFORM
# DAY 23 - COMPANY PROFILE
# File: src/dashboard/pages/02_profile.py
# ============================================================

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# DATABASE IMPORT
# ============================================================

try:
    from src.dashboard.utils.db import (
        get_bs,
        get_cf,
        get_companies,
        get_pl,
        get_ratios,
    )
except ModuleNotFoundError:
    from dashboard.utils.db import (
        get_bs,
        get_cf,
        get_companies,
        get_pl,
        get_ratios,
    )


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Company Profile | Nifty 100 Analytics",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def is_missing(value):
    """Return True when value is None, NaN or empty."""
    if value is None:
        return True

    try:
        if pd.isna(value):
            return True
    except Exception:
        pass

    if isinstance(value, str) and not value.strip():
        return True

    return False


def safe_float(value):
    """Safely convert a value to float."""
    if is_missing(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def display_number(value, decimals=2):
    """Display numeric value or N/A."""
    number = safe_float(value)

    if number is None:
        return "N/A"

    return f"{number:,.{decimals}f}"


def clean_percent(value):
    """
    Normalize percentage values.

    The database can contain percentage values at either scale:

        0.14  -> 14.00%
        0.05  -> 5.00%
        47.44 -> 47.44%
        38.16 -> 38.16%

    Values between -1 and +1 are treated as decimal
    percentages and converted to percentage scale.
    """

    number = safe_float(value)

    if number is None:
        return "N/A"

    # Decimal percentage -> percentage
    if -1 <= number <= 1:
        number = number * 100

    return f"{number:.2f}%"


def normalize_percent_value(value):
    """
    Numeric version of clean_percent().

    Used for Plotly charts.
    """

    number = safe_float(value)

    if number is None:
        return None

    if -1 <= number <= 1:
        number = number * 100

    return number


def get_column(df, possible_names, default=None):
    """Get first matching column from a DataFrame."""
    if df is None or not isinstance(df, pd.DataFrame):
        return default

    for name in possible_names:
        if name in df.columns:
            return name

    return default


def first_value(df, possible_names, default=None):
    """Return first non-null value from matching DataFrame column."""
    column = get_column(df, possible_names)

    if column is None or df.empty:
        return default

    for value in df[column].tolist():
        if not is_missing(value):
            return value

    return default


def to_dataframe(data):
    """
    Convert different DB return types into DataFrame.

    Supports:
    - DataFrame
    - list of dictionaries
    - list of tuples
    - dictionary
    """

    if data is None:
        return pd.DataFrame()

    if isinstance(data, pd.DataFrame):
        return data.copy()

    if isinstance(data, dict):
        try:
            return pd.DataFrame(data)
        except Exception:
            return pd.DataFrame()

    if isinstance(data, list):
        if not data:
            return pd.DataFrame()

        try:
            # List of dictionaries
            if isinstance(data[0], dict):
                return pd.DataFrame(data)

            # List of tuples
            return pd.DataFrame(data)
        except Exception:
            return pd.DataFrame()

    return pd.DataFrame()


def sort_years(df):
    """Sort financial records chronologically."""

    if df.empty or "year" not in df.columns:
        return df

    result = df.copy()

    result["_year_sort"] = result["year"].astype(str).str.extract(r"(\d{4})")[0]

    result["_year_sort"] = pd.to_numeric(result["_year_sort"], errors="coerce")

    result = result.sort_values("_year_sort", kind="stable")

    return result.drop(columns=["_year_sort"])


def get_latest_record(df):
    """Return latest available financial record."""

    if df.empty:
        return None

    ordered = sort_years(df)

    if ordered.empty:
        return None

    return ordered.iloc[-1]


# ============================================================
# LOAD COMPANIES
# ============================================================


@st.cache_data(ttl=600)
def load_companies():
    try:
        return to_dataframe(get_companies())
    except Exception as exc:
        st.error(f"Unable to load companies: {exc}")
        return pd.DataFrame()


companies = load_companies()


# ============================================================
# PAGE HEADER
# ============================================================

st.title("🏢 Company Profile")

st.caption("Detailed financial profile for companies in the Nifty 100 universe")

st.divider()


# ============================================================
# VALIDATE COMPANY DATA
# ============================================================

if companies.empty:

    st.error(
        "Company data could not be loaded. " "Please check the N100 SQLite database."
    )

    st.stop()


# ============================================================
# NORMALIZE COMPANY COLUMNS
# ============================================================

company_id_col = get_column(companies, ["id", "company_id", "ticker"])

company_name_col = get_column(companies, ["company_name", "name"])

if company_id_col is None:

    st.error("Company ID column was not found in the companies table.")

    st.stop()


if company_name_col is None:

    st.error("Company name column was not found in the companies table.")

    st.stop()


companies[company_id_col] = (
    companies[company_id_col].astype(str).str.strip().str.upper()
)

companies[company_name_col] = (
    companies[company_name_col].fillna("").astype(str).str.strip()
)


# ============================================================
# SEARCH COMPANY
# ============================================================

st.subheader("🔎 Search company")

search_text = st.text_input(
    "Search company",
    placeholder="Enter company name or NSE ticker...",
    label_visibility="collapsed",
)


# ============================================================
# FILTER SEARCH RESULTS
# ============================================================

search_text_clean = search_text.strip().lower()

if search_text_clean:

    mask = companies[company_id_col].str.lower().str.contains(
        search_text_clean, na=False
    ) | companies[company_name_col].str.lower().str.contains(
        search_text_clean, na=False
    )

    filtered_companies = companies.loc[mask].copy()

else:

    filtered_companies = companies.copy()


# ============================================================
# COMPANY OPTIONS
# ============================================================

filtered_companies = filtered_companies.sort_values(company_name_col)

if filtered_companies.empty:

    st.warning("Ticker not found — please try another")

    st.stop()


def company_label(row):
    return f"{row[company_name_col]} " f"({row[company_id_col]})"


company_options = filtered_companies.to_dict(orient="records")

labels = [company_label(row) for row in company_options]


selected_label = st.selectbox("Select company", labels)


# ============================================================
# SELECTED COMPANY
# ============================================================

selected_index = labels.index(selected_label)

selected_company = company_options[selected_index]

ticker = str(selected_company[company_id_col]).strip().upper()

company_name = selected_company[company_name_col]


# ============================================================
# LOAD COMPANY FINANCIAL DATA
# ============================================================

try:
    ratios_raw = get_ratios(ticker)
except Exception:
    ratios_raw = None

try:
    pl_raw = get_pl(ticker)
except Exception:
    pl_raw = None

try:
    bs_raw = get_bs(ticker)
except Exception:
    bs_raw = None

try:
    cf_raw = get_cf(ticker)
except Exception:
    cf_raw = None


ratios_df = to_dataframe(ratios_raw)
pl_df = to_dataframe(pl_raw)
bs_df = to_dataframe(bs_raw)
cf_df = to_dataframe(cf_raw)


# ============================================================
# SORT DATA
# ============================================================

ratios_df = sort_years(ratios_df)
pl_df = sort_years(pl_df)
bs_df = sort_years(bs_df)
cf_df = sort_years(cf_df)


# ============================================================
# COMPANY SECTOR
# ============================================================

sector = "N/A"
sub_sector = "N/A"

try:

    # get_ratios may contain sector information in some versions
    sector = first_value(ratios_df, ["broad_sector", "sector"], None)

    sub_sector = first_value(ratios_df, ["sub_sector", "subsector"], None)

except Exception:
    pass


# ============================================================
# FALLBACK: GET SECTOR FROM DATABASE DIRECTLY
# ============================================================

if is_missing(sector) or is_missing(sub_sector):

    try:

        import sqlite3

        db_path = PROJECT_ROOT / "database" / "n100.db"

        connection = sqlite3.connect(str(db_path))

        sector_df = pd.read_sql_query(
            """
            SELECT
                broad_sector,
                sub_sector
            FROM sectors
            WHERE UPPER(TRIM(company_id)) = ?
            LIMIT 1
            """,
            connection,
            params=(ticker,),
        )

        connection.close()

        if not sector_df.empty:

            if is_missing(sector):
                sector = sector_df.iloc[0]["broad_sector"]

            if is_missing(sub_sector):
                sub_sector = sector_df.iloc[0]["sub_sector"]

    except Exception:
        pass


if is_missing(sector):
    sector = "N/A"

if is_missing(sub_sector):
    sub_sector = "N/A"


# ============================================================
# COMPANY INFORMATION
# ============================================================

about = selected_company.get("about_company", "N/A")

if is_missing(about):
    about = "N/A"


nse_ticker = selected_company.get("nse_profile", ticker)

if is_missing(nse_ticker):
    nse_ticker = ticker


# ============================================================
# COMPANY CARD
# ============================================================

st.markdown(f"## 📌 {company_name}")

info1, info2, info3, info4 = st.columns(4)

with info1:

    st.markdown("**NSE Ticker**")
    st.write(nse_ticker)

with info2:

    st.markdown("**Sector**")
    st.write(sector)

with info3:

    st.markdown("**Sub-Sector**")
    st.write(sub_sector)

with info4:

    st.markdown("**Company ID**")
    st.write(ticker)


st.markdown("### About")

st.write(about)


st.divider()


# ============================================================
# LATEST RATIOS
# ============================================================

latest_ratio = get_latest_record(ratios_df)


roe = None
roce = None
npm = None
de = None
fcf = None


if latest_ratio is not None:

    if "roe" in latest_ratio.index:
        roe = latest_ratio["roe"]

    if "roce" in latest_ratio.index:
        roce = latest_ratio["roce"]

    if "net_profit_margin" in latest_ratio.index:
        npm = latest_ratio["net_profit_margin"]

    if "debt_to_equity" in latest_ratio.index:
        de = latest_ratio["debt_to_equity"]

    if "free_cash_flow" in latest_ratio.index:
        fcf = latest_ratio["free_cash_flow"]


# ============================================================
# REVENUE CAGR 5 YEAR
# ============================================================

revenue_cagr_5yr = None

if not pl_df.empty and "sales" in pl_df.columns:

    revenue_data = pl_df[["year", "sales"]].copy()

    revenue_data["sales"] = pd.to_numeric(revenue_data["sales"], errors="coerce")

    revenue_data = revenue_data.dropna(subset=["sales"])

    revenue_data = sort_years(revenue_data)

    if len(revenue_data) >= 6:

        start_sales = float(revenue_data.iloc[-6]["sales"])

        end_sales = float(revenue_data.iloc[-1]["sales"])

        if start_sales > 0 and end_sales >= 0:

            try:

                revenue_cagr_5yr = (((end_sales / start_sales) ** (1 / 5)) - 1) * 100

            except Exception:
                revenue_cagr_5yr = None


# ============================================================
# KEY FINANCIAL METRICS
# ============================================================

st.subheader("📊 Key Financial Metrics")

k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:

    st.metric("ROE", clean_percent(roe))

with k2:

    st.metric("ROCE", clean_percent(roce))

with k3:

    st.metric("Net Profit Margin", clean_percent(npm))

with k4:

    st.metric("Debt / Equity", display_number(de))

with k5:

    st.metric("Revenue CAGR 5yr", clean_percent(revenue_cagr_5yr))

with k6:

    st.metric("FCF", display_number(fcf))


# ============================================================
# DATA AVAILABILITY
# ============================================================

period_count = max(len(pl_df), len(ratios_df), len(bs_df), len(cf_df))

if period_count > 0:

    st.info(f"Data available for {period_count} financial periods.")

else:

    st.warning("No historical financial data is available for this company.")


st.divider()


# ============================================================
# REVENUE & NET PROFIT HISTORICAL CHART
# ============================================================

st.subheader("📈 Revenue & Net Profit — Historical Trend")


if (
    not pl_df.empty
    and "year" in pl_df.columns
    and "sales" in pl_df.columns
    and "net_profit" in pl_df.columns
):

    chart_df = pl_df[["year", "sales", "net_profit"]].copy()

    chart_df["sales"] = pd.to_numeric(chart_df["sales"], errors="coerce")

    chart_df["net_profit"] = pd.to_numeric(chart_df["net_profit"], errors="coerce")

    chart_df = chart_df.dropna(subset=["year"])

    chart_df = chart_df.tail(10)

    if not chart_df.empty:

        fig_revenue = go.Figure()

        fig_revenue.add_trace(
            go.Bar(x=chart_df["year"], y=chart_df["sales"], name="Revenue")
        )

        fig_revenue.add_trace(
            go.Bar(x=chart_df["year"], y=chart_df["net_profit"], name="Net Profit")
        )

        fig_revenue.update_layout(
            barmode="group",
            height=480,
            margin=dict(l=20, r=20, t=30, b=40),
            xaxis_title="Financial Year",
            yaxis_title="Amount",
            legend_title="Metric",
        )

        st.plotly_chart(fig_revenue, use_container_width=True)

    else:

        st.info("Revenue and Net Profit historical data unavailable.")

else:

    st.info("Revenue and Net Profit historical data unavailable.")


st.divider()


# ============================================================
# ROE & ROCE HISTORICAL CHART
# ============================================================

st.subheader("📊 ROE & ROCE — Historical Trend")

try:
    import sqlite3

    db_path = PROJECT_ROOT / "database" / "n100.db"

    connection = sqlite3.connect(str(db_path))

    trend_df = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            roe,
            roce
        FROM historical_financial_ratios
        WHERE UPPER(TRIM(company_id)) = ?
        ORDER BY
            CAST(
                substr(year, -4)
                AS INTEGER
            )
        """,
        connection,
        params=(ticker,),
    )

    connection.close()

except Exception:
    trend_df = pd.DataFrame()


if not trend_df.empty:

    trend_df["roe"] = pd.to_numeric(trend_df["roe"], errors="coerce")

    trend_df["roce"] = pd.to_numeric(trend_df["roce"], errors="coerce")

    # Convert decimal-scale values to percentage scale.
    # Example:
    # 0.1434 -> 14.34
    # 14.34  -> 14.34
    trend_df["roe"] = trend_df["roe"].apply(normalize_percent_value)

    trend_df["roce"] = trend_df["roce"].apply(normalize_percent_value)

    trend_df = trend_df.dropna(subset=["roe", "roce"])

    trend_df = trend_df.tail(10)

    if not trend_df.empty:

        fig_roe = go.Figure()

        fig_roe.add_trace(
            go.Scatter(
                x=trend_df["year"],
                y=trend_df["roe"],
                mode="lines+markers",
                name="ROE",
                line=dict(width=3),
                marker=dict(size=7),
                hovertemplate=(
                    "<b>ROE</b><br>" "Year: %{x}<br>" "ROE: %{y:.2f}%" "<extra></extra>"
                ),
            )
        )

        fig_roe.add_trace(
            go.Scatter(
                x=trend_df["year"],
                y=trend_df["roce"],
                mode="lines+markers",
                name="ROCE",
                line=dict(width=3),
                marker=dict(size=7),
                hovertemplate=(
                    "<b>ROCE</b><br>"
                    "Year: %{x}<br>"
                    "ROCE: %{y:.2f}%"
                    "<extra></extra>"
                ),
            )
        )

        fig_roe.update_layout(
            height=480,
            margin=dict(l=20, r=20, t=30, b=40),
            xaxis_title="Financial Year",
            yaxis_title="Percentage (%)",
            hovermode="x unified",
            legend_title="Metric",
        )

        st.plotly_chart(fig_roe, use_container_width=True)

    else:

        st.info("ROE and ROCE historical data unavailable.")

else:

    st.info("ROE and ROCE historical data unavailable.")

# ============================================================
# PROS & CONS
# ============================================================

st.subheader("⚖️ Pros & Cons")


def load_pros_cons(company_id):
    """
    Load pros and cons directly from SQLite.

    This avoids dependency on any optional db.py function.
    """

    try:

        import sqlite3

        db_path = PROJECT_ROOT / "database" / "n100.db"

        connection = sqlite3.connect(str(db_path))

        result = pd.read_sql_query(
            """
            SELECT
                pros,
                cons
            FROM prosandcons
            WHERE UPPER(TRIM(company_id)) = ?
            LIMIT 1
            """,
            connection,
            params=(company_id,),
        )

        connection.close()

        return result

    except Exception:
        return pd.DataFrame()


pros_cons_df = load_pros_cons(ticker)


pros = []
cons = []


if not pros_cons_df.empty:

    pros_value = pros_cons_df.iloc[0].get("pros")

    cons_value = pros_cons_df.iloc[0].get("cons")

    if not is_missing(pros_value):

        if isinstance(pros_value, str):

            pros = [item.strip() for item in pros_value.split("|") if item.strip()]

            if len(pros) == 1:
                pros = [item.strip() for item in pros_value.split("\n") if item.strip()]

        else:

            pros = [str(pros_value)]

    if not is_missing(cons_value):

        if isinstance(cons_value, str):

            cons = [item.strip() for item in cons_value.split("|") if item.strip()]

            if len(cons) == 1:
                cons = [item.strip() for item in cons_value.split("\n") if item.strip()]

        else:

            cons = [str(cons_value)]


# ============================================================
# PROS / CONS DISPLAY
# ============================================================

pros_col, cons_col = st.columns(2)


with pros_col:

    st.markdown("### 🟢 Pros")

    if pros:

        for item in pros:

            st.success(f"✓ {item}")

    else:

        st.info("No pros available.")


with cons_col:

    st.markdown("### 🔴 Cons")

    if cons:

        for item in cons:

            st.error(f"✕ {item}")

    else:

        st.info("No cons available.")


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "All profile metrics are calculated from the N100 SQLite "
    "database. Missing or unavailable values are displayed as N/A."
)
