"""
DAY 34 - BATCH COMPANY TEARSHEET GENERATION

Reuses the validated Day 33 tearsheet template.

Requirements:
- Skip companies with fewer than 3 years of financial data.
- Generate one PDF per eligible company.
- Log skipped companies.
- Generate sector reports through sector_report.py.

Usage:
    python src/reports/batch_reports.py
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "database" / "n100.db"
TEARSHEET_DIR = ROOT / "reports" / "tearsheets"
OUTPUT_DIR = ROOT / "output"

TEARSHEET_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SKIPPED_PATH = OUTPUT_DIR / "skipped_tearsheets.csv"

MIN_YEARS = 3


def clean_ticker(value):
    return str(value).strip().upper()


def main():
    print("=" * 70)
    print("DAY 34 - BATCH TEARSHEET GENERATION")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query(
        "SELECT id, company_name FROM companies",
        conn,
    )

    cashflow = pd.read_sql_query(
        "SELECT company_id, year FROM cashflow",
        conn,
    )

    pnl = pd.read_sql_query(
        "SELECT company_id, year FROM profitandloss",
        conn,
    )

    ratios = pd.read_sql_query(
        "SELECT company_id, year FROM historical_financial_ratios",
        conn,
    )

    conn.close()

    companies["ticker"] = companies["id"].map(clean_ticker)

    for df in [cashflow, pnl, ratios]:
        df["company_id"] = df["company_id"].map(clean_ticker)

    # Use the union of financial sources so partial-data companies
    # are evaluated correctly.
    years_by_company = {}

    for df in [cashflow, pnl, ratios]:
        for ticker, group in df.groupby("company_id"):
            years = {str(x).strip() for x in group["year"].dropna()}
            years_by_company.setdefault(ticker, set()).update(years)

    skipped = []
    generated = []
    failed = []

    # Import the already-tested Day 33 template.
    from tearsheet import TearsheetData, build_tearsheet

    data = TearsheetData()

    total = len(companies)

    print(f"Companies expected : {total}")
    print(f"Minimum data years : {MIN_YEARS}")
    print("\nGenerating company PDFs...\n")

    for index, row in companies.iterrows():

        ticker = clean_ticker(row["ticker"])
        name = str(row.get("company_name", ticker))

        year_count = len(years_by_company.get(ticker, set()))

        if year_count < MIN_YEARS:
            skipped.append(
                {
                    "company_id": ticker,
                    "company_name": name,
                    "available_years": year_count,
                    "reason": f"Fewer than {MIN_YEARS} years of data",
                }
            )

            print(f"[SKIP] {ticker}: only {year_count} years")
            continue

        output_path = TEARSHEET_DIR / f"{ticker}_tearsheet.pdf"

        try:
            result = build_tearsheet(
                data,
                ticker,
                output_path,
            )

            if result and result.exists():
                size_kb = result.stat().st_size / 1024

                generated.append(
                    {
                        "company_id": ticker,
                        "company_name": name,
                        "available_years": year_count,
                        "file": str(result),
                        "size_kb": round(size_kb, 2),
                    }
                )

                print(f"[{index + 1}/{total}] {ticker}: " f"{size_kb:.1f} KB")

            else:
                failed.append(
                    {
                        "company_id": ticker,
                        "company_name": name,
                        "reason": "PDF was not created",
                    }
                )

                print(f"[FAIL] {ticker}: PDF not created")

        except Exception as exc:
            failed.append(
                {
                    "company_id": ticker,
                    "company_name": name,
                    "reason": str(exc),
                }
            )

            print(f"[FAIL] {ticker}: {exc}")

    data.close()

    skipped_df = pd.DataFrame(
        skipped,
        columns=[
            "company_id",
            "company_name",
            "available_years",
            "reason",
        ],
    )

    skipped_df.to_csv(
        SKIPPED_PATH,
        index=False,
    )

    # --------------------------------------------------------
    # Sector reports
    # --------------------------------------------------------

    print("\n" + "-" * 70)
    print("GENERATING SECTOR REPORTS")
    print("-" * 70)

    sector_script = ROOT / "src" / "reports" / "sector_report.py"

    sector_result = subprocess.run(
        [sys.executable, str(sector_script)],
        cwd=str(ROOT),
        text=True,
    )

    print(f"\nSector report exit code: {sector_result.returncode}")

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("DAY 34 VALIDATION")
    print("=" * 70)

    print(f"Companies expected       : {total}")
    print(f"Tearsheet PDFs generated : {len(generated)}")
    print(f"Companies skipped        : {len(skipped)}")
    print(f"Generation failures      : {len(failed)}")

    actual_pdf_count = len(list(TEARSHEET_DIR.glob("*_tearsheet.pdf")))

    print(f"PDF files in directory   : {actual_pdf_count}")

    if skipped:
        print("\nSkipped companies:")
        print(skipped_df.to_string(index=False))

    if failed:
        failed_df = pd.DataFrame(failed)
        failed_path = OUTPUT_DIR / "tearsheet_generation_failures.csv"
        failed_df.to_csv(failed_path, index=False)

        print("\nFailures:")
        print(failed_df.to_string(index=False))
        print(f"\nFailure log: {failed_path}")

    print(f"\nSkipped log: {SKIPPED_PATH}")
    print(f"Tearsheet directory: {TEARSHEET_DIR}")

    if len(failed) == 0 and len(generated) + len(skipped) == total:
        print("\n✓ Every company was either generated or explicitly skipped.")
    else:
        print("\n⚠ Batch validation requires attention.")

    print("\n" + "=" * 70)
    print("DAY 34 BATCH REPORT GENERATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
