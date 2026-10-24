from src.analysis.health_score import HealthScore
from src.analysis.metrics import FinancialMetrics
from src.database.database import Database


class Recommendation:

    def __init__(self):
        self.db = Database()
        self.db.connect()

        self.metrics = FinancialMetrics()
        self.health = HealthScore()

    def recommend(self, company_id):

        company = self.db.get_company(company_id)
        pnl = self.db.get_profit_loss(company_id)
        bs = self.db.get_balance_sheet(company_id)

        if company is None or len(pnl) < 2 or bs is None:
            print("Insufficient data.")
            return

        latest = pnl[0]
        previous = pnl[1]

        revenue_growth = self.metrics.revenue_growth(latest[3], previous[3])

        profit_growth = self.metrics.profit_growth(latest[12], previous[12])

        debt_equity = self.metrics.debt_to_equity(bs[5], bs[3])

        roe = self.metrics.roe(latest[12], bs[3])

        roce = self.metrics.roce(latest[12], bs[12])

        health_score = self.health.calculate_score(
            revenue_growth, profit_growth, debt_equity, roe, roce
        )

        rating = self.health.get_rating(health_score)

        if health_score >= 90:
            recommendation = "STRONG BUY"
        elif health_score >= 75:
            recommendation = "BUY"
        elif health_score >= 60:
            recommendation = "HOLD"
        else:
            recommendation = "SELL"

        print("\n" + "=" * 70)
        print("INVESTMENT RECOMMENDATION")
        print("=" * 70)

        print(f"Company         : {company[2]}")
        print(f"Revenue Growth  : {revenue_growth:.2f}%")
        print(f"Profit Growth   : {profit_growth:.2f}%")
        print(f"Debt/Equity     : {debt_equity:.2f}")
        print(f"ROE             : {roe:.2f}%")
        print(f"ROCE            : {roce:.2f}%")

        print("-" * 70)

        print(f"Health Score    : {health_score}/100")
        print(f"Rating          : {rating}")
        print(f"Recommendation  : {recommendation}")

        print("\nReason")

        if revenue_growth >= 10:
            print("✓ Strong Revenue Growth")
        else:
            print("✗ Weak Revenue Growth")

        if profit_growth >= 10:
            print("✓ Strong Profit Growth")
        else:
            print("✗ Weak Profit Growth")

        if debt_equity <= 1:
            print("✓ Healthy Debt Level")
        else:
            print("✗ High Debt Level")

        if roe >= 15:
            print("✓ Strong Return on Equity")
        else:
            print("✗ Weak Return on Equity")

        if roce >= 15:
            print("✓ Strong Return on Capital Employed")
        else:
            print("✗ Weak Return on Capital Employed")

        print("=" * 70)

    def close(self):
        self.db.close()
