from src.screener.engine import ScreenerEngine


class DynamicScreener:

    def __init__(self):
        self.engine = ScreenerEngine()

    def run(
        self,
        min_roe=None,
        max_debt=None,
        min_growth=None,
        sort_by=None,
        ascending=True,
        top=None,
    ):

        filters = {}

        if min_roe is not None:
            filters["roe"] = (min_roe, None)

        if max_debt is not None:
            filters["debt_to_equity"] = (None, max_debt)

        if min_growth is not None:
            filters["revenue_growth"] = (min_growth, None)

        df = self.engine.filter_data(filters)

        # Sorting
        if sort_by is not None:
            if sort_by not in df.columns:
                raise ValueError(f"Column '{sort_by}' not found.")

            df = df.sort_values(by=sort_by, ascending=ascending)

        # Top N
        if top is not None:
            df = df.head(top)

        return df.reset_index(drop=True)

    def close(self):
        self.engine.close()
