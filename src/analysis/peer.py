from src.database.database import Database


class PeerPercentile:

    def __init__(self):

        self.db = Database()
        self.db.connect()

        self.db.create_peer_percentiles_table()

    def calculate_metric_percentile(
        self, group_name, companies, metric_name, column_index, year=2025, inverse=False
    ):

        values = []

        for company in companies:

            ratios = self.db.get_financial_ratios(company["company_id"])

            if ratios is None:
                continue

            value = ratios[column_index]

            if value is None:
                continue

            values.append({"company": company["company_id"], "value": value})

        values.sort(key=lambda x: x["value"])

        total = len(values)

        if total <= 1:
            print(f"{metric_name}: Not enough companies.")
            return

        print("\n" + "-" * 70)
        print(metric_name)
        print("-" * 70)

        for rank, row in enumerate(values):

            percentile = rank / (total - 1)

            if inverse:
                percentile = 1 - percentile

            percentile = round(percentile, 4)

            print(f"{row['company']:<15}" f"{row['value']:<15}" f"{percentile}")

            self.db.save_peer_percentile(
                company_id=row["company"],
                peer_group_name=group_name,
                metric=metric_name,
                value=row["value"],
                percentile_rank=percentile,
                year=year,
            )

    def calculate_cagr(self, start_value, end_value, years):

        if start_value is None:
            return None

        if end_value is None:
            return None

        if years <= 0:
            return None

        if start_value <= 0:
            return None

        if end_value <= 0:
            return None

        try:
            cagr = ((end_value / start_value) ** (1 / years) - 1) * 100

            return round(cagr, 2)

        except (ZeroDivisionError, ValueError, OverflowError, TypeError):
            return None

    def get_company_cagr(self, company_id):

        history = self.db.get_profit_history(company_id)

        if history is None:
            return None

        if len(history) < 5:
            return None

        first = history[0]
        last = history[-1]

        years = len(history) - 1

        revenue_cagr = self.calculate_cagr(first[3], last[3], years)

        pat_cagr = self.calculate_cagr(first[12], last[12], years)

        eps_cagr = self.calculate_cagr(first[13], last[13], years)

        return {
            "Revenue CAGR": revenue_cagr,
            "PAT CAGR": pat_cagr,
            "EPS CAGR": eps_cagr,
        }

    def calculate_cagr_percentile(
        self, group_name, companies, metric_name, key, year=2025
    ):

        values = []

        for company in companies:

            cagr = self.get_company_cagr(company["company_id"])

            if cagr is None:
                continue

            value = cagr.get(key)

            if value is None:
                continue

            values.append({"company": company["company_id"], "value": value})

        values.sort(key=lambda x: x["value"])

        total = len(values)

        if total <= 1:
            print(f"{metric_name}: Not enough companies.")
            return

        print("\n" + "-" * 70)
        print(metric_name)
        print("-" * 70)

        for rank, row in enumerate(values):

            percentile = rank / (total - 1)

            percentile = round(percentile, 4)

            print(f"{row['company']:<15}" f"{row['value']:<15}" f"{percentile}")

            self.db.save_peer_percentile(
                company_id=row["company"],
                peer_group_name=group_name,
                metric=metric_name,
                value=row["value"],
                percentile_rank=percentile,
                year=year,
            )

    def calculate_peer_percentiles(self):

        print("=" * 60)
        print("PEER PERCENTILE RANKING")
        print("=" * 60)

        peer_groups = self.db.get_peer_groups()

        print(f"Total Peer Group Records : {len(peer_groups)}")

        grouped = {}

        for group_name, company_id, benchmark in peer_groups:

            if group_name not in grouped:

                grouped[group_name] = []

            grouped[group_name].append(
                {"company_id": company_id, "benchmark": benchmark}
            )

        print("\nPeer Groups Found\n")

        self.db.clear_peer_percentiles()

        for group in grouped:

            print(f"{group:<35}" f"{len(grouped[group])} Companies")

        print("\nCalculating Peer Percentiles...")

        for group in grouped:

            print("\n" + "=" * 60)
            print(group)
            print("=" * 60)

            # ROE
            self.calculate_metric_percentile(
                group_name=group,
                companies=grouped[group],
                metric_name="ROE",
                column_index=6,
            )

            # ROCE
            self.calculate_metric_percentile(
                group_name=group,
                companies=grouped[group],
                metric_name="ROCE",
                column_index=7,
            )

            # Net Profit Margin
            self.calculate_metric_percentile(
                group_name=group,
                companies=grouped[group],
                metric_name="Net Profit Margin",
                column_index=4,
            )

            # Debt to Equity (Lower is Better)
            self.calculate_metric_percentile(
                group_name=group,
                companies=grouped[group],
                metric_name="Debt to Equity",
                column_index=8,
                inverse=True,
            )

            # Free Cash Flow
            self.calculate_metric_percentile(
                group_name=group,
                companies=grouped[group],
                metric_name="Free Cash Flow",
                column_index=12,
            )

            # Interest Coverage
            self.calculate_metric_percentile(
                group_name=group,
                companies=grouped[group],
                metric_name="Interest Coverage",
                column_index=9,
            )

            # Asset Turnover
            self.calculate_metric_percentile(
                group_name=group,
                companies=grouped[group],
                metric_name="Asset Turnover",
                column_index=10,
            )

            self.calculate_cagr_percentile(
                group_name=group,
                companies=grouped[group],
                metric_name="Revenue CAGR",
                key="Revenue CAGR",
            )

            self.calculate_cagr_percentile(
                group_name=group,
                companies=grouped[group],
                metric_name="PAT CAGR",
                key="PAT CAGR",
            )

            self.calculate_cagr_percentile(
                group_name=group,
                companies=grouped[group],
                metric_name="EPS CAGR",
                key="EPS CAGR",
            )

        print("\n" + "=" * 60)
        print("Peer Percentile Calculation Completed")
        print("=" * 60)

    def close(self):

        self.db.close()
