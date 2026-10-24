from src.screener.engine import ScreenerEngine

engine = ScreenerEngine()

presets = [
    "quality_compounder",
    "value_pick",
    "growth_accelerator",
    "dividend_champion",
    "debt_free_bluechip",
    "turnaround_watch"
]

for preset in presets:

    result = engine.filter_data(preset)

    print("=" * 60)
    print(preset.upper())
    print("=" * 60)
    print("Companies :", len(result))

    if len(result) > 0:
        print(result[["company_id"]].head())

engine.close()