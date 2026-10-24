import pytest

from src.analysis.cagr import CAGR
from src.analysis.metrics import FinancialMetrics
from src.analysis.ratios import RatioEngine

# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def metrics():
    return FinancialMetrics()


@pytest.fixture
def ratio_engine():
    """
    Create RatioEngine without opening the real database.

    calculate_from_records() only needs the metrics object,
    so this keeps these tests isolated from SQLite.
    """
    engine = RatioEngine.__new__(RatioEngine)
    engine.metrics = FinancialMetrics()
    return engine


def make_pnl(
    sales=1000,
    expenses=700,
    operating_profit=300,
    other_income=0,
    interest=50,
    net_profit=200,
):
    """
    RatioEngine expects the P&L fields at fixed positions.
    """
    row = [None] * 13

    row[3] = sales
    row[4] = expenses
    row[5] = operating_profit
    row[7] = other_income
    row[8] = interest
    row[12] = net_profit

    return row


def make_bs(
    equity=1000,
    borrowings=200,
    investments=100,
    total_assets=1500,
):
    """
    RatioEngine expects the balance-sheet fields at fixed positions.
    """
    row = [None] * 13

    row[3] = equity
    row[4] = 0
    row[5] = borrowings
    row[10] = investments
    row[12] = total_assets

    return row


def make_cf(
    cfo=250,
    investing=-100,
):
    """
    RatioEngine expects cash-flow fields at fixed positions.
    """
    row = [None] * 5

    row[3] = cfo
    row[4] = investing

    return row


# ============================================================
# 1. ROE - POSITIVE EQUITY
# ============================================================


def test_roe_positive_equity(metrics):
    result = metrics.roe(
        net_profit=200,
        equity=1000,
    )

    assert result == 20.00


# ============================================================
# 2. ROE - NEGATIVE EQUITY
# ============================================================


def test_roe_negative_equity(metrics):
    result = metrics.roe(
        net_profit=200,
        equity=-1000,
    )

    assert result == -20.00


# ============================================================
# 3. ROE - ZERO EQUITY
# ============================================================


def test_roe_zero_equity(metrics):
    result = metrics.roe(
        net_profit=200,
        equity=0,
    )

    assert result is None


# ============================================================
# 4. DEBT / EQUITY - NORMAL
# ============================================================


def test_debt_to_equity_normal(metrics):
    result = metrics.debt_to_equity(
        total_debt=500,
        equity=1000,
    )

    assert result == 0.50


# ============================================================
# 5. DEBT / EQUITY - DEBT FREE
# ============================================================


def test_debt_to_equity_debt_free(ratio_engine):
    latest = make_pnl()
    previous = make_pnl(
        sales=900,
        net_profit=150,
    )

    bs = make_bs(
        equity=1000,
        borrowings=0,
    )

    cf = make_cf()

    result = ratio_engine.calculate_from_records(
        "TEST",
        latest,
        previous,
        bs,
        cf,
    )

    assert result["Debt/Equity"] == 0


# ============================================================
# 6. INTEREST COVERAGE - NORMAL
# ============================================================


def test_interest_coverage_normal(metrics):
    result = metrics.interest_coverage(
        ebit=300,
        interest_expense=50,
    )

    assert result == 6.00


# ============================================================
# 7. INTEREST COVERAGE - ZERO INTEREST
# ============================================================


def test_interest_coverage_zero_interest(metrics):
    result = metrics.interest_coverage(
        ebit=300,
        interest_expense=0,
    )

    assert result is None


# ============================================================
# 8. HIGH LEVERAGE - D/E > 5
# ============================================================


def test_high_leverage_flag(ratio_engine):
    latest = make_pnl()
    previous = make_pnl(
        sales=900,
        net_profit=150,
    )

    bs = make_bs(
        equity=100,
        borrowings=600,
    )

    cf = make_cf()

    result = ratio_engine.calculate_from_records(
        "TEST",
        latest,
        previous,
        bs,
        cf,
    )

    assert result["Debt/Equity"] == 6.00
    assert result["High Leverage"] is True


# ============================================================
# 9. HIGH LEVERAGE - BELOW THRESHOLD
# ============================================================


def test_high_leverage_below_threshold(ratio_engine):
    latest = make_pnl()
    previous = make_pnl(
        sales=900,
        net_profit=150,
    )

    bs = make_bs(
        equity=1000,
        borrowings=500,
    )

    cf = make_cf()

    result = ratio_engine.calculate_from_records(
        "TEST",
        latest,
        previous,
        bs,
        cf,
    )

    assert result["Debt/Equity"] == 0.50
    assert result["High Leverage"] is False


# ============================================================
# 10. CAGR - NORMAL
# ============================================================


def test_cagr_normal():
    value, status = CAGR.calculate(
        start_value=100,
        end_value=200,
        years=5,
    )

    assert value == pytest.approx(14.87, abs=0.01)
    assert status == "OK"


# ============================================================
# 11. CAGR - TURNAROUND
# ============================================================


def test_cagr_turnaround():
    value, status = CAGR.calculate(
        start_value=-100,
        end_value=100,
        years=5,
    )

    assert value is None
    assert status == "TURNAROUND"


# ============================================================
# 12. CAGR - DECLINE TO LOSS
# ============================================================


def test_cagr_decline_to_loss():
    value, status = CAGR.calculate(
        start_value=100,
        end_value=-50,
        years=5,
    )

    assert value is None
    assert status == "DECLINE_TO_LOSS"


# ============================================================
# 13. CAGR - ZERO BASE
# ============================================================


def test_cagr_zero_base():
    value, status = CAGR.calculate(
        start_value=0,
        end_value=100,
        years=5,
    )

    assert value is None
    assert status == "ZERO_BASE"


# ============================================================
# 14. CAGR - BOTH NEGATIVE
# ============================================================


def test_cagr_both_negative():
    value, status = CAGR.calculate(
        start_value=-100,
        end_value=-50,
        years=5,
    )

    assert value is None
    assert status == "BOTH_NEGATIVE"


# ============================================================
# 15. CAGR - INSUFFICIENT DATA
# ============================================================


def test_cagr_insufficient_data():
    value, status = CAGR.calculate(
        start_value=None,
        end_value=100,
        years=5,
    )

    assert value is None
    assert status == "INSUFFICIENT_DATA"


# ============================================================
# 16. REVENUE CAGR
# ============================================================


def test_revenue_cagr():
    value, status = CAGR.revenue_cagr(
        start_sales=100,
        end_sales=200,
        years=5,
    )

    assert value == pytest.approx(14.87, abs=0.01)
    assert status == "OK"


# ============================================================
# 17. PROFIT CAGR
# ============================================================


def test_profit_cagr():
    value, status = CAGR.profit_cagr(
        start_profit=200,
        end_profit=400,
        years=5,
    )

    assert value == pytest.approx(14.87, abs=0.01)
    assert status == "OK"


# ============================================================
# 18. OPERATING PROFIT MARGIN
# ============================================================


def test_operating_profit_margin(metrics):
    result = metrics.operating_profit_margin(
        operating_profit=250,
        revenue=1000,
    )

    assert result == 25.00


# ============================================================
# 19. CFO QUALITY SCORE
# ============================================================


def test_cfo_quality_score(metrics):
    result = metrics.cfo_quality_score(
        cfo=300,
        net_profit=200,
    )

    assert result == 1.50


# ============================================================
# 20. CFO QUALITY - ZERO PROFIT
# ============================================================


def test_cfo_quality_zero_profit(metrics):
    result = metrics.cfo_quality_score(
        cfo=300,
        net_profit=0,
    )

    assert result is None
