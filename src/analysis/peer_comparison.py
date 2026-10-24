from src.analysis.health_score import HealthScore
from src.analysis.metrics import FinancialMetrics
from src.database.database import Database


class PeerComparison:

    def __init__(self):
        self.db = Database()
        self.db.connect()

        self.metrics = FinancialMetrics()
        self.health = HealthScore()

    def compare(self, company_ids):

        print("\n" + "=" * 130)
        print("PEER COMPARISON")
        print("=" * 130)

        print(
            f"{'Company':<30}"
            f"{'Rev %':>10}"
            f"{'Profit %':>12}"
            f"{'D/E':>10}"
            f"{'ROE':>10}"
            f"{'ROCE':>10}"
            f"{'Health':>10}"
            f"{'Recommendation':>18}"
        )

        print("-" * 130)

        best_company = ""
        best_health = -1

        for company_id in company_ids:

            company = self.db.get_company(company_id)
            pnl = self.db.get_profit_loss(company_id)
            bs = self.db.get_balance_sheet(company_id)

            if company is None or len(pnl) < 2 or bs is None:
                continue

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

            if health_score >= 90:
                recommendation = "STRONG BUY"
            elif health_score >= 75:
                recommendation = "BUY"
            elif health_score >= 60:
                recommendation = "HOLD"
            else:
                recommendation = "SELL"

            if health_score > best_health:
                best_health = health_score
                best_company = company[2]

            print(
                f"{company[2]:<30}"
                f"{revenue_growth:>10.2f}"
                f"{profit_growth:>12.2f}"
                f"{debt_equity:>10.2f}"
                f"{roe:>10.2f}"
                f"{roce:>10.2f}"
                f"{health_score:>10}"
                f"{recommendation:>18}"
            )

        print("=" * 130)
        print(f"Best Company : {best_company}")
        print(f"Health Score : {best_health}/100")
        print("=" * 130)

    def close(self):
        self.db.close()
