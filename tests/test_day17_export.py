import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, PROJECT_ROOT)

from src.screener.engine import ScreenerEngine
from src.screener.exporter import ScreenerExporter

print("=" * 70)
print("DAY 17 - COMPOSITE SCORE & EXCEL EXPORT")
print("=" * 70)

engine = ScreenerEngine()

try:

    # ------------------------------------------------------
    # LOAD DATA
    # ------------------------------------------------------

    df = engine.load_financial_data()

    print()
    print("FULL UNIVERSE:", len(df))

    # ------------------------------------------------------
    # COMPOSITE SCORE
    # ------------------------------------------------------

    scored = engine.calculate_composite_score(df)

    print(
        "COMPOSITE SCORE:",
        "PASS" if "composite_quality_score" in scored.columns else "FAIL",
    )

    print("FCF CAGR:", "PASS" if "fcf_cagr" in scored.columns else "FAIL")

    print(
        "SECTOR RELATIVE:",
        "PASS" if "sector_relative_score" in scored.columns else "FAIL",
    )

    # ------------------------------------------------------
    # EXPORT
    # ------------------------------------------------------

    exporter = ScreenerExporter(engine)

    output_file = exporter.export()

    print()
    print("=" * 70)
    print("DAY 17 STATUS")
    print("=" * 70)

    print("OUTPUT FILE:", output_file)

finally:

    engine.close()

print()
print("=" * 70)
print("DAY 17 TEST COMPLETE")
print("=" * 70)
