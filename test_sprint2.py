from src.analysis.metrics import FinancialMetrics
from src.analysis.cagr import CAGR
from src.analysis.validator import FinancialValidator

print("=" * 50)
print("SPRINT 2 TEST SUITE")
print("=" * 50)

# Revenue Growth
print("\nRevenue Growth")
print(FinancialMetrics.revenue_growth(1200, 1000))

# Profit Growth
print("\nProfit Growth")
print(FinancialMetrics.profit_growth(600, 500))

# Debt to Equity
print("\nDebt/Equity")
print(FinancialMetrics.debt_to_equity(200, 1000))

# ROE
print("\nROE")
print(FinancialMetrics.roe(350, 1000))

# ROCE
print("\nROCE")
print(FinancialMetrics.roce(420, 1200))

# Net Profit Margin
print("\nNet Profit Margin")
print(FinancialMetrics.net_profit_margin(250, 1000))

# Operating Margin
print("\nOperating Margin")
print(FinancialMetrics.operating_profit_margin(300, 1000))

# Interest Coverage
print("\nInterest Coverage")
print(FinancialMetrics.interest_coverage(500, 20))

# Asset Turnover
print("\nAsset Turnover")
print(FinancialMetrics.asset_turnover(1000, 1500))

# Free Cash Flow
print("\nFree Cash Flow")
print(FinancialMetrics.free_cash_flow(1200, -300))

# CAGR
print("\nRevenue CAGR")
print(CAGR.revenue_cagr(1000, 1800, 5))

# Validator
print("\nValidator")
print(FinancialValidator.is_valid_number(100))
print(FinancialValidator.is_positive(50))

print("\n")
print("=" * 50)
print("ALL TESTS COMPLETED")
print("=" * 50)