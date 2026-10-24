from src.backtest.backtest import PortfolioBacktest

backtest = PortfolioBacktest()

portfolio = backtest.portfolio_backtest(

    companies=[
        "TCS",
        "INFY",
        "HCLTECH"
    ],

    investment=300000

)

print("=" * 70)
print("PORTFOLIO BACKTEST")
print("=" * 70)

for stock in portfolio["results"]:

    print(
        f"{stock['company']:<10}"
        f"Return={stock['return_pct']:>8}%   "
        f"CAGR={stock['cagr']:>6}%"
    )

print("-" * 70)

print("Investment :", portfolio["investment"])
print("Final Value:", portfolio["final_value"])
print("Profit     :", portfolio["profit"])
print("Return %   :", portfolio["return_pct"])
print("CAGR       :", portfolio["cagr"])

backtest.close()