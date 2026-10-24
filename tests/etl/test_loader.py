import pytest

from src.etl.loader import ExcelLoader


@pytest.fixture(scope="module")
def datasets():
    return ExcelLoader().load_all_excels()


def test_analysis_dataset(datasets):
    df = datasets["analysis"]

    assert len(df) == 21
    assert list(df.columns) == [
        "Bluestock Fintech — Nifty 100  |  Analysis  |  20 records",
        "Unnamed: 1",
        "Unnamed: 2",
        "Unnamed: 3",
        "Unnamed: 4",
        "Unnamed: 5",
    ]


def test_balance_sheet_dataset(datasets):
    df = datasets["balancesheet"]

    assert len(df) == 1312
    assert list(df.columns) == [
        "id",
        "company_id",
        "year",
        "equity_capital",
        "reserves",
        "borrowings",
        "other_liabilities",
        "total_liabilities",
        "fixed_assets",
        "cwip",
        "investments",
        "other_asset",
        "total_assets",
    ]


def test_cashflow_dataset(datasets):
    df = datasets["cashflow"]

    assert len(df) == 1187
    assert list(df.columns) == [
        "id",
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]


def test_companies_dataset(datasets):
    df = datasets["companies"]

    assert len(df) == 92
    assert list(df.columns) == [
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


def test_documents_dataset(datasets):
    df = datasets["documents"]

    assert len(df) == 1586
    assert list(df.columns) == [
        "Bluestock Fintech — Nifty 100  |  Documents  |  1,585 records",
        "Unnamed: 1",
        "Unnamed: 2",
        "Unnamed: 3",
    ]


def test_financial_ratios_dataset(datasets):
    df = datasets["financial_ratios"]

    assert len(df) == 1184
    assert list(df.columns) == [
        "id",
        "company_id",
        "year",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "capex_cr",
        "earnings_per_share",
        "book_value_per_share",
        "dividend_payout_ratio_pct",
        "total_debt_cr",
        "cash_from_operations_cr",
    ]


def test_market_cap_and_peer_groups(datasets):
    market_cap = datasets["market_cap"]
    peer_groups = datasets["peer_groups"]

    assert len(market_cap) == 552
    assert list(market_cap.columns) == [
        "id",
        "company_id",
        "year",
        "market_cap_crore",
        "enterprise_value_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
    ]

    assert len(peer_groups) == 56
    assert list(peer_groups.columns) == [
        "id",
        "peer_group_name",
        "company_id",
        "is_benchmark",
    ]


def test_profit_and_loss_dataset(datasets):
    df = datasets["profitandloss"]

    assert len(df) == 1276
    assert list(df.columns) == [
        "id",
        "company_id",
        "year",
        "sales",
        "expenses",
        "operating_profit",
        "opm_percentage",
        "other_income",
        "interest",
        "depreciation",
        "profit_before_tax",
        "tax_percentage",
        "net_profit",
        "eps",
        "dividend_payout",
    ]


def test_pros_and_cons_and_sectors(datasets):
    pros_cons = datasets["prosandcons"]
    sectors = datasets["sectors"]

    assert len(pros_cons) == 17
    assert list(pros_cons.columns) == [
        "Bluestock Fintech — Nifty 100  |  Pros & Cons  |  16 records",
        "Unnamed: 1",
        "Unnamed: 2",
        "Unnamed: 3",
    ]

    assert len(sectors) == 92
    assert list(sectors.columns) == [
        "id",
        "company_id",
        "broad_sector",
        "sub_sector",
        "index_weight_pct",
        "market_cap_category",
    ]


def test_stock_prices_dataset(datasets):
    df = datasets["stock_prices"]

    assert len(df) == 5520
    assert list(df.columns) == [
        "id",
        "company_id",
        "date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
        "adjusted_close",
    ]
