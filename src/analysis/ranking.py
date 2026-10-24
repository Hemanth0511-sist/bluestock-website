from src.analysis.health_score import HealthScore
from src.analysis.metrics import FinancialMetrics
from src.analysis.score_calculator import ScoreCalculator
from src.database.database import Database


class CompanyRanking:

    def __init__(self):
        self.db = Database()
        self.db.connect()
        self.db.create_company_rankings_table()

        self.metrics = FinancialMetrics()
        self.health = HealthScore()
        self.score = ScoreCalculator()

    def rank_companies(self):

        companies = self.db.get_all_companies()

        rankings = []

        for company in companies:

            company_id = company[0]
            company_name = company[2]

            pnl = self.db.get_profit_loss(company_id)
            bs = self.db.get_balance_sheet(company_id)

            if pnl is None or len(pnl) < 2 or bs is None:
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

            rating = self.health.get_rating(health_score)

            rankings.append(
                {
                    "id": company_id,
                    "name": company_name,
                    "score": health_score,
                    "rating": rating,
                }
            )

        # Sort rankings
        rankings.sort(key=lambda x: x["score"], reverse=True)

        # Clear old rankings
        self.db.clear_company_rankings()

        # Save new rankings
        for rank, company in enumerate(rankings, start=1):

            self.db.save_company_ranking(
                company_id=company["id"],
                quality_score=0,
                growth_score=0,
                value_score=0,
                risk_score=0,
                final_score=company["score"],
                recommendation=company["rating"],
                overall_rank=rank,
            )

        print("\n" + "=" * 90)
        print("TOP COMPANY RANKINGS")
        print("=" * 90)

        print(f"{'Rank':<6}" f"{'Company':<65}" f"{'Score':<10}" f"{'Rating'}")

        print("-" * 90)

        for i, company in enumerate(rankings[:20], start=1):

            print(
                f"{i:<6}"
                f"{company['name']:<65}"
                f"{company['score']:<10}"
                f"{company['rating']}"
            )

        print("=" * 90)

    def close(self):
        self.db.close()
