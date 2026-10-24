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
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Annual Reports | Nifty 100 Analytics", page_icon="📄", layout="wide"
)


# ============================================================
# DATABASE PATH
# ============================================================

DB_PATH = PROJECT_ROOT / "database" / "n100.db"


# ============================================================
# LOAD DOCUMENTS
# ============================================================


@st.cache_data(ttl=600)
def get_documents():

    conn = sqlite3.connect(DB_PATH)

    try:
        rows = conn.execute("SELECT * FROM documents").fetchall()

    finally:
        conn.close()

    if not rows:
        return pd.DataFrame(columns=["id", "company_id", "Year", "Annual_Report"])

    # --------------------------------------------------------
    # The database table has generic/malformed column names.
    # The FIRST ROW contains the actual headers.
    # --------------------------------------------------------

    first_row = [str(x).strip() for x in rows[0]]

    expected_headers = {"id", "company_id", "year", "annual_report"}

    normalized_headers = {x.lower().replace(" ", "_") for x in first_row}

    # If first row is the actual header
    if expected_headers.issubset(normalized_headers):

        headers = [x.lower().strip().replace(" ", "_") for x in first_row]

        data = rows[1:]

    else:

        # Fallback
        headers = ["id", "company_id", "year", "annual_report"]

        data = rows

    df = pd.DataFrame(data, columns=headers)

    # --------------------------------------------------------
    # Rename possible variations
    # --------------------------------------------------------

    rename_map = {}

    for col in df.columns:

        normalized = str(col).lower().strip()

        if normalized in ["company", "ticker", "symbol"]:
            rename_map[col] = "company_id"

        elif normalized in [
            "annual_report",
            "annualreport",
            "report",
            "report_url",
            "url",
        ]:
            rename_map[col] = "annual_report"

        elif normalized in ["year", "financial_year"]:
            rename_map[col] = "year"

    df = df.rename(columns=rename_map)

    # --------------------------------------------------------
    # Make sure required columns exist
    # --------------------------------------------------------

    required_columns = ["company_id", "year", "annual_report"]

    for col in required_columns:

        if col not in df.columns:
            df[col] = None

    # --------------------------------------------------------
    # Clean data
    # --------------------------------------------------------

    df["company_id"] = df["company_id"].astype(str).str.strip().str.upper()

    df["year"] = df["year"].astype(str).str.strip()

    df["annual_report"] = df["annual_report"].astype(str).str.strip()

    # Remove invalid/header rows
    df = df[
        (df["company_id"] != "")
        & (df["company_id"] != "NONE")
        & (df["company_id"] != "COMPANY_ID")
        & (df["year"] != "YEAR")
        & (df["annual_report"] != "ANNUAL_REPORT")
    ]

    return df


# ============================================================
# CHECK REPORT URL
# ============================================================


@st.cache_data(ttl=3600)
def check_report_url(url):

    if not url:
        return False

    if not str(url).startswith("http"):
        return False

    try:

        response = requests.head(url, timeout=8, allow_redirects=True)

        # BSE can sometimes reject HEAD requests.
        # Only mark unavailable when we receive an actual 404.
        if response.status_code == 404:
            return False

        if response.status_code in [200, 301, 302, 403]:
            return True

        # Try GET if HEAD gives another response
        response = requests.get(url, timeout=8, stream=True, allow_redirects=True)

        return response.status_code != 404

    except requests.RequestException:

        # Don't incorrectly mark a valid BSE URL unavailable
        # because of network restrictions.
        return True


# ============================================================
# LOAD DATA
# ============================================================

documents = get_documents()


# ============================================================
# PAGE HEADER
# ============================================================

st.title("📄 Annual Reports")

st.write("Find and access available annual reports for Nifty 100 companies.")

st.divider()


# ============================================================
# DATABASE ERROR
# ============================================================

if documents.empty:

    st.error("No annual report records were found in the documents table.")

    st.stop()


# ============================================================
# COMPANY SEARCH
# ============================================================

st.sidebar.header("📄 Report Controls")

search_text = st.sidebar.text_input(
    "Search Company", placeholder="Enter company name or ticker..."
)


# ============================================================
# GET COMPANY INFORMATION
# ============================================================


