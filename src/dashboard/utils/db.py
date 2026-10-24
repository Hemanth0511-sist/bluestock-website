import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

# ============================================================
# DATABASE PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATABASE_PATH = PROJECT_ROOT / "database" / "n100.db"


# ============================================================
# DATABASE HELPER
# ============================================================


def _read_sql(query, params=None):
    """
    Execute a SQL SELECT query and return the result
    as a pandas DataFrame.
    """

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        dataframe = pd.read_sql_query(query, connection, params=params)
    finally:
        connection.close()

    return dataframe


# ============================================================
# COMPANIES
# ============================================================


@st.cache_data(ttl=600)
def get_companies():
    """
    Return all N100 companies with sector information.
    """

    query = """
        SELECT
            c.id AS company_id,
            c.company_name,
            c.company_logo,
            c.about_company,
            c.website,
            c.nse_profile,
            c.bse_profile,
            c.face_value,
            c.book_value,
            c.roce_percentage,
            c.roe_percentage,
            s.broad_sector,
            s.sub_sector,
            s.index_weight_pct,
            s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s
            ON c.id = s.company_id
        ORDER BY c.company_name
    """

    return _read_sql(query)


# ============================================================
# FINANCIAL RATIOS
# ============================================================


@st.cache_data(ttl=600)
def get_ratios(ticker=None, year=None):
    """
    Return financial ratios.

    ticker=None:
        Return ratios for all companies.

    ticker=<symbol>:
        Return ratios for one company.

    year=None:
        For a ticker, return the current/latest ratio record.
        For ticker=None, return all historical ratio records.

    year=<YYYY>:
        Return historical ratios for the requested year.
    """

    if ticker is None:

        if year is None:
            query = """
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
                    free_cash_flow,
                    cfo_quality,
                    capex_intensity,
                    icr_label,
                    icr_warning,
                    high_leverage
                FROM historical_financial_ratios
                ORDER BY company_id, year
            """
            return _read_sql(query)

        query = """
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
                free_cash_flow,
                cfo_quality,
                capex_intensity,
                icr_label,
                icr_warning,
                high_leverage
            FROM historical_financial_ratios
            WHERE year = ?
            ORDER BY company_id
        """
        return _read_sql(query, (f"Mar {year}",))

    if year is None:

        query = """
            SELECT
                company_id,
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
            FROM financial_ratios
            WHERE company_id = ?
        """
        return _read_sql(query, (ticker,))

    query = """
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
            free_cash_flow,
            cfo_quality,
            capex_intensity,
            icr_label,
            icr_warning,
            high_leverage
        FROM historical_financial_ratios
        WHERE company_id = ?
          AND year = ?
    """

    return _read_sql(query, (ticker, f"Mar {year}"))


# ============================================================
# HISTORICAL FINANCIAL RATIOS
# ============================================================


@st.cache_data(ttl=600)
def get_historical_ratios(ticker):
    """
    Return all available historical financial ratios
    for a company.

    Historical years are stored in values such as:
    Mar 2012
    Mar 2014
    Mar 2015
    """

    query = """
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
            free_cash_flow,
            cfo_quality,
            capex_intensity,
            icr_label,
            icr_warning,
            high_leverage
        FROM historical_financial_ratios
        WHERE company_id = ?
        ORDER BY year
    """

    return _read_sql(query, (ticker,))


# ============================================================
# PROFIT & LOSS
# ============================================================


@st.cache_data(ttl=600)
def get_pl(ticker):
    """
    Return Profit & Loss data for a company.
    """

    query = """
        SELECT
            company_id,
            year,
            sales,
            expenses,
            operating_profit,
            opm_percentage,
            other_income,
            interest,
            depreciation,
            profit_before_tax,
            tax_percentage,
            net_profit,
            eps,
            dividend_payout
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY year
    """

    return _read_sql(query, (ticker,))


# ============================================================
# ALL PROFIT & LOSS RECORDS
# ============================================================


@st.cache_data(ttl=600)
def get_pl_all():
    """Return Profit & Loss data for all companies."""
    query = """
        SELECT
            company_id,
            year,
            sales,
            expenses,
            operating_profit,
            opm_percentage,
            other_income,
            interest,
            depreciation,
            profit_before_tax,
            tax_percentage,
            net_profit,
            eps,
            dividend_payout
        FROM profitandloss
        ORDER BY company_id, year
    """
    return _read_sql(query)


# ============================================================
# BALANCE SHEET
# ============================================================


