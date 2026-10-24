from src.database.database import Database
from src.analysis.historical_ratio_engine import HistoricalRatioEngine


# ==========================================================
# EXTRACT YEAR
# ==========================================================

def extract_year(value):

    if value is None:
        return 0

    text = str(value).strip().upper()

    # Remove FY prefix
    text = text.replace("FY", "")

    # Extract numeric characters
    digits = "".join(
        character
        for character in text
        if character.isdigit()
    )

    if len(digits) >= 4:
        return int(digits[-4:])

    if len(digits) == 2:
        return 2000 + int(digits)

    return 0


# ==========================================================
# MAIN
# ==========================================================

def main():

    db = Database()
    db.connect()

    try:

        # ==================================================
        # CREATE TABLES
        # ==================================================

        db.create_historical_financial_ratios_table()
        db.create_financial_ratios_table()

        # ==================================================
        # CLEAR OLD DATA
        # ==================================================

        print("=" * 70)
        print("CLEARING OLD FINANCIAL RATIO DATA")
        print("=" * 70)

        db.execute_non_query(
            "DELETE FROM historical_financial_ratios"
        )

        db.execute_non_query(
            "DELETE FROM financial_ratios"
        )

        # ==================================================
        # CREATE HISTORICAL RATIO ENGINE
        # ==================================================

        engine = HistoricalRatioEngine()

        companies = db.get_all_companies()

        total_historical = 0
        total_latest = 0
        skipped = 0

        print()
        print("=" * 70)
        print("FINANCIAL RATIO POPULATION")
        print("=" * 70)

        print(
            f"Found {len(companies)} companies"
        )

        print()

        # ==================================================
        # PROCESS EVERY COMPANY
        # ==================================================

        for company in companies:

            company_id = company[0]

            try:

                history = engine.calculate_company_history(
                    company_id
                )

            except Exception as error:

                print(
                    f"ERROR {company_id}: {error}"
                )

                skipped += 1

                continue

            # --------------------------------------------------
            # No historical data
            # --------------------------------------------------

            if not history:

                print(
                    f"Skipped {company_id} - "
                    f"insufficient financial data"
                )

                skipped += 1

                continue

            # ==================================================
            # SAVE ALL HISTORICAL RATIOS
            # ==================================================

            for record in history:

                db.save_historical_financial_ratio(
                    record["company_id"],
                    record["year"],
                    record["ratios"]
                )

                total_historical += 1

            # ==================================================
            # FIND LATEST AVAILABLE YEAR
            # ==================================================

            latest_record = max(
                history,
                key=lambda record: extract_year(
                    record["year"]
                )
            )

            latest_year = latest_record["year"]

            latest_ratios = latest_record["ratios"]

            # ==================================================
            # SAVE LATEST RATIO
            # ==================================================

            db.save_financial_ratios(
                company_id,
                latest_ratios
            )

            total_latest += 1

            print(
                f"{company_id} -> "
                f"{len(history)} historical years -> "
                f"latest {latest_year}"
            )

        # ==================================================
        # CLOSE HISTORICAL ENGINE
        # ==================================================

        engine.close()

        # ==================================================
        # SUMMARY
        # ==================================================

        print()
        print("=" * 70)
        print("FINANCIAL RATIO POPULATION COMPLETE")
        print("=" * 70)

        print(
            f"Companies Found    : {len(companies)}"
        )

        print(
            f"Latest Companies   : {total_latest}"
        )

        print(
            f"Historical Records : {total_historical}"
        )

        print(
            f"Skipped Companies  : {skipped}"
        )

        print("=" * 70)

    finally:

        # ==================================================
        # CLOSE DATABASE
        # ==================================================

        db.close()


# ==========================================================
# PROGRAM ENTRY POINT
# ==========================================================

if __name__ == "__main__":
    main()