@st.cache_data(ttl=600)
def get_company_mapping():

    conn = sqlite3.connect(DB_PATH)

    try:

        tables = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """).fetchall()

        table_names = {row[0] for row in tables}

        if "companies" not in table_names:
            return pd.DataFrame()

        df = pd.read_sql_query("SELECT * FROM companies", conn)

    finally:

        conn.close()

    return df


companies = get_company_mapping()


# ============================================================
# FIND COMPANY NAME COLUMN
# ============================================================

company_name_column = None
company_id_column = None

if not companies.empty:

    for col in companies.columns:

        normalized = str(col).lower().strip()

        if normalized in ["company_name", "name", "company"]:
            company_name_column = col

        if normalized in ["company_id", "ticker", "symbol", "nse_ticker"]:
            company_id_column = col


# ============================================================
# CREATE SEARCH OPTIONS
# ============================================================

company_options = sorted(documents["company_id"].dropna().astype(str).unique().tolist())


# ============================================================
# SEARCH FILTER
# ============================================================

if search_text:

    search_upper = search_text.strip().upper()

    matching_tickers = [
        ticker for ticker in company_options if search_upper in ticker.upper()
    ]

    # Search company names if available
    if (
        not companies.empty
        and company_name_column is not None
        and company_id_column is not None
    ):

        for _, row in companies.iterrows():

            ticker = str(row[company_id_column]).strip().upper()

            company_name = str(row[company_name_column]).strip()

            if search_upper in company_name.upper():

                if ticker in company_options:
                    matching_tickers.append(ticker)

    matching_tickers = sorted(set(matching_tickers))

else:

    matching_tickers = company_options


# ============================================================
# COMPANY DROPDOWN
# ============================================================

if not matching_tickers:

    st.warning("Company not found — please try another company or ticker.")

    st.stop()


selected_ticker = st.sidebar.selectbox("Select Company", matching_tickers)


# ============================================================
# COMPANY NAME
# ============================================================

company_name = selected_ticker

if (
    not companies.empty
    and company_name_column is not None
    and company_id_column is not None
):

    company_rows = companies[
        companies[company_id_column].astype(str).str.upper().str.strip()
        == selected_ticker
    ]

    if not company_rows.empty:

        company_name = str(company_rows.iloc[0][company_name_column])


# ============================================================
# COMPANY HEADER
# ============================================================

st.subheader(f"🏢 {company_name}")

st.caption(f"NSE Ticker: {selected_ticker}")

st.divider()


# ============================================================
# FILTER REPORTS
# ============================================================

company_reports = documents[documents["company_id"] == selected_ticker].copy()


if company_reports.empty:

    st.warning("No annual reports are available for this company.")

    st.stop()


# ============================================================
# YEAR SORT
# ============================================================


def year_sort(value):

    try:
        return int(str(value))
    except:
        return 0


company_reports["_sort_year"] = company_reports["year"].apply(year_sort)

company_reports = company_reports.sort_values("_sort_year", ascending=False)


# ============================================================
# SUMMARY
# ============================================================

col1, col2, col3 = st.columns(3)

with col1:

    st.metric("Available Reports", len(company_reports))

with col2:

    latest_year = company_reports.iloc[0]["year"]

    st.metric("Latest Report", latest_year)

with col3:

    oldest_year = company_reports.iloc[-1]["year"]

    st.metric("Oldest Report", oldest_year)


st.divider()


# ============================================================
# AVAILABLE REPORTS
# ============================================================

st.subheader("📚 Available Annual Reports")

st.write(f"Annual reports available for **{company_name}**:")


# ============================================================
# REPORT LIST
# ============================================================

for _, row in company_reports.iterrows():

    year = str(row["year"])

    url = str(row["annual_report"]).strip()

    col1, col2, col3 = st.columns([1.5, 3, 1.5])

    with col1:

        st.markdown(f"### 📅 {year}")

    with col2:

        if url.startswith("http"):

            st.markdown(f"[🔗 Open BSE Annual Report]({url})")

        else:

            st.write("No valid report URL available.")

    with col3:

        if url.startswith("http"):

            available = check_report_url(url)

            if available:

                st.success("Report available")

            else:

                st.error("Report unavailable")

        else:

            st.error("Report unavailable")

    st.divider()


# ============================================================
# DATA TABLE
# ============================================================

with st.expander("View Report Data"):

    display_df = company_reports[["company_id", "year", "annual_report"]].copy()

    display_df.columns = ["Company", "Year", "Annual Report URL"]

    st.dataframe(display_df, use_container_width=True, hide_index=True)
