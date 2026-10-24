from src.analysis.metrics import FinancialMetrics
from src.database.database import Database


class Recommendation:

    def __init__(self):
        self.db = Database()
        self.db.connect()

    def strong_buy(self):

        query = """
        SELECT
            c.company_name,
            r.final_score,
            r.recommendation,
            r.overall_rank
        FROM company_rankings r
        INNER JOIN companies c
            ON r.company_id = c.id
        WHERE r.final_score >= 80
        ORDER BY r.final_score DESC,
                 r.overall_rank ASC;
        """

        companies = self.db.execute_query(query)

        if len(companies) == 0:
            print("\nNo Strong Buy companies found.")
            return

        print("\n" + "=" * 90)
        print("STRONG BUY RECOMMENDATIONS")
        print("=" * 90)

        print(f"{'Rank':<6}" f"{'Company':<65}" f"{'Score':<10}" f"{'Recommendation'}")

        print("-" * 90)

        for company in companies:

            print(
                f"{company[3]:<6}"
                f"{company[0].strip()[:60]:<65}"
                f"{company[1]:<10}"
                f"{company[2]}"
            )

        print("=" * 90)

    def buy(self):

        query = """
        SELECT
            c.company_name,
            r.final_score,
            r.recommendation,
            r.overall_rank
        FROM company_rankings r
        INNER JOIN companies c
            ON r.company_id = c.id
        WHERE r.final_score >= 70
          AND r.final_score < 80
        ORDER BY r.final_score DESC,
                 r.overall_rank ASC;
        """

        companies = self.db.execute_query(query)

        if len(companies) == 0:
            print("\nNo Buy companies found.")
            return

        print("\n" + "=" * 90)
        print("BUY RECOMMENDATIONS")
        print("=" * 90)

        print(f"{'Rank':<6}" f"{'Company':<65}" f"{'Score':<10}" f"{'Recommendation'}")

        print("-" * 90)

        for company in companies:

            print(
                f"{company[3]:<6}"
                f"{company[0].strip()[:60]:<65}"
                f"{company[1]:<10}"
                f"{company[2]}"
            )

        print("=" * 90)

    def hold(self):

        query = """
        SELECT
            c.company_name,
            r.final_score,
            r.recommendation,
            r.overall_rank
        FROM company_rankings r
        INNER JOIN companies c
            ON r.company_id = c.id
        WHERE r.final_score >= 60
          AND r.final_score < 70
        ORDER BY r.final_score DESC,
                 r.overall_rank ASC;
        """

        companies = self.db.execute_query(query)

        if len(companies) == 0:
            print("\nNo Hold companies found.")
            return

        print("\n" + "=" * 90)
        print("HOLD RECOMMENDATIONS")
        print("=" * 90)

        print(f"{'Rank':<6}" f"{'Company':<65}" f"{'Score':<10}" f"{'Recommendation'}")

        print("-" * 90)

        for company in companies:

            print(
                f"{company[3]:<6}"
                f"{company[0].strip()[:60]:<65}"
                f"{company[1]:<10}"
                f"{company[2]}"
            )

        print("=" * 90)

    def growth_stocks(self):

        companies = self.db.get_all_companies()

        growth_list = []

        for company in companies:

            company_id = company[0]
            company_name = company[2]

            pnl = self.db.get_profit_loss(company_id)

            if pnl is None or len(pnl) < 2:
                continue

            latest = pnl[0]
            previous = pnl[1]

            revenue_growth = FinancialMetrics.revenue_growth(latest[3], previous[3])

            profit_growth = FinancialMetrics.profit_growth(latest[12], previous[12])

            growth_score = round((revenue_growth + profit_growth) / 2, 2)

            growth_list.append((company_name, growth_score))

        growth_list.sort(key=lambda x: x[1], reverse=True)

        print("\n" + "=" * 90)
        print("TOP GROWTH STOCKS")
        print("=" * 90)

        print(f"{'Rank':<6}" f"{'Company':<65}" f"{'Growth Score'}")

        print("-" * 90)

        for i, company in enumerate(growth_list[:20], start=1):

            print(f"{i:<6}" f"{company[0].strip()[:60]:<65}" f"{company[1]}")

        print("=" * 90)

        # KEEP YOUR EXISTING CODE HERE
        print("=" * 90)

    # ADD VALUE STOCKS HERE
    def value_stocks(self):

        query = """
        SELECT
            c.company_name,
            m.pe_ratio,
            m.pb_ratio,
            m.dividend_yield_pct,
            m.market_cap_crore
        FROM market_cap m
        INNER JOIN companies c
            ON m.company_id = c.id
        WHERE m.year = (
            SELECT MAX(m2.year)
            FROM market_cap m2
            WHERE m2.company_id = m.company_id
        )
          AND m.pe_ratio IS NOT NULL
          AND m.pb_ratio IS NOT NULL
          AND m.dividend_yield_pct IS NOT NULL
          AND m.pe_ratio > 0
          AND m.pe_ratio <= 25
          AND m.pb_ratio > 0
          AND m.pb_ratio <= 5
          AND m.dividend_yield_pct >= 1
        ORDER BY
            m.pe_ratio ASC,
            m.pb_ratio ASC,
            m.dividend_yield_pct DESC;
        """

        companies = self.db.execute_query(query)

        if not companies:
            print("\nNo Value Stocks found.")
            return

        print("\n" + "=" * 110)
        print("TOP VALUE STOCKS")
        print("=" * 110)

        print(
            f"{'Rank':<6}"
            f"{'Company':<50}"
            f"{'P/E':<10}"
            f"{'P/B':<10}"
            f"{'Div Yield %':<15}"
            f"{'Market Cap'}"
        )

        print("-" * 110)

        for i, company in enumerate(companies[:20], start=1):

            company_name = str(company[0]).strip().replace("\n", " ")[:45]

            print(
                f"{i:<6}"
                f"{company_name:<50}"
                f"{company[1]:<10.2f}"
                f"{company[2]:<10.2f}"
                f"{company[3]:<15.2f}"
                f"{company[4]:.2f}"
            )

        print("=" * 110)

    def close(self):
        self.db.close()

    def quality_stocks(self):

        query = """
        SELECT
            c.company_name,
            f.roe,
            f.roce,
            f.cfo_quality,
            f.debt_to_equity
        FROM financial_ratios f
        INNER JOIN companies c
            ON f.company_id = c.id
        WHERE f.roe >= 15
          AND f.roce >= 15
          AND f.cfo_quality >= 1
          AND f.debt_to_equity <= 1
        ORDER BY
            f.roe DESC,
            f.roce DESC;
        """

        companies = self.db.execute_query(query)

        if not companies:
            print("\nNo Quality Stocks found.")
            return

        print("\n" + "=" * 110)
        print("TOP QUALITY STOCKS")
        print("=" * 110)

        print(
            f"{'Rank':<6}"
            f"{'Company':<50}"
            f"{'ROE %':<12}"
            f"{'ROCE %':<12}"
            f"{'CFO Quality':<15}"
            f"{'D/E'}"
        )

        print("-" * 110)

        for i, company in enumerate(companies[:20], start=1):

            company_name = str(company[0]).strip().replace("\n", " ")[:45]

            print(
                f"{i:<6}"
                f"{company_name:<50}"
                f"{company[1]:<12.2f}"
                f"{company[2]:<12.2f}"
                f"{company[3]:<15.2f}"
                f"{company[4]:.2f}"
            )

        print("=" * 110)

    def low_risk_stocks(self):

        query = """
        SELECT
            c.company_name,
            f.debt_to_equity,
            f.interest_coverage,
            f.icr_label,
            f.high_leverage
        FROM financial_ratios f
        INNER JOIN companies c
            ON f.company_id = c.id
        WHERE f.debt_to_equity IS NOT NULL
          AND f.interest_coverage IS NOT NULL
          AND f.debt_to_equity <= 1
          AND f.interest_coverage >= 3
          AND f.icr_warning = 0
          AND f.high_leverage = 0
        ORDER BY
            f.debt_to_equity ASC,
            f.interest_coverage DESC;
        """

        companies = self.db.execute_query(query)

        if not companies:
            print("\nNo Low Risk Stocks found.")
            return

        print("\n" + "=" * 110)
        print("TOP LOW RISK STOCKS")
        print("=" * 110)

        print(
            f"{'Rank':<6}"
            f"{'Company':<50}"
            f"{'D/E':<12}"
            f"{'Interest Cov.':<18}"
            f"{'ICR Status'}"
        )

        print("-" * 110)

        for i, company in enumerate(companies[:20], start=1):

            company_name = str(company[0]).strip().replace("\n", " ")[:45]

            print(
                f"{i:<6}"
                f"{company_name:<50}"
                f"{company[1]:<12.2f}"
                f"{company[2]:<18.2f}"
                f"{company[3]}"
            )

        print("=" * 110)

    def close(self):
        self.db.close()
