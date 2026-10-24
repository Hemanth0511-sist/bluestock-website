from datetime import datetime
from pathlib import Path


class EdgeCaseLogger:

    def __init__(self):

        Path("logs").mkdir(exist_ok=True)

        self.file = Path("logs/ratio_edge_cases.log")

    def log(self, company_id, reason):

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.file, "a", encoding="utf-8") as f:

            f.write(f"{timestamp} | {company_id} | {reason}\n")
