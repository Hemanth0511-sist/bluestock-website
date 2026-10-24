from src.database.database import Database
from src.analysis.ratios import RatioEngine
from src.analysis.report import ValidationReport
from src.utils.logger import EdgeCaseLogger


# -----------------------------------
# Database Connection
# -----------------------------------

db = Database()
db.connect()

# Create financial_ratios table (if not exists)
db.create_financial_ratios_table()

# Clear old ratio data
db.execute_non_query("DELETE FROM financial_ratios")

# -----------------------------------
# Initialize Objects
# -----------------------------------

engine = RatioEngine()
report = ValidationReport()
logger = EdgeCaseLogger()

# -----------------------------------
# Load Companies
# -----------------------------------

companies = db.get_all_companies()

print(f"Found {len(companies)} companies\n")

saved = 0
failed = 0

# -----------------------------------
# Process Companies
# -----------------------------------

for company in companies:

    company_id = company[0]

    ratios = engine.calculate_ratios(company_id)

    if ratios is None:

        report.add(None)

        logger.log(
            company_id,
            "Ratio calculation failed"
        )

        print(f"Skipped Company ID: {company_id}")

        failed += 1

        continue

    report.add(ratios)

    db.save_financial_ratios(
        company_id,
        ratios
    )

    print(f"Saved ratios for Company ID: {company_id}")

    saved += 1

# -----------------------------------
# Summary
# -----------------------------------

print("\n------------------------------")
print("Population Completed")
print("------------------------------")
print(f"Saved  : {saved}")
print(f"Skipped: {failed}")

print()

report.summary()

# -----------------------------------
# Close Connections
# -----------------------------------

engine.close()
db.close()	