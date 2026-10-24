import sqlite3
from pathlib import Path


class Database:
    """
    Database Manager for the N100 Financial Intelligence Platform.
    Handles database connection, execution of SQL queries,
    and provides helper methods for all modules.
    """

    def __init__(self, db_path="database/n100.db"):
        self.db_path = Path(db_path)
        self.connection = None
        self.cursor = None

    # ==========================================================
    # CONNECTION
    # ==========================================================

    def connect(self):
        """Connect to SQLite database."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.cursor = self.connection.cursor()

            print("=" * 60)
            print("Connected to SQLite Database")
            print(f"Database Path : {self.db_path.resolve()}")
            print("=" * 60)

            return self.connection

        except sqlite3.Error as e:
            print(f"Database Error : {e}")
            return None

    # ==========================================================
    # CLOSE CONNECTION
    # ==========================================================

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None
            print("Database connection closed.")

    # ==========================================================
    # QUERY HELPERS
    # ==========================================================

    def execute_query(self, query, params=()):
        """
        Execute SELECT query.

        Returns:
            list
        """
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def execute_one(self, query, params=()):
        """
        Execute SELECT query.

        Returns:
            tuple
        """
        self.cursor.execute(query, params)
        return self.cursor.fetchone()

    def execute_non_query(self, query, params=()):
        """
        Execute INSERT / UPDATE / DELETE / CREATE query.
        """
        self.cursor.execute(query, params)
        self.connection.commit()

    # ==========================================================
    # COMPANY METHODS
    # ==========================================================

    def get_company(self, company_id):

        query = """
        SELECT *
        FROM companies
        WHERE id = ?
        """

        return self.execute_one(query, (company_id,))

    def get_all_companies(self):

        query = """
        SELECT *
        FROM companies
        ORDER BY company_name
        """

        return self.execute_query(query)

    def get_peer_groups(self):

        query = """
        SELECT
            peer_group_name,
            company_id,
            is_benchmark
        FROM peer_groups
        ORDER BY
            peer_group_name,
            company_id;
        """

        return self.execute_query(query)

    # ==========================================================
    # PROFIT & LOSS
    # ==========================================================

    def get_profit_loss(self, company_id):

        query = """
        SELECT *
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY
            CASE
                WHEN year = 'TTM' THEN 0
                ELSE 1
            END,
            CAST(SUBSTR(year, -4) AS INTEGER) DESC
        LIMIT 2
        """

        return self.execute_query(query, (company_id,))

    def get_profit_history(self, company_id):

        query = """
        SELECT *
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY id
        """

        return self.execute_query(query, (company_id,))

    def get_all_profit_loss(self, company_id):

        query = """
        SELECT *
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY
            CASE
                WHEN year = 'TTM' THEN 1
                ELSE 0
            END,
            CAST(SUBSTR(year, -4) AS INTEGER) ASC
        """

        return self.execute_query(query, (company_id,))

    # ==========================================================
    # BALANCE SHEET
    # ==========================================================

    def get_balance_sheet(self, company_id):

        query = """
        SELECT *
        FROM balancesheet
        WHERE company_id = ?
        ORDER BY
            CAST(SUBSTR(year, -4) AS INTEGER) DESC
        LIMIT 1
        """

        return self.execute_one(query, (company_id,))

    def get_all_balance_sheet(self, company_id):

        query = """
        SELECT *
        FROM balancesheet
        WHERE company_id = ?
        ORDER BY
        CAST(SUBSTR(year, -4) AS INTEGER) ASC
        """

        return self.execute_query(query, (company_id,))

    # ==========================================================
    # CASH FLOW
    # ==========================================================

    def get_cashflow(self, company_id):

        query = """
        SELECT *
        FROM cashflow
        WHERE company_id = ?
        ORDER BY
            CAST(SUBSTR(year, -4) AS INTEGER) DESC
        LIMIT 1
        """

        return self.execute_one(query, (company_id,))

    def get_all_cashflow(self, company_id):

        query = """
        SELECT *
        FROM cashflow
        WHERE company_id = ?
        ORDER BY
         CAST(SUBSTR(year, -4) AS INTEGER) ASC
        """

        return self.execute_query(query, (company_id,))

    # ==========================================================
    # STOCK PRICE
    # ==========================================================

    def get_stock_prices(self, company_id):

        query = """
        SELECT *
        FROM stock_prices
        WHERE company_id = ?
        ORDER BY date DESC
        """

        return self.execute_query(query, (company_id,))

        # ==========================================================

    # PORTFOLIO TABLE
    # ==========================================================

    def create_portfolio_table(self):

        query = """
        CREATE TABLE IF NOT EXISTS portfolio(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            company_id TEXT NOT NULL,

            quantity INTEGER NOT NULL,

            buy_price REAL NOT NULL,

            added_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(company_id)
            REFERENCES companies(id)

        );
        """

        self.execute_non_query(query)

    # ==========================================================
    # WATCHLIST TABLE
    # ==========================================================

    def create_watchlist_table(self):

        query = """
        CREATE TABLE IF NOT EXISTS watchlist(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            company_id TEXT UNIQUE,

            added_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(company_id)
            REFERENCES companies(id)

        );
        """

        self.execute_non_query(query)

    # ==========================================================
    # FINANCIAL RATIOS TABLE
    # ==========================================================

    def create_financial_ratios_table(self):

        query = """
        CREATE TABLE IF NOT EXISTS financial_ratios(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            company_id TEXT,

            revenue_growth REAL,
            profit_growth REAL,
            net_profit_margin REAL,
            operating_profit_margin REAL,

            roe REAL,
            roce REAL,

            debt_to_equity REAL,
            interest_coverage REAL,
            asset_turnover REAL,

            net_debt REAL,
            free_cash_flow REAL,
            cfo_quality REAL,
            capex_intensity REAL,

            icr_label TEXT,
            icr_warning INTEGER,
            high_leverage INTEGER,

            FOREIGN KEY(company_id)
            REFERENCES companies(id)

        );
        """

        self.execute_non_query(query)

    # ==========================================================
    # HISTORICAL FINANCIAL RATIOS TABLE
    # ==========================================================

    def create_historical_financial_ratios_table(self):

        query = """
        CREATE TABLE IF NOT EXISTS historical_financial_ratios(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            company_id TEXT,

            year TEXT,

            revenue_growth REAL,
            profit_growth REAL,
            net_profit_margin REAL,
            operating_profit_margin REAL,

            roe REAL,
            roce REAL,

            debt_to_equity REAL,
            interest_coverage REAL,
            asset_turnover REAL,

            net_debt REAL,
            free_cash_flow REAL,
            cfo_quality REAL,
            capex_intensity REAL,

            icr_label TEXT,
            icr_warning INTEGER,
            high_leverage INTEGER,

            FOREIGN KEY(company_id)
            REFERENCES companies(id)

        );
        """

        self.execute_non_query(query)

    # ==========================================================
    # COMPANY RANKINGS TABLE
    # (DAY 16)
    # ==========================================================

    def create_company_rankings_table(self):

        query = """
        CREATE TABLE IF NOT EXISTS company_rankings(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            company_id TEXT UNIQUE,

            quality_score REAL,
            growth_score REAL,
            value_score REAL,
            risk_score REAL,

            final_score REAL,

            recommendation TEXT,

            overall_rank INTEGER,

            FOREIGN KEY(company_id)
            REFERENCES companies(id)

        );
        """

        self.execute_non_query(query)

    def create_peer_percentiles_table(self):

        query = """
        CREATE TABLE IF NOT EXISTS peer_percentiles(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            company_id TEXT,

            peer_group_name TEXT,

            metric TEXT,

            value REAL,

            percentile_rank REAL,

            year INTEGER

        );
        """

        self.execute_non_query(query)

        # ==========================================================

    # SAVE HISTORICAL FINANCIAL RATIOS
    # ==========================================================

    def save_historical_financial_ratio(self, company_id, year, ratios):

        query = """
        INSERT INTO historical_financial_ratios(

            company_id,
            year,

            revenue_growth,
            profit_growth,
            net_profit_margin,
            operating_profit_margin,

            roe,
            roce,

            debt_to_equity,
            interest_coverage,
            asset_turnover,

            net_debt,
            free_cash_flow,
            cfo_quality,
            capex_intensity,

            icr_label,
            icr_warning,
            high_leverage

        )

        VALUES(

            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?

        );
        """

        values = (
            company_id,
            year,
            ratios["Revenue Growth"],
            ratios["Profit Growth"],
            ratios["Net Profit Margin"],
            ratios["Operating Profit Margin"],
            ratios["ROE"],
            ratios["ROCE"],
            ratios["Debt/Equity"],
            ratios["Interest Coverage"],
            ratios["Asset Turnover"],
            ratios["Net Debt"],
            ratios["Free Cash Flow"],
            ratios["CFO Quality"],
            ratios["CapEx Intensity"],
            ratios["ICR Label"],
            int(ratios["ICR Warning"]),
            int(ratios["High Leverage"]),
        )

        self.execute_non_query(query, values)

    # ==========================================================
    # SAVE LATEST FINANCIAL RATIOS
    # ==========================================================

    def save_financial_ratios(self, company_id, ratios):

        query = """
        INSERT INTO financial_ratios(

            company_id,

            revenue_growth,
            profit_growth,
            net_profit_margin,
            operating_profit_margin,

            roe,
            roce,

            debt_to_equity,
            interest_coverage,
            asset_turnover,

            net_debt,
            free_cash_flow,
            cfo_quality,
            capex_intensity,

            icr_label,
            icr_warning,
            high_leverage

        )

        VALUES(

            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?

        );
        """

        values = (
            company_id,
            ratios["Revenue Growth"],
            ratios["Profit Growth"],
            ratios["Net Profit Margin"],
            ratios["Operating Profit Margin"],
            ratios["ROE"],
            ratios["ROCE"],
            ratios["Debt/Equity"],
            ratios["Interest Coverage"],
            ratios["Asset Turnover"],
            ratios["Net Debt"],
            ratios["Free Cash Flow"],
            ratios["CFO Quality"],
            ratios["CapEx Intensity"],
            ratios["ICR Label"],
            int(ratios["ICR Warning"]),
            int(ratios["High Leverage"]),
        )

        self.execute_non_query(query, values)

    def save_peer_percentile(
        self, company_id, peer_group_name, metric, value, percentile_rank, year
    ):

        query = """
        INSERT INTO peer_percentiles(

            company_id,
            peer_group_name,
            metric,
            value,
            percentile_rank,
            year

        )

        VALUES(

            ?, ?, ?, ?, ?, ?

        );
        """

        values = (company_id, peer_group_name, metric, value, percentile_rank, year)

        self.execute_non_query(query, values)

    # ==========================================================
    # COMPANY RANKINGS
    # ==========================================================

    def clear_company_rankings(self):

        query = """
        DELETE FROM company_rankings;
        """

        self.execute_non_query(query)

    def save_company_ranking(
        self,
        company_id,
        quality_score,
        growth_score,
        value_score,
        risk_score,
        final_score,
        recommendation,
        overall_rank,
    ):

        query = """
        INSERT INTO company_rankings(

            company_id,
            quality_score,
            growth_score,
            value_score,
            risk_score,
            final_score,
            recommendation,
            overall_rank

        )

        VALUES(

            ?, ?, ?, ?, ?, ?, ?, ?

        );
        """

        values = (
            company_id,
            quality_score,
            growth_score,
            value_score,
            risk_score,
            final_score,
            recommendation,
            overall_rank,
        )

        self.execute_non_query(query, values)

    def clear_peer_percentiles(self):

        query = """
        DELETE FROM peer_percentiles;
        """

        self.execute_non_query(query)

    def save_peer_percentile(
        self, company_id, peer_group_name, metric, value, percentile_rank, year
    ):

        query = """
        INSERT INTO peer_percentiles(

            company_id,
            peer_group_name,
            metric,
            value,
            percentile_rank,
            year

        )

        VALUES(

            ?, ?, ?, ?, ?, ?

        );
        """

        values = (company_id, peer_group_name, metric, value, percentile_rank, year)

        self.execute_non_query(query, values)

        # ==========================================================

    # PORTFOLIO HELPERS
    # ==========================================================

    def add_to_portfolio(self, company_id, quantity, buy_price):

        query = """
        INSERT INTO portfolio(

            company_id,
            quantity,
            buy_price

        )

        VALUES(

            ?, ?, ?

        );
        """

        self.execute_non_query(query, (company_id, quantity, buy_price))

    def remove_from_portfolio(self, portfolio_id):

        query = """
        DELETE FROM portfolio
        WHERE id = ?;
        """

        self.execute_non_query(query, (portfolio_id,))

    def get_portfolio(self):

        query = """
        SELECT
            p.id,
            p.company_id,
            c.company_name,
            p.quantity,
            p.buy_price,
            p.added_on

        FROM portfolio p

        LEFT JOIN companies c

        ON p.company_id = c.id

        ORDER BY c.company_name;
        """

        return self.execute_query(query)

    # ==========================================================
    # WATCHLIST HELPERS
    # ==========================================================

    def add_to_watchlist(self, company_id):

        query = """
        INSERT OR IGNORE INTO watchlist(

            company_id

        )

        VALUES(

            ?

        );
        """

        self.execute_non_query(query, (company_id,))

    def remove_from_watchlist(self, company_id):

        query = """
        DELETE FROM watchlist
        WHERE company_id = ?;
        """

        self.execute_non_query(query, (company_id,))

    def get_watchlist(self):

        query = """
        SELECT

            w.company_id,
            c.company_name,
            w.added_on

        FROM watchlist w

        LEFT JOIN companies c

        ON w.company_id = c.id

        ORDER BY c.company_name;
        """

        return self.execute_query(query)

    # ==========================================================
    # COMPANY RANKINGS
    # ==========================================================

    def get_company_rankings(self):

        query = """
        SELECT

            r.company_id,
            c.company_name,

            r.quality_score,
            r.growth_score,
            r.value_score,
            r.risk_score,

            r.final_score,

            r.recommendation,

            r.overall_rank

        FROM company_rankings r

        LEFT JOIN companies c

        ON r.company_id = c.id

        ORDER BY r.overall_rank;
        """

        return self.execute_query(query)

    def get_top_ranked_companies(self, limit=10):

        query = """
        SELECT

            r.company_id,
            c.company_name,

            r.final_score,

            r.recommendation,

            r.overall_rank

        FROM company_rankings r

        LEFT JOIN companies c

        ON r.company_id = c.id

        ORDER BY r.final_score DESC

        LIMIT ?;
        """

        return self.execute_query(query, (limit,))

    # ==========================================================
    # COMPANY SEARCH
    # ==========================================================

    def search_company(self, keyword):

        query = """
        SELECT *

        FROM companies

        WHERE company_name LIKE ?

        ORDER BY company_name;
        """

        return self.execute_query(query, (f"%{keyword}%",))

        # ==========================================================

    # DATABASE STATISTICS
    # ==========================================================

    def get_table_count(self, table_name):
        """
        Returns the number of rows in a table.
        """

        query = f"""
        SELECT COUNT(*)
        FROM {table_name};
        """

        result = self.execute_one(query)

        if result:
            return result[0]

        return 0

    def table_exists(self, table_name):
        """
        Check if a table exists.
        """

        query = """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name=?;
        """

        result = self.execute_one(query, (table_name,))

        return result is not None

    def get_financial_ratios(self, company_id):

        query = """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?;
        """

        return self.execute_one(query, (company_id,))

    # ==========================================================
    # DATABASE SUMMARY
    # ==========================================================

    def database_summary(self):

        tables = [
            "companies",
            "balancesheet",
            "cashflow",
            "profitandloss",
            "market_cap",
            "financial_ratios",
            "historical_financial_ratios",
            "portfolio",
            "watchlist",
            "company_rankings",
        ]

        print("\n" + "=" * 70)
        print("DATABASE SUMMARY")
        print("=" * 70)

        for table in tables:

            if self.table_exists(table):

                rows = self.get_table_count(table)

                print(f"{table:<35} {rows:>10} rows")

            else:

                print(f"{table:<35} NOT FOUND")

        print("=" * 70)

    # ==========================================================
    # DELETE HELPERS
    # ==========================================================

    def clear_table(self, table_name):
        """
        Delete all rows from a table.
        """

        query = f"""
        DELETE FROM {table_name};
        """

        self.execute_non_query(query)

    def drop_table(self, table_name):
        """
        Drop a table from the database.
        """

        query = f"""
        DROP TABLE IF EXISTS {table_name};
        """

        self.execute_non_query(query)

    # ==========================================================
    # TRANSACTION HELPERS
    # ==========================================================

    def begin_transaction(self):
        self.cursor.execute("BEGIN")

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    # ==========================================================
    # CONNECTION STATUS
    # ==========================================================

    def is_connected(self):

        return self.connection is not None

    # ==========================================================
    # CLOSE DATABASE
    # ==========================================================

    def close(self):
        """
        Close SQLite connection safely.
        """

        try:

            if self.cursor:
                self.cursor.close()

            if self.connection:
                self.connection.close()

            self.cursor = None
            self.connection = None

            print("=" * 60)
            print("Database connection closed successfully.")
            print("=" * 60)

        except sqlite3.Error as e:

            print(f"Close Error: {e}")