@st.cache_data(ttl=600)
def get_bs(ticker):
    """
    Return Balance Sheet data for a company.
    """

    query = """
        SELECT
            company_id,
            year,
            equity_capital,
            reserves,
            borrowings,
            other_liabilities,
            total_liabilities,
            fixed_assets,
            cwip,
            investments,
            other_asset,
            total_assets
        FROM balancesheet
        WHERE company_id = ?
        ORDER BY year
    """

    return _read_sql(query, (ticker,))


# ============================================================
# CASH FLOW
# ============================================================


@st.cache_data(ttl=600)
def get_cf(ticker):
    """
    Return Cash Flow data for a company.
    """

    query = """
        SELECT
            company_id,
            year,
            operating_activity,
            investing_activity,
            financing_activity,
            net_cash_flow
        FROM cashflow
        WHERE company_id = ?
        ORDER BY year
    """

    return _read_sql(query, (ticker,))


# ============================================================
# SECTORS
# ============================================================


@st.cache_data(ttl=600)
def get_sectors():
    """
    Return sector information for all companies.
    """

    query = """
        SELECT
            id,
            company_id,
            broad_sector,
            sub_sector,
            index_weight_pct,
            market_cap_category
        FROM sectors
        ORDER BY broad_sector, sub_sector
    """

    return _read_sql(query)


# ============================================================
# PEER GROUPS
# ============================================================

# ============================================================
# PEER GROUPS
# ============================================================


@st.cache_data(ttl=600)
def get_peers(group_name):
    """
    Return all companies belonging to a selected peer group.

    Parameters
    ----------
    group_name : str
        Peer group name such as:
        Banks
        Financial Services
        Insurance
        Information Technology
        Automobiles
        Pharmaceuticals
        Consumer
        Energy
        Industrials
        Telecom
        Others

    Returns
    -------
    pandas.DataFrame
        Peer group companies with benchmark information.
    """

    query = """
        SELECT
            pg.id,
            pg.peer_group_name,
            pg.company_id,
            pg.is_benchmark,
            c.company_name AS name
        FROM peer_groups pg
        LEFT JOIN companies c
            ON pg.company_id = c.id
        WHERE pg.peer_group_name = ?
        ORDER BY
            pg.is_benchmark DESC,
            c.company_name
    """

    return _read_sql(query, (group_name,))


# ============================================================
# VALUATION
# ============================================================


@st.cache_data(ttl=600)
def get_valuation(ticker):
    """
    Return valuation information for a company.

    The valuation table will be generated during Day 26.
    Until then, return an empty DataFrame safely.
    """

    query = """
        SELECT
            company_id,
            company_name,
            sector,
            pe,
            pb,
            ev_ebitda,
            fcf_yield_pct,
            median_pe,
            pe_vs_sector_median_pct,
            flag
        FROM valuation
        WHERE company_id = ?
    """

    try:
        return _read_sql(query, (ticker,))

    except Exception:
        return pd.DataFrame()


# ============================================================
# ADDITIONAL HELPERS FOR DASHBOARD
# ============================================================


@st.cache_data(ttl=600)
def get_rankings():
    """
    Return company ranking information.
    """

    query = """
        SELECT
            company_id,
            quality_score,
            growth_score,
            value_score,
            risk_score,
            final_score,
            recommendation,
            overall_rank
        FROM company_rankings
        ORDER BY overall_rank
    """

    return _read_sql(query)


# ============================================================
# MARKET CAP
# ============================================================


@st.cache_data(ttl=600)
def get_market_cap(year=None):
    """
    Return market cap and valuation information.

    If year is provided, return only that year.
    Otherwise return all available years.
    """

    if year is None:

        query = """
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
        """

        return _read_sql(query)

    query = """
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
        WHERE year = ?
    """

    return _read_sql(query, (year,))


# ============================================================
# STOCK PRICES
# ============================================================


@st.cache_data(ttl=600)
def get_stock_prices(ticker):
    """
    Return historical stock prices for a company.
    """

    query = """
        SELECT
            company_id,
            date,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            adjusted_close
        FROM stock_prices
        WHERE company_id = ?
        ORDER BY date
    """

    return _read_sql(query, (ticker,))


# ============================================================
# PROS & CONS
# ============================================================


@st.cache_data(ttl=600)
def get_pros_cons(company_id):
    """
    Get qualitative pros and cons for a company.
    """

    query = """
        SELECT
            company_id,
            pros,
            cons
        FROM prosandcons
        WHERE company_id = ?
        ORDER BY id
    """

    try:
        return _read_sql(query, (company_id,))

    except Exception as e:

        print(f"Error loading pros and cons for {company_id}: {e}")

        return pd.DataFrame(
            columns=[
                "company_id",
                "pros",
                "cons",
            ]
        )
