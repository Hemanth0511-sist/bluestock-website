from src.database.database import Database


class CompanyComparison:

    def __init__(self):

        self.db = Database()
        self.db.connect()

    def load_company_data(self):

        query = """
        SELECT

            fr.company_id,

            fr.roe,
            fr.roce,
            fr.revenue_growth,
            fr.profit_growth,
            fr.debt_to_equity,
            fr.free_cash_flow,

            mc.market_cap_crore,
            mc.pe_ratio,
            mc.pb_ratio

        FROM financial_ratios fr

        LEFT JOIN market_cap mc

            ON fr.company_id = mc.company_id

        WHERE mc.year = (

            SELECT MAX(year)

            FROM market_cap

            WHERE company_id = fr.company_id

        );
        """

        rows = self.db.execute_query(query)

        return rows

    def compare_companies(self, company_list):

        query = """
        SELECT

            fr.company_id,

            fr.roe,
            fr.roce,
            fr.revenue_growth,
            fr.profit_growth,
            fr.debt_to_equity,
            fr.free_cash_flow,

            mc.market_cap_crore,
            mc.pe_ratio,
            mc.pb_ratio

        FROM financial_ratios fr

        LEFT JOIN market_cap mc
            ON fr.company_id = mc.company_id

        WHERE fr.company_id IN ({})

        AND mc.year = (
            SELECT MAX(year)
            FROM market_cap
            WHERE company_id = fr.company_id
        );
        """.format(",".join(["?"] * len(company_list)))

        rows = self.db.execute_query(query, tuple(company_list))

        return rows

    def display_comparison(self, rows):

        print("\n" + "=" * 150)
        print("COMPANY COMPARISON")
        print("=" * 150)

        print(
            f"{'Company':<12}"
            f"{'ROE':>8}"
            f"{'ROCE':>10}"
            f"{'Revenue':>12}"
            f"{'Profit':>12}"
            f"{'D/E':>10}"
            f"{'FCF':>12}"
            f"{'Market Cap':>15}"
            f"{'P/E':>10}"
            f"{'P/B':>10}"
        )

        print("-" * 150)

        for row in rows:

            print(
                f"{row[0]:<12}"
                f"{row[1]:>8.2f}"
                f"{row[2]:>10.2f}"
                f"{row[3]:>12.2f}"
                f"{row[4]:>12.2f}"
                f"{row[5]:>10.2f}"
                f"{row[6]:>12.2f}"
                f"{row[7]:>15.2f}"
                f"{row[8]:>10.2f}"
                f"{row[9]:>10.2f}"
            )

        print("=" * 150)

    def highlight_best(self, rows):

        if not rows:
            print("No companies to compare.")
            return

        metrics = {
            "Best ROE": (1, max),
            "Best ROCE": (2, max),
            "Best Revenue Growth": (3, max),
            "Best Profit Growth": (4, max),
            "Lowest Debt/Equity": (5, min),
            "Highest Free Cash Flow": (6, max),
            "Highest Market Cap": (7, max),
            "Lowest P/E": (8, min),
            "Lowest P/B": (9, min),
        }

        print("\n")
        print("=" * 70)
        print("BEST COMPANY BY METRIC")
        print("=" * 70)

        for metric_name, (index, func) in metrics.items():

            best_row = func(rows, key=lambda x: x[index])

            print(f"{metric_name:<25}" f"{best_row[0]:<15}" f"{best_row[index]}")

        print("=" * 70)

    def overall_winner(self, rows):

        if not rows:
            return

        scores = {}

        for row in rows:
            scores[row[0]] = 0

        metrics = [
            (1, max),  # ROE
            (2, max),  # ROCE
            (3, max),  # Revenue Growth
            (4, max),  # Profit Growth
            (5, min),  # Debt/Equity
            (6, max),  # Free Cash Flow
            (7, max),  # Market Cap
            (8, min),  # P/E
            (9, min),  # P/B
        ]

        for index, func in metrics:

            best = func(rows, key=lambda x: x[index])

            scores[best[0]] += 1

        print("\n")
        print("=" * 60)
        print("OVERALL WINNER")
        print("=" * 60)

        for company, score in scores.items():

            print(f"{company:<15} {score} Points")

        winner = max(scores.items(), key=lambda x: x[1])

        print("-" * 60)
        print(f"Winner : {winner[0]}")
        print(f"Score  : {winner[1]}/9")
        print("=" * 60)

    def close(self):

        self.db.close()
