import os

import matplotlib.pyplot as plt
import numpy as np

from src.database.database import Database


class RadarChart:

    def __init__(self):

        self.db = Database()
        self.db.connect()

        self.output_folder = "reports/radar_charts"

        os.makedirs(self.output_folder, exist_ok=True)

    def close(self):

        self.db.close()

    def load_financial_ratios(self):

        query = """
        SELECT
            company_id,
            revenue_growth,
            profit_growth,
            net_profit_margin,
            roe,
            roce,
            debt_to_equity,
            interest_coverage,
            asset_turnover,
            free_cash_flow
        FROM financial_ratios
        """

        rows = self.db.execute_query(query)

        data = {}

        for row in rows:

            data[row[0]] = {
                "revenue_growth": row[1],
                "profit_growth": row[2],
                "net_profit_margin": row[3],
                "roe": row[4],
                "roce": row[5],
                "debt_to_equity": row[6],
                "interest_coverage": row[7],
                "asset_turnover": row[8],
                "free_cash_flow": row[9],
            }

        return data

    def load_peer_groups(self):

        peer_groups = self.db.get_peer_groups()

        grouped = {}

        for group_name, company_id, benchmark in peer_groups:

            if group_name not in grouped:

                grouped[group_name] = []

            grouped[group_name].append(company_id)

        return grouped

    def get_peer_group(self, company_id):

        peer_groups = self.load_peer_groups()

        for group_name, companies in peer_groups.items():

            if company_id in companies:
                return group_name

        return None

    def get_company_metrics(self, company_id):

        data = self.load_financial_ratios()

        if company_id not in data:
            return None

        return data[company_id]

    def get_peer_average(self, peer_group):

        financial_data = self.load_financial_ratios()
        peer_groups = self.load_peer_groups()

        if peer_group not in peer_groups:
            return None

        companies = peer_groups[peer_group]

        metrics = [
            "roe",
            "roce",
            "net_profit_margin",
            "debt_to_equity",
            "free_cash_flow",
            "revenue_growth",
            "profit_growth",
            "interest_coverage",
        ]

        averages = {}

        for metric in metrics:

            values = []

            for company in companies:

                if company in financial_data:

                    value = financial_data[company][metric]

                    if value is not None:
                        values.append(value)

            if len(values) == 0:
                averages[metric] = 0
            else:
                averages[metric] = sum(values) / len(values)

        return averages

    def generate_radar_chart(self, company_id):

        company = self.get_company_metrics(company_id)

        if company is None:
            print(f"{company_id} not found.")
            return

        peer_group = self.get_peer_group(company_id)

        if peer_group is None:
            self.generate_nifty_reference_chart(company_id)
            return

        peer_average = self.get_peer_average(peer_group)

        labels = ["ROE", "ROCE", "NPM", "D/E", "FCF", "Revenue", "PAT", "Interest"]

        company_values = [
            company["roe"],
            company["roce"],
            company["net_profit_margin"],
            company["debt_to_equity"],
            company["free_cash_flow"],
            company["revenue_growth"],
            company["profit_growth"],
            company["interest_coverage"],
        ]

        peer_values = [
            peer_average["roe"],
            peer_average["roce"],
            peer_average["net_profit_margin"],
            peer_average["debt_to_equity"],
            peer_average["free_cash_flow"],
            peer_average["revenue_growth"],
            peer_average["profit_growth"],
            peer_average["interest_coverage"],
        ]

        company_values += company_values[:1]
        peer_values += peer_values[:1]

        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()

        angles += angles[:1]

        fig = plt.figure(figsize=(8, 8))

        ax = plt.subplot(111, polar=True)

        ax.plot(angles, company_values, linewidth=2, label=company_id)

        ax.fill(angles, company_values, alpha=0.25)

        ax.plot(angles, peer_values, linestyle="--", linewidth=2, label="Peer Average")

        ax.set_xticks(angles[:-1])

        ax.set_xticklabels(labels, fontsize=10)

        ax.set_title(f"{company_id} Radar Chart", fontsize=14)

        ax.legend(loc="upper right")

        filename = os.path.join(self.output_folder, f"{company_id}_radar.png")

        plt.savefig(filename, dpi=300, bbox_inches="tight")

        plt.close()

        print(f"Generated : {filename}")

    def generate_nifty_reference_chart(self, company_id):

        financial_data = self.load_financial_ratios()

        if company_id not in financial_data:
            print(f"{company_id} not found.")
            return

        company = financial_data[company_id]

        roe_values = []

        for data in financial_data.values():

            if data["roe"] is not None:
                roe_values.append(data["roe"])

        if len(roe_values) == 0:
            print("No ROE data available.")
            return

        nifty_average = sum(roe_values) / len(roe_values)

        plt.figure(figsize=(6, 5))

        plt.bar(
            ["Company", "Nifty 100 Avg"],
            [company["roe"], nifty_average],
            color=["steelblue", "orange"],
        )

        plt.ylabel("ROE")

        plt.title(f"{company_id} vs Nifty 100 Average")

        plt.grid(axis="y", alpha=0.3)

        filename = os.path.join(self.output_folder, f"{company_id}_radar.png")

        plt.savefig(filename, dpi=300, bbox_inches="tight")

        plt.close()

        print(f"Generated : {filename}")
