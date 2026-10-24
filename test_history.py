from src.analysis.historical_ratio_engine import HistoricalRatioEngine

engine = HistoricalRatioEngine()

history = engine.calculate_company_history("TCS")

print(f"Years Found: {len(history)}\n")

for item in history[:5]:
    print(item["year"])
    print(item["ratios"])
    print("-" * 50)

engine.close()