from src.analysis.ratios import RatioEngine
from src.database.database import Database


class HistoricalRatioEngine:

    def __init__(self):
        self.db = Database()
        self.db.connect()
        self.engine = RatioEngine()

    def calculate_company_history(self, company_id):
        """
        Calculate financial ratios for every available financial year.
        """

        pnl_records = self.db.get_all_profit_loss(company_id)
        bs_records = self.db.get_all_balance_sheet(company_id)
        cf_records = self.db.get_all_cashflow(company_id)

        if len(pnl_records) < 2:
            return []

        # -----------------------------
        # Create lookup dictionaries
        # -----------------------------

        bs_map = {}

        for row in bs_records:
            year = row[2]
            bs_map[year] = row

        cf_map = {}

        for row in cf_records:
            year = row[2]
            cf_map[year] = row

        history = []

        # -----------------------------
        # Calculate year-wise ratios
        # -----------------------------

        for i in range(len(pnl_records) - 1):

            current = pnl_records[i]
            previous = pnl_records[i + 1]

            year = current[2]

            if year not in bs_map:
                continue

            if year not in cf_map:
                continue

            ratios = self.engine.calculate_from_records(
                company_id, current, previous, bs_map[year], cf_map[year]
            )

            if ratios is None:
                continue

            history.append({"company_id": company_id, "year": year, "ratios": ratios})

        return history

    def close(self):
        self.engine.close()
        self.db.close()
