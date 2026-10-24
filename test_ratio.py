from src.analysis.ratios import RatioEngine

engine = RatioEngine()

ratios = engine.calculate_ratios("ABB")

for name, value in ratios.items():
    print(f"{name:<30}: {value}")

engine.close()