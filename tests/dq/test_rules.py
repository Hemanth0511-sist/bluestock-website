import pandas as pd

from src.etl.validator import DataValidator

validator = DataValidator()


def assert_failed_rule(result, rule_id):
    assert isinstance(result, dict)
    assert result["rule_id"] == rule_id
    assert result["severity"] == DataValidator.RULE_SEVERITY[rule_id]
    assert result["valid"] is False


# ============================================================
# DQ-01 — Company PK Uniqueness
# ============================================================


def test_dq_01_duplicate_company_primary_key():
    df = pd.DataFrame({"id": ["TCS", "TCS", "INFY"]})

    result = validator.check_dq_01(df)

    assert_failed_rule(result, "DQ-01")
    assert result["row_indices"] == [0, 1]


# ============================================================
# DQ-02 — Annual PK Uniqueness
# ============================================================


def test_dq_02_duplicate_company_year():
    df = pd.DataFrame(
        {
            "company_id": ["TCS", "TCS", "INFY"],
            "year": ["2024-03", "2024-03", "2024-03"],
        }
    )

    result = validator.check_dq_02(df)

    assert_failed_rule(result, "DQ-02")
    assert result["row_indices"] == [0, 1]


# ============================================================
# DQ-03 — Foreign Key Integrity
# ============================================================


def test_dq_03_orphan_company_id():
    companies_df = pd.DataFrame({"id": ["TCS", "INFY"]})

    df = pd.DataFrame({"company_id": ["TCS", "UNKNOWN"]})

    result = validator.check_dq_03(df, companies_df)

    assert_failed_rule(result, "DQ-03")
    assert result["row_indices"] == [1]


# ============================================================
# DQ-04 — Balance Sheet Balance
# ============================================================


def test_dq_04_balance_sheet_imbalance():
    df = pd.DataFrame({"total_assets": [1000], "total_liabilities": [900]})

    result = validator.check_dq_04(df)

    assert_failed_rule(result, "DQ-04")
    assert result["row_indices"] == [0]


# ============================================================
# DQ-05 — OPM Cross-Check
# ============================================================


def test_dq_05_opm_cross_check_divergence():
    df = pd.DataFrame(
        {"opm_percentage": [10], "operating_profit": [20], "sales": [100]}
    )

    result = validator.check_dq_05(df)

    assert_failed_rule(result, "DQ-05")
    assert result["row_indices"] == [0]


# ============================================================
# DQ-06 — Positive Sales
# ============================================================


def test_dq_06_non_bank_non_positive_sales():
    df = pd.DataFrame({"sales": [0], "broad_sector": ["Information Technology"]})

    result = validator.check_dq_06(df)

    assert_failed_rule(result, "DQ-06")
    assert result["row_indices"] == [0]


# ============================================================
# DQ-07 — Year Format
# ============================================================


def test_dq_07_invalid_year_format():
    df = pd.DataFrame({"year": ["FY2024"]})

    result = validator.check_dq_07(df)

    assert_failed_rule(result, "DQ-07")
    assert result["row_indices"] == [0]


# ============================================================
# DQ-08 — Ticker Format
# ============================================================


def test_dq_08_invalid_ticker_format():
    df = pd.DataFrame({"ticker": ["INVALID@TICKER!"]})

    result = validator.check_dq_08(df)

    assert_failed_rule(result, "DQ-08")
    assert result["row_indices"] == [0]


# ============================================================
# DQ-09 — Net Cash Flow Check
# ============================================================


def test_dq_09_net_cash_flow_mismatch():
    df = pd.DataFrame({"net_cash_flow": [100], "cfo": [10], "cfi": [10], "cff": [10]})

    result = validator.check_dq_09(df)

    assert_failed_rule(result, "DQ-09")
    assert result["row_indices"] == [0]


# ============================================================
# DQ-10 — Non-Negative Fixed Assets
# ============================================================


def test_dq_10_negative_fixed_assets():
    df = pd.DataFrame({"fixed_assets": [-100]})

    result = validator.check_dq_10(df)

    assert_failed_rule(result, "DQ-10")
    assert result["row_indices"] == [0]


# ============================================================
# DQ-11 — Tax Rate Range
# ============================================================


def test_dq_11_tax_rate_above_allowed_range():
    df = pd.DataFrame({"tax_rate": [61]})

    result = validator.check_dq_11(df)

    assert_failed_rule(result, "DQ-11")
    assert result["row_indices"] == [0]


# ============================================================
# DQ-12 — Dividend Payout Cap
# ============================================================


def test_dq_12_dividend_payout_above_cap():
    df = pd.DataFrame({"dividend_payout": [201]})

    result = validator.check_dq_12(df)

    assert_failed_rule(result, "DQ-12")
    assert result["row_indices"] == [0]


# ============================================================
# DQ-13 — URL Validity
# ============================================================


def test_dq_13_invalid_annual_report_url(monkeypatch):
    df = pd.DataFrame(
        {"annual_report_url": ["https://invalid-example-url.com/report.pdf"]}
    )

    # Avoid making a real internet request during a unit test.
    monkeypatch.setattr(validator, "check_url", lambda url: False)

    result = validator.check_dq_13(df)

    assert_failed_rule(result, "DQ-13")
    assert result["row_indices"] == [0]


# ============================================================
# DQ-14 — EPS Sign Consistency
# ============================================================


def test_dq_14_positive_profit_negative_eps():
    df = pd.DataFrame({"net_profit": [100], "eps": [-1]})

    result = validator.check_dq_14(df)

    assert_failed_rule(result, "DQ-14")
    assert result["row_indices"] == [0]
