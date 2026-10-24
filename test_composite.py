from src.screener.engine import ScreenerEngine

engine = ScreenerEngine()

df = engine.load_financial_data()

df = df.sort_values(
    by="composite_quality_score",
    ascending=False
)

print("=" * 80)
print("TOP 10 COMPOSITE QUALITY SCORE")
print("=" * 80)

print(
    df[
        [
            "company_id",
	    "broad_sector",
            "composite_quality_score",
            "sector_quality_score"
        ]
    ].head(10)
)

engine.close()