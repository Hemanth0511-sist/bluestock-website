from src.screener.engine import ScreenerEngine

engine = ScreenerEngine()

result = engine.filter_quality_stocks(
    min_roe=20,
    min_roce=20,
    max_debt=0.50,
    min_revenue_growth=10,
    min_free_cash_flow=1000
)

print(
    result[
        [
            "company_id",
            "roe",
            "roce",
            "debt_to_equity",
            "revenue_growth",
            "free_cash_flow"
        ]
    ]
)

engine.close()