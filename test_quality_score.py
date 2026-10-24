from src.analysis.quality_score import QualityScore

sample = {
    "ROE": 24,
    "ROCE": 28,
    "Net Profit Margin": 18,
    "Revenue Growth": 16,
    "Profit Growth": 19,
    "Debt/Equity": 0.35,
    "Interest Coverage": 8,
    "CFO Quality": 1.4,
    "High Leverage": False
}

print("Quality Score =", QualityScore.calculate(sample))