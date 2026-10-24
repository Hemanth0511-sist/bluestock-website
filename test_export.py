from src.screener.engine import ScreenerEngine
from src.screener.export import ScreenerExporter


engine = ScreenerEngine()

exporter = ScreenerExporter()

sheets = {

    "QUALITY_COMPOUNDER":
        engine.filter_data("quality_compounder"),

    "VALUE_PICK":
        engine.filter_data("value_pick"),

    "GROWTH_ACCELERATOR":
        engine.filter_data("growth_accelerator"),

    "DIVIDEND_CHAMPION":
        engine.filter_data("dividend_champion"),

    "DEBT_FREE_BLUECHIP":
        engine.filter_data("debt_free_bluechip"),

    "TURNAROUND_WATCH":
        engine.filter_data("turnaround_watch")

}

exporter.export(sheets)

engine.close()