from src.database.database import Database

db = Database()
db.connect()

count = db.execute_one(
    "SELECT COUNT(*) FROM financial_ratios"
)

print("Rows in financial_ratios:", count[0])

db.close()