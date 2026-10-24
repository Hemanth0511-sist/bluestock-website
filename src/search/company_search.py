from src.database.database import Database


class CompanySearch:

    def __init__(self):
        self.db = Database()
        self.db.connect()

    def search_company(self, keyword):

        query = """
        SELECT id, company_name
        FROM companies
        WHERE id LIKE ?
           OR company_name LIKE ?
        ORDER BY company_name;
        """

        result = self.db.execute_query(query, (f"%{keyword}%", f"%{keyword}%"))

        if not result:
            print("No company found.")
            return

        print("\nSearch Results")
        print("-" * 50)

        for company in result:
            print(company)

    def close(self):
        self.db.close()
