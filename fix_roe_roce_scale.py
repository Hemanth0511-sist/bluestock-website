import sqlite3
import shutil
from pathlib import Path

DB_PATH = Path("database/n100.db")
BACKUP_PATH = Path("database/n100_before_roe_roce_fix.db")

# Create an additional backup
shutil.copy2(DB_PATH, BACKUP_PATH)

conn = sqlite3.connect(DB_PATH)

try:
    cursor = conn.cursor()

    print("=" * 60)
    print("ROE / ROCE SCALE FIX")
    print("=" * 60)

    # ----------------------------------------------------------
    # Show values before fixing
    # ----------------------------------------------------------

    print("\nBEFORE FIX - historical_financial_ratios")

    rows = cursor.execute("""
        SELECT company_id, year, roe, roce
        FROM historical_financial_ratios
        WHERE roe IS NOT NULL OR roce IS NOT NULL
        ORDER BY company_id, year
        LIMIT 10
    """).fetchall()

    for row in rows:
        print(row)

    # ----------------------------------------------------------
    # Correct historical ratios
    #
    # Old calculation:
    #     ratio * 100
    #
    # New calculation:
    #     ratio
    #
    # Therefore existing stored values are 100x too large.
    # ----------------------------------------------------------

    cursor.execute("""
        UPDATE historical_financial_ratios
        SET roe = roe / 100.0
        WHERE roe IS NOT NULL
    """)

    historical_roe = cursor.rowcount

    cursor.execute("""
        UPDATE historical_financial_ratios
        SET roce = roce / 100.0
        WHERE roce IS NOT NULL
    """)

    historical_roce = cursor.rowcount

    # ----------------------------------------------------------
    # Correct latest financial ratios too
    # ----------------------------------------------------------

    cursor.execute("""
        UPDATE financial_ratios
        SET roe = roe / 100.0
        WHERE roe IS NOT NULL
    """)

    current_roe = cursor.rowcount

    cursor.execute("""
        UPDATE financial_ratios
        SET roce = roce / 100.0
        WHERE roce IS NOT NULL
    """)

    current_roce = cursor.rowcount

    conn.commit()

    print("\nUPDATED:")
    print("Historical ROE rows :", historical_roe)
    print("Historical ROCE rows:", historical_roce)
    print("Current ROE rows    :", current_roe)
    print("Current ROCE rows   :", current_roce)

    # ----------------------------------------------------------
    # Verification
    # ----------------------------------------------------------

    print("\nAFTER FIX - BEL / HAL / INDIGO")

    rows = cursor.execute("""
        SELECT
            company_id,
            year,
            roe,
            roce
        FROM historical_financial_ratios
        WHERE company_id IN ('BEL', 'HAL', 'INDIGO')
        ORDER BY company_id, year
    """).fetchall()

    for row in rows:
        print(row)

    print("\n" + "=" * 60)
    print("ROE / ROCE FIX COMPLETE")
    print("Backup:", BACKUP_PATH)
    print("=" * 60)

except Exception as e:
    conn.rollback()
    print("\nERROR:", e)
    print("Database changes were rolled back.")

finally:
    conn.close